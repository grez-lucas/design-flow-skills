#!/usr/bin/env python3
"""Revisa las salidas de una iteración de spec-a-html y escribe grading.json por corrida."""
import json, re, subprocess, sys
from pathlib import Path

HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgba?\(")
EXTERNAL = re.compile(r"""(?:src|href)\s*=\s*["']https?://""")
FIXTURE_TOKENS = Path(__file__).parent / "fixtures/equipo-diseno/design/tokens.css"
FIXTURE_LISTADO = Path(__file__).parent / "fixtures/equipo-diseno/design/vistas/miembros/listado.html"


def strip_css_comments(s):
    return re.sub(r"/\*.*?\*/", "", s, flags=re.S)


def raw_values_outside_tokens(path):
    s = path.read_text(errors="ignore")
    if path.suffix == ".html":
        styles = re.findall(r"<style[^>]*>(.*?)</style>", s, flags=re.S)
        inline = re.findall(r'style\s*=\s*"([^"]*)"', s)
        s = "\n".join(styles + inline)
    s = strip_css_comments(s)
    return HEX.findall(s)


def views(repo):
    return sorted((repo / "design/vistas").glob("*/*.html")) if (repo / "design/vistas").exists() else []


def all_html(repo):
    return [p for p in repo.rglob("*.html") if ".git" not in p.parts]


def commits(repo):
    out = subprocess.run(["git", "-C", str(repo), "rev-list", "--count", "HEAD"], capture_output=True, text=True)
    return int(out.stdout.strip() or 0)


def check(text, ok, evidence):
    return {"text": text, "passed": bool(ok), "evidence": evidence}


def archivos(repo, patron):
    return [p for p in repo.rglob(patron) if ".git" not in p.parts]


def common(repo, tickets, escenarios):
    """El contenido se revisa en todo HTML del repositorio; la ubicación, en un chequeo aparte."""
    v = views(repo)
    html = all_html(repo)
    res = []
    res.append(check("Las vistas están en design/vistas/<épica>/<vista>.html", len(v) >= 1,
                     f"{len(v)} vistas por épica; HTML totales: {[str(p.relative_to(repo)) for p in html]}"))
    linked = [p for p in html if "tokens.css" in p.read_text() and "components.css" in p.read_text()]
    res.append(check("Cada vista enlaza tokens.css y components.css", html and len(linked) == len(html),
                     f"{len(linked)}/{len(html)} enlazan ambos"))
    raw = {str(p.relative_to(repo)): raw_values_outside_tokens(p) for p in html}
    for css in archivos(repo, "*.css"):
        if css.name != "tokens.css":
            raw[str(css.relative_to(repo))] = raw_values_outside_tokens(css)
    bad = {k: x for k, x in raw.items() if x}
    res.append(check("Sin colores sueltos fuera de tokens.css (vistas y CSS compartido)", html and not bad,
                     json.dumps(bad, ensure_ascii=False)[:400] or "ninguno"))
    ext = [str(p.relative_to(repo)) for p in html if EXTERNAL.search(p.read_text())]
    res.append(check("Sin recursos externos ni CDN", not ext, f"con externos: {ext}"))
    body = " ".join(p.read_text() for p in html)
    miss_t = [t for t in tickets if t not in body]
    res.append(check(f"Las vistas citan los tickets {tickets}", html and not miss_t, f"faltan: {miss_t}"))
    norm = body.lower().replace("í", "i").replace("á", "a")
    miss_e = [e for e in escenarios if not re.search(e, norm)]
    res.append(check(f"Escenarios del spec presentes: {escenarios}", html and not miss_e, f"faltan: {miss_e}"))
    uses_state = [p for p in html if "data-state" in p.read_text()]
    proto = archivos(repo, "proto.js")
    res.append(check("Los escenarios se alternan con data-state y proto.js", html and len(uses_state) == len(html)
                     and proto, f"{len(uses_state)}/{len(html)} con data-state; proto.js: {[str(p.relative_to(repo)) for p in proto]}"))
    sizes = {str(p.relative_to(repo)): len(p.read_text()) for p in html}
    res.append(check("Cada vista bajo 40 KB (unos 10 mil tokens)", html and max(sizes.values()) < 40_000, json.dumps(sizes)))
    res.append(check("Hay al menos un commit nuevo", commits(repo) >= 2, f"commits: {commits(repo)}"))
    return res


def eval1(repo):
    toks = archivos(repo, "tokens.css")
    t = "\n".join(p.read_text() for p in toks)
    prefixes = ["--color-", "--space-", "--font-size-", "--radius-"]
    res = [check("Crea tokens.css con la convención de prefijos", toks and all(p in t for p in prefixes),
                 f"tokens.css: {[str(p.relative_to(repo)) for p in toks]}; prefijos faltantes: {[p for p in prefixes if p not in t]}"),
           check("tokens.css está en design/", (repo / "design/tokens.css").exists(), "")]
    res += common(repo, ["US-REC-001", "US-REC-002"], ["plan-basico|plan basico", "sin-permiso|sin permiso", "vacio", "muchos-datos|muchos datos"])
    return res


def eval2(repo):
    tok = repo / "design/tokens.css"
    before = dict(re.findall(r"(--color-[\w-]+)\s*:\s*([^;]+);", FIXTURE_TOKENS.read_text()))
    after = dict(re.findall(r"(--color-[\w-]+)\s*:\s*([^;]+);", tok.read_text())) if tok.exists() else {}
    changed = {k: (before[k], after.get(k)) for k in before if after.get(k, "").strip() != before[k].strip()}
    new = [k for k in after if k not in before]
    res = [check("Reutiliza los colores existentes de tokens.css sin cambiarlos (agregar con confirmación está permitido)", not changed,
                 f"cambiados: {changed}; nuevos: {new}")]
    res += common(repo, ["EQ-021", "EQ-022"], ["limite|límite", "vacio", "muchos-datos|muchos datos"])
    return res


def eval3(repo, outdir):
    listado = repo / "design/vistas/miembros/listado.html"
    same = listado.exists() and listado.read_text() == FIXTURE_LISTADO.read_text()
    notas = (outdir / "notas.md").read_text().lower() if (outdir / "notas.md").exists() else ""
    asks = any(w in notas for w in ["ticket", "spec", "grilling"])
    return [
        check("No edita la vista: el cambio es de comportamiento y alcance", same, "listado.html idéntico" if same else "listado.html modificado"),
        check("Pide actualizar spec, tickets o grilling antes del HTML", asks, notas[:300]),
    ]


REQUERIDO = "notas.md"


def falta(out):
    """Una corrida sin salidas o sin notas.md falla entera, en vez de pasar chequeos negativos por omisión."""
    if not out.is_dir() or not any(out.iterdir()):
        return "la carpeta outputs está vacía o no existe"
    f = out / REQUERIDO
    if not f.is_file() or not f.read_text(errors="ignore").strip():
        return f"falta {REQUERIDO} o está vacío"
    return None


def calificar(name, out):
    repo, name = out / "repo", name.split("-", 2)[2]
    if name.startswith("recordatorios"):
        return eval1(repo)
    if name.startswith("invitar"):
        return eval2(repo)
    return eval3(repo, out)


def main(iteration):
    runs = sorted(Path(iteration).glob("*/*/run-*"))
    if not runs:
        print(f"No hay corridas en {iteration}")
        return 1
    fallidas = 0
    for run in runs:
        name, config, out = run.parent.parent.name, run.parent.name, run / "outputs"
        error = falta(out)
        if error:
            fallidas += 1
            g = {"error": error, "expectations": [], "summary": {"passed": 0, "failed": 0, "total": 0, "pass_rate": 0.0}}
            print(f"{name}/{config}: ERROR, {error}")
        else:
            res = calificar(name, out)
            passed = sum(r["passed"] for r in res)
            g = {"expectations": res, "summary": {"passed": passed, "failed": len(res) - passed, "total": len(res),
                                                  "pass_rate": round(passed / len(res), 2)}}
            print(f"{name}/{config}: {passed}/{len(res)}")
        (run / "grading.json").write_text(json.dumps(g, ensure_ascii=False, indent=1))
    return 1 if fallidas else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
