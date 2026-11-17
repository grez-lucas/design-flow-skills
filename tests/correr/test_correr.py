"""Pruebas de tests/correr.py, el comando que corre todo lo de CI, sobre repositorios armados para cada prueba.

Cada prueba copia correr.py y aislar_git.py a un repositorio temporal con sus propias carpetas de tests/, y lo corre con
un PATH que solo tiene git y los `claude`, `go`, `sh` y `actionlint` falsos o reales que la prueba pone.
Uso: python3 -m unittest discover -s tests/correr -v
"""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
TESTS = RAIZ / "tests"
spec = importlib.util.spec_from_file_location("aislar_git", TESTS / "aislar_git.py")
aislar_git = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aislar_git)
# Sin GIT_DIR ni las demás variables del repositorio del entorno, como dentro de `git rebase --exec`.
setUpModule = aislar_git.aislar_modulo
sys.modules["aislar_git"] = aislar_git
spec = importlib.util.spec_from_file_location("correr", TESTS / "correr.py")
correr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(correr)

PASA = """import unittest


class Pasa(unittest.TestCase):
    def test_pasa(self):
        pass
"""

SALTA = """import unittest


class Salta(unittest.TestCase):
    def test_pasa(self):
        pass

    @unittest.skip("sin la herramienta")
    def test_uno(self):
        pass

    @unittest.skip("sin la herramienta")
    def test_dos(self):
        pass
"""

FALLA = """import unittest


class Falla(unittest.TestCase):
    def test_falla(self):
        self.fail("falla a propósito")
"""

# Arma un repositorio temporal y hace un commit con el entorno heredado: con GIT_DIR definido, escribe en ese repositorio.
COMMIT = """import subprocess
import tempfile
import unittest
{aislar}

class Commit(unittest.TestCase):
    def test_commit(self):
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(["git", "init", "-q", d], check=True)
            subprocess.run(["git", "-C", d, "-c", "user.name=p", "-c", "user.email=p@example.com",
                            "-c", "commit.gpgsign=false", "commit", "-q", "--allow-empty", "-m", "prueba"], check=True)
"""

AISLAR = """import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location("aislar_git", Path(__file__).resolve().parents[1] / "aislar_git.py")
aislar_git = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aislar_git)
setUpModule = aislar_git.aislar_modulo
"""

# Herramienta falsa: anota sus argumentos, su directorio y si heredó GIT_DIR, y sale con el código de SALIDA_<nombre>.
FALSA = """#!{python}
import json, os, sys
from pathlib import Path
nombre = Path(sys.argv[0]).name
with open(os.path.join({registro!r}, nombre + ".json"), "w") as f:
    json.dump({{"args": sys.argv[1:], "cwd": os.getcwd(), "git_dir": "GIT_DIR" in os.environ}}, f)
sys.exit(int(os.environ.get("SALIDA_" + nombre, "0")))
"""

GO = """#!{python}
import sys
if sys.argv[1:] == ["env", "GOPATH"]:
    print({gopath!r})
"""

# `go` falso que anota cada llamada en una línea de go.jsonl y sale con el código de SALIDA_go.
GO_REGISTRA = """#!{python}
import json, os, sys
with open(os.path.join({registro!r}, "go.jsonl"), "a") as f:
    f.write(json.dumps({{"args": sys.argv[1:], "cwd": os.getcwd()}}) + "\\n")
sys.exit(int(os.environ.get("SALIDA_go", "0")))
"""

# `scripts/compilar` falso: anota sus argumentos y sale con el código de SALIDA_compilar.
COMPILAR = """#!/bin/sh
echo "$@" >> "$REGISTRO/compilar"
exit "${{SALIDA_compilar:-0}}"
"""

# Un test de tests/rama que anota el RAMA con que corrió.
VE_RAMA = """import os
import unittest


class VeRama(unittest.TestCase):
    def test_anota(self):
        with open(os.path.join({registro!r}, "rama.jsonl"), "a") as f:
            f.write(repr(os.environ.get("RAMA")) + "\\n")
"""


def git(*args, cwd):
    subprocess.run(["git", "-c", "user.name=p", "-c", "user.email=p@example.com", "-c", "commit.gpgsign=false", *args],
                   cwd=cwd, check=True, capture_output=True)


def huella(directorio):
    return {p.relative_to(directorio).as_posix(): p.read_bytes() if p.is_file() else None
            for p in sorted(directorio.rglob("*"))}


class Base(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        self.tmp = tmp
        self.raiz = tmp / "repo"
        (self.raiz / "tests").mkdir(parents=True)
        for nombre in ("correr.py", "aislar_git.py"):
            shutil.copy(TESTS / nombre, self.raiz / "tests" / nombre)
        self.bin = tmp / "bin"
        self.bin.mkdir()
        os.symlink(shutil.which("git"), self.bin / "git")
        self.registro = tmp / "registro"
        self.registro.mkdir()

    def carpeta(self, nombre, codigo):
        d = self.raiz / "tests" / nombre
        d.mkdir(exist_ok=True)
        (d / "test_algo.py").write_text(codigo)

    def falsa(self, directorio, nombre):
        ruta = directorio / nombre
        ruta.write_text(FALSA.format(python=sys.executable, registro=str(self.registro)))
        ruta.chmod(0o755)

    def llamada(self, nombre):
        archivo = self.registro / f"{nombre}.json"
        return json.loads(archivo.read_text()) if archivo.exists() else None

    def correr(self, cwd=None, args=(), **entorno):
        env = {**os.environ, "PATH": str(self.bin), **entorno}
        r = subprocess.run([sys.executable, str(self.raiz / "tests" / "correr.py"), *args], cwd=cwd or self.raiz, env=env,
                           capture_output=True, text=True, timeout=300)
        return r, r.stdout + r.stderr

    def resumen(self, salida):
        """Las líneas `estado: paso` del resumen final, como diccionario paso -> estado."""
        cola = salida.split("== Resumen", 1)[1]
        return {m[1]: m[0] for m in re.findall(r"^(ok(?: \(\d+ saltados?\))?|falló|saltado): (.+)$", cola, re.M)}


class Descubrimiento(Base):
    def test_corre_cada_carpeta_de_tests_sin_lista(self):
        self.carpeta("uno", PASA)
        r, salida = self.correr()
        self.assertEqual(r.returncode, 0, salida)
        self.assertEqual(self.resumen(salida).get("tests/uno"), "ok", salida)

        self.carpeta("dos", FALLA)
        r, salida = self.correr()
        self.assertEqual(r.returncode, 1, salida)
        resumen = self.resumen(salida)
        self.assertEqual(resumen.get("tests/uno"), "ok", salida)
        self.assertEqual(resumen.get("tests/dos"), "falló", salida)

    def test_no_corre_carpetas_ocultas_ni_pycache(self):
        self.carpeta("uno", PASA)
        self.carpeta("__pycache__", FALLA)
        self.carpeta(".oculta", FALLA)
        r, salida = self.correr()
        self.assertEqual(r.returncode, 0, salida)
        self.assertEqual([p for p in self.resumen(salida) if p.startswith("tests/")], ["tests/uno"], salida)


    def test_salta_y_lista_la_carpeta_sin_test(self):
        self.carpeta("uno", PASA)
        datos = self.raiz / "tests" / "fixtures"
        datos.mkdir()
        (datos / "datos.json").write_text("{}")
        # Lo que queda de una carpeta borrada o renombrada: solo el bytecode de sus tests.
        vieja = self.raiz / "tests" / "vieja" / "__pycache__"
        vieja.mkdir(parents=True)
        (vieja / "test_algo.cpython-312.pyc").write_bytes(b"")
        r, salida = self.correr()
        self.assertEqual(r.returncode, 0, salida)
        resumen = self.resumen(salida)
        self.assertEqual(resumen.get("tests/uno"), "ok", salida)
        self.assertEqual(resumen.get("tests/fixtures (sin test*.py)"), "saltado", salida)
        self.assertEqual(resumen.get("tests/vieja (sin test*.py)"), "saltado", salida)

    def test_no_deja_bytecode_en_tests(self):
        self.carpeta("uno", COMMIT.format(aislar=AISLAR))
        r, salida = self.correr()
        self.assertEqual(r.returncode, 0, salida)
        self.assertEqual(list((self.raiz / "tests").rglob("__pycache__")), [], salida)

    def test_muestra_los_tests_saltados(self):
        self.carpeta("uno", SALTA)
        self.carpeta("dos", PASA)
        r, salida = self.correr()
        self.assertEqual(r.returncode, 0, salida)
        resumen = self.resumen(salida)
        self.assertEqual(resumen.get("tests/uno"), "ok (2 saltados)", salida)
        self.assertEqual(resumen.get("tests/dos"), "ok", salida)

    def test_corre_desde_fuera_de_la_raiz(self):
        self.carpeta("uno", PASA)
        self.falsa(self.bin, "claude")
        r, salida = self.correr(cwd=self.tmp)
        self.assertEqual(r.returncode, 0, salida)
        self.assertEqual(self.resumen(salida).get("tests/uno"), "ok", salida)
        self.assertEqual(Path(self.llamada("claude")["cwd"]).resolve(), self.raiz.resolve())


class RepositorioDelEntorno(Base):
    def setUp(self):
        super().setUp()
        # El repositorio de quien corre el comando, como el de un `git rebase --exec`.
        self.real = self.tmp / "real"
        self.real.mkdir()
        git("init", "-q", cwd=self.real)
        (self.real / "a.txt").write_text("a\n")
        git("add", "a.txt", cwd=self.real)
        git("commit", "-q", "-m", "inicial", cwd=self.real)
        self.entorno = {"GIT_DIR": str(self.real / ".git"), "GIT_WORK_TREE": str(self.real),
                        "GIT_INDEX_FILE": str(self.real / ".git" / "index")}

    def test_falla_la_carpeta_cuyo_test_escribe_en_el_repositorio_del_entorno(self):
        self.carpeta("hereda", COMMIT.format(aislar=""))
        self.carpeta("aislada", COMMIT.format(aislar=AISLAR))
        antes = huella(self.real)
        r, salida = self.correr(**self.entorno)
        self.assertEqual(r.returncode, 1, salida)
        resumen = self.resumen(salida)
        self.assertEqual(resumen.get("tests/hereda"), "falló", salida)
        self.assertEqual(resumen.get("tests/aislada"), "ok", salida)
        self.assertIn("señuelo", salida)
        # Nombra lo que cambió en el señuelo, para buscar al test sin volver a correr: el commit mueve HEAD.
        self.assertRegex(salida, r"cambió: [^\n]*\.git/logs/HEAD")
        self.assertRegex(salida, r"apareció: [^\n]*\.git/objects/")
        self.assertEqual(huella(self.real), antes, "el comando dejó que un test escribiera en el repositorio del entorno")

    def test_claude_y_actionlint_corren_en_la_raiz_sin_el_repositorio_del_entorno(self):
        self.carpeta("uno", PASA)
        self.falsa(self.bin, "claude")
        self.falsa(self.bin, "actionlint")
        r, salida = self.correr(**self.entorno)
        self.assertEqual(r.returncode, 0, salida)
        claude, actionlint = self.llamada("claude"), self.llamada("actionlint")
        self.assertEqual(claude["args"], ["plugin", "validate", ".", "--strict"])
        for llamada in (claude, actionlint):
            self.assertEqual(Path(llamada["cwd"]).resolve(), self.raiz.resolve())
            self.assertFalse(llamada["git_dir"])
        resumen = self.resumen(salida)
        self.assertEqual(resumen.get("claude plugin validate . --strict"), "ok", salida)
        self.assertEqual(resumen.get("actionlint"), "ok", salida)


class Herramientas(Base):
    def test_lista_lo_que_salta_sin_fallar(self):
        self.carpeta("uno", PASA)
        r, salida = self.correr()
        self.assertEqual(r.returncode, 0, salida)
        saltados = {p for p, estado in self.resumen(salida).items() if estado == "saltado"}
        self.assertEqual({p.split(" (")[0] for p in saltados}, {"claude plugin validate . --strict", "actionlint"},
                         salida)
        self.assertTrue(all("no está instalado" in p for p in saltados), salida)

    def test_busca_actionlint_en_el_gopath(self):
        self.carpeta("uno", PASA)
        gopath = self.tmp / "gopath"
        (gopath / "bin").mkdir(parents=True)
        self.falsa(gopath / "bin", "actionlint")
        go = self.bin / "go"
        go.write_text(GO.format(python=sys.executable, gopath=str(gopath)))
        go.chmod(0o755)
        r, salida = self.correr()
        self.assertEqual(r.returncode, 0, salida)
        self.assertIsNotNone(self.llamada("actionlint"), salida)
        self.assertEqual(self.resumen(salida).get("actionlint"), "ok", salida)

    def test_falla_si_falla_una_herramienta(self):
        self.carpeta("uno", PASA)
        self.falsa(self.bin, "claude")
        self.falsa(self.bin, "actionlint")
        for nombre, paso in (("claude", "claude plugin validate . --strict"), ("actionlint", "actionlint")):
            with self.subTest(herramienta=nombre):
                r, salida = self.correr(**{f"SALIDA_{nombre}": "1"})
                self.assertEqual(r.returncode, 1, salida)
                self.assertEqual(self.resumen(salida).get(paso), "falló", salida)


class Go(Base):
    """Con `go.mod` en la raíz: `go vet`, `go test`, la verificación de los ejecutables de bin/ y tests/rama contra el
    lanzador de bin/."""

    def setUp(self):
        super().setUp()
        (self.raiz / "go.mod").write_text("module prueba\n\ngo 1.27.3\n")
        os.symlink(shutil.which("sh"), self.bin / "sh")
        compilar = self.raiz / "scripts" / "compilar"
        compilar.parent.mkdir()
        compilar.write_text(COMPILAR.format())
        compilar.chmod(0o755)
        self.carpeta("uno", PASA)

    def go_falso(self):
        go = self.bin / "go"
        go.write_text(GO_REGISTRA.format(python=sys.executable, registro=str(self.registro)))
        go.chmod(0o755)

    def llamadas_a_go(self):
        archivo = self.registro / "go.jsonl"
        return [json.loads(l) for l in archivo.read_text().splitlines()] if archivo.exists() else []

    def test_corre_vet_test_y_la_verificacion_de_bin_en_la_raiz(self):
        self.go_falso()
        r, salida = self.correr(REGISTRO=str(self.registro))
        self.assertEqual(r.returncode, 0, salida)
        llamadas = [l for l in self.llamadas_a_go() if l["args"] != ["env", "GOPATH"]]
        self.assertEqual([l["args"] for l in llamadas], [["vet", "./..."], ["test", "./..."]], salida)
        self.assertTrue(all(Path(l["cwd"]).resolve() == self.raiz.resolve() for l in llamadas), llamadas)
        self.assertEqual((self.registro / "compilar").read_text(), "--verificar\n")
        resumen = self.resumen(salida)
        for paso in ("go vet ./...", "go test ./...", "scripts/compilar --verificar"):
            self.assertEqual(resumen.get(paso), "ok", salida)

    def test_falla_si_falla_go_o_la_verificacion(self):
        self.go_falso()
        for variable, paso in (("SALIDA_go", "go test ./..."), ("SALIDA_compilar", "scripts/compilar --verificar")):
            with self.subTest(paso=paso):
                r, salida = self.correr(REGISTRO=str(self.registro), **{variable: "1"})
                self.assertEqual(r.returncode, 1, salida)
                self.assertEqual(self.resumen(salida).get(paso), "falló", salida)

    def test_sin_go_salta_lo_de_go(self):
        r, salida = self.correr(REGISTRO=str(self.registro))
        self.assertEqual(r.returncode, 0, salida)
        resumen = self.resumen(salida)
        self.assertEqual(resumen.get("go vet ./... (no está instalado)"), "saltado", salida)
        self.assertEqual(resumen.get("go test ./... (no está instalado)"), "saltado", salida)
        self.assertEqual(resumen.get("scripts/compilar --verificar (go o sh no están instalados)"), "saltado", salida)
        self.assertFalse((self.registro / "compilar").exists())

    def test_corre_tests_rama_tambien_contra_el_lanzador_de_bin(self):
        self.carpeta("rama", VE_RAMA.format(registro=str(self.registro)))
        r, salida = self.correr(REGISTRO=str(self.registro))
        self.assertEqual(r.returncode, 0, salida)
        lanzador = (self.raiz / "bin" / "flujo").as_posix() + " rama"
        self.assertEqual((self.registro / "rama.jsonl").read_text().splitlines(), ["None", repr(lanzador)])
        resumen = self.resumen(salida)
        self.assertEqual(resumen.get("tests/rama"), "ok", salida)
        self.assertEqual(resumen.get(f"tests/rama con RAMA={lanzador}"), "ok", salida)


class SoloRama(Base):
    """`--rama <orden>`: lo que corre el job de CI de cada sistema, solo tests/rama con ese `RAMA`."""

    def test_corre_solo_tests_rama_con_esa_orden(self):
        self.carpeta("rama", VE_RAMA.format(registro=str(self.registro)))
        self.carpeta("otra", FALLA)
        orden = "'/ruta con espacio/bash' /repo/bin/rama"
        r, salida = self.correr(args=("--rama", orden))
        self.assertEqual(r.returncode, 0, salida)
        self.assertEqual((self.registro / "rama.jsonl").read_text().splitlines(), [repr(orden)])
        self.assertEqual(self.resumen(salida), {f"tests/rama con RAMA={orden}": "ok"}, salida)

    def test_falla_si_falla_tests_rama(self):
        self.carpeta("rama", FALLA)
        r, salida = self.correr(args=("--rama", "rama"))
        self.assertEqual(r.returncode, 1, salida)
        self.assertEqual(self.resumen(salida), {"tests/rama con RAMA=rama": "falló"}, salida)


# Una orden de unittest para una carpeta concreta de tests/, como las de la lista que el comando reemplaza.
POR_CARPETA = re.compile(r"unittest discover -s tests/[\w-]+")


class Senuelo(unittest.TestCase):
    """El señuelo queda quieto mientras se toma la huella: su repositorio no corre el mantenimiento automático de git, que
    el commit del armado lanzaba en segundo plano y que en macOS seguía con `.git/objects/maintenance.lock` cuando se
    tomaba la huella de antes (job de macOS del PR 50)."""

    def test_el_senuelo_no_corre_mantenimiento_ni_gc_automaticos(self):
        with tempfile.TemporaryDirectory() as tmp:
            repositorio = Path(tmp) / "senuelo"
            correr.senuelo(repositorio, aislar_git.sin_repositorio(os.environ))
            for clave, valor in (("maintenance.auto", "false"), ("gc.auto", "0")):
                with self.subTest(clave=clave):
                    r = subprocess.run(["git", "config", "--file", str(repositorio / ".git" / "config"), "--get", clave],
                                       capture_output=True, text=True)
                    self.assertEqual(r.stdout.strip(), valor)


class CIYReadme(unittest.TestCase):
    def test_ci_corre_los_tests_con_el_comando(self):
        ci = (RAIZ / ".github" / "workflows" / "ci.yml").read_text()
        self.assertIn("run: python3 tests/correr.py", [l.strip() for l in ci.splitlines()])
        self.assertEqual(POR_CARPETA.findall(ci), [])

    def test_el_readme_da_el_comando_y_no_la_lista_de_carpetas(self):
        readme = (RAIZ / "README.md").read_text()
        self.assertIn("python3 tests/correr.py", [l.strip() for l in readme.splitlines()])
        self.assertEqual(POR_CARPETA.findall(readme), [])


if __name__ == "__main__":
    unittest.main()
