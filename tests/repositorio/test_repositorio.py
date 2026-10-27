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


class CommitSoloDeDesignYSpecs(unittest.TestCase):
    SKILLS_CON_COMMIT = ("grilling-es", "spec-a-html", "spec-a-tickets")

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
