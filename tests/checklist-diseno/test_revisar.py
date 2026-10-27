"""Pruebas de skills/checklist-diseno/scripts/revisar.py.

Cada fixture es una vista mínima con un caso que el script ya resolvió mal una vez.
Uso: python3 -m unittest discover -s tests/checklist-diseno -v
"""
import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "skills" / "checklist-diseno" / "scripts" / "revisar.py"
PROTO = RAIZ / "skills" / "spec-a-html" / "assets" / "proto.js"
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

    def revisar(self, fixture):
        vista = self.design / "vistas" / "pedidos" / fixture
        shutil.copy(FIXTURES / fixture, vista)
        _, _, _, bloquea, avisa = revisar.revisar_vista(vista, self.repo, revisar.tokens_definidos(self.design))
        return bloquea, avisa

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


if __name__ == "__main__":
    unittest.main()
