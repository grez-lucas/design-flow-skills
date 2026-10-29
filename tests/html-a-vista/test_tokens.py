"""Pruebas de skills/html-a-vista/scripts/tokens.py.

Uso: python3 -m unittest discover -s tests/html-a-vista -v
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "skills" / "html-a-vista" / "scripts" / "tokens.py"
FIX = Path(__file__).resolve().parent / "fixtures" / "tokens"
PRUEBAS = RAIZ / "pruebas" / "html-a-vista"
TOKENS_CON_DS = PRUEBAS / "fixtures" / "con-ds" / "design" / "tokens.css"
MOCKUPS = PRUEBAS / "fixtures" / "mockups"


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

    def test_cada_tema_contra_los_tokens_de_su_tema(self):
        claro = self.filas[("#e6efe8", "color")]
        self.assertEqual(claro["bloque"], ":root", "un valor del tema claro no va a un token del oscuro")
        oscuro = self.filas[("#131916", "color")]
        self.assertEqual((oscuro["token"], oscuro["bloque"], oscuro["dentro"]), ("--color-bg", '[data-theme="dark"]', True))

    def test_radio_de_pildora_va_al_radio_completo(self):
        f = self.fila("999px", "radius")
        self.assertEqual((f["token"], f["dentro"]), ("--radius-full", True))

    def test_umbral_declarado(self):
        r = correr("mapear", FIX / "tokens.css", FIX / "mockup.html", "--json")
        umbral = json.loads(r.stdout)["umbral"]
        self.assertEqual(umbral["color"], 2.0)
        self.assertIn("medida", umbral)

    def test_cada_valor_dice_que_selectores_pinta(self):
        self.assertEqual(self.fila("#7a3df0")["selectores"], [".b"])
        self.assertEqual(self.fila("#2f7d4f")["selectores"], [".d"])
        self.assertEqual(self.fila("#b3261f")["selectores"], ["style en línea"])
        fuera = correr("mapear", FIX / "tokens.css", FIX / "mockup.html").stdout.split("## Fuera del umbral")[1]
        fila = next(l for l in fuera.splitlines() if l.startswith("| #7a3df0 "))
        self.assertIn(".b", fila)

    def test_dentro_del_umbral_muestra_el_valor_del_token_cuando_no_es_igual(self):
        dentro = correr("mapear", FIX / "tokens.css", FIX / "mockup.html").stdout.split("## Fuera del umbral")[0]
        filas = {l.split("|")[1].strip() + " " + l.split("|")[2].strip(): l for l in dentro.splitlines() if l.startswith("| ") and "---" not in l}
        self.assertIn("--space-3 (12px)", filas["13px space"])
        self.assertIn("--color-primary (#2f7d4f)", filas["#2f7d50 color"])
        self.assertNotIn("(", filas["rgb(47,125,79) color"].split("|")[4], "a distancia 0 el token basta")

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
        self.assertEqual(radios, {"10px": "12px", "999px": "9999px"})


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


    def test_un_solo_archivo_se_revisa_contra_si_mismo(self):
        r = correr("verificar", FIX / "casi-iguales-entre-si.css", "--json")
        self.assertEqual(r.returncode, 1, r.stdout)
        pares = [(c["token"], c["existente"]) for c in json.loads(r.stdout)["casi_iguales"]]
        self.assertEqual(pares, [("--color-bg", "--color-surface-alt")],
                         "los alias de igual valor no cuentan y cada tema se compara solo consigo")
        texto = correr("verificar", FIX / "casi-iguales-entre-si.css").stdout
        self.assertIn("--color-bg (#f6f7f3)", texto)
        self.assertIn("--color-surface-alt (#f0f2f5)", texto)

    def test_un_solo_archivo_sin_pares_casi_iguales_pasa(self):
        r = correr("verificar", FIX / "tokens.css", "--json")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(json.loads(r.stdout)["casi_iguales"], [])


class MockupsDeLasEvals(unittest.TestCase):
    """Los mockups de pruebas/html-a-vista contra el design system de fixtures/con-ds, o consolidados sin él."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        r = subprocess.run([sys.executable, "-B", str(PRUEBAS / "generar.py"), str(cls.tmp)], capture_output=True, text=True)
        if r.returncode != 0:
            raise AssertionError(r.stderr)
        cls.grande = cls.tmp / "grande.html"

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_el_design_system_de_las_evals_existe(self):
        self.assertTrue(TOKENS_CON_DS.is_file(), TOKENS_CON_DS)
        self.assertIn("--color-warning: #b26b00;", TOKENS_CON_DS.read_text())

    def mapeo(self, mockup):
        r = correr("mapear", TOKENS_CON_DS, mockup, "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        return {(f["valor"], f["categoria"]): f for f in json.loads(r.stdout)["valores"]}

    def test_los_valores_a_decidir_quedan_fuera_del_umbral_con_su_token_mas_cercano(self):
        casos = {
            "chico": (MOCKUPS / "chico.html", "#e07a1f", "--color-warning", "#b26b00", [".estado--pendiente"]),
            "demo": (MOCKUPS / "demo.html", "#7b4fd6", "--color-info", "#1f6f8b", [".programado"]),
            "grande": (self.grande, "#e07a1f", "--color-warning", "#b26b00", [".atrasada"]),
        }
        for caso, (mockup, valor, token, valor_token, selectores) in casos.items():
            with self.subTest(caso=caso):
                f = self.mapeo(mockup)[(valor, "color")]
                self.assertEqual((f["token"], f["valor_token"], f["bloque"], f["dentro"]), (token, valor_token, ":root", False))
                self.assertGreater(f["distancia"], 2.0)
                self.assertEqual(f["selectores"], selectores)
                md = correr("mapear", TOKENS_CON_DS, mockup).stdout
                dentro, fuera = md.split("## Fuera del umbral")
                self.assertIn(f"| {valor} | color |", fuera)
                self.assertNotIn(valor, dentro)

    def test_el_tema_oscuro_del_grande_va_a_los_tokens_oscuros(self):
        f = self.mapeo(self.grande)[("#101712", "color")]
        self.assertEqual((f["token"], f["bloque"], f["distancia"], f["dentro"]), ("--color-bg", '[data-theme="dark"]', 0, True))

    def test_la_consolidacion_del_grande_queda_en_escala_de_4_px_y_verificar_sale_con_0(self):
        r = correr("consolidar", self.grande, "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(r.stdout)
        escala = [g for g in d["medidas"] if g["categoria"] in ("space", "radius", "size")]
        self.assertEqual({g["categoria"] for g in escala}, {"space", "radius", "size"})
        fuera = [g["propuesta"] for g in escala if g["propuesta"] != "9999px" and int(g["propuesta"].removesuffix("px")) % 4]
        self.assertEqual(fuera, [])
        propuesta = {(g["categoria"], m["valor"]): g["propuesta"] for g in d["medidas"] for m in g["miembros"]}
        self.assertEqual(propuesta[("space", "22px")], "24px")
        self.assertEqual(propuesta[("space", "9px")], "8px")
        self.assertEqual(propuesta[("radius", "7px")], "8px")
        self.assertEqual(propuesta[("radius", "999px")], "9999px")
        self.assertEqual(propuesta[("size", "210px")], "212px")
        fondo = next(g for g in d["colores"] if "#0e1410" in [m["valor"] for m in g["miembros"]])
        self.assertEqual({"#111814", "#101712", "#0f1511"} - {m["valor"] for m in fondo["miembros"]}, set(),
                         "el fondo oscuro de cada módulo es un solo color")
        lineas = [f"  --color-{n}: {g['representante']};" for n, g in enumerate(d["colores"], start=1)]
        for categoria, prefijo in (("space", "--space"), ("radius", "--radius"), ("size", "--size"), ("font-size", "--font-size")):
            grupos = [g for g in d["medidas"] if g["categoria"] == categoria]
            lineas += [f"  {prefijo}-{n}: {g['propuesta']};" for n, g in enumerate(grupos, start=1)]
        tokens = self.tmp / "tokens.css"
        tokens.write_text(":root {\n" + "\n".join(lineas) + "\n}\n")
        r = correr("verificar", tokens, "--json")
        self.assertEqual(json.loads(r.stdout)["casi_iguales"], [])
        self.assertEqual(r.returncode, 0, r.stdout)


class Uso(unittest.TestCase):
    def test_uso_incorrecto(self):
        self.assertEqual(correr().returncode, 2)
        self.assertEqual(correr("mapear", FIX / "tokens.css").returncode, 2)
        self.assertEqual(correr("inventar", FIX / "tokens.css", FIX / "mockup.html").returncode, 2)


if __name__ == "__main__":
    unittest.main()
