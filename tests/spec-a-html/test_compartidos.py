"""Pruebas de skills/spec-a-html/scripts/compartidos.py: llevar los assets nuevos a un repositorio de diseño que ya existe.

`fixtures/repo-viejo/` es el design/ que dejaba la skill antes de 8b269c9 (sin `[data-frame]`, `.modal`,
`.toast-region`, `--color-overlay`, `--size-modal` ni `data-valores` en proto.js); `fixtures/repo-propio/` tiene reglas
y tokens propios que no se tocan. En los dos, proto.js va como `proto-anterior.js` y la prueba lo renombra.
Uso: python3 -m unittest discover -s tests/spec-a-html -v
"""
import difflib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import test_proto

RAIZ = Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "skills" / "spec-a-html" / "scripts" / "compartidos.py"
ASSETS = RAIZ / "skills" / "spec-a-html" / "assets"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
COMPARTIDOS = ("tokens.css", "components.css", "proto.js")


def cargar(nombre, ruta):
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = modulo
    spec.loader.exec_module(modulo)
    return modulo


revisar = cargar("revisar", RAIZ / "skills" / "checklist-diseno" / "scripts" / "revisar.py")
DARK = '[data-theme="dark"]'
NUEVAS_DE_LOS_ASSETS = [":where([data-frame])", ".modal", ".modal__dialog", ".modal__actions", ".toast-region",
                        ".toast-region > *"]


def correr(*args):
    return subprocess.run([sys.executable, "-B", str(SCRIPT), *map(str, args)], capture_output=True, text=True)


def solo_inserta(antes, despues):
    """True si `despues` es `antes` con texto insertado y nada borrado ni cambiado."""
    return all(op in ("equal", "insert") for op, *_ in difflib.SequenceMatcher(None, antes, despues, autojunk=False).get_opcodes())


class Repositorio(unittest.TestCase):
    def repo(self, fixture="repo-viejo"):
        repo = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, repo)
        shutil.copytree(FIXTURES / fixture / "design", repo / "design")
        # Las copias viejas de proto.js se guardan con otro nombre: tests/pruebas exige que todo proto.js sea el de la skill.
        (repo / "design" / "proto-anterior.js").rename(repo / "design" / "proto.js")
        return repo

    def leer(self, repo):
        return {a: (repo / "design" / a).read_bytes() if (repo / "design" / a).exists() else None for a in COMPARTIDOS}

    def json(self, comando, repo):
        r = correr(comando, repo)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def tokens(self, salida, clave="faltan"):
        return [(t["bloque"], t["token"]) for t in salida["tokens"][clave]]


class RepoViejo(Repositorio):
    def test_comparar_lista_lo_que_falta(self):
        salida = self.json("comparar", self.repo())
        self.assertEqual(salida["tokens"]["faltan"], [
            {"bloque": ":root", "token": "--color-overlay", "valor": "rgba(16, 24, 40, 0.45)"},
            {"bloque": ":root", "token": "--size-modal", "valor": "480px"},
            {"bloque": DARK, "token": "--color-overlay", "valor": "rgba(0, 0, 0, 0.6)"}])
        self.assertEqual(salida["tokens"]["omitidos"], [])
        self.assertEqual(salida["components"]["faltan"], NUEVAS_DE_LOS_ASSETS)
        self.assertEqual(salida["components"]["omitidos"], [])
        self.assertEqual(salida["components"]["cambian_lo_propio"], [":where([data-frame])"])
        self.assertEqual(salida["proto"], {"existe": True, "difiere": True})
        self.assertTrue(salida["cambios"])

    def test_comparar_y_mostrar_no_escriben(self):
        repo = self.repo()
        antes = self.leer(repo)
        for comando in ("comparar", "mostrar"):
            with self.subTest(comando=comando):
                self.assertEqual(correr(comando, repo).returncode, 0)
                self.assertEqual(self.leer(repo), antes)

    def test_mostrar_da_el_diff_de_lo_que_aplicar_escribe(self):
        r = correr("mostrar", self.repo())
        self.assertEqual(r.returncode, 0, r.stderr)
        for linea in ("+++ b/design/tokens.css", "+  --size-modal: 480px;", "+  --color-overlay: rgba(0, 0, 0, 0.6);",
                      "+++ b/design/components.css", "+:where([data-frame]) { position: relative; display: flow-root; min-height: 100vh; }",
                      "+.toast-region > * { margin: 0; box-shadow: var(--shadow-2); }", "+++ b/design/proto.js"):
            self.assertIn(linea, r.stdout.splitlines(), linea)

    def test_aplicar_deja_los_compartidos_al_dia_solo_insertando(self):
        repo = self.repo()
        antes = self.leer(repo)
        salida = self.json("aplicar", repo)
        self.assertEqual(salida["components"]["faltan"], NUEVAS_DE_LOS_ASSETS)
        design = repo / "design"
        self.assertEqual((design / "proto.js").read_bytes(), (ASSETS / "proto.js").read_bytes())
        for archivo in ("tokens.css", "components.css"):
            with self.subTest(archivo=archivo):
                self.assertTrue(solo_inserta(antes[archivo].decode(), (design / archivo).read_text()))
        self.assertFalse(self.json("comparar", repo)["cambios"])
        tokens = (design / "tokens.css").read_text()
        self.assertEqual(revisar.declaraciones(revisar.strip_comments(tokens), ":root")["--size-modal"], "480px")
        self.assertEqual(revisar.declaraciones(revisar.strip_comments(tokens), DARK)["--color-overlay"], "rgba(0, 0, 0, 0.6)")
        self.assertEqual(revisar.revisar_compartidos(design, revisar.tokens_definidos(design))[0], [])

    def test_el_comentario_de_una_regla_nueva_va_con_ella(self):
        repo = self.repo()
        correr("aplicar", repo)
        comp = (repo / "design" / "components.css").read_text()
        self.assertIn("Nada de position: fixed. */\n.modal {", comp)

    def test_aplicar_dos_veces_no_cambia_nada(self):
        repo = self.repo()
        correr("aplicar", repo)
        despues = self.leer(repo)
        salida = self.json("aplicar", repo)
        self.assertFalse(salida["cambios"])
        self.assertEqual(self.leer(repo), despues)

    def test_tras_aplicar_una_vista_con_modal_pasa_la_regla_de_clases(self):
        """Q108 y Q107 juntas: la vista nueva con modal y avisos bloquea en el repositorio viejo y pasa tras aplicar."""
        repo = self.repo()
        vista = repo / "design" / "vistas" / "prueba" / "vista.html"
        vista.parent.mkdir(parents=True)
        shutil.copy(FIXTURES / "modal.html", vista)

        def sin_regla():
            _, _, _, bloquea, _ = revisar.revisar_vista(vista, repo, revisar.tokens_definidos(repo / "design"))
            return [b for b in bloquea if "Usa clases que `components.css` no define" in b]
        self.assertEqual(len(sin_regla()), 1)
        correr("aplicar", repo)
        self.assertEqual(sin_regla(), [])

    def test_sin_tema_oscuro_no_agrega_el_bloque_oscuro(self):
        repo = self.repo()
        tokens = repo / "design" / "tokens.css"
        texto = tokens.read_text()
        tokens.write_text(texto[:texto.index(DARK)])
        salida = self.json("comparar", repo)
        self.assertEqual(self.tokens(salida), [(":root", "--color-overlay"), (":root", "--size-modal")])
        self.assertEqual(self.tokens(salida, "omitidos"), [(DARK, "--color-overlay")])
        self.assertIn("tema oscuro", salida["tokens"]["omitidos"][0]["motivo"])
        correr("aplicar", repo)
        self.assertNotIn("data-theme", tokens.read_text())

    def test_sin_root_agrega_un_bloque_root_al_final(self):
        repo = self.repo()
        tokens = repo / "design" / "tokens.css"
        antes = tokens.read_text().replace(":root {", "html {", 1)
        tokens.write_text(antes)
        correr("aplicar", repo)
        despues = tokens.read_text()
        self.assertTrue(solo_inserta(antes, despues))
        nuevo = revisar.declaraciones(revisar.strip_comments(despues), ":root")
        self.assertEqual((nuevo["--color-overlay"], nuevo["--size-modal"]), ("rgba(16, 24, 40, 0.45)", "480px"))

    def test_fin_de_linea_crlf_se_conserva(self):
        repo = self.repo()
        for archivo in ("tokens.css", "components.css"):
            ruta = repo / "design" / archivo
            ruta.write_bytes(ruta.read_bytes().replace(b"\n", b"\r\n"))
        antes = self.leer(repo)
        correr("aplicar", repo)
        for archivo in ("tokens.css", "components.css"):
            with self.subTest(archivo=archivo):
                despues = (repo / "design" / archivo).read_bytes()
                self.assertEqual(despues.count(b"\n"), despues.count(b"\r\n"))
                self.assertTrue(solo_inserta(antes[archivo].decode(), despues.decode()))

    def test_sin_components_o_proto_los_copia_de_los_assets(self):
        repo = self.repo()
        (repo / "design" / "components.css").unlink()
        (repo / "design" / "proto.js").unlink()
        salida = self.json("comparar", repo)
        self.assertEqual(salida["proto"], {"existe": False, "difiere": True})
        self.assertFalse(salida["components"]["existe"])
        correr("aplicar", repo)
        for archivo in ("components.css", "proto.js"):
            self.assertEqual((repo / "design" / archivo).read_bytes(), (ASSETS / archivo).read_bytes(), archivo)

    def test_sale_con_2_sin_escribir_si_no_puede_leer_el_repositorio(self):
        casos = {"sin design/": lambda d: shutil.rmtree(d),
                 "sin tokens.css": lambda d: (d / "tokens.css").unlink(),
                 "llave sin cerrar en components.css": lambda d: (d / "components.css").write_text(".x { color: red;\n"),
                 "llave de más en tokens.css": lambda d: (d / "tokens.css").write_text(":root { --a: 1px; } }\n")}
        for caso, romper in casos.items():
            with self.subTest(caso=caso):
                repo = self.repo()
                romper(repo / "design")
                antes = self.leer(repo)
                for comando in ("comparar", "mostrar", "aplicar"):
                    r = correr(comando, repo)
                    self.assertEqual(r.returncode, 2, (comando, r.stdout))
                    self.assertTrue(r.stderr.strip(), comando)
                self.assertEqual(self.leer(repo), antes)

    def test_uso_incorrecto_sale_con_2(self):
        for args in ((), ("copiar", self.repo())):
            with self.subTest(args=args):
                self.assertEqual(correr(*args).returncode, 2)


class RepoPropio(Repositorio):
    def test_no_agrega_tokens_que_ya_define_ni_reglas_que_cambiarian_lo_propio(self):
        salida = self.json("comparar", self.repo("repo-propio"))
        self.assertEqual(self.tokens(salida), [(":root", "--size-modal")])
        self.assertEqual(self.tokens(salida, "omitidos"), [])
        faltan = salida["components"]["faltan"]
        for selector in ("*::before, *::after", ":where([data-frame])", ".btn--danger", ".modal__dialog", ".modal__actions",
                         ".toast-region", ".toast-region > *", ".field", ".field label", ".table", ".badge"):
            self.assertIn(selector, faltan)
        for selector in ("*", "*, *::before, *::after", "body", "[hidden]", ".btn", ".btn:hover", ".btn[disabled]",
                         ".btn--primary", ".card", ".modal"):
            self.assertNotIn(selector, faltan)
        omitidos = {o["selector"]: o["motivo"] for o in salida["components"]["omitidos"]}
        self.assertEqual(set(omitidos), {".btn:hover", ".btn:focus-visible", ".btn[disabled]"})
        self.assertIn("`.btn`", omitidos[".btn:hover"])
        self.assertEqual(salida["components"]["cambian_lo_propio"], ["*::before", "*::after", ":where([data-frame])"])

    def test_aplicar_solo_inserta_y_deja_igual_cada_regla_propia(self):
        repo = self.repo("repo-propio")
        antes = self.leer(repo)
        correr("aplicar", repo)
        design = repo / "design"
        for archivo in ("tokens.css", "components.css"):
            with self.subTest(archivo=archivo):
                self.assertTrue(solo_inserta(antes[archivo].decode(), (design / archivo).read_text()))
        comp = (design / "components.css").read_text()
        self.assertNotIn("components.css: componentes compartidos", comp)
        propias = revisar.reglas_de_primer_nivel(revisar.strip_comments(antes["components.css"].decode()))
        despues = revisar.reglas_de_primer_nivel(revisar.strip_comments(comp))
        for selector, cuerpo in propias:
            self.assertEqual([c for s, c in despues if s == selector], [cuerpo], selector)
        tokens = (design / "tokens.css").read_text()
        raiz = revisar.declaraciones(revisar.strip_comments(tokens), ":root")
        self.assertEqual((raiz["--size-sidebar"], raiz["--size-modal"], raiz["--color-overlay"]),
                         ("256px", "480px", "rgba(34, 32, 27, 0.5)"))
        self.assertEqual(revisar.revisar_compartidos(design, revisar.tokens_definidos(design))[0], [])


class AtRuleDeLosAssets(Repositorio):
    def test_una_regla_nueva_dentro_de_media_va_con_su_preludio(self):
        compartidos = cargar("compartidos", SCRIPT)
        assets = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, assets)
        for archivo in COMPARTIDOS:
            shutil.copy(ASSETS / archivo, assets / archivo)
        with (assets / "components.css").open("a") as c:
            c.write("@media (min-width: 600px) {\n  .columnas { display: grid; }\n  .card { padding: var(--space-6); }\n}\n")
        repo = self.repo()
        salida = compartidos.comparar(repo / "design", assets)
        self.assertEqual(salida["components"]["faltan"], NUEVAS_DE_LOS_ASSETS + ["@media (min-width: 600px) .columnas"])
        compartidos.aplicar(repo / "design", assets)
        comp = (repo / "design" / "components.css").read_text()
        self.assertIn("@media (min-width: 600px) {\n  .columnas { display: grid; }\n}\n", comp)
        self.assertNotIn("padding: var(--space-6); }\n}", comp)

class Revision(Repositorio):
    """Los casos de la revisión independiente de la rama."""

    def assets_con(self, components="", tokens=None):
        """Una copia de assets/ con `components` al final de components.css y, si se da, otro tokens.css."""
        assets = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, assets)
        for archivo in COMPARTIDOS:
            shutil.copy(ASSETS / archivo, assets / archivo)
        with (assets / "components.css").open("a") as c:
            c.write(components)
        if tokens is not None:
            (assets / "tokens.css").write_text(tokens)
        return assets

    def compartidos(self):
        return cargar("compartidos", SCRIPT)

    def test_skill_md_nombra_las_reglas_que_cambian_lo_propio_y_no_promete_que_nada_cambia(self):
        """Q110: las reglas sin clase cambian cómo se ven las vistas propias, y la skill lo dice antes del sí."""
        skill = (RAIZ / "skills" / "spec-a-html" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("`cambian_lo_propio`", skill)
        self.assertNotIn("lo que el repositorio ya tiene no cambia", skill)
        doc = self.compartidos().__doc__
        self.assertIn("cambian_lo_propio", doc)
        self.assertNotIn("solo pinta elementos que lo propio no pinta", doc)
        self.assertNotIn("Nada de lo que ya está cambia", doc)

    def test_bom_inicial_se_reconoce_y_se_conserva(self):
        sin, con = self.repo(), self.repo()
        for archivo in ("tokens.css", "components.css"):
            ruta = con / "design" / archivo
            ruta.write_bytes(b"\xef\xbb\xbf" + ruta.read_bytes())
        self.assertEqual(self.json("comparar", con), self.json("comparar", sin))
        correr("aplicar", sin)
        correr("aplicar", con)
        for archivo in ("tokens.css", "components.css"):
            with self.subTest(archivo=archivo):
                self.assertEqual((con / "design" / archivo).read_bytes(), b"\xef\xbb\xbf" + (sin / "design" / archivo).read_bytes())

    def test_comentario_o_cadena_sin_cerrar_sale_con_2_sin_escribir(self):
        casos = {"comentario al final de components.css": ("components.css", "\n/* sin cerrar .modal { }\n"),
                 "cadena al final de components.css": ("components.css", '\n.x::after { content: "sin cerrar }\n'),
                 "comentario al final de tokens.css": ("tokens.css", "\n/* sin cerrar\n")}
        for caso, (archivo, extra) in casos.items():
            with self.subTest(caso=caso):
                repo = self.repo()
                ruta = repo / "design" / archivo
                ruta.write_text(ruta.read_text() + extra)
                antes = self.leer(repo)
                for comando in ("comparar", "mostrar", "aplicar"):
                    r = correr(comando, repo)
                    self.assertEqual(r.returncode, 2, (comando, r.stdout))
                self.assertEqual(self.leer(repo), antes)

    def test_aplicar_el_diff_de_mostrar_da_lo_mismo_que_aplicar(self):
        """Con LF, con CRLF y sin salto de línea final, `git apply` sobre la salida de mostrar deja los mismos bytes."""
        for caso in ("lf", "crlf", "sin salto final", "crlf sin salto final", "sin proto.js"):
            with self.subTest(caso=caso):
                por_diff, por_aplicar = self.repo(), self.repo()
                for repo in (por_diff, por_aplicar):
                    for archivo in ("tokens.css", "components.css", "proto.js"):
                        ruta = repo / "design" / archivo
                        datos = ruta.read_bytes()
                        if "crlf" in caso:
                            datos = datos.replace(b"\n", b"\r\n")
                        if "sin salto final" in caso:
                            datos = datos.rstrip(b"\r\n")
                        ruta.write_bytes(datos)
                    if caso == "sin proto.js":
                        (repo / "design" / "proto.js").unlink()
                r = subprocess.run([sys.executable, "-B", str(SCRIPT), "mostrar", str(por_diff)], capture_output=True)
                self.assertEqual(r.returncode, 0, r.stderr)
                parche = por_diff / "cambios.diff"
                parche.write_bytes(r.stdout)
                g = subprocess.run(["git", "apply", "--whitespace=nowarn", "-p1", str(parche)], cwd=por_diff,
                                   capture_output=True, text=True)
                self.assertEqual(g.returncode, 0, g.stderr)
                correr("aplicar", por_aplicar)
                self.assertEqual(self.leer(por_diff), self.leer(por_aplicar))

    def test_tema_oscuro_en_root_con_data_theme_o_con_comillas_simples(self):
        for selector in (':root[data-theme="dark"]', "[data-theme='dark']", "html[data-theme=dark]"):
            with self.subTest(selector=selector):
                repo = self.repo()
                tokens = repo / "design" / "tokens.css"
                tokens.write_text(tokens.read_text().replace(DARK + " {", selector + " {"))
                salida = self.json("comparar", repo)
                self.assertIn((DARK, "--color-overlay"), self.tokens(salida))
                self.assertEqual(salida["tokens"]["omitidos"], [])
                correr("aplicar", repo)
                texto = tokens.read_text()
                bloque = texto[texto.index(selector + " {"):]
                self.assertIn("--color-overlay: rgba(0, 0, 0, 0.6);", bloque[:bloque.index("}")])

    def test_tema_oscuro_en_media_que_no_se_reconoce_da_un_motivo_cierto(self):
        repo = self.repo()
        tokens = repo / "design" / "tokens.css"
        texto = tokens.read_text()
        oscuro = texto[texto.index(DARK):]
        tokens.write_text(texto[:texto.index(DARK)] + "@media (prefers-color-scheme: dark) {\n:root" + oscuro[len(DARK):] + "}\n")
        salida = self.json("comparar", repo)
        motivo = salida["tokens"]["omitidos"][0]["motivo"]
        self.assertIn(DARK, motivo)
        self.assertNotIn("tema que no tiene", motivo)
        correr("aplicar", repo)
        self.assertEqual(tokens.read_text().count("--color-overlay: rgba(0, 0, 0, 0.6)"), 0)

    def test_proto_js_con_crlf_no_difiere(self):
        repo = self.repo()
        (repo / "design" / "proto.js").write_bytes((ASSETS / "proto.js").read_bytes().replace(b"\n", b"\r\n"))
        self.assertEqual(self.json("comparar", repo)["proto"], {"existe": True, "difiere": False})

    def test_con_root_repetido_agrega_en_el_ultimo(self):
        repo = self.repo()
        tokens = repo / "design" / "tokens.css"
        texto = tokens.read_text()
        tokens.write_text(texto + "\n:root {\n  --color-brand-alt: #c9a227;\n}\n")
        correr("aplicar", repo)
        ultimo = tokens.read_text().rsplit(":root {", 1)[1]
        self.assertIn("--size-modal: 480px;", ultimo[:ultimo.index("}")])

    def test_token_en_un_comentario_de_tokens_css_falta(self):
        repo = self.repo()
        tokens = repo / "design" / "tokens.css"
        tokens.write_text("/* --size-modal: 480px; */\n" + tokens.read_text())
        self.assertIn((":root", "--size-modal"), self.tokens(self.json("comparar", repo)))

    def test_clase_nueva_junto_a_una_propia_entra_y_not_no_cuenta_como_exigida(self):
        """`.btn .icono-nuevo` solo pinta elementos con una clase nueva; `.btn:not(.activo)` pinta el `.btn` propio."""
        assets = self.assets_con(".btn .icono-nuevo { margin: 0; }\n.btn:not(.activo) { margin: 0; }\n"
                                 ".btn:has(.icono:not(.lleno)) { margin: 0; }\n")
        salida = self.compartidos().comparar(self.repo("repo-propio") / "design", assets)
        self.assertIn(".btn .icono-nuevo", salida["components"]["faltan"])
        self.assertNotIn(".btn:not(.activo)", salida["components"]["faltan"])
        omitidos = [o["selector"] for o in salida["components"]["omitidos"]]
        self.assertIn(".btn:not(.activo)", omitidos)
        self.assertIn(".btn:has(.icono:not(.lleno))", omitidos)

    def test_sin_salto_final_las_reglas_nuevas_van_tras_una_linea_en_blanco(self):
        repo = self.repo()
        comp = repo / "design" / "components.css"
        comp.write_text(comp.read_text().rstrip("\n"))
        correr("aplicar", repo)
        self.assertIn("}\n\n/* Reglas que agregó spec-a-html", comp.read_text())


@unittest.skipIf(test_proto.CHROME is None, "No hay Chrome: google-chrome, chromium o Playwright en ~/.cache/ms-playwright.")
class ModalEnElRepoViejo(test_proto.EnChrome, Repositorio):
    """De punta a punta: una vista nueva con modal en un repositorio viejo, en Chrome a 390, antes y después de aplicar."""

    def velo_y_frame(self, repo):
        vista = repo / "design" / "vistas" / "prueba" / "vista.html"
        vista.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(FIXTURES / "modal.html", vista)
        dom = self.abrir(vista.as_uri() + "?ancho=390")
        return test_proto.rect(dom.body["data-prueba-velo"]), test_proto.rect(dom.body["data-prueba-frame"])

    def test_el_modal_cubre_el_frame_solo_despues_de_aplicar(self):
        repo = self.repo()
        velo, frame = self.velo_y_frame(repo)
        self.assertNotEqual(velo, frame, "en el repositorio viejo .modal no tiene regla")
        self.assertEqual(correr("aplicar", repo).returncode, 0)
        velo, frame = self.velo_y_frame(repo)
        self.assertEqual(frame[2] - frame[0], 390)
        self.assertEqual(velo, frame)


if __name__ == "__main__":
    unittest.main()
