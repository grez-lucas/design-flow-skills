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


if __name__ == "__main__":
    unittest.main()
