"""Lo que comparten las pruebas de `tests/rama`: git sin la configuración del entorno, un servidor bare local con la
copia de quien usa la skill, y la orden que corre `rama.py` como proceso.

`RAMA` en el entorno cambia el ejecutable que se prueba, por ejemplo el de Go (Q151, Q152): las pruebas miran solo
el JSON, el código de salida y el estado de git después, así que corren igual contra cualquier ejecutable con la misma
interfaz. Sin `RAMA`, corren contra `skills/grilling-es/scripts/rama.py`.
"""
import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SKILLS = RAIZ / "skills"
SCRIPT = SKILLS / "grilling-es" / "scripts" / "rama.py"

_spec = importlib.util.spec_from_file_location("aislar_git", Path(__file__).resolve().parents[1] / "aislar_git.py")
aislar_git = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(aislar_git)

# Sin la configuración global ni la del sistema, para que local y CI corran igual, y sin GIT_DIR ni las demás
# variables del repositorio del entorno, como dentro de `git rebase --exec`.
ENTORNO = {**aislar_git.sin_repositorio(os.environ), "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
IDENTIDAD = ["-c", "user.name=prueba", "-c", "user.email=prueba@example.com", "-c", "commit.gpgsign=false"]


def orden_de_rama():
    return shlex.split(os.environ["RAMA"]) if os.environ.get("RAMA") else [sys.executable, "-B", str(SCRIPT)]


def git(*args, cwd, check=True, entorno=None):
    return subprocess.run(["git", *IDENTIDAD, *args], cwd=cwd, env=entorno or ENTORNO, check=check,
                          capture_output=True, text=True, encoding="utf-8")


def escribir(repo, ruta, texto):
    destino = Path(repo) / ruta
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(texto, encoding="utf-8")


def bloques(texto):
    """Las líneas de cada bloque ``` del texto, con o sin sangría."""
    return [[l.strip() for l in b.splitlines() if l.strip()]
            for b in re.findall(r"^[ \t]*```[^\n]*\n(.*?)^[ \t]*```", texto, flags=re.S | re.M)]


def bloque_con(texto, comienzo):
    """El bloque cuya primera línea empieza con `comienzo`."""
    encontrados = [b for b in bloques(texto) if b and b[0].startswith(comienzo)]
    if len(encontrados) != 1:
        raise AssertionError(f"no hay un bloque que empiece con {comienzo!r}: {bloques(texto)}")
    return encontrados[0]


class Repositorio(unittest.TestCase):
    """Un servidor bare con `main`, que tiene `design/vistas/alertas/a.html`, `specs/alertas/spec.md` y `notas.txt`,
    la copia de quien usa la skill, con su identidad de git, y otra copia de alguien más."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.servidor = self.tmp / "servidor.git"
        self.copia = self.tmp / "copia"
        self.otra = self.tmp / "otra"
        git("init", "-q", "--bare", "--initial-branch=main", str(self.servidor), cwd=self.tmp)
        git("clone", "-q", str(self.servidor), str(self.otra), cwd=self.tmp)
        escribir(self.otra, "design/vistas/alertas/a.html", "<p>a</p>\n")
        escribir(self.otra, "specs/alertas/spec.md", "# Spec\n")
        escribir(self.otra, "notas.txt", "notas\n")
        git("add", "-A", cwd=self.otra)
        git("commit", "-q", "-m", "inicio", cwd=self.otra)
        git("push", "-q", "origin", "HEAD:main", cwd=self.otra)
        git("clone", "-q", str(self.servidor), str(self.copia), cwd=self.tmp)
        git("config", "user.name", "producto", cwd=self.copia)
        git("config", "user.email", "producto@example.com", cwd=self.copia)

    escribir = staticmethod(escribir)

    def correr(self, *args, codigo=0):
        """Corre `rama.py` como proceso desde la copia y devuelve su JSON."""
        r = subprocess.run([*orden_de_rama(), *args], cwd=self.copia, env=ENTORNO, capture_output=True, text=True,
                           encoding="utf-8")
        self.assertEqual(r.returncode, codigo, r.stderr)
        if codigo:
            self.assertEqual(r.stdout, "")
            return r.stderr
        return json.loads(r.stdout)

    def en_el_servidor(self, *ramas):
        """Crea las ramas en el servidor desde la otra copia, sin que la copia de quien usa la skill las vea."""
        for rama in ramas:
            git("push", "-q", "origin", f"HEAD:refs/heads/{rama}", cwd=self.otra)

    def trabajar_en(self, rama):
        """La copia de quien usa la skill en `rama`, publicada en el servidor y con upstream."""
        git("switch", "-q", "-c", rama, cwd=self.copia)
        git("push", "-q", "-u", "origin", rama, cwd=self.copia)

    def rama_actual(self):
        return git("branch", "--show-current", cwd=self.copia).stdout.strip()

    def status(self):
        return git("status", "--porcelain", cwd=self.copia).stdout

    def archivos_de(self, ref):
        """Lo que cambia el commit `ref`, como `git show --name-status`: estado y ruta."""
        return set(git("show", "--name-status", "--no-renames", "--format=", ref, cwd=self.copia).stdout.split())

    def contenido(self, ref, ruta):
        return git("show", f"{ref}:{ruta}", cwd=self.copia).stdout

    def ramas_locales(self, patron="*"):
        return git("branch", "--format=%(refname:short)", "--list", patron, cwd=self.copia).stdout.split()
