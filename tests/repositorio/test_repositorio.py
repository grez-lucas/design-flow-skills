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
