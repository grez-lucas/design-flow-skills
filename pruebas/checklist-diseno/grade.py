#!/usr/bin/env python3
"""Revisa los informes de checklist-diseno contra los defectos plantados.

Regla: el contenido se busca en todo el informe, sin depender de secciones ni
formato, y la severidad (si el hallazgo bloquea) se verifica en un chequeo aparte.
"""
import json, re, subprocess, sys
from pathlib import Path


def check(text, ok, evidence=""):
    return {"text": text, "passed": bool(ok), "evidence": str(evidence)[:300]}


def sin_cambios(repo):
    out = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True).stdout
    return out.strip() == "", out


DEFECTOS = [
    ("Reponer: falta la columna proveedor del criterio de BOD-2", r"proveedor"),
    ("Reponer: falta el escenario error", r"escenario (de )?error|sin (escenario|estado) (de )?error|falta.{0,40}error|(no tiene|sin) (un )?estado de error"),
    ("Reponer: falta el estado plan-gratis del spec", r"plan.?gratis"),
    ("Reponer: color suelto #d93025", r"#d93025|(rojo|color)[^.\n]{0,80}(a mano|suelto|fuera de)"),
    # Dominio plantado en reponer.html: parece real y no está registrado (NXDOMAIN en a.nic.cl, 27-10-2026).
    # No se marca en el fixture porque el agente evaluado lee el repositorio.
    ("Reponer: dominio que parece real", r"abastos-quiltraco"),
    ("Reponer por plan: selector de plan dentro de la pantalla", r"select|selector"),
    ("Reponer por plan: texto de relleno", r"lorem"),
]
DE_OTRAS_VISTAS = r"reponer-plan|reponer\.html|plan.?gratis|#d93025|abastos-quiltraco|lorem|proveedor"
NO_LISTA = r"\b(no|casi|todav[íi]a no)\s+(est[áa]\s+)?lista"
NIEGA_LISTA = r"\b(no|casi|todav[íi]a no|a[úu]n no)\b[^.\n]{0,30}\blista\b"
PENDIENTE = r"\bpara\s+(\w+\s+){0,3}lista\b"


def dice_lista(low):
    """Líneas que dicen que la vista está lista. Si alguna línea lo niega, el veredicto es que no lo está, y
    una frase de algo pendiente ("para dejarla lista") no cuenta como afirmación."""
    lineas = low.splitlines()
    if any(re.search(NIEGA_LISTA, l) for l in lineas):
        return []
    return [l for l in lineas if re.search(r"\blista\b", re.sub(PENDIENTE, "", l))]


SEVERIDAD = r"bloque|conviene|aviso|menor|detalle|ajuste"
COLUMNA_SEVERIDAD = r"severidad|gravedad|nivel|prioridad|bloquea"


def sin_marcas(s):
    return re.sub(r"[*_`]", "", s).strip()


def es_etiqueta(linea):
    """Encabezado, línea en negrita sola o línea corta que termina en dos puntos."""
    s = linea.strip()
    if s.startswith("#"):
        return True
    if re.match(r"^([-*+]\s|\d+\.|\|)", s):
        return False
    if re.fullmatch(r"(\*\*|__)[^*_]+(\*\*|__):?", s):
        return True
    s = sin_marcas(s)
    return len(s) < 80 and s.endswith(":")


def declara_bloqueo(texto):
    """True si el texto empieza declarando que bloquea, False si declara lo contrario, None si no dice."""
    t = sin_marcas(texto).lower()
    if re.match(r"^\W*no bloque", t) or re.match(rf"^\W*({SEVERIDAD})", t) and not re.match(r"^\W*(lo que )?bloque", t):
        return False
    if re.match(r"^\W*(lo que )?bloque", t):
        return True
    return None


def hallazgo(texto):
    """La primera oración del ítem, sin viñeta ni prefijo de severidad: nombra el hallazgo. Lo que viene
    después es contexto y puede mencionar otro defecto sin calificarlo."""
    s = re.sub(r"^\s*([-*+]|\d+\.)\s+", "", texto)
    s = re.sub(rf"^(\*\*|__)?\s*(no )?({SEVERIDAD})\w*\s*:\s*(\*\*|__)?\s*", "", s)
    m = re.search(r"[.!?](\*\*)?\s", s)
    return s[: m.start() + 1] if m else s


def celdas(linea):
    return [c.strip() for c in re.split(r"(?<!\\)\|", linea.strip().strip("|"))]


def items(inf):
    """Cada ítem (línea de lista, párrafo o fila de tabla) con su hallazgo, el encabezado que lo gobierna
    y si bloquea, según lo declare el ítem, su columna de severidad o la etiqueta bajo la que está."""
    out, encabezado, etiqueta = [], "", ""
    lineas = inf.splitlines()
    col = None
    for n, linea in enumerate(lineas):
        if not linea.strip():
            col = None
            continue
        s = linea.strip()
        if s.startswith("|"):
            c = celdas(s)
            if all(re.fullmatch(r":?-+:?", x) for x in c if x):
                continue
            siguiente = lineas[n + 1].strip() if n + 1 < len(lineas) else ""
            if re.fullmatch(r"\|?(\s*:?-+:?\s*\|)+\s*:?-*:?\s*", siguiente):
                col = next((i for i, x in enumerate(c) if re.search(COLUMNA_SEVERIDAD, x.lower())), None)
                continue
            if col is not None and col < len(c):
                sev, resto = c[col], [x for i, x in enumerate(c) if i != col]
                bloquea = declara_bloqueo(sev)
            else:
                marcas = [x for x in c if declara_bloqueo(x) is not None and len(sin_marcas(x)) < 30]
                sev = marcas[0] if marcas else ""
                resto = [x for x in c if x is not sev]
                bloquea = declara_bloqueo(sev) if marcas else None
            texto = " · ".join(x for x in resto if x).lower()
            if bloquea is None:
                bloquea = declara_bloqueo(etiqueta) or False
            out.append({"texto": texto, "hallazgo": texto, "encabezado": encabezado, "bloquea": bloquea})
            continue
        if es_etiqueta(linea):
            low = sin_marcas(linea).lower().lstrip("# ")
            if s.startswith("#") and not re.match(rf"^\W*(lo que )?({SEVERIDAD})", low):
                encabezado = etiqueta = low
            else:
                etiqueta = low
            continue
        low = linea.lower()
        propio = declara_bloqueo(re.sub(r"^\s*([-*+]|\d+\.)\s+", "", low))
        if re.search(r"no bloque", low):
            bloquea = False
        elif propio is not None:
            bloquea = propio
        else:
            bloquea = declara_bloqueo(etiqueta) or False
        out.append({"texto": low, "hallazgo": hallazgo(low), "encabezado": encabezado, "bloquea": bloquea})
    return out


def eval1(out):
    inf = (out / "informe.md").read_text() if (out / "informe.md").exists() else ""
    low, its = inf.lower(), items(inf)
    res = []
    for texto, pat in DEFECTOS:
        res.append(check(f"Encuentra: {texto}", re.search(pat, low) is not None))
        marcado = [i["hallazgo"] for i in its if i["bloquea"] and re.search(pat, i["hallazgo"])]
        res.append(check(f"Lo marca como bloqueo: {texto}", marcado, marcado[:1]))
    lista = [l for l in low.splitlines() if re.search(r"editar[ -]producto", l) and re.search(r"\blista\b|se puede llevar|ya se puede", l) and not re.search(NO_LISTA, l)]
    res.append(check("Dice que Editar producto está lista", lista, lista[:1]))
    bloqueos_editar = [i["texto"] for i in its if i["bloquea"] and re.search(r"editar[ -]producto", i["texto"] + i["encabezado"])]
    res.append(check("Editar producto queda sin bloqueos", not bloqueos_editar, bloqueos_editar[:2]))
    limpio, diff = sin_cambios(out / "repo")
    res.append(check("No modifica el repositorio", limpio, diff))
    return res


def eval2(out):
    inf = (out / "informe.md").read_text() if (out / "informe.md").exists() else ""
    low = inf.lower()
    limpio, diff = sin_cambios(out / "repo")
    lista = dice_lista(low)
    bloqueos = [i["texto"] for i in items(inf) if i["bloquea"]]
    otras = sorted(set(m.group(0) for m in re.finditer(DE_OTRAS_VISTAS, low)))
    return [
        check("Dice que la vista está lista", lista, lista[:1]),
        check("No inventa hallazgos que bloquean", not bloqueos, bloqueos[:2]),
        check("Solo revisa la vista pedida", not otras, otras),
        check("No modifica el repositorio", limpio, diff),
    ]


def eval3(out):
    inf = (out / "informe.md").read_text() if (out / "informe.md").exists() else ""
    low, its = inf.lower(), items(inf)
    limpio, diff = sin_cambios(out / "repo")
    lista = dice_lista(low)
    bloqueos = [i["texto"] for i in its if i["bloquea"]]
    por_tickets = [i["texto"] for i in its if i["bloquea"] and re.search(r"ticket", i["hallazgo"])]
    return [
        check("Dice que la vista está lista", lista, lista[:1]),
        check("Cita el spec specs/proveedores/spec.md", "specs/proveedores/spec.md" in low),
        check("No la marca por no citar tickets", not por_tickets, por_tickets[:2]),
        check("No inventa hallazgos que bloquean", not bloqueos, bloqueos[:2]),
        check("No modifica el repositorio", limpio, diff),
    ]


REQUERIDO = "informe.md"


def falta(out):
    """Una corrida sin salidas o sin informe.md falla entera, en vez de pasar chequeos negativos por omisión."""
    if not out.is_dir() or not any(out.iterdir()):
        return "la carpeta outputs está vacía o no existe"
    f = out / REQUERIDO
    if not f.is_file() or not f.read_text(errors="ignore").strip():
        return f"falta {REQUERIDO} o está vacío"
    return None


def calificar(name, out):
    if "defectos" in name:
        return eval1(out)
    return eval3(out) if "solo-spec" in name else eval2(out)


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
