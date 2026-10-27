"""Pruebas de skills/html-a-vista/scripts/desarmar.py.

Cada fixture es un mockup mínimo y ficticio con una forma que el script tiene que desarmar.
Uso: python3 -m unittest discover -s tests/html-a-vista -v
"""
import json
import math
import shutil
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "skills" / "html-a-vista" / "scripts" / "desarmar.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def desarmar(entrada, trabajo, *extra):
    return subprocess.run([sys.executable, str(SCRIPT), str(entrada), str(trabajo), *extra], capture_output=True, text=True)


class Etiquetas(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)


def etiquetas(texto):
    p = Etiquetas()
    p.feed(texto)
    return p.tags


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.trabajo = self.tmp / "trabajo"

    def manifiesto(self, fixture, *extra):
        r = desarmar(FIXTURES / fixture, self.trabajo, *extra)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        return json.loads((self.trabajo / "manifiesto.json").read_text())

    def parte(self, m, id_):
        return next(p for p in m["partes"] if p["id"] == id_)

    def trozos(self, parte, tipo):
        return [t for t in parte["trozos"] if t["tipo"] == tipo]


class DocumentoUnico(Base):
    def test_una_parte_con_css_js_y_markup_por_separado(self):
        m = self.manifiesto("documento.html")
        self.assertFalse(m["compuesto"])
        self.assertEqual([p["id"] for p in m["partes"]], ["documento"])
        p = m["partes"][0]
        self.assertTrue((self.trabajo / p["archivo"]).is_file())
        css = (self.trabajo / self.trozos(p, "css")[0]["archivo"]).read_text()
        js = (self.trabajo / self.trozos(p, "js")[0]["archivo"]).read_text()
        self.assertIn(".tarjeta", css)
        self.assertNotIn("<style", css)
        self.assertIn("function abrir", js)
        self.assertNotIn("<script", js)
        markup = "".join((self.trabajo / t["archivo"]).read_text() for t in self.trozos(p, "markup"))
        self.assertIn("Pedidos de la semana", markup)
        self.assertNotIn(".tarjeta {", markup)
        self.assertNotIn("function abrir", markup)

    def test_trozos_por_pantalla_y_superposicion_con_bytes_y_tokens(self):
        m = self.manifiesto("documento.html")
        p = m["partes"][0]
        markup = {t["id"]: t for t in self.trozos(p, "markup")}
        self.assertEqual(markup["pedidos-page"]["clase"], "pantalla")
        self.assertEqual(markup["ajustes-page"]["clase"], "pantalla")
        self.assertEqual(markup["confirmar-modal"]["clase"], "superposicion")
        self.assertIn("_resto", markup)
        self.assertIn("Pedidos de la semana", (self.trabajo / markup["pedidos-page"]["archivo"]).read_text())
        self.assertNotIn("Ajustes de entrega", (self.trabajo / markup["pedidos-page"]["archivo"]).read_text())
        for t in p["trozos"]:
            contenido = (self.trabajo / t["archivo"]).read_bytes()
            self.assertEqual(t["bytes"], len(contenido), t["archivo"])
            self.assertEqual(t["tokens"], math.ceil(len(contenido) / 4), t["archivo"])
        self.assertEqual(m["estimacion"]["metodo"], "bytes/4")
        self.assertTrue(m["estimacion"]["margen"])

    def test_variables_de_root_y_de_cada_tema(self):
        p = self.manifiesto("documento.html")["partes"][0]
        self.assertEqual(p["variables"][":root"]["--acento"], "#2f7d4f")
        self.assertEqual(p["variables"]['[data-theme="dark"]'], {"--fondo": "#121815", "--tinta": "#e8efe9"})

    def test_frecuencia_de_valores_sueltos_sin_contar_las_variables(self):
        p = self.manifiesto("documento.html")["partes"][0]
        valores = {v["valor"]: v for v in p["valores"]}
        self.assertEqual(valores["14px"]["css"], 3)
        self.assertEqual(valores["#2f7d4f"]["css"], 1)
        self.assertEqual(valores["#d9dfd8"]["css"], 1)
        self.assertEqual(valores["#d9dfd8"]["js"], 1)
        self.assertNotIn("#fafaf7", valores)
        self.assertNotIn("1px", valores)

    def test_recursos_externos_y_cdn(self):
        m = self.manifiesto("documento.html")
        urls = [e["url"] for e in m["externos"]]
        self.assertIn("https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap", urls)
        self.assertNotIn("ventas@example.com", " ".join(urls))
        self.assertFalse(m["requiere_render"])
        r = self.manifiesto_aparte("react-cdn.html")
        self.assertEqual(r["frameworks"], ["babel", "react", "tailwind"])
        self.assertTrue(r["requiere_render"])
        self.assertTrue(all(e["cdn"] for e in r["externos"]))
        local = self.tmp / "babel-local.html"
        local.write_text('<html><body><div id="root"></div><script src="vendor/react.min.js"></script>'
                         '<script type="text/babel">const A = () => <p>Hola</p>;</script></body></html>')
        r = desarmar(local, self.tmp / "babel-local")
        m = json.loads((self.tmp / "babel-local" / "manifiesto.json").read_text())
        self.assertEqual(m["frameworks"], ["babel", "react"])
        self.assertTrue(m["requiere_render"])

    def manifiesto_aparte(self, fixture):
        otro = self.tmp / fixture
        r = desarmar(FIXTURES / fixture, otro)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads((otro / "manifiesto.json").read_text())

    def test_data_state_existentes(self):
        p = self.manifiesto("documento.html")["partes"][0]
        self.assertEqual([(d["valor"], d.get("linea"), d.get("origen")) for d in p["data_state"]],
                         [("lleno", 30, None), ("parcial", None, "js")])

    def test_controles_de_prototipo_por_texto_y_por_funcion(self):
        p = self.manifiesto("documento.html")["partes"][0]
        textos = [c["texto"] for c in p["controles"]["por_texto"]]
        self.assertEqual(textos, ["DEMO: plan vencido"], "los nombres de clase en strings de JS no son textos")
        funciones = [f["nombre"] for f in p["controles"]["por_funcion"]]
        self.assertEqual(funciones, ["activarDemo", "SIM_ESTADOS"])
        r = self.manifiesto_aparte("react-cdn.html")["partes"][0]
        self.assertIn("Simular plan vencido", " ".join(c["texto"] for c in r["controles"]["por_texto"]))

    def test_resumen_para_el_plan(self):
        self.manifiesto("documento.html")
        resumen = (self.trabajo / "resumen.md").read_text()
        for texto in ("pedidos-page", "ajustes-page", "confirmar-modal", "DEMO: plan vencido", "activarDemo", "lleno",
                      "fonts.googleapis.com", "14px", "bytes/4"):
            self.assertIn(texto, resumen)

    def test_animaciones_y_tiempos(self):
        p = self.manifiesto("documento.html")["partes"][0]
        self.assertEqual(p["animaciones"], {"keyframes": 1, "setTimeout": 1, "setInterval": 0})


class Compuesto(Base):
    def test_srcdoc_una_parte_por_modulo_decodificada_y_un_shell(self):
        m = self.manifiesto("compuesto-srcdoc.html")
        self.assertTrue(m["compuesto"])
        self.assertEqual([p["id"] for p in m["partes"]], ["shell", "mod-ventas", "mod-stock"])
        ventas = self.parte(m, "mod-ventas")
        self.assertEqual(ventas["origen"]["lineas"], [13, 16])
        self.assertEqual(ventas["origen"]["via"], "iframe srcdoc")
        texto = (self.trabajo / ventas["archivo"]).read_text()
        self.assertTrue(texto.startswith("<!doctype html>"))
        self.assertIn("body", etiquetas(texto))
        self.assertIn('<section id="ventas-page">', texto)
        shell = (self.trabajo / self.parte(m, "shell")["archivo"]).read_text()
        self.assertNotIn("Ventas del mes", shell)
        self.assertIn('id="mod-ventas"', shell)
        self.assertEqual(self.parte(m, "mod-ventas")["variables"][":root"], {"--verde": "#2f7d4f"})
        self.assertEqual([f["nombre"] for f in ventas["controles"]["por_funcion"]], ["ventasSimular"])

    def test_text_plain_con_script_escapado(self):
        m = self.manifiesto("compuesto-plain.html")
        self.assertEqual([p["id"] for p in m["partes"]], ["shell", "tpl-pedidos", "tpl-clientes"])
        pedidos = self.parte(m, "tpl-pedidos")
        self.assertEqual(pedidos["origen"], {"via": "script text/plain", "lineas": [11, 20], "decodificacion": "<\\ -> <"})
        texto = (self.trabajo / pedidos["archivo"]).read_text()
        self.assertIn("</script>", texto)
        self.assertNotIn("<\\/script>", texto)
        js = (self.trabajo / self.trozos(pedidos, "js")[0]["archivo"]).read_text()
        self.assertIn("pedidosModoDemo", js)
        clientes = self.parte(m, "tpl-clientes")
        self.assertEqual(clientes["origen"]["decodificacion"], "<# -> <")
        texto = (self.trabajo / clientes["archivo"]).read_text()
        self.assertIn("<!-- plantilla de clientes -->", texto)
        self.assertIn('var cierre = "<\\/script>";</script>', texto)
        shell = (self.trabajo / self.parte(m, "shell")["archivo"]).read_text()
        self.assertIn('<script type="text/plain" id="tpl-pedidos"></script>', shell)
        self.assertNotIn("Pedidos abiertos", shell)
        self.assertEqual([t["id"] for t in self.trozos(pedidos, "markup")], ["pedidos-page", "_resto"])

    def test_galeria_de_una_carpeta_como_un_mockup(self):
        r = desarmar(FIXTURES / "galeria", self.trabajo)
        self.assertEqual(r.returncode, 0, r.stderr)
        m = json.loads((self.trabajo / "manifiesto.json").read_text())
        self.assertTrue(m["compuesto"])
        self.assertEqual([p["id"] for p in m["partes"]], ["shell", "variante-a", "variante-b"])
        self.assertEqual(self.parte(m, "variante-a")["origen"], {"via": "iframe src", "archivo": "variante-a.html", "lineas": [1, 3]})


class Iconos(Base):
    def test_svg_repetidos_van_a_un_diccionario_y_los_unicos_quedan(self):
        m = self.manifiesto("documento.html")
        self.assertEqual([(i["id"], i["usos"]) for i in m["iconos"]], [("i0", 2)])
        diccionario = (self.trabajo / "trozos" / "iconos.html").read_text()
        self.assertEqual(diccionario.count("<svg"), 1)
        p = m["partes"][0]
        markup = "".join((self.trabajo / t["archivo"]).read_text() for t in self.trozos(p, "markup"))
        self.assertEqual(markup.count('<svg data-icono="i0"></svg>'), 2)
        self.assertEqual(markup.count("<circle"), 1)
        self.assertEqual(markup.count('<path d="M2 2h12v12H2z"/>'), 0)


class SinBody(Base):
    def test_archivo_sin_body_se_desarma_como_documento(self):
        m = self.manifiesto("sin-body.html")
        p = m["partes"][0]
        markup = {t["id"]: t for t in self.trozos(p, "markup")}
        self.assertEqual(sorted(markup), ["_resto", "lista-page", "nuevo-modal"])
        self.assertEqual(markup["nuevo-modal"]["clase"], "superposicion")
        self.assertIn("gap: 12px", (self.trabajo / self.trozos(p, "css")[0]["archivo"]).read_text())
        resto = (self.trabajo / markup["_resto"]["archivo"]).read_text()
        self.assertNotIn("<style", resto)
        self.assertNotIn("<title", resto)
        self.assertNotIn("var n", resto)


class Tope(Base):
    def test_trozo_que_pasa_el_tope_se_parte(self):
        filas = "\n".join(f'<li class="fila">Producto {n} de la huerta con descripción larga</li>' for n in range(400))
        grande = self.tmp / "grande.html"
        grande.write_text(f"<!doctype html><html><body>\n<section id=\"catalogo-page\">\n<ul>\n{filas}\n</ul>\n</section>\n</body></html>\n")
        r = desarmar(grande, self.trabajo, "--tope", "2000")
        self.assertEqual(r.returncode, 0, r.stderr)
        m = json.loads((self.trabajo / "manifiesto.json").read_text())
        catalogo = [t for t in m["partes"][0]["trozos"] if t.get("id", "").startswith("catalogo-page")]
        self.assertGreater(len(catalogo), 1)
        self.assertTrue(all(t["tokens"] <= 2000 for t in catalogo), [t["tokens"] for t in catalogo])
        juntos = "".join((self.trabajo / t["archivo"]).read_text() for t in catalogo)
        self.assertEqual(juntos.count("<li"), 400)
        self.assertEqual(m["estimacion"]["tope_por_trozo"], 2000)

    def test_pantalla_que_pasa_el_tope_se_parte_por_sus_subpantallas(self):
        tabla = "\n".join(f"<p>Fila {n} del detalle con texto suficiente</p>" for n in range(150))
        grande = self.tmp / "contenedor.html"
        grande.write_text("<!doctype html><html><body>\n<main id=\"app-view\">\n<h1>Marco</h1>\n"
                          f"<section id=\"resumen-tab\">\n{tabla}\n</section>\n<section id=\"detalle-tab\">\n{tabla}\n</section>\n"
                          "</main>\n</body></html>\n")
        r = desarmar(grande, self.trabajo, "--tope", "2500")
        self.assertEqual(r.returncode, 0, r.stderr)
        m = json.loads((self.trabajo / "manifiesto.json").read_text())
        ids = [t["id"] for t in m["partes"][0]["trozos"] if t["tipo"] == "markup"]
        self.assertIn("resumen-tab", ids)
        self.assertIn("detalle-tab", ids)
        self.assertIn("app-view.marco", ids)


class NoDesarmable(Base):
    def assert_falla(self, entrada, mensaje):
        r = desarmar(entrada, self.trabajo)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn(mensaje, r.stderr)
        self.assertFalse((self.trabajo / "manifiesto.json").exists())

    def test_sin_marcado_html(self):
        f = self.tmp / "notas.html"
        f.write_text("Solo texto, sin etiquetas.\n")
        self.assert_falla(f, "no encontré marcado HTML")

    def test_no_es_utf8(self):
        f = self.tmp / "binario.html"
        f.write_bytes(b"<html>\xff\xfe\x00</html>")
        self.assert_falla(f, "no es texto UTF-8")

    def test_modulo_sin_cierre(self):
        f = self.tmp / "abierto.html"
        f.write_text('<html><body><script type="text/plain" id="tpl-a"><!doctype html><html><body>Hola</body></html>\n')
        self.assert_falla(f, "tpl-a")

    def test_modulo_con_escape_desconocido(self):
        f = self.tmp / "escape.html"
        f.write_text('<html><body><script type="text/plain" id="tpl-b"><!doctype html><html><body>'
                     '<script>var a = 1;</ script></body></html></script></body></html>\n')
        self.assert_falla(f, "tpl-b")

    def test_carpeta_sin_index(self):
        d = self.tmp / "vacia"
        d.mkdir()
        self.assert_falla(d, "index.html")

    def test_no_pisa_un_manifiesto_anterior(self):
        self.trabajo.mkdir()
        (self.trabajo / "manifiesto.json").write_text("{}")
        r = desarmar(FIXTURES / "documento.html", self.trabajo)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual((self.trabajo / "manifiesto.json").read_text(), "{}")


if __name__ == "__main__":
    unittest.main()
