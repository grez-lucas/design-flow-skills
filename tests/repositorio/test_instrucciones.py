"""Pruebas de instrucciones de las skills que fijan una decisión: el orden de un paso o un paso que no puede faltar.

Uso: python3 -m unittest discover -s tests/repositorio -v
"""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SKILLS = RAIZ / "skills"


def seccion(texto, titulo, nivel):
    """El cuerpo de la sección cuyo encabezado de `nivel` (##, ###) contiene `titulo`, hasta el siguiente del mismo
    nivel o uno mayor."""
    marca = "#" * nivel
    m = re.search(rf"^{marca} [^\n]*{re.escape(titulo)}[^\n]*\n", texto, flags=re.M)
    if not m:
        raise AssertionError(f"no hay sección {marca} con {titulo!r}")
    fin = re.search(rf"^#{{1,{nivel}}} ", texto[m.end():], flags=re.M)
    return texto[m.end():m.end() + fin.start()] if fin else texto[m.end():]


class DesignSystemDesdeLaZonaDelProducto(unittest.TestCase):
    """Issue 21: las variables CSS de la parte del producto que se diseña van antes que las del framework."""

    def setUp(self):
        texto = (SKILLS / "spec-a-html" / "references" / "design-system.md").read_text(encoding="utf-8")
        self.extraer = seccion(texto, "Extraer del código", 2)
        self.antes_de_la_tabla = self.extraer.split("| Stack")[0]

    def test_busca_las_variables_css_de_la_zona_antes_de_la_tabla_por_framework(self):
        self.assertIn("| Stack", self.extraer)
        self.assertIn("`--*`", self.antes_de_la_tabla)
        self.assertRegex(self.antes_de_la_tabla, r"parte del producto que se diseña")
        self.assertRegex(self.antes_de_la_tabla, r"antes que (las|los) del framework")

    def test_pide_confirmar_la_fuente_cuando_hay_mas_de_una(self):
        self.assertRegex(self.antes_de_la_tabla, r"más de una fuente[^.]*confirm|confirm[^.]*más de una fuente")


class CapturasEnSpecAHtml(unittest.TestCase):
    """Q89: con navegador, capturas por escenario y ancho, revisadas contra el spec antes de pedir el visto bueno."""

    def setUp(self):
        self.texto = (SKILLS / "spec-a-html" / "SKILL.md").read_text(encoding="utf-8")
        self.pasos = re.findall(r"^### (\d+)\. (.+)$", self.texto, flags=re.M)
        self.capturas = seccion(self.texto, "Capturas", 3)

    def numero(self, titulo):
        return next(int(n) for n, t in self.pasos if titulo in t)

    def test_los_pasos_estan_numerados_en_orden(self):
        self.assertEqual([int(n) for n, _ in self.pasos], list(range(1, len(self.pasos) + 1)))

    def test_las_capturas_van_despues_de_escribir_y_antes_de_la_revision_y_el_visto_bueno(self):
        capturas = self.numero("Capturas")
        self.assertLess(self.numero("Escribir el HTML"), capturas)
        self.assertLess(capturas, self.numero("Revisión con la persona"))
        self.assertLess(capturas, self.numero("Guardar"))

    def test_una_captura_por_escenario_y_ancho_sin_panel(self):
        comandos = [l for l in self.capturas.splitlines() if "--screenshot=" in l]
        self.assertTrue(comandos, "el paso no da el comando de la captura")
        for comando in comandos:
            self.assertIn("--window-size=<ancho>,", comando)
            self.assertIn("?escenario=<escenario>", comando)
            self.assertIn("proto=0", comando)

    def test_las_capturas_quedan_fuera_del_repositorio_de_diseno(self):
        for destino in re.findall(r"--screenshot=(\S+)", self.capturas):
            self.assertFalse(destino.startswith(("design/", "specs/", "<repo>")), destino)
            self.assertNotIn("/design/", destino)

    def test_con_navegador_son_obligatorias_y_se_revisan_contra_el_spec(self):
        self.assertIn("obligatorias", self.capturas)
        self.assertRegex(self.capturas, r"contra el spec")

    def test_sin_navegador_lo_dice_y_sigue(self):
        self.assertRegex(self.capturas, r"Sin navegador[^.]*dilo[^.]*sigue")


if __name__ == "__main__":
    unittest.main()
