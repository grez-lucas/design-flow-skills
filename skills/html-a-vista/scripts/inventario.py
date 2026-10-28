#!/usr/bin/env python3
"""Inventario de fidelidad: compara textos, controles, campos y estados del original con una vista convertida.

Uso: python3 inventario.py <vista.html> <original.html> [<original.html> ...] [--json] [--salida <archivo>]

Los originales son los trozos de markup de la pantalla y de sus superposiciones (trozos/<parte>/markup/),
la parte entera, o el DOM renderizado si la sesión tiene navegador. Imprime el inventario en markdown,
o en JSON con --json; con --salida lo escribe en ese archivo (crea la carpeta) y solo imprime la ruta. Sale con 1 si faltan textos, controles o campos, o si la vista conserva un control
de prototipo o un data-state del original; con 0 si no; con 2 si el uso es incorrecto.
"""
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from desarmar import DEMO, literales_js  # noqa: E402

BASE = ["normal", "vacio", "cargando", "error", "sin-permiso", "muchos-datos"]
OCULTOS = {"script", "style", "svg", "template", "noscript", "head", "title"}
CONTROLES = {"button", "a", "summary"}
TIPOS_BOTON = {"button", "submit", "reset", "image"}
CAMPOS = {"input", "select", "textarea"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
LETRA = re.compile(r"[^\W\d_]")


def norm(s):
    return " ".join(s.split()).casefold()


def limpio(s):
    return " ".join(s.split())


class Lectura(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.textos, self.comentarios, self.controles, self.campos = [], [], [], []
        self.data_state, self.escenarios, self.scripts = [], [], []
        self.ocultos = 0
        self.pila = []
        self.abiertos = []
        self.etiquetas = []
        self.por_id = {}
        self.en_script = False

    def texto(self, t):
        t = limpio(t)
        if t and LETRA.search(t):
            self.textos.append(t)

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "body" and a.get("data-escenarios"):
            self.escenarios = [e.strip() for e in a["data-escenarios"].split(",") if e.strip()]
        if "data-state" in a:
            self.data_state += a["data-state"].split()
        if tag == "script" and not a.get("src"):
            self.en_script = True
            self.scripts.append("")
        if tag in OCULTOS:
            self.ocultos += 1
        elif not self.ocultos:
            for k in ("aria-label", "placeholder", "title", "alt"):
                if a.get(k):
                    self.texto(a[k])
        es_control = (tag in CONTROLES and (tag != "a" or a.get("href") or a.get("onclick"))) \
            or (tag == "input" and a.get("type", "").lower() in TIPOS_BOTON | {"checkbox", "radio"}) \
            or a.get("role") in ("button", "tab", "menuitem", "switch") or ("onclick" in a and tag not in CAMPOS)
        if not self.ocultos and es_control:
            rotulo = a.get("aria-label") or a.get("title") or (a.get("value") if tag == "input" else "")
            self.abiertos.append({"tag": tag, "rotulo": rotulo, "texto": [], "fijo": tag in VOID})
            if tag in VOID:
                self.cerrar_control()
        if not self.ocultos and tag in CAMPOS and a.get("type", "").lower() not in TIPOS_BOTON | {"hidden", "checkbox", "radio"}:
            campo = {"rotulo": a.get("aria-label") or "", "respaldo": a.get("placeholder") or a.get("name") or a.get("id") or tag}
            self.campos.append(campo)
            if a.get("id"):
                self.por_id[a["id"]] = campo
            if self.etiquetas:
                self.etiquetas[-1]["campos"].append(campo)
        if tag == "label":
            self.etiquetas.append({"for": a.get("for"), "texto": [], "campos": []})
        if tag not in VOID:
            self.pila.append(tag)

    def cerrar_control(self):
        c = self.abiertos.pop()
        rotulo = limpio(c["rotulo"] or " ".join(c["texto"]))
        if rotulo:
            self.controles.append(rotulo)

    def handle_endtag(self, tag):
        if tag == "script":
            self.en_script = False
        if tag in OCULTOS and self.ocultos:
            self.ocultos -= 1
        if self.abiertos and self.abiertos[-1]["tag"] == tag:
            self.cerrar_control()
        if tag == "label" and self.etiquetas:
            e = self.etiquetas.pop()
            texto = limpio(" ".join(e["texto"]))
            for campo in e["campos"]:
                campo["rotulo"] = campo["rotulo"] or texto
            if e["for"]:
                self.por_id.setdefault("label:" + e["for"], texto)
        if tag in self.pila:
            while self.pila and self.pila.pop() != tag:
                pass

    def handle_data(self, data):
        if self.en_script:
            self.scripts[-1] += data
            return
        if self.ocultos:
            return
        self.texto(data)
        for c in self.abiertos:
            c["texto"].append(data)
        if self.etiquetas and not any(t in ("select", "option", "textarea") for t in self.pila):
            self.etiquetas[-1]["texto"].append(data)

    def handle_comment(self, data):
        self.comentarios.append(data)

    def resultado(self):
        for id_, campo in [(k, v) for k, v in self.por_id.items() if not k.startswith("label:")]:
            campo["rotulo"] = campo["rotulo"] or self.por_id.get("label:" + id_, "")
        textos_js = []
        for js in self.scripts:
            for lit in literales_js(js):
                if re.search(r"<[a-zA-Z][^>]*>", lit):
                    for t in re.split(r"<[^>]+>|\$\{[^}]*\}", lit):
                        t = limpio(t)
                        if t and LETRA.search(t) and t not in textos_js:
                            textos_js.append(t)
        return {
            "textos": self.textos,
            "comentarios": self.comentarios,
            "controles": self.controles,
            "campos": [limpio(c["rotulo"] or c["respaldo"]) for c in self.campos],
            "data_state": self.data_state,
            "escenarios": self.escenarios,
            "textos_js": textos_js,
        }


def leer(path):
    p = Lectura()
    p.feed(Path(path).read_text(errors="replace"))
    p.close()
    return p.resultado()


def unicos(xs):
    return list(dict.fromkeys(xs))


def comparar(esperados, presentes):
    faltan = [x for x in esperados if not any(norm(x) in norm(p) for p in presentes)]
    return {"total": len(esperados), "presentes": len(esperados) - len(faltan), "faltan": faltan}


def inventario(vista, originales):
    v = leer(vista)
    origs = [leer(o) for o in originales]
    proto = unicos(c for o in origs for c in o["controles"] if DEMO.search(c))
    textos = unicos(t for o in origs for t in o["textos"] if t not in proto)
    controles = unicos(c for o in origs for c in o["controles"] if c not in proto)
    campos = unicos(c for o in origs for c in o["campos"])
    textos_js = unicos(t for o in origs for t in o["textos_js"])
    estados_original = unicos(s for o in origs for s in o["data_state"])
    visible = " \n ".join(v["textos"])
    nuevos = [t for t in unicos(v["textos"]) if not any(norm(t) in norm(o) or norm(o) in norm(t) for o in textos)]
    return {
        "textos": comparar(textos, [visible]),
        "controles": comparar(controles, v["controles"]),
        "campos": comparar(campos, v["campos"]),
        "textos_js": comparar(textos_js, [visible] + v["comentarios"]),
        "textos_nuevos": nuevos,
        "estados": {
            "escenarios_vista": v["escenarios"],
            "data_state_original": estados_original,
            "data_state_ajeno_en_vista": [s for s in estados_original if s in v["data_state"] and s not in BASE],
            "controles_prototipo_original": proto,
            "controles_prototipo_en_vista": unicos(c for c in v["controles"] + v["textos"] if DEMO.search(c)),
        },
    }


def falla(d):
    e = d["estados"]
    return any(d[k]["faltan"] for k in ("textos", "controles", "campos")) or e["data_state_ajeno_en_vista"] \
        or e["controles_prototipo_en_vista"]


def markdown(d, vista, originales):
    lineas = [f"# Inventario de {vista}", "", f"Originales: {', '.join(originales)}.", ""]
    nombres = {"textos": "Textos", "controles": "Controles", "campos": "Campos", "textos_js": "Textos que arma el JS del original"}
    for clave, titulo in nombres.items():
        x = d[clave]
        lineas += [f"## {titulo}", "", f"{x['presentes']} de {x['total']} en la vista."]
        lineas += [f"- Falta: {t}" for t in x["faltan"]]
        if clave == "textos_js" and x["total"]:
            lineas.append("Se buscan también en los comentarios de la vista: el comportamiento queda como comentario.")
        lineas.append("")
    e = d["estados"]
    lineas += ["## Estados", "",
               f"- Escenarios de la vista: {', '.join(e['escenarios_vista']) or 'ninguno'}.",
               f"- data-state del original: {', '.join(e['data_state_original']) or 'ninguno'}.",
               f"- Controles de prototipo del original, cada uno tiene que ser un escenario: {'; '.join(e['controles_prototipo_original']) or 'ninguno'}."]
    if e["data_state_ajeno_en_vista"]:
        lineas.append(f"- La vista usa data-state del original con otro significado: {', '.join(e['data_state_ajeno_en_vista'])}.")
    if e["controles_prototipo_en_vista"]:
        lineas.append(f"- La vista conserva controles de prototipo: {'; '.join(e['controles_prototipo_en_vista'])}.")
    lineas += ["", "## Textos nuevos de la vista", ""]
    lineas += [f"- {t}" for t in d["textos_nuevos"]] or ["Ninguno."]
    return "\n".join(lineas) + "\n"


def main(argv):
    args = [a for a in argv[1:] if a != "--json"]
    salida = None
    if "--salida" in args:
        i = args.index("--salida")
        if i + 1 >= len(args):
            print(__doc__, file=sys.stderr)
            return 2
        salida = Path(args[i + 1])
        del args[i:i + 2]
    if len(args) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    faltan = [a for a in args if not Path(a).is_file()]
    if faltan:
        print(f"No existe: {', '.join(faltan)}", file=sys.stderr)
        return 2
    d = inventario(args[0], args[1:])
    texto = json.dumps(d, ensure_ascii=False, indent=1) if "--json" in argv else markdown(d, args[0], args[1:])
    if salida:
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(texto + "\n")
        print(f"Inventario: {salida}")
    else:
        print(texto)
    return 1 if falla(d) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
