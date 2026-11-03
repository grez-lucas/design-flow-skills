#!/usr/bin/env python3
"""Revisa de forma mecánica las vistas de design/ contra la definición de listo.

Uso: python3 revisar.py <repo-de-diseño> [vista.html ...]
Sin vistas, revisa todas las de design/vistas/. Imprime un informe en markdown y
termina con código 1 si hay algún hallazgo que bloquea.

Cruza los escenarios de cada vista con la tabla `## Escenarios en pantalla` de su spec: el de
`<meta name="spec">` o, sin él, `specs/<épica>/spec.md` de la épica de la vista. Los base son
implícitos; un escenario que no es base ni está en la tabla bloquea, y una fila de la tabla que
ninguna vista declara, un spec sin la tabla o una vista sin spec van como aviso.
"""
import math
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

BASE = ["normal", "vacio", "cargando", "error", "sin-permiso", "muchos-datos"]
COLOR = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgb|rgba|hsl|hsla)\(")
PX = re.compile(r"(?<![\w.])-?(\d+(?:\.\d+)?)(px|rem|em|pt)\b")
PX_OK = {("0", "px"), ("1", "px"), ("2", "px"), ("0", "rem"), ("0", "em")}
NAMED = re.compile(r"(?<![\w-])(red|blue|green|black|white|gray|grey|orange|yellow|purple|pink|brown)(?![\w-])", re.I)
COLOR_ATTRS = ("fill", "stroke", "color", "bgcolor", "stop-color")
COLOR_OK = {"none", "currentcolor", "transparent", "inherit"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
MAX_LINEAS = 300
VAR = re.compile(r"var\(\s*(--[\w-]+)")
EXTERNAL = re.compile(r"""(?:\b(?:src|href|srcset|poster|data)\s*=\s*["']?|url\(\s*["']?|@import\s+["'])(?:https?:)?//""", re.I)
DOMAIN = re.compile(r"\b[\w.+-]+@([\w-]+(?:\.[\w-]+)+)|\bhttps?://([\w-]+(?:\.[\w-]+)+)", re.I)
FAKE_DOMAINS = re.compile(r"(^|\.)(example(\.(com|org|net|cl))?|test|invalid|localhost|ejemplo\.(com|cl)|w3\.org)$", re.I)
LOREM = re.compile(r"lorem ipsum", re.I)
KEYFRAMES = re.compile(r"@(?:-[a-z]+-)?keyframes\s+([^\s{]+)\s*\{", re.I)
IMPORT = re.compile(r"""@import\s+(?:url\(\s*)?["']?([^"')\s;]+)""", re.I)
ESCAPE_CSS = re.compile(r"\\(?:([0-9a-fA-F]{1,6})\s?|(.))", re.S)
EXTERNO = re.compile(r"(?:https?:)?//", re.I)
ESQUEMA = re.compile(r"[a-z][\w+.-]*:", re.I)
COMPARTIDOS_CSS = ("tokens.css", "components.css")
FONT_FACE = re.compile(r"@font-face\s*\{([^}]*)\}", re.I)
URL = re.compile(r"""url\(\s*(?:"([^"]*)"|'([^']*)'|([^)\s]*))""", re.I)
CADENA = re.compile(r""""(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'""", re.S)
ATRIBUTO_CLASE = re.compile(r"""\[\s*class\s*([~|^$*]?=)\s*(?:"([^"]*)"|'([^']*)'|([^\s\]]+))\s*([iIsS])?\s*\]""")
SECCION_ESCENARIOS = "## Escenarios en pantalla"
ESCENARIO_SPEC = re.compile(r"### Escenario \d+: (.+)$")
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
SEPARADOR = re.compile(r"\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)+\|?")
CERCA = re.compile(r"\s{0,3}(`{3,}|~{3,})")
CLASE = re.compile(r"\.(-?(?:\\[0-9a-fA-F]{1,6}\s?|\\[^\n0-9a-fA-F]|[\w-]|[^\x00-\x7f])+)")


class Vista(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.body = {}
        self.metas = {}
        self.hojas = []
        self.js_en_atributos = []
        self.scripts = []
        self.states = []
        self.styles = []
        self.inline = []
        self.in_style = False
        self.in_script = False
        self.script_inline = []
        self.controls_in_frame = []
        self.stack = []
        self.frame_at = None
        self.clases = []

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.stack.append(tag)
        if tag == "body":
            self.body = a
        if tag == "meta" and a.get("name"):
            self.metas[a["name"]] = a.get("content", "")
        if tag == "link" and ("stylesheet" in (a.get("rel") or "").lower().split()
                              or re.sub(r"[?#].*", "", a.get("href") or "").lower().endswith(".css")):
            self.hojas.append(a.get("href") or "")
        for k, valor in attrs:
            if re.sub(r"[\x00-\x20]", "", valor or "").lower().startswith("javascript:"):
                self.js_en_atributos.append(f'<{tag} {k}="{valor}">')
        if tag == "script":
            self.in_script = True
            self.scripts.append(a.get("src", ""))
        if tag == "style":
            self.in_style = True
        if "style" in a:
            self.inline.append(a["style"])
        self.clases += (a.get("class") or "").split()
        for k in COLOR_ATTRS:
            if k in a and (a[k] or "").strip().lower() not in COLOR_OK and not (a[k] or "").startswith("var("):
                self.inline.append(f"{k}: {a[k]}")
        if "data-state" in a:
            self.states.append(a["data-state"])
        if "data-frame" in a and self.frame_at is None:
            self.frame_at = len(self.stack)
        if self.frame_at is None:
            self.js_en_atributos += [f'<{tag} {k}="{v}">' for k, v in attrs if k.startswith("on")]
        else:
            handlers = [k for k, _ in attrs if k.startswith("on")]
            links = [v for k, v in attrs if k == "href" and v and "escenario=" in v]
            if handlers or links:
                self.controls_in_frame.append(f"<{tag}> con {', '.join(handlers) or 'enlace a ?escenario='}")

    def handle_endtag(self, tag):
        if tag == "style":
            self.in_style = False
        if tag == "script":
            self.in_script = False
        if tag in VOID or tag not in self.stack:
            return
        while self.stack:
            if self.frame_at is not None and len(self.stack) == self.frame_at:
                self.frame_at = None
            if self.stack.pop() == tag:
                break

    def handle_data(self, data):
        if self.in_style:
            self.styles.append(data)
        elif self.in_script and data.strip():
            self.script_inline.append(data.strip()[:80])


def strip_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def sin_escapes(css):
    """El CSS con sus escapes resueltos: `@\\6b eyframes` es `@keyframes` para el navegador, y para la revisión."""
    def letra(m):
        if m.group(1):
            n = int(m.group(1), 16)
            return chr(n) if 0 < n <= 0x10FFFF else "\ufffd"
        return m.group(2)
    return ESCAPE_CSS.sub(letra, css)


def keyframes(texto):
    """Nombres de las reglas @keyframes de un CSS o un HTML, con cualquier prefijo (-webkit-, -o-) o escritas con
    escapes de CSS. Un comentario, `/* */` o `<!-- -->`, que las nombra no cuenta: es justo el comentario de intención
    que reemplaza a la animación."""
    return KEYFRAMES.findall(sin_escapes(re.sub(r"<!--.*?-->", " ", strip_comments(texto), flags=re.S)))


def imports_locales(css):
    """Lo que un CSS importa con `@import` desde un archivo local o un `data:`, no desde un CDN (eso es un recurso
    externo, aparte)."""
    return [r for r in IMPORT.findall(sin_escapes(strip_comments(css))) if not EXTERNO.match(r)]


def resolver(ref, desde):
    """La ruta local a la que lleva un `href` o `src` desde la carpeta de la vista, o None si es externo o tiene
    esquema (`data:`, `javascript:`)."""
    ref = re.sub(r"[?#].*", "", ref.strip())
    if not ref or EXTERNO.match(ref) or ESQUEMA.match(ref):
        return None
    return (desde / ref).resolve()


def urls(css):
    """Lo que va dentro de cada `url()`, con o sin comillas."""
    return [a or b or c for a, b, c in URL.findall(css)]


def urls_locales(css, design):
    """Las `url()` locales de un CSS compartido que no se admiten, en dos listas: las de un `@font-face` que no llevan
    a un `.woff2` que existe directo en `design/fuentes/`, y las de fuera de un `@font-face` (imágenes, `data:`), salvo
    `url(#id)`. Las externas no cuentan aquí: las bloquea la regla de recursos externos."""
    css = sin_escapes(strip_comments(css))
    fuentes = (design / "fuentes").resolve()
    malas_fuentes = []
    for bloque in FONT_FACE.findall(css):
        for ref in urls(bloque):
            if EXTERNO.match(ref):
                continue
            ruta = resolver(ref, design)
            if ruta is None or ruta.parent != fuentes or ruta.suffix.lower() != ".woff2" or not ruta.is_file():
                malas_fuentes.append(ref[:40])
    otras = [r[:40] for r in urls(FONT_FACE.sub("", css)) if r and not EXTERNO.match(r) and not r.startswith("#")]
    return malas_fuentes, otras


def sin_animacion(archivo, nombres):
    return (f"{archivo}tiene animación con `@keyframes` ({', '.join(f'`{n}`' for n in nombres)}). Las vistas no se animan: el movimiento "
            "va como comentario de intención junto al elemento, y si el tiempo importa, como un escenario (`cargando`).")


def negaciones(selector):
    """Los tramos `:not(...)` y `:has(...)` de un selector, con sus paréntesis anidados."""
    tramos, desde = [], 0
    while True:
        m = re.compile(r":(?:not|has)\(", re.I).search(selector, desde)
        if not m:
            return tramos
        prof, i = 1, m.end()
        while i < len(selector) and prof:
            prof += {"(": 1, ")": -1}.get(selector[i], 0)
            i += 1
        tramos.append((m.start(), i))
        desde = i


def sin_tramos(texto, tramos):
    for a, b in reversed(tramos):
        texto = texto[:a] + texto[b:]
    return texto


def clases_definidas(css):
    """(clases, atributos) de los selectores de un CSS, a cualquier profundidad (`@media`, `@layer`). Las clases son las
    que nombra un selector, también como contexto (`.field label`), con pseudoclase o dentro de `:where()`, con sus
    escapes resueltos. Los atributos son los `[class~="x"]`, `[class*="col-"]` y demás, como (operador, valor, sin
    distinguir mayúsculas). No cuenta lo que nombran un comentario, una cadena, el preludio de una regla @ ni un
    `:not()` o un `:has()`, que no pintan al elemento con esa clase."""
    css = strip_comments(css)
    oculto = CADENA.sub(lambda m: m.group(0)[0] + " " * (len(m.group(0)) - 2) + m.group(0)[-1], css)
    clases, atributos = set(), set()
    for m in re.finditer(r"([^{};]*)\{", oculto):
        preludio, original = m.group(1), css[m.start(1):m.end(1)]
        if preludio.strip().startswith("@"):
            continue
        tramos = negaciones(preludio)
        clases.update(sin_escapes(c).rstrip() for c in CLASE.findall(sin_tramos(preludio, tramos)))
        for op, a, b, c, bandera in ATRIBUTO_CLASE.findall(sin_tramos(original, tramos)):
            atributos.add((op, a or b or c, bandera.lower() == "i"))
    return clases, atributos


def calza(clase, atributo):
    """True si un selector de atributo sobre `class` pinta a un elemento con esa clase, mirando la clase sola."""
    op, valor, sin_mayusculas = atributo
    if sin_mayusculas:
        clase, valor = clase.lower(), valor.lower()
    if op in ("=", "~="):
        return clase == valor
    if op == "|=":
        return clase == valor or clase.startswith(valor + "-")
    if not valor:
        return False
    return {"^=": clase.startswith, "$=": clase.endswith, "*=": lambda v: v in clase}[op](valor)


def tokens_definidos(design):
    t = design / "tokens.css"
    return set(re.findall(r"(--[\w-]+)\s*:", t.read_text())) if t.exists() else set()


def valores_sueltos(css):
    css = strip_comments(css)
    css = re.sub(r"@(?:media|container|supports)[^{]*\{", "{", css)
    colores = COLOR.findall(css) + NAMED.findall(css)
    medidas = [m.group(0) for m in PX.finditer(css) if (m.group(1), m.group(2)) not in PX_OK]
    return colores + medidas


def error_del_spec(spec, repo):
    """El bloqueo de un `<meta name="spec">` declarado que no sirve, o None si no hay meta o apunta bien."""
    if not spec:
        return None
    if "<" in spec:
        return f"`<meta name=\"spec\">` tiene el marcador de la plantilla: `{spec}`."
    if Path(spec).is_absolute() or repo not in (repo / spec).resolve().parents:
        return f"El spec de `<meta name=\"spec\">`, `{spec}`, está fuera del repositorio. Va como ruta relativa a su raíz."
    if not (repo / spec).is_file():
        return f"El spec de `<meta name=\"spec\">`, `{spec}`, no existe en el repositorio."
    return None


def fuera_de_bloques(texto):
    """Las líneas del markdown que no están dentro de un bloque de código cercado (``` o ~~~)."""
    lineas, cerca = [], None
    for linea in texto.splitlines():
        m = CERCA.match(linea)
        if m and (cerca is None or m.group(1)[0] == cerca[0] and len(m.group(1)) >= len(cerca)):
            cerca = m.group(1) if cerca is None else None
            continue
        if cerca is None:
            lineas.append(linea)
    return lineas


def celdas(fila):
    t = fila.strip()
    t = t[1:] if t.startswith("|") else t
    t = t[:-1] if t.endswith("|") and not t.endswith("\\|") else t
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", t)]


def leer_spec(texto):
    """Los nombres de los `### Escenario N: <nombre>` del spec y las filas de `## Escenarios en pantalla`.

    `tabla` es None si el spec no tiene la sección. `errores` lista lo que impide usar la tabla: sin tabla o con otras
    columnas, una fila sin tres celdas, un slug que no es minúsculas y guiones o que se repite en el mismo alcance,
    un alcance vacío y un nombre que no es el de ningún `### Escenario N`.
    """
    lineas = fuera_de_bloques(texto)
    escenarios = [m.group(1).strip() for m in map(ESCENARIO_SPEC.match, lineas) if m]
    inicio = next((i for i, l in enumerate(lineas) if l.rstrip() == SECCION_ESCENARIOS), None)
    if inicio is None:
        return {"escenarios": escenarios, "tabla": None, "errores": []}
    seccion = []
    for linea in lineas[inicio + 1:]:
        if re.match(r"#{1,2} ", linea):
            break
        seccion.append(linea)
    filas = [l for l in seccion if l.strip().startswith("|")]
    errores, tabla = [], []
    columnas = "`| Slug | Nombre | Alcance |`"
    if len(filas) < 2 or [c.lower() for c in celdas(filas[0])] != ["slug", "nombre", "alcance"] or not SEPARADOR.fullmatch(filas[1].strip()):
        errores.append(f"`{SECCION_ESCENARIOS}` no tiene una tabla con las columnas {columnas}, así que no se puede "
                       "cruzar con las vistas.")
        return {"escenarios": escenarios, "tabla": [], "errores": errores}
    vistos = set()
    for fila in filas[2:]:
        c = celdas(fila)
        if len(c) != 3:
            errores.append(f"La fila `{fila.strip()}` de `{SECCION_ESCENARIOS}` no tiene tres columnas ({columnas}).")
            continue
        slug, nombre, alcance = c[0].strip("`").strip(), c[1], c[2]
        if not SLUG.fullmatch(slug):
            errores.append(f"El slug `{slug}` de `{SECCION_ESCENARIOS}` no es minúsculas, números y guiones, sin tildes "
                           "ni espacios: las vistas no pueden declararlo igual.")
            continue
        if (slug, alcance) in vistos:
            errores.append(f"`{SECCION_ESCENARIOS}` repite el slug `{slug}` con el mismo alcance, {alcance or 'sin decir'}.")
            continue
        vistos.add((slug, alcance))
        if not alcance:
            errores.append(f"La fila `{slug}` de `{SECCION_ESCENARIOS}` no dice su alcance: `global` o el nombre de la pantalla.")
        if nombre not in escenarios:
            errores.append(f"La fila `{slug}` de `{SECCION_ESCENARIOS}` nombra \"{nombre}\", y el spec no tiene un "
                           f"`### Escenario N: {nombre}`: la vista no tiene un criterio que diga qué muestra.")
        tabla.append({"slug": slug, "nombre": nombre, "alcance": alcance})
    return {"escenarios": escenarios, "tabla": tabla, "errores": errores}


def declarados(path):
    v = Vista()
    v.feed(path.read_text(errors="ignore"))
    return [e.strip() for e in v.body.get("data-escenarios", "").split(",") if e.strip()], v.metas


def spec_de_vista(path, repo, metas):
    """El spec contra el que se cruzan los escenarios de la vista, relativo a la raíz, y si se pudo resolver.

    Manda `<meta name="spec">`; sin él, `specs/<épica>/spec.md` de la épica de `design/vistas/<épica>/<vista>.html`.
    Devuelve (ruta, None) si existe, (None, ruta esperada o None) si no hay spec, y (None, False) si el meta no sirve,
    porque ese caso ya bloquea en revisar_vista.
    """
    meta = metas.get("spec", "").strip()
    if meta:
        return (None, False) if error_del_spec(meta, repo) else (Path(meta).as_posix(), None)
    partes = path.relative_to(repo).parts
    if len(partes) != 4 or partes[:2] != ("design", "vistas"):
        return None, None
    ruta = f"specs/{partes[2]}/spec.md"
    return (ruta, None) if (repo / ruta).is_file() else (None, ruta)


def cruzar_escenarios(repo, vistas):
    """Cruza los escenarios de cada vista con la tabla `## Escenarios en pantalla` de su spec.

    Devuelve los hallazgos por vista ({ruta: (bloquea, avisa)}) y por spec ({ruta relativa: (bloquea, avisa)}). Un
    escenario de la vista que no es base ni está en la tabla bloquea. Una fila de la tabla que ninguna vista de
    `design/vistas/` declara, revisada o no, avisa: puede llegar en otro ticket. Sin tabla o sin spec, avisa.
    """
    por_vista, por_spec, leidos = {}, {}, {}

    def leer(ruta):
        if ruta not in leidos:
            leidos[ruta] = leer_spec((repo / ruta).read_text(errors="ignore"))
        return leidos[ruta]

    for path in vistas:
        bloquea, avisa = [], []
        escenarios, metas = declarados(path)
        ruta, esperada = spec_de_vista(path, repo, metas)
        if ruta is None:
            if esperada is not False:
                donde = f"`{esperada}`" if esperada else "`specs/<épica>/spec.md`"
                avisa.append(f"No tiene spec contra el cual cruzar sus escenarios: ni `<meta name=\"spec\">` ni {donde}. "
                             "Sin spec, nadie confirma que cada escenario propio de la vista es uno que producto decidió.")
            por_vista[path] = (bloquea, avisa)
            continue
        leido = leer(ruta)
        por_spec.setdefault(ruta, ([], []))
        if leido["tabla"] is None:
            avisa.append(f"`{ruta}` no tiene la sección `{SECCION_ESCENARIOS}`, así que sus escenarios no se cruzan con "
                         "el spec. `grilling-es` la agrega cuando vuelva a tocar ese spec; un spec congelado no se "
                         "reescribe por esto.")
        elif not leido["errores"] or leido["tabla"]:
            tabla = {f["slug"] for f in leido["tabla"]}
            sin_respaldo = [e for e in escenarios if e not in BASE and e not in tabla]
            if sin_respaldo:
                bloquea.append(f"Declara escenarios que no son base ni están en `{SECCION_ESCENARIOS}` de `{ruta}`: "
                               f"{', '.join(f'`{e}`' for e in sin_respaldo)}. DEV no tiene un escenario del spec que diga "
                               "qué pasa ahí: usa el slug que la tabla ya tiene o agrega el escenario al spec con `grilling-es`.")
        por_vista[path] = (bloquea, avisa)

    usados = {}
    for path in sorted((repo / "design" / "vistas").rglob("*.html")):
        escenarios, metas = declarados(path)
        ruta, _ = spec_de_vista(path, repo, metas)
        if ruta in por_spec:
            usados.setdefault(ruta, set()).update(escenarios)
    for ruta, (bloquea, avisa) in por_spec.items():
        leido = leer(ruta)
        bloquea += leido["errores"]
        for fila in leido["tabla"] or []:
            if fila["slug"] not in usados.get(ruta, set()):
                avisa.append(f"`{fila['slug']}` (\"{fila['nombre']}\", alcance {fila['alcance'] or 'sin decir'}) está en "
                             f"`{SECCION_ESCENARIOS}` y ninguna vista de `design/vistas/` lo declara. Puede llegar en otro "
                             "ticket; si no, falta en la vista que lo muestra.")
    return por_vista, por_spec


def revisar_vista(path, repo, definidos):
    texto = path.read_text(errors="ignore")
    v = Vista()
    v.feed(texto)
    bloquea, avisa = [], []
    rel = path.relative_to(repo)

    design = (repo / "design").resolve()
    compartidos = {design / a for a in COMPARTIDOS_CSS}
    for archivo in COMPARTIDOS_CSS:
        if not any(resolver(h, path.parent) == design / archivo for h in v.hojas):
            bloquea.append(f"No enlaza `{archivo}` del repositorio de diseño (`design/{archivo}`).")
    ajenas = [h for h in v.hojas if not EXTERNO.match(h.strip()) and resolver(h, path.parent) not in compartidos]
    ajenas += imports_locales("\n".join(v.styles))
    if ajenas:
        bloquea.append(f"Enlaza o importa {', '.join(f'`{h}`' for h in dict.fromkeys(ajenas))}, y una vista usa solo `tokens.css` "
                       "y `components.css` del repositorio de diseño. Lo que esa hoja trae no lo ve esta revisión: los estilos "
                       "propios van en el `<style>` de la vista, y lo que se repite, en `components.css`.")
    proto = design / "proto.js"
    if not any(resolver(s, path.parent) == proto for s in v.scripts if s):
        bloquea.append("No enlaza `proto.js` del repositorio de diseño (`design/proto.js`).")
    otros_js = [s for s in v.scripts if s and resolver(s, path.parent) != proto] + v.script_inline + v.js_en_atributos
    if otros_js:
        bloquea.append(f"Tiene JavaScript propio además de `proto.js`: {otros_js[:3]}. El comportamiento va como comentario, no como código.")

    escenarios = [e.strip() for e in v.body.get("data-escenarios", "").split(",") if e.strip()]
    no_aplica = set()
    for parte in v.body.get("data-no-aplica", "").split(";"):
        if not parte.strip():
            continue
        nombre, _, motivo = parte.partition(":")
        nombre = nombre.strip()
        if nombre not in BASE:
            bloquea.append(f"`data-no-aplica` nombra `{nombre}`, que no es un escenario base. Separa cada uno con `;` y revisa la ortografía.")
            continue
        if not motivo.strip():
            bloquea.append(f"`data-no-aplica` marca `{nombre}` sin motivo.")
        if nombre in escenarios:
            avisa.append(f"`{nombre}` está declarado y a la vez marcado como no aplica.")
        no_aplica.add(nombre)
    if not escenarios:
        bloquea.append("No declara `data-escenarios` en `<body>`.")
    faltan = [b for b in BASE if b not in escenarios and b not in no_aplica]
    if faltan:
        bloquea.append(f"Escenarios base sin declarar ni marcar en `data-no-aplica`: {', '.join(faltan)}.")
    usados = {s for grupo in v.states for s in grupo.split()}
    huerfanos = sorted(usados - set(escenarios))
    if huerfanos:
        bloquea.append(f"`data-state` con escenarios que `data-escenarios` no declara: {', '.join(huerfanos)}.")
    sin_bloque = [e for e in escenarios if e not in usados and e != escenarios[0]]
    if sin_bloque:
        avisa.append(f"Escenarios declarados sin ningún bloque `data-state` propio: {', '.join(sin_bloque)}. Revisa que se vean distintos.")
    if "muchos-datos" in escenarios and "data-repeat" not in texto and not any(g.split() == ["muchos-datos"] for g in v.states):
        avisa.append("`muchos-datos` no tiene `data-repeat` ni bloque propio: se ve igual que `normal`.")
    if "cargando" in escenarios and "skeleton" not in texto:
        avisa.append("`cargando` no usa `.skeleton`.")
    if v.controls_in_frame:
        bloquea.append(f"Controles de prototipo dentro del frame: {v.controls_in_frame[:3]}. Los escenarios se cambian desde el panel de `proto.js`.")

    sueltos = valores_sueltos("\n".join(v.styles + v.inline))
    if sueltos:
        bloquea.append(f"Valores visuales sueltos fuera de `tokens.css`: {sorted(set(sueltos))[:8]}.")
    css_vista = "\n".join(v.styles + v.inline)
    animadas = keyframes(css_vista)
    if animadas:
        bloquea.append(sin_animacion("La vista ", animadas))
    if FONT_FACE.search(sin_escapes(strip_comments(css_vista))):
        bloquea.append("La vista declara un `@font-face`. La fuente del producto se declara una sola vez, en `tokens.css`, "
                       "con el archivo en `design/fuentes/`.")
    no_definidos = sorted(set(VAR.findall(css_vista)) - definidos)
    if no_definidos:
        bloquea.append(f"Variables que `tokens.css` no define: {', '.join(no_definidos)}.")
    comp = design / "components.css"
    con_regla, atributos = clases_definidas((comp.read_text() if comp.exists() else "") + "\n" + "\n".join(v.styles))
    sin_regla = [c for c in dict.fromkeys(v.clases) if c not in con_regla and not any(calza(c, a) for a in atributos)]
    if sin_regla:
        bloquea.append(f"Usa clases que `components.css` no define, ni el `<style>` de la vista: "
                       f"{', '.join(f'`.{c}`' for c in sin_regla[:8])}. Sin su regla, la pantalla no se ve como DEV la "
                       "tiene que construir. Las de la skill, como `.modal` o `.toast-region`, las agrega `spec-a-html` a "
                       "`components.css`; las de una sola vista van en su `<style>`.")

    if EXTERNAL.search(texto):
        bloquea.append("Carga recursos externos (CDN, fuentes, imágenes remotas).")

    tickets = v.metas.get("tickets", "").strip()
    spec = v.metas.get("spec", "").strip()
    error = error_del_spec(spec, repo)
    if error:
        bloquea.append(error)
    if tickets and "ID-DEL-TICKET" not in tickets:
        cita = f"Tickets: {tickets}"
    elif spec:
        cita = f"Spec: {spec}"
    elif "tickets" in v.metas:
        cita = f"Tickets: {tickets or 'ninguno'}"
        bloquea.append("No cita sus tickets en `<meta name=\"tickets\">`.")
    else:
        cita = "Tickets: ninguno"
        bloquea.append("No cita sus tickets en `<meta name=\"tickets\">` ni su spec en `<meta name=\"spec\">`.")

    visible = re.sub(r"<!--.*?-->", "", texto, flags=re.S)
    dominios = set()
    for m in DOMAIN.finditer(visible):
        d = (m.group(1) or m.group(2) or "").lower()
        if d and not FAKE_DOMAINS.search(d):
            dominios.add(d)
    if dominios:
        avisa.append(f"Dominios que podrían ser reales: {sorted(dominios)[:6]}. Los datos van con `example.com` o equivalentes.")
    if LOREM.search(visible):
        bloquea.append("Tiene texto de relleno (lorem ipsum).")

    lineas = texto.count("\n") + 1
    if lineas > MAX_LINEAS:
        avisa.append(f"Tiene {lineas} líneas; una vista típica queda bajo {MAX_LINEAS}. Busca estilos repetidos que sean componentes o markup duplicado por escenario.")
    partes = rel.parts
    if len(partes) != 4 or partes[:2] != ("design", "vistas"):
        avisa.append("No está en `design/vistas/<épica>/<vista>.html`.")

    return rel, escenarios, cita, bloquea, avisa


def revisar_compartidos(design, definidos):
    bloquea, avisa = [], []
    for archivo in ("tokens.css", "components.css"):
        ruta = design / archivo
        if not ruta.exists():
            continue
        css = ruta.read_text()
        animadas = keyframes(css)
        if animadas:
            bloquea.append(sin_animacion(f"`{archivo}` ", animadas))
        if EXTERNAL.search(sin_escapes(strip_comments(css))):
            bloquea.append(f"`{archivo}` carga recursos externos (CDN, fuentes, imágenes remotas).")
        if archivo != "tokens.css" and FONT_FACE.search(sin_escapes(strip_comments(css))):
            bloquea.append(f"`{archivo}` declara un `@font-face`. La fuente del producto se declara una sola vez, en `tokens.css`, "
                           "con el archivo en `design/fuentes/`.")
        fuentes, otras = urls_locales(css, design)
        if fuentes:
            bloquea.append(f"`{archivo}` carga {', '.join(f'`{r}`' for r in fuentes)} en un `@font-face`. La fuente del producto va "
                           "como archivo `.woff2` directo en `design/fuentes/`, con una `url()` relativa que llega a él.")
        if otras:
            bloquea.append(f"`{archivo}` carga {', '.join(f'`{r}`' for r in otras)} con `url()`. La única `url()` local de los "
                           "archivos compartidos es la fuente del producto en `design/fuentes/`: los íconos van como SVG inline "
                           "en la vista y las imágenes como marcador.")
        locales = imports_locales(css)
        if locales:
            bloquea.append(f"`{archivo}` importa {', '.join(f'`{r}`' for r in locales)} con `@import`. Los archivos compartidos "
                           "no cargan otras hojas: lo que haga falta va dentro del mismo archivo, donde la revisión lo ve.")
    if not (design / "tokens.css").exists():
        bloquea.append("No existe `design/tokens.css`.")
    comp = design / "components.css"
    if comp.exists():
        css = comp.read_text()
        sueltos = valores_sueltos(css)
        if sueltos:
            bloquea.append(f"`components.css` tiene valores sueltos: {sorted(set(sueltos))[:8]}.")
        no_def = sorted(set(VAR.findall(css)) - definidos)
        if no_def:
            bloquea.append(f"`components.css` usa variables que `tokens.css` no define: {', '.join(no_def)}.")
    else:
        bloquea.append("No existe `design/components.css`.")
    if not (design / "proto.js").exists():
        bloquea.append("No existe `design/proto.js`.")
    else:
        original = Path(__file__).resolve().parents[2] / "spec-a-html" / "assets" / "proto.js"
        if original.exists() and original.read_text() != (design / "proto.js").read_text():
            avisa.append("`proto.js` no es igual al de la skill `spec-a-html`; se copia sin modificar.")
    tok = design / "tokens.css"
    if tok.exists():
        t = strip_comments(tok.read_text())
        if "calc(" in t:
            avisa.append("`tokens.css` usa `calc()`; los tokens son una lista de valores que se trasladan a otros stacks.")
        prefijos = ("--color-", "--font-family-", "--font-size-", "--font-weight-", "--line-height-", "--space-", "--radius-", "--shadow-", "--size-")
        raros = sorted(n for n in re.findall(r"(--[\w-]+)\s*:", t) if not n.startswith(prefijos))
        if raros:
            avisa.append(f"`tokens.css` tiene nombres fuera de la convención de prefijos: {raros[:8]}.")
    avisa += avisos_de_tema(design)
    return bloquea, avisa


def reglas_de_primer_nivel(css):
    """(selector, cuerpo) de cada regla de primer nivel, en orden de aparición. Entra a los bloques `@layer`, que no
    cambian a qué aplica una regla; salta `@media`, `@supports` y las demás reglas @, que la condicionan."""
    reglas, prof, desde, selector = [], 0, 0, ""
    for i, c in enumerate(css):
        if c == "{":
            if prof == 0:
                selector, desde = css[desde:i].split(";")[-1].strip(), i + 1
            prof += 1
        elif c == "}" and prof:
            prof -= 1
            if prof == 0:
                if re.match(r"@layer\b", selector, re.I):
                    reglas += reglas_de_primer_nivel(css[desde:i])
                elif not selector.startswith("@"):
                    reglas.append((selector, css[desde:i]))
                desde = i + 1
    return reglas


def selector_normal(selector):
    """El selector sin espacios ni comillas simples; `html:root` es `:root`."""
    s = re.sub(r"\s+", "", selector).replace("'", '"')
    return ":root" if s.lower() == "html:root" else s


def declaraciones(css, selector):
    """Las declaraciones de las reglas de primer nivel cuyo selector incluye `selector`, sin `!important`; la última
    manda."""
    buscado = selector_normal(selector)
    valores = {}
    for sel, cuerpo in reglas_de_primer_nivel(css):
        if buscado not in (selector_normal(s) for s in sel.split(",")):
            continue
        for decl in cuerpo.split(";"):
            nombre, dos_puntos, valor = decl.partition(":")
            nombre = nombre.strip()
            if dos_puntos and nombre:
                valor = re.sub(r"\s*!\s*important\s*$", "", valor.strip(), flags=re.I)
                valores[nombre if nombre.startswith("--") else nombre.lower()] = valor
    return valores


def color_scheme(css, selectores):
    """El `color-scheme` del primer selector de `selectores` que lo declara, en minúsculas, o None."""
    for selector in selectores:
        valor = declaraciones(css, selector).get("color-scheme")
        if valor is not None:
            return " ".join(valor.lower().split())
    return None


NOMBRES_DE_COLOR = {"black": (0, 0, 0), "white": (255, 255, 255)}


def angulo(texto):
    """Un ángulo de CSS (`deg`, `turn`, `rad`, `grad` o un número en grados) en grados."""
    m = re.fullmatch(r"(-?[\d.]+)(deg|turn|rad|grad)?", texto)
    if not m:
        raise ValueError(texto)
    return float(m.group(1)) * {None: 1, "deg": 1, "turn": 360, "rad": 180 / math.pi, "grad": 0.9}[m.group(2)]


def numero(texto, cien=1.0):
    """Un número de CSS; un porcentaje vale `cien` en 100%, y `none`, 0."""
    if texto == "none":
        return 0.0
    return float(texto[:-1]) / 100 * cien if texto.endswith("%") else float(texto)


def oklab_a_rgb(l, a, b):
    """sRGB de 0 a 255 de un color OKLab."""
    l_, m_, s_ = (l + 0.3963377774 * a + 0.2158037573 * b, l - 0.1055613458 * a - 0.0638541728 * b,
                  l - 0.0894841775 * a - 1.2914855480 * b)
    l3, m3, s3 = l_ ** 3, m_ ** 3, s_ ** 3
    lineales = (4.0767416621 * l3 - 3.3077115913 * m3 + 0.2309699292 * s3,
                -1.2684380046 * l3 + 2.6097574011 * m3 - 0.3413193965 * s3,
                -0.0041960863 * l3 - 0.7034186147 * m3 + 1.7076147010 * s3)

    def gamma(c):
        c = min(max(c, 0.0), 1.0)
        return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
    return tuple(gamma(c) * 255 for c in lineales)


def leer_color(valor):
    """(r, g, b) de 0 a 255 de un color hex, `rgb()`, `hsl()`, `oklab()`, `oklch()`, `black` o `white`, o None si no
    es un color literal que se pueda leer."""
    valor = valor.strip().lower()
    if valor in NOMBRES_DE_COLOR:
        return NOMBRES_DE_COLOR[valor]
    m = re.fullmatch(r"#([0-9a-f]{3,8})", valor)
    if m and len(m.group(1)) in (3, 4, 6, 8):
        h = m.group(1)
        h = "".join(c * 2 for c in h) if len(h) <= 4 else h
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    m = re.fullmatch(r"(rgba?|hsla?|oklab|oklch)\(([^)]*)\)", valor)
    if not m:
        return None
    partes = re.split(r"[\s,/]+", m.group(2).strip())[:3]
    if len(partes) < 3:
        return None
    funcion = m.group(1)
    try:
        if funcion.startswith("rgb"):
            return tuple(numero(p, 255) for p in partes)
        if funcion == "oklab":
            return oklab_a_rgb(numero(partes[0]), numero(partes[1], 0.4), numero(partes[2], 0.4))
        if funcion == "oklch":
            l, c, h = numero(partes[0]), numero(partes[1], 0.4), math.radians(0 if partes[2] == "none" else angulo(partes[2]))
            return oklab_a_rgb(l, c * math.cos(h), c * math.sin(h))
        h = angulo(partes[0]) % 360 / 360
        s, l = (numero(p) for p in partes[1:])
        s, l = (x / 100 if not p.endswith("%") else x for x, p in zip((s, l), partes[1:]))
    except ValueError:
        return None
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
    return tuple(canal(h + d) * 255 for d in (1 / 3, 0, -1 / 3))


def luminancia(rgb):
    """Luminancia relativa de WCAG 2."""
    def lineal(c):
        c = min(max(c, 0), 255) / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = map(lineal, rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def tema_base_oscuro(css):
    """True si en `:root` el fondo (`--color-bg`) tiene menos luminancia que el texto (`--color-text`), False si no,
    None si alguno de los dos falta o no es un color literal."""
    raiz = declaraciones(css, ":root")
    fondo, texto = (leer_color(raiz.get(n, "")) for n in ("--color-bg", "--color-text"))
    if fondo is None or texto is None:
        return None
    return luminancia(fondo) < luminancia(texto)


def avisos_de_tema(design):
    """Aviso, sin bloquear, si el tema base de `tokens.css` es oscuro y `:root` (o `html`) no declara
    `color-scheme: dark`, o si no se puede comprobar porque `--color-bg` o `--color-text` faltan o no son colores
    literales."""
    tok = design / "tokens.css"
    if not tok.exists():
        return []
    css = strip_comments(tok.read_text())
    esquema = color_scheme(css, (":root", "html")) or ""
    if set(esquema.split()) - {"only"} == {"dark"}:
        return []
    oscuro = tema_base_oscuro(css)
    if oscuro is None:
        return ["La revisión no puede comprobar si el tema base de `tokens.css` es oscuro, porque `--color-bg` o `--color-text` de "
                "`:root` faltan o no son un color que se pueda leer (por ejemplo, un `var()`). Defínelos con su valor en "
                "`:root`; si el tema base es oscuro, declara también `color-scheme: dark`."]
    if not oscuro:
        return []
    hoy = f"hoy declara `color-scheme: {esquema}`" if esquema else "no declara `color-scheme`"
    return [f"`tokens.css` tiene el tema base oscuro (en `:root`, `--color-bg` es más oscuro que `--color-text`) sin "
            f"`color-scheme: dark` ({hoy}): el navegador dibuja claras las barras de desplazamiento y los controles "
            "nativos. Agrega `color-scheme: dark;` en `:root`."]


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    repo = Path(sys.argv[1]).resolve()
    design = repo / "design"
    definidos = tokens_definidos(design)
    vistas = [(p if p.is_absolute() else repo / p).resolve() for p in map(Path, sys.argv[2:])] or sorted((design / "vistas").rglob("*.html"))
    fuera = [p for p in vistas if repo not in p.parents]
    if fuera:
        print(f"Vistas fuera del repositorio, no se revisan: {[str(p) for p in fuera]}")
        vistas = [p for p in vistas if p not in fuera]
    total = 0
    print("# Revisión mecánica\n")
    b, a = revisar_compartidos(design, definidos)
    total += len(b)
    print("## Archivos compartidos\n")
    for x in b:
        print(f"- BLOQUEA: {x}")
    for x in a:
        print(f"- AVISO: {x}")
    if not b and not a:
        print("- Sin hallazgos.")
    if not vistas:
        print("\nNo hay vistas en `design/vistas/<épica>/`.")
        return 1
    por_vista, por_spec = cruzar_escenarios(repo, vistas)
    for path in vistas:
        rel, esc, cita, b, a = revisar_vista(path, repo, definidos)
        b, a = b + por_vista[path][0], a + por_vista[path][1]
        total += len(b)
        print(f"\n## {rel}\n")
        print(f"{cita} · Escenarios: {', '.join(esc) or 'ninguno'}\n")
        for x in b:
            print(f"- BLOQUEA: {x}")
        for x in a:
            print(f"- AVISO: {x}")
        if not b and not a:
            print("- Sin hallazgos.")
    for ruta, (b, a) in por_spec.items():
        total += len(b)
        print(f"\n## Escenarios del spec: {ruta}\n")
        for x in b:
            print(f"- BLOQUEA: {x}")
        for x in a:
            print(f"- AVISO: {x}")
        if not b and not a:
            print("- Sin hallazgos.")
    print(f"\nTotal de hallazgos que bloquean: {total}")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
