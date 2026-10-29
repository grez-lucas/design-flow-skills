"""Pruebas de skills/html-a-vista/scripts/aprobadas.py.

Uso: python3 -m unittest discover -s tests/html-a-vista -v
"""
import hashlib
import importlib.util
import re
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


HUELLA = "sha256:" + "0123456789abcdef" * 4
REVISION_CON_HUELLA = f"""# Revisión · ola 3

## panel: aprobada {HUELLA}

## historial: no aprobada
- Falta el escenario vacío.

## historial, segunda revisión: aprobada {HUELLA}
"""
REVISION_RECHAZO_FUERA_DE_FORMATO = f"""## lista: aprobada {HUELLA}

## lista - no aprobada
- El revisor cambió de opinión, pero escribió el encabezado fuera del formato.
"""


class Veredictos(unittest.TestCase):
    """Un solo lector de veredictos: lo usan el paso que mueve las vistas y el calificador de pruebas/html-a-vista.
    Por defecto lee solo el formato fijo; los formatos de las iteraciones 1 y 2 se leen con historico=True."""

    def test_formato_fijo_ultimo_veredicto_de_cada_vista(self):
        formato_fijo = (FIX / "revision-segunda.md").read_text()
        casos = {
            "formato fijo de la skill": (formato_fijo, ["panel", "historial"], {"panel": "aprobada", "historial": "aprobada"}),
            "revisión de eval-3, iteración 3": ((FIX / "revision-iteracion-3.md").read_text(), ["marco", "lista", "ajustes"],
                                                {"marco": "no aprobada", "lista": "aprobada", "ajustes": "aprobada"}),
            "con huella": (REVISION_CON_HUELLA, ["panel", "historial"], {"panel": "aprobada", "historial": "aprobada"}),
            "vista que el revisor no nombra": (formato_fijo, ["panel", "historial", "ajustes"],
                                               {"panel": "aprobada", "historial": "aprobada", "ajustes": None}),
            "un rechazo fuera de formato no deja en pie la aprobación anterior": (
                REVISION_RECHAZO_FUERA_DE_FORMATO, ["lista"], {"lista": "fuera de formato"}),
        }
        for caso, (revision, nombres, esperado) in casos.items():
            with self.subTest(caso=caso):
                self.assertEqual(aprobadas.veredictos(revision, nombres), esperado)

    def test_la_huella_es_la_del_ultimo_veredicto(self):
        leidos = aprobadas.leer(REVISION_CON_HUELLA, ["panel", "historial"])
        self.assertEqual({v: (x.estado, x.huella) for v, x in leidos.items()},
                         {"panel": ("aprobada", HUELLA), "historial": ("aprobada", HUELLA)})
        sin = aprobadas.leer((FIX / "revision-segunda.md").read_text(), ["panel"])
        self.assertEqual((sin["panel"].estado, sin["panel"].huella), ("aprobada", None))

    def test_formatos_informales_solo_en_modo_historico(self):
        """Los revisores de las iteraciones 1 y 2 escribieron el veredicto a su manera. El modo histórico los lee para
        calificar esas corridas; el modo por defecto no aprueba ninguno, y marca el encabezado que no sigue el formato."""
        casos = {
            "sin segunda revisión": (REVISION_SIN_SEGUNDA, ["marco", "lista", "ajustes"],
                                     {"marco": "no aprobada", "lista": "aprobada", "ajustes": "no aprobada"},
                                     {"marco": "fuera de formato", "lista": "fuera de formato", "ajustes": "fuera de formato"}),
            "con segunda vuelta en viñetas": (REVISION_CON_SEGUNDA_VUELTA, ["marco", "lista", "detalle-lote"],
                                              {"marco": "aprobada", "lista": "aprobada", "detalle-lote": "aprobada"},
                                              {"marco": "fuera de formato", "lista": "fuera de formato",
                                               "detalle-lote": "fuera de formato"}),
            "primera revisión escrita después": (REVISION_PRIMERA_DESPUES, ["panel"], {"panel": "aprobada"},
                                                 {"panel": "fuera de formato"}),
            "una vista, segunda revisión sin nombrarla": (REVISION_UNA_VISTA, ["semana"], {"semana": "aprobada"}, {"semana": None}),
            "una vista que el archivo no nombra": (REVISION_SIN_NOMBRE, ["reservas"], {"reservas": "aprobada"}, {"reservas": None}),
            "detalle no es detalle-lote": (REVISION_CON_SEGUNDA_VUELTA, ["detalle"], {"detalle": None}, {"detalle": None}),
        }
        for caso, (revision, nombres, historico, estricto) in casos.items():
            with self.subTest(caso=caso):
                self.assertEqual(aprobadas.veredictos(revision, nombres, historico=True), historico)
                self.assertEqual(aprobadas.veredictos(revision, nombres), estricto)

    def test_el_modo_historico_lee_tambien_el_formato_fijo(self):
        self.assertEqual(aprobadas.veredictos((FIX / "revision-iteracion-3.md").read_text(), ["marco", "lista"], historico=True),
                         {"marco": "no aprobada", "lista": "aprobada"})


VISTAS_ITERACION_3 = {"semilla/marco.html", "inventario/lista.html", "inventario/detalle.html", "inventario/movimientos.html",
                      "compostaje/resumen.html", "compostaje/pilas.html", "socios/socios.html", "socios/cuotas.html",
                      "socios/ajustes.html"}
APROBADAS_ITERACION_3 = VISTAS_ITERACION_3 - {"semilla/marco.html"}


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

    def huella(self, vista):
        r = subprocess.run([sys.executable, "-B", str(SCRIPT), "huella", str(vista)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout.strip()

    def revision(self, texto, huellas=True):
        """revision.md con el texto dado. Con huellas, cada "aprobada" lleva la huella de su vista en la copia, como la
        registra el revisor; las revisiones de las fixtures son anteriores a la huella."""
        if huellas:
            def firmar(m):
                vista = next((self.copia / "vistas").rglob(f"{m.group(1)}.html"), None)
                return m.group(0) + (f" {self.huella(vista)}" if vista else "")
            texto = re.sub(r"(?m)^## ([^\s:,]+)(?:, segunda revisión)?: aprobada$", firmar, texto)
        (self.trabajo / "ola-3" / "revision.md").write_text(texto)

    def correr(self, *extra):
        return subprocess.run([sys.executable, "-B", str(SCRIPT), "mover", str(self.trabajo), str(self.repo), *extra],
                              capture_output=True, text=True)

    def en_repo(self):
        return {p.relative_to(self.repo / "design" / "vistas").as_posix() for p in (self.repo / "design" / "vistas").rglob("*.html")} \
            if (self.repo / "design" / "vistas").is_dir() else set()

    def test_la_revision_de_la_iteracion_3_sin_pendientes_no_mueve_nada(self):
        """En eval-3 de la iteración 3 el revisor no aprobó el marco: sin nombrarlo como pendiente, no entra nada."""
        self.vistas(*VISTAS_ITERACION_3)
        self.revision((FIX / "revision-iteracion-3.md").read_text())
        r = self.correr()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(self.en_repo(), set())
        self.assertEqual((self.repo / "design" / "components.css").read_text(), "/* components.css del repositorio */\n")
        self.assertIn("No se movió nada", r.stdout)
        self.assertIn("--pendientes", r.stdout)
        fuera = r.stdout.split("Fuera del repositorio")[1]
        self.assertRegex(fuera, r"design/vistas/semilla/marco\.html: no aprobada")

    def test_la_revision_de_la_iteracion_3_con_el_marco_pendiente_mueve_las_8(self):
        self.vistas(*VISTAS_ITERACION_3)
        self.revision((FIX / "revision-iteracion-3.md").read_text())
        r = self.correr("--pendientes", "marco")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.en_repo(), APROBADAS_ITERACION_3)
        self.assertEqual(len(self.en_repo()), 8)
        self.assertEqual((self.repo / "design" / "components.css").read_text(), "/* components.css integrado */\n")
        pendientes = r.stdout.split("## Pendientes")[1]
        self.assertRegex(pendientes, r"design/vistas/semilla/marco\.html: no aprobada")
        self.assertNotIn("Fuera del repositorio", r.stdout)

    def test_pendientes_que_no_coinciden_con_lo_que_queda_fuera_no_mueven_nada(self):
        self.vistas(*VISTAS_ITERACION_3)
        self.revision((FIX / "revision-iteracion-3.md").read_text())
        casos = {"nombra una aprobada en vez del marco": ("lista", "marco", "lista"),
                 "nombra el marco y una aprobada": ("marco,ajustes", None, "ajustes"),
                 "nombra una vista que no existe": ("marco,mapa", None, "mapa")}
        for caso, (pendientes, sin_nombrar, de_mas) in casos.items():
            with self.subTest(caso=caso):
                r = self.correr("--pendientes", pendientes)
                self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                self.assertEqual(self.en_repo(), set())
                self.assertIn("No se movió nada", r.stdout)
                aviso = r.stdout.split("No se movió nada")[1].split("\n\n")[0]
                if sin_nombrar:
                    self.assertRegex(aviso, rf"quedan fuera sin nombrar: {sin_nombrar}\b")
                self.assertRegex(aviso, rf"no quedan fuera: {de_mas}\b")

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
        self.assertEqual(self.en_repo(), set())
        self.assertRegex(r.stdout, r"design/vistas/riego/calendario\.html.*sin veredicto")
        r = self.correr("--pendientes", "calendario")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.en_repo(), {"riego/panel.html"})
        self.assertRegex(r.stdout.split("## Pendientes")[1], r"design/vistas/riego/calendario\.html.*sin veredicto")

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
        for extra in ([], ["--pendientes", "marco"]):
            with self.subTest(extra=extra):
                r = self.correr(*extra)
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

    def test_la_huella_cubre_la_vista_y_los_compartidos(self):
        """sha256 de las líneas de sha256sum de la vista y de tokens.css, components.css y proto.js, relativas a design/."""
        self.vistas("riego/panel.html")
        vista = self.copia / "vistas" / "riego" / "panel.html"
        rutas = ["vistas/riego/panel.html", "tokens.css", "components.css", "proto.js"]
        lineas = "".join(f"{hashlib.sha256((self.copia / r).read_bytes()).hexdigest()}  {r}\n" for r in rutas)
        antes = self.huella(vista)
        self.assertEqual(antes, "sha256:" + hashlib.sha256(lineas.encode()).hexdigest())
        (self.copia / "components.css").write_text("/* components.css cambiado después de la revisión */\n")
        self.assertNotEqual(self.huella(vista), antes)
        r = subprocess.run([sys.executable, "-B", str(SCRIPT), "huella", str(self.trabajo / "contrato.md")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2, "solo una vista bajo design/vistas/ tiene huella")

    def test_aprobada_cuya_huella_no_coincide_queda_fuera(self):
        """La vista o un compartido cambió después de que el revisor la aprobó: lo que entraría no es lo que vio."""
        casos = {"la vista cambió": lambda: (self.copia / "vistas" / "riego" / "historial.html").write_text("<!doctype html><title>otra</title>\n"),
                 "components.css cambió": lambda: (self.copia / "components.css").write_text("/* otro components.css */\n")}
        for caso, cambiar in casos.items():
            with self.subTest(caso=caso):
                self.setUp()
                self.vistas("riego/panel.html", "riego/historial.html")
                self.revision((FIX / "revision-segunda.md").read_text())
                cambiar()
                r = self.correr()
                self.assertEqual(r.returncode, 1, r.stdout)
                self.assertEqual(self.en_repo(), set())
                fuera = r.stdout.split("Fuera del repositorio")[1]
                self.assertRegex(fuera, r"design/vistas/riego/historial\.html: .*huella")
                if caso == "components.css cambió":
                    self.assertRegex(fuera, r"design/vistas/riego/panel\.html: .*huella")

    def test_aprobada_sin_huella_queda_fuera(self):
        self.vistas("riego/panel.html", "riego/historial.html")
        self.revision((FIX / "revision-segunda.md").read_text(), huellas=False)
        r = self.correr()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertEqual(self.en_repo(), set())
        self.assertRegex(r.stdout.split("Fuera del repositorio")[1], r"design/vistas/riego/panel\.html: aprobada sin huella")

    def test_con_el_marco_pendiente_y_una_huella_que_no_coincide_no_mueve_nada(self):
        self.vistas(*VISTAS_ITERACION_3)
        self.revision((FIX / "revision-iteracion-3.md").read_text())
        (self.copia / "vistas" / "inventario" / "lista.html").write_text("<!doctype html><title>lista cambiada</title>\n")
        r = self.correr("--pendientes", "marco")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertEqual(self.en_repo(), set())
        self.assertIn("quedan fuera sin nombrar: lista", r.stdout)

    def test_vista_fuera_de_vistas_epica_vista_sale_con_2_sin_mover(self):
        """Una vista sin épica o anidada de más no tiene huella ni lugar en el repositorio: error claro, sin traceback."""
        for caso, ruta in {"sin épica": "x.html", "anidada": "a/b/c.html"}.items():
            with self.subTest(caso=caso):
                self.setUp()
                self.vistas("riego/panel.html", ruta)
                self.revision((FIX / "revision-segunda.md").read_text())
                r = self.correr()
                self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
                self.assertNotIn("Traceback", r.stderr)
                self.assertEqual(self.en_repo(), set())
                self.assertIn(f"design/vistas/{ruta}", r.stderr)
                self.assertIn("design/vistas/<épica>/<vista>.html", r.stderr)
                self.assertIn("No se movió nada", r.stderr)

    def test_enlace_simbolico_en_la_copia_sale_con_2_sin_mover(self):
        self.vistas("riego/panel.html")
        afuera = self.trabajo / "secreto.txt"
        afuera.write_text("fuera de la copia\n")
        (self.copia / "vistas" / "riego" / "enlace.html").symlink_to(afuera)
        self.revision((FIX / "revision-segunda.md").read_text())
        r = self.correr()
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(self.en_repo(), set())
        self.assertIn("design/vistas/riego/enlace.html", r.stderr)
        self.assertIn("enlace simbólico", r.stderr)

    def test_huella_de_una_ruta_que_no_es_una_vista_de_design_sale_con_2(self):
        fuera = self.trabajo / "x" / "vistas" / "e" / "v.html"
        sin_epica = self.copia / "vistas" / "v.html"
        for caso, ruta in {"fuera de design/": fuera, "sin épica": sin_epica}.items():
            with self.subTest(caso=caso):
                ruta.parent.mkdir(parents=True, exist_ok=True)
                ruta.write_text("<!doctype html><title>v</title>\n")
                r = subprocess.run([sys.executable, "-B", str(SCRIPT), "huella", str(ruta)], capture_output=True, text=True)
                self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
                self.assertEqual(r.stdout, "")
                self.assertNotIn("Traceback", r.stderr)
                self.assertIn("design/vistas/<épica>/<vista>.html", r.stderr)

    def test_sin_revision_no_mueve_nada(self):
        self.vistas("riego/panel.html")
        r = self.correr()
        self.assertEqual(r.returncode, 2)
        self.assertIn("revision.md", r.stdout + r.stderr)
        self.assertEqual(self.en_repo(), set())


if __name__ == "__main__":
    unittest.main()
