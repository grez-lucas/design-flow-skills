#!/usr/bin/env python3
"""Revisa de forma mecánica las vistas de design/ contra la definición de listo.

Uso: python3 revisar.py <repo-de-diseño> [vista.html ...]
Sin vistas, revisa todas las de design/vistas/. Imprime un informe en markdown y
termina con código 1 si hay algún hallazgo que bloquea.
"""
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


def sin_animacion(archivo, nombres):
    return (f"{archivo}tiene animación con `@keyframes` ({', '.join(f'`{n}`' for n in nombres)}). Las vistas no se animan: el movimiento "
            "va como comentario de intención junto al elemento, y si el tiempo importa, como un escenario (`cargando`).")


def tokens_definidos(design):
    t = design / "tokens.css"
    return set(re.findall(r"(--[\w-]+)\s*:", t.read_text())) if t.exists() else set()


def valores_sueltos(css):
    css = strip_comments(css)
    css = re.sub(r"@(?:media|container|supports)[^{]*\{", "{", css)
    colores = COLOR.findall(css) + NAMED.findall(css)
    medidas = [m.group(0) for m in PX.finditer(css) if (m.group(1), m.group(2)) not in PX_OK]
    return colores + medidas


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
    no_definidos = sorted(set(VAR.findall(css_vista)) - definidos)
    if no_definidos:
        bloquea.append(f"Variables que `tokens.css` no define: {', '.join(no_definidos)}.")

    if EXTERNAL.search(texto):
        bloquea.append("Carga recursos externos (CDN, fuentes, imágenes remotas).")

    tickets = v.metas.get("tickets", "").strip()
    spec = v.metas.get("spec", "").strip()
    if spec:
        if "<" in spec:
            bloquea.append(f"`<meta name=\"spec\">` tiene el marcador de la plantilla: `{spec}`.")
        elif Path(spec).is_absolute() or repo not in (repo / spec).resolve().parents:
            bloquea.append(f"El spec de `<meta name=\"spec\">`, `{spec}`, está fuera del repositorio. Va como ruta relativa a su raíz.")
        elif not (repo / spec).is_file():
            bloquea.append(f"El spec de `<meta name=\"spec\">`, `{spec}`, no existe en el repositorio.")
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
        if EXTERNAL.search(strip_comments(css)):
            bloquea.append(f"`{archivo}` carga recursos externos (CDN, fuentes, imágenes remotas).")
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
    return bloquea, avisa


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
    for path in vistas:
        rel, esc, cita, b, a = revisar_vista(path, repo, definidos)
        total += len(b)
        print(f"\n## {rel}\n")
        print(f"{cita} · Escenarios: {', '.join(esc) or 'ninguno'}\n")
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
