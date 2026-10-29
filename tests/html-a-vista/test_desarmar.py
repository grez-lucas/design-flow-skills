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

    def test_selector_de_estados_y_su_variable_en_html_y_en_react(self):
        """Un <select> cuyas opciones son escenarios base (normal, vacío, cargando, error...) es un control de
        prototipo, aunque su rótulo no diga demo ni escenario; también la variable de estado que arranca en uno de
        ellos y la función que el selector llama. Un selector de prioridad con "Normal" o un "Estado: Pagado" no."""
        casos = {
            "estados-html.html": ([("Normal / Vacío / Cargando / Error", 10, "select")], ["estado", "mostrarEstado"]),
            "estados-react.html": ([("Con datos / Sin datos / Cargando", 18, "select")], ["estado", "setEstado"]),
        }
        for fixture, (textos, funciones) in casos.items():
            with self.subTest(fixture=fixture):
                p = self.manifiesto_aparte(fixture)["partes"][0]
                self.assertEqual([(c["texto"], c.get("linea"), c.get("etiqueta")) for c in p["controles"]["por_texto"]], textos)
                self.assertEqual([f["nombre"] for f in p["controles"]["por_funcion"]], funciones)

    def test_resumen_para_el_plan(self):
        self.manifiesto("documento.html")
        resumen = (self.trabajo / "resumen.md").read_text()
        for texto in ("pedidos-page", "ajustes-page", "confirmar-modal", "DEMO: plan vencido", "activarDemo", "lleno",
                      "fonts.googleapis.com", "14px", "bytes/4"):
            self.assertIn(texto, resumen)

    def test_titulo_visible_de_cada_pantalla_superposicion_y_marco(self):
        m = self.manifiesto("documento.html")
        p = m["partes"][0]
        self.assertEqual(p["titulo"], "Huerta · Pedidos")
        titulos = {t["id"]: t.get("titulo") for t in self.trozos(p, "markup")}
        self.assertEqual(titulos["pedidos-page"], "Pedidos de la semana")
        self.assertEqual(titulos["ajustes-page"], "Ajustes de entrega")
        self.assertEqual(titulos["_resto"], "Huerta", "el marco lleva la marca de la cabecera, no el texto de un botón")
        self.assertEqual(titulos["confirmar-modal"], "Confirmar pedido", "sin encabezado, el texto del control que la abre")
        resumen = (self.trabajo / "resumen.md").read_text()
        self.assertIn('`pedidos-page` "Pedidos de la semana"', resumen)
        self.assertIn('`_resto` "Huerta"', resumen)
        self.assertIn("Huerta · Pedidos", resumen)

    def test_titulo_desde_rotulo_cuando_no_hay_encabezado(self):
        f = self.tmp / "rotulos.html"
        f.write_text('<!doctype html><html><body>\n<header><button>Menú</button><strong>Granja &amp; Cía</strong></header>\n'
                     '<section id="lista-page" aria-label="Lista de proveedores"><p>Proveedor</p></section>\n'
                     '<div id="borrar-modal" title="Borrar proveedor"><p>¿Seguro?</p></div>\n'
                     '<section id="partida-page"><h3>Detalle</h3><div><h2> Partida <em>12</em> </h2></div><h1>Otro</h1></section>\n'
                     '<nav><a href="#cosechas-page">Cosechas</a><button onclick="ver(\'riego-page\')">Riego <b>diario</b></button></nav>\n'
                     '<section id="cosechas-page"><p>Sin encabezado</p></section><section id="riego-page"><p>Tampoco</p></section>\n'
                     '<div id="aviso-modal"><p>Sin nada que lo nombre</p></div>\n'
                     '</body></html>\n')
        r = desarmar(f, self.trabajo)
        self.assertEqual(r.returncode, 0, r.stderr)
        p = json.loads((self.trabajo / "manifiesto.json").read_text())["partes"][0]
        titulos = {t["id"]: t.get("titulo") for t in self.trozos(p, "markup")}
        self.assertEqual(titulos, {"lista-page": "Lista de proveedores", "borrar-modal": "Borrar proveedor",
                                   "partida-page": "Partida 12", "cosechas-page": "Cosechas", "riego-page": "Riego diario",
                                   "aviso-modal": None, "_resto": "Granja & Cía"})

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
        titulos = {t["id"]: t.get("titulo") for t in m["partes"][0]["trozos"] if t["tipo"] == "markup"}
        self.assertEqual(titulos["app-view.marco"], "Marco")

    def test_los_pedazos_de_una_pantalla_partida_llevan_su_titulo(self):
        filas = "\n".join(f'<li class="fila">Producto {n} de la huerta con descripción larga</li>' for n in range(400))
        grande = self.tmp / "grande.html"
        grande.write_text(f"<!doctype html><html><body>\n<section id=\"catalogo-page\">\n<h1>Catálogo</h1>\n<ul>\n{filas}\n</ul>\n</section>\n</body></html>\n")
        r = desarmar(grande, self.trabajo, "--tope", "2000")
        self.assertEqual(r.returncode, 0, r.stderr)
        m = json.loads((self.trabajo / "manifiesto.json").read_text())
        catalogo = [t for t in m["partes"][0]["trozos"] if t.get("id", "").startswith("catalogo-page")]
        self.assertGreater(len(catalogo), 1)
        self.assertEqual({t["titulo"] for t in catalogo}, {"Catálogo"})


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


PRUEBAS = RAIZ / "pruebas" / "html-a-vista"
MOCKUPS = PRUEBAS / "fixtures" / "mockups"
LIMITE = 256 * 1024


def desarmado(entrada, trabajo):
    r = desarmar(entrada, trabajo)
    if r.returncode != 0:
        raise AssertionError(r.stderr + r.stdout)
    return json.loads((trabajo / "manifiesto.json").read_text())


class MockupGrande(unittest.TestCase):
    """El mockup grande de las evals 3 y 4, tal como lo genera pruebas/html-a-vista/generar.py."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        r = subprocess.run([sys.executable, "-B", str(PRUEBAS / "generar.py"), str(cls.tmp)], capture_output=True, text=True)
        if r.returncode != 0:
            raise AssertionError(r.stderr)
        cls.original = cls.tmp / "grande.html"
        cls.trabajo = cls.tmp / "trabajo"
        cls.m = desarmado(cls.original, cls.trabajo)
        cls.partes = {p["id"]: p for p in cls.m["partes"]}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def markup(self, parte):
        return {t["id"]: t for t in self.partes[parte]["trozos"] if t["tipo"] == "markup"}

    def test_una_parte_por_modulo_y_el_shell_con_su_tramo_de_lineas(self):
        self.assertTrue(self.m["compuesto"])
        self.assertEqual(list(self.partes), ["shell", "tpl-inventario", "tpl-compostaje", "tpl-socios"])
        lineas = self.original.read_text().splitlines()
        self.assertEqual(self.partes["shell"]["origen"]["lineas"], [1, len(lineas)])
        anterior = 0
        for modulo in ("inventario", "compostaje", "socios"):
            p = self.partes[f"tpl-{modulo}"]
            self.assertEqual(p["origen"]["via"], "script text/plain")
            self.assertEqual(p["origen"]["decodificacion"], "<\\ -> <")
            desde, hasta = p["origen"]["lineas"]
            self.assertGreater(desde, anterior, "los tramos de los módulos no se pisan y van en orden")
            self.assertTrue(lineas[desde - 1].startswith(f'<script type="text/plain" id="tpl-{modulo}"><!doctype html>'), modulo)
            self.assertEqual(lineas[hasta - 1], "</html>", modulo)
            self.assertEqual(lineas[hasta], "</script>", modulo)
            anterior = hasta
            texto = (self.trabajo / p["archivo"]).read_text()
            self.assertTrue(texto.startswith("<!doctype html>"), modulo)
            self.assertNotIn("<\\/script>", texto, modulo)
            self.assertIn("</script>", texto, modulo)
        shell = (self.trabajo / self.partes["shell"]["archivo"]).read_text()
        for texto_de_modulo in ("Inventario de semillas", "Resumen de compostaje", "Socios del huerto"):
            self.assertNotIn(texto_de_modulo, shell)
        self.assertIn('<script type="text/plain" id="tpl-socios"></script>', shell)

    def test_variables_de_root_y_de_cada_tema_por_modulo(self):
        oscuro, claro = ':root, [data-theme="dark"]', '[data-theme="light"]'
        esperado = {
            "shell": ("--bg", "#0e1410", "#f6f7f2", 6),
            "tpl-inventario": ("--warn", "#e0a21f", "#b26b00", 7),
            "tpl-compostaje": ("--calor", "#e8743b", "#c4501b", 7),
            "tpl-socios": ("--brand", "#74c795", "#2f7d4f", 6),
        }
        for parte, (nombre, valor_oscuro, valor_claro, cuantas) in esperado.items():
            with self.subTest(parte=parte):
                v = self.partes[parte]["variables"]
                self.assertEqual(list(v), [oscuro, claro])
                self.assertEqual((v[oscuro][nombre], v[claro][nombre]), (valor_oscuro, valor_claro))
                self.assertEqual(set(v[oscuro]), set(v[claro]), "cada tema define las mismas variables")
                self.assertEqual(len(v[oscuro]), cuantas)
        self.assertNotIn("--brand", self.partes["tpl-inventario"]["variables"][oscuro], "cada módulo tiene sus propias variables")

    def test_controles_demo_de_la_bascula_en_el_shell(self):
        textos = [(c["texto"], c.get("onclick")) for c in self.partes["shell"]["controles"]["por_texto"]]
        self.assertEqual(textos, [("DEMO ▾", "document.getElementById('demo').classList.toggle('open')"),
                                  ("Simular báscula desconectada", "aplicarBascula(true)"),
                                  ("Salir de demo", "aplicarBascula(false)")])
        for modulo in ("tpl-inventario", "tpl-compostaje", "tpl-socios"):
            self.assertEqual(self.partes[modulo]["controles"]["por_texto"], [], modulo)
        resumen = (self.trabajo / "resumen.md").read_text()
        self.assertIn('"Simular báscula desconectada" (línea 32)', resumen)

    def test_el_svg_que_arma_el_js_queda_avisado(self):
        compostaje = self.partes["tpl-compostaje"]
        self.assertEqual(compostaje["js_arma_markup"], 1)
        for otra in ("shell", "tpl-inventario", "tpl-socios"):
            self.assertEqual(self.partes[otra]["js_arma_markup"], 0, otra)
        resumen = (self.trabajo / "trozos" / "tpl-compostaje" / "markup" / "resumen-tab.html").read_text()
        self.assertIn('<svg id="grafico-temp" viewBox="0 0 600 200" width="100%" height="200"></svg>', resumen,
                      "en el markup el gráfico está vacío")
        js = next(t for t in compostaje["trozos"] if t["tipo"] == "js")
        self.assertIn("<polyline", (self.trabajo / js["archivo"]).read_text())
        texto = (self.trabajo / "resumen.md").read_text().split("### tpl-compostaje")[1].split("###")[0]
        self.assertIn("el JS arma markup en 1 strings", texto)
        valores = {v["valor"]: v for v in compostaje["valores"]}
        self.assertEqual(valores["#e8743b"]["js"], 1, "el color del trazo del SVG está en el JS")

    def test_ninguna_parte_ni_trozo_pasa_256_kb(self):
        self.assertGreater(self.original.stat().st_size, LIMITE, "el mockup entero sí pasa el límite")
        archivos = [p for p in self.trabajo.rglob("*") if p.is_file()]
        self.assertTrue(any(p.parent.name == "partes" for p in archivos))
        pesados = [(str(p.relative_to(self.trabajo)), p.stat().st_size) for p in archivos if p.stat().st_size > LIMITE]
        self.assertEqual(pesados, [])
        for p in self.m["partes"]:
            for t in p["trozos"]:
                self.assertLessEqual(t["tokens"], self.m["estimacion"]["tope_por_trozo"], t["archivo"])

    def test_titulo_visible_de_cada_pantalla_y_superposicion(self):
        esperado = {
            "shell": {"notif-drawer": "Notificaciones", "ayuda-overlay": "Centro de ayuda", "_resto": "Semilla · Huerto Los Aromos"},
            "tpl-inventario": {"lista-page.1": "Inventario de semillas", "lista-page.2": "Inventario de semillas",
                               "lista-page.3": "Inventario de semillas", "detalle-page": "Detalle del lote",
                               "movimientos-page": "Movimientos de semillas", "nuevo-lote-modal": "Nuevo lote",
                               "baja-modal": "Dar de baja el lote", "_resto": None},
            "tpl-compostaje": {"resumen-tab": "Resumen de compostaje", "pilas-tab": "Pilas de compost",
                               "registrar-modal": "Registrar aporte", "_resto": None},
            "tpl-socios": {"panel-socios.1": "Socios del huerto", "panel-socios.2": "Socios del huerto", "panel-cuotas": "Cuotas",
                           "panel-ajustes": "Ajustes del huerto", "invitar-modal": "Invitar socio",
                           "cuota-modal": "Registrar pago de cuota", "_resto": None},
        }
        for parte, titulos in esperado.items():
            with self.subTest(parte=parte):
                self.assertEqual({i: t.get("titulo") for i, t in self.markup(parte).items()}, titulos)
        clases = {i: t["clase"] for p in esperado for i, t in self.markup(p).items()}
        self.assertEqual({i for i, c in clases.items() if c == "superposicion"},
                         {"notif-drawer", "ayuda-overlay", "nuevo-lote-modal", "baja-modal", "registrar-modal", "invitar-modal", "cuota-modal"})
        self.assertEqual([p["titulo"] for p in self.m["partes"]],
                         ["Semilla · Integrado", "Semilla · Inventario de semillas", "Semilla · Compostaje", "Semilla · Socios"])

    def test_la_pantalla_partida_conserva_todas_sus_filas(self):
        lista = [t for t in self.partes["tpl-inventario"]["trozos"] if t.get("id", "").startswith("lista-page")]
        juntos = "".join((self.trabajo / t["archivo"]).read_text() for t in lista)
        self.assertEqual(juntos.count("<tr><td>L-"), 620)
        self.assertEqual({tuple(t["lineas"]) for t in lista}, {(31, 657)})


class MockupsChicos(unittest.TestCase):
    """Los mockups demo, react y chico de pruebas/html-a-vista/fixtures/mockups."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def desarmar(self, mockup):
        trabajo = self.tmp / mockup
        return desarmado(MOCKUPS / f"{mockup}.html", trabajo), trabajo

    def test_demo_con_sus_controles_y_sus_data_state(self):
        m, trabajo = self.desarmar("demo")
        p = m["partes"][0]
        botones = [(c["texto"], c["onclick"]) for c in p["controles"]["por_texto"] if c.get("etiqueta") == "button"]
        self.assertEqual(botones, [("DEMO ▾", "demoToggleMenu()"), ("Simular sensor sin señal", "demoSet('sin-senal')"),
                                   ("Simular tanque vacío", "demoSet('tanque-vacio')"), ("Salir de demo", "demoSet('')")])
        self.assertEqual([f["nombre"] for f in p["controles"]["por_funcion"]], ["DEMO_MODES", "demoToggleMenu", "demoSet"])
        self.assertEqual(p["data_state"], [{"valor": "full", "linea": 70}, {"valor": "partial", "linea": 70},
                                           {"valor": "off", "linea": 70}])
        resumen = (trabajo / "resumen.md").read_text()
        self.assertIn("data-state existentes full, off, partial", resumen)
        for texto in ('"Simular sensor sin señal" (línea 56)', '"Simular tanque vacío" (línea 57)'):
            self.assertIn(texto, resumen)
        markup = {t["id"]: t for t in p["trozos"] if t["tipo"] == "markup"}
        self.assertEqual({i: (t["clase"], t["titulo"]) for i, t in markup.items()},
                         {"panel-page": ("pantalla", "Zonas"), "historial-page": ("pantalla", "Historial de riego"),
                          "regar-modal": ("superposicion", "Regar ahora"), "_resto": ("resto", "Panel de riego")})
        self.assertIn("Simular tanque vacío", (trabajo / markup["_resto"]["archivo"]).read_text(), "el menú DEMO vive en el marco")
        self.assertFalse(m["requiere_render"])

    def test_el_selector_escenario_del_react_es_control_de_prototipo(self):
        """El mockup de las evals 7 y 8 cambia de escenario con un <select> rotulado "Escenario:" y un useState."""
        m, trabajo = self.desarmar("react")
        c = m["partes"][0]["controles"]
        self.assertEqual([x["texto"] for x in c["por_texto"]], ["Escenario:"])
        self.assertEqual([f["nombre"] for f in c["por_funcion"]], ["escenario", "setEscenario"])
        self.assertIn('textos "Escenario:" (JS); funciones escenario, setEscenario', (trabajo / "resumen.md").read_text())

    def test_react_por_cdn_requiere_render(self):
        m, trabajo = self.desarmar("react")
        self.assertEqual(m["frameworks"], ["babel", "react", "tailwind"])
        self.assertTrue(m["requiere_render"])
        self.assertEqual([(e["url"], e["cdn"]) for e in m["externos"]],
                         [("https://unpkg.com/react@18/umd/react.development.js", True),
                          ("https://unpkg.com/react-dom@18/umd/react-dom.development.js", True),
                          ("https://unpkg.com/@babel/standalone/babel.min.js", True),
                          ("https://cdn.tailwindcss.com", True)])
        self.assertIn("Frameworks por CDN: babel, react, tailwind; requiere render: sí.", (trabajo / "resumen.md").read_text())
        markup = [t for t in m["partes"][0]["trozos"] if t["tipo"] == "markup"]
        self.assertEqual([t["id"] for t in markup], ["_resto"], "sin render solo queda el contenedor vacío")
        self.assertEqual((trabajo / markup[0]["archivo"]).read_text(), '<div id="root"></div>\n')

    def test_chico_con_google_fonts_keyframes_y_settimeout(self):
        m, trabajo = self.desarmar("chico")
        self.assertEqual([(e["url"], e["cdn"]) for e in m["externos"]],
                         [("https://fonts.googleapis.com", True),
                          ("https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700&display=swap", True)])
        self.assertEqual(m["frameworks"], [])
        self.assertFalse(m["requiere_render"])
        p = m["partes"][0]
        self.assertEqual(p["animaciones"], {"keyframes": 1, "setTimeout": 1, "setInterval": 0})
        self.assertEqual(p["variables"], {":root": {"--hoja": "#2e7d4f", "--tierra": "#6b4f2a", "--crema": "#f6f7f3",
                                                    "--tinta": "#1d2b21", "--borde": "#d6dcd0"}})
        valores = {v["valor"]: v["css"] for v in p["valores"]}
        self.assertEqual(valores["#e07a1f"], 1, "el naranja de pendiente que la eval 1 deja a decidir")
        self.assertIn("1 keyframes, 1 setTimeout, 0 setInterval", (trabajo / "resumen.md").read_text())
        css = next(t for t in p["trozos"] if t["tipo"] == "css")
        self.assertIn("@keyframes pulso", (trabajo / css["archivo"]).read_text())


if __name__ == "__main__":
    unittest.main()
