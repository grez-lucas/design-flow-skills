#!/usr/bin/env python3
"""Lleva a un repositorio de diseño que ya existe lo nuevo de los assets de spec-a-html, sin tocar lo propio.

Uso:
  python3 -B compartidos.py comparar <repo-de-diseño>
  python3 -B compartidos.py mostrar <repo-de-diseño>
  python3 -B compartidos.py aplicar <repo-de-diseño>

comparar  imprime un JSON con lo que falta en design/ respecto de assets/:
            tokens      {existe, faltan: [{bloque, token, valor}], omitidos: [{bloque, token, motivo}]}
            components  {existe, faltan: [selector], omitidos: [{selector, motivo}]}
            proto       {existe, difiere}
            cambios     true si aplicar escribiría algo
mostrar   imprime el diff unificado de lo que aplicar escribiría. No escribe.
aplicar   escribe lo que comparar lista e imprime el mismo JSON.

Tokens. Un token de assets/tokens.css falta si design/tokens.css no lo declara en ningún bloque. Se agrega en el
bloque con el mismo selector que en assets (`:root`, `[data-theme="dark"]`), en una línea nueva después de su última
declaración. Sin bloque `:root`, se agrega uno al final. Sin el bloque del tema oscuro, el valor oscuro queda en
omitidos: agregar el bloque le daría al producto un tema que no tiene.

Reglas. Cada selector de una regla de assets/components.css falta si design/components.css no tiene ese selector en
ninguna regla, a cualquier profundidad (`@media`, `@layer`). Uno que falta se agrega solo si nombra una clase que
design/components.css no usa, o si no nombra clases (`:where([data-frame])`, `*::before`): así la regla nueva solo
pinta elementos que lo propio no pinta. Si todas sus clases ya son del repositorio (`.btn:hover` con un `.btn`
propio), cambiaría cómo se ve un componente propio y queda en omitidos. Las reglas nuevas van al final, en el orden
de assets, con el comentario que las precede y solo con sus selectores que faltan; una regla dentro de un `@media`
va con su preludio.

proto.js. Si falta o difiere, se reemplaza por el de assets, sin modificar. Si falta components.css, se copia entero.

Nada de lo que ya está cambia: aplicar solo inserta, con el fin de línea del archivo. Sale con 2, sin escribir, si
no existe design/ o design/tokens.css, si tokens.css o components.css tienen llaves sin par, o con uso incorrecto.
"""
import argparse
import difflib
import json
import re
import shutil
import sys
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[1] / "assets"
OSCURO = '[data-theme="dark"]'
ENCABEZADO = "/* Reglas que agregó spec-a-html desde sus assets: este archivo no las tenía. */"
OCULTO = re.compile(r"""/\*.*?\*/|"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*'""", re.S)
CLASE = re.compile(r"\.(-?(?:\\[0-9a-fA-F]{1,6}\s?|\\[^\n0-9a-fA-F]|[\w-]|[^\x00-\x7f])+)")
ESCAPE = re.compile(r"\\(?:([0-9a-fA-F]{1,6})\s?|(.))", re.S)


class Ilegible(Exception):
    pass


# --- CSS -----------------------------------------------------------------------------------------

def enmascarar(css):
    """El CSS con comentarios y cadenas en blanco, con el mismo largo y los mismos saltos de línea."""
    return OCULTO.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), css)


def arbol(css, nombre):
    """Las reglas del CSS como nodos {preludio, desde, abre, cierra, hijos}: `desde` es donde empieza el texto de la
    regla, con los comentarios que la preceden, y `abre` y `cierra`, sus llaves."""
    m = enmascarar(css)
    raiz, pila, desde = [], [], 0
    hijos = raiz
    for i, c in enumerate(m):
        if c == "{":
            preludio = re.sub(r"/\*.*?\*/", "", css[desde:i], flags=re.S).strip()
            nodo = {"preludio": preludio, "desde": desde, "abre": i, "cierra": None, "hijos": []}
            hijos.append(nodo)
            pila.append((hijos, nodo))
            hijos, desde = nodo["hijos"], i + 1
        elif c == "}":
            if not pila:
                raise Ilegible(f"`{nombre}` cierra una llave que no abrió (posición {i}).")
            hijos, nodo = pila.pop()
            nodo["cierra"], desde = i, i + 1
        elif c == ";":
            desde = i + 1
    if pila:
        raise Ilegible(f"`{nombre}` deja una llave sin cerrar, la de `{pila[-1][1]['preludio'][:40]}`.")
    return raiz


def es_regla_at(nodo):
    return nodo["preludio"].startswith("@")


def separar(lista):
    """Los selectores de una lista separada por comas, sin cortar dentro de paréntesis ni corchetes."""
    partes, prof, actual = [], 0, ""
    for c in lista:
        if c in "([":
            prof += 1
        elif c in ")]":
            prof -= 1
        if c == "," and prof == 0:
            partes.append(actual)
            actual = ""
        else:
            actual += c
    return [p.strip() for p in partes + [actual] if p.strip()]


def normal(selector):
    """El selector con un solo espacio entre partes, sin espacios junto a `>`, `+`, `~` y `,` ni dentro de los
    paréntesis, y con comillas dobles."""
    s = re.sub(r"\s+", " ", selector.strip()).replace("'", '"')
    return re.sub(r"\s*([>+~,])\s*", r"\1", re.sub(r"\(\s+", "(", re.sub(r"\s+\)", ")", s)))


def sin_escapes(texto):
    def letra(m):
        if m.group(1):
            n = int(m.group(1), 16)
            return chr(n) if 0 < n <= 0x10FFFF else "\ufffd"
        return m.group(2)
    return ESCAPE.sub(letra, texto)


def clases(selector):
    """Las clases que un selector exige al elemento; las de un `:not()` no las exige."""
    return {sin_escapes(c).rstrip() for c in CLASE.findall(re.sub(r":not\([^()]*\)", "", selector))}


def recorrer(nodos):
    for nodo in nodos:
        yield nodo
        yield from recorrer(nodo["hijos"])


def selectores_y_clases(nodos):
    """Los selectores normalizados y las clases de todas las reglas, a cualquier profundidad."""
    selectores, nombres = set(), set()
    for nodo in recorrer(nodos):
        if not es_regla_at(nodo):
            for s in separar(nodo["preludio"]):
                selectores.add(normal(s))
                nombres |= clases(s)
    return selectores, nombres


def fin_de_linea(texto):
    return "\r\n" if "\r\n" in texto else "\n"


# --- components.css --------------------------------------------------------------------------------

def reglas_que_faltan(asset, nodos, propio, faltan, omitidos, prefijo="", primero=True):
    """Los textos de las reglas de `nodos` (del asset) que van al repositorio. `propio` son los selectores y las clases
    de design/components.css. Anota en `faltan` y `omitidos` cada selector."""
    selectores, nombres = propio
    textos = []
    for n, nodo in enumerate(nodos):
        comentario = "" if primero and n == 0 else asset[nodo["desde"]:nodo["abre"]].strip()
        comentario = "\n".join(re.findall(r"/\*.*?\*/", comentario, re.S))
        if es_regla_at(nodo):
            interiores = reglas_que_faltan(asset, nodo["hijos"], propio, faltan, omitidos, f"{prefijo}{nodo['preludio']} ", False)
            if interiores:
                cuerpo = "\n".join("  " + l if l else l for t in interiores for l in t.split("\n"))
                textos.append(("\n" + comentario + "\n" if comentario else "") + f"{nodo['preludio']} {{\n{cuerpo}\n}}")
            continue
        nuevos = []
        for s in separar(nodo["preludio"]):
            if normal(s) in selectores:
                continue
            propias = clases(s)
            if propias and propias <= nombres:
                omitidos.append({"selector": prefijo + s, "motivo": f"el repositorio ya define {', '.join(f'`.{c}`' for c in sorted(propias))}: "
                                 "la regla cambiaría cómo se ve un componente propio."})
            else:
                nuevos.append(s)
        if nuevos:
            faltan.append(prefijo + ", ".join(nuevos))
            regla = ", ".join(nuevos) + " " + asset[nodo["abre"]:nodo["cierra"] + 1]
            textos.append(("\n" + comentario + "\n" if comentario else "") + regla)
    return textos


def components(design, assets):
    asset = (assets / "components.css").read_text(encoding="utf-8")
    ruta = design / "components.css"
    existe = ruta.exists()
    texto = leer(ruta) if existe else ""
    propio = selectores_y_clases(arbol(texto, "components.css"))
    faltan, omitidos = [], []
    textos = reglas_que_faltan(asset, arbol(asset, "assets/components.css"), propio, faltan, omitidos)
    if not existe:
        return {"existe": False, "faltan": faltan, "omitidos": []}, asset
    nuevo = texto
    if textos:
        nl = fin_de_linea(texto)
        bloque = "\n" + ENCABEZADO + "\n" + "\n".join(textos) + "\n"
        nuevo = texto + ("" if texto.endswith("\n") or not texto else nl) + bloque.replace("\n", nl)
    return {"existe": True, "faltan": faltan, "omitidos": omitidos}, nuevo


# --- tokens.css ------------------------------------------------------------------------------------

def declaraciones(css, nodo):
    """(nombre, valor) de cada variable que declara el cuerpo de una regla, en orden."""
    cuerpo = re.sub(r"/\*.*?\*/", "", css[nodo["abre"] + 1:nodo["cierra"]], flags=re.S)
    pares = (d.partition(":") for d in cuerpo.split(";"))
    return [(n.strip(), " ".join(v.split())) for n, dos, v in pares if dos and n.strip().startswith("--")]


def bloque(nodos, selector):
    """El último bloque de primer nivel cuyo selector incluye `selector`, o None."""
    candidatos = [n for n in nodos if not es_regla_at(n) and normal(selector) in map(normal, separar(n["preludio"]))]
    return candidatos[-1] if candidatos else None


def insertar(texto, nodo, lineas, nl):
    """El texto con `lineas` dentro del bloque, en líneas nuevas después de su última declaración, con su sangría.
    Devuelve (posición, texto a insertar)."""
    m = enmascarar(texto)
    ultimo = m.rfind(";", nodo["abre"] + 1, nodo["cierra"])
    if ultimo == -1:
        pos, sangria = nodo["abre"] + 1, "  "
    else:
        inicio = m.rfind("\n", 0, ultimo) + 1
        sangria = re.match(r"[ \t]*", texto[inicio:]).group(0) or "  "
        fin = m.find("\n", ultimo, nodo["cierra"])
        pos = fin - (1 if fin > 0 and texto[fin - 1] == "\r" else 0) if fin != -1 else ultimo + 1
    return pos, "".join(nl + sangria + l for l in lineas)


def tokens(design, assets):
    asset = (assets / "tokens.css").read_text(encoding="utf-8")
    texto = leer(design / "tokens.css")
    nodos = arbol(texto, "tokens.css")
    definidos = set(re.findall(r"(--[\w-]+)\s*:", re.sub(r"/\*.*?\*/", "", texto, flags=re.S)))
    faltan, omitidos, por_bloque = [], [], []
    for nodo in arbol(asset, "assets/tokens.css"):
        if es_regla_at(nodo):
            continue
        nuevas = [(n, v) for n, v in declaraciones(asset, nodo) if n not in definidos]
        if not nuevas:
            continue
        selector = nodo["preludio"]
        destino = bloque(nodos, selector)
        if destino is None and normal(selector) != ":root":
            omitidos += [{"bloque": selector, "token": n, "motivo": f"el repositorio no tiene el bloque `{selector}` del tema oscuro: "
                          "agregarlo le daría al producto un tema que no tiene."} for n, _ in nuevas]
            continue
        faltan += [{"bloque": selector, "token": n, "valor": v} for n, v in nuevas]
        por_bloque.append((selector, destino, [f"{n}: {v};" for n, v in nuevas]))
    nl = fin_de_linea(texto)
    inserciones, al_final = [], ""
    for selector, destino, lineas in por_bloque:
        if destino is None:
            al_final += nl + selector + " {" + "".join(nl + "  " + l for l in lineas) + nl + "}" + nl
        else:
            inserciones.append(insertar(texto, destino, lineas, nl))
    nuevo = texto
    for pos, agregado in sorted(inserciones, reverse=True):
        nuevo = nuevo[:pos] + agregado + nuevo[pos:]
    if al_final:
        nuevo += ("" if nuevo.endswith("\n") or not nuevo else nl) + al_final
    return {"existe": True, "faltan": faltan, "omitidos": omitidos}, nuevo


# --- Comparar, mostrar, aplicar --------------------------------------------------------------------

def leer(ruta):
    with open(ruta, encoding="utf-8", newline="") as f:
        return f.read()


def escribir(ruta, texto):
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        f.write(texto)


def calcular(design, assets=ASSETS):
    """(JSON de comparar, {archivo: (texto actual o None, texto nuevo)} de lo que cambia)."""
    if not design.is_dir():
        raise Ilegible(f"No existe `{design}`: el repositorio de diseño todavía no tiene design/.")
    if not (design / "tokens.css").exists():
        raise Ilegible("No existe `design/tokens.css`: el design system se arma antes, en el paso 4 de spec-a-html.")
    salida, cambios = {}, {}
    salida["tokens"], nuevo = tokens(design, assets)
    if salida["tokens"]["faltan"]:
        cambios["tokens.css"] = (leer(design / "tokens.css"), nuevo)
    salida["components"], nuevo = components(design, assets)
    if salida["components"]["faltan"]:
        actual = design / "components.css"
        cambios["components.css"] = (leer(actual) if actual.exists() else None, nuevo)
    proto, original = design / "proto.js", assets / "proto.js"
    existe = proto.exists()
    salida["proto"] = {"existe": existe, "difiere": not existe or proto.read_bytes() != original.read_bytes()}
    if salida["proto"]["difiere"]:
        cambios["proto.js"] = (leer(proto) if existe else None, leer(original))
    salida["cambios"] = bool(cambios)
    return salida, cambios


def comparar(design, assets=ASSETS):
    return calcular(design, assets)[0]


def aplicar(design, assets=ASSETS):
    salida, cambios = calcular(design, assets)
    for archivo in cambios:
        if archivo == "proto.js":
            shutil.copyfile(assets / "proto.js", design / "proto.js")
        elif archivo == "components.css" and cambios[archivo][0] is None:
            shutil.copyfile(assets / "components.css", design / "components.css")
        else:
            escribir(design / archivo, cambios[archivo][1])
    return salida


def mostrar(design, assets=ASSETS):
    _, cambios = calcular(design, assets)
    partes = []
    for archivo, (antes, despues) in cambios.items():
        partes += difflib.unified_diff((antes or "").splitlines(), despues.splitlines(), f"a/design/{archivo}",
                                       f"b/design/{archivo}", lineterm="")
    return "\n".join(partes)


def main(argv=None):
    uso = argparse.ArgumentParser(prog="compartidos.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    uso.add_argument("comando", choices=("comparar", "mostrar", "aplicar"))
    uso.add_argument("repo")
    args = uso.parse_args(argv)
    design = Path(args.repo).resolve() / "design"
    try:
        if args.comando == "mostrar":
            print(mostrar(design) or "Sin cambios.")
        else:
            print(json.dumps((comparar if args.comando == "comparar" else aplicar)(design), ensure_ascii=False, indent=1))
    except Ilegible as e:
        print(e, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
