"""Pruebas de skills/html-a-vista/scripts/inventario.py.

Uso: python3 -m unittest discover -s tests/html-a-vista -v
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "skills" / "html-a-vista" / "scripts" / "inventario.py"
FIX = Path(__file__).resolve().parent / "fixtures" / "inventario"


def inventario(vista, *originales, formato="--json"):
    args = [sys.executable, str(SCRIPT), str(FIX / vista), *(str(FIX / o) for o in originales)]
    return subprocess.run(args + ([formato] if formato else []), capture_output=True, text=True)


class Inventario(unittest.TestCase):
    def datos(self, vista, *originales):
        r = inventario(vista, *originales)
        self.assertIn(r.returncode, (0, 1), r.stderr)
        return r.returncode, json.loads(r.stdout)

    def test_vista_fiel_no_tiene_faltantes(self):
        codigo, d = self.datos("vista-fiel.html", "original.html", "modal.html")
        for clave in ("textos", "controles", "campos", "textos_js"):
            self.assertEqual(d[clave]["faltan"], [], clave)
            self.assertEqual(d[clave]["presentes"], d[clave]["total"], clave)
        self.assertEqual(codigo, 0)

    def test_textos_controles_y_campos_que_faltan(self):
        codigo, d = self.datos("vista-incompleta.html", "original.html", "modal.html")
        self.assertEqual(codigo, 1)
        self.assertEqual(d["textos"]["faltan"], ["Correo de contacto", "nombre@example.com", "Exportar", "Cerrar aviso",
                                                 "¿Confirmas el pedido de esta semana?", "Sí, confirmar"])
        self.assertEqual(d["controles"]["faltan"], ["Exportar", "Cerrar aviso", "Sí, confirmar"])
        self.assertEqual(d["campos"]["faltan"], ["Correo de contacto"])

    def test_normaliza_espacios_y_mayusculas_pero_no_cuenta_comentarios(self):
        _, d = self.datos("vista-incompleta.html", "original.html")
        self.assertNotIn("Pedidos de la semana", d["textos"]["faltan"])
        self.assertIn("Exportar", d["textos"]["faltan"])

    def test_no_espera_el_control_de_prototipo_ni_textos_del_svg(self):
        _, d = self.datos("vista-fiel.html", "original.html")
        self.assertNotIn("DEMO: plan vencido", d["textos"]["faltan"] + d["controles"]["faltan"])
        self.assertEqual(d["estados"]["controles_prototipo_original"], ["DEMO: plan vencido"])
        _, d = self.datos("vista-incompleta.html", "original.html")
        self.assertNotIn("Texto del gráfico", d["textos"]["faltan"])

    def test_textos_que_arma_el_js_valen_tambien_en_comentarios(self):
        _, fiel = self.datos("vista-fiel.html", "original.html")
        self.assertEqual(fiel["textos_js"], {"total": 1, "presentes": 1, "faltan": []})
        _, incompleta = self.datos("vista-incompleta.html", "original.html")
        self.assertEqual(incompleta["textos_js"]["faltan"], ["Planilla enviada a"])

    def test_estados_prototipo_y_data_state_ajeno_en_la_vista(self):
        _, d = self.datos("vista-incompleta.html", "original.html")
        self.assertEqual(d["estados"]["escenarios_vista"], ["normal", "vacio"])
        self.assertEqual(d["estados"]["data_state_original"], ["lleno"])
        self.assertEqual(d["estados"]["data_state_ajeno_en_vista"], ["lleno"])
        self.assertEqual(d["estados"]["controles_prototipo_en_vista"], ["DEMO: plan vencido"])
        _, fiel = self.datos("vista-fiel.html", "original.html")
        self.assertEqual(fiel["estados"]["data_state_ajeno_en_vista"], [])
        self.assertEqual(fiel["estados"]["controles_prototipo_en_vista"], [])

    def test_textos_nuevos_de_la_vista(self):
        _, d = self.datos("vista-fiel.html", "original.html", "modal.html")
        self.assertEqual(d["textos_nuevos"], ["Tu plan venció."])

    def test_informe_en_markdown(self):
        r = inventario("vista-incompleta.html", "original.html", formato=None)
        self.assertEqual(r.returncode, 1)
        for texto in ("## Textos", "## Controles", "## Campos", "## Estados", "Correo de contacto", "DEMO: plan vencido", "otro significado: lleno"):
            self.assertIn(texto, r.stdout)

    def test_uso_incorrecto(self):
        r = subprocess.run([sys.executable, str(SCRIPT), str(FIX / "vista-fiel.html")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        r = inventario("no-existe.html", "original.html")
        self.assertEqual(r.returncode, 2)
        self.assertIn("no-existe.html", r.stderr)


if __name__ == "__main__":
    unittest.main()
