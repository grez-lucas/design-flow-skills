#!/usr/bin/env python3
"""Mueve al repositorio de diseño solo las vistas que el revisor aprobó.

Uso: python3 -B aprobadas.py <trabajo> <repo-de-diseño>

Lee <trabajo>/ola-3/revision.md y la copia integrada <trabajo>/ola-3/repo/design/. Cada vista de la copia que es
nueva o distinta de la del repositorio entra solo si su último veredicto es "aprobada" y tiene en disco lo que el
revisor lee, <trabajo>/ola-2/<vista>/contrato.md y <trabajo>/ola-3/inventario/<vista>.json; `tokens.css`,
`components.css` y `proto.js` entran si cambiaron y entró alguna vista. Lo demás queda fuera y se lista: vistas no
aprobadas o sin veredicto, dos vistas con el mismo nombre y cualquier otro archivo de la copia (contratos,
inventarios). Las secciones del spec no las toca.

Sale con 0 si todo entró, 1 si algo quedó fuera (lo aprobado ya se movió) y 2 si falta revision.md o la copia.
"""
import re
import shutil
import sys
from collections import namedtuple
from pathlib import Path

COMPARTIDOS = ("tokens.css", "components.css", "proto.js")
FORMATO = re.compile(r"## (?P<vista>[^\s:,]+)(?:, segunda revisión)?: (?:(?P<no>no aprobada)|aprobada(?: (?P<huella>sha256:[0-9a-f]{64}))?)")
VEREDICTO = re.compile(r"(?:^|[:|·(-])\s*(no\s+)?aprobada\b")
SIN_NOMBRE = re.compile(r"[\s#|>-]*(?:veredicto|decisi[oó]n)?(?:\s+final)?\s*")
Veredicto = namedtuple("Veredicto", "estado huella")


def palabra(valor):
    """El valor como palabra suelta, no como parte de otro nombre (detalle no es detalle-lote)."""
    return rf"(?<![\w-]){re.escape(valor)}(?![\w-])"


def leer(revision, nombres, historico=False):
    """Último veredicto del revisor por vista en revision.md: {vista: Veredicto(estado, huella) o None}.

    Por defecto lee solo el formato fijo, un encabezado por vista: `## <vista>: aprobada sha256:<huella>`,
    `## <vista>: no aprobada`, y la segunda revisión al final como `## <vista>, segunda revisión: ...`. Vale el último
    en el archivo. Un encabezado que nombra una vista y dice "aprobada" sin seguir el formato cuenta como veredicto
    "fuera de formato": no aprueba, y tampoco deja en pie una aprobación anterior.

    historico=True lee además lo que escribieron los revisores de las iteraciones 1 y 2, antes del formato fijo; lo
    usa solo el calificador de esas corridas (pruebas/html-a-vista/grade.py --historico)."""
    if historico:
        return {v: Veredicto(e, None) if e else None for v, e in _historico(revision, nombres).items()}
    patrones = {v: re.compile(palabra(v.lower())) for v in nombres}
    ultimo = {}
    for linea in revision.splitlines():
        linea = linea.rstrip()
        m = FORMATO.fullmatch(linea)
        if m and m.group("vista") in patrones:
            ultimo[m.group("vista")] = Veredicto("no aprobada" if m.group("no") else "aprobada", m.group("huella"))
        elif linea.startswith("#") and re.search(r"aprobad", linea, re.I):
            for v, p in patrones.items():
                if p.search(linea.lower()):
                    ultimo[v] = Veredicto("fuera de formato", None)
    return {v: ultimo.get(v) for v in nombres}


def veredictos(revision, nombres, historico=False):
    """Último veredicto por vista: "aprobada", "no aprobada", "fuera de formato" o None. Ver leer()."""
    return {v: x.estado if x else None for v, x in leer(revision, nombres, historico).items()}


def _historico(revision, nombres):
    """Los veredictos de antes del formato fijo: "aprobada" o "no aprobada" tras dos puntos, guion, barra o paréntesis,
    en singular, para no leer un resumen ("6 aprobadas") ni una frase ("la tabla de tokens aprobada"). Va a la vista que
    la línea nombra antes del veredicto; un "Veredicto:" sin vista, a la del último encabezado que nombró una, o a la
    única vista. Vale el último en el archivo, salvo que diga "primera revisión": esa pierde contra cualquier otra."""
    patrones = {v: re.compile(palabra(v.lower())) for v in nombres}
    mejor, contexto, encabezado = {}, [], ""
    for n, linea in enumerate(revision.splitlines()):
        plano = re.sub(r"[*_`]", "", linea).strip().lower()
        if plano.startswith("#"):
            encabezado = plano
            contexto = [v for v, p in patrones.items() if p.search(plano)] or contexto
        m = VEREDICTO.search(plano)
        if not m:
            continue
        antes = plano[:m.start()]
        vistas = [v for v, p in patrones.items() if p.search(antes)]
        if not vistas and SIN_NOMBRE.fullmatch(antes):
            vistas = contexto or (list(nombres) if len(nombres) == 1 else [])
        rango = (0 if "primera" in plano or "primera" in encabezado else 1, n)
        for v in vistas:
            if v not in mejor or rango > mejor[v][0]:
                mejor[v] = (rango, "no aprobada" if m.group(1) else "aprobada")
    return {v: mejor[v][1] if v in mejor else None for v in nombres}


def cambiados(copia, destino):
    """Archivos de la copia que no están en el destino o tienen otro contenido, relativos a la copia."""
    return sorted(p.relative_to(copia) for p in copia.rglob("*")
                  if p.is_file() and not ((destino / p.relative_to(copia)).is_file()
                                          and (destino / p.relative_to(copia)).read_bytes() == p.read_bytes()))


def sin_evidencia(trabajo, vista):
    """Lo que el revisor tenía que leer y no está en disco: el contrato de la ola 2 y el inventario de la ola 3."""
    faltan = [str(r.relative_to(trabajo)) for r in (trabajo / "ola-2" / vista / "contrato.md",
                                                     trabajo / "ola-3" / "inventario" / f"{vista}.json") if not r.is_file()]
    return " ni ".join(f"`{r}`" for r in faltan)


def mover(trabajo, repo):
    """Copia al repositorio lo aprobado y devuelve (movidos, fuera): rutas bajo design/ y (ruta, motivo)."""
    copia, design = trabajo / "ola-3" / "repo" / "design", repo / "design"
    candidatos = cambiados(copia, design)
    vistas = [p for p in candidatos if p.parts[0] == "vistas" and p.suffix == ".html"]
    otros = [p for p in candidatos if p not in vistas]
    por_nombre = {}
    for v in vistas:
        por_nombre.setdefault(v.stem, []).append(v)
    veredicto = veredictos((trabajo / "ola-3" / "revision.md").read_text(errors="ignore"), list(por_nombre))
    entran, fuera = [], []
    for v in vistas:
        if len(por_nombre[v.stem]) > 1:
            fuera.append((v, f"hay otra vista con el mismo nombre, `{v.stem}`, y el veredicto no dice de cuál es"))
        elif veredicto[v.stem] != "aprobada":
            fuera.append((v, {None: "sin veredicto en revision.md",
                              "fuera de formato": f"su último encabezado en revision.md no sigue el formato `## {v.stem}: aprobada "
                                                  "sha256:<huella>` o `## <vista>: no aprobada`"}.get(veredicto[v.stem], veredicto[v.stem])))
        elif falta := sin_evidencia(trabajo, v.stem):
            fuera.append((v, f"aprobada, pero sin {falta}: el revisor aprueba leyendo el contrato y el inventario"))
        else:
            entran.append(v)
    for p in otros:
        if str(p) not in COMPARTIDOS:
            fuera.append((p, "no es una vista ni un archivo compartido"))
        elif entran:
            entran.append(p)
        else:
            fuera.append((p, "ninguna vista aprobada lo usa"))
    for p in entran:
        (design / p).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(copia / p, design / p)
    return [Path("design") / p for p in entran], [(Path("design") / p, m) for p, m in fuera]


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    trabajo, repo = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    revision, copia = trabajo / "ola-3" / "revision.md", trabajo / "ola-3" / "repo" / "design"
    for ruta, falta in ((revision, "el revisor no dejó su veredicto"), (copia, "no hay copia integrada")):
        if not ruta.exists():
            print(f"No existe `{ruta}`: {falta}. No se movió nada.")
            return 2
    movidos, fuera = mover(trabajo, repo)
    print("# Vistas al repositorio\n")
    print("## Movido\n")
    for p in movidos:
        print(f"- {p.as_posix()}")
    if not movidos:
        print("- Nada.")
    if fuera:
        print("\n## Fuera del repositorio\n")
        for p, motivo in fuera:
            print(f"- {p.as_posix()}: {motivo}")
        print("\nUna vista fuera vuelve a su subagente de la ola 2 y a una segunda revisión; si ya la tuvo, va al informe "
              "como pendiente. Un archivo que no es vista ni compartido es de la carpeta de trabajo y no entra.")
    return 1 if fuera else 0


if __name__ == "__main__":
    sys.exit(main())
