"""Pruebas de skills/html-a-vista/scripts/aprobadas.py.

Uso: python3 -m unittest discover -s tests/html-a-vista -v
"""
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "skills" / "html-a-vista" / "scripts" / "aprobadas.py"
FIX = Path(__file__).resolve().parent / "fixtures" / "aprobadas"

spec = importlib.util.spec_from_file_location("aprobadas", SCRIPT)
aprobadas = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aprobadas)

REVISION_SIN_SEGUNDA = """# Revisión ola 3

## Hallazgo transversal (no bloquea por sí solo cada vista)
- El menú lateral del marco no llega al alto de la pantalla.

## marco - no aprobada
- Falta: menú lateral a altura completa.

## lista - aprobada
- Inventario: textos 74/443, faltantes con motivo en el contrato.

## ajustes - no aprobada
- Falta: el contenido queda desplazado frente a cuotas. Sin motivo en el contrato.
"""
REVISION_CON_SEGUNDA_VUELTA = """# Revisión de la ola 3

Resultado: 2 aprobadas (marco, lista) y 1 no aprobadas (detalle-lote).

## marco: Aprobada

## lista: Aprobada
- Los encabezados siguen la tabla de tokens aprobada.

## detalle-lote: No aprobada
- "Dar de baja" no lleva btn--primary.

## Segunda vuelta

- detalle-lote: Aprobada. "Dar de baja" lleva btn--primary.
"""
REVISION_PRIMERA_DESPUES = """# Revisión

| Vista | Veredicto |
| :--- | :--- |
| panel | aprobada (segunda revisión) |

## Panel, segunda revisión: aprobada

## Panel, primera revisión: no aprobada (lo que sigue es lo que se pidió corregir)
"""
REVISION_UNA_VISTA = """# Revisión · ola 3

## semana (`design/vistas/cosechas/semana.html`)

**Veredicto: no aprobada.** Los encabezados de la tabla. Todo lo demás está aprobado.

## Segunda revisión

**Veredicto: aprobada.**
"""
REVISION_SIN_NOMBRE = """# Revisión · ola 3 · chico.html

Veredicto: **aprobada**
"""


class Veredictos(unittest.TestCase):
    """Un solo lector de veredictos: lo usan el paso que mueve las vistas y el calificador de pruebas/html-a-vista."""

    def test_ultimo_veredicto_de_cada_vista(self):
        formato_fijo = (FIX / "revision-segunda.md").read_text()
        casos = {
            "formato fijo de la skill": (formato_fijo, ["panel", "historial"], {"panel": "aprobada", "historial": "aprobada"}),
            "revisión de eval-3, iteración 3": ((FIX / "revision-iteracion-3.md").read_text(), ["marco", "lista", "ajustes"],
                                                {"marco": "no aprobada", "lista": "aprobada", "ajustes": "aprobada"}),
            "sin segunda revisión": (REVISION_SIN_SEGUNDA, ["marco", "lista", "ajustes"],
                                     {"marco": "no aprobada", "lista": "aprobada", "ajustes": "no aprobada"}),
            "con segunda vuelta en viñetas": (REVISION_CON_SEGUNDA_VUELTA, ["marco", "lista", "detalle-lote"],
                                              {"marco": "aprobada", "lista": "aprobada", "detalle-lote": "aprobada"}),
            "primera revisión escrita después": (REVISION_PRIMERA_DESPUES, ["panel"], {"panel": "aprobada"}),
            "una vista, segunda revisión sin nombrarla": (REVISION_UNA_VISTA, ["semana"], {"semana": "aprobada"}),
            "una vista que el archivo no nombra": (REVISION_SIN_NOMBRE, ["reservas"], {"reservas": "aprobada"}),
            "vista que el revisor no nombra": (formato_fijo, ["panel", "historial", "ajustes"],
                                               {"panel": "aprobada", "historial": "aprobada", "ajustes": None}),
            "detalle no es detalle-lote": (REVISION_CON_SEGUNDA_VUELTA, ["detalle"], {"detalle": None}),
        }
        for caso, (revision, nombres, esperado) in casos.items():
            with self.subTest(caso=caso):
                self.assertEqual(aprobadas.veredictos(revision, nombres), esperado)


VISTAS_ITERACION_3 = {"semilla/marco.html", "inventario/lista.html", "socios/ajustes.html"}


class MoverAprobadas(unittest.TestCase):
    """El paso que mueve al repositorio de diseño solo lo que el revisor aprobó."""

    def setUp(self):
        base = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, base)
        self.trabajo, self.repo = base / "trabajo", base / "repo"
        self.copia = self.trabajo / "ola-3" / "repo" / "design"
        (self.repo / "design").mkdir(parents=True)
        for archivo in ("tokens.css", "components.css", "proto.js"):
            (self.repo / "design" / archivo).write_text(f"/* {archivo} del repositorio */\n")
        shutil.copytree(self.repo / "design", self.copia)
        (self.copia / "components.css").write_text("/* components.css integrado */\n")

    def vistas(self, *rutas, carpeta=None, contrato=True, inventario=True):
        """Vistas en la copia integrada, cada una con su contrato de la ola 2 y su inventario de la ola 3."""
        for ruta in rutas:
            destino = (carpeta or self.copia) / "vistas" / ruta
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(f"<!doctype html><title>{ruta}</title>\n")
            if carpeta:
                continue
            nombre = Path(ruta).stem
            if contrato:
                (self.trabajo / "ola-2" / nombre).mkdir(parents=True, exist_ok=True)
                (self.trabajo / "ola-2" / nombre / "contrato.md").write_text(f"# Contrato · {nombre}\n")
            if inventario:
                (self.trabajo / "ola-3" / "inventario").mkdir(parents=True, exist_ok=True)
                (self.trabajo / "ola-3" / "inventario" / f"{nombre}.json").write_text("{}\n")

    def revision(self, texto):
        (self.trabajo / "ola-3" / "revision.md").write_text(texto)

    def correr(self):
        return subprocess.run([sys.executable, "-B", str(SCRIPT), str(self.trabajo), str(self.repo)], capture_output=True, text=True)

    def en_repo(self):
        return {p.relative_to(self.repo / "design" / "vistas").as_posix() for p in (self.repo / "design" / "vistas").rglob("*.html")} \
            if (self.repo / "design" / "vistas").is_dir() else set()

    def test_la_revision_de_la_iteracion_3_deja_fuera_el_marco(self):
        self.vistas(*VISTAS_ITERACION_3)
        self.revision((FIX / "revision-iteracion-3.md").read_text())
        r = self.correr()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(self.en_repo(), {"inventario/lista.html", "socios/ajustes.html"})
        fuera = r.stdout.split("Fuera del repositorio")[1]
        self.assertIn("design/vistas/semilla/marco.html", fuera)
        self.assertIn("no aprobada", fuera)
        self.assertEqual((self.repo / "design" / "components.css").read_text(), "/* components.css integrado */\n")

    def test_todo_aprobado_mueve_todo_y_sale_con_0(self):
        self.vistas("riego/panel.html", "riego/historial.html")
        self.revision((FIX / "revision-segunda.md").read_text())
        r = self.correr()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.en_repo(), {"riego/panel.html", "riego/historial.html"})
        self.assertNotIn("Fuera del repositorio", r.stdout)

    def test_vista_sin_veredicto_queda_fuera(self):
        self.vistas("riego/panel.html", "riego/calendario.html")
        self.revision((FIX / "revision-segunda.md").read_text())
        r = self.correr()
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.en_repo(), {"riego/panel.html"})
        self.assertRegex(r.stdout, r"design/vistas/riego/calendario\.html.*sin veredicto")

    def test_vista_que_ya_estaba_igual_en_el_repositorio_no_necesita_veredicto(self):
        self.vistas("pedidos/listado.html", carpeta=self.repo / "design")
        self.vistas("pedidos/listado.html", "riego/panel.html")
        self.revision((FIX / "revision-segunda.md").read_text())
        r = self.correr()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertNotIn("listado", r.stdout)

    def test_vista_existente_cambiada_sin_veredicto_no_se_pisa(self):
        self.vistas("pedidos/listado.html", carpeta=self.repo / "design")
        self.vistas("pedidos/listado.html")
        (self.copia / "vistas" / "pedidos" / "listado.html").write_text("<!doctype html><title>cambiada</title>\n")
        self.revision((FIX / "revision-segunda.md").read_text())
        r = self.correr()
        self.assertEqual(r.returncode, 1)
        self.assertNotIn("cambiada", (self.repo / "design" / "vistas" / "pedidos" / "listado.html").read_text())

    def test_sin_ninguna_aprobada_no_mueve_los_compartidos(self):
        self.vistas("semilla/marco.html")
        self.revision((FIX / "revision-iteracion-3.md").read_text())
        r = self.correr()
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.en_repo(), set())
        self.assertEqual((self.repo / "design" / "components.css").read_text(), "/* components.css del repositorio */\n")

    def test_archivo_de_trabajo_en_la_copia_no_entra(self):
        self.vistas("riego/panel.html")
        (self.copia / "vistas" / "riego" / "contrato.md").write_text("# Contrato · panel\n")
        self.revision((FIX / "revision-segunda.md").read_text())
        r = self.correr()
        self.assertEqual(r.returncode, 1)
        self.assertFalse((self.repo / "design" / "vistas" / "riego" / "contrato.md").exists())
        self.assertIn("design/vistas/riego/contrato.md", r.stdout.split("Fuera del repositorio")[1])

    def test_dos_vistas_con_el_mismo_nombre_quedan_fuera(self):
        self.vistas("riego/panel.html", "cosechas/panel.html")
        self.revision((FIX / "revision-segunda.md").read_text())
        r = self.correr()
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.en_repo(), set())
        self.assertIn("mismo nombre", r.stdout)

    def test_aprobada_sin_contrato_o_sin_inventario_queda_fuera(self):
        """El revisor aprueba leyendo el contrato y el inventario: en las iteraciones 1 y 2 el marco no tuvo contrato
        en la ola 2 y dos corridas no dejaron el inventario en disco."""
        self.vistas("riego/panel.html", contrato=False)
        self.vistas("riego/historial.html", inventario=False)
        self.revision((FIX / "revision-segunda.md").read_text())
        r = self.correr()
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.en_repo(), set())
        fuera = r.stdout.split("Fuera del repositorio")[1]
        self.assertRegex(fuera, r"design/vistas/riego/panel\.html: .*ola-2/panel/contrato\.md")
        self.assertRegex(fuera, r"design/vistas/riego/historial\.html: .*ola-3/inventario/historial\.json")

    def test_sin_revision_no_mueve_nada(self):
        self.vistas("riego/panel.html")
        r = self.correr()
        self.assertEqual(r.returncode, 2)
        self.assertIn("revision.md", r.stdout + r.stderr)
        self.assertEqual(self.en_repo(), set())


if __name__ == "__main__":
    unittest.main()
