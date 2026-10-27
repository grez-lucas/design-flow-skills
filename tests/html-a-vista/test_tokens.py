"""Pruebas de skills/html-a-vista/scripts/tokens.py.

Uso: python3 -m unittest discover -s tests/html-a-vista -v
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "skills" / "html-a-vista" / "scripts" / "tokens.py"
FIX = Path(__file__).resolve().parent / "fixtures" / "tokens"


def correr(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True)


class Mapear(unittest.TestCase):
    def setUp(self):
        r = correr("mapear", FIX / "tokens.css", FIX / "mockup.html", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.filas = {(f["valor"], f["categoria"]): f for f in json.loads(r.stdout)["valores"]}

    def fila(self, valor, categoria="color"):
        return self.filas[(valor, categoria)]

    def test_color_cercano_va_al_token_por_distancia_perceptual(self):
        f = self.fila("#2f7d50")
        self.assertEqual((f["token"], f["dentro"]), ("--color-primary", True))
        self.assertLess(f["distancia"], 1)
        self.assertEqual(self.fila("#b3261f")["token"], "--color-danger")

    def test_rgb_y_hsl_se_leen_como_el_hex_equivalente(self):
        self.assertEqual((self.fila("rgb(47,125,79)")["token"], self.fila("rgb(47,125,79)")["distancia"]), ("--color-primary", 0))
        f = self.fila("hsl(0,0%,100%)")
        self.assertEqual((f["token"], f["bloque"], f["distancia"]), ("--color-bg", ":root", 0))

    def test_color_lejano_queda_fuera_con_el_token_mas_cercano(self):
        f = self.fila("#7a3df0")
        self.assertFalse(f["dentro"])
        self.assertTrue(f["token"].startswith("--color-"))

    def test_el_mas_cercano_es_perceptual_y_no_por_rgb(self):
        f = self.fila("#1c6e04")
        self.assertEqual(f["token"], "--color-primary", "por RGB el más cercano sería --color-text")

    def test_la_transparencia_cuenta_en_la_distancia(self):
        f = self.fila("rgba(0,0,0,0.4)")
        self.assertEqual((f["token"], f["dentro"]), ("--color-overlay", False))

    def test_medidas_al_paso_de_escala_de_su_categoria(self):
        self.assertEqual((self.fila("13px", "space")["token"], self.fila("13px", "space")["dentro"]), ("--space-3", True))
        self.assertEqual(self.fila("13px", "space")["ocurrencias"], 2)
        catorce = self.fila("14px", "space")
        self.assertEqual((catorce["ocurrencias"], catorce["dentro"], catorce["token"]), (3, False, "--space-3"))
        self.assertTrue(self.fila("15px", "font-size")["dentro"])
        self.assertFalse(self.fila("10px", "radius")["dentro"])
        self.assertFalse(self.fila("10px", "space")["dentro"])
        self.assertNotIn(("4px", "space"), self.filas, "las medidas de box-shadow no son espacios")

    def test_umbral_declarado(self):
        r = correr("mapear", FIX / "tokens.css", FIX / "mockup.html", "--json")
        umbral = json.loads(r.stdout)["umbral"]
        self.assertEqual(umbral["color"], 2.0)
        self.assertIn("medida", umbral)

    def test_markdown_separa_lo_que_producto_decide(self):
        r = correr("mapear", FIX / "tokens.css", FIX / "mockup.html")
        self.assertEqual(r.returncode, 0, r.stderr)
        dentro, fuera = r.stdout.split("## Fuera del umbral")
        self.assertIn("#2f7d50", dentro)
        self.assertIn("#7a3df0", fuera)
        self.assertNotIn("#7a3df0", dentro)
        self.assertNotIn("#2f7d50", fuera)


class Consolidar(unittest.TestCase):
    def setUp(self):
        r = correr("consolidar", FIX / "mockup.html", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.d = json.loads(r.stdout)

    def test_agrupa_colores_parecidos(self):
        grupo = next(g for g in self.d["colores"] if "#2f7d50" in [m["valor"] for m in g["miembros"]])
        self.assertEqual(sorted(m["valor"] for m in grupo["miembros"]), ["#2f7d4f", "#2f7d50", "rgb(47,125,79)"])
        self.assertEqual(grupo["ocurrencias"], 3)
        lejano = next(g for g in self.d["colores"] if "#7a3df0" in [m["valor"] for m in g["miembros"]])
        self.assertEqual(len(lejano["miembros"]), 1)

    def test_agrupa_por_color_base_y_conserva_cada_opacidad(self):
        negro = next(g for g in self.d["colores"] if "#000" in [m["valor"] for m in g["miembros"]])
        self.assertEqual(sorted(m["valor"] for m in negro["miembros"]), ["#000", "rgba(0,0,0,0.4)"])
        self.assertEqual(sorted(m["opacidad"] for m in negro["miembros"]), [0.4, 1.0])

    def test_lleva_espacios_y_radios_a_la_escala_de_4px(self):
        espacios = {m["valor"]: g["propuesta"] for g in self.d["medidas"] if g["categoria"] == "space" for m in g["miembros"]}
        self.assertEqual(espacios, {"14px": "16px", "13px": "12px", "10px": "12px"})
        radios = {m["valor"]: g["propuesta"] for g in self.d["medidas"] if g["categoria"] == "radius" for m in g["miembros"]}
        self.assertEqual(radios, {"10px": "12px"})


class Verificar(unittest.TestCase):
    def test_tokens_nuevos_distintos_pasan(self):
        r = correr("verificar", FIX / "tokens.css", FIX / "despues-ok.css", "--json")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(json.loads(r.stdout)["casi_iguales"], [])

    def test_token_nuevo_dentro_del_umbral_de_uno_existente_falla(self):
        r = correr("verificar", FIX / "tokens.css", FIX / "despues-casi-igual.css", "--json")
        self.assertEqual(r.returncode, 1)
        pares = [(c["token"], c["existente"]) for c in json.loads(r.stdout)["casi_iguales"]]
        self.assertEqual(pares, [("--color-primary-2", "--color-primary"), ("--space-3b", "--space-3")])


class Uso(unittest.TestCase):
    def test_uso_incorrecto(self):
        self.assertEqual(correr().returncode, 2)
        self.assertEqual(correr("mapear", FIX / "tokens.css").returncode, 2)
        self.assertEqual(correr("inventar", FIX / "tokens.css", FIX / "mockup.html").returncode, 2)


if __name__ == "__main__":
    unittest.main()
