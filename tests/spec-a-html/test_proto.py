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
ASSETS = RAIZ / "skills" / "spec-a-html" / "assets"
PROTO = ASSETS / "proto.js"
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
        self.panel_attrs, self.filas = {}, []
        self._en_td = False
        self._en_panel, self._titulo = 0, False
        self.feed(texto)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.html = a
        elif tag == "body":
            self.body = a
        elif tag == "aside" and "data-proto" in a:
            self.panel, self._en_panel, self.panel_attrs = True, 1, a
        elif tag == "tr":
            self.filas.append("")
        elif tag == "td" and self.filas and not self.filas[-1]:
            self._en_td = True
        elif self._en_panel and tag == "div":
            self._en_panel += 1
            # El título de cada grupo es el primer div de texto dentro del grupo.
            self._titulo = self._en_panel == 3

    def handle_endtag(self, tag):
        if tag == "td":
            self._en_td = False
        if self._en_panel and tag in ("div", "aside"):
            self._en_panel -= 1
        self._titulo = False

    def handle_data(self, data):
        if self._en_td:
            self.filas[-1] += data.strip()
        if self._titulo and data.strip():
            self.grupos.append(data.strip())


class Silencioso(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@unittest.skipIf(CHROME is None, "No hay Chrome: google-chrome, chromium o Playwright en ~/.cache/ms-playwright.")
class EnChrome(unittest.TestCase):
    def armar(self, tokens, vista="vista.html"):
        """Un design/ temporal con `tokens` (un fixture, o la ruta de un asset), components.css y proto.js
        de la skill, y `vista` en design/vistas/prueba/vista.html."""
        repo = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, repo)
        design = repo / "design"
        (design / "vistas" / "prueba").mkdir(parents=True)
        shutil.copy(FIXTURES / tokens, design / "tokens.css")
        shutil.copy(ASSETS / "components.css", design / "components.css")
        shutil.copy(PROTO, design / "proto.js")
        shutil.copy(FIXTURES / vista, design / "vistas" / "prueba" / "vista.html")
        return design

    def abrir(self, url):
        args = [CHROME, "--headless=new", "--disable-gpu", "--window-size=1440,900",
                "--virtual-time-budget=2000", "--dump-dom", url]
        if os.environ.get("CI") or os.geteuid() == 0:
            args.insert(2, "--no-sandbox")
        r = subprocess.run(args, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        return Dom(r.stdout)

    def vista(self, tokens, query="", vista="vista.html"):
        url = (self.armar(tokens, vista) / "vistas" / "prueba" / "vista.html").as_uri()
        return self.abrir(url + ("?" + query if query else ""))


@unittest.skipIf(CHROME is None, "No hay Chrome: google-chrome, chromium o Playwright en ~/.cache/ms-playwright.")
class Tema(EnChrome):

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


def rect(texto):
    izquierda, arriba, derecha, abajo = (int(n) for n in texto.split(","))
    return izquierda, arriba, derecha, abajo


def dentro(interior, exterior):
    return (interior[0] >= exterior[0] and interior[1] >= exterior[1]
            and interior[2] <= exterior[2] and interior[3] <= exterior[3])


@unittest.skipIf(CHROME is None, "No hay Chrome: google-chrome, chromium o Playwright en ~/.cache/ms-playwright.")
class ModalYAvisoEnElFrame(EnChrome):
    """Con `?ancho=390`, el modal y el aviso de components.css quedan dentro del frame, no de la ventana."""
    TOKENS = ASSETS / "tokens.css"

    def test_a_390_el_modal_y_el_aviso_caben_en_el_frame(self):
        dom = self.vista(self.TOKENS, "ancho=390", vista="modal.html")
        frame = rect(dom.body["data-prueba-frame"])
        self.assertEqual(frame[2] - frame[0], 390)
        self.assertEqual(rect(dom.body["data-prueba-velo"]), frame, "el velo cubre el frame y solo el frame")
        for clave in ("data-prueba-dialogo", "data-prueba-aviso"):
            with self.subTest(clave=clave):
                self.assertTrue(dentro(rect(dom.body[clave]), frame), f"{dom.body[clave]} fuera de {frame}")

    def test_el_style_de_la_vista_manda_sobre_el_frame(self):
        """`main { display: grid }` en la vista le gana a la regla del frame de components.css."""
        dom = self.vista(self.TOKENS, vista="lista.html")
        self.assertEqual(dom.body["data-prueba-display"], "grid")

    def test_un_frame_corto_llena_la_ventana_sin_hacerla_crecer(self):
        """El velo cubre toda la pantalla aunque haya poco contenido, y el frame no suma scroll."""
        dom = self.vista(self.TOKENS, "ancho=390&proto=0", vista="modal.html")
        frame, ventana = rect(dom.body["data-prueba-frame"]), rect(dom.body["data-prueba-ventana"])
        self.assertEqual((frame[1], frame[3]), (ventana[1], ventana[3]))


@unittest.skipIf(CHROME is None, "No hay Chrome: google-chrome, chromium o Playwright en ~/.cache/ms-playwright.")
class PanelMovible(EnChrome):
    """El panel de proto.js se pasa de lado para no tapar un aviso, y la URL lo recuerda."""

    def test_abre_a_la_izquierda_lejos_de_los_avisos(self):
        """`.toast-region` va abajo a la derecha del frame: el panel abre en la esquina opuesta."""
        estilo = self.vista("tokens-claro.css").panel_attrs["style"]
        self.assertIn("left: 8px", estilo)
        self.assertNotIn("right", estilo)

    def test_cambiar_de_lado_lo_pasa_a_la_derecha_y_lo_anota_en_la_url(self):
        dom = self.vista("tokens-claro.css", "clic=Cambiar de lado")
        self.assertIn("right: 8px", dom.panel_attrs["style"])
        self.assertNotIn("left", dom.panel_attrs["style"])
        self.assertIn("panel=derecha", dom.body["data-prueba-url"])

    def test_panel_derecha_en_la_url_abre_a_la_derecha_y_vuelve(self):
        dom = self.vista("tokens-claro.css", "panel=derecha&clic=Cambiar de lado")
        self.assertIn("left: 8px", dom.panel_attrs["style"])
        self.assertIn("panel=izquierda", dom.body["data-prueba-url"])

    def test_los_grupos_no_cambian(self):
        self.assertEqual(self.vista("tokens-oscuro.css", "panel=derecha").grupos, ["Escenario", "Ancho", "Tema"])


@unittest.skipIf(CHROME is None, "No hay Chrome: google-chrome, chromium o Playwright en ~/.cache/ms-playwright.")
class RepetirConValores(EnChrome):
    """`data-repeat` con `data-valores`: cada copia de una fila toma el valor siguiente de la lista."""

    def test_muchos_datos_reparte_los_valores_entre_las_copias(self):
        dom = self.vista("tokens-claro.css", "escenario=muchos-datos", vista="repetir.html")
        self.assertEqual(dom.filas, ["Ana Pérez", "Beatriz Rojas", "Bruno Díaz", "Elena Vidal",
                                     "Carla Ruiz", "Fabián Mora", "Diego Soto"])

    def test_con_valores_suficientes_ninguna_fila_se_repite(self):
        dom = self.vista("tokens-claro.css", "escenario=muchos-datos", vista="repetir.html")
        self.assertEqual(len(dom.filas), 7)
        self.assertEqual(len(set(dom.filas)), 7)

    def test_en_la_fila_misma_y_la_lista_vuelve_a_empezar_cuando_se_acaba(self):
        """`data-valores` en el hijo directo del contenedor (un <li>), con más copias que valores."""
        dom = self.vista("tokens-claro.css", "escenario=muchos-datos", vista="lista.html")
        self.assertEqual(dom.body["data-prueba-items"].split("|"),
                         ["Ana Pérez", "Bruno Díaz", "Carla Ruiz", "Bruno Díaz", "Carla Ruiz"])

    def test_normal_muestra_solo_las_filas_escritas(self):
        dom = self.vista("tokens-claro.css", "escenario=normal", vista="repetir.html")
        self.assertEqual(dom.filas, ["Ana Pérez", "Beatriz Rojas"])


if __name__ == "__main__":
    unittest.main()
