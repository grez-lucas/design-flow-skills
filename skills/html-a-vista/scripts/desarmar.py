#!/usr/bin/env python3
"""Desarma un mockup HTML en partes y trozos, y escribe un manifiesto para repartir la conversión.

Uso: python3 desarmar.py <mockup.html | carpeta-de-galería> <carpeta-de-trabajo> [--tope TOKENS]

Escribe en la carpeta de trabajo:
  partes/<parte>.html          el shell y cada módulo embebido, decodificados y abribles solos
  trozos/<parte>/estilos.css   el CSS de la parte
  trozos/<parte>/script.js     el JS de la parte
  trozos/<parte>/markup/*.html el markup por pantalla, panel o superposición con id, y el resto
  trozos/iconos.html           los SVG repetidos, una vez cada uno
  resumen.md                   lo que hace falta para el plan, en una lectura
  manifiesto.json              partes, trozos con bytes y tokens, variables, valores, externos,
                               data-state, controles de prototipo y origen de cada parte

Un trozo que pasa el tope (en tokens estimados) se parte antes de escribirse. Sale con 1 y un
mensaje, sin escribir nada, si no puede desarmar la entrada; con 2 si el uso es incorrecto.
"""
import hashlib
import html
import json
import math
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

TOPE = 15000
METODO = "bytes/4"
MARGEN = ("Estimación sin tokenizador. En un mockup real de 1,7 MB dio un 14 % menos que o200k_base, "
          "y los tokenizadores de Claude cuentan hasta 1,35 veces más que o200k_base para el mismo texto: "
          "el tope por defecto deja ese margen bajo los 25.000 tokens de una lectura.")
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
CONTENEDORES = {"div", "section", "main", "article", "aside", "dialog", "form", "template"}
PANTALLA = re.compile(r"(^|-)(page|pagina|screen|pantalla|view|vista|panel|tab|step|paso|route|ruta)s?(-|$|\d)")
SUPERPOSICION = re.compile(r"(^|-)(modal|dialog|dialogo|drawer|overlay|popover|pop|sheet)s?(-|$|\d)")
DEMO = re.compile(r"\bdemo\b|\bsimul\w*|salir de (la )?(demo|simulaci)|modo (prueba|demo)|\bprototipo\b", re.I)
PALABRAS_PROTO = {"demo", "sim", "simular", "simulate", "simulation", "simulacion", "mode", "modo", "modes", "modos",
                  "fake", "mock", "escenario", "escenarios", "scenario", "scenarios"}
TIPOS_MODULO = {"text/plain", "text/html", "text/template", "text/x-template"}
COLOR = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?)\([^)]*\)")
NOMBRADO = re.compile(r"(?<![\w-])(red|blue|green|black|white|gray|grey|orange|yellow|purple|pink|brown)(?![\w-])", re.I)
MEDIDA = re.compile(r"(?<![\w.#-])-?(\d+(?:\.\d+)?)(px|rem|em|pt)\b")
MEDIDA_OK = {("0", "px"), ("1", "px"), ("2", "px"), ("0", "rem"), ("0", "em")}
CDN = re.compile(r"(^|\.)(unpkg\.com|jsdelivr\.net|cdnjs\.cloudflare\.com|cdn\.tailwindcss\.com|esm\.sh|skypack\.dev|"
                 r"googleapis\.com|gstatic\.com|bootstrapcdn\.com|jquery\.com|cdn\.\w[\w.-]*)$", re.I)
FRAMEWORKS = [("react", re.compile(r"\breact(-dom)?([@./-]|$)", re.I)), ("vue", re.compile(r"\bvue([@./-]|$)", re.I)),
              ("babel", re.compile(r"babel", re.I)), ("tailwind", re.compile(r"tailwind", re.I)),
              ("preact", re.compile(r"\bpreact\b", re.I)), ("alpine", re.compile(r"alpinejs", re.I))]
URL_CSS = re.compile(r"""url\(\s*["']?((?:https?:)?//[^"')\s]+)|@import\s+(?:url\(\s*)?["']((?:https?:)?//[^"']+)""", re.I)
URL_JS = re.compile(r"""\bfrom\s+["'](https?://[^"']+)|\bimport\(\s*["'](https?://[^"']+)""")


class Fallo(Exception):
    pass


def tokens(texto):
    return math.ceil(len(texto.encode()) / 4)


def linea(texto, offset):
    return texto.count("\n", 0, offset) + 1


def n_lineas(texto):
    return len(texto.splitlines()) or 1


def kebab(s):
    return re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", s).replace("_", "-").lower()


def nombre_archivo(s):
    return re.sub(r"[^\w.-]+", "-", s).strip("-") or "sin-id"


# --- CSS ---------------------------------------------------------------------------------------

def sin_comentarios_css(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def reglas(css):
    """(contexto, selector, cuerpo) de cada regla con declaraciones; el contexto son las at-rules que la envuelven."""
    out, pila, buf = [], [], []
    for ch in sin_comentarios_css(css):
        if ch == "{":
            pila.append("".join(buf).strip())
            buf = []
        elif ch == "}":
            if pila:
                prel = pila.pop()
                cuerpo = "".join(buf)
                if not prel.startswith("@") and cuerpo.strip():
                    out.append(([p for p in pila if p.startswith("@")], " ".join(prel.split()), cuerpo))
            buf = []
        else:
            buf.append(ch)
    return out


def declaraciones(cuerpo):
    for d in cuerpo.split(";"):
        prop, sep, valor = d.partition(":")
        if sep and prop.strip():
            yield prop.strip().lower() if not prop.strip().startswith("--") else prop.strip(), valor.strip()


def es_bloque_de_variables(contexto, selector):
    if ":root" in selector or "data-theme" in selector or re.search(r"\.(dark|light)\b|\.theme-", selector):
        return True
    return any("prefers-color-scheme" in c for c in contexto) and re.search(r"\b(html|body)\b", selector) is not None


def variables(css):
    bloques = {}
    for contexto, selector, cuerpo in reglas(css):
        if not es_bloque_de_variables(contexto, selector):
            continue
        defs = {p: v for p, v in declaraciones(cuerpo) if p.startswith("--")}
        if defs:
            clave = " ".join([*(c for c in contexto), selector]).strip()
            bloques.setdefault(clave, {}).update(defs)
    return bloques


def css_sin_variables(css):
    partes = []
    for contexto, selector, cuerpo in reglas(css):
        if es_bloque_de_variables(contexto, selector):
            cuerpo = ";".join(f"{p}: {v}" for p, v in declaraciones(cuerpo) if not p.startswith("--"))
        partes.append(cuerpo)
    return "\n".join(partes)


def valores_sueltos(texto):
    colores = [c.lower().replace(" ", "") for c in COLOR.findall(texto)] + [c.lower() for c in NOMBRADO.findall(texto)]
    medidas = [m.group(0) for m in MEDIDA.finditer(texto) if (m.group(1), m.group(2)) not in MEDIDA_OK]
    return colores + medidas


def sin_comentarios_js(js):
    return re.sub(r"(?m)^\s*//.*$", "", re.sub(r"/\*.*?\*/", "", js, flags=re.S))


def literales_js(js):
    """Strings de JS: comillas simples o dobles en una línea, backticks en varias."""
    patron = r"""'((?:\\.|[^'\\\n])*)'|"((?:\\.|[^"\\\n])*)"|`((?:\\.|[^`\\])*)`"""
    return [a or b or c for a, b, c in re.findall(patron, sin_comentarios_js(js))]


# --- HTML --------------------------------------------------------------------------------------

class Lector(HTMLParser):
    """Recorre una parte y anota elementos con su posición, estilos, scripts y textos de control."""

    def __init__(self, texto):
        super().__init__(convert_charrefs=True)
        self.texto = texto
        self.inicios = [0]
        for l in texto.split("\n"):
            self.inicios.append(self.inicios[-1] + len(l) + 1)
        self.elementos = []
        self.pila = []
        self.estilos, self.scripts, self.inline = [], [], []
        self.data_state, self.recursos, self.textos_demo = [], [], []
        self.excluidos = []
        self.body = self.head = None
        self.actual = None

    def pos(self):
        l, c = self.getpos()
        return self.inicios[l - 1] + c

    def handle_starttag(self, tag, attrs):
        inicio = self.pos()
        fin_apertura = inicio + len(self.get_starttag_text() or "")
        a = {k: (v or "") for k, v in attrs}
        if tag in ("script", "style"):
            self.actual = {"tag": tag, "attrs": a, "inicio": inicio, "datos": []}
        if "style" in a:
            self.inline.append(a["style"])
        if "data-state" in a:
            self.data_state.append({"valor": a["data-state"], "linea": linea(self.texto, inicio)})
        if tag == "link" and a.get("href"):
            self.recursos.append(a["href"])
        for k in ("src", "poster", "data"):
            if a.get(k) and tag != "a":
                self.recursos.append(a[k])
        if a.get("srcset"):
            self.recursos += [s.split()[0] for s in a["srcset"].split(",") if s.strip()]
        if tag == "body":
            self.body = [fin_apertura, None]
        if tag == "head":
            self.head = [inicio, None]
        if tag in VOID or (self.get_starttag_text() or "").rstrip().endswith("/>"):
            return
        e = {"tag": tag, "attrs": a, "inicio": inicio, "fin": None, "padre": self.pila[-1] if self.pila else None,
             "texto": []}
        self.elementos.append(e)
        self.pila.append(len(self.elementos) - 1)

    def handle_endtag(self, tag):
        inicio = self.pos()
        fin = self.texto.find(">", inicio) + 1 or len(self.texto)
        if tag in ("script", "style") and self.actual and self.actual["tag"] == tag:
            datos = "".join(self.actual["datos"])
            (self.estilos if tag == "style" else self.scripts).append(
                datos if tag == "style" else {"attrs": self.actual["attrs"], "texto": datos})
            self.excluidos.append((self.actual["inicio"], fin))
            self.actual = None
        if tag == "body" and self.body:
            self.body[1] = inicio
        if tag == "head" and self.head:
            self.head[1] = fin
        if tag in VOID or not any(self.elementos[i]["tag"] == tag for i in self.pila):
            return
        while self.pila:
            e = self.elementos[self.pila.pop()]
            e["fin"] = fin if e["tag"] == tag else inicio
            if e["tag"] == tag:
                break

    def handle_data(self, data):
        if self.actual:
            self.actual["datos"].append(data)
            return
        if data.strip() and DEMO.search(data):
            control = next((self.elementos[i] for i in reversed(self.pila)
                            if self.elementos[i]["tag"] in ("button", "a", "option", "summary", "label", "select")
                            or "onclick" in self.elementos[i]["attrs"]), None)
            self.textos_demo.append({"texto": " ".join(data.split()), "linea": linea(self.texto, self.pos()),
                                     "etiqueta": control["tag"] if control else None,
                                     "onclick": control["attrs"].get("onclick") if control else None})

    def close(self):
        super().close()
        for i in self.pila:
            self.elementos[i]["fin"] = len(self.texto)
        if self.head and self.head[1] is None:
            self.head[1] = len(self.texto)


def clase_de(e):
    a = e["attrs"]
    if e["tag"] not in CONTENEDORES:
        return None
    ident = a.get("id") or a.get("data-screen") or a.get("data-view") or a.get("data-page") or a.get("data-tab")
    if not ident:
        return None
    nombres = [kebab(ident)] + [kebab(c) for c in a.get("class", "").split()]
    if e["tag"] == "dialog" or a.get("role") in ("dialog", "alertdialog") or any(SUPERPOSICION.search(n) for n in nombres):
        return "superposicion"
    if a.get("role") == "tabpanel" or any(a.get(k) for k in ("data-screen", "data-view", "data-page", "data-tab")) \
            or any(PANTALLA.search(n) for n in nombres):
        return "pantalla"
    return None


def ident(e):
    a = e["attrs"]
    return a.get("id") or a.get("data-screen") or a.get("data-view") or a.get("data-page") or a.get("data-tab")


# --- Módulos -----------------------------------------------------------------------------------

def spans_de_script(texto):
    return [(m.start(), m.end(), m.group(1), m.start(2), m.end(2))
            for m in re.finditer(r"<script\b([^>]*)>(.*?)</script\s*>", texto, flags=re.S | re.I)]


def atributo(attrs, nombre):
    m = re.search(rf"""\b{nombre}\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""", attrs, flags=re.I)
    return None if not m else next(g for g in m.groups() if g is not None)


def parece_documento(s):
    return re.search(r"<!doctype|<html\b|<body\b", s, flags=re.I) is not None


def scripts_consistentes(s):
    """True si cada <script> cierra y no hay </script> suelto, leyendo el contenido de cada script como texto, igual que el navegador."""
    pos = 0
    while True:
        m = re.compile(r"<script\b[^>]*>|</script\s*>", re.I).search(s, pos)
        if not m:
            return True
        if m.group(0).startswith("</"):
            return False
        cierre = re.compile(r"</script\s*>", re.I).search(s, m.end())
        if not cierre:
            return False
        pos = cierre.end()


def decodificar(s, nombre):
    """Restituye el </script> que el módulo escapa para vivir dentro de otro <script>.

    Prueba cada escape encontrado (<#/script, <\\/script...) y se queda con el que deja los scripts consistentes.
    Si más de uno sirve, descarta <\\/, que también aparece legítimo dentro de strings de JS.
    """
    candidatos = [(f"<{e} -> <", s.replace("<" + e, "<"))
                  for e in sorted(set(re.findall(r"<([^\s\w<>/!])/script", s, flags=re.I)), key=lambda e: e == "\\")]
    if "&lt;" in s and not re.search(r"<(html|head|body|div|section)\b", s, flags=re.I):
        candidatos.append(("entidades HTML", html.unescape(s)))
    candidatos.append((None, s))
    for metodo, decodificado in candidatos:
        if scripts_consistentes(decodificado):
            return decodificado, metodo
    raise Fallo(f"el módulo {nombre} tiene <script> sin cierre o </script> sueltos con cualquier decodificación que probé; "
                "no reconozco cómo escapa </script>")


def modulos(texto):
    """Lista de (id, via, inicio, fin, contenido, decodificación) de los módulos embebidos, en orden."""
    out = []
    scripts = spans_de_script(texto)
    for m in re.finditer(r"<script\b([^>]*)>", texto, flags=re.I):
        tipo = (atributo(m.group(1), "type") or "").lower()
        if tipo in TIPOS_MODULO and not any(a <= m.start() < b for a, b, *_ in scripts):
            nombre = atributo(m.group(1), "id") or f"modulo-{len(out) + 1}"
            raise Fallo(f"el módulo {nombre} (<script type=\"{tipo}\">) no tiene cierre </script>")
    for inicio, fin, attrs, ci, cf in scripts:
        tipo = (atributo(attrs, "type") or "").lower()
        if tipo not in TIPOS_MODULO:
            continue
        nombre = atributo(attrs, "id") or f"modulo-{len(out) + 1}"
        contenido, metodo = decodificar(texto[ci:cf], nombre)
        if parece_documento(contenido):
            out.append((nombre, "script text/plain" if tipo == "text/plain" else f"script {tipo}", ci, cf, contenido, metodo))
    for m in re.finditer(r"""<iframe\b[^>]*?\bsrcdoc\s*=\s*("([^"]*)"|'([^']*)')""", texto, flags=re.I | re.S):
        if any(a <= m.start() < b for a, b, *_ in scripts):
            continue
        grupo = 2 if m.group(2) is not None else 3
        etiqueta = texto[m.start():m.end()]
        nombre = atributo(etiqueta, "id") or atributo(etiqueta, "title") or f"srcdoc-{len(out) + 1}"
        out.append((nombre, "iframe srcdoc", m.start(grupo), m.end(grupo), html.unescape(m.group(grupo)), None))
    return sorted(out, key=lambda x: x[2])


# --- Análisis de una parte -------------------------------------------------------------------

def partir(texto, tope_bytes):
    """Corta un texto en pedazos de hasta tope_bytes, en límites de línea cuando se puede."""
    piezas, actual = [], ""
    for l in texto.splitlines(keepends=True):
        while len(l.encode()) > tope_bytes:
            corte = len(l.encode()[:tope_bytes].decode(errors="ignore"))
            if actual:
                piezas.append(actual)
                actual = ""
            piezas.append(l[:corte])
            l = l[corte:]
        if actual and len((actual + l).encode()) > tope_bytes:
            piezas.append(actual)
            actual = ""
        actual += l
    if actual:
        piezas.append(actual)
    return piezas or [""]


def quitar(texto, base, spans, reemplazo=lambda s: ""):
    """El tramo de texto que empieza en base, sin los spans absolutos indicados."""
    out, pos = [], base
    for a, b, *rest in sorted(spans, key=lambda s: (s[0], s[1])):
        if b <= pos or a >= base + len(texto):
            continue
        out.append(texto[pos - base:max(a, pos) - base])
        out.append(reemplazo(rest[0] if rest else None))
        pos = max(pos, b)
    out.append(texto[pos - base:])
    return "".join(out)


class Parte:
    def __init__(self, id_, texto, origen, tope):
        self.id, self.texto, self.origen, self.tope = id_, texto, origen, tope
        self.lector = Lector(texto)
        self.lector.feed(texto)
        self.lector.close()
        self.archivos = {}
        self.trozos = []

    def agregar(self, tipo, ident_, clase, contenido, lineas=None, contiene=None):
        carpeta = f"trozos/{nombre_archivo(self.id)}"
        nombre = {"css": "estilos", "js": "script"}.get(tipo, ident_)
        ext = {"css": ".css", "js": ".js"}.get(tipo, ".html")
        piezas = partir(contenido, self.tope * 4) if tokens(contenido) > self.tope else [contenido]
        for n, pieza in enumerate(piezas, start=1):
            sufijo = f".{n}" if len(piezas) > 1 else ""
            sub = "markup/" if tipo == "markup" else ""
            archivo = f"{carpeta}/{sub}{nombre_archivo(nombre)}{sufijo}{ext}"
            t = {"tipo": tipo, "archivo": archivo}
            if tipo == "markup":
                t.update({"id": f"{ident_}{sufijo}", "clase": clase})
                if lineas:
                    t["lineas"] = lineas
                if contiene:
                    t["contiene"] = contiene
            self.archivos[archivo] = pieza
            self.trozos.append(t)

    def region(self):
        L = self.lector
        if L.body and L.body[1] is not None:
            return L.body[0], L.body[1]
        if L.body:
            return L.body[0], len(self.texto)
        return 0, len(self.texto)

    def excluidos(self):
        L = self.lector
        spans = list(L.excluidos)
        if L.head:
            spans.append(tuple(L.head))
        for m in re.finditer(r"<!doctype[^>]*>|</?(html|body)\b[^>]*>|<title\b[^>]*>.*?</title\s*>", self.texto, flags=re.I | re.S):
            spans.append((m.start(), m.end()))
        return spans

    def elegir_trozos(self):
        """Candidatos de primer nivel; un candidato sobre el tope con candidatos adentro se parte en ellos."""
        L = self.lector
        ini, fin = self.region()
        cand = [i for i, e in enumerate(L.elementos) if clase_de(e) and ini <= e["inicio"] < fin]
        conjunto = set(cand)

        def padre_cand(i):
            p = L.elementos[i]["padre"]
            while p is not None and p not in conjunto:
                p = L.elementos[p]["padre"]
            return p

        hijos = {i: [] for i in cand}
        raices = []
        for i in cand:
            p = padre_cand(i)
            (hijos[p] if p is not None else raices).append(i)
        exc = self.excluidos()
        elegidos = []

        def visitar(i):
            e = L.elementos[i]
            contenido = quitar(self.texto[e["inicio"]:e["fin"]], e["inicio"], exc)
            if tokens(contenido) > self.tope and hijos[i]:
                for h in hijos[i]:
                    visitar(h)
                marco = quitar(contenido, e["inicio"], [(L.elementos[h]["inicio"], L.elementos[h]["fin"], ident(L.elementos[h]))
                                                         for h in hijos[i]] + exc,
                               lambda nombre: f"<!-- trozo: {nombre} -->" if nombre else "")
                elegidos.append((e["inicio"], e["fin"], f"{ident(e)}.marco", "marco", marco, None))
            else:
                elegidos.append((e["inicio"], e["fin"], ident(e), clase_de(e), contenido,
                                 [ident(L.elementos[h]) for h in hijos[i]] or None))

        for r in raices:
            visitar(r)
        return sorted(elegidos)

    def analizar(self):
        L = self.lector
        css = "\n".join(L.estilos)
        js_scripts = [s for s in L.scripts if not s["attrs"].get("src")
                      and (s["attrs"].get("type") or "text/javascript").lower() not in TIPOS_MODULO | {"application/json", "application/ld+json"}]
        js = "\n".join(s["texto"] for s in js_scripts)
        if css.strip():
            self.agregar("css", None, None, css)
        if js.strip():
            self.agregar("js", None, None, js)

        ini, fin = self.region()
        exc = self.excluidos()
        elegidos = self.elegir_trozos()
        superiores = [x for x in elegidos if x[3] != "marco"]
        for a, b, nombre, clase, contenido, contiene in elegidos:
            self.agregar("markup", nombre, clase, contenido.strip("\n") + "\n", [linea(self.texto, a), linea(self.texto, b - 1)], contiene)
        fuera = [(a, b, n) for a, b, n, c, *_ in superiores] + [(a, b, n.rsplit(".marco", 1)[0]) for a, b, n, c, *_ in elegidos if c == "marco"]
        resto = quitar(self.texto[ini:fin], ini, fuera + [(a, b, None) for a, b in exc],
                       lambda n: f"<!-- trozo: {n} -->" if n else "")
        resto = re.sub(r"\n\s*\n+", "\n", resto).strip("\n")
        if resto.strip():
            self.agregar("markup", "_resto", "resto", resto + "\n")

        css_suelto = css_sin_variables(css) + "\n" + "\n".join(f"x{{{s}}}" for s in L.inline)
        conteo = {}
        for v in valores_sueltos(css_suelto):
            conteo.setdefault(v, {"valor": v, "css": 0, "js": 0})["css"] += 1
        for lit in literales_js(js):
            for v in valores_sueltos(lit):
                conteo.setdefault(v, {"valor": v, "css": 0, "js": 0})["js"] += 1
        valores = sorted(conteo.values(), key=lambda v: (-(v["css"] + v["js"]), v["valor"]))

        textos_js = []
        for s in js_scripts:
            tipo = (s["attrs"].get("type") or "").lower()
            fuentes = literales_js(s["texto"])
            if tipo in ("text/babel", "text/jsx"):
                fuentes += re.findall(r">([^<>{}]+)<", s["texto"])
            for f in fuentes:
                limpio = " ".join(re.sub(r"<[^>]+>|\$\{[^}]*\}", " ", f).split())
                es_nombre = re.fullmatch(r"[\w.#-]+", limpio) and limpio != limpio.upper()
                es_nombre = es_nombre or re.search(r"[;{}]|=>", limpio)
                if limpio and DEMO.search(limpio) and not es_nombre and limpio not in [t["texto"] for t in textos_js]:
                    textos_js.append({"texto": limpio, "origen": "js"})
        funciones = []
        patron = r"\bfunction\s+([A-Za-z_$][\w$]*)|\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*="
        for m in re.finditer(patron, js):
            n = m.group(1) or m.group(2)
            if set(kebab(n).split("-")) & PALABRAS_PROTO and n not in [f["nombre"] for f in funciones]:
                funciones.append({"nombre": n, "linea_en_js": linea(js, m.start())})

        recursos = list(L.recursos)
        for s in L.estilos + L.inline:
            recursos += [a or b for a, b in URL_CSS.findall(s)]
        recursos += [a or b for a, b in URL_JS.findall(js)]
        externos = []
        for u in recursos:
            if re.match(r"(https?:)?//", u, flags=re.I) and u not in [e["url"] for e in externos]:
                host = re.sub(r"^(https?:)?//", "", u).split("/")[0].split(":")[0]
                externos.append({"url": u, "parte": self.id, "cdn": bool(CDN.search(host))})
        srcs = [s["attrs"]["src"] for s in L.scripts if s["attrs"].get("src")] + [u for u in recursos if u.endswith(".css")]
        frameworks = {n for u in srcs + [e["url"] for e in externos] for n, p in FRAMEWORKS if p.search(u)}
        if any((s["attrs"].get("type") or "").lower() in ("text/babel", "text/jsx") for s in L.scripts):
            frameworks.add("babel")

        return {
            "id": self.id,
            "tipo": self.origen.pop("tipo"),
            "archivo": f"partes/{nombre_archivo(self.id)}.html",
            "origen": self.origen,
            "bytes": len(self.texto.encode()),
            "tokens": tokens(self.texto),
            "lineas": n_lineas(self.texto),
            "trozos": self.trozos,
            "variables": variables(css),
            "valores": valores,
            "data_state": L.data_state + [{"valor": v, "origen": "js"} for v in dict.fromkeys(
                a or b for a, b in re.findall(r"""data-state\s*=\s*(?:"([^"]+)"|'([^']+)')""", js))],
            "controles": {"por_texto": [{k: v for k, v in t.items() if v is not None} for t in L.textos_demo] + textos_js,
                          "por_funcion": funciones},
            "animaciones": {"keyframes": len(re.findall(r"@(?:-webkit-)?keyframes\b", css)),
                            "setTimeout": len(re.findall(r"\bsetTimeout\s*\(", js)),
                            "setInterval": len(re.findall(r"\bsetInterval\s*\(", js))},
            "js_arma_markup": len([l for l in literales_js(js) if re.search(r"<[a-zA-Z][^>]*>", l)]),
        }, externos, frameworks


# --- Entrada y salida --------------------------------------------------------------------------

def leer(path):
    try:
        datos = path.read_bytes()
    except OSError as e:
        raise Fallo(f"no puedo leer {path}: {e.strerror}")
    try:
        texto = datos.decode("utf-8")
    except UnicodeDecodeError:
        raise Fallo(f"{path.name} no es texto UTF-8")
    if not re.search(r"<[a-zA-Z!][^>]*>", texto):
        raise Fallo(f"{path.name}: no encontré marcado HTML")
    return texto


def partes_de(entrada):
    """Lista de (id, texto, origen) y los datos del archivo de origen."""
    if entrada.is_dir():
        index = entrada / "index.html"
        if not index.is_file():
            raise Fallo(f"la carpeta {entrada.name} no tiene index.html; una galería se convierte desde su index.html")
        shell = leer(index)
        partes = [("shell", shell, {"tipo": "shell", "via": "index.html", "lineas": [1, n_lineas(shell)]})]
        vistos = set()
        for m in re.finditer(r"""<iframe\b[^>]*?\bsrc\s*=\s*["']([^"']+)["']""", shell, flags=re.I):
            src = m.group(1).split("#")[0].split("?")[0]
            if re.match(r"([a-z]+:)?//", src, flags=re.I) or src in vistos:
                continue
            f = (entrada / src)
            if f.is_file() and entrada.resolve() in f.resolve().parents:
                vistos.add(src)
                t = leer(f)
                partes.append((f.stem, t, {"tipo": "modulo", "via": "iframe src", "archivo": src, "lineas": [1, n_lineas(t)]}))
        archivos = [index] + [entrada / s for s in sorted(vistos)]
        origen = {"carpeta": entrada.name, "archivos": [
            {"archivo": f.name, "bytes": f.stat().st_size, "md5": hashlib.md5(f.read_bytes()).hexdigest()} for f in archivos]}
        return partes, origen
    texto = leer(entrada)
    mods = modulos(texto)
    origen = {"archivo": entrada.name, "bytes": len(texto.encode()), "lineas": n_lineas(texto),
              "md5": hashlib.md5(texto.encode()).hexdigest()}
    if not mods:
        return [("documento", texto, {"tipo": "documento", "lineas": [1, n_lineas(texto)]})], origen
    shell, pos, partes = [], 0, []
    for nombre, via, a, b, contenido, metodo in mods:
        shell.append(texto[pos:a])
        pos = b
        o = {"tipo": "modulo", "via": via, "lineas": [linea(texto, a), linea(texto, max(a, b - 1))]}
        if metodo:
            o["decodificacion"] = metodo
        partes.append((nombre, contenido, o))
    shell.append(texto[pos:])
    shell = "".join(shell)
    return [("shell", shell, {"tipo": "shell", "lineas": [1, n_lineas(texto)]})] + partes, origen


def iconos(archivos):
    """Reemplaza en el markup cada SVG que aparece más de una vez por una referencia al diccionario."""
    patron = re.compile(r"<svg\b.*?</svg\s*>", flags=re.S | re.I)
    usos = {}
    for ruta, texto in archivos.items():
        if "/markup/" in ruta:
            for m in patron.finditer(texto):
                usos[m.group(0)] = usos.get(m.group(0), 0) + 1
    repetidos = [s for s, n in usos.items() if n > 1]
    ids = {s: f"i{n}" for n, s in enumerate(repetidos)}
    for ruta in archivos:
        if "/markup/" in ruta:
            archivos[ruta] = patron.sub(lambda m: f'<svg data-icono="{ids[m.group(0)]}"></svg>' if m.group(0) in ids else m.group(0),
                                        archivos[ruta])
    if repetidos:
        archivos["trozos/iconos.html"] = "".join(f"<!-- {ids[s]} -->\n{s}\n" for s in repetidos)
    return [{"id": ids[s], "usos": usos[s], "bytes": len(s.encode())} for s in repetidos]


def desarmar(entrada, tope=TOPE):
    partes, origen = partes_de(entrada)
    ids = [p[0] for p in partes]
    if len(set(ids)) != len(ids):
        raise Fallo(f"hay partes con el mismo id: {sorted({i for i in ids if ids.count(i) > 1})}")
    archivos, salida, externos, frameworks = {}, [], [], set()
    for id_, texto, o in partes:
        p = Parte(id_, texto, dict(o), tope)
        datos, ext, fw = p.analizar()
        archivos[datos["archivo"]] = texto
        archivos.update(p.archivos)
        salida.append(datos)
        externos += [e for e in ext if e["url"] not in [x["url"] for x in externos]]
        frameworks |= fw
    lista_iconos = iconos(archivos)
    for datos in salida:
        for t in datos["trozos"]:
            contenido = archivos[t["archivo"]]
            t["bytes"], t["tokens"] = len(contenido.encode()), tokens(contenido)
    total = {}
    for datos in salida:
        for v in datos["valores"]:
            total[v["valor"]] = total.get(v["valor"], 0) + v["css"] + v["js"]
    manifiesto = {
        "version": 1,
        "origen": origen,
        "estimacion": {"metodo": METODO, "margen": MARGEN, "tope_por_trozo": tope},
        "compuesto": len(salida) > 1,
        "frameworks": sorted(frameworks),
        "requiere_render": bool(frameworks & {"react", "vue", "babel", "tailwind", "preact", "alpine"}),
        "externos": externos,
        "partes": salida,
        "iconos": lista_iconos,
        "valores": [{"valor": k, "total": n} for k, n in sorted(total.items(), key=lambda x: (-x[1], x[0]))],
    }
    return archivos, manifiesto


def escribir(trabajo, archivos, manifiesto):
    if (trabajo / "manifiesto.json").exists():
        raise Fallo(f"ya hay un manifiesto en {trabajo}; usa una carpeta de trabajo vacía")
    for ruta, contenido in archivos.items():
        f = trabajo / ruta
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(contenido)
    (trabajo / "resumen.md").write_text(resumen(manifiesto))
    (trabajo / "manifiesto.json").write_text(json.dumps(manifiesto, ensure_ascii=False, indent=1))


def resumen(m):
    """Lo que la skill necesita para armar el plan, en markdown corto: el manifiesto entero no cabe en una lectura."""
    o = m["origen"]
    nombre = o.get("archivo") or o.get("carpeta")
    l = [f"# Resumen de {nombre}", "",
         f"- Partes: {len(m['partes'])}{' (mockup compuesto)' if m['compuesto'] else ''}.",
         f"- Frameworks por CDN: {', '.join(m['frameworks']) or 'ninguno'}; requiere render: {'sí' if m['requiere_render'] else 'no'}.",
         f"- Tokens estimados con {m['estimacion']['metodo']}, tope por trozo {m['estimacion']['tope_por_trozo']}. "
         f"{m['estimacion']['margen']}", "",
         "## Partes", "", "| Parte | Origen | Tokens | CSS | JS | Markup | Variables | Animaciones |", "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"]
    for p in m["partes"]:
        suma = {t: sum(x["tokens"] for x in p["trozos"] if x["tipo"] == t) for t in ("css", "js", "markup")}
        lin = p["origen"].get("lineas")
        origen = f"{p['origen'].get('via', p['tipo'])}, líneas {lin[0]} a {lin[1]}" if lin else p["tipo"]
        variables_ = ", ".join(f"{k} {len(v)}" for k, v in p["variables"].items()) or "ninguna"
        a = p["animaciones"]
        l.append(f"| {p['id']} | {origen} | {p['tokens']} | {suma['css']} | {suma['js']} | {suma['markup']} | {variables_} | "
                 f"{a['keyframes']} keyframes, {a['setTimeout']} setTimeout, {a['setInterval']} setInterval |")
    l += ["", "## Pantallas y superposiciones", ""]
    for p in m["partes"]:
        l.append(f"### {p['id']}")
        l.append("")
        for t in p["trozos"]:
            if t["tipo"] == "markup":
                extra = f", contiene {', '.join(t['contiene'])}" if t.get("contiene") else ""
                l.append(f"- {t['clase']} `{t['id']}`: {t['tokens']} tokens, `{t['archivo']}`{extra}")
            else:
                l.append(f"- {t['tipo']}: {t['tokens']} tokens, `{t['archivo']}`")
        if p["js_arma_markup"]:
            l.append(f"- el JS arma markup en {p['js_arma_markup']} strings: parte del contenido solo se ve leyendo el JS")
        l.append("")
    l += ["## Escenarios y controles de prototipo", ""]
    for p in m["partes"]:
        c = p["controles"]
        textos = "; ".join(f"\"{x['texto']}\"" + (f" (línea {x['linea']})" if x.get("linea") else " (JS)") for x in c["por_texto"])
        funciones = ", ".join(f["nombre"] for f in c["por_funcion"])
        estados = ", ".join(sorted({d["valor"] for d in p["data_state"]}))
        if textos or funciones or estados:
            l.append(f"- {p['id']}: textos {textos or 'ninguno'}; funciones {funciones or 'ninguna'}; data-state existentes {estados or 'ninguno'}")
    l += ["", "## Valores sueltos más frecuentes", ""]
    l.append(", ".join(f"{v['valor']} ({v['total']})" for v in m["valores"][:30]) or "Ninguno.")
    l += ["", "## Recursos externos", ""]
    l += [f"- {e['url']} ({e['parte']}{', CDN' if e['cdn'] else ''})" for e in m["externos"]] or ["Ninguno."]
    if m["iconos"]:
        l += ["", f"SVG repetidos: {len(m['iconos'])}, en `trozos/iconos.html`; el markup los cita con `<svg data-icono=\"iN\">`."]
    return "\n".join(l) + "\n"


def main(argv):
    args = list(argv[1:])
    tope = TOPE
    if "--tope" in args:
        i = args.index("--tope")
        try:
            tope = int(args[i + 1])
            del args[i:i + 2]
        except (IndexError, ValueError):
            print(__doc__, file=sys.stderr)
            return 2
    if len(args) != 2 or tope <= 0:
        print(__doc__, file=sys.stderr)
        return 2
    entrada, trabajo = Path(args[0]), Path(args[1])
    try:
        archivos, manifiesto = desarmar(entrada, tope)
        escribir(trabajo, archivos, manifiesto)
    except Fallo as e:
        print(f"No pude desarmar {entrada}: {e}", file=sys.stderr)
        return 1
    print(f"Manifiesto: {trabajo / 'manifiesto.json'}")
    print(f"Resumen para el plan: {trabajo / 'resumen.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
