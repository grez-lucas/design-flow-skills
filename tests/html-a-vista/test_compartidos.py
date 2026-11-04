"""Pruebas de la puesta al día de los compartidos en html-a-vista: las órdenes que da su SKILL.md llevan los assets de
spec-a-html a un repositorio de diseño creado con una versión anterior, antes de la ola 1.

El repositorio viejo es `tests/spec-a-html/fixtures/repo-viejo/`, el design/ que dejaba spec-a-html antes de 8b269c9
(sin `.modal`, `--color-overlay` ni el proto.js de hoy). `fixtures/puesta-al-dia/` trae la vista que deja la conversión
de un mockup que abre un modal y su spec. Las órdenes se leen de SKILL.md y se corren como las corre la skill, con
`<ruta-de-esta-skill>` y `<intérprete>` en su lugar. La ola 1 se modela con lo que `references/olas.md` le pide sobre
los compartidos: el subagente de componentes base copia de los assets la regla del frame y las del modal y los avisos,
y la tabla de tokens propone `--color-overlay` y `--size-modal`.
Uso: python3 -m unittest discover -s tests/html-a-vista -v
"""
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SKILL = RAIZ / "skills" / "html-a-vista"
ASSETS = RAIZ / "skills" / "spec-a-html" / "assets"
REVISAR = RAIZ / "skills" / "checklist-diseno" / "scripts" / "revisar.py"
APROBADAS = SKILL / "scripts" / "aprobadas.py"
REPO_VIEJO = RAIZ / "tests" / "spec-a-html" / "fixtures" / "repo-viejo"
FIX = Path(__file__).resolve().parent / "fixtures" / "puesta-al-dia"
MOCKUP = RAIZ / "pruebas" / "html-a-vista" / "fixtures" / "mockups" / "chico.html"
VISTA = Path("design") / "vistas" / "pedidos" / "lista.html"
# Las reglas que la ola 1 copia de assets/components.css cuando el mockup tiene modales o avisos (olas.md, "Ola 1").
REGLAS_DE_LA_OLA_1 = (":where([data-frame])", ".modal", ".modal__dialog", ".modal__actions", ".toast-region")
ORDEN_SOLO_USADOS = re.compile(r"^<intérprete> -B <ruta-de-esta-skill>/(\S+/compartidos\.py) (comparar|mostrar|aplicar) "
                               r"<repo-de-diseño> --solo-usados$", re.M)
ORDEN = re.compile(r"^<intérprete> -B <ruta-de-esta-skill>/(\S+/compartidos\.py) (comparar|mostrar|aplicar) <repo-de-diseño>$", re.M)


def ordenes():
    """{comando: argv} de las órdenes de compartidos.py que da SKILL.md, con el intérprete y la ruta de la skill."""
    texto = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    return {comando: [sys.executable, "-B", str(SKILL / script), comando] for script, comando in ORDEN.findall(texto)}


_spec = importlib.util.spec_from_file_location("compartidos", RAIZ / "skills" / "spec-a-html" / "scripts" / "compartidos.py")
compartidos = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(compartidos)


def ordenes_solo_usados():
    """{comando: argv} de las órdenes con `--solo-usados` que da SKILL.md para el design/ a medias (Q137)."""
    texto = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    return {comando: [sys.executable, "-B", str(SKILL / script), comando]
            for script, comando in ORDEN_SOLO_USADOS.findall(texto)}


def usados(css):
    return set(re.findall(r"var\(\s*(--[\w-]+)", css))


def correr(argv, *args):
    return subprocess.run([*map(str, argv), *map(str, args)], capture_output=True, text=True)


def json_cambios(resultado):
    """`cambios` del JSON de `compartidos.py comparar`."""
    if resultado.returncode != 0:
        raise AssertionError(resultado.stderr)
    return json.loads(resultado.stdout)["cambios"]


class PuestaAlDia(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.repo = self.tmp / "repo"
        shutil.copytree(REPO_VIEJO / "design", self.repo / "design")
        # tests/pruebas exige que todo proto.js del repositorio sea el de la skill: el viejo se guarda con otro nombre.
        (self.repo / "design" / "proto-anterior.js").rename(self.repo / "design" / "proto.js")
        (self.repo / "specs" / "pedidos").mkdir(parents=True)
        shutil.copyfile(FIX / "spec.md", self.repo / "specs" / "pedidos" / "spec.md")
        self.trabajo = self.tmp / "trabajo"
        self.copia = self.trabajo / "ola-3" / "repo"

    def orden(self, comando):
        argv = ordenes().get(comando)
        self.assertIsNotNone(argv, f"SKILL.md no da la orden `compartidos.py {comando} <repo-de-diseño>`")
        return argv

    def poner_al_dia(self):
        """Lo que hace la skill antes de la ola 1, con el sí de la persona: comparar, mostrar y aplicar."""
        for comando in ("comparar", "mostrar", "aplicar"):
            r = correr(self.orden(comando), self.repo)
            self.assertEqual(r.returncode, 0, f"{comando}: {r.stderr}")

    def ola_1(self, design):
        """Lo que la ola 1 deja en tokens.css y components.css para un mockup con modal: los tokens del velo y del
        ancho del cuadro, y las reglas de REGLAS_DE_LA_OLA_1 que el repositorio no tiene, copiadas de los assets."""
        _, tokens = compartidos.tokens(design, ASSETS)
        (design / "tokens.css").write_text(tokens, encoding="utf-8")
        asset = (ASSETS / "components.css").read_text(encoding="utf-8")
        actual = (design / "components.css").read_text(encoding="utf-8")
        propios, _ = compartidos.selectores_y_clases(compartidos.arbol(actual, "components.css"))
        reglas = []
        for nodo in compartidos.recorrer(compartidos.arbol(asset, "assets/components.css")):
            selectores = [s for s in compartidos.separar(nodo["preludio"])
                          if s in REGLAS_DE_LA_OLA_1 and compartidos.normal(s) not in propios]
            if selectores:
                reglas.append(", ".join(selectores) + " " + asset[nodo["abre"]:nodo["cierra"] + 1])
        (design / "components.css").write_text(actual + "\n" + "\n".join(reglas) + "\n", encoding="utf-8")

    def integrar(self):
        """Ola 3, paso 1: la copia parte del repositorio de diseño, con los compartidos de la ola 1, y recibe la vista
        convertida."""
        shutil.copytree(self.repo, self.copia)
        self.ola_1(self.copia / "design")
        (self.copia / VISTA).parent.mkdir(parents=True)
        shutil.copyfile(FIX / "lista.html", self.copia / VISTA)

    def revisar(self):
        return correr([sys.executable, "-B", REVISAR], self.copia)

    def huella(self):
        r = correr([sys.executable, "-B", APROBADAS, "huella"], self.copia / VISTA)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def aprobar(self, huella):
        """El veredicto del revisor y lo que leyó: contrato de la ola 2 e inventario de la ola 3."""
        (self.trabajo / "ola-3" / "revision.md").write_text(f"# Revisión\n\n## pedidos/lista: aprobada {huella}\n", encoding="utf-8")
        (self.trabajo / "ola-2" / "pedidos" / "lista").mkdir(parents=True)
        (self.trabajo / "ola-2" / "pedidos" / "lista" / "contrato.md").write_text("# Contrato · lista\n", encoding="utf-8")
        (self.trabajo / "ola-3" / "inventario" / "pedidos").mkdir(parents=True)
        (self.trabajo / "ola-3" / "inventario" / "pedidos" / "lista.json").write_text("{}\n", encoding="utf-8")

    def mover(self):
        return correr([sys.executable, "-B", APROBADAS, "mover"], self.trabajo, self.repo)

    def test_la_skill_llama_al_script_de_spec_a_html_sin_copia_propia(self):
        for comando in ("comparar", "mostrar", "aplicar"):
            with self.subTest(comando=comando):
                self.assertEqual(Path(self.orden(comando)[2]).resolve(), RAIZ / "skills" / "spec-a-html" / "scripts" / "compartidos.py")
        self.assertFalse((SKILL / "scripts" / "compartidos.py").exists())

    def tokens_desde_la_tabla(self, consolidacion):
        """El `tokens.css` que sale de la tabla de consolidación cuando producto acepta cada grupo: un token por grupo
        de color en su tema, uno por medida propuesta y, para cada rol del components.css viejo (Q133), el primer
        candidato del mockup, o el valor por defecto del navegador si el mockup no tiene uno (Q134)."""
        bloques = {}
        for rol in consolidacion["roles"]:
            self.assertTrue(rol["candidatos"], rol["token"])
            bloques.setdefault(":root", []).append(f"{rol['token']}: {rol['candidatos'][0]};")
        for n, grupo in enumerate(consolidacion["colores"], 1):
            bloques.setdefault(grupo["tema"], []).append(f"--color-mockup-{n}: {grupo['representante']};")
        for n, medida in enumerate(consolidacion["medidas"], 1):
            bloques.setdefault(":root", []).append(f"--{medida['categoria']}-mockup-{n}: {medida['propuesta']};")
        return "".join(f"{tema} {{\n" + "".join(f"  {d}\n" for d in decls) + "}\n" for tema, decls in bloques.items())

    def test_design_a_medias_arma_tokens_css_desde_el_mockup_y_sigue_la_puesta_al_dia(self):
        """Q132: con `components.css` y `proto.js` viejos y sin `tokens.css`, `comparar` sale con 2 sin escribir. Con
        `tokens.css` armado desde el mockup por `tokens.py consolidar`, `comparar` sigue, la puesta al día se aplica,
        la ola 1 mapea sobre ese `tokens.css` y `revisar.py` pasa al final."""
        (self.repo / "design" / "tokens.css").unlink()
        antes = {p.name: p.read_bytes() for p in (self.repo / "design").iterdir()}
        r = correr(self.orden("comparar"), self.repo)
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("No existe `design/tokens.css`", r.stderr)
        self.assertEqual({p.name: p.read_bytes() for p in (self.repo / "design").iterdir()}, antes)

        texto = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        orden = re.search(r"^<intérprete> -B <ruta-de-esta-skill>/scripts/tokens\.py consolidar <trabajo>/trozos/\*/estilos\*\.css "
                          r"--roles <repo-de-diseño>/design/components\.css$", texto, re.M)
        self.assertIsNotNone(orden, "SKILL.md no da la orden `tokens.py consolidar` para el design/ a medias")
        r = correr([sys.executable, "-B", SKILL / "scripts" / "desarmar.py"], MOCKUP, self.trabajo)
        self.assertEqual(r.returncode, 0, r.stderr)
        estilos = sorted(self.trabajo.glob("trozos/*/estilos*.css"))
        self.assertTrue(estilos)
        r = correr([sys.executable, "-B", SKILL / "scripts" / "tokens.py", "consolidar"], *estilos,
                   "--roles", self.repo / "design" / "components.css", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        consolidacion = json.loads(r.stdout)
        (self.repo / "design" / "tokens.css").write_text(self.tokens_desde_la_tabla(consolidacion), encoding="utf-8")

        solo = ordenes_solo_usados()
        self.assertEqual(set(solo), {"comparar", "mostrar", "aplicar"}, "SKILL.md no da las órdenes con `--solo-usados`")
        viejo = usados((self.repo / "design" / "components.css").read_text(encoding="utf-8"))
        r = correr(solo["comparar"], self.repo, "--solo-usados")
        self.assertEqual(r.returncode, 0, r.stderr)
        salida = json.loads(r.stdout)
        faltan = {t["token"] for t in salida["tokens"]["faltan"]}
        self.assertEqual(faltan & viejo, set(), "la puesta al día agregaría con valores de la plantilla tokens que usa el components.css viejo")
        # Q137: solo entran los tokens de la plantilla que usa algún compartido, como los del modal.
        self.assertLessEqual({"--color-overlay", "--size-modal"}, faltan)
        for token in ("--color-info", "--font-size-lg", "--space-8", "--size-content-max", "--font-family-mono"):
            self.assertNotIn(token, faltan)
        self.assertTrue(salida["cambios"])
        for comando in ("mostrar", "aplicar"):
            r = correr(solo[comando], self.repo, "--solo-usados")
            self.assertEqual(r.returncode, 0, f"{comando}: {r.stderr}")
        components = (self.repo / "design" / "components.css").read_text(encoding="utf-8")
        tokens_css = (self.repo / "design" / "tokens.css").read_text(encoding="utf-8")
        nuevos = set(re.findall(r"(--[\w-]+)\s*:", tokens_css))
        self.assertLessEqual(faltan, usados(components) | usados(tokens_css), "entró un token de la plantilla que nada usa")
        self.assertLessEqual(usados(components), nuevos, "components.css usa un token que tokens.css no declara")
        self.assertFalse(json.loads(correr(solo["comparar"], self.repo, "--solo-usados").stdout)["cambios"])
        tokens = (self.repo / "design" / "tokens.css").read_text(encoding="utf-8")
        declarados = dict(re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", tokens))
        for rol in consolidacion["roles"]:
            with self.subTest(rol=rol["token"]):
                self.assertEqual(declarados.get(rol["token"]), rol["candidatos"][0], "el rol no quedó con el valor del mockup")
        for n, grupo in enumerate(consolidacion["colores"], 1):
            self.assertEqual(declarados.get(f"--color-mockup-{n}"), grupo["representante"])
        r = correr([sys.executable, "-B", SKILL / "scripts" / "tokens.py", "mapear", self.repo / "design" / "tokens.css"], *estilos, "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        colores = [v for v in json.loads(r.stdout)["valores"] if v["tipo"] == "color"]
        self.assertTrue(colores)
        for v in colores:
            with self.subTest(valor=v["valor"]):
                self.assertTrue(v["dentro"], v)
                self.assertEqual(declarados.get(v["token"]), v["valor_token"])
        mapeados = [v for v in json.loads(r.stdout)["valores"] if v.get("token")]
        self.assertTrue(any(v["tipo"] == "medida" for v in mapeados))
        for v in mapeados:
            with self.subTest(valor=v["valor"], tipo=v["tipo"]):
                self.assertNotIn(v["token"], faltan, "un valor del mockup se mapeó a un token de la plantilla")
        self.integrar()
        r = self.revisar()
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_solo_usados_deja_en_omitidos_los_tokens_de_la_plantilla_que_nada_usa(self):
        """Q137: `--solo-usados` agrega solo los tokens que usa algún compartido; sin el modo, como spec-a-html, todos."""
        tokens = self.repo / "design" / "tokens.css"
        tokens.write_text(":root {\n  --color-primary: #2f7d4f;\n}\n", encoding="utf-8")
        script = RAIZ / "skills" / "spec-a-html" / "scripts" / "compartidos.py"
        todos = json.loads(correr([sys.executable, "-B", script, "comparar"], self.repo).stdout)
        solo = json.loads(correr([sys.executable, "-B", script, "comparar"], self.repo, "--solo-usados").stdout)
        nombres = lambda s, clave: {t["token"] for t in s["tokens"][clave]}
        self.assertIn("--color-info", nombres(todos, "faltan"))
        self.assertNotIn("--color-info", nombres(solo, "faltan"))
        sin_uso = {t["token"]: t["motivo"] for t in solo["tokens"]["omitidos"]}
        self.assertIn("--color-info", sin_uso)
        self.assertIn("ningún compartido lo usa", sin_uso["--color-info"])
        self.assertLessEqual({"--color-overlay", "--size-modal", "--color-surface"}, nombres(solo, "faltan"))
        self.assertEqual(nombres(solo, "faltan") | {t for t in sin_uso}, nombres(todos, "faltan"))
        diff = correr([sys.executable, "-B", script, "mostrar"], self.repo, "--solo-usados").stdout
        self.assertIn("+  --size-modal: 480px;", diff.splitlines())
        self.assertNotIn("--color-info", diff)
        antes = tokens.read_text(encoding="utf-8")
        self.assertEqual(correr([sys.executable, "-B", script, "aplicar"], self.repo, "--solo-usados").returncode, 0)
        despues = tokens.read_text(encoding="utf-8")
        self.assertTrue(despues.startswith(antes.rstrip("}\n")))
        self.assertNotIn("--color-info", despues)
        self.assertFalse(json.loads(correr([sys.executable, "-B", script, "comparar"], self.repo, "--solo-usados").stdout)["cambios"])

    def test_un_css_con_una_llave_sin_cerrar_se_corrige_y_comparar_sigue(self):
        """Q125 con Q131: `comparar` sale con 2 y nombra el archivo; corregido lo que señala, la puesta al día sigue."""
        components = self.repo / "design" / "components.css"
        sano = components.read_text(encoding="utf-8")
        components.write_text(sano.rstrip().rstrip("}") + "\n", encoding="utf-8")
        r = correr(self.orden("comparar"), self.repo)
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("`components.css` deja una llave sin cerrar", r.stderr)
        components.write_text(sano, encoding="utf-8")
        self.assertTrue(json_cambios(correr(self.orden("comparar"), self.repo)))
        self.poner_al_dia()
        self.integrar()
        self.assertEqual(self.revisar().returncode, 0)

    def test_sin_poner_al_dia_la_ola_1_cubre_el_modal_y_queda_el_proto_js_viejo(self):
        """Sin la puesta al día, lo que la ola 1 no trae de los assets queda viejo: proto.js, que revisar.py solo avisa."""
        self.assertTrue(json_cambios(correr(self.orden("comparar"), self.repo)))
        self.integrar()
        r = self.revisar()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("AVISO: `proto.js` no es igual al de la skill `spec-a-html`", r.stdout)
        self.assertNotEqual((self.copia / "design" / "proto.js").read_bytes(), (ASSETS / "proto.js").read_bytes())

    def test_puesta_al_dia_antes_de_la_ola_1_deja_pasar_la_vista_con_modal(self):
        self.poner_al_dia()
        self.assertFalse(json_cambios(correr(self.orden("comparar"), self.repo)))
        self.integrar()
        r = self.revisar()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual((self.copia / "design" / "proto.js").read_bytes(), (ASSETS / "proto.js").read_bytes())

    def solo_proto_js_viejo(self):
        """El repositorio con tokens.css y components.css al día y proto.js viejo: la puesta al día cambia solo proto.js."""
        viejo = (self.repo / "design" / "proto.js").read_bytes()
        self.poner_al_dia()
        (self.repo / "design" / "proto.js").write_bytes(viejo)
        salida = json.loads(correr(self.orden("comparar"), self.repo).stdout)
        self.assertEqual((salida["tokens"]["faltan"], salida["components"]["faltan"], salida["proto"]["difiere"]), ([], [], True))
        self.integrar()

    def aplicar_en_la_copia(self):
        """La puesta al día corrida sobre la copia de la ola 3; tokens.css y components.css quedan igual."""
        antes = {a: (self.copia / "design" / a).read_bytes() for a in ("tokens.css", "components.css")}
        r = correr(self.orden("aplicar"), self.copia)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual({a: (self.copia / "design" / a).read_bytes() for a in antes}, antes)
        self.assertEqual((self.copia / "design" / "proto.js").read_bytes(), (ASSETS / "proto.js").read_bytes())

    def test_la_puesta_al_dia_cambia_proto_js_y_la_huella_del_revisor(self):
        self.solo_proto_js_viejo()
        vieja = self.huella()
        self.aplicar_en_la_copia()
        self.assertNotEqual(self.huella(), vieja)

    def test_una_aprobacion_sobre_el_proto_js_viejo_no_entra_al_repositorio(self):
        """Si proto.js se pone al día después de la revisión, la vista ya no es la que el revisor vio."""
        self.solo_proto_js_viejo()
        self.aprobar(self.huella())
        self.aplicar_en_la_copia()
        r = self.mover()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertFalse((self.repo / VISTA).exists())

    def test_con_el_repositorio_al_dia_la_aprobacion_entra_y_proto_js_queda_el_de_la_skill(self):
        self.poner_al_dia()
        self.integrar()
        self.assertEqual(self.revisar().returncode, 0)
        self.aprobar(self.huella())
        r = self.mover()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((self.repo / VISTA).read_bytes(), (FIX / "lista.html").read_bytes())
        self.assertEqual((self.repo / "design" / "proto.js").read_bytes(), (ASSETS / "proto.js").read_bytes())
        self.assertEqual(correr([sys.executable, "-B", REVISAR], self.repo).returncode, 0)


if __name__ == "__main__":
    unittest.main()
