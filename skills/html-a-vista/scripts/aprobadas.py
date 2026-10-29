#!/usr/bin/env python3
"""Mueve al repositorio de diseño solo las vistas que el revisor aprobó, tal como las aprobó.

Uso:
  python3 -B aprobadas.py huella <trabajo>/ola-3/repo/design/vistas/<épica>/<vista>.html
  python3 -B aprobadas.py mover <trabajo> <repo-de-diseño> [--pendientes <vista>[,<vista>...]]

huella  imprime `sha256:<hex>`, la huella de lo que el revisor ve de una vista: el sha256 de las líneas que daría
        `sha256sum` (o `shasum -a 256`) desde design/ sobre la vista y los compartidos que existan, en este orden:
        `vistas/<épica>/<vista>.html`, `tokens.css`, `components.css`, `proto.js`. Cambia si cambia la vista o
        cualquiera de los compartidos que la pintan. El revisor la escribe en su veredicto:
        `## <vista>: aprobada sha256:<hex>`.

mover   lee <trabajo>/ola-3/revision.md y la copia integrada <trabajo>/ola-3/repo/design/. Cada vista de la copia que
        es nueva o distinta de la del repositorio entra solo si su último veredicto es "aprobada" con una huella igual
        a la de la copia, y tiene en disco lo que el revisor lee, <trabajo>/ola-2/<vista>/contrato.md y
        <trabajo>/ola-3/inventario/<vista>.json; `tokens.css`, `components.css` y `proto.js` entran si cambiaron y
        entró alguna vista. Las secciones del spec no las toca.

        Si alguna vista queda fuera (no aprobada, sin veredicto, sin huella o con otra, sin contrato o inventario, o
        con otra del mismo nombre), no mueve nada. Con --pendientes, que nombra las vistas que ya tuvieron su segunda
        revisión y siguen sin aprobarse, mueve las aprobadas solo si las que quedan fuera son exactamente esas; si no
        coinciden, no mueve nada y dice cuáles sobran o faltan. Cualquier otro archivo de la copia (contratos,
        inventarios) no entra y se lista.

        Sale con 0 si entró todo lo que no es pendiente, 1 si no movió nada o dejó fuera un archivo, y 2 si falta
        revision.md o la copia.

Con uso incorrecto, o una ruta de huella que no es una vista bajo design/vistas/, sale con 2.
"""
import argparse
import hashlib
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
Resultado = namedtuple("Resultado", "movidos pendientes fuera problema")


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


def raiz_design(vista):
    """La carpeta design/ de una vista en design/vistas/<épica>/<vista>.html, o None si la ruta no es una vista."""
    vista = Path(vista).resolve()
    if vista.suffix != ".html" or not vista.is_file() or len(vista.parents) < 3 or vista.parents[1].name != "vistas":
        return None
    return vista.parents[2]


def huella(vista):
    """`sha256:<hex>` de las líneas de sha256sum de la vista y de los compartidos que existen, relativas a design/."""
    vista = Path(vista).resolve()
    design = raiz_design(vista)
    rutas = [vista.relative_to(design).as_posix()] + [c for c in COMPARTIDOS if (design / c).is_file()]
    lineas = "".join(f"{hashlib.sha256((design / r).read_bytes()).hexdigest()}  {r}\n" for r in rutas)
    return "sha256:" + hashlib.sha256(lineas.encode()).hexdigest()


def mover(trabajo, repo, pendientes=()):
    """Copia al repositorio lo aprobado si las vistas que quedan fuera son exactamente `pendientes`.

    Devuelve un Resultado: movidos (rutas bajo design/), pendientes y fuera ((ruta, motivo)), y problema, el motivo
    por el que no se movió nada, o None."""
    copia, design = trabajo / "ola-3" / "repo" / "design", repo / "design"
    candidatos = cambiados(copia, design)
    vistas = [p for p in candidatos if p.parts[0] == "vistas" and p.suffix == ".html"]
    otros = [p for p in candidatos if p not in vistas]
    por_nombre = {}
    for v in vistas:
        por_nombre.setdefault(v.stem, []).append(v)
    leidos = leer((trabajo / "ola-3" / "revision.md").read_text(errors="ignore"), list(por_nombre))
    veredicto = {v: x.estado if x else None for v, x in leidos.items()}
    entran, sin_aprobar, fuera = [], [], []
    for v in vistas:
        if len(por_nombre[v.stem]) > 1:
            sin_aprobar.append((v, f"hay otra vista con el mismo nombre, `{v.stem}`, y el veredicto no dice de cuál es"))
        elif veredicto[v.stem] != "aprobada":
            sin_aprobar.append((v, {None: "sin veredicto en revision.md",
                                    "fuera de formato": f"su último encabezado en revision.md no sigue el formato `## {v.stem}: "
                                                        "aprobada sha256:<huella>` o `## <vista>: no aprobada`"}.get(veredicto[v.stem], veredicto[v.stem])))
        elif not leidos[v.stem].huella:
            sin_aprobar.append((v, "aprobada sin huella: el veredicto no dice qué versión de la vista vio el revisor"))
        elif leidos[v.stem].huella != (actual := huella(copia / v)):
            sin_aprobar.append((v, f"aprobada con la huella {leidos[v.stem].huella}, pero la copia tiene {actual}: la vista o un "
                                   "compartido cambió después de la revisión, y vuelve al revisor"))
        elif falta := sin_evidencia(trabajo, v.stem):
            sin_aprobar.append((v, f"aprobada, pero sin {falta}: el revisor aprueba leyendo el contrato y el inventario"))
        else:
            entran.append(v)
    afuera, nombradas = {v.stem for v, _ in sin_aprobar}, set(pendientes)
    problema = None
    if afuera != nombradas:
        if not nombradas:
            problema = (f"No se movió nada: quedan fuera {', '.join(sorted(afuera))}. Una vista fuera vuelve a su subagente de "
                        "la ola 2 y a una segunda revisión; si ya la tuvo y sigue sin aprobarse, nómbrala con "
                        "`--pendientes <vista>[,<vista>...]` y va al informe como pendiente.")
        else:
            detalle = [f"quedan fuera sin nombrar: {', '.join(sorted(afuera - nombradas))}" if afuera - nombradas else "",
                       f"nombradas que no quedan fuera: {', '.join(sorted(nombradas - afuera))}" if nombradas - afuera else ""]
            problema = ("No se movió nada: `--pendientes` tiene que nombrar exactamente las vistas que quedan fuera; "
                        + "; ".join(d for d in detalle if d) + ".")
        entran = []
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
    d = Path("design")
    if problema:
        fuera = sin_aprobar + fuera
    return Resultado([d / p for p in entran], [] if problema else [(d / p, m) for p, m in sin_aprobar],
                     [(d / p, m) for p, m in fuera], problema)


def lista_de_vistas(texto):
    vistas = [v.strip() for v in texto.split(",") if v.strip()]
    if not vistas:
        raise argparse.ArgumentTypeError("nombra al menos una vista: --pendientes <vista>[,<vista>...]")
    return vistas


def main(argv):
    uso = argparse.ArgumentParser(prog="aprobadas.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = uso.add_subparsers(dest="comando", required=True)
    sub.add_parser("huella").add_argument("vista")
    m = sub.add_parser("mover")
    m.add_argument("trabajo")
    m.add_argument("repo")
    m.add_argument("--pendientes", type=lista_de_vistas, default=[])
    args = uso.parse_args(argv[1:])
    if args.comando == "huella":
        if raiz_design(args.vista) is None:
            print(f"`{args.vista}` no es una vista en design/vistas/<épica>/<vista>.html.", file=sys.stderr)
            return 2
        print(huella(args.vista))
        return 0
    trabajo, repo = Path(args.trabajo).resolve(), Path(args.repo).resolve()
    revision, copia = trabajo / "ola-3" / "revision.md", trabajo / "ola-3" / "repo" / "design"
    for ruta, falta in ((revision, "el revisor no dejó su veredicto"), (copia, "no hay copia integrada")):
        if not ruta.exists():
            print(f"No existe `{ruta}`: {falta}. No se movió nada.")
            return 2
    r = mover(trabajo, repo, args.pendientes)
    print("# Vistas al repositorio\n")
    if r.problema:
        print(r.problema + "\n")
    print("## Movido\n")
    for p in r.movidos:
        print(f"- {p.as_posix()}")
    if not r.movidos:
        print("- Nada.")
    if r.pendientes:
        print("\n## Pendientes\n")
        for p, motivo in r.pendientes:
            print(f"- {p.as_posix()}: {motivo}")
        print("\nVan al informe como pendientes, con lo que el revisor dijo que falta.")
    if r.fuera:
        print("\n## Fuera del repositorio\n")
        for p, motivo in r.fuera:
            print(f"- {p.as_posix()}: {motivo}")
        print("\nUn archivo que no es vista ni compartido es de la carpeta de trabajo y no entra.")
    return 1 if r.problema or r.fuera else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
