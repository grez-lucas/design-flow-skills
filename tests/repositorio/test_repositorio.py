import json
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SKILLS = RAIZ / "skills"


class RevisarSinBytecode(unittest.TestCase):
    def test_checklist_diseno_corre_revisar_py_con_python3_b(self):
        texto = (SKILLS / "checklist-diseno" / "SKILL.md").read_text(encoding="utf-8")
        llamadas = [l for l in texto.splitlines() if "revisar.py" in l and "python" in l]
        self.assertTrue(llamadas, "SKILL.md no corre revisar.py")
        for linea in llamadas:
            self.assertRegex(linea, r"\bpython3 -B ", linea)

    def test_html_a_vista_corre_sus_scripts_con_python3_b(self):
        for ruta in [SKILLS / "html-a-vista" / "SKILL.md", *sorted((SKILLS / "html-a-vista" / "references").glob("*.md"))]:
            texto = ruta.read_text(encoding="utf-8")
            llamadas = re.findall(r"python3?[^`\n]*\.py", texto)
            with self.subTest(archivo=ruta.name):
                for llamada in llamadas:
                    self.assertRegex(llamada, r"^python3 -B ", llamada)
        texto = (SKILLS / "html-a-vista" / "SKILL.md").read_text(encoding="utf-8")
        for script in ("desarmar.py", "tokens.py", "inventario.py", "revisar.py"):
            self.assertRegex(texto, rf"python3 -B [^`\n]*{script}", script)


class CommitSoloDeDesignYSpecs(unittest.TestCase):
    SKILLS_CON_COMMIT = ("grilling-es", "html-a-vista", "spec-a-html", "spec-a-tickets")

    def archivos_con_commit(self, skill):
        return [
            ruta
            for ruta in sorted((SKILLS / skill).rglob("*.md"))
            if re.search(r"\bcommit y push\b", ruta.read_text(encoding="utf-8"))
        ]

    def test_cada_skill_que_hace_commit_lo_dice_en_algun_archivo(self):
        for skill in self.SKILLS_CON_COMMIT:
            with self.subTest(skill=skill):
                self.assertTrue(self.archivos_con_commit(skill))

    def test_el_commit_agrega_solo_design_y_specs(self):
        for skill in self.SKILLS_CON_COMMIT:
            for ruta in self.archivos_con_commit(skill):
                with self.subTest(archivo=str(ruta.relative_to(RAIZ))):
                    texto = ruta.read_text(encoding="utf-8")
                    permitidos = []
                    for linea in texto.splitlines():
                        for argumentos in re.findall(r"`git add ([^`]*)`", linea):
                            rutas = [a for a in argumentos.split() if a != "--"]
                            if rutas and all(r.startswith(("design/", "specs/")) for r in rutas):
                                permitidos.append(argumentos)
                            else:
                                self.assertIn("nunca", linea.lower(), linea)
                    self.assertTrue(permitidos, "no da un git add limitado a design/ y specs/")

    def test_el_resumen_antes_del_push_lista_solo_lo_que_entra_al_commit(self):
        for skill in self.SKILLS_CON_COMMIT:
            for ruta in self.archivos_con_commit(skill):
                with self.subTest(archivo=str(ruta.relative_to(RAIZ))):
                    texto = ruta.read_text(encoding="utf-8")
                    self.assertIn("skills-lock.json", texto)
                    self.assertIn("el resumen", texto.lower())


class NombreDelSiguientePaso(unittest.TestCase):
    PLUGIN = "flujo-diseno"

    def skills(self):
        return sorted(p.name for p in SKILLS.iterdir() if (p / "SKILL.md").is_file())

    def test_el_cierre_da_el_nombre_con_y_sin_prefijo_del_plugin(self):
        nombres = self.skills()
        for skill in nombres:
            texto = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
            cierre = re.split(r"^#{2,3} ", texto, flags=re.M)[-1]
            nombrados = [n for n in nombres if n != skill and f"`{n}`" in cierre]
            with self.subTest(skill=skill):
                self.assertTrue(nombrados, "el cierre no nombra el siguiente paso")
                for nombre in nombrados:
                    self.assertIn(f"`{self.PLUGIN}:{nombre}`", cierre)

    def test_el_readme_da_los_dos_nombres_de_cada_skill(self):
        readme = (RAIZ / "README.md").read_text(encoding="utf-8")
        for skill in self.skills():
            with self.subTest(skill=skill):
                self.assertIn(f"`{skill}`", readme)
                self.assertIn(f"`{self.PLUGIN}:{skill}`", readme)


class VersionDelPlugin(unittest.TestCase):
    def test_plugin_y_marketplace_declaran_la_misma_version_semver(self):
        manifiestos = RAIZ / ".claude-plugin"
        plugin = json.loads((manifiestos / "plugin.json").read_text(encoding="utf-8"))
        marketplace = json.loads((manifiestos / "marketplace.json").read_text(encoding="utf-8"))
        entrada = next(p for p in marketplace["plugins"] if p["name"] == plugin["name"])
        self.assertRegex(plugin.get("version", ""), r"^\d+\.\d+\.\d+$")
        self.assertEqual(entrada.get("version"), plugin["version"])


if __name__ == "__main__":
    unittest.main()
