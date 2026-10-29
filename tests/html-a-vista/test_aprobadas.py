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

## riego/panel: aprobada {HUELLA}

## riego/historial: no aprobada
- Falta el escenario vacío.

## riego/historial, segunda revisión: aprobada {HUELLA}
"""
REVISION_RECHAZO_FUERA_DE_FORMATO = f"""## inventario/lista: aprobada {HUELLA}

## inventario/lista - no aprobada
- El revisor cambió de opinión, pero escribió el encabezado fuera del formato.
"""
ITERACION_3 = {"marco": "semilla/marco", "lista": "inventario/lista", "ajustes": "socios/ajustes"}


class Veredictos(unittest.TestCase):
    """Un solo lector de veredictos: lo usan el paso que mueve las vistas y el calificador de pruebas/html-a-vista.
    Por defecto lee solo el formato fijo, por ruta `<épica>/<vista>`; los formatos de las iteraciones 1 a 3, por
    nombre de archivo, se leen con historico=True."""

    def test_formato_fijo_ultimo_veredicto_de_cada_vista(self):
        formato_fijo = (FIX / "revision-segunda.md").read_text()
        casos = {
            "formato fijo de la skill": (formato_fijo, ["riego/panel", "riego/historial"],
                                         {"riego/panel": "aprobada", "riego/historial": "aprobada"}),
            "revisión de eval-3, iteración 3, por ruta": ((FIX / "revision-por-ruta.md").read_text(), list(ITERACION_3.values()),
                                                          {"semilla/marco": "no aprobada", "inventario/lista": "aprobada",
                                                           "socios/ajustes": "aprobada"}),
            "con huella": (REVISION_CON_HUELLA, ["riego/panel", "riego/historial"],
                           {"riego/panel": "aprobada", "riego/historial": "aprobada"}),
            "vista que el revisor no nombra": (formato_fijo, ["riego/panel", "riego/historial", "riego/ajustes"],
                                               {"riego/panel": "aprobada", "riego/historial": "aprobada", "riego/ajustes": None}),
            "un rechazo fuera de formato no deja en pie la aprobación anterior": (
                REVISION_RECHAZO_FUERA_DE_FORMATO, ["inventario/lista"], {"inventario/lista": "fuera de formato"}),
        }
        for caso, (revision, nombres, esperado) in casos.items():
            with self.subTest(caso=caso):
                self.assertEqual(aprobadas.veredictos(revision, nombres), esperado)

    def test_el_veredicto_va_por_ruta_y_el_nombre_suelto_queda_fuera_de_formato(self):
        """Dos vistas con el mismo nombre en épicas distintas se aprueban cada una por su ruta. El veredicto con el nombre
        suelto, como lo escribieron los revisores hasta la iteración 3, no dice de cuál es: fuera de formato."""
        revision = f"## compostaje/resumen: aprobada {HUELLA}\n## socios/resumen: no aprobada\n"
        self.assertEqual(aprobadas.veredictos(revision, ["compostaje/resumen", "socios/resumen"]),
                         {"compostaje/resumen": "aprobada", "socios/resumen": "no aprobada"})
        self.assertEqual(aprobadas.veredictos((FIX / "revision-iteracion-3.md").read_text(), list(ITERACION_3.values())),
                         {v: "fuera de formato" for v in ITERACION_3.values()})
        self.assertEqual(aprobadas.veredictos(f"## resumen: aprobada {HUELLA}\n", ["compostaje/resumen", "socios/resumen"]),
                         {"compostaje/resumen": "fuera de formato", "socios/resumen": "fuera de formato"})

    def test_cualquier_linea_fuera_de_formato_que_nombra_la_vista_anula_la_aprobacion(self):
        """Un rechazo posterior escrito en viñeta, en negrita, como encabezado con sangría o dentro de un bloque de código
        no se puede leer sin interpretar: cuenta como "fuera de formato" y la vista no entra. Ante la duda, bloquea."""
        aprobada = f"## inventario/lista: aprobada {HUELLA}\n"
        casos = {"viñeta": "- inventario/lista: no aprobada, el revisor cambió de opinión\n",
                 "encabezado con sangría": "   ## inventario/lista: no aprobada\n",
                 "negrita sin encabezado": "**inventario/lista: no aprobada**\n",
                 "cita": "> inventario/lista: no aprobada\n",
                 "frase con el nombre suelto": "Al final la lista queda no aprobada.\n",
                 "veredicto exacto dentro de un bloque de código": f"```\n## inventario/lista: aprobada {HUELLA}\n```\n",
                 "aprobación en viñeta": "- lista: aprobada\n"}
        for caso, despues in casos.items():
            with self.subTest(caso=caso):
                self.assertEqual(aprobadas.veredictos(aprobada + despues, ["inventario/lista", "socios/ajustes"]),
                                 {"inventario/lista": "fuera de formato", "socios/ajustes": None})

    def test_lineas_que_no_nombran_la_vista_o_no_dicen_aprobada_no_cuentan(self):
        revision = (f"## inventario/lista: aprobada {HUELLA}\n- lista: los encabezados de la tabla siguen el original.\n"
                    "- Los tokens de la tabla aprobada por producto.\n- compostaje/lista: no aprobada\n## Segunda revisión\n")
        self.assertEqual(aprobadas.veredictos(revision, ["inventario/lista"]), {"inventario/lista": "aprobada"})

    def test_la_huella_es_la_del_ultimo_veredicto(self):
        leidos = aprobadas.leer(REVISION_CON_HUELLA, ["riego/panel", "riego/historial"])
        self.assertEqual({v: (x.estado, x.huella) for v, x in leidos.items()},
                         {"riego/panel": ("aprobada", HUELLA), "riego/historial": ("aprobada", HUELLA)})
        sin = aprobadas.leer((FIX / "revision-segunda.md").read_text(), ["riego/panel"])
        self.assertEqual((sin["riego/panel"].estado, sin["riego/panel"].huella), ("aprobada", None))

    def test_formatos_informales_solo_en_modo_historico(self):
        """Los revisores de las iteraciones 1 y 2 escribieron el veredicto a su manera y por nombre de archivo. El modo
        histórico los lee por el nombre de la vista para calificar esas corridas; el modo por defecto no aprueba
        ninguno, y marca la línea que no sigue el formato."""
        def rutas(*nombres):
            return [f"e/{n}" for n in nombres]

        def por_ruta(d):
            return {f"e/{n}": x for n, x in d.items()}
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
                self.assertEqual(aprobadas.veredictos(revision, rutas(*nombres), historico=True), por_ruta(historico))
                self.assertEqual(aprobadas.veredictos(revision, rutas(*nombres)), por_ruta(estricto))

    def test_el_modo_historico_lee_el_nombre_suelto_y_la_ruta(self):
        """Las iteraciones 2 y 3 se califican con el nombre suelto; una corrida nueva, por ruta, también se lee."""
        nombres = ["semilla/marco", "inventario/lista"]
        esperado = {"semilla/marco": "no aprobada", "inventario/lista": "aprobada"}
        for fixture in ("revision-iteracion-3.md", "revision-por-ruta.md"):
            with self.subTest(fixture=fixture):
                self.assertEqual(aprobadas.veredictos((FIX / fixture).read_text(), nombres, historico=True), esperado)

    def test_el_modo_historico_no_adivina_entre_dos_vistas_con_el_mismo_nombre(self):
        self.assertEqual(aprobadas.veredictos("## resumen: aprobada\n", ["compostaje/resumen", "socios/resumen"], historico=True),
                         {"compostaje/resumen": None, "socios/resumen": None})


SEGUNDA_DEL_MARCO = "\n## semilla/marco, segunda revisión: no aprobada\n- El menú lateral sigue sin llegar al alto de la pantalla.\n"
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
            clave = Path(ruta).with_suffix("").as_posix()
            if contrato:
                (self.trabajo / "ola-2" / clave).mkdir(parents=True, exist_ok=True)
                (self.trabajo / "ola-2" / clave / "contrato.md").write_text(f"# Contrato · {clave}\n")
            if inventario:
                (self.trabajo / "ola-3" / "inventario" / clave).parent.mkdir(parents=True, exist_ok=True)
                (self.trabajo / "ola-3" / "inventario" / f"{clave}.json").write_text("{}\n")

    def huella(self, vista):
        r = subprocess.run([sys.executable, "-B", str(SCRIPT), "huella", str(vista)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout.strip()

    def revision(self, texto, huellas=True):
        """revision.md con el texto dado. Con huellas, cada "aprobada" lleva la huella de su vista en la copia, como la
        registra el revisor; las revisiones de las fixtures son anteriores a la huella."""
        if huellas:
            def firmar(m):
                vista = self.copia / "vistas" / f"{m.group(1)}.html"
                return m.group(0) + (f" {self.huella(vista)}" if vista.is_file() else "")
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
        self.revision((FIX / "revision-por-ruta.md").read_text())
        r = self.correr()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(self.en_repo(), set())
        self.assertEqual((self.repo / "design" / "components.css").read_text(), "/* components.css del repositorio */\n")
        self.assertIn("No se movió nada", r.stdout)
        self.assertIn("--pendientes", r.stdout)
        fuera = r.stdout.split("Fuera del repositorio")[1]
        self.assertRegex(fuera, r"design/vistas/semilla/marco\.html: no aprobada")

    def test_la_revision_de_la_iteracion_3_con_el_marco_pendiente_no_mueve_nada(self):
        """En la iteración 3 el marco solo tuvo la primera revisión: no volvió a su subagente. --pendientes acepta solo
        una vista que tuvo su segunda revisión y sigue sin aprobarse; el marco vuelve a su subagente."""
        self.vistas(*VISTAS_ITERACION_3)
        self.revision((FIX / "revision-por-ruta.md").read_text())
        r = self.correr("--pendientes", "semilla/marco")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(self.en_repo(), set())
        self.assertEqual((self.repo / "design" / "components.css").read_text(), "/* components.css del repositorio */\n")
        aviso = r.stdout.split("No se movió nada")[1].split("\n\n")[0]
        self.assertRegex(aviso, r"semilla/marco: no tuvo segunda revisión")
        self.assertIn("vuelve a su subagente", aviso)
        self.assertNotIn("## Pendientes", r.stdout)

    def test_con_el_marco_no_aprobado_en_la_segunda_revision_mueve_las_8(self):
        self.vistas(*VISTAS_ITERACION_3)
        self.revision((FIX / "revision-por-ruta.md").read_text() + SEGUNDA_DEL_MARCO)
        r = self.correr("--pendientes", "semilla/marco")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.en_repo(), APROBADAS_ITERACION_3)
        self.assertEqual(len(self.en_repo()), 8)
        self.assertEqual((self.repo / "design" / "components.css").read_text(), "/* components.css integrado */\n")
        pendientes = r.stdout.split("## Pendientes")[1]
        self.assertRegex(pendientes, r"design/vistas/semilla/marco\.html: no aprobada")
        self.assertNotIn("Fuera del repositorio", r.stdout)

    def test_pendientes_que_no_coinciden_con_lo_que_queda_fuera_no_mueven_nada(self):
        self.vistas(*VISTAS_ITERACION_3)
        self.revision((FIX / "revision-por-ruta.md").read_text())
        casos = {"nombra una aprobada en vez del marco": ("inventario/lista", "semilla/marco", "inventario/lista"),
                 "nombra el marco y una aprobada": ("semilla/marco,socios/ajustes", None, "socios/ajustes"),
                 "nombra una vista que no existe": ("semilla/marco,mapa/mapa", None, "mapa/mapa")}
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
        r = self.correr("--pendientes", "riego/calendario")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertEqual(self.en_repo(), set())
        self.assertRegex(r.stdout, r"riego/calendario: no tuvo segunda revisión")

    def test_pendientes_exige_que_el_ultimo_veredicto_de_la_segunda_revision_sea_no_aprobada(self):
        """Una vista que tuvo su segunda revisión pero cuyo último veredicto no es "no aprobada" no es pendiente: si está
        fuera de formato o su huella cambió, vuelve al revisor."""
        casos = {"fuera de formato después de la segunda": "## riego/historial, segunda revisión: no aprobada\n- historial: aprobada\n",
                 "aprobada en la segunda con otra huella": f"## riego/historial, segunda revisión: aprobada {HUELLA}\n"}
        for caso, segunda in casos.items():
            with self.subTest(caso=caso):
                self.setUp()
                self.vistas("riego/panel.html", "riego/historial.html")
                self.revision("## riego/panel: aprobada\n## riego/historial: no aprobada\n" + segunda)
                r = self.correr("--pendientes", "riego/historial")
                self.assertEqual(r.returncode, 1, r.stdout)
                self.assertEqual(self.en_repo(), set())
                self.assertRegex(r.stdout, r"riego/historial: tuvo segunda revisión, pero su último veredicto no es `no aprobada`")

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
        self.revision((FIX / "revision-por-ruta.md").read_text() + SEGUNDA_DEL_MARCO)
        for extra in ([], ["--pendientes", "semilla/marco"]):
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

    def test_dos_vistas_con_el_mismo_nombre_en_epicas_distintas_se_aprueban_por_ruta(self):
        """Cada una con su veredicto, su contrato y su inventario por ruta: no se pisan ni se confunden."""
        self.vistas("riego/panel.html", "cosechas/panel.html")
        self.revision("## riego/panel: aprobada\n## cosechas/panel: aprobada\n")
        r = self.correr()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.en_repo(), {"riego/panel.html", "cosechas/panel.html"})
        self.assertTrue((self.trabajo / "ola-2" / "riego" / "panel" / "contrato.md").is_file())
        self.assertTrue((self.trabajo / "ola-2" / "cosechas" / "panel" / "contrato.md").is_file())

    def test_veredicto_con_el_nombre_suelto_no_aprueba(self):
        self.vistas("riego/panel.html", "cosechas/panel.html")
        huella = self.huella(self.copia / "vistas" / "riego" / "panel.html")
        (self.trabajo / "ola-3" / "revision.md").write_text(f"## panel: aprobada {huella}\n")
        r = self.correr()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertEqual(self.en_repo(), set())
        fuera = r.stdout.split("Fuera del repositorio")[1]
        self.assertRegex(fuera, r"design/vistas/riego/panel\.html: .*no sigue el formato `## riego/panel: aprobada")
        self.assertRegex(fuera, r"design/vistas/cosechas/panel\.html: .*no sigue el formato")

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
        self.assertRegex(fuera, r"design/vistas/riego/panel\.html: .*ola-2/riego/panel/contrato\.md")
        self.assertRegex(fuera, r"design/vistas/riego/historial\.html: .*ola-3/inventario/riego/historial\.json")

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
        self.revision((FIX / "revision-por-ruta.md").read_text() + SEGUNDA_DEL_MARCO)
        (self.copia / "vistas" / "inventario" / "lista.html").write_text("<!doctype html><title>lista cambiada</title>\n")
        r = self.correr("--pendientes", "semilla/marco")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertEqual(self.en_repo(), set())
        self.assertIn("quedan fuera sin nombrar: inventario/lista", r.stdout)

    def test_pendientes_con_el_nombre_suelto_es_un_error_de_uso(self):
        self.vistas(*VISTAS_ITERACION_3)
        self.revision((FIX / "revision-por-ruta.md").read_text())
        r = self.correr("--pendientes", "marco")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("<épica>/<vista>", r.stderr)
        self.assertEqual(self.en_repo(), set())

    def test_rechazo_posterior_fuera_de_formato_no_mueve_nada(self):
        """Los tres casos con que la revisión final movía una vista que el revisor rechazó después de aprobarla."""
        for caso, despues in {"viñeta": "- riego/panel: no aprobada\n", "encabezado con sangría": "   ## riego/panel: no aprobada\n",
                              "negrita": "**riego/panel: no aprobada**\n"}.items():
            with self.subTest(caso=caso):
                self.setUp()
                self.vistas("riego/panel.html")
                self.revision("## riego/panel: aprobada\n\n## Segunda revisión\n" + despues)
                r = self.correr()
                self.assertEqual(r.returncode, 1, r.stdout)
                self.assertEqual(self.en_repo(), set())
                self.assertRegex(r.stdout.split("Fuera del repositorio")[1], r"design/vistas/riego/panel\.html: .*no sigue el formato")

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

    def test_casos_adversos_de_la_revision_final(self):
        """Los casos con que la revisión final intentó que `mover` moviera algo que el revisor no aprobó tal cual."""
        def h(ruta):
            return self.huella(self.copia / "vistas" / ruta)
        casos = {
            "huella de otra vista copiada": (("e/panel.html", "e/hist.html"),
                                             lambda: f"## e/panel: aprobada {h('e/hist.html')}\n## e/hist: aprobada {h('e/hist.html')}\n",
                                             [], 1, set()),
            "huella en mayúsculas": (("e/panel.html",), lambda: f"## e/panel: aprobada sha256:{h('e/panel.html')[7:].upper()}\n",
                                     [], 1, set()),
            "resumen posterior que nombra la vista": (("e/panel.html",),
                                                      lambda: f"## e/panel: aprobada {h('e/panel.html')}\n\n## Resumen: panel aprobada\n",
                                                      [], 1, set()),
            "CRLF": (("e/panel.html",), lambda: f"## e/panel: aprobada {h('e/panel.html')}\r\n", [], 0, {"e/panel.html"}),
            "--pendientes con espacios y repetida": (
                ("e/panel.html", "e/marco.html"),
                lambda: f"## e/panel: aprobada {h('e/panel.html')}\n## e/marco: no aprobada\n## e/marco, segunda revisión: no aprobada\n",
                ["--pendientes", " e/marco , e/marco"], 0, {"e/panel.html"}),
            "--pendientes vacío": (("e/panel.html", "e/marco.html"), lambda: f"## e/panel: aprobada {h('e/panel.html')}\n",
                                   ["--pendientes", ""], 2, set()),
        }
        for caso, (vistas, texto, extra, codigo, movidas) in casos.items():
            with self.subTest(caso=caso):
                self.setUp()
                self.vistas(*vistas)
                (self.trabajo / "ola-3" / "revision.md").write_bytes(texto().encode())
                r = self.correr(*extra)
                self.assertEqual(r.returncode, codigo, r.stdout + r.stderr)
                self.assertNotIn("Traceback", r.stderr)
                self.assertEqual(self.en_repo(), movidas)

    def test_solo_cambian_los_compartidos_o_hay_un_archivo_ajeno(self):
        (self.copia / "tokens.css").write_text("/* tokens.css nuevo */\n")
        self.revision("")
        r = self.correr()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertEqual((self.repo / "design" / "tokens.css").read_text(), "/* tokens.css del repositorio */\n")
        self.assertIn("design/tokens.css: ninguna vista aprobada lo usa", r.stdout)
        self.setUp()
        self.vistas("e/panel.html")
        (self.copia / ".DS_Store").write_bytes(b"\0")
        self.revision("## e/panel: aprobada\n")
        r = self.correr()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertEqual(self.en_repo(), {"e/panel.html"})
        self.assertIn("design/.DS_Store: no es una vista ni un archivo compartido", r.stdout)

    def test_sin_revision_no_mueve_nada(self):
        self.vistas("riego/panel.html")
        r = self.correr()
        self.assertEqual(r.returncode, 2)
        self.assertIn("revision.md", r.stdout + r.stderr)
        self.assertEqual(self.en_repo(), set())


if __name__ == "__main__":
    unittest.main()
