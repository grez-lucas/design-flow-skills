"""Pruebas de los grade.py de pruebas/: una corrida vacía o sin informe falla entera.

Uso: python3 -m unittest discover -s tests/pruebas -v
"""
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PRUEBAS = Path(__file__).resolve().parents[2] / "pruebas"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
REQUERIDO = {"checklist-diseno": "informe.md", "grilling-es": "transcripcion.md",
             "spec-a-html": "notas.md", "spec-a-tickets": "notas.md", "html-a-vista": "notas.md"}


class CorridaSinSalidas(unittest.TestCase):
    def preparar(self, skill):
        it = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, it)
        subprocess.run([sys.executable, str(PRUEBAS / "preparar.py"), skill, str(it)], check=True, capture_output=True)
        return it

    def calificar(self, skill, it):
        r = subprocess.run([sys.executable, str(PRUEBAS / skill / "grade.py"), str(it)], capture_output=True, text=True)
        notas = {p.relative_to(it).parent.as_posix(): json.loads(p.read_text()) for p in it.glob("*/*/run-*/grading.json")}
        return r, notas

    def test_corrida_vacia_o_sin_informe_falla_entera(self):
        for skill, requerido in REQUERIDO.items():
            with self.subTest(skill=skill):
                it = self.preparar(skill)
                prueba = sorted(it.iterdir())[0]
                (prueba / "with_skill" / "run-1" / "outputs" / requerido).write_text("Salida de la corrida.\n")
                (prueba / "with_skill" / "run-2" / "outputs").mkdir(parents=True)
                r, notas = self.calificar(skill, it)
                self.assertNotEqual(r.returncode, 0, r.stdout)
                for corrida in (f"{prueba.name}/with_skill/run-2", f"{prueba.name}/without_skill/run-1"):
                    self.assertIn("error", notas[corrida], corrida)
                    self.assertEqual(notas[corrida]["summary"]["passed"], 0, corrida)
                    self.assertEqual(notas[corrida]["expectations"], [], corrida)
                self.assertNotIn("error", notas[f"{prueba.name}/with_skill/run-1"])

    def test_iteracion_sin_corridas_falla(self):
        for skill in REQUERIDO:
            with self.subTest(skill=skill):
                it = Path(tempfile.mkdtemp())
                self.addCleanup(shutil.rmtree, it)
                r, _ = self.calificar(skill, it)
                self.assertNotEqual(r.returncode, 0)


def secciones(informe):
    """Devuelve (líneas fuera de secciones de severidad, [(etiqueta, [ítems])]) en orden, para reescribir el informe."""
    out, actual = [], None
    for linea in informe.splitlines():
        if linea in ("Bloquea:", "Conviene mirar:"):
            actual = (linea, [])
            out.append(actual)
        elif actual and linea.startswith("- "):
            actual[1].append(linea[2:])
        else:
            actual = None
            out.append(linea)
    return out


def reescribir(informe, forma):
    lineas = []
    for x in secciones(informe):
        if isinstance(x, str):
            lineas.append(x)
            continue
        etiqueta, its = x
        bloquea = etiqueta == "Bloquea:"
        if forma == "tabla":
            lineas += ["| Hallazgo | Severidad |", "| :--- | :--- |"]
            lineas += [f"| {i} | {'Bloquea' if bloquea else 'Aviso'} |" for i in its]
        elif forma == "viñeta" and bloquea:
            lineas += [f"- **Bloquea:** {i}" for i in its]
        else:
            nueva = {"original": etiqueta, "encabezado": "### Bloqueos" if bloquea else "### Conviene mirar",
                     "negrita": "**Bloqueantes**" if bloquea else "**Conviene mirar**", "viñeta": etiqueta}[forma]
            lineas += [nueva] + [f"- {i}" for i in its]
    return "\n".join(lineas) + "\n"


class SeveridadSinFormatoFijo(unittest.TestCase):
    def test_mismo_informe_en_cinco_formas_da_el_mismo_puntaje(self):
        informe = (FIXTURES / "informe-checklist.md").read_text()
        it = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, it)
        subprocess.run([sys.executable, str(PRUEBAS / "preparar.py"), "checklist-diseno", str(it)], check=True, capture_output=True)
        base = it / "eval-1-defectos" / "with_skill"
        formas = ["original", "encabezado", "viñeta", "tabla", "negrita"]
        for n, forma in enumerate(formas, start=2):
            shutil.copytree(base / "run-1", base / f"run-{n}", symlinks=True)
            (base / f"run-{n}" / "outputs" / "informe.md").write_text(reescribir(informe, forma))
        shutil.rmtree(it / "eval-1-defectos" / "without_skill")
        for otra in it.iterdir():
            if otra.name != "eval-1-defectos":
                shutil.rmtree(otra)
        (base / "run-1" / "outputs" / "informe.md").write_text(informe)
        subprocess.run([sys.executable, str(PRUEBAS / "checklist-diseno" / "grade.py"), str(it)], check=True, capture_output=True)
        resultados = {}
        for n, forma in enumerate(["sin reescribir"] + formas, start=1):
            g = json.loads((base / f"run-{n}" / "grading.json").read_text())
            resultados[forma] = [(e["text"], e["passed"]) for e in g["expectations"]]
        esperado = resultados.pop("sin reescribir")
        self.assertEqual(sum(p for t, p in esperado if t.startswith("Lo marca como bloqueo")), 6)
        for forma, r in resultados.items():
            self.assertEqual(r, esperado, forma)


def cargar(skill):
    spec = importlib.util.spec_from_file_location(f"grade_{skill.replace('-', '_')}", PRUEBAS / skill / "grade.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


ESTADOS_EN_LINEA = """## Estados por vista

- Listado: normal, vacío (sin facturas), cargando, error, sin permiso (no aplica), muchos datos (pendiente: equipo técnico).

## Reglas
"""
ESTADOS_EN_SUBLISTA = """## Estados por vista

- Listado:
  - normal
  - vacío: sin facturas
  - cargando
  - error
  - sin permiso: no aplica
  - muchos datos: pendiente, equipo técnico

## Reglas
"""


class EstadosBaseDeGrilling(unittest.TestCase):
    def test_estados_en_la_misma_linea_o_en_sublista(self):
        grade = cargar("grilling-es")
        for spec in (ESTADOS_EN_LINEA, ESTADOS_EN_SUBLISTA):
            estados = [r for r in grade.extra_checks(spec) if r["text"].startswith("Cada vista declara")][0]
            self.assertTrue(estados["passed"], estados["evidence"])


NIEGA_LISTA = """No, todavía no está lista para la planning. Falta el ticket.

## Lo que bloquea

1. **No hay ticket.**

## Para dejarla lista

1. Crear el ticket con `specs/proveedores/spec.md`.
"""
SOLO_PENDIENTE = """La vista tiene dos bloqueos.

## Para dejarla lista

1. Crear el ticket.
"""
LISTA_RESUMEN = """## Resultado

1 vista revisada: 1 lista (con avisos), 0 con bloqueos.

## design/vistas/proveedores/proveedores.html · Spec: specs/proveedores/spec.md

Conviene mirar:
- El orden de la lista de proveedores no está en el spec.
"""
LISTA_PROSA = """**Veredicto:** la vista de proveedores está lista para la planning; la crucé con `specs/proveedores/spec.md`.

No encontré nada que bloquee.
"""


class VeredictoLista(unittest.TestCase):
    def dice_lista(self, informe):
        grade = cargar("checklist-diseno")
        out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out)
        (out / "informe.md").write_text(informe)
        res = {}
        for nombre, evaluar in (("eval2", grade.eval2), ("eval3", grade.eval3)):
            res[nombre] = next(r["passed"] for r in evaluar(out) if r["text"] == "Dice que la vista está lista")
        return res

    def test_informe_que_niega_y_tiene_pendientes_no_cuenta_como_lista(self):
        for informe in (NIEGA_LISTA, SOLO_PENDIENTE):
            with self.subTest(informe=informe[:20]):
                self.assertEqual(self.dice_lista(informe), {"eval2": False, "eval3": False})

    def test_informe_afirmativo_en_dos_formatos_cuenta_como_lista(self):
        for informe in (LISTA_RESUMEN, LISTA_PROSA):
            with self.subTest(informe=informe[:20]):
                self.assertEqual(self.dice_lista(informe), {"eval2": True, "eval3": True})


PENDIENTE_FORMAS = {
    "viñeta": "- Pendiente de decisión: #e07a1f, el naranja del estado pendiente; mientras tanto usa --color-warning.\n"
              "- Criterio para el ticket: dado que elijo un estado, cuando filtro, entonces veo solo esas reservas.\n",
    "tabla": "| Valor | Token usado | Estado |\n| :--- | :--- | :--- |\n| #e07a1f | Naranja del estado. Se usó --color-warning | Pendiente de decisión |\n\n"
             "| Lógica | Destino |\n| :--- | :--- |\n| Filtro por estado de la tabla | Criterio para el ticket SEM-11 |\n",
    "encabezado": "## Pendientes de decisión\n\n- #e07a1f (naranja de pendiente): se usó --color-warning.\n\n"
                  "## Criterios para los tickets\n\n- El filtro por estado muestra solo las reservas de ese estado.\n",
    "negrita": "**Pendiente de decisión:**\n- #e07a1f, naranja del estado.\n\n**Criterios para SEM-11:**\n- Filtrar por estado.\n",
}
SIN_MARCA = {
    "resuelto": "## Tokens\n\n- #e07a1f quedó aprobado como --color-pending.\n- La lógica de filtro quedó como comentario en la vista.\n",
    "dentro de otro hallazgo": "- Pendiente de decisión: el radio de 999px. El naranja #e07a1f ya quedó en --color-warning.\n"
                               "- Criterio para el ticket: el total del mes. La vista también filtra por estado.\n",
}
MARCAS = ("El valor fuera de umbral figura como pendiente de decisión", "La lógica JS figura como criterio para el ticket")


class SeveridadHtmlAVista(unittest.TestCase):
    def marcas(self, notas):
        grade = cargar("html-a-vista")
        out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out)
        (out / "notas.md").write_text("Reservas de parcelas convertida, sin render.\n\n" + notas)
        cfg = grade.MOCKUPS["chico"]
        res, low, its = grade.informe(out, cfg, False)
        res += grade.chequeos_fuera(cfg, low, its, out / "repo", True)
        return {r["text"]: r["passed"] for r in res if r["text"] in MARCAS}

    def test_pendiente_y_criterio_en_cuatro_formas(self):
        for forma, notas in PENDIENTE_FORMAS.items():
            with self.subTest(forma=forma):
                self.assertEqual(self.marcas(notas), dict.fromkeys(MARCAS, True))

    def test_el_mockup_grande_busca_su_valor_fuera_de_umbral_como_pendiente(self):
        grade = cargar("html-a-vista")
        out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out)
        cfg = grade.MOCKUPS["grande"]
        for notas, esperado in (("- Pendiente de decisión: #e07a1f, el naranja de las cuotas atrasadas.\n", True),
                                ("- #e07a1f quedó como --color-warning.\n", False)):
            with self.subTest(notas=notas):
                its = grade.hallazgos(notas)
                res = grade.chequeos_fuera(cfg, notas.lower(), its, out / "repo", True)
                self.assertEqual(next(r["passed"] for r in res if r["text"] == MARCAS[0]), esperado)

    def test_resuelto_o_mencionado_dentro_de_otro_hallazgo_no_cuenta(self):
        for caso, notas in SIN_MARCA.items():
            with self.subTest(caso=caso):
                self.assertEqual(self.marcas(notas), dict.fromkeys(MARCAS, False))


PANTALLAS_GRANDE = ("Inventario de semillas, Detalle del lote, Movimientos de semillas, Resumen de compostaje, "
                    "Pilas de compost, Socios del huerto, Cuotas y Ajustes del huerto.")


def uso(nombre, **entrada):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": nombre, "input": entrada}]}}


class ChequeosHtmlAVista(unittest.TestCase):
    def setUp(self):
        self.grade = cargar("html-a-vista")
        self.out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.out)

    def paso(self, res, texto):
        return next(r["passed"] for r in res if r["text"].startswith(texto))

    def informe(self, mockup, notas, navegador=False):
        (self.out / "notas.md").write_text(notas)
        return self.grade.informe(self.out, self.grade.MOCKUPS[mockup], navegador)[0]

    def transcript(self, *usos):
        (self.out / "transcript.jsonl").write_text("".join(json.dumps(u) + "\n" for u in usos))

    def test_el_marco_se_nombra_con_el_titulo_que_muestra_el_mockup(self):
        casos = {"Semilla · Huerto Los Aromos": True, "Semilla · Integrado": True, "Marco (cabecera + menú)": False,
                 "Semilla, el marco común": False}
        for marco, esperado in casos.items():
            with self.subTest(marco=marco):
                res = self.informe("grande", f"Pantallas: {marco}, {PANTALLAS_GRANDE}\n")
                self.assertEqual(self.paso(res, "El informe nombra cada pantalla"), esperado)

    def test_el_informe_nombra_los_tres_data_state_renombrados(self):
        casos = {
            "- El chip del nivel del tanque usaba `full`, `partial` y `off`. Ahora es un modificador del chip.": True,
            "## Escenarios\n\n**`data-state` del mockup renombrados.** Quedaron así:\n\n"
            "- `full` → `badge--lleno`, `partial` → `badge--mitad`, off → `badge--sin-agua`.": True,
            "### Modificadores en vez de data-state\n\n- `full` → `badge--lleno`\n- `partial` → `badge--mitad`\n- `off` → `badge--sin-agua`": True,
            "- `full` → `badge--lleno`, `partial` → `badge--mitad`, off → `badge--sin-agua`.": False,
            "## Tokens\n\n| Valor | Token |\n| :--- | :--- |\n| full | --radius-full |\n| partial, off | --color-muted |\n\n"
            "## Escenarios\n\n- Los data-state del mockup se renombraron.": False,
            "- Renombré el data-state del chip a data-nivel.": False,
            "- El chip usaba `full` y `partial`, renombrados a modificadores del data-state.": False,
            "- El radio --radius-full, el riego partial y el sensor off.": False,
        }
        for notas, esperado in casos.items():
            with self.subTest(notas=notas):
                res = self.informe("demo", "Panel de riego e Historial de riego, sin render.\n" + notas + "\n")
                self.assertEqual(self.paso(res, "El informe nombra cada data-state ajeno"), esperado)

    def test_capturas_con_ruta_del_original_y_de_la_vista(self):
        casos = {
            "Capturas lado a lado: `trabajo/capturas/semana-original.png` y `trabajo/capturas/semana-normal.png`.": True,
            "Original en capturas/original-shell.png; la vista, en capturas/semana-vacio.png.": True,
            "No se capturó nada: faltó el navegador.": False,
            "Capturas en `<vista>-<escenario>.png` y el original en `original-shell.png`.": False,
            "Capturas de la vista: `trabajo/capturas/semana-normal.png`.": False,
        }
        for notas, esperado in casos.items():
            with self.subTest(notas=notas):
                res = self.informe("react", "Cosechas de la semana.\n" + notas + "\n", navegador=True)
                self.assertEqual(self.paso(res, "El informe trae capturas lado a lado"), esperado)

    def test_el_informe_describe_las_tres_olas(self):
        casos = {
            "En la ola 1 fijé los tokens, en la ola 2 armé las vistas y en la ola 3 integré y revisé.": True,
            "Olas:\n\n1. Tokens, componentes y marco.\n2. Un subagente por vista.\n3. Integración y revisión.": True,
            "## Olas\n\n1. Tokens.\n\n2. Vistas.\n\n3. Revisión.": True,
            "La ola de cambios llegó al inventario.": False,
            "Olas:\n\n1. Tokens.\n2. Vistas.\n\n## Tokens\n\n3. Otra cosa.": False,
        }
        for notas, esperado in casos.items():
            with self.subTest(notas=notas):
                (self.out / "notas.md").write_text(notas + "\n")
                res = self.grade.extra_grande(self.out, {}, self.out / "sin-tokens.css")
                self.assertEqual(self.paso(res, "El informe describe las tres olas"), esperado)

    def test_el_valor_fuera_de_umbral_del_grande_va_con_su_uso(self):
        cfg = self.grade.MOCKUPS["grande"]
        casos = {"- Pendiente de decisión: #e07a1f, el naranja de las cuotas atrasadas; se usó --color-warning.\n": True,
                 "- Pendiente de decisión: #e07a1f, el ámbar del aviso de báscula; se usó --color-warning.\n": False}
        for notas, esperado in casos.items():
            with self.subTest(notas=notas):
                res = self.grade.chequeos_fuera(cfg, notas.lower(), self.grade.hallazgos(notas), self.out / "repo", True)
                self.assertEqual(self.paso(res, "El valor fuera de umbral figura como pendiente"), esperado)

    def test_parada_sin_navegador_sin_subagentes_ni_lectura_del_mockup(self):
        base = [uso("Skill", skill="html-a-vista"),
                uso("Bash", command="python3 -B /skills/html-a-vista/scripts/desarmar.py /it/insumos/react.html trabajo"),
                uso("Bash", command="head -60 trabajo/trozos/documento/script.js"), uso("Write", file_path="notas.md", content="react.html")]
        casos = {"base": (base, True, True),
                 "con subagente": (base + [uso("Agent", description="Ola 1: componentes", prompt="...")], False, True),
                 "con Task": (base + [uso("Task", description="algo", prompt="...")], False, True),
                 "lee el mockup": (base + [uso("Read", file_path="/it/insumos/react.html")], True, False),
                 "cat del mockup": (base + [uso("Bash", command="cat /it/insumos/react.html | wc -l")], True, False)}
        for caso, (usos, sin_agentes, sin_lectura) in casos.items():
            with self.subTest(caso=caso):
                self.transcript(*usos)
                res = self.grade.chequeos_parada(self.out, "react", "navegador")
                self.assertEqual(self.paso(res, "No lanza subagentes"), sin_agentes)
                self.assertEqual(self.paso(res, "No lee el mockup entero"), sin_lectura)

    def test_parada_sin_subagentes_no_abre_ni_desarma_el_mockup(self):
        casos = {"solo Skill y Write": ([uso("Skill", skill="html-a-vista"), uso("Write", file_path="notas.md", content="chico.html")], True),
                 "desarma": ([uso("Bash", command="python3 -B desarmar.py /it/insumos/chico.html trabajo")], False),
                 "busca en el mockup": ([uso("Grep", pattern="reservas", path="/it/insumos/chico.html")], False)}
        for caso, (usos, esperado) in casos.items():
            with self.subTest(caso=caso):
                self.transcript(*usos)
                res = self.grade.chequeos_parada(self.out, "chico", "subagentes")
                self.assertEqual(self.paso(res, "No abre ni desarma el mockup"), esperado)

    def test_parada_sin_transcript_no_se_puede_verificar(self):
        res = self.grade.chequeos_parada(self.out, "react", "navegador")
        self.assertEqual([r["passed"] for r in res], [False, False])

    def test_tokens_con_design_system_detecta_un_color_casi_igual(self):
        fixture = PRUEBAS / "html-a-vista" / "fixtures" / "con-ds"
        original = (fixture / "design" / "tokens.css").read_text()
        tok = self.out / "tokens.css"
        casos = {"sin cambios": (original, True),
                 "casi igual": (original.replace("--color-primary: #2f7d4f;", "--color-primary: #2f7d4f;\n  --color-primary-2: #2f7d50;"), False)}
        for caso, (texto, esperado) in casos.items():
            with self.subTest(caso=caso):
                tok.write_text(texto)
                res = self.grade.chequeo_tokens(tok, fixture, True)
                self.assertEqual(self.paso(res, "tokens.css no tiene colores nuevos dentro del umbral"), esperado)

    def test_tokens_sin_design_system_sin_pares_que_se_vean_iguales(self):
        tok = self.out / "tokens.css"
        casos = {"#f0f2f5": False, "#e3e8dd": True}
        for alterno, esperado in casos.items():
            with self.subTest(alterno=alterno):
                tok.write_text(":root { --color-bg: #f6f7f3; --color-surface: #ffffff; --color-primary-contrast: #ffffff; "
                               f"--color-surface-alt: {alterno}; --space-1: 4px; --space-2: 8px; }}\n")
                res = self.grade.chequeo_tokens(tok, None, False)
                self.assertTrue(self.paso(res, "Crea tokens.css con las medidas en escala de 4 px"))
                self.assertEqual(self.paso(res, "tokens.css no tiene dos tokens del mismo tema que se vean iguales"), esperado)

    def test_keyframes_cuenta_reglas_y_no_comentarios(self):
        casos = {
            "comentario CSS": ("/* Sin @keyframes, sin @import, sin fuentes externas. */\n.badge { color: var(--color-text); }\n", []),
            "comentario HTML": ('<!-- el valor "58 °C" late (@keyframes latir, 1.4s, infinito) -->\n<p>58 °C</p>\n', []),
            "regla en CSS": ("@keyframes latir { from { opacity: 1; } to { opacity: .5; } }\n", ["latir"]),
            "regla con prefijo": ("@-webkit-keyframes girar{to{transform:rotate(1turn)}}\n", ["girar"]),
            "regla después de un comentario": ("/* @keyframes en el comentario */\n@keyframes pulso {\n  50% { opacity: .5; }\n}\n", ["pulso"]),
            "regla en <style> de una vista": ("<html><head><!-- sin @keyframes -->\n<style>\n  @keyframes latir { to { opacity: .5; } }\n</style></head>"
                                              "<body><p>58 °C</p></body></html>\n", ["latir"]),
        }
        for caso, (texto, esperado) in casos.items():
            with self.subTest(caso=caso):
                self.assertEqual(self.grade.keyframes(texto), esperado)

    def test_ola_2_con_un_subagente_por_vista_cotejado_por_nombre(self):
        def agentes(*descripciones):
            return [uso("Agent", description=d, prompt="...") for d in descripciones]
        nombres = ["marco", "lista", "detalle-lote", "movimientos", "resumen", "pilas", "socios", "cuotas", "ajustes"]
        ola2 = [f"Ola 2: {n}" for n in nombres]
        casos = {
            "una por vista, el marco incluido": (agentes("Ola 1: componentes base", "Ola 1: escenarios globales", *ola2, "Ola 3: revisor"), True),
            "con el prefijo vista": (agentes(*[f"Ola 2: vista {n}" for n in nombres]), True),
            "vista partida en dos": (agentes(*[d for d in ola2 if d != "Ola 2: detalle-lote"], "Ola 2: detalle-lote (parte 1)",
                                             "Ola 2: detalle-lote (parte 2)"), True),
            "el marco sin subagente de la ola 2": (agentes("Ola 1: marco y escenarios globales", *ola2[1:]), False),
            "reintentos de una sola vista": (agentes(*["Ola 2: lista"] * 9), False),
            "otro nombre para la vista": (agentes(*[d for d in ola2 if d != "Ola 2: detalle-lote"], "Ola 2: detalle"), False),
            "dos vistas en uno": (agentes(*ola2[:4], "Ola 2: resumen y pilas", *ola2[6:]), False),
            "agrupadas": (agentes("Ola 1: componentes", *ola2[:5], "Ola 3: revisor"), False),
            "por módulo": (agentes("Ola 2 vistas inventario", "Ola 2 vistas compostaje", "Ola 2 vistas socios"), False),
        }
        for caso, (usos, esperado) in casos.items():
            with self.subTest(caso=caso):
                self.transcript(*usos)
                res = self.grade.chequeo_ola2(self.out, nombres)
                self.assertEqual(self.paso(res, "La ola 2 tiene un subagente por vista"), esperado)
        (self.out / "transcript.jsonl").unlink()
        self.assertFalse(self.paso(self.grade.chequeo_ola2(self.out, ["semana"]), "La ola 2 tiene un subagente por vista"))

REVISION_SIN_SEGUNDA = """# Revisión ola 3

## Hallazgo transversal (no bloquea por sí solo cada vista)
- El menú lateral del marco no llega al alto de la pantalla.

## marco - no aprobada
- Falta: menú lateral a altura completa.

## lista - aprobada
- Inventario: textos 74/443, faltantes con motivo en el contrato.

## ajustes - no aprobada
- Falta: el contenido queda desplazado frente a cuotas. Sin motivo en el contrato.
"""
REVISION_CON_SEGUNDA_VUELTA = """# Revisión de la ola 3

Resultado: 2 aprobadas (marco, lista) y 1 no aprobadas (detalle-lote).

## marco: Aprobada

## lista: Aprobada
- Los encabezados siguen la tabla de tokens aprobada.

## detalle-lote: No aprobada
- "Dar de baja" no lleva btn--primary.

## Segunda vuelta

- detalle-lote: Aprobada. "Dar de baja" lleva btn--primary.
"""
REVISION_FORMATO_FIJO = """# Revisión · ola 3

## panel: aprobada

## historial: no aprobada
- Falta el escenario vacío.

## historial, segunda revisión: aprobada
"""
REVISION_PRIMERA_DESPUES = """# Revisión

| Vista | Veredicto |
| :--- | :--- |
| panel | aprobada (segunda revisión) |

## Panel, segunda revisión: aprobada

## Panel, primera revisión: no aprobada (lo que sigue es lo que se pidió corregir)
"""
REVISION_UNA_VISTA = """# Revisión · ola 3

## semana (`design/vistas/cosechas/semana.html`)

**Veredicto: no aprobada.** Los encabezados de la tabla. Todo lo demás está aprobado.

## Segunda revisión

**Veredicto: aprobada.**
"""
REVISION_SIN_NOMBRE = """# Revisión · ola 3 · chico.html

Veredicto: **aprobada**
"""


class VeredictoDelRevisor(unittest.TestCase):
    def setUp(self):
        self.grade = cargar("html-a-vista")
        self.out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.out)

    def test_ultimo_veredicto_de_cada_vista(self):
        casos = {
            "sin segunda revisión": (REVISION_SIN_SEGUNDA, ["marco", "lista", "ajustes"],
                                     {"marco": "no aprobada", "lista": "aprobada", "ajustes": "no aprobada"}),
            "con segunda vuelta en viñetas": (REVISION_CON_SEGUNDA_VUELTA, ["marco", "lista", "detalle-lote"],
                                              {"marco": "aprobada", "lista": "aprobada", "detalle-lote": "aprobada"}),
            "formato fijo de la skill": (REVISION_FORMATO_FIJO, ["panel", "historial"], {"panel": "aprobada", "historial": "aprobada"}),
            "primera revisión escrita después": (REVISION_PRIMERA_DESPUES, ["panel"], {"panel": "aprobada"}),
            "una vista, segunda revisión sin nombrarla": (REVISION_UNA_VISTA, ["semana"], {"semana": "aprobada"}),
            "una vista que el archivo no nombra": (REVISION_SIN_NOMBRE, ["reservas"], {"reservas": "aprobada"}),
            "vista que el revisor no nombra": (REVISION_FORMATO_FIJO, ["panel", "historial", "ajustes"],
                                               {"panel": "aprobada", "historial": "aprobada", "ajustes": None}),
            "detalle no es detalle-lote": (REVISION_CON_SEGUNDA_VUELTA, ["detalle"], {"detalle": None}),
        }
        for caso, (revision, nombres, esperado) in casos.items():
            with self.subTest(caso=caso):
                self.assertEqual(self.grade.veredictos(revision, nombres), esperado)

    def test_toda_vista_del_repositorio_tiene_aprobada_como_ultimo_veredicto(self):
        texto = "Toda vista del repositorio tiene \"aprobada\" como último veredicto del revisor"
        revision = self.out / "trabajo" / "ola-3" / "revision.md"
        casos = {"vistas no aprobadas en el repositorio": (REVISION_SIN_SEGUNDA, ["marco", "lista", "ajustes"], False),
                 "solo lo aprobado en el repositorio": (REVISION_SIN_SEGUNDA, ["lista"], True),
                 "aprobada en la segunda revisión": (REVISION_CON_SEGUNDA_VUELTA, ["marco", "lista", "detalle-lote"], True),
                 "vista sin veredicto": (REVISION_FORMATO_FIJO, ["panel", "ajustes"], False)}
        for caso, (texto_revision, nombres, esperado) in casos.items():
            with self.subTest(caso=caso):
                revision.parent.mkdir(parents=True, exist_ok=True)
                revision.write_text(texto_revision)
                res = self.grade.chequeo_revisor(self.out, nombres)
                self.assertEqual(next(r["passed"] for r in res if r["text"] == texto), esperado)
        revision.unlink()
        res = self.grade.chequeo_revisor(self.out, ["lista"])
        self.assertFalse(next(r["passed"] for r in res if r["text"] == texto))

if __name__ == "__main__":
    unittest.main()
