#!/usr/bin/env python3
"""Mapea los valores visuales de un mockup a los tokens de design/tokens.css, o los consolida si no hay tokens.

Uso:
  python3 tokens.py mapear <tokens.css> <fuente.css|.html> [...] [--json]
  python3 tokens.py consolidar <fuente.css|.html> [...] [--json]
  python3 tokens.py verificar <tokens-antes.css> <tokens-después.css> [--json]
  python3 tokens.py verificar <tokens.css> [--json]

mapear      cada color al token --color-* más cercano por distancia perceptual (OKLab), y cada medida al
            token más cercano de su escala (--space-*, --font-size-*, --radius-*, --size-*, según la propiedad).
            Lo que queda fuera del umbral va a una tabla aparte, para que producto elija.
consolidar  sin tokens.css: agrupa colores por su color base dentro del umbral y dentro de su tema, con cada
            opacidad anotada en sus miembros; lista como un token con un valor por tema cada rol (una variable, o
            un selector y su propiedad) que cambia de valor entre temas; lleva espacios, radios y medidas fijas a
            múltiplos de 4 px y junta tamaños de letra a 1 px o menos.
verificar   con dos archivos, lista los tokens nuevos que quedan dentro del umbral de uno existente; con uno,
            los pares de tokens del mismo tema con valores distintos dentro del umbral, que se ven iguales.
            Sale con 1 si hay alguno.

Cada valor lleva su tema: la marca del selector que lo elige ([data-theme="dark"], .dark, .theme-x), el
@media (prefers-color-scheme: ...) que lo envuelve, los dos si el selector vale para dos temas
(:root, [data-theme="dark"]), o :root, el tema por defecto, si nada lo elige. Al mapear, cada valor se compara
con los tokens de su tema: los de un tema oscuro con los de [data-theme="dark"], los demás con los de :root. Un radio de 100 px o más es una píldora y va al
radio mayor. Umbral de color: distancia OKLab por 100, más la diferencia de opacidad por 100, de 2,0 o menos, que es
del orden de la diferencia mínima perceptible. Umbral de medida: 1 px o el 10 % del paso, lo que sea mayor.
Sale con 2 si el uso es incorrecto.
"""
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from desarmar import declaraciones, es_bloque_de_variables, reglas  # noqa: E402

UMBRAL_COLOR = 2.0
UMBRAL_MEDIDA = {"px": 1.0, "relativo": 0.10}
NOMBRES = {"black": "#000000", "white": "#ffffff", "red": "#ff0000", "green": "#008000", "blue": "#0000ff",
           "gray": "#808080", "grey": "#808080", "orange": "#ffa500", "yellow": "#ffff00", "purple": "#800080",
           "pink": "#ffc0cb", "brown": "#a52a2a"}
COLOR = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?)\([^)]*\)|(?<![\w-])(?:" + "|".join(NOMBRES) + r")(?![\w-])", re.I)
MEDIDA = re.compile(r"(?<![\w.#-])(\d+(?:\.\d+)?)(px|rem|em|pt)\b")
PILDORA = 100
EN_LINEA = "style en línea"
PREFIJO = {"space": "--space-", "font-size": "--font-size-", "radius": "--radius-", "size": "--size-"}
TEMA_ATRIBUTO = re.compile(r"""\[data-(theme|tema|mode|modo|color-scheme)\s*=\s*["']?([\w-]+)["']?\s*\]""", re.I)
TEMA_CLASE = re.compile(r"\.(dark|light|oscuro|claro|(?:theme|tema)-[\w-]+|(?:dark|light)-mode|modo-(?:oscuro|claro))(?![\w-])")


# --- Colores -----------------------------------------------------------------------------------

def leer_color(s):
    s = s.strip().lower()
    s = NOMBRES.get(s, s)
    if s.startswith("#"):
        h = s[1:]
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        if len(h) not in (6, 8):
            return None
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
        return r, g, b, int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
    m = re.match(r"(rgba?|hsla?)\((.*)\)$", s)
    if not m:
        return None
    partes = [p for p in re.split(r"[\s,/]+", m.group(2).strip()) if p]
    if len(partes) < 3:
        return None

    def num(p, escala):
        return float(p[:-1]) / 100 if p.endswith("%") else float(p) / escala

    try:
        alfa = num(partes[3], 1) if len(partes) > 3 else 1.0
        if m.group(1).startswith("rgb"):
            r, g, b = (num(p, 255) for p in partes[:3])
        else:
            h = float(partes[0].replace("deg", "")) % 360 / 360
            sat, luz = num(partes[1], 100), num(partes[2], 100)
            r, g, b = hsl_a_rgb(h, sat, luz)
    except ValueError:
        return None
    return r, g, b, alfa


def hsl_a_rgb(h, s, l):
    if s == 0:
        return l, l, l
    q = l * (1 + s) if l < 0.5 else l + s - l * s
    p = 2 * l - q

    def canal(t):
        t %= 1
        if t < 1 / 6:
            return p + (q - p) * 6 * t
        if t < 1 / 2:
            return q
        if t < 2 / 3:
            return p + (q - p) * (2 / 3 - t) * 6
        return p

    return canal(h + 1 / 3), canal(h), canal(h - 1 / 3)


def oklab(r, g, b):
    def lineal(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = lineal(r), lineal(g), lineal(b)
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def distancia_color(a, b):
    la, lb = oklab(*a[:3]), oklab(*b[:3])
    return round(math.dist(la, lb) * 100 + abs(a[3] - b[3]) * 100, 2)


# --- Medidas -----------------------------------------------------------------------------------

def leer_medida(s):
    m = MEDIDA.fullmatch(s.strip())
    if not m:
        return None
    n, u = float(m.group(1)), m.group(2)
    return n * {"px": 1, "rem": 16, "em": 16, "pt": 4 / 3}[u]


def categoria_de_propiedad(prop):
    if prop == "font-size":
        return "font-size"
    if "radius" in prop:
        return "radius"
    if re.match(r"(padding|margin|gap|row-gap|column-gap|inset|top|right|bottom|left)\b", prop):
        return "space"
    if re.match(r"(min-|max-)?(width|height)$|flex-basis$", prop):
        return "size"
    return None


def categoria_de_variable(nombre):
    n = nombre.lower()
    if "radius" in n or re.match(r"--r\d|--r-|--radio", n):
        return "radius"
    if "font" in n or re.match(r"--(fs|text)-", n):
        return "font-size"
    if re.search(r"space|gap|pad|margin|--sp-|--s\d", n):
        return "space"
    if re.search(r"width|height|size|--w-|--h-", n):
        return "size"
    return None


def fmt(px):
    return f"{int(px)}px" if float(px).is_integer() else f"{px:g}px"


# --- Lectura -----------------------------------------------------------------------------------

def css_de(path):
    texto = Path(path).read_text(errors="replace")
    if path.suffix.lower() in (".html", ".htm"):
        estilos = re.findall(r"<style\b[^>]*>(.*?)</style\s*>", texto, flags=re.S | re.I)
        inline = re.findall(r"""\bstyle\s*=\s*(?:"([^"]*)"|'([^']*)')""", texto, flags=re.I)
        return "\n".join(estilos + [f"{EN_LINEA}{{{a or b}}}" for a, b in inline])
    return texto


def es_oscuro(contexto, selector):
    texto = " ".join([*contexto, selector]).lower()
    return "dark" in texto or "oscuro" in texto


def marcas_de_tema(sub):
    """Lo que en un selector simple elige un tema: [data-theme="dark"], .dark, .theme-x, normalizado."""
    marcas = [f'[data-{a.lower()}="{v}"]' for a, v in TEMA_ATRIBUTO.findall(sub)]
    return marcas + [f".{c}" for c in TEMA_CLASE.findall(sub)]


def tema_de(contexto, selector):
    """El tema de una regla: :root si nada lo elige, la marca del selector ([data-theme="dark"], .dark) o el
    @media (prefers-color-scheme: ...) que la envuelve. Un selector que vale para dos temas lleva los dos."""
    media = next((re.sub(r"\s+", " ", c.strip()) for c in contexto if "prefers-color-scheme" in c), None)
    media = media and re.sub(r"\(\s*prefers-color-scheme\s*:\s*(\w+)\s*\)", r"(prefers-color-scheme: \1)", media)
    temas = []
    for sub in selector.split(","):
        t = " ".join(marcas_de_tema(sub)) or ":root"
        temas.append(t if not media else media if t == ":root" else f"{media} {t}")
    return ", ".join(dict.fromkeys(temas))


def sin_tema(selector):
    """El selector sin lo que elige el tema ni la raíz: [data-theme="dark"] .card es .card, :root queda vacío."""
    bases = []
    for sub in selector.split(","):
        limpio = TEMA_CLASE.sub("", TEMA_ATRIBUTO.sub("", sub)).split()
        while limpio and limpio[0] in ("html", "body", ":root"):
            limpio.pop(0)
        bases.append(" ".join(limpio))
    return ", ".join(b for b in dict.fromkeys(bases) if b)


def ocurrencias(fuentes):
    """Valores (normalizados) con su tipo, categoría, cuántas veces aparecen, en qué propiedades y en qué selectores."""
    out = {}

    def sumar(valor, tipo, categoria, prop, tema, selector, rol):
        clave = (valor, categoria, tema)
        o = out.setdefault(clave, {"valor": valor, "tipo": tipo, "categoria": categoria, "tema": tema, "ocurrencias": 0,
                                   "usos": [], "selectores": [], "roles": []})
        o["ocurrencias"] += 1
        for lista, x in ((o["usos"], prop), (o["selectores"], selector), (o["roles"], rol)):
            if x not in lista:
                lista.append(x)

    for f in fuentes:
        for contexto, selector, cuerpo in reglas(css_de(Path(f))):
            if any(c.lstrip("@").startswith(("keyframes", "-webkit-keyframes")) for c in contexto):
                continue
            variables = es_bloque_de_variables(contexto, selector)
            tema, base = tema_de(contexto, selector), sin_tema(selector)
            for prop, valor in declaraciones(cuerpo):
                if prop.startswith("--") and not variables:
                    continue
                rol = prop if prop.startswith("--") or not base else f"{base} {prop}"
                for c in COLOR.findall(valor):
                    if leer_color(c):
                        sumar(c.lower().replace(" ", ""), "color", "color", prop, tema, selector, rol)
                cat = categoria_de_variable(prop) if prop.startswith("--") else categoria_de_propiedad(prop)
                if cat:
                    for m in MEDIDA.finditer(valor):
                        px = leer_medida(m.group(0))
                        if px is not None and px > 2:
                            sumar(m.group(0).lower(), "medida", cat, prop, tema, selector, rol)
    return sorted(out.values(), key=lambda o: -o["ocurrencias"])


def temas_en_orden(fuentes):
    """Los temas de las reglas con algún color, en el orden en que aparecen en las fuentes."""
    temas = []
    for f in fuentes:
        for contexto, selector, cuerpo in reglas(css_de(Path(f))):
            if not any(c.lstrip("@").startswith(("keyframes", "-webkit-keyframes")) for c in contexto) \
                    and any(leer_color(c) for _, v in declaraciones(cuerpo) for c in COLOR.findall(v)):
                tema = tema_de(contexto, selector)
                if tema not in temas:
                    temas.append(tema)
    return temas


def tokens_de(path):
    """{nombre: (valor, bloque)} de cada token, sin repetir: el de :root manda sobre los temas."""
    out = {}
    for contexto, selector, cuerpo in reglas(Path(path).read_text(errors="replace")):
        if not es_bloque_de_variables(contexto, selector):
            continue
        bloque = " ".join([*contexto, selector])
        for prop, valor in declaraciones(cuerpo):
            if prop.startswith("--"):
                out.setdefault((prop, bloque), valor)
    return out


def mas_cercano(o, toks):
    mismo_tema = {k: v for k, v in toks.items() if es_oscuro([], k[1]) == es_oscuro([], o.get("tema") or "")}
    toks = mismo_tema or toks
    if o["tipo"] == "color":
        c = leer_color(o["valor"])
        cands = [(distancia_color(c, leer_color(v)), n, v, b) for (n, b), v in toks.items()
                 if n.startswith("--color-") and leer_color(v)]
        if not cands:
            return None
        d, n, v, b = min(cands, key=lambda x: x[0])
        return {"token": n, "valor_token": v, "bloque": b, "distancia": d, "dentro": d <= UMBRAL_COLOR}
    px = leer_medida(o["valor"])
    if o["categoria"] == "radius" and px >= PILDORA:
        px = max([leer_medida(v) for (n, _), v in toks.items() if n.startswith("--radius-") and leer_medida(v)] + [px])
    cands = [(abs(px - leer_medida(v)), n, v, b) for (n, b), v in toks.items()
             if n.startswith(PREFIJO[o["categoria"]]) and leer_medida(v) is not None]
    if not cands:
        return None
    d, n, v, b = min(cands, key=lambda x: x[0])
    tope = max(UMBRAL_MEDIDA["px"], UMBRAL_MEDIDA["relativo"] * leer_medida(v))
    return {"token": n, "valor_token": v, "bloque": b, "distancia": round(d, 2), "dentro": d <= tope}


# --- Comandos ----------------------------------------------------------------------------------

def mapear(tokens_css, fuentes):
    toks = tokens_de(tokens_css)
    filas = []
    for o in ocurrencias(fuentes):
        c = mas_cercano(o, toks)
        filas.append({**o, **(c or {"token": None, "valor_token": None, "bloque": None, "distancia": None, "dentro": False})})
    return {"umbral": {"color": UMBRAL_COLOR, "medida": UMBRAL_MEDIDA}, "valores": filas}


def consolidar(fuentes):
    ocs = ocurrencias(fuentes)
    grupos, temas, por_rol = [], temas_en_orden(fuentes), {}
    for o in [x for x in ocs if x["tipo"] == "color"]:
        for rol in o["roles"]:
            valores = por_rol.setdefault(rol, {}).setdefault(o["tema"], [])
            if o["valor"] not in valores:
                valores.append(o["valor"])
        c = leer_color(o["valor"])
        base = c[:3] + (1.0,)
        g = next((g for g in grupos if g["tema"] == o["tema"]
                  and distancia_color(base, leer_color(g["representante"])[:3] + (1.0,)) <= UMBRAL_COLOR), None)
        if g is None:
            g = {"tema": o["tema"], "representante": o["valor"], "miembros": [], "ocurrencias": 0, "usos": []}
            grupos.append(g)
        g["miembros"].append({"valor": o["valor"], "ocurrencias": o["ocurrencias"], "opacidad": round(c[3], 3)})
        g["ocurrencias"] += o["ocurrencias"]
        g["usos"] += [u for u in o["usos"] if u not in g["usos"]]
    medidas = {}
    letras = []
    for o in [x for x in ocs if x["tipo"] == "medida"]:
        px = leer_medida(o["valor"])
        if o["categoria"] == "font-size":
            g = next((g for g in letras if abs(leer_medida(g["propuesta"]) - px) <= 1), None)
            if g is None:
                g = {"categoria": "font-size", "propuesta": fmt(px), "miembros": [], "ocurrencias": 0}
                letras.append(g)
        else:
            propuesta = "9999px" if o["categoria"] == "radius" and px >= PILDORA else fmt(max(4, math.floor(px / 4 + 0.5) * 4))
            g = medidas.setdefault((o["categoria"], propuesta), {"categoria": o["categoria"], "propuesta": propuesta,
                                                                  "miembros": [], "ocurrencias": 0})
        g["miembros"].append({"valor": o["valor"], "ocurrencias": o["ocurrencias"]})
        g["ocurrencias"] += o["ocurrencias"]
    orden = sorted(medidas.values(), key=lambda g: (g["categoria"], leer_medida(g["propuesta"]))) + letras
    orden_temas = {t: i for i, t in enumerate(temas)}
    por_tema = [{"rol": rol, "valores": dict(sorted(v.items(), key=lambda x: orden_temas[x[0]]))}
                for rol, v in por_rol.items() if len(v) > 1]
    return {"umbral": {"color": UMBRAL_COLOR, "medida": UMBRAL_MEDIDA}, "temas": temas,
            "colores": sorted(grupos, key=lambda g: -g["ocurrencias"]), "por_tema": por_tema, "medidas": orden}


def casi_iguales_entre_si(path):
    """Pares de tokens del mismo bloque con valores distintos que quedan dentro del umbral: se ven iguales."""
    casi, toks = [], list(tokens_de(path).items())
    for i, ((n1, b1), v1) in enumerate(toks):
        for (n2, b2), v2 in toks[i + 1:]:
            if b1 != b2 or v1.lower().replace(" ", "") == v2.lower().replace(" ", ""):
                continue
            if n1.startswith("--color-") and n2.startswith("--color-") and leer_color(v1) and leer_color(v2):
                d = distancia_color(leer_color(v1), leer_color(v2))
                dentro = d <= UMBRAL_COLOR
            else:
                cat = next((p for p in PREFIJO.values() if n1.startswith(p)), None)
                if not cat or not n2.startswith(cat) or leer_medida(v1) is None or leer_medida(v2) is None:
                    continue
                d = abs(leer_medida(v1) - leer_medida(v2))
                dentro = d == 0
            if dentro:
                casi.append({"token": n1, "valor": v1, "existente": n2, "valor_existente": v2, "distancia": round(d, 2), "bloque": b1})
    return casi


def verificar(antes, despues=None):
    if despues is None:
        return {"umbral": {"color": UMBRAL_COLOR}, "entre_si": True, "casi_iguales": casi_iguales_entre_si(antes)}
    viejos, nuevos = tokens_de(antes), tokens_de(despues)
    nombres_viejos = {n for n, _ in viejos}
    casi = []
    for (n, b), v in nuevos.items():
        if n in nombres_viejos:
            continue
        o = {"valor": v, "tipo": "color" if n.startswith("--color-") else "medida",
             "categoria": next((k for k, p in PREFIJO.items() if n.startswith(p)), None)}
        if o["tipo"] == "color" and not leer_color(v) or o["tipo"] == "medida" and (not o["categoria"] or leer_medida(v) is None):
            continue
        c = mas_cercano(o, viejos)
        if c and (c["dentro"] if o["tipo"] == "color" else c["distancia"] == 0):
            casi.append({"token": n, "valor": v, "existente": c["token"], "valor_existente": c["valor_token"], "distancia": c["distancia"]})
    return {"umbral": {"color": UMBRAL_COLOR}, "casi_iguales": casi}


def token_con_valor(f):
    """El token, con su valor cuando no es igual al del mockup: así se ve cuánto cambia la pantalla."""
    return f"{f['token']} ({f['valor_token']})" if f["distancia"] else f["token"]


def md_mapear(d):
    l = ["# Valores del mockup contra tokens.css", "",
         f"Umbral: color {UMBRAL_COLOR} (OKLab por 100, más opacidad); medida 1 px o 10 % del paso.", "",
         "## Dentro del umbral", "", "| Valor | Categoría | Ocurrencias | Token | Distancia |", "| :--- | :--- | :--- | :--- | :--- |"]
    l += [f"| {f['valor']} | {f['categoria']} | {f['ocurrencias']} | {token_con_valor(f)} | {f['distancia']} |"
          for f in d["valores"] if f["dentro"]]
    l += ["", "## Fuera del umbral, a decidir por producto", "",
          "| Valor | Categoría | Ocurrencias | Token más cercano | Distancia | Usos | Selectores |",
          "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"]
    l += [f"| {f['valor']} | {f['categoria']} | {f['ocurrencias']} | {f['token'] or 'sin escala'} ({f['valor_token']}) | {f['distancia']} | "
          f"{', '.join(f['usos'][:4])} | {', '.join(f['selectores'][:4])} |" for f in d["valores"] if not f["dentro"]]
    return "\n".join(l) + "\n"


def miembros(g):
    return ", ".join(f"{m['valor']} ({m['ocurrencias']})" for m in g["miembros"])


def md_consolidar(d):
    l = ["# Consolidación de valores del mockup", "", "## Colores", "",
         "Agrupados por color base dentro de cada tema: el mismo valor en dos temas va en dos grupos.", "",
         "| Tema | Representante | Ocurrencias | Miembros | Usos |", "| :--- | :--- | :--- | :--- | :--- |"]
    l += [f"| {g['tema']} | {g['representante']} | {g['ocurrencias']} | {miembros(g)} | "
          f"{', '.join(g['usos'][:4])} |" for g in d["colores"]]
    if d["por_tema"]:
        columnas = [t for t in d["temas"] if any(t in x["valores"] for x in d["por_tema"])]
        l += ["", "## Un token con un valor por tema", "",
              "Cada fila es un rol del mockup (una variable, o un selector y su propiedad) con otro valor en cada tema: "
              "un solo token, con su valor en cada bloque de tema.", "",
              "| Rol | " + " | ".join(columnas) + " |", "| :--- |" + " :--- |" * len(columnas)]
        l += [f"| {x['rol']} | " + " | ".join(", ".join(x["valores"].get(t, [])) for t in columnas) + " |" for x in d["por_tema"]]
    l += ["", "## Medidas", "", "| Categoría | Propuesta | Ocurrencias | Valores originales |", "| :--- | :--- | :--- | :--- |"]
    l += [f"| {g['categoria']} | {g['propuesta']} | {g['ocurrencias']} | {miembros(g)} |"
          for g in d["medidas"]]
    return "\n".join(l) + "\n"


def md_verificar(d):
    if d.get("entre_si"):
        if not d["casi_iguales"]:
            return "Ningún par de tokens del mismo tema queda dentro del umbral.\n"
        return "Tokens del mismo tema casi iguales entre sí (se ven iguales; deja uno o sepáralos):\n" + "".join(
            f"- {c['token']} ({c['valor']}) y {c['existente']} ({c['valor_existente']}) en {c['bloque']}, distancia {c['distancia']}\n"
            for c in d["casi_iguales"])
    if not d["casi_iguales"]:
        return "Ningún token nuevo queda dentro del umbral de uno existente.\n"
    return "Tokens nuevos casi iguales a uno existente:\n" + "".join(
        f"- {c['token']} ({c['valor']}) contra {c['existente']} ({c['valor_existente']}), distancia {c['distancia']}\n" for c in d["casi_iguales"])


def main(argv):
    como_json = "--json" in argv
    args = [a for a in argv[1:] if a != "--json"]
    minimo = {"mapear": 3, "consolidar": 2, "verificar": 3}
    minimo["verificar"] = 2
    if not args or args[0] not in minimo or len(args) < minimo[args[0]] or (args[0] == "verificar" and len(args) > 3):
        print(__doc__, file=sys.stderr)
        return 2
    faltan = [a for a in args[1:] if not Path(a).is_file()]
    if faltan:
        print(f"No existe: {', '.join(faltan)}", file=sys.stderr)
        return 2
    rutas = [Path(a) for a in args[1:]]
    if args[0] == "mapear":
        d, md = mapear(rutas[0], rutas[1:]), md_mapear
    elif args[0] == "consolidar":
        d, md = consolidar(rutas), md_consolidar
    else:
        d, md = verificar(*rutas), md_verificar
    print(json.dumps(d, ensure_ascii=False, indent=1) if como_json else md(d))
    return 1 if args[0] == "verificar" and d["casi_iguales"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
