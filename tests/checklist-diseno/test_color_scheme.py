"""Pruebas del aviso de revisar.py sobre el tema base oscuro sin `color-scheme: dark`.

El tema base es el de `:root` en `tokens.css`. Es oscuro cuando `--color-bg` tiene menos luminancia relativa que
`--color-text`. Sin `color-scheme: dark` en ese bloque, Chrome dibuja claras las barras de desplazamiento y los
controles nativos sobre el fondo oscuro.
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
ASSETS = RAIZ / "skills" / "spec-a-html" / "assets"

spec = importlib.util.spec_from_file_location("revisar_color_scheme", SCRIPT)
revisar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(revisar)

OSCURO = "--color-bg: #0f1216;\n  --color-text: #e8ebef;"
CLARO = "--color-bg: #f7f8fa;\n  --color-text: #1b1f24;"


class TemaBaseOscuro(unittest.TestCase):
    def setUp(self):
        self.repo = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.repo)
        self.design = self.repo / "design"
        self.design.mkdir()
        (self.design / "components.css").write_text("/* sin componentes: la prueba mira solo tokens.css */\n")
        shutil.copy(ASSETS / "proto.js", self.design / "proto.js")

    def avisos(self, tokens):
        (self.design / "tokens.css").write_text(tokens)
        bloquea, avisa = revisar.revisar_compartidos(self.design, revisar.tokens_definidos(self.design))
        return [a for a in avisa if "color-scheme" in a], bloquea

    def test_avisa_si_el_tema_base_es_oscuro_sin_color_scheme_dark(self):
        casos = {
            "sin color-scheme": f":root {{\n  {OSCURO}\n}}\n",
            "light dark deja elegir el claro": f":root {{\n  color-scheme: light dark;\n  {OSCURO}\n}}\n",
            "dark light también": f":root {{\n  color-scheme: dark light;\n  {OSCURO}\n}}\n",
            "light": f":root {{\n  color-scheme: light;\n  {OSCURO}\n}}\n",
            "solo en un comentario": f":root {{\n  /* color-scheme: dark; */\n  {OSCURO}\n}}\n",
            "solo en otro bloque": f':root {{\n  {OSCURO}\n}}\n[data-theme="dark"] {{\n  color-scheme: dark;\n}}\n',
            "rgb y hsl": ":root {\n  --color-bg: rgb(15 18 22);\n  --color-text: hsl(210, 20%, 92%);\n}\n",
            "hex corto": ":root {\n  --color-bg: #000;\n  --color-text: #fff;\n}\n",
            "oklch": ":root {\n  --color-bg: oklch(0.2 0.01 250);\n  --color-text: oklch(0.95 0 0);\n}\n",
            "oklch en porcentaje": ":root {\n  --color-bg: oklch(20% 0.01 250);\n  --color-text: oklch(95% 0 0);\n}\n",
            "oklab": ":root {\n  --color-bg: oklab(0.2 0 -0.01);\n  --color-text: oklab(0.95 0 0);\n}\n",
            "oklch contra hex": ":root {\n  --color-bg: oklch(0.2 0.01 250);\n  --color-text: #e8ebef;\n}\n",
            "black y white": ":root {\n  --color-bg: black;\n  --color-text: White;\n}\n",
            "hsl con turn": ":root {\n  --color-bg: hsl(0.5turn 20% 8%);\n  --color-text: hsl(180deg 10% 95%);\n}\n",
            "fondo con !important": ":root {\n  --color-bg: #000 !important;\n  --color-text: #fff;\n}\n",
            "color-scheme dark de otro bloque con !important": f':root {{\n  {OSCURO}\n}}\n[data-theme="dark"] {{ color-scheme: dark !important; }}\n',
            ":root dentro de @layer": "@layer base {\n  :root {\n    --color-bg: #0f1216;\n    --color-text: #e8ebef;\n  }\n}\n",
            "html:root": "html:root {\n  --color-bg: #0f1216;\n  --color-text: #e8ebef;\n}\n",
            "el último valor manda": f":root {{\n  color-scheme: dark;\n  {OSCURO}\n  color-scheme: light dark;\n}}\n",
            "el último bloque manda": f":root {{\n  {CLARO}\n}}\n:root {{\n  {OSCURO}\n}}\n",
        }
        for caso, tokens in casos.items():
            with self.subTest(caso=caso):
                avisos, bloquea = self.avisos(tokens)
                self.assertEqual(len(avisos), 1, avisos)
                self.assertIn("`color-scheme: dark`", avisos[0])
                self.assertIn("`tokens.css`", avisos[0])
                self.assertEqual(bloquea, [])

    def test_no_avisa_si_el_tema_base_es_oscuro_con_color_scheme_dark(self):
        casos = {
            "dark": f":root {{\n  color-scheme: dark;\n  {OSCURO}\n}}\n",
            "only dark": f":root {{\n  color-scheme: only dark;\n  {OSCURO}\n}}\n",
            "mayúsculas y sin espacios": f":root{{COLOR-SCHEME:Dark;{OSCURO}}}\n",
            "en un bloque :root aparte": f":root {{\n  {OSCURO}\n}}\n:root {{ color-scheme: dark; }}\n",
            "en html": f":root {{\n  {OSCURO}\n}}\nhtml {{ color-scheme: dark; }}\n",
            "con !important": f":root {{\n  color-scheme: dark !important;\n  {OSCURO}\n}}\n",
            "only dark con !important": f":root {{\n  color-scheme: only dark!important;\n  {OSCURO}\n}}\n",
            "dentro de @layer": f"@layer base {{\n  :root {{\n    color-scheme: dark;\n    {OSCURO}\n  }}\n}}\n",
            "en html:root": f"html:root {{\n  color-scheme: dark;\n  {OSCURO}\n}}\n",
        }
        for caso, tokens in casos.items():
            with self.subTest(caso=caso):
                self.assertEqual(self.avisos(tokens)[0], [])

    def test_no_avisa_si_el_tema_base_es_claro(self):
        casos = {
            "sin color-scheme": f":root {{\n  {CLARO}\n}}\n",
            "con un tema oscuro opcional sin color-scheme": f':root {{\n  {CLARO}\n}}\n[data-theme="dark"] {{\n  {OSCURO}\n}}\n',
            "oklch claro": ":root {\n  --color-bg: oklch(0.98 0.01 250);\n  --color-text: oklch(0.2 0 0);\n}\n",
            "white y black": ":root {\n  --color-bg: white;\n  --color-text: black;\n}\n",
            "oscuro solo en un @layer anidado en @media": f":root {{\n  {CLARO}\n}}\n@media (prefers-color-scheme: dark) {{\n  @layer base {{\n    :root {{\n      {OSCURO}\n    }}\n  }}\n}}\n",
            "oscuro solo con prefers-color-scheme": f":root {{\n  {CLARO}\n}}\n@media (prefers-color-scheme: dark) {{\n  :root {{\n    {OSCURO}\n  }}\n}}\n",
        }
        for caso, tokens in casos.items():
            with self.subTest(caso=caso):
                self.assertEqual(self.avisos(tokens)[0], [])

    def test_avisa_si_no_puede_comprobar_el_tema_base(self):
        """Sin un fondo y un texto que se puedan leer no hay cómo saber si el tema base es oscuro: avisa, sin bloquear."""
        casos = {
            "sin --color-bg": ":root {\n  --color-text: #e8ebef;\n}\n",
            "sin --color-text": ":root {\n  --color-bg: #0f1216;\n}\n",
            "sin ninguno de los dos": ":root {\n  --space-2: 8px;\n}\n",
            "fondo con var()": ":root {\n  --color-bg: var(--color-surface);\n  --color-text: #e8ebef;\n}\n",
            "texto con var()": ":root {\n  --color-bg: #0f1216;\n  --color-text: var(--color-ink);\n}\n",
            "un color con nombre que no lee": ":root {\n  --color-bg: navy;\n  --color-text: #e8ebef;\n}\n",
            "con color-scheme light": ":root {\n  color-scheme: light;\n  --color-bg: var(--color-surface);\n  --color-text: #e8ebef;\n}\n",
        }
        for caso, tokens in casos.items():
            with self.subTest(caso=caso):
                avisos, bloquea = self.avisos(tokens)
                self.assertEqual(len(avisos), 1, avisos)
                self.assertIn("no puede comprobar", avisos[0])
                self.assertIn("`--color-bg`", avisos[0])
                self.assertIn("`--color-text`", avisos[0])
                self.assertEqual(bloquea, [])

    def test_no_avisa_si_no_puede_comprobarlo_pero_declara_color_scheme_dark(self):
        tokens = ":root {\n  color-scheme: dark;\n  --color-bg: var(--color-surface);\n  --color-text: #e8ebef;\n}\n"
        self.assertEqual(self.avisos(tokens)[0], [])

    def test_la_plantilla_declara_color_scheme_en_cada_tema(self):
        tokens = revisar.strip_comments((ASSETS / "tokens.css").read_text())
        self.assertEqual(revisar.color_scheme(tokens, (":root", "html")), "light")
        self.assertEqual(revisar.color_scheme(tokens, ('[data-theme="dark"]',)), "dark")
        avisos, bloquea = self.avisos((ASSETS / "tokens.css").read_text())
        self.assertEqual((avisos, bloquea), ([], []))


if __name__ == "__main__":
    unittest.main()
