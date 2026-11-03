"""Pruebas de skills/checklist-diseno/scripts/revisar.py.

Cada fixture es una vista mínima con un caso que el script ya resolvió mal una vez.
Uso: python3 -m unittest discover -s tests/checklist-diseno -v
"""
import importlib.util
import io
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "skills" / "checklist-diseno" / "scripts" / "revisar.py"
ASSETS = RAIZ / "skills" / "spec-a-html" / "assets"
PROTO = ASSETS / "proto.js"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

spec = importlib.util.spec_from_file_location("revisar", SCRIPT)
revisar = importlib.util.module_from_spec(spec)
sys.modules["revisar"] = revisar
spec.loader.exec_module(revisar)


class Revision(unittest.TestCase):
    def setUp(self):
        self.repo = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.repo)
        self.design = self.repo / "design"
        (self.design / "vistas" / "pedidos").mkdir(parents=True)
        shutil.copy(FIXTURES / "tokens.css", self.design / "tokens.css")
        shutil.copy(FIXTURES / "components.css", self.design / "components.css")
        shutil.copy(PROTO, self.design / "proto.js")

        (self.repo / "specs" / "pedidos").mkdir(parents=True)
        (self.repo / "specs" / "pedidos" / "spec.md").write_text("# Spec · Pedidos\n")

    def revisar(self, fixture):
        vista = self.design / "vistas" / "pedidos" / fixture
        shutil.copy(FIXTURES / fixture, vista)
        _, _, _, bloquea, avisa = revisar.revisar_vista(vista, self.repo, revisar.tokens_definidos(self.design))
        return bloquea, avisa

    def resumen(self, fixture):
        """La línea de resumen que imprime main() para la vista."""
        vista = self.design / "vistas" / "pedidos" / fixture
        shutil.copy(FIXTURES / fixture, vista)
        salida = io.StringIO()
        with mock.patch.object(sys, "argv", ["revisar.py", str(self.repo), str(vista)]), redirect_stdout(salida):
            revisar.main()
        return next(l for l in salida.getvalue().splitlines() if "Escenarios:" in l)

    def test_vista_limpia_sin_hallazgos(self):
        self.assertEqual(self.revisar("limpia.html"), ([], []))
        self.assertEqual(revisar.revisar_compartidos(self.design, revisar.tokens_definidos(self.design)), ([], []))

    def test_container_no_es_valor_suelto(self):
        bloquea, _ = self.revisar("container.html")
        self.assertEqual(bloquea, [])

    def test_colores_en_atributos_svg_bloquean(self):
        bloquea, _ = self.revisar("svg.html")
        sueltos = [b for b in bloquea if "Valores visuales sueltos" in b]
        self.assertEqual(len(sueltos), 1, bloquea)
        self.assertIn("#ff0000", sueltos[0])
        self.assertIn("#00ff00", sueltos[0])

    def test_xmlns_de_svg_no_es_dominio_real(self):
        _, avisa = self.revisar("svg.html")
        self.assertEqual([a for a in avisa if "Dominios" in a], [])

    def test_etiquetas_vacias_cierran_el_frame(self):
        bloquea, _ = self.revisar("etiquetas-vacias.html")
        self.assertEqual([b for b in bloquea if "Controles de prototipo" in b], [])

    def test_autocerradas_no_void_y_void_cierran_el_frame(self):
        bloquea, _ = self.revisar("autocerradas.html")
        self.assertEqual([b for b in bloquea if "Controles de prototipo" in b], [])

    def test_comentarios_css_no_son_valores_sueltos(self):
        self.assertEqual(self.revisar("comentarios-css.html"), ([], []))

    def test_proto_js_distinto_al_original_avisa(self):
        (self.design / "proto.js").write_text(PROTO.read_text() + "\n// cambio local\n")
        _, avisa = revisar.revisar_compartidos(self.design, revisar.tokens_definidos(self.design))
        self.assertIn("`proto.js` no es igual al de la skill `spec-a-html`; se copia sin modificar.", avisa)

    def test_proto_js_anterior_al_control_de_tema_avisa_una_vez(self):
        shutil.copy(FIXTURES / "proto-anterior.js", self.design / "proto.js")
        _, avisa = revisar.revisar_compartidos(self.design, revisar.tokens_definidos(self.design))
        self.assertEqual([a for a in avisa if "proto.js" in a], ["`proto.js` no es igual al de la skill `spec-a-html`; se copia sin modificar."])
        shutil.copy(PROTO, self.design / "proto.js")
        _, avisa = revisar.revisar_compartidos(self.design, revisar.tokens_definidos(self.design))
        self.assertEqual([a for a in avisa if "proto.js" in a], [])

    def test_no_aplica_valido_cubre_escenarios_base(self):
        self.assertEqual(self.revisar("no-aplica-valido.html"), ([], []))

    def test_no_aplica_sin_motivo_bloquea(self):
        bloquea, _ = self.revisar("no-aplica-sin-motivo.html")
        self.assertIn("`data-no-aplica` marca `sin-permiso` sin motivo.", bloquea)

    def test_no_aplica_mal_escrito_bloquea(self):
        bloquea, _ = self.revisar("no-aplica-mal-escrito.html")
        self.assertTrue(any("nombra `sin-permisos`, que no es un escenario base" in b for b in bloquea), bloquea)

    def test_no_aplica_declarado_avisa(self):
        _, avisa = self.revisar("no-aplica-declarado.html")
        self.assertIn("`sin-permiso` está declarado y a la vez marcado como no aplica.", avisa)

    def test_recursos_externos_desde_css_bloquean(self):
        bloquea, _ = self.revisar("externos-css.html")
        self.assertIn("Carga recursos externos (CDN, fuentes, imágenes remotas).", bloquea)

    def test_medidas_negativas_rem_pt_y_colores_con_nombre_bloquean(self):
        bloquea, _ = self.revisar("medidas.html")
        sueltos = " ".join(b for b in bloquea if "Valores visuales sueltos" in b)
        for valor in ("-8px", "1.5rem", "14pt", "red"):
            self.assertIn(f"'{valor}'", sueltos, valor)

    def test_comentarios_html_no_cuentan(self):
        self.assertEqual(self.revisar("comentarios.html"), ([], []))

    def test_spec_existente_sin_tickets_no_bloquea(self):
        self.assertEqual(self.revisar("spec-sin-tickets.html"), ([], []))

    def test_spec_inexistente_bloquea_nombrando_la_ruta(self):
        bloquea, _ = self.revisar("spec-inexistente.html")
        self.assertEqual(len(bloquea), 1, bloquea)
        self.assertIn("`specs/envios/spec.md`", bloquea[0])
        self.assertIn("no existe", bloquea[0])

    def test_spec_marcador_de_plantilla_bloquea(self):
        bloquea, _ = self.revisar("spec-marcador.html")
        self.assertEqual(len(bloquea), 1, bloquea)
        self.assertIn("specs/<épica>/spec.md", bloquea[0])
        self.assertIn("marcador", bloquea[0])

    def test_spec_fuera_del_repositorio_bloquea(self):
        fuera = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, fuera)
        (fuera / "spec.md").write_text("# Spec\n")
        texto = (FIXTURES / "spec-sin-tickets.html").read_text().replace("specs/pedidos/spec.md", str(fuera / "spec.md"))
        vista = self.design / "vistas" / "pedidos" / "spec-fuera.html"
        vista.write_text(texto)
        _, _, _, bloquea, _ = revisar.revisar_vista(vista, self.repo, revisar.tokens_definidos(self.design))
        self.assertEqual(len(bloquea), 1, bloquea)
        self.assertIn("fuera del repositorio", bloquea[0])

    def test_sin_tickets_ni_spec_bloquea_nombrando_las_dos_metas(self):
        bloquea, _ = self.revisar("sin-tickets-ni-spec.html")
        self.assertEqual(len(bloquea), 1, bloquea)
        self.assertIn('<meta name="tickets">', bloquea[0])
        self.assertIn('<meta name="spec">', bloquea[0])

    def test_tickets_vacio_o_marcador_sin_spec_sigue_bloqueando(self):
        for fixture in ("tickets-vacio.html", "tickets-marcador.html"):
            with self.subTest(fixture=fixture):
                bloquea, _ = self.revisar(fixture)
                self.assertEqual(bloquea, ["No cita sus tickets en `<meta name=\"tickets\">`."])

    def test_tickets_y_spec_resumen_con_tickets_sin_hallazgos(self):
        self.assertEqual(self.revisar("tickets-y-spec.html"), ([], []))
        self.assertTrue(self.resumen("tickets-y-spec.html").startswith("Tickets: DEMO-1 · "))

    def test_tickets_validos_y_spec_inexistente_bloquea(self):
        bloquea, _ = self.revisar("tickets-y-spec-inexistente.html")
        self.assertEqual(len(bloquea), 1, bloquea)
        self.assertIn("`specs/envios/spec.md`", bloquea[0])
        self.assertIn("no existe", bloquea[0])

    def test_tickets_validos_y_spec_fuera_del_repositorio_bloquea(self):
        texto = (FIXTURES / "tickets-y-spec.html").read_text().replace("specs/pedidos/spec.md", "../fuera/spec.md")
        vista = self.design / "vistas" / "pedidos" / "tickets-y-spec-fuera.html"
        vista.write_text(texto)
        _, _, _, bloquea, _ = revisar.revisar_vista(vista, self.repo, revisar.tokens_definidos(self.design))
        self.assertEqual(len(bloquea), 1, bloquea)
        self.assertIn("fuera del repositorio", bloquea[0])

    def test_animacion_en_la_vista_bloquea(self):
        bloquea, _ = self.revisar("animacion.html")
        animacion = [b for b in bloquea if "animación" in b]
        self.assertEqual(len(animacion), 1, bloquea)
        self.assertIn("`latir`", animacion[0])

    def test_animacion_nombrada_en_un_comentario_no_cuenta(self):
        self.assertEqual(self.revisar("animacion-comentario.html"), ([], []))

    def test_javascript_propio_en_la_vista_bloquea(self):
        bloquea, avisa = self.revisar("js-propio.html")
        self.assertTrue(any("JavaScript propio" in b for b in bloquea), bloquea)
        self.assertEqual([a for a in avisa if "JavaScript" in a], [])

    def revisar_texto(self, texto, nombre="caso.html"):
        vista = self.design / "vistas" / "pedidos" / nombre
        vista.write_text(texto)
        _, _, _, bloquea, avisa = revisar.revisar_vista(vista, self.repo, revisar.tokens_definidos(self.design))
        return bloquea, avisa

    def test_script_que_no_es_el_proto_js_del_repositorio_bloquea(self):
        """`../../mi-proto.js` termina en proto.js, pero no es design/proto.js: es JavaScript propio."""
        bloquea, _ = self.revisar("js-mi-proto.html")
        self.assertEqual(len(bloquea), 1, bloquea)
        self.assertIn("JavaScript propio", bloquea[0])
        self.assertIn("../../mi-proto.js", bloquea[0])
        limpia = (FIXTURES / "limpia.html").read_text()
        casos = {"solo mi-proto.js": "../../mi-proto.js", "proto.js de otra carpeta": "../proto.js",
                 "proto.js con otra ruta absoluta": "/proto.js"}
        for caso, src in casos.items():
            with self.subTest(caso=caso):
                bloquea, _ = self.revisar_texto(limpia.replace('src="../../proto.js"', f'src="{src}"'))
                self.assertIn("No enlaza `proto.js` del repositorio de diseño (`design/proto.js`).", bloquea)
                self.assertTrue(any("JavaScript propio" in b and src in b for b in bloquea), bloquea)

    def test_url_javascript_es_javascript_propio(self):
        bloquea, _ = self.revisar("href-javascript.html")
        self.assertEqual(len(bloquea), 1, bloquea)
        self.assertIn("JavaScript propio", bloquea[0])
        self.assertIn("javascript:void(0)", bloquea[0])
        limpia = (FIXTURES / "limpia.html").read_text()
        casos = {"mayúsculas y espacios": '<a href="  JavaScript:alert(1)">x</a>',
                 "entidad en el esquema": '<a href="java&#x09;script:alert(1)">x</a>',
                 "en un formulario": '<form action="javascript:enviar()"><button>Enviar</button></form>'}
        for caso, html in casos.items():
            with self.subTest(caso=caso):
                bloquea, _ = self.revisar_texto(limpia.replace("<main data-frame>", "<main data-frame>\n    " + html))
                self.assertTrue(any("JavaScript propio" in b for b in bloquea), bloquea)

    def test_manejador_de_eventos_fuera_del_frame_es_javascript_propio(self):
        limpia = (FIXTURES / "limpia.html").read_text()
        bloquea, _ = self.revisar_texto(limpia.replace("<body ", '<body onload="iniciar()" '))
        self.assertTrue(any("JavaScript propio" in b and "onload" in b for b in bloquea), bloquea)

    def test_hoja_de_estilo_local_enlazada_o_importada_bloquea(self):
        """La convención enlaza solo tokens.css y components.css: otra hoja local escondería @keyframes o valores sueltos
        que el script no mira."""
        (self.design / "anim.css").write_text("@keyframes latir { 50% { opacity: .5; } }\n")
        for fixture in ("css-local-enlazado.html", "css-local-importado.html"):
            with self.subTest(fixture=fixture):
                bloquea, _ = self.revisar(fixture)
                self.assertEqual(len(bloquea), 1, bloquea)
                self.assertIn("`../../anim.css`", bloquea[0])
                self.assertIn("solo `tokens.css` y `components.css`", bloquea[0])

    def test_tokens_o_components_de_otra_ruta_no_cuentan(self):
        limpia = (FIXTURES / "limpia.html").read_text()
        bloquea, _ = self.revisar_texto(limpia.replace('href="../../tokens.css"', 'href="../../mi-tokens.css"'))
        self.assertIn("No enlaza `tokens.css` del repositorio de diseño (`design/tokens.css`).", bloquea)
        self.assertTrue(any("`../../mi-tokens.css`" in b for b in bloquea), bloquea)

    def test_keyframes_con_cualquier_prefijo_o_escapado_bloquean(self):
        bloquea, _ = self.revisar("animacion-prefijo.html")
        self.assertEqual(len([b for b in bloquea if "animación" in b]), 1, bloquea)
        animacion = (FIXTURES / "animacion.html").read_text()
        for caso, regla in {"-ms-": "@-ms-keyframes", "-khtml-": "@-khtml-keyframes", "escape CSS": "@\\6b eyframes",
                            "escape de una letra": "@ke\\yframes"}.items():
            with self.subTest(caso=caso):
                bloquea, _ = self.revisar_texto(animacion.replace("@keyframes", regla))
                self.assertTrue(any("animación" in b and "`latir`" in b for b in bloquea), bloquea)

    def compartidos(self):
        return revisar.revisar_compartidos(self.design, revisar.tokens_definidos(self.design))

    def test_import_local_en_components_o_tokens_bloquea(self):
        for archivo in ("components.css", "tokens.css"):
            with self.subTest(archivo=archivo):
                original = (self.design / archivo).read_text()
                (self.design / archivo).write_text('@import "anim.css";\n' + original)
                bloquea, _ = self.compartidos()
                (self.design / archivo).write_text(original)
                self.assertEqual(len(bloquea), 1, bloquea)
                self.assertIn(f"`{archivo}`", bloquea[0])
                self.assertIn("`anim.css`", bloquea[0])

    def test_keyframes_con_prefijo_en_components_css_bloquea(self):
        with (self.design / "components.css").open("a") as c:
            c.write("@-o-keyframes girar { to { opacity: 0; } }\n")
        bloquea, _ = self.compartidos()
        self.assertEqual(len(bloquea), 1, bloquea)
        self.assertIn("`girar`", bloquea[0])

    def test_keyframes_en_components_css_bloquea(self):
        """El components.css que dejó el subagente de componentes en eval-3 de la iteración 3 de html-a-vista."""
        shutil.copy(FIXTURES / "live-pulse" / "tokens.css", self.design / "tokens.css")
        shutil.copy(FIXTURES / "live-pulse" / "components.css", self.design / "components.css")
        bloquea, _ = self.compartidos()
        self.assertEqual(len(bloquea), 1, bloquea)
        self.assertIn("`components.css`", bloquea[0])
        self.assertIn("`live-pulse`", bloquea[0])

    def test_keyframes_en_tokens_css_bloquea(self):
        with (self.design / "tokens.css").open("a") as t:
            t.write("@keyframes girar { to { transform: rotate(1turn); } }\n")
        bloquea, _ = self.compartidos()
        self.assertEqual(len(bloquea), 1, bloquea)
        self.assertIn("`tokens.css`", bloquea[0])
        self.assertIn("`girar`", bloquea[0])

    def test_animacion_mencionada_en_un_comentario_de_components_css_no_cuenta(self):
        with (self.design / "components.css").open("a") as c:
            c.write("/* Sin @keyframes, sin @import, sin fuentes externas. */\n")
        self.assertEqual(self.compartidos(), ([], []))

    def test_recursos_externos_en_components_y_tokens_bloquean(self):
        casos = {"components.css": '@import url("https://cdn.example.net/iconos.css");\n',
                 "tokens.css": "@import url(//fonts.example.net/css2?family=Nunito);\n"}
        for archivo, linea in casos.items():
            with self.subTest(archivo=archivo):
                original = (self.design / archivo).read_text()
                (self.design / archivo).write_text(linea + original)
                bloquea, _ = self.compartidos()
                (self.design / archivo).write_text(original)
                self.assertEqual(len(bloquea), 1, bloquea)
                self.assertIn(f"`{archivo}`", bloquea[0])
                self.assertIn("recursos externos", bloquea[0])

    def test_casos_adversos_de_la_revision_final_en_la_vista(self):
        """Los casos con que la revisión final de html-a-vista intentó pasar JS, animaciones o CDN por revisar.py: cada
        uno bloquea con su motivo, y los comentarios que nombran la animación no."""
        limpia = (FIXTURES / "limpia.html").read_text()

        def head(x):
            return limpia.replace("</head>", x + "\n</head>")

        def frame(x):
            return limpia.replace("<main data-frame>", "<main data-frame>" + x)
        animacion, externo, js, hoja = "animación", "recursos externos", "JavaScript propio", "solo `tokens.css` y `components.css`"
        casos = {
            "@keyframes en <style>": (head("<style>@keyframes latir{from{opacity:1}to{opacity:.5}}</style>"), animacion),
            "-webkit-": (head("<style>@-webkit-keyframes latir {0%{opacity:1}}</style>"), animacion),
            "-o-": (head("<style>@-o-keyframes latir {0%{opacity:1}}</style>"), animacion),
            "tras un comentario": (head("<style>/* x */ @keyframes latir {0%{opacity:1}}</style>"), animacion),
            "en mayúsculas": (head("<style>@KEYFRAMES latir {0%{opacity:1}}</style>"), animacion),
            "con escape CSS": (head("<style>@\\6b eyframes latir {0%{opacity:1}}</style>"), animacion),
            "en <svg><style>": (frame("<svg><style>@keyframes g{0%{opacity:1}}</style></svg>"), animacion),
            "en <template>": (frame("<template><style>@keyframes g{0%{opacity:1}}</style></template>"), animacion),
            "en un comentario CSS": (head("<style>/* @keyframes latir { } */</style>"), None),
            "en un comentario HTML": (head("<!-- @keyframes latir { } -->"), None),
            "hoja local enlazada": (head('<link rel="stylesheet" href="../../anim.css">'), hoja),
            "hoja local importada": (head('<style>@import "../../anim.css";</style>'), hoja),
            "@import url(https://...)": (head("<style>@import url(https://cdn.example.com/x.css);</style>"), externo),
            "@import 'https://...'": (head("<style>@import 'https://cdn.example.com/x.css';</style>"), externo),
            "@import url('//...')": (head("<style>@import url('//cdn.example.com/x.css');</style>"), externo),
            "onclick en el frame": (frame('<button onclick="alert(1)">x</button>'), "Controles de prototipo"),
            "href javascript:": (frame('<a href="javascript:void(0)">x</a>'), js),
            "script module inline": (head('<script type="module">console.log(1)</script>'), js),
            "React por CDN": (head('<script src="https://cdn.example.com/react.production.min.js"></script>'), js),
            "mi-proto.js": (head('<script src="../../mi-proto.js"></script>'), js),
            "proto.js de un CDN": (head('<script src="https://cdn.example.com/proto.js"></script>'), externo),
        }
        for caso, (html, motivo) in casos.items():
            with self.subTest(caso=caso):
                bloquea, _ = self.revisar_texto(html)
                if motivo is None:
                    self.assertEqual(bloquea, [])
                else:
                    self.assertTrue(any(motivo in b for b in bloquea), bloquea)

    def test_casos_adversos_de_la_revision_final_en_los_compartidos(self):
        casos = {"@keyframes en components.css": ("components.css", "@keyframes g{0%{opacity:1}}", "animación"),
                 "comentado": ("components.css", "/* @keyframes g{0%{opacity:1}} */", None),
                 "@import url de un CDN": ("components.css", "@import url(https://cdn.example.com/x.css);", "recursos externos"),
                 "@import local": ("components.css", '@import "anim.css";', "`anim.css`"),
                 "@keyframes en tokens.css": ("tokens.css", "@keyframes g{0%{opacity:1}}", "animación"),
                 "@font-face de un CDN": ("tokens.css", "@font-face{font-family:X;src:url(https://cdn.example.com/x.woff2)}",
                                          "recursos externos")}
        for caso, (archivo, css, motivo) in casos.items():
            with self.subTest(caso=caso):
                original = (self.design / archivo).read_text()
                (self.design / archivo).write_text(original + "\n" + css + "\n")
                bloquea, _ = self.compartidos()
                (self.design / archivo).write_text(original)
                if motivo is None:
                    self.assertEqual(bloquea, [])
                else:
                    self.assertTrue(any(motivo in b and f"`{archivo}`" in b for b in bloquea), bloquea)

    def con_fuente(self, css, archivos=("fuentes/marca-regular.woff2",)):
        """Agrega `css` a tokens.css y crea en design/ los archivos de fuente nombrados; devuelve lo que bloquea."""
        for nombre in archivos:
            (self.design / nombre).parent.mkdir(parents=True, exist_ok=True)
            (self.design / nombre).write_bytes(b"wOF2")
        tokens = self.design / "tokens.css"
        tokens.write_text(tokens.read_text() + "\n" + css + "\n")
        bloquea, _ = self.compartidos()
        return bloquea

    def test_fuente_local_en_design_fuentes_no_bloquea(self):
        casos = {
            "url sin comillas": '@font-face { font-family: "Marca"; src: url(fuentes/marca-regular.woff2) format("woff2"); }',
            "url con comillas y ./": "@font-face{font-family:Marca;src:url('./fuentes/marca-regular.woff2') format('woff2');font-weight:400}",
            "nombre con espacios": ('@font-face{font-family:Marca;src:url("fuentes/Marca Regular.woff2") format("woff2")}',
                                    ("fuentes/Marca Regular.woff2",)),
        }
        for caso, css in casos.items():
            with self.subTest(caso=caso):
                self.setUp()
                if isinstance(css, tuple):
                    self.assertEqual(self.con_fuente(*css), [])
                else:
                    self.assertEqual(self.con_fuente(css), [])

    def test_fuente_mal_ubicada_o_inexistente_bloquea_nombrando_la_ruta(self):
        casos = {
            "archivo que no existe": ("@font-face{font-family:Marca;src:url(fuentes/otra.woff2)}", (), "`fuentes/otra.woff2`"),
            "fuera de fuentes/": ("@font-face{font-family:Marca;src:url(marca.woff2)}", ("marca.woff2",), "`marca.woff2`"),
            "fuera de design/": ("@font-face{font-family:Marca;src:url(../marca.woff2)}", ("../marca.woff2",), "`../marca.woff2`"),
            "otro formato": ("@font-face{font-family:Marca;src:url(fuentes/marca.ttf)}", ("fuentes/marca.ttf",), "`fuentes/marca.ttf`"),
            "embebida en data:": ("@font-face{font-family:Marca;src:url(data:font/woff2;base64,d09GMg==)}", (), "`data:"),
            "en una subcarpeta de fuentes/": ("@font-face{font-family:Marca;src:url('fuentes/marca/regular.woff2')}",
                                              ("fuentes/marca/regular.woff2",), "`fuentes/marca/regular.woff2`"),
            "con espacios y mal ubicada": ('@font-face{font-family:Marca;src:url("Marca Regular.woff2")}',
                                           ("Marca Regular.woff2",), "`Marca Regular.woff2`"),
            "segunda url mal": ("@font-face{font-family:Marca;src:url(fuentes/marca-regular.woff2) format('woff2'), url(marca.woff)}",
                                ("fuentes/marca-regular.woff2", "marca.woff"), "`marca.woff`"),
        }
        for caso, (css, archivos, ruta) in casos.items():
            with self.subTest(caso=caso):
                self.setUp()
                bloquea = self.con_fuente(css, archivos)
                self.assertTrue(any(ruta in b and "design/fuentes/" in b for b in bloquea), bloquea)

    def test_fuente_externa_sigue_bloqueando(self):
        casos = {
            "Google Fonts con @import": "@import url(https://fonts.googleapis.com/css2?family=Marca);",
            "woff2 de un CDN": "@font-face{font-family:Marca;src:url(https://fonts.example.com/marca.woff2)}",
            "sin esquema": "@font-face{font-family:Marca;src:url(//fonts.example.com/marca.woff2)}",
            "https escrito con escape": '@font-face{font-family:Marca;src:url("\\68ttps://fonts.example.com/marca.woff2")}',
            "// escrito con escapes": "@font-face{font-family:Marca;src:url(\\2f\\2f fonts.example.com/marca.woff2)}",
        }
        for caso, css in casos.items():
            with self.subTest(caso=caso):
                self.setUp()
                self.assertTrue(any("recursos externos" in b for b in self.con_fuente(css)), caso)

    def test_url_local_que_no_es_la_fuente_bloquea_en_los_compartidos(self):
        casos = {
            "imagen local en components.css": ("components.css", ".logo{background:url(img/logo.png)}", "`img/logo.png`"),
            "data: en components.css": ("components.css", ".chevron{background:url('data:image/svg+xml;utf8,<svg/>')}", "`data:"),
            "imagen local en tokens.css": ("tokens.css", ":root{--x:1px} .fondo{background:url(fondo.jpg)}", "`fondo.jpg`"),
        }
        for caso, (archivo, css, ruta) in casos.items():
            with self.subTest(caso=caso):
                self.setUp()
                (self.design / archivo).write_text((self.design / archivo).read_text() + "\n" + css + "\n")
                bloquea, _ = self.compartidos()
                self.assertTrue(any(ruta in b and f"`{archivo}`" in b for b in bloquea), bloquea)

    def test_url_a_un_id_del_documento_no_bloquea(self):
        """`url(#degradado)` apunta a un SVG de la misma página, no a un archivo."""
        comp = self.design / "components.css"
        comp.write_text(comp.read_text() + "\n.grafico path{fill:url(#degradado)}\n")
        bloquea, _ = self.compartidos()
        self.assertEqual(bloquea, [])

    def test_font_face_en_components_css_bloquea(self):
        """El `@font-face` va solo en `tokens.css`, aunque la fuente esté bien ubicada."""
        (self.design / "fuentes").mkdir()
        (self.design / "fuentes" / "marca-regular.woff2").write_bytes(b"wOF2")
        comp = self.design / "components.css"
        comp.write_text(comp.read_text() + "\n@font-face{font-family:Marca;src:url(fuentes/marca-regular.woff2)}\n")
        bloquea, _ = self.compartidos()
        self.assertTrue(any("`components.css`" in b and "@font-face" in b and "tokens.css" in b for b in bloquea), bloquea)

    def test_font_face_en_la_vista_bloquea(self):
        limpia = (FIXTURES / "limpia.html").read_text()
        casos = {
            "archivo local": "@font-face{font-family:Marca;src:url(../../marca.ttf)}",
            "embebida": "@font-face{font-family:Marca;src:url(data:font/woff2;base64,d09GMg==)}",
            "la de design/fuentes": "@font-face{font-family:Marca;src:url(../../fuentes/marca-regular.woff2)}",
        }
        for caso, css in casos.items():
            with self.subTest(caso=caso):
                bloquea, _ = self.revisar_texto(limpia.replace("</head>", f"<style>{css}</style>\n</head>"))
                self.assertTrue(any("@font-face" in b and "tokens.css" in b for b in bloquea), bloquea)

    def test_tokens_y_components_de_la_skill_pasan_sin_bloqueos(self):
        shutil.copy(ASSETS / "tokens.css", self.design / "tokens.css")
        shutil.copy(ASSETS / "components.css", self.design / "components.css")
        bloquea, _ = self.compartidos()
        self.assertEqual(bloquea, [])

    CLASES_SIN_DEFINIR = "Usa clases que `components.css` no define"

    def clases_sin_definir(self, bloquea):
        return [b for b in bloquea if self.CLASES_SIN_DEFINIR in b]

    def test_clase_que_components_css_no_define_bloquea(self):
        """Q108: una vista nueva de un repositorio de diseño viejo usa `.modal` y `.toast-region` sin regla."""
        bloquea, _ = self.revisar("clases-sin-definir.html")
        self.assertEqual(len(bloquea), 1, bloquea)
        self.assertIn(self.CLASES_SIN_DEFINIR, bloquea[0])
        for clase in ("`.modal`", "`.modal__dialog`", "`.toast-region`"):
            self.assertIn(clase, bloquea[0])
        self.assertNotIn("`.card`", bloquea[0])

    def test_clases_de_los_assets_de_la_skill_no_bloquean(self):
        shutil.copy(ASSETS / "tokens.css", self.design / "tokens.css")
        shutil.copy(ASSETS / "components.css", self.design / "components.css")
        bloquea, _ = self.revisar("clases-sin-definir.html")
        self.assertEqual(self.clases_sin_definir(bloquea), [])

    def test_clase_definida_en_cualquier_parte_de_un_selector_de_components_css_no_bloquea(self):
        """Una clase cuenta como definida si aparece en el selector de alguna regla de `components.css`, también como
        contexto, con pseudoclase, compuesta, dentro de `:where()`, `@media` o `@layer`, o escrita con escapes."""
        comp = self.design / "components.css"
        comp.write_text(comp.read_text() + "\n".join([
            ".lista .fila { padding: var(--space-2); }",
            ".chip:hover, .chip--activo::after { color: var(--color-text); }",
            ".aviso.aviso--grave > p { color: var(--color-danger); }",
            ":where(.marco) { padding: var(--space-2); }",
            "@media (min-width: 600px) { .columnas { display: grid; } }",
            "@layer base { .base { margin: 0; } }",
            ".w-1\\/2 { width: 50%; }",
            ".\\31 col { display: block; }",
        ]) + "\n")
        limpia = (FIXTURES / "limpia.html").read_text()
        clases = "lista fila chip chip--activo aviso aviso--grave marco columnas base w-1/2 1col"
        bloquea, _ = self.revisar_texto(limpia.replace('<ul class="card"', f'<ul class="card {clases}"'))
        self.assertEqual(self.clases_sin_definir(bloquea), [])

    def test_clase_definida_en_el_style_de_la_vista_no_bloquea(self):
        """Los estilos propios de una vista van en su `<style>`: una clase que define ahí está definida."""
        limpia = (FIXTURES / "limpia.html").read_text()
        html = limpia.replace("</head>", "<style>.resumen { padding: var(--space-2); }</style>\n</head>")
        bloquea, _ = self.revisar_texto(html.replace('<ul class="card"', '<ul class="card resumen"'))
        self.assertEqual(bloquea, [])

    def test_clase_que_solo_nombra_un_comentario_o_tokens_css_bloquea(self):
        """Un comentario no define una clase, ni en `components.css` ni en el `<style>` de la vista, y `tokens.css` no
        es donde viven los componentes: ante la duda, bloquea."""
        comp = self.design / "components.css"
        comp.write_text(comp.read_text() + "/* .comentada { } */\n")
        tok = self.design / "tokens.css"
        tok.write_text(tok.read_text() + ".en-tokens { color: var(--color-text); }\n")
        limpia = (FIXTURES / "limpia.html").read_text()
        html = limpia.replace("</head>", "<style>/* .en-comentario { } */</style>\n</head>")
        html = html.replace('<ul class="card"', '<ul class="card comentada en-tokens en-comentario"')
        bloquea = self.clases_sin_definir(self.revisar_texto(html)[0])
        self.assertEqual(len(bloquea), 1, bloquea)
        for clase in ("`.comentada`", "`.en-comentario`", "`.en-tokens`"):
            self.assertIn(clase, bloquea[0])

    def test_clase_usada_en_svg_template_o_body_cuenta_y_en_un_comentario_html_no(self):
        limpia = (FIXTURES / "limpia.html").read_text()
        html = limpia.replace("<body ", '<body class="pagina" ').replace(
            "<main data-frame>", '<main data-frame>\n<svg class="icono"></svg><template><p class="plantilla">x</p></template>'
            '\n<!-- <p class="solo-comentario">x</p> -->')
        bloquea = self.clases_sin_definir(self.revisar_texto(html)[0])
        self.assertEqual(len(bloquea), 1, bloquea)
        for clase in ("`.pagina`", "`.icono`", "`.plantilla`"):
            self.assertIn(clase, bloquea[0])
        self.assertNotIn("solo-comentario", bloquea[0])

    def test_solo_spec_resumen_con_spec(self):
        self.assertTrue(self.resumen("spec-sin-tickets.html").startswith("Spec: specs/pedidos/spec.md · "))

    def test_limpia_resumen_con_tickets(self):
        self.assertTrue(self.resumen("limpia.html").startswith("Tickets: DEMO-1 · "))


if __name__ == "__main__":
    unittest.main()
