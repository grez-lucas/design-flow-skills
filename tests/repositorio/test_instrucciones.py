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


if __name__ == "__main__":
    unittest.main()
