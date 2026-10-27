"""Pruebas de skills/spec-a-html/assets/proto.js en Chrome headless.

Abre una vista de prueba con `--dump-dom` y revisa el DOM volcado. Sin Chrome la
prueba se salta, salvo con CI definido, donde falla. CHROME=<ruta> elige el binario.
Uso: python3 -m unittest discover -s tests/spec-a-html -v
"""
import functools
import http.server
import os
import shutil
import subprocess
import tempfile
import threading
import unittest
from html.parser import HTMLParser
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PROTO = RAIZ / "skills" / "spec-a-html" / "assets" / "proto.js"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
CLARO = "#f7f8fa"
OSCURO = "#0f1216"


def buscar_chrome():
    candidatos = [os.environ.get("CHROME")]
    candidatos += [shutil.which(n) for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")]
    candidatos += sorted(Path.home().glob(".cache/ms-playwright/chromium-*/chrome-linux*/chrome"), reverse=True)
    return next((str(c) for c in candidatos if c and Path(c).exists()), None)


CHROME = buscar_chrome()
if CHROME is None and os.environ.get("CI"):
    raise RuntimeError("No hay Chrome y CI está definido: las pruebas de proto.js no pueden saltarse en CI.")


class Dom(HTMLParser):
    def __init__(self, texto):
        super().__init__()
        self.html, self.body, self.panel, self.grupos = {}, {}, False, []
        self._en_panel, self._titulo = 0, False
        self.feed(texto)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.html = a
        elif tag == "body":
            self.body = a
        elif tag == "aside" and "data-proto" in a:
            self.panel, self._en_panel = True, 1
        elif self._en_panel and tag == "div":
            self._en_panel += 1
            # El título de cada grupo es el primer div de texto dentro del grupo.
            self._titulo = self._en_panel == 3

    def handle_endtag(self, tag):
        if self._en_panel and tag in ("div", "aside"):
            self._en_panel -= 1
        self._titulo = False

    def handle_data(self, data):
        if self._titulo and data.strip():
            self.grupos.append(data.strip())


class Silencioso(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@unittest.skipIf(CHROME is None, "No hay Chrome: google-chrome, chromium o Playwright en ~/.cache/ms-playwright.")
class Tema(unittest.TestCase):
    def armar(self, tokens):
        repo = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, repo)
        design = repo / "design"
        (design / "vistas" / "prueba").mkdir(parents=True)
        shutil.copy(FIXTURES / tokens, design / "tokens.css")
        shutil.copy(PROTO, design / "proto.js")
        shutil.copy(FIXTURES / "vista.html", design / "vistas" / "prueba" / "vista.html")
        return design

    def abrir(self, url):
        args = [CHROME, "--headless=new", "--disable-gpu", "--virtual-time-budget=2000", "--dump-dom", url]
        if os.environ.get("CI") or os.geteuid() == 0:
            args.insert(2, "--no-sandbox")
        r = subprocess.run(args, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        return Dom(r.stdout)

    def vista(self, tokens, query=""):
        url = (self.armar(tokens) / "vistas" / "prueba" / "vista.html").as_uri()
        return self.abrir(url + ("?" + query if query else ""))

    def test_con_tema_oscuro_el_panel_tiene_grupo_tema_y_abre_en_claro(self):
        dom = self.vista("tokens-oscuro.css")
        self.assertEqual(dom.grupos, ["Escenario", "Ancho", "Tema"])
        self.assertNotIn("data-theme", dom.html)
        self.assertEqual(dom.body["data-prueba-bg"], CLARO)

    def test_sin_tema_oscuro_no_hay_grupo_tema_y_tema_oscuro_no_cambia_nada(self):
        dom = self.vista("tokens-claro.css", "tema=oscuro")
        self.assertTrue(dom.panel)
        self.assertNotIn("Tema", dom.grupos)
        self.assertNotIn("data-theme", dom.html)
        self.assertEqual(dom.body["data-prueba-bg"], CLARO)

    def test_elegir_oscuro_en_el_panel(self):
        dom = self.vista("tokens-oscuro.css", "clic=oscuro")
        self.assertEqual(dom.html.get("data-theme"), "dark")
        self.assertEqual(dom.body["data-prueba-bg"], OSCURO)
        self.assertIn("tema=oscuro", dom.body["data-prueba-url"])

    def test_elegir_claro_desde_oscuro(self):
        dom = self.vista("tokens-oscuro.css", "tema=oscuro&clic=claro")
        self.assertNotIn("data-theme", dom.html)
        self.assertEqual(dom.body["data-prueba-bg"], CLARO)
        self.assertIn("tema=claro", dom.body["data-prueba-url"])

    def test_tema_escenario_y_ancho_a_la_vez(self):
        dom = self.vista("tokens-oscuro.css", "tema=oscuro&escenario=vacio&ancho=390")
        self.assertEqual(dom.html.get("data-theme"), "dark")
        self.assertEqual(dom.body.get("data-escenario"), "vacio")
        self.assertEqual(dom.body.get("data-ancho"), "390")

    def test_sin_panel_respeta_el_tema(self):
        dom = self.vista("tokens-oscuro.css", "tema=oscuro&proto=0")
        self.assertFalse(dom.panel)
        self.assertEqual(dom.html.get("data-theme"), "dark")
        self.assertEqual(dom.body["data-prueba-bg"], OSCURO)

    def test_file_igual_que_http(self):
        design = self.armar("tokens-oscuro.css")
        handler = functools.partial(Silencioso, directory=str(design))
        servidor = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=servidor.serve_forever, daemon=True).start()
        self.addCleanup(servidor.server_close)
        self.addCleanup(servidor.shutdown)
        query = "?tema=oscuro"
        por_file = self.abrir((design / "vistas" / "prueba" / "vista.html").as_uri() + query)
        por_http = self.abrir(f"http://127.0.0.1:{servidor.server_port}/vistas/prueba/vista.html" + query)
        for dom in (por_file, por_http):
            self.assertEqual(dom.grupos, ["Escenario", "Ancho", "Tema"])
            self.assertEqual(dom.html.get("data-theme"), "dark")
            self.assertEqual(dom.body["data-prueba-bg"], OSCURO)


if __name__ == "__main__":
    unittest.main()
