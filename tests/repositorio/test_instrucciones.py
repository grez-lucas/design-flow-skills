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
    """Las variables CSS de la parte del producto que se diseña van antes que las del framework. Las regex toman la
    oración entera que fija la decisión, para que una negación no pase."""

    def setUp(self):
        texto = (SKILLS / "spec-a-html" / "references" / "design-system.md").read_text(encoding="utf-8")
        self.extraer = seccion(texto, "Extraer del código", 2)
        self.antes_de_la_tabla = self.extraer.split("| Stack")[0]

    def test_busca_las_variables_css_de_la_zona_antes_de_la_tabla_por_framework(self):
        self.assertIn("| Stack", self.extraer)
        self.assertRegex(self.antes_de_la_tabla, r"Mira primero la parte del producto que se diseña, no el producto entero:")
        self.assertRegex(self.antes_de_la_tabla, r"Busca variables CSS \(`--\*`\) en las hojas globales y en los componentes de esa parte")
        self.assertRegex(self.antes_de_la_tabla, r"Si las hay, son el design system de esa parte, antes que las del framework:")

    def test_con_variables_propias_igual_compara_con_el_tema_del_framework(self):
        self.assertRegex(self.antes_de_la_tabla, r"Aunque haya variables propias, mira también el tema del framework[^.]*para compararlo")

    def test_pide_confirmar_la_fuente_cuando_hay_mas_de_una(self):
        self.assertRegex(self.antes_de_la_tabla, r"Cuando hay más de una fuente \([^)]*\), muestra a la persona de dónde sale "
                                                 r"cada valor y pídele que confirme de qué parte del producto sale el design system")


class CapturasEnSpecAHtml(unittest.TestCase):
    """Con navegador, capturas por escenario y ancho, revisadas contra el spec antes de pedir el visto bueno. Las regex
    toman la oración entera que fija la decisión, para que una negación no pase."""

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
            self.assertRegex(comando, r"--window-size=<ancho>,\d+ ")
            self.assertIn("?escenario=<escenario>", comando)
            self.assertIn("proto=0", comando)

    def test_las_vistas_largas_se_capturan_enteras(self):
        self.assertRegex(self.capturas, r"Si la vista es más larga que la ventana[^.]*repite la captura con `--window-size=<ancho>,3000`")
        self.assertIn("full_page=True", self.capturas)

    def test_dice_como_saber_si_hay_navegador(self):
        self.assertIn("command -v google-chrome chromium chromium-browser", self.capturas)
        self.assertRegex(self.capturas, r"python3 -c \"import playwright\"")

    def test_las_capturas_quedan_en_la_carpeta_de_trabajo_fuera_del_repositorio(self):
        destinos = re.findall(r"--screenshot=(\S+)", self.capturas)
        self.assertTrue(destinos)
        for destino in destinos:
            self.assertTrue(destino.startswith("<trabajo>/"), destino)
        self.assertRegex(self.capturas, r"en una carpeta de trabajo fuera del repositorio[^.]*para que no entren al commit")

    def test_con_navegador_son_obligatorias_y_se_revisan_contra_el_spec(self):
        self.assertRegex(self.capturas, r"Con navegador en la sesión \([^)]*\), las capturas son obligatorias antes de mostrarle la vista a la persona\.")
        self.assertRegex(self.capturas, r"Mira cada captura y revísala contra el spec:")

    def test_un_cambio_en_un_archivo_compartido_se_vuelve_a_capturar_en_todas_las_vistas(self):
        self.assertRegex(self.capturas, r"Si corregiste `components\.css` o `tokens\.css`, vuelve a capturar todas las vistas")

    def test_el_tema_oscuro_se_captura_solo_si_hay_bloque_oscuro(self):
        self.assertRegex(self.capturas, r'Si `tokens\.css` define `\[data-theme="dark"\]`, repite cada escenario en un ancho con `&tema=oscuro`')

    def test_sin_navegador_lo_dice_y_sigue(self):
        self.assertRegex(self.capturas, r"Sin navegador en la sesión, dilo en una línea[^.]*y sigue\.")


class DatosFueraDelSpecEnElChecklist(unittest.TestCase):
    """El checklist tiene un paso explícito, y uno solo, para datos o textos de la vista que el spec no menciona."""

    def setUp(self):
        texto = (SKILLS / "checklist-diseno" / "SKILL.md").read_text(encoding="utf-8")
        self.vinetas = [l for l in seccion(texto, "Revisión de criterio", 3).splitlines() if l.startswith("- **")]

    def vineta(self, titulo):
        encontradas = [l for l in self.vinetas if l.startswith(f"- **{titulo}**")]
        self.assertEqual(len(encontradas), 1, f"no hay una viñeta {titulo!r}: {[l[:40] for l in self.vinetas]}")
        return encontradas[0]

    def test_la_revision_de_criterio_busca_datos_y_textos_que_el_spec_no_menciona(self):
        paso = self.vineta("Datos o textos fuera del spec")
        self.assertRegex(paso, r"Un dato que el spec no menciona \([^)]*\) bloquea:")
        self.assertRegex(paso, r"Un texto que contradice al spec o a otro texto del mismo escenario \([^)]*\) también bloquea\.")
        self.assertRegex(paso, r"Ante la duda, bloquea y se pregunta en la planificación\.")

    def test_lo_que_sobra_deja_los_datos_al_paso_de_datos_o_textos(self):
        sobra = self.vineta("Lo que sobra")
        self.assertNotIn("columna", sobra)
        self.assertRegex(sobra, r"Los datos y los textos se revisan en \"Datos o textos fuera del spec\"\.")

    def test_la_verosimilitud_de_los_datos_no_se_confunde_con_el_paso_de_datos_fuera_del_spec(self):
        self.assertFalse([l for l in self.vinetas if l.startswith("- **Datos**")])
        self.vineta("Datos ficticios")


if __name__ == "__main__":
    unittest.main()
