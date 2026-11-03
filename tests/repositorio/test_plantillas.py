"""Pruebas de las plantillas de spec (grilling-es) y de story (spec-a-tickets): el formato de los escenarios.

La historia va como **COMO** / **QUIERO** / **PARA**, cada criterio como `### Escenario N: <nombre>` con un bloque
`gherkin` en español, y el spec cierra con la tabla `## Escenarios en pantalla`, que revisar.py lee sin errores. El
ejemplo de story copia tal cual los escenarios de su historia en el ejemplo de spec, y no lleva la tabla.
Uso: python3 -m unittest discover -s tests/repositorio -v
"""
import importlib.util
import re
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SKILLS = RAIZ / "skills"
PLANTILLA_SPEC = SKILLS / "grilling-es" / "references" / "plantilla-spec.md"
PLANTILLA_STORY = SKILLS / "spec-a-tickets" / "references" / "plantilla-story.md"

spec = importlib.util.spec_from_file_location("revisar", SKILLS / "checklist-diseno" / "scripts" / "revisar.py")
revisar = importlib.util.module_from_spec(spec)
sys.modules["revisar"] = revisar
spec.loader.exec_module(revisar)

ESCENARIO = re.compile(r"^### Escenario \d+: .+\n\n```gherkin\n(?:.+\n)+?```$", re.M)
PASO = re.compile(r"^(Dado|Cuando|Entonces|Y|Esquema del escenario|Ejemplos)\b")


def bloque(texto, titulo):
    """El primer bloque cercado `markdown` después del encabezado `titulo`, cerrado por una cerca igual."""
    resto = texto.split(titulo, 1)[1]
    m = re.search(r"^(`{3,})markdown\n(.*?)^\1$", resto, flags=re.M | re.S)
    if not m:
        raise AssertionError(f"no hay bloque markdown después de {titulo!r}")
    return m.group(2)


def historia(texto, id_historia):
    """Desde el encabezado de la historia hasta el siguiente `### <ID> ·` o `## `."""
    resto = texto.split(f"### {id_historia} ·", 1)[1]
    fin = re.search(r"^(### [A-Z]+-[A-Z]+-\d+ ·|## )", resto, flags=re.M)
    return resto[:fin.start()] if fin else resto


class PlantillaDelSpec(unittest.TestCase):
    def setUp(self):
        texto = PLANTILLA_SPEC.read_text(encoding="utf-8")
        self.plantilla = bloque(texto, "## Plantilla")
        self.ejemplo = bloque(texto, "## Ejemplo corto")

    def test_la_plantilla_cierra_con_la_tabla_de_escenarios_en_pantalla(self):
        secciones = re.findall(r"^## .+$", self.plantilla, flags=re.M)
        self.assertEqual(secciones[-1], "## Escenarios en pantalla")
        self.assertIn("| Slug | Nombre | Alcance |", self.plantilla.split("## Escenarios en pantalla")[1])

    def test_la_plantilla_usa_como_quiero_para_y_escenarios_gherkin(self):
        self.assertRegex(self.plantilla, r"(?m)^\*\*COMO\*\* <rol>\n\*\*QUIERO\*\* <capacidad>\n\*\*PARA\*\* <beneficio>$")
        self.assertRegex(self.plantilla, r"(?m)^### Escenario 1: <nombre>\n\n```gherkin\nDado ")

    def test_el_ejemplo_tiene_tabla_que_revisar_lee_sin_errores(self):
        leido = revisar.leer_spec(self.ejemplo)
        self.assertTrue(leido["tabla"], leido)
        self.assertEqual(leido["errores"], [])
        self.assertEqual(re.findall(r"^## .+$", self.ejemplo, flags=re.M)[-1], "## Escenarios en pantalla")

    def test_cada_historia_del_ejemplo_tiene_como_quiero_para_y_escenarios_gherkin(self):
        ids = re.findall(r"^### ([A-Z]+-[A-Z]+-\d+) ·", self.ejemplo, flags=re.M)
        self.assertTrue(ids)
        for id_historia in ids:
            with self.subTest(historia=id_historia):
                cuerpo = historia(self.ejemplo, id_historia)
                self.assertRegex(cuerpo, r"(?m)^\*\*COMO\*\* .+\n\*\*QUIERO\*\* .+\n\*\*PARA\*\* .+$")
                escenarios = ESCENARIO.findall(cuerpo)
                self.assertEqual(len(escenarios), len(re.findall(r"^### Escenario", cuerpo, flags=re.M)))
                self.assertTrue(escenarios)
                for e in escenarios:
                    pasos = e.split("```gherkin\n", 1)[1].rsplit("```", 1)[0].splitlines()
                    self.assertTrue(all(PASO.match(p) for p in pasos), pasos)
                    self.assertTrue({"Dado", "Cuando", "Entonces"} <= {p.split()[0] for p in pasos}, pasos)


class ReglasDeLaPlantillaDelSpec(unittest.TestCase):
    def setUp(self):
        self.reglas = PLANTILLA_SPEC.read_text(encoding="utf-8").split("## Reglas de redacción", 1)[1].split("\n## ", 1)[0]

    def test_el_esquema_del_escenario_va_bajo_su_encabezado(self):
        self.assertRegex(self.reglas, r"(?m)^  ### Escenario \d+: Recordatorio según atraso\n\n  ```gherkin\n  Esquema del escenario: Recordatorio según atraso$")

    def test_la_seccion_de_escenarios_en_pantalla_va_siempre_con_su_tabla(self):
        self.assertRegex(self.reglas, r"`## Escenarios en pantalla` va siempre, con la tabla aunque sea solo el encabezado")


class PlantillaDeLaStory(unittest.TestCase):
    def setUp(self):
        texto = PLANTILLA_STORY.read_text(encoding="utf-8")
        self.plantilla = bloque(texto, "## Plantilla")
        self.ejemplo = bloque(texto, "## Ejemplo")
        self.spec = bloque(PLANTILLA_SPEC.read_text(encoding="utf-8"), "## Ejemplo corto")

    def test_la_plantilla_usa_como_quiero_para_y_escenarios_gherkin(self):
        self.assertRegex(self.plantilla, r"(?m)^\*\*COMO\*\* <rol>\n\*\*QUIERO\*\* <capacidad>\n\*\*PARA\*\* <beneficio>$")
        criterios = self.plantilla.split("## ✅ Acceptance Criteria", 1)[1].split("\n## ", 1)[0]
        self.assertRegex(criterios, r"(?m)^### Escenario 1: <nombre>\n\n```gherkin\nDado ")

    def test_el_ejemplo_copia_tal_cual_los_escenarios_de_su_historia_en_el_spec(self):
        id_historia = re.search(r"\[(US-[A-Z]+-\d+)\]", PLANTILLA_STORY.read_text(encoding="utf-8").split("## Ejemplo", 1)[1])[1]
        del_spec = ESCENARIO.findall(historia(self.spec, id_historia))
        criterios = self.ejemplo.split("## ✅ Acceptance Criteria", 1)[1].split("\n## ", 1)[0]
        self.assertTrue(del_spec)
        self.assertEqual(ESCENARIO.findall(criterios), del_spec)

    def test_la_historia_del_ejemplo_es_la_del_spec(self):
        id_historia = re.search(r"\[(US-[A-Z]+-\d+)\]", PLANTILLA_STORY.read_text(encoding="utf-8").split("## Ejemplo", 1)[1])[1]
        como = re.search(r"^\*\*COMO\*\* .+\n\*\*QUIERO\*\* .+\n\*\*PARA\*\* .+$", historia(self.spec, id_historia), flags=re.M)
        self.assertIsNotNone(como)
        self.assertIn(como.group(0), self.ejemplo)

    def test_la_story_no_lleva_la_tabla_de_escenarios_en_pantalla(self):
        self.assertNotIn("Escenarios en pantalla", self.plantilla)
        self.assertNotIn("Escenarios en pantalla", self.ejemplo)


if __name__ == "__main__":
    unittest.main()
