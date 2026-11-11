"""Q162 y Q163: `flujo` en `bin/` corre en cada plataforma y le llega cada argumento tal cual.

`bin/` lleva `flujo-<os>-<arch>` para Linux y macOS en amd64 y arm64, `flujo.exe` para Windows, y `bin/flujo`, un sh
POSIX que elige por `uname -s` y `uname -m` y en Git Bash (MINGW, MSYS) corre `flujo.exe`. PowerShell resuelve `flujo`
a `flujo.exe` por PATHEXT, sin pasar por `cmd.exe`. Sin ejecutable para la plataforma, el sh sale con 3 y lo dice en
stderr. Estas pruebas corren lo que está en `bin/`, con o sin `RAMA`: en Windows, `flujo` por su nombre desde
PowerShell y desde el bash de Git para Windows, como lo llaman las skills, con `bin/` al final del PATH; en Linux y
macOS, `bin/flujo` como proceso.
Uso: python3 -m unittest discover -s tests/rama -p 'test_lanzadores.py' -v
"""
import base64
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from repos import ENTORNO, RAIZ, SCRIPT, Repositorio, git

BIN = RAIZ / "bin"
WINDOWS = os.name == "nt"
SIN_EJECUTABLE = 3
EJECUTABLES = {"flujo", "flujo.exe", "flujo-linux-amd64", "flujo-linux-arm64", "flujo-darwin-amd64",
               "flujo-darwin-arm64"}

# Lo que rompe una capa que reinterpreta la línea de órdenes: espacios, tildes y lo que CMD y sh tratan como operador
# o variable, con y sin espacios alrededor. Las comillas dobles van por `-F` (Q162): PowerShell 5.1 las pierde en
# cualquier argumento de un ejecutable.
MENSAJES = [
    "espacios y tildes: ñandú, café, acción",
    "a & b, a && b, a | b",
    "a ^ b, a ^^ b",
    "100 % listo, %PATH%, %%, %1, %*",
    "!PATH! y $HOME y `uname` y $(uname)",
    "(paréntesis) <menor> >mayor; punto y coma, coma, 'simples'",
    "a&b",
    "a^b",
    "a|b",
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


class Contenido(unittest.TestCase):
    def test_bin_lleva_el_sh_y_un_ejecutable_por_plataforma(self):
        self.assertEqual({p.name for p in BIN.iterdir()}, EJECUTABLES)


class Lanzadores(Repositorio):
    """Cada forma de llamar a `flujo` que usa una skill en esta plataforma: (nombre, función que corre los argumentos)."""

    def formas(self):
        if not WINDOWS:
            return [("bin/flujo", self.por_sh)]
        formas = []
        if powershell():
            formas.append(("PowerShell", self.por_powershell))
        if git_bash():
            formas.append(("Git Bash", self.por_git_bash))
        if not formas:
            self.fail("en Windows hace falta PowerShell o el bash de Git para Windows")
        return formas

    def por_sh(self, *args, entorno=None):
        return subprocess.run([str(BIN / "flujo"), *args], cwd=self.copia, env={**ENTORNO, **(entorno or {})},
                              capture_output=True, text=True, encoding="utf-8")

    def por_git_bash(self, *args, entorno=None):
        # `flujo` por su nombre: Git Bash toma primero el archivo sin extensión (prueba en Windows del issue 45).
        return subprocess.run([git_bash(), "-c", 'flujo "$@"', "flujo", *args], cwd=self.copia,
                              env=con_bin_en_el_path(entorno), capture_output=True, text=True, encoding="utf-8")

    def por_powershell(self, *args, entorno=None):
        # `flujo` por su nombre: PowerShell resuelve por PATHEXT y llega a `flujo.exe`. Cada argumento va como cadena
        # literal de PowerShell, como la escribiría el agente, y el script entero en -EncodedCommand.
        script = ("[Console]::OutputEncoding = [Text.Encoding]::UTF8; $OutputEncoding = [Text.Encoding]::UTF8; "
                  f"& flujo {' '.join(comillas_de_powershell(a) for a in args)}; exit $LASTEXITCODE")
        codificado = base64.b64encode(script.encode("utf-16-le")).decode()
        return subprocess.run([powershell(), "-NoProfile", "-NonInteractive", "-EncodedCommand", codificado],
                              cwd=self.copia, env=con_bin_en_el_path(entorno), capture_output=True, text=True,
                              encoding="utf-8")

    def test_corre_el_ejecutable_de_esta_plataforma(self):
        for nombre, correr in self.formas():
            with self.subTest(forma=nombre):
                r = correr("rama", "revisar", "--tipo", "spec", "--epica", "alertas")
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertEqual(r.stdout.strip(), '{"accion": "guardar", "rama": "main", "principal": "main"}')

    def test_el_uso_es_el_mismo_que_el_de_rama_py(self):
        """`flujo rama -h` y `rama.py -h` imprimen el mismo contrato, que las pruebas de tests/rama prueban contra los
        dos."""
        python = subprocess.run([sys.executable, "-B", str(SCRIPT), "-h"], cwd=self.copia, env=ENTORNO,
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(python.returncode, 0, python.stderr)
        for nombre, correr in self.formas():
            with self.subTest(forma=nombre):
                r = correr("rama", "-h")
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertEqual(r.stdout.rstrip("\n"), python.stdout.rstrip("\n"))

    def test_pasa_el_codigo_de_salida_y_stderr(self):
        for nombre, correr in self.formas():
            with self.subTest(forma=nombre):
                r = correr("rama", "revisar", "--tipo", "spec", "--epica", "fase-2")
                self.assertEqual((r.returncode, r.stdout), (2, ""), r.stderr)
                self.assertIn("guion y número", r.stderr)

    def assertCommit(self, r, mensaje):
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('"accion": "empujar"', r.stdout)
        self.assertEqual(git("log", "-1", "--format=%B", cwd=self.copia).stdout.strip(), mensaje)
        self.assertEqual(git("-c", "core.quotePath=false", "show", "--name-only", "--format=", "HEAD",
                             cwd=self.copia).stdout.strip(), RUTA_RARA)

    def test_pasa_los_argumentos_tal_cual(self):
        for nombre, correr in self.formas():
            for mensaje in MENSAJES:
                with self.subTest(forma=nombre, mensaje=mensaje):
                    self.escribir(self.copia, RUTA_RARA, mensaje + "\n")
                    git("add", "design/", cwd=self.copia)
                    r = correr("rama", "commit", "-m", mensaje, "-m", "segundo párrafo", "--", RUTA_RARA)
                    self.assertCommit(r, mensaje + "\n\nsegundo párrafo")

    def test_el_mensaje_con_comillas_dobles_va_por_archivo(self):
        mensaje = 'diseno(alertas): "comillas" dobles & %PATH% ^ |'
        for nombre, correr in self.formas():
            with self.subTest(forma=nombre):
                self.escribir(self.copia, RUTA_RARA, nombre + "\n")
                git("add", "design/", cwd=self.copia)
                archivo = self.tmp / f"mensaje con espacio {nombre.replace('/', '-')}.txt"
                archivo.write_text(mensaje + "\n", encoding="utf-8")
                self.assertCommit(correr("rama", "commit", "-F", str(archivo), "--", RUTA_RARA), mensaje)


class SinEjecutable(unittest.TestCase):
    """Una plataforma sin ejecutable en `bin/`: el sh sale con 3 y dice cuál falta."""

    def assertSinEjecutable(self, r, *en_el_mensaje):
        self.assertEqual((r.returncode, r.stdout), (SIN_EJECUTABLE, ""), r.stderr)
        self.assertIn("no hay ejecutable", r.stderr)
        for texto in en_el_mensaje:
            self.assertIn(texto, r.stderr)

    def uname_falso(self, carpeta, sistema, maquina):
        uname = Path(carpeta) / "uname"
        uname.write_text(f'#!/bin/sh\ncase "$1" in -s) echo {sistema} ;; -m) echo {maquina} ;; esac\n',
                         encoding="utf-8", newline="\n")
        uname.chmod(0o755)
        return {"PATH": str(carpeta) + os.pathsep + ENTORNO.get("PATH", "")}

    @unittest.skipIf(WINDOWS, "en Windows el sh no mira la arquitectura: corre flujo.exe")
    def test_una_arquitectura_sin_ejecutable(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = subprocess.run([str(BIN / "flujo"), "rama"], capture_output=True, text=True, encoding="utf-8",
                               env={**ENTORNO, **self.uname_falso(tmp, "Linux", "riscv64")})
        self.assertSinEjecutable(r, "riscv64")

    @unittest.skipIf(WINDOWS, "el uname falso es un sh que Windows no corre por su nombre")
    def test_un_sistema_sin_ejecutable(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = subprocess.run([str(BIN / "flujo"), "rama"], capture_output=True, text=True, encoding="utf-8",
                               env={**ENTORNO, **self.uname_falso(tmp, "FreeBSD", "amd64")})
        self.assertSinEjecutable(r, "FreeBSD")

    def test_en_una_carpeta_sin_ejecutables(self):
        """El sh solo, sin los ejecutables al lado, como un `bin/` a medio copiar: en Windows, desde Git Bash."""
        sh = git_bash() if WINDOWS else "sh"
        if not sh:
            self.skipTest("sin el bash de Git para Windows")
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(BIN / "flujo", tmp)
            r = subprocess.run([sh, str(Path(tmp) / "flujo"), "rama"], env=ENTORNO, capture_output=True,
                               text=True, encoding="utf-8")
        self.assertSinEjecutable(r, "flujo.exe" if WINDOWS else "flujo-")


if __name__ == "__main__":
    unittest.main()
