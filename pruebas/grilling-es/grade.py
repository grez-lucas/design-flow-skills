#!/usr/bin/env python3
"""Revisa las salidas de una iteración de grilling-es y escribe grading.json por corrida."""
import json, re, subprocess, sys
from pathlib import Path

SECCIONES = ["## Contexto", "## Historias", "## Estados por vista", "## Reglas", "## Decisiones del grilling", "## Fuera de alcance", "## Enlaces"]


def check(text, ok, evidence):
    return {"text": text, "passed": bool(ok), "evidence": str(evidence)[:400]}


def commits(repo):
    out = subprocess.run(["git", "-C", str(repo), "rev-list", "--count", "HEAD"], capture_output=True, text=True)
    return int(out.stdout.strip() or 0)


def specs_nuevos(repo):
    return sorted(p for p in (repo / "specs").glob("*/spec*.md") if p.parent.name != "recordatorios" or p.name != "spec.md")


def spec_checks(s, pendientes):
    """pendientes: (tema, patrón del tema, patrón de quién decide). El tema se busca en todo el spec;
    que quede pendiente con quién decide se verifica aparte, en la misma línea."""
    miss = [h for h in SECCIONES if h not in s]
    res = [check("El spec sigue la plantilla (siete secciones)", not miss, f"faltan: {miss}")]
    res.append(check("Historias con Como, quiero, para", bool(re.search(r"Como .+, quiero .+, para", s)), ""))
    res.append(check("Escenarios con Dado, cuando, entonces", bool(re.search(r"Dado .+cuando .+entonces", s, re.I)), ""))
    low = s.lower()
    for tema, pat, quien in pendientes:
        res.append(check(f"El spec trata lo que la persona no sabe: {tema}", re.search(pat, low) is not None, ""))
        lineas = [l for l in low.splitlines() if re.search(pat, l) and "pendiente" in l and re.search(quien, l)]
        res.append(check(f"Queda pendiente con quién decide: {tema}", lineas, lineas[:1]))
    return res


def ronda_checks(out):
    t = (out / "transcripcion.md").read_text() if (out / "transcripcion.md").exists() else ""
    recs = len(re.findall(r"➡️|recomend", t, re.I))
    return [check("Las preguntas llevan respuesta recomendada", recs >= 3, f"{recs} marcas de recomendación")]


def eval1(repo, out):
    nuevos = [p for p in (repo / "specs").rglob("*.md") if "recordatorios" not in p.parts]
    s = "\n".join(p.read_text() for p in nuevos)
    res = [check("Guarda un spec nuevo en specs/<épica>/spec.md", any(p.name == "spec.md" for p in nuevos), [str(p.relative_to(repo)) for p in nuevos])]
    res += spec_checks(s, [("límite de filas", r"l[íi]mite de filas", r"t[ée]cnic|equipo"), ("plan Básico", r"b[áa]sico", r"rodrigo|due[ñn]o")])
    low = s.lower()
    res.append(check("Trata PDF y correo", "pdf" in low and "correo" in low, ""))
    fuera = low.split("## fuera de alcance", 1)[-1].split("\n## ", 1)[0] if "## fuera de alcance" in low else ""
    res.append(check("PDF y correo quedan fuera de alcance", "pdf" in fuera and "correo" in fuera, fuera[:200]))
    res += extra_checks(s)
    res += ronda_checks(out)
    res.append(check("Hay commit nuevo", commits(repo) >= 2, commits(repo)))
    return res


def eval2(repo, out):
    nuevo = repo / "specs/recordatorios/spec.md"
    s = nuevo.read_text() if nuevo.exists() else ""
    anteriores = sorted((repo / "specs/recordatorios/anteriores").glob("spec-*.md"))
    viejo = anteriores[0].read_text() if anteriores else ""
    res = [check("El spec nuevo completo ocupa specs/recordatorios/spec.md", "whatsapp" in s.lower() and "US-REC-001" in s and "Superado" not in s[:300],
                 s.splitlines()[:3])]
    res.append(check("El anterior pasa a anteriores/spec-<fecha>.md con la línea Superado y sin otros cambios",
                     bool(anteriores) and "Superado" in "\n".join(viejo.splitlines()[:3]) and "Configurar recordatorio" in viejo,
                     [str(p.relative_to(repo)) for p in anteriores]))
    res.append(check("Las historias que siguen conservan su ID y la nueva toma el siguiente", "US-REC-001" in s and "US-REC-002" in s and "US-REC-003" in s, ""))
    res += spec_checks(s, [("proveedor", r"proveedor", r"rodrigo|due[ñn]o")])
    res += extra_checks(s)
    res += ronda_checks(out)
    res.append(check("Hay commit nuevo", commits(repo) >= 2, commits(repo)))
    return res


def estados_por_vista(seccion):
    """Una entrada por vista: un ítem de lista de primer nivel con su sublista, o una fila de tabla."""
    vistas = []
    for l in seccion.splitlines():
        t = l.strip()
        if t.startswith("|"):
            if not re.match(r"^\|[\s:|-]+\|?$", t) and not re.search(r"\|\s*vista\s*\|", t):
                vistas.append(t)
        elif re.match(r"^[-*]\s", l):
            vistas.append(t)
        elif re.match(r"^\s+([-*]|\d+\.)\s", l) and vistas:
            vistas[-1] += " " + t
    return vistas


def extra_checks(s):
    filas = [l for l in s.splitlines() if l.startswith("|") and "pendiente" in l.lower()]
    sin_nombre = [l for l in filas if re.search(r"\|\s*(por definir|-|nadie|sin definir)?\s*\|\s*pendiente", l.lower())]
    estados = s.split("## Estados por vista", 1)[-1].split("\n## ", 1)[0].lower()
    vistas = estados_por_vista(estados)
    base = ["vac", "cargando", "error", "sin permiso", "muchos datos"]
    incompletas = [v[:60] for v in vistas if not all(b in v for b in base)]
    return [check("Todo pendiente tiene nombre en Quién", not sin_nombre, sin_nombre),
            check("Cada vista declara los estados base (decidido, no aplica o pendiente)", vistas and not incompletas, incompletas)]


def eval3(repo, out):
    nuevos = [p for p in (repo / "specs").rglob("*.md") if p != repo / "specs/recordatorios/spec.md"]
    viejo = (repo / "specs/recordatorios/spec.md").read_text()
    t = ((out / "transcripcion.md").read_text() if (out / "transcripcion.md").exists() else "").lower()
    return [
        check("No crea un spec para un cambio cosmético", not nuevos, [str(p.relative_to(repo)) for p in nuevos]),
        check("No toca el spec congelado", "Superado" not in viejo, ""),
        check("Deriva a spec-a-html", "spec-a-html" in t, t[:200]),
    ]


REQUERIDO = "transcripcion.md"


def falta(out):
    """Una corrida sin salidas o sin transcripcion.md falla entera, en vez de pasar chequeos negativos por omisión."""
    if not out.is_dir() or not any(out.iterdir()):
        return "la carpeta outputs está vacía o no existe"
    f = out / REQUERIDO
    if not f.is_file() or not f.read_text(errors="ignore").strip():
        return f"falta {REQUERIDO} o está vacío"
    return None


def calificar(name, out):
    repo = out / "repo"
    return eval1(repo, out) if "exportar" in name else eval2(repo, out) if "whatsapp" in name else eval3(repo, out)


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
