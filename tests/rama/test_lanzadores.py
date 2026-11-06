"""Q161: los lanzadores de `bin/` eligen el ejecutable de la plataforma y le pasan los argumentos tal cual.

`bin/rama` es un sh POSIX para Linux, macOS y Git Bash, que elige por `uname -s` y `uname -m`; `bin/rama.cmd` es para
PowerShell y CMD, y elige por `%PROCESSOR_ARCHITECTURE%`. Sin ejecutable para la plataforma, salen con 3 y lo dicen
en stderr. Estas pruebas corren los lanzadores de `bin/` con los ejecutables que están ahí, con o sin `RAMA`: en
Windows, `rama` por su nombre desde PowerShell y desde el bash de Git para Windows, como lo llaman las skills, con
`bin/` en el PATH; en Linux y macOS, `bin/rama` como proceso.
Uso: python3 -m unittest discover -s tests/rama -p 'test_lanzadores.py' -v
"""
import base64
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from repos import ENTORNO, RAIZ, Repositorio, git

BIN = RAIZ / "bin"
WINDOWS = os.name == "nt"
SIN_EJECUTABLE = 3

# Lo que rompe un lanzador que reinterpreta la línea de órdenes: comillas, espacios, tildes y lo que CMD y sh tratan
# como operador o variable.
MENSAJES = [
    "espacios y tildes: ñandú, café, acción",
    "a & b, a && b, a | b",
    "a ^ b, a ^^ b",
    "100 % listo, %PATH%, %%, %1, %*",
    "!PATH! y $HOME y `uname` y $(uname)",
    "(paréntesis) <menor> >mayor; punto y coma, coma",
    "comillas \"dobles\" y 'simples'",
    "a&b",
    "a^b",
    "%PATH%",
]
RUTA_RARA = "design/con espacio/señal & 100% ñ.html"


def git_bash():
    """El bash de Git para Windows, al lado del `git.exe` de `cmd\\`; no el de WSL de System32."""
    git_exe = shutil.which("git")
    if not git_exe:
        return None
    bash = Path(git_exe).resolve().parents[1] / "bin" / "bash.exe"
    return str(bash) if bash.is_file() else None


def powershell():
    return shutil.which("powershell") or shutil.which("pwsh")


def con_bin_en_el_path(entorno=None):
    """`bin/` al final del PATH, como lo deja Claude Code al cargar el plugin."""
    base = {**ENTORNO, **(entorno or {})}
    return {**base, "PATH": base.get("PATH", "") + os.pathsep + str(BIN)}


def comillas_de_powershell(texto):
    return "'" + texto.replace("'", "''") + "'"


class Lanzadores(Repositorio):
    """Cada forma de llamar a `rama` que usa una skill en esta plataforma: (nombre, función que corre los argumentos)."""

    def formas(self):
        if not WINDOWS:
            return [("bin/rama", self.por_sh)]
        formas = []
        if powershell():
            formas.append(("PowerShell", self.por_powershell))
        if git_bash():
            formas.append(("Git Bash", self.por_git_bash))
        if not formas:
            self.fail("en Windows hace falta PowerShell o el bash de Git para Windows")
        return formas

    def por_sh(self, *args, entorno=None):
        return subprocess.run([str(BIN / "rama"), *args], cwd=self.copia, env={**ENTORNO, **(entorno or {})},
                              capture_output=True, text=True, encoding="utf-8")

    def por_git_bash(self, *args, entorno=None):
        # `rama` por su nombre: Git Bash toma primero el archivo sin extensión (prueba en Windows del issue 45).
        return subprocess.run([git_bash(), "-c", 'rama "$@"', "rama", *args], cwd=self.copia,
                              env=con_bin_en_el_path(entorno), capture_output=True, text=True, encoding="utf-8")

    def por_powershell(self, *args, entorno=None):
        # `rama` por su nombre: PowerShell resuelve por PATHEXT y llega a `rama.cmd`. Cada argumento va como cadena
        # literal de PowerShell, como la escribiría el agente, y el script entero en -EncodedCommand.
        script = ("[Console]::OutputEncoding = [Text.Encoding]::UTF8; $OutputEncoding = [Text.Encoding]::UTF8; "
                  f"& rama {' '.join(comillas_de_powershell(a) for a in args)}; exit $LASTEXITCODE")
        codificado = base64.b64encode(script.encode("utf-16-le")).decode()
        return subprocess.run([powershell(), "-NoProfile", "-NonInteractive", "-EncodedCommand", codificado],
                              cwd=self.copia, env=con_bin_en_el_path(entorno), capture_output=True, text=True,
                              encoding="utf-8")

    def test_corre_el_ejecutable_de_esta_plataforma(self):
        for nombre, correr in self.formas():
            with self.subTest(forma=nombre):
                r = correr("revisar", "--tipo", "spec", "--epica", "alertas")
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertEqual(r.stdout.strip(), '{"accion": "guardar", "rama": "main", "principal": "main"}')

    def test_pasa_el_codigo_de_salida_y_stderr(self):
        for nombre, correr in self.formas():
            with self.subTest(forma=nombre):
                r = correr("revisar", "--tipo", "spec", "--epica", "fase-2")
                self.assertEqual((r.returncode, r.stdout), (2, ""), r.stderr)
                self.assertIn("guion y número", r.stderr)

    def test_pasa_los_argumentos_tal_cual(self):
        for nombre, correr in self.formas():
            for mensaje in MENSAJES:
                with self.subTest(forma=nombre, mensaje=mensaje):
                    self.escribir(self.copia, RUTA_RARA, mensaje + "\n")
                    git("add", "design/", cwd=self.copia)
                    r = correr("commit", "-m", mensaje, "-m", "segundo párrafo", "--", RUTA_RARA)
                    self.assertEqual(r.returncode, 0, r.stderr)
                    self.assertIn('"accion": "empujar"', r.stdout)
                    self.assertEqual(git("log", "-1", "--format=%B", cwd=self.copia).stdout.strip(),
                                     mensaje + "\n\nsegundo párrafo")
                    self.assertEqual(git("-c", "core.quotePath=false", "show", "--name-only", "--format=", "HEAD",
                                         cwd=self.copia).stdout.strip(),
                                     RUTA_RARA)


class Comprobar:
    def assertSinEjecutable(self, r, *en_el_mensaje):
        self.assertEqual((r.returncode, r.stdout), (SIN_EJECUTABLE, ""), r.stderr)
        self.assertIn("no hay ejecutable", r.stderr)
        for texto in en_el_mensaje:
            self.assertIn(texto, r.stderr)


class SinEjecutable(Comprobar, unittest.TestCase):
    """Una plataforma sin ejecutable en `bin/`: el lanzador sale con 3 y dice cuál falta."""

    def uname_falso(self, carpeta, sistema, maquina):
        uname = Path(carpeta) / "uname"
        uname.write_text(f'#!/bin/sh\ncase "$1" in -s) echo {sistema} ;; -m) echo {maquina} ;; esac\n',
                         encoding="utf-8", newline="\n")
        uname.chmod(0o755)
        return {"PATH": str(carpeta) + os.pathsep + ENTORNO.get("PATH", "")}

    @unittest.skipIf(WINDOWS, "el sh se prueba en Windows desde Git Bash, en SinEjecutableEnWindows")
    def test_sh_con_una_arquitectura_sin_ejecutable(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = subprocess.run([str(BIN / "rama"), "revisar"], capture_output=True, text=True, encoding="utf-8",
                               env={**ENTORNO, **self.uname_falso(tmp, "Linux", "riscv64")})
        self.assertSinEjecutable(r, "riscv64")

    @unittest.skipIf(WINDOWS, "el sh se prueba en Windows desde Git Bash, en SinEjecutableEnWindows")
    def test_sh_con_un_sistema_sin_ejecutable(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = subprocess.run([str(BIN / "rama"), "revisar"], capture_output=True, text=True, encoding="utf-8",
                               env={**ENTORNO, **self.uname_falso(tmp, "FreeBSD", "amd64")})
        self.assertSinEjecutable(r, "FreeBSD")

    def test_sh_en_una_carpeta_sin_ejecutables(self):
        """El lanzador solo, sin los ejecutables al lado, como un `bin/` a medio copiar."""
        sh = git_bash() if WINDOWS else "sh"
        if not sh:
            self.skipTest("sin el bash de Git para Windows")
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(BIN / "rama", tmp)
            r = subprocess.run([sh, str(Path(tmp) / "rama"), "revisar"], env=ENTORNO, capture_output=True,
                               text=True, encoding="utf-8")
        self.assertSinEjecutable(r, "rama-")


@unittest.skipUnless(WINDOWS, "rama.cmd corre solo en Windows")
class SinEjecutableEnWindows(Comprobar, unittest.TestCase):
    """`rama.cmd` sin ejecutable para la arquitectura, y desde un proceso de 32 bits."""

    def cmd(self, carpeta, entorno):
        base = {clave: valor for clave, valor in ENTORNO.items()
                if clave.upper() not in ("PROCESSOR_ARCHITECTURE", "PROCESSOR_ARCHITEW6432")}
        return subprocess.run([os.environ.get("ComSpec", "cmd.exe"), "/d", "/c", str(Path(carpeta) / "rama.cmd"),
                               "revisar"], env={**base, **entorno}, capture_output=True, text=True, encoding="utf-8")

    def test_cmd_con_una_arquitectura_sin_ejecutable(self):
        r = self.cmd(BIN, {"PROCESSOR_ARCHITECTURE": "x86"})
        self.assertSinEjecutable(r, "x86")

    def test_cmd_desde_un_proceso_de_32_bits_usa_la_arquitectura_del_sistema(self):
        """Un proceso de 32 bits ve `x86` en PROCESSOR_ARCHITECTURE y la del sistema en PROCESSOR_ARCHITEW6432."""
        real = os.environ.get("PROCESSOR_ARCHITEW6432") or os.environ["PROCESSOR_ARCHITECTURE"]
        self.assertIn(real.upper(), ("AMD64", "ARM64"))
        r = self.cmd(BIN, {"PROCESSOR_ARCHITECTURE": "x86", "PROCESSOR_ARCHITEW6432": real})
        self.assertEqual(r.returncode, 2, r.stderr)

    def test_cmd_en_una_carpeta_sin_ejecutables(self):
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(BIN / "rama.cmd", tmp)
            r = self.cmd(tmp, {"PROCESSOR_ARCHITECTURE": os.environ["PROCESSOR_ARCHITECTURE"]})
        self.assertSinEjecutable(r, "rama-windows-")


if __name__ == "__main__":
    unittest.main()
