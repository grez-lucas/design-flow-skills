"""Pruebas de skills/spec-a-html/scripts/compartidos.py: llevar los assets nuevos a un repositorio de diseño que ya existe.

`fixtures/repo-viejo/` es el design/ que dejaba la primera versión de la skill (sin `[data-frame]`, `.modal`,
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
