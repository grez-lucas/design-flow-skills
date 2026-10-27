"""Toda copia de proto.js en pruebas/ y tests/ es igual byte a byte a la de spec-a-html.

Uso: python3 -m unittest discover -s tests/pruebas -v
"""
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
ORIGINAL = RAIZ / "skills" / "spec-a-html" / "assets" / "proto.js"


class CopiasDeProto(unittest.TestCase):
    def test_copias_iguales_al_original(self):
        """Una copia vieja a propósito se nombra distinto, como `proto-anterior.js`, y queda fuera."""
        copias = sorted(p for d in ("pruebas", "tests") for p in (RAIZ / d).rglob("proto.js"))
        self.assertTrue(copias)
        original = ORIGINAL.read_bytes()
        distintas = [str(p.relative_to(RAIZ)) for p in copias if p.read_bytes() != original]
        self.assertEqual(distintas, [], "Copia distinta de skills/spec-a-html/assets/proto.js; cópiala de nuevo.")


if __name__ == "__main__":
    unittest.main()
