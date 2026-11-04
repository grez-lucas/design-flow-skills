"""Pruebas de la puesta al día de los compartidos en html-a-vista: las órdenes que da su SKILL.md llevan los assets de
spec-a-html a un repositorio de diseño creado con una versión anterior, antes de la ola 1.

El repositorio viejo es `tests/spec-a-html/fixtures/repo-viejo/`, el design/ que dejaba spec-a-html antes de 8b269c9
(sin `.modal`, `--color-overlay` ni el proto.js de hoy). `fixtures/puesta-al-dia/` trae la vista que deja la conversión
de un mockup que abre un modal y su spec. Las órdenes se leen de SKILL.md y se corren como las corre la skill, con
`<ruta-de-esta-skill>` y `<intérprete>` en su lugar.
Uso: python3 -m unittest discover -s tests/html-a-vista -v
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SKILL = RAIZ / "skills" / "html-a-vista"
ASSETS = RAIZ / "skills" / "spec-a-html" / "assets"
REVISAR = RAIZ / "skills" / "checklist-diseno" / "scripts" / "revisar.py"
APROBADAS = SKILL / "scripts" / "aprobadas.py"
REPO_VIEJO = RAIZ / "tests" / "spec-a-html" / "fixtures" / "repo-viejo"
FIX = Path(__file__).resolve().parent / "fixtures" / "puesta-al-dia"
VISTA = Path("design") / "vistas" / "pedidos" / "lista.html"
ORDEN = re.compile(r"^<intérprete> -B <ruta-de-esta-skill>/(\S+/compartidos\.py) (comparar|mostrar|aplicar) <repo-de-diseño>$", re.M)


def ordenes():
    """{comando: argv} de las órdenes de compartidos.py que da SKILL.md, con el intérprete y la ruta de la skill."""
    texto = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    return {comando: [sys.executable, "-B", str(SKILL / script), comando] for script, comando in ORDEN.findall(texto)}


def correr(argv, *args):
    return subprocess.run([*map(str, argv), *map(str, args)], capture_output=True, text=True)


def json_cambios(resultado):
    """`cambios` del JSON de `compartidos.py comparar`."""
    if resultado.returncode != 0:
        raise AssertionError(resultado.stderr)
    return json.loads(resultado.stdout)["cambios"]


class PuestaAlDia(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.repo = self.tmp / "repo"
        shutil.copytree(REPO_VIEJO / "design", self.repo / "design")
        # tests/pruebas exige que todo proto.js del repositorio sea el de la skill: el viejo se guarda con otro nombre.
        (self.repo / "design" / "proto-anterior.js").rename(self.repo / "design" / "proto.js")
        (self.repo / "specs" / "pedidos").mkdir(parents=True)
        shutil.copyfile(FIX / "spec.md", self.repo / "specs" / "pedidos" / "spec.md")
        self.trabajo = self.tmp / "trabajo"
        self.copia = self.trabajo / "ola-3" / "repo"

    def orden(self, comando):
        argv = ordenes().get(comando)
        self.assertIsNotNone(argv, f"SKILL.md no da la orden `compartidos.py {comando} <repo-de-diseño>`")
        return argv

    def poner_al_dia(self):
        """Lo que hace la skill antes de la ola 1, con el sí de la persona: comparar, mostrar y aplicar."""
        for comando in ("comparar", "mostrar", "aplicar"):
            r = correr(self.orden(comando), self.repo)
            self.assertEqual(r.returncode, 0, f"{comando}: {r.stderr}")

    def integrar(self):
        """Ola 3, paso 1: la copia parte del repositorio de diseño y recibe la vista convertida."""
        shutil.copytree(self.repo, self.copia)
        (self.copia / VISTA).parent.mkdir(parents=True)
        shutil.copyfile(FIX / "lista.html", self.copia / VISTA)

    def revisar(self):
        return correr([sys.executable, "-B", REVISAR], self.copia)

    def huella(self):
        r = correr([sys.executable, "-B", APROBADAS, "huella"], self.copia / VISTA)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def aprobar(self, huella):
        """El veredicto del revisor y lo que leyó: contrato de la ola 2 e inventario de la ola 3."""
        (self.trabajo / "ola-3" / "revision.md").write_text(f"# Revisión\n\n## pedidos/lista: aprobada {huella}\n", encoding="utf-8")
        (self.trabajo / "ola-2" / "pedidos" / "lista").mkdir(parents=True)
        (self.trabajo / "ola-2" / "pedidos" / "lista" / "contrato.md").write_text("# Contrato · lista\n", encoding="utf-8")
        (self.trabajo / "ola-3" / "inventario" / "pedidos").mkdir(parents=True)
        (self.trabajo / "ola-3" / "inventario" / "pedidos" / "lista.json").write_text("{}\n", encoding="utf-8")

    def mover(self):
        return correr([sys.executable, "-B", APROBADAS, "mover"], self.trabajo, self.repo)

    def test_la_skill_llama_al_script_de_spec_a_html_sin_copia_propia(self):
        for comando in ("comparar", "mostrar", "aplicar"):
            with self.subTest(comando=comando):
                self.assertEqual(Path(self.orden(comando)[2]).resolve(), RAIZ / "skills" / "spec-a-html" / "scripts" / "compartidos.py")
        self.assertFalse((SKILL / "scripts" / "compartidos.py").exists())

    def test_sin_poner_al_dia_la_vista_con_modal_bloquea_en_la_ola_3(self):
        self.assertTrue(json_cambios(correr(self.orden("comparar"), self.repo)))
        self.integrar()
        r = self.revisar()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertRegex(r.stdout, r"BLOQUEA: Usa clases que `components.css` no define[^\n]*`\.modal`")

    def test_puesta_al_dia_antes_de_la_ola_1_deja_pasar_la_vista_con_modal(self):
        self.poner_al_dia()
        self.assertFalse(json_cambios(correr(self.orden("comparar"), self.repo)))
        self.integrar()
        r = self.revisar()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual((self.copia / "design" / "proto.js").read_bytes(), (ASSETS / "proto.js").read_bytes())

    def test_la_puesta_al_dia_cambia_proto_js_y_la_huella_del_revisor(self):
        self.integrar()
        vieja = self.huella()
        r = correr(self.orden("aplicar"), self.copia)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((self.copia / "design" / "proto.js").read_bytes(), (ASSETS / "proto.js").read_bytes())
        self.assertNotEqual(self.huella(), vieja)

    def test_una_aprobacion_sobre_el_proto_js_viejo_no_entra_al_repositorio(self):
        """Si los compartidos se ponen al día después de la revisión, la vista ya no es la que el revisor vio."""
        self.integrar()
        self.aprobar(self.huella())
        self.assertEqual(correr(self.orden("aplicar"), self.copia).returncode, 0)
        r = self.mover()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertFalse((self.repo / VISTA).exists())

    def test_con_el_repositorio_al_dia_la_aprobacion_entra_y_proto_js_queda_el_de_la_skill(self):
        self.poner_al_dia()
        self.integrar()
        self.assertEqual(self.revisar().returncode, 0)
        self.aprobar(self.huella())
        r = self.mover()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((self.repo / VISTA).read_bytes(), (FIX / "lista.html").read_bytes())
        self.assertEqual((self.repo / "design" / "proto.js").read_bytes(), (ASSETS / "proto.js").read_bytes())
        self.assertEqual(correr([sys.executable, "-B", REVISAR], self.repo).returncode, 0)


if __name__ == "__main__":
    unittest.main()
