#!/usr/bin/env python3
"""Revisa las salidas de una iteración de spec-a-tickets y escribe grading.json por corrida."""
import json, re, subprocess, sys
from pathlib import Path


def check(text, ok, evidence):
    return {"text": text, "passed": bool(ok), "evidence": str(evidence)[:400]}


def commits(repo):
    out = subprocess.run(["git", "-C", str(repo), "rev-list", "--count", "HEAD"], capture_output=True, text=True)
    return int(out.stdout.strip() or 0)


def tickets(repo, epica):
    d = repo / "specs" / epica / "tickets"
    return sorted(p for p in d.glob("[0-9][0-9]-*.md")) if d.exists() else []


def all_md(repo):
    return [p for p in repo.rglob("*.md") if ".git" not in p.parts and ".claude" not in p.parts]


def ticket_md(repo, epica):
    """Todo markdown de tickets de la épica, con cualquier nombre, salvo el índice y el spec."""
    return [p for p in all_md(repo) if epica in p.parts and p.name.lower() != "readme.md" and not p.name.startswith("spec")]


def eval1(repo):
    """El contenido se revisa en todo ticket de la épica; el nombre NN-titulo.md, en un chequeo aparte."""
    t = ticket_md(repo, "recordatorios")
    body = {p.name: p.read_text() for p in t}
    res = [check("Un archivo por historia", len(t) == 2, f"md en el repo: {[str(p.relative_to(repo)) for p in all_md(repo)]}"),
           check("Los tickets están en specs/recordatorios/tickets/NN-*.md", len(tickets(repo, "recordatorios")) == 2,
                 [p.name for p in tickets(repo, "recordatorios")])]
    heads = ["## 📝 Description", "## ✅ Acceptance Criteria", "## 🧪 Testing Requirements", "## 🎨 Designs & Mockups", "### ⚠️ Edge Cases", "### ❓ Open Questions"]
    miss = {n: [h for h in heads if h not in b] for n, b in body.items()}
    res.append(check("Siguen la plantilla de story (encabezados)", t and not any(miss.values()), miss))
    res.append(check("Títulos con el identificador del spec", t and all(re.search(r"US-REC-00[12]", b.splitlines()[0]) for b in body.values()),
                     [b.splitlines()[0] for b in body.values()]))
    res.append(check("Criterios con Dado, Cuando, Entonces", t and all(all(w in b for w in ["Dado", "Cuando", "Entonces"]) for b in body.values()), ""))
    res.append(check("Pruebas unitarias e integración quedan para DEV", t and all(b.lower().count("lo completa dev") >= 2 for b in body.values()),
                     {n: b.lower().count("lo completa dev") for n, b in body.items()}))
    res.append(check("Enlazan la vista en design/vistas/recordatorios/", t and all("design/vistas/recordatorios/" in b for b in body.values()), ""))
    res.append(check("Sin campo de aprobación", t and not any(re.search(r"^\*\*Aprob", b, re.M) for b in body.values()), ""))
    spec = (repo / "specs/recordatorios/spec.md").read_text()
    res.append(check("El spec queda congelado con una línea al inicio", "Congelado" in "\n".join(spec.splitlines()[:6]), spec.splitlines()[:4]))
    res.append(check("Índice specs/recordatorios/tickets/README.md", (repo / "specs/recordatorios/tickets/README.md").exists(), ""))
    res.append(check("Hay commit nuevo", commits(repo) >= 2, commits(repo)))
    return res


def eval2(repo, out):
    t = tickets(repo, "reservas")
    created = [str(p.relative_to(repo)) for p in all_md(repo) if p.name != "spec.md" and "notas" not in p.name]
    notas = (out / "notas.md").read_text().lower() if (out / "notas.md").exists() else ""
    return [
        check("No publica tickets sobre un spec débil", not t and not created, created),
        check("Recomienda volver al grilling o a refinar el spec con producto", re.search(r"grilling|refin|aclarar el spec|volver a producto", notas) is not None, notas[:300]),
    ]


def eval3(repo):
    t = tickets(repo, "stock")
    md = [p for p in all_md(repo) if "stock" in str(p) and p.name != "spec.md" and p.name.lower() != "readme.md"]
    files = t or md
    body = {p.name: p.read_text() for p in files}
    heads = ["## Contexto", "## Qué entrega", "## Criterios de aceptación", "## Fuera de alcance", "## Referencias"]
    miss = {n: [h for h in heads if h not in b] for n, b in body.items()}
    return [
        check("Un ticket por historia", len(files) == 2, [str(p.relative_to(repo)) for p in files]),
        check("Usan la plantilla del proyecto, no la de la skill", files and not any(miss.values()) and not any("📝" in b for b in body.values()), miss),
        check("Títulos con el formato BOD-<n>", files and all(re.search(r"BOD-\d+", b.splitlines()[0]) for b in body.values()),
              [b.splitlines()[0] for b in body.values()]),
        check("Hay commit nuevo", commits(repo) >= 2, commits(repo)),
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
    repo = out / "repo"
    return eval1(repo) if "facturo" in name else eval2(repo, out) if "agenda" in name else eval3(repo)


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
