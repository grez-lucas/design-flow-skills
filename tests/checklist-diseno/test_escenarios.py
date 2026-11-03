"""Pruebas del cruce de escenarios de revisar.py: los de cada vista contra la tabla `## Escenarios en pantalla` del spec.

Un escenario de una vista que no está en la tabla ni es base bloquea; uno de la tabla que ninguna vista declara, y un
spec sin la tabla o una vista sin spec, van a "Conviene mirar" (AVISO).
Uso: python3 -m unittest discover -s tests/checklist-diseno -v
"""
import importlib.util
import io
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "skills" / "checklist-diseno" / "scripts" / "revisar.py"
PROTO = RAIZ / "skills" / "spec-a-html" / "assets" / "proto.js"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

spec = importlib.util.spec_from_file_location("revisar", SCRIPT)
revisar = importlib.util.module_from_spec(spec)
sys.modules["revisar"] = revisar
spec.loader.exec_module(revisar)

BASE = "normal, vacio, cargando, error, sin-permiso, muchos-datos"

SPEC = """# Spec · Pedidos

## Historias

### US-PED-001 · Ver pedidos del día

**COMO** encargado de bodega
**QUIERO** ver los pedidos del día
**PARA** despacharlos a tiempo

### Escenario 1: Hay pedidos del día

```gherkin
Dado que hay pedidos del día
Cuando entro a "Pedidos"
Entonces veo cada pedido con su cliente y su hora de retiro
```

### Escenario 2: Pedido atrasado

```gherkin
Dado que un pedido pasó su hora de retiro
Cuando entro a "Pedidos"
Entonces veo el pedido marcado como atrasado
```

### Escenario 3: Lector de códigos desconectado

```gherkin
Dado que el lector de códigos está desconectado
Cuando entro a cualquier pantalla
Entonces veo un aviso que dice que el lector no responde
```

## Estados por vista

- Pedidos: normal, vacío, cargando, error, sin permiso, muchos datos.

## Escenarios en pantalla

| Slug | Nombre | Alcance |
| :--- | :--- | :--- |
| `pedido-atrasado` | Pedido atrasado | Pedidos |
| `lector-desconectado` | Lector de códigos desconectado | global |
"""

SIN_TABLA = """# Spec · Pedidos

## Historias

### US-PED-001 · Ver pedidos del día

Como encargado de bodega, quiero ver los pedidos del día, para despacharlos a tiempo.

- Escenario 1: Dado que hay pedidos del día, cuando entro, entonces veo cada pedido.

## Estados por vista

- Pedidos: normal, vacío, cargando, error, sin permiso, muchos datos, pedido-atrasado.
"""


def vista(escenarios, meta='<meta name="tickets" content="DEMO-1">'):
    return (FIXTURES / "limpia.html").read_text().replace('<meta name="tickets" content="DEMO-1">', meta).replace(
        f'data-escenarios="{BASE}"', f'data-escenarios="{escenarios}"')


class LeerSpec(unittest.TestCase):
    def test_lee_los_escenarios_y_la_tabla(self):
        leido = revisar.leer_spec(SPEC)
        self.assertEqual(leido["escenarios"], ["Hay pedidos del día", "Pedido atrasado", "Lector de códigos desconectado"])
        self.assertEqual(leido["tabla"], [
            {"slug": "pedido-atrasado", "nombre": "Pedido atrasado", "alcance": "Pedidos"},
            {"slug": "lector-desconectado", "nombre": "Lector de códigos desconectado", "alcance": "global"},
        ])
        self.assertEqual(leido["errores"], [])

    def test_sin_la_seccion_la_tabla_es_none_y_no_es_error(self):
        leido = revisar.leer_spec(SIN_TABLA)
        self.assertIsNone(leido["tabla"])
        self.assertEqual(leido["errores"], [])
        self.assertEqual(leido["escenarios"], [])

    def test_los_encabezados_dentro_de_un_bloque_de_codigo_no_cuentan(self):
        texto = SPEC.replace("## Estados por vista", "```markdown\n### Escenario 9: Ejemplo\n## Escenarios en pantalla\n```\n\n## Estados por vista")
        leido = revisar.leer_spec(texto)
        self.assertNotIn("Ejemplo", leido["escenarios"])
        self.assertEqual(len(leido["tabla"]), 2)
        self.assertEqual(leido["errores"], [])

    def test_solo_cuenta_el_encabezado_de_tercer_nivel_con_numero(self):
        texto = SPEC.replace("### Escenario 2: Pedido atrasado", "#### Escenario 2: Pedido atrasado")
        leido = revisar.leer_spec(texto)
        self.assertNotIn("Pedido atrasado", leido["escenarios"])
        texto = SPEC.replace("### Escenario 2: Pedido atrasado", "### Escenario: Pedido atrasado")
        self.assertNotIn("Pedido atrasado", revisar.leer_spec(texto)["escenarios"])

    def test_nombre_de_la_tabla_que_no_coincide_con_ningun_escenario_es_error(self):
        leido = revisar.leer_spec(SPEC.replace("| Pedido atrasado | Pedidos |", "| Pedido con atraso | Pedidos |"))
        self.assertEqual(len(leido["errores"]), 1, leido["errores"])
        self.assertIn("`pedido-atrasado`", leido["errores"][0])
        self.assertIn("Pedido con atraso", leido["errores"][0])
        self.assertIn("### Escenario", leido["errores"][0])

    def test_la_seccion_sin_tabla_o_con_otras_columnas_es_error(self):
        sin_tabla = SPEC.split("| Slug |")[0] + "Ninguno.\n"
        otras = SPEC.replace("| Slug | Nombre | Alcance |", "| Slug | Nombre | Pantalla |")
        for caso, texto in (("sin tabla", sin_tabla), ("otras columnas", otras)):
            with self.subTest(caso=caso):
                leido = revisar.leer_spec(texto)
                self.assertEqual(len(leido["errores"]), 1, leido["errores"])
                self.assertIn("Slug | Nombre | Alcance", leido["errores"][0])

    def test_filas_mal_formadas_son_error(self):
        casos = {
            "slug con mayúsculas": ("| `pedido-atrasado` |", "| `Pedido-Atrasado` |", "`Pedido-Atrasado`"),
            "slug con tilde": ("| `pedido-atrasado` |", "| `pedido-atrasádo` |", "`pedido-atrasádo`"),
            "alcance vacío": ("| Pedido atrasado | Pedidos |", "| Pedido atrasado |  |", "alcance"),
            "celdas de más": ("| Pedido atrasado | Pedidos |", "| Pedido atrasado | Pedidos | extra |", "tres columnas"),
            "slug repetido en el mismo alcance": ("| `lector-desconectado` | Lector de códigos desconectado | global |",
                                                  "| `pedido-atrasado` | Lector de códigos desconectado | Pedidos |", "repite"),
        }
        for caso, (viejo, nuevo, marca) in casos.items():
            with self.subTest(caso=caso):
                leido = revisar.leer_spec(SPEC.replace(viejo, nuevo))
                self.assertTrue(leido["errores"], caso)
                self.assertTrue(any(marca in e for e in leido["errores"]), leido["errores"])

    def test_el_mismo_slug_en_dos_pantallas_no_es_error(self):
        texto = SPEC.replace("| `lector-desconectado` | Lector de códigos desconectado | global |",
                             "| `lector-desconectado` | Lector de códigos desconectado | global |\n"
                             "| `vacio` | Hay pedidos del día | Pedidos |\n| `vacio` | Pedido atrasado | Despacho |")
        leido = revisar.leer_spec(texto)
        self.assertEqual(leido["errores"], [])
        self.assertEqual([f["slug"] for f in leido["tabla"]], ["pedido-atrasado", "lector-desconectado", "vacio", "vacio"])

    def test_el_slug_va_con_o_sin_comillas_invertidas(self):
        leido = revisar.leer_spec(SPEC.replace("| `pedido-atrasado` |", "| pedido-atrasado |"))
        self.assertEqual(leido["tabla"][0]["slug"], "pedido-atrasado")
        self.assertEqual(leido["errores"], [])


class Cruce(unittest.TestCase):
    def setUp(self):
        self.repo = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.repo)
        self.design = self.repo / "design"
        for epica in ("pedidos", "despacho"):
            (self.design / "vistas" / epica).mkdir(parents=True)
        shutil.copy(FIXTURES / "tokens.css", self.design / "tokens.css")
        shutil.copy(FIXTURES / "components.css", self.design / "components.css")
        shutil.copy(PROTO, self.design / "proto.js")
        (self.repo / "specs" / "pedidos").mkdir(parents=True)
        self.spec = self.repo / "specs" / "pedidos" / "spec.md"
        self.spec.write_text(SPEC)

    def escribir(self, ruta, texto):
        p = self.design / "vistas" / ruta
        p.write_text(texto)
        return p

    def cruzar(self, *vistas):
        return revisar.cruzar_escenarios(self.repo, list(vistas))

    def main(self, *vistas):
        salida = io.StringIO()
        with mock.patch.object(sys, "argv", ["revisar.py", str(self.repo), *map(str, vistas)]), redirect_stdout(salida):
            codigo = revisar.main()
        return codigo, salida.getvalue()

    def test_spec_con_escenario_global_declarado_en_dos_vistas_no_tiene_hallazgos(self):
        lista = self.escribir("pedidos/lista.html", vista(f"{BASE}, pedido-atrasado, lector-desconectado"))
        detalle = self.escribir("pedidos/detalle.html", vista(f"{BASE}, lector-desconectado"))
        por_vista, por_spec = self.cruzar(lista, detalle)
        self.assertEqual(por_vista, {lista: ([], []), detalle: ([], [])})
        self.assertEqual(por_spec, {"specs/pedidos/spec.md": ([], [])})

    def test_escenario_de_la_vista_que_no_esta_en_la_tabla_bloquea(self):
        lista = self.escribir("pedidos/lista.html", vista(f"{BASE}, pedido-atrasado, lector-desconectado, bascula-apagada"))
        (bloquea, avisa), = self.cruzar(lista)[0].values()
        self.assertEqual(len(bloquea), 1, bloquea)
        self.assertIn("`bascula-apagada`", bloquea[0])
        self.assertIn("specs/pedidos/spec.md", bloquea[0])
        self.assertEqual(avisa, [])

    def test_escenarios_base_sin_respaldo_en_el_spec_no_bloquean(self):
        lista = self.escribir("pedidos/lista.html", vista(f"{BASE}, pedido-atrasado, lector-desconectado"))
        self.assertEqual(self.cruzar(lista)[0][lista], ([], []))

    def test_escenario_de_la_tabla_que_ninguna_vista_declara_avisa_en_el_spec(self):
        lista = self.escribir("pedidos/lista.html", vista(f"{BASE}, lector-desconectado"))
        por_vista, por_spec = self.cruzar(lista)
        self.assertEqual(por_vista[lista], ([], []))
        bloquea, avisa = por_spec["specs/pedidos/spec.md"]
        self.assertEqual(bloquea, [])
        self.assertEqual(len(avisa), 1, avisa)
        self.assertIn("`pedido-atrasado`", avisa[0])

    def test_la_vista_que_lo_declara_cuenta_aunque_no_se_revise(self):
        lista = self.escribir("pedidos/lista.html", vista(f"{BASE}, lector-desconectado"))
        self.escribir("pedidos/detalle.html", vista(f"{BASE}, pedido-atrasado"))
        self.assertEqual(self.cruzar(lista)[1]["specs/pedidos/spec.md"], ([], []))

    def test_nombre_de_la_tabla_que_no_coincide_bloquea_en_el_spec(self):
        self.spec.write_text(SPEC.replace("| Pedido atrasado | Pedidos |", "| Pedido con atraso | Pedidos |"))
        lista = self.escribir("pedidos/lista.html", vista(f"{BASE}, pedido-atrasado, lector-desconectado"))
        por_vista, por_spec = self.cruzar(lista)
        self.assertEqual(por_vista[lista], ([], []))
        bloquea, _ = por_spec["specs/pedidos/spec.md"]
        self.assertEqual(len(bloquea), 1, bloquea)
        self.assertIn("Pedido con atraso", bloquea[0])
        codigo, salida = self.main(lista)
        self.assertEqual(codigo, 1)
        self.assertIn("## Escenarios del spec: specs/pedidos/spec.md", salida)

    def test_spec_sin_la_tabla_avisa_y_no_bloquea(self):
        self.spec.write_text(SIN_TABLA)
        lista = self.escribir("pedidos/lista.html", vista(f"{BASE}, pedido-atrasado"))
        por_vista, por_spec = self.cruzar(lista)
        bloquea, avisa = por_vista[lista]
        self.assertEqual(bloquea, [])
        self.assertEqual(len(avisa), 1, avisa)
        self.assertIn("## Escenarios en pantalla", avisa[0])
        self.assertIn("specs/pedidos/spec.md", avisa[0])
        self.assertEqual(por_spec, {"specs/pedidos/spec.md": ([], [])})
        codigo, _ = self.main(lista)
        self.assertEqual(codigo, 0)

    def test_mockup_sin_spec_avisa_y_no_bloquea(self):
        sin_spec = self.escribir("despacho/ruta.html", vista(f"{BASE}, camion-lleno"))
        por_vista, por_spec = self.cruzar(sin_spec)
        bloquea, avisa = por_vista[sin_spec]
        self.assertEqual(bloquea, [])
        self.assertEqual(len(avisa), 1, avisa)
        self.assertIn("specs/despacho/spec.md", avisa[0])
        self.assertEqual(por_spec, {})
        codigo, _ = self.main(sin_spec)
        self.assertEqual(codigo, 0)

    def test_el_meta_spec_manda_sobre_la_epica(self):
        (self.repo / "specs" / "general").mkdir()
        (self.repo / "specs" / "general" / "spec.md").write_text(SPEC.replace("`pedido-atrasado`", "`ruta-cortada`"))
        ruta = self.escribir("despacho/ruta.html", vista(f"{BASE}, ruta-cortada, lector-desconectado",
                                                         meta='<meta name="spec" content="specs/general/spec.md">'))
        por_vista, por_spec = self.cruzar(ruta)
        self.assertEqual(por_vista[ruta], ([], []))
        self.assertEqual(list(por_spec), ["specs/general/spec.md"])

    def test_un_meta_spec_que_no_existe_no_suma_avisos_al_bloqueo_que_ya_tiene(self):
        ruta = self.escribir("pedidos/ruta.html", vista(f"{BASE}, camion-lleno", meta='<meta name="spec" content="specs/envios/spec.md">'))
        por_vista, por_spec = self.cruzar(ruta)
        self.assertEqual(por_vista[ruta], ([], []))
        self.assertEqual(por_spec, {})

    def test_main_pone_el_bloqueo_de_la_vista_en_su_seccion_y_sale_con_1(self):
        lista = self.escribir("pedidos/lista.html", vista(f"{BASE}, pedido-atrasado, lector-desconectado, bascula-apagada"))
        codigo, salida = self.main(lista)
        self.assertEqual(codigo, 1)
        seccion = salida.split("## design/vistas/pedidos/lista.html", 1)[1].split("\n## ", 1)[0]
        self.assertIn("BLOQUEA", seccion)
        self.assertIn("`bascula-apagada`", seccion)


if __name__ == "__main__":
    unittest.main()
