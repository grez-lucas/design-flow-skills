"""Pruebas de skills/html-a-vista/scripts/inventario.py.

Uso: python3 -m unittest discover -s tests/html-a-vista -v
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "skills" / "html-a-vista" / "scripts" / "inventario.py"
FIX = Path(__file__).resolve().parent / "fixtures" / "inventario"
REFERENCIA = Path(__file__).resolve().parent / "fixtures" / "referencia"
DESARMAR = RAIZ / "skills" / "html-a-vista" / "scripts" / "desarmar.py"
MOCKUPS = RAIZ / "pruebas" / "html-a-vista" / "fixtures" / "mockups"


def inventario(vista, *originales, formato="--json"):
    args = [sys.executable, str(SCRIPT), str(FIX / vista)] + [o if o.startswith("--") else str(FIX / o) for o in map(str, originales)]
    return subprocess.run(args + ([formato] if formato else []), capture_output=True, text=True)


class Inventario(unittest.TestCase):
    def datos(self, vista, *originales):
        r = inventario(vista, *originales)
        self.assertIn(r.returncode, (0, 1), r.stderr)
        return r.returncode, json.loads(r.stdout)

    def test_vista_fiel_no_tiene_faltantes(self):
        codigo, d = self.datos("vista-fiel.html", "original.html", "modal.html")
        for clave in ("textos", "controles", "campos", "textos_js"):
            self.assertEqual(d[clave]["faltan"], [], clave)
            self.assertEqual(d[clave]["presentes"], d[clave]["total"], clave)
        self.assertEqual(codigo, 0)

    def test_textos_controles_y_campos_que_faltan(self):
        codigo, d = self.datos("vista-incompleta.html", "original.html", "modal.html")
        self.assertEqual(codigo, 1)
        self.assertEqual(d["textos"]["faltan"], ["Correo de contacto", "nombre@example.com", "Exportar", "Cerrar aviso",
                                                 "¿Confirmas el pedido de esta semana?", "Sí, confirmar"])
        self.assertEqual(d["controles"]["faltan"], ["Exportar", "Cerrar aviso", "Sí, confirmar"])
        self.assertEqual(d["campos"]["faltan"], ["Correo de contacto"])

    def test_normaliza_espacios_y_mayusculas_pero_no_cuenta_comentarios(self):
        _, d = self.datos("vista-incompleta.html", "original.html")
        self.assertNotIn("Pedidos de la semana", d["textos"]["faltan"])
        self.assertIn("Exportar", d["textos"]["faltan"])

    def test_no_espera_el_control_de_prototipo_ni_textos_del_svg(self):
        _, d = self.datos("vista-fiel.html", "original.html")
        self.assertNotIn("DEMO: plan vencido", d["textos"]["faltan"] + d["controles"]["faltan"])
        self.assertEqual(d["estados"]["controles_prototipo_original"], ["DEMO: plan vencido"])
        _, d = self.datos("vista-incompleta.html", "original.html")
        self.assertNotIn("Texto del gráfico", d["textos"]["faltan"])

    def test_textos_que_arma_el_js_valen_tambien_en_comentarios(self):
        _, fiel = self.datos("vista-fiel.html", "original.html")
        self.assertEqual(fiel["textos_js"], {"total": 1, "presentes": 1, "faltan": []})
        _, incompleta = self.datos("vista-incompleta.html", "original.html")
        self.assertEqual(incompleta["textos_js"]["faltan"], ["Planilla enviada a"])

    def test_estados_prototipo_y_data_state_ajeno_en_la_vista(self):
        _, d = self.datos("vista-incompleta.html", "original.html")
        self.assertEqual(d["estados"]["escenarios_vista"], ["normal", "vacio"])
        self.assertEqual(d["estados"]["data_state_original"], ["lleno"])
        self.assertEqual(d["estados"]["data_state_ajeno_en_vista"], ["lleno"])
        self.assertEqual(d["estados"]["controles_prototipo_en_vista"], ["DEMO: plan vencido"])
        _, fiel = self.datos("vista-fiel.html", "original.html")
        self.assertEqual(fiel["estados"]["data_state_ajeno_en_vista"], [])
        self.assertEqual(fiel["estados"]["controles_prototipo_en_vista"], [])

    def test_textos_nuevos_de_la_vista(self):
        _, d = self.datos("vista-fiel.html", "original.html", "modal.html")
        self.assertEqual(d["textos_nuevos"], ["Tu plan venció."])

    def test_informe_en_markdown(self):
        r = inventario("vista-incompleta.html", "original.html", formato=None)
        self.assertEqual(r.returncode, 1)
        for texto in ("## Textos", "## Controles", "## Campos", "## Estados", "Correo de contacto", "DEMO: plan vencido", "otro significado: lleno"):
            self.assertIn(texto, r.stdout)

    def test_salida_a_un_archivo_sin_redireccion(self):
        with tempfile.TemporaryDirectory() as tmp:
            destino = Path(tmp) / "inventario" / "pedidos.json"
            r = inventario("vista-incompleta.html", "original.html", "--salida", destino)
            self.assertEqual(r.returncode, 1, r.stderr)
            self.assertEqual(json.loads(destino.read_text()), json.loads(inventario("vista-incompleta.html", "original.html").stdout))
            self.assertIn(str(destino), r.stdout)
            self.assertNotIn('"textos"', r.stdout, "con --salida la pantalla no repite el inventario")
            md = Path(tmp) / "pedidos.md"
            inventario("vista-incompleta.html", "original.html", "--salida", md, formato=None)
            self.assertIn("## Controles", md.read_text())

    def test_salida_sin_ruta_es_uso_incorrecto(self):
        self.assertEqual(inventario("vista-fiel.html", "original.html", "--salida").returncode, 2)

    def test_uso_incorrecto(self):
        r = subprocess.run([sys.executable, str(SCRIPT), str(FIX / "vista-fiel.html")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        r = inventario("no-existe.html", "original.html")
        self.assertEqual(r.returncode, 2)
        self.assertIn("no-existe.html", r.stderr)


class VistasAprobadas(unittest.TestCase):
    """Vistas que el revisor aprobó en la iteración 2 (eval 1, reservas; eval 5, panel de riego), contra los trozos
    que desarmar.py saca del mockup real, los mismos que usó cada corrida."""

    CASOS = {
        "reservas": ("chico", ["reservas-page"]),
        "panel": ("demo", ["panel-page", "regar-modal", "_resto"]),
    }

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        for mockup in ("chico", "demo"):
            r = subprocess.run([sys.executable, "-B", str(DESARMAR), str(MOCKUPS / f"{mockup}.html"), str(cls.tmp / mockup)],
                               capture_output=True, text=True)
            if r.returncode != 0:
                raise AssertionError(r.stderr)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def originales(self, vista, trozos=None):
        mockup, ids = self.CASOS[vista]
        return [self.tmp / mockup / "trozos" / "documento" / "markup" / f"{t}.html" for t in trozos or ids]

    def datos(self, vista, html=None, trozos=None):
        archivo = REFERENCIA / f"{vista}.html"
        if html is not None:
            archivo = self.tmp / f"{vista}-mutada.html"
            archivo.write_text(html)
        r = subprocess.run([sys.executable, str(SCRIPT), str(archivo), *map(str, self.originales(vista, trozos)), "--json"],
                           capture_output=True, text=True)
        self.assertIn(r.returncode, (0, 1), r.stderr)
        return r.returncode, json.loads(r.stdout)

    def faltan(self, d):
        return {k: d[k]["faltan"] for k in ("textos", "controles", "campos", "textos_js")}

    def test_la_vista_aprobada_cubre_todo_el_original(self):
        for vista, totales in {"reservas": (27, 5, 0), "panel": (21, 5, 1)}.items():
            with self.subTest(vista=vista):
                codigo, d = self.datos(vista)
                self.assertEqual(self.faltan(d), dict.fromkeys(("textos", "controles", "campos", "textos_js"), []))
                self.assertEqual((d["textos"]["total"], d["controles"]["total"], d["campos"]["total"]), totales)
                self.assertEqual(d["estados"]["data_state_ajeno_en_vista"], [])
                self.assertEqual(d["estados"]["controles_prototipo_en_vista"], [])
                self.assertEqual(codigo, 0)

    def test_el_panel_no_arrastra_el_menu_demo_ni_los_data_state_del_mockup(self):
        _, d = self.datos("panel")
        self.assertEqual(d["estados"]["controles_prototipo_original"],
                         ["DEMO ▾", "Simular sensor sin señal", "Simular tanque vacío", "Salir de demo"])
        self.assertEqual(d["estados"]["data_state_original"], ["full", "partial", "off"])
        self.assertIn("sensor-sin-senal", d["estados"]["escenarios_vista"])
        self.assertIn("tanque-vacio", d["estados"]["escenarios_vista"])

    def test_la_cabecera_de_reservas_cambio_el_nombre_de_la_persona(self):
        codigo, d = self.datos("reservas", trozos=["reservas-page", "_resto"])
        self.assertEqual(self.faltan(d)["textos"], ["Huerto Los Aromos · Paula Rivas"])
        self.assertEqual(codigo, 1)

    def test_la_vista_sin_un_texto_lo_marca(self):
        casos = {
            "panel": ('<p class="text-schedule">Próximo riego: hoy 18:15</p>', "", "Próximo riego: hoy 18:15"),
            "reservas": ('>No hay reservas con este estado.</p>', "></p>", "No hay reservas con este estado."),
        }
        for vista, (quitar, poner, texto) in casos.items():
            with self.subTest(vista=vista):
                html = (REFERENCIA / f"{vista}.html").read_text()
                self.assertEqual(html.count(quitar), 1)
                codigo, d = self.datos(vista, html.replace(quitar, poner))
                self.assertEqual(self.faltan(d), {"textos": [texto], "controles": [], "campos": [], "textos_js": []})
                self.assertEqual(codigo, 1)

    def test_la_vista_sin_un_control_lo_marca(self):
        casos = {
            "panel": ('<button class="btn" type="button">Cancelar</button>', "Cancelar"),
            "reservas": ('<button class="btn btn--primary" type="button" data-state="normal vacio cargando error muchos-datos '
                         'filtro-pendientes filtro-sin-resultados">Nueva reserva</button>', "Nueva reserva"),
        }
        for vista, (quitar, control) in casos.items():
            with self.subTest(vista=vista):
                html = (REFERENCIA / f"{vista}.html").read_text()
                self.assertEqual(html.count(quitar), 1)
                codigo, d = self.datos(vista, html.replace(quitar, ""))
                self.assertEqual(self.faltan(d), {"textos": [control], "controles": [control], "campos": [], "textos_js": []})
                self.assertEqual(codigo, 1)

    def test_la_vista_sin_el_campo_del_modal_lo_marca(self):
        html = (REFERENCIA / "panel.html").read_text()
        sin_campos = html.replace('<input id="duracion" type="number" value="15" min="5" max="60">', "").replace(
            '<input id="duracion-invalida" type="number" value="3" min="5" max="60" aria-invalid="true" aria-describedby="duracion-error">', "")
        codigo, d = self.datos("panel", sin_campos)
        self.assertEqual(self.faltan(d)["campos"], ["Duración en minutos"])
        self.assertEqual(self.faltan(d)["textos"], [], "el rótulo sigue en la vista")
        self.assertEqual(codigo, 1)


if __name__ == "__main__":
    unittest.main()
