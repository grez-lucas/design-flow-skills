"""Pruebas de los grade.py de pruebas/: una corrida vacía o sin informe falla entera.

Uso: python3 -m unittest discover -s tests/pruebas -v
"""
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PRUEBAS = Path(__file__).resolve().parents[2] / "pruebas"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
REQUERIDO = {"checklist-diseno": "informe.md", "grilling-es": "transcripcion.md",
             "spec-a-html": "notas.md", "spec-a-tickets": "notas.md"}


class CorridaSinSalidas(unittest.TestCase):
    def preparar(self, skill):
        it = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, it)
        subprocess.run([sys.executable, str(PRUEBAS / "preparar.py"), skill, str(it)], check=True, capture_output=True)
        return it

    def calificar(self, skill, it):
        r = subprocess.run([sys.executable, str(PRUEBAS / skill / "grade.py"), str(it)], capture_output=True, text=True)
        notas = {p.relative_to(it).parent.as_posix(): json.loads(p.read_text()) for p in it.glob("*/*/run-*/grading.json")}
        return r, notas

    def test_corrida_vacia_o_sin_informe_falla_entera(self):
        for skill, requerido in REQUERIDO.items():
            with self.subTest(skill=skill):
                it = self.preparar(skill)
                prueba = sorted(it.iterdir())[0]
                (prueba / "with_skill" / "run-1" / "outputs" / requerido).write_text("Salida de la corrida.\n")
                (prueba / "with_skill" / "run-2" / "outputs").mkdir(parents=True)
                r, notas = self.calificar(skill, it)
                self.assertNotEqual(r.returncode, 0, r.stdout)
                for corrida in (f"{prueba.name}/with_skill/run-2", f"{prueba.name}/without_skill/run-1"):
                    self.assertIn("error", notas[corrida], corrida)
                    self.assertEqual(notas[corrida]["summary"]["passed"], 0, corrida)
                    self.assertEqual(notas[corrida]["expectations"], [], corrida)
                self.assertNotIn("error", notas[f"{prueba.name}/with_skill/run-1"])

    def test_iteracion_sin_corridas_falla(self):
        for skill in REQUERIDO:
            with self.subTest(skill=skill):
                it = Path(tempfile.mkdtemp())
                self.addCleanup(shutil.rmtree, it)
                r, _ = self.calificar(skill, it)
                self.assertNotEqual(r.returncode, 0)


def secciones(informe):
    """Devuelve (líneas fuera de secciones de severidad, [(etiqueta, [ítems])]) en orden, para reescribir el informe."""
    out, actual = [], None
    for linea in informe.splitlines():
        if linea in ("Bloquea:", "Conviene mirar:"):
            actual = (linea, [])
            out.append(actual)
        elif actual and linea.startswith("- "):
            actual[1].append(linea[2:])
        else:
            actual = None
            out.append(linea)
    return out


def reescribir(informe, forma):
    lineas = []
    for x in secciones(informe):
        if isinstance(x, str):
            lineas.append(x)
            continue
        etiqueta, its = x
        bloquea = etiqueta == "Bloquea:"
        if forma == "tabla":
            lineas += ["| Hallazgo | Severidad |", "| :--- | :--- |"]
            lineas += [f"| {i} | {'Bloquea' if bloquea else 'Aviso'} |" for i in its]
        elif forma == "viñeta" and bloquea:
            lineas += [f"- **Bloquea:** {i}" for i in its]
        else:
            nueva = {"original": etiqueta, "encabezado": "### Bloqueos" if bloquea else "### Conviene mirar",
                     "negrita": "**Bloqueantes**" if bloquea else "**Conviene mirar**", "viñeta": etiqueta}[forma]
            lineas += [nueva] + [f"- {i}" for i in its]
    return "\n".join(lineas) + "\n"


class SeveridadSinFormatoFijo(unittest.TestCase):
    def test_mismo_informe_en_cinco_formas_da_el_mismo_puntaje(self):
        informe = (FIXTURES / "informe-checklist.md").read_text()
        it = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, it)
        subprocess.run([sys.executable, str(PRUEBAS / "preparar.py"), "checklist-diseno", str(it)], check=True, capture_output=True)
        base = it / "eval-1-defectos" / "with_skill"
        formas = ["original", "encabezado", "viñeta", "tabla", "negrita"]
        for n, forma in enumerate(formas, start=2):
            shutil.copytree(base / "run-1", base / f"run-{n}", symlinks=True)
            (base / f"run-{n}" / "outputs" / "informe.md").write_text(reescribir(informe, forma))
        shutil.rmtree(it / "eval-1-defectos" / "without_skill")
        for otra in it.iterdir():
            if otra.name != "eval-1-defectos":
                shutil.rmtree(otra)
        (base / "run-1" / "outputs" / "informe.md").write_text(informe)
        subprocess.run([sys.executable, str(PRUEBAS / "checklist-diseno" / "grade.py"), str(it)], check=True, capture_output=True)
        resultados = {}
        for n, forma in enumerate(["sin reescribir"] + formas, start=1):
            g = json.loads((base / f"run-{n}" / "grading.json").read_text())
            resultados[forma] = [(e["text"], e["passed"]) for e in g["expectations"]]
        esperado = resultados.pop("sin reescribir")
        self.assertEqual(sum(p for t, p in esperado if t.startswith("Lo marca como bloqueo")), 6)
        for forma, r in resultados.items():
            self.assertEqual(r, esperado, forma)


def cargar(skill):
    spec = importlib.util.spec_from_file_location(f"grade_{skill.replace('-', '_')}", PRUEBAS / skill / "grade.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


ESTADOS_EN_LINEA = """## Estados por vista

- Listado: normal, vacío (sin facturas), cargando, error, sin permiso (no aplica), muchos datos (pendiente: equipo técnico).

## Reglas
"""
ESTADOS_EN_SUBLISTA = """## Estados por vista

- Listado:
  - normal
  - vacío: sin facturas
  - cargando
  - error
  - sin permiso: no aplica
  - muchos datos: pendiente, equipo técnico

## Reglas
"""


class EstadosBaseDeGrilling(unittest.TestCase):
    def test_estados_en_la_misma_linea_o_en_sublista(self):
        grade = cargar("grilling-es")
        for spec in (ESTADOS_EN_LINEA, ESTADOS_EN_SUBLISTA):
            estados = [r for r in grade.extra_checks(spec) if r["text"].startswith("Cada vista declara")][0]
            self.assertTrue(estados["passed"], estados["evidence"])


if __name__ == "__main__":
    unittest.main()
