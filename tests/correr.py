"""Corre todo lo que corre CI: los tests de cada carpeta de tests/, `claude plugin validate . --strict` y `actionlint`.

Uso: python3 tests/correr.py

Descubre las carpetas de tests/, todas salvo las ocultas y `__pycache__`, y corre cada una con
`python -m unittest discover -s tests/<carpeta>`, sin escribir bytecode. Una carpeta sin `test*.py`, como una de
fixtures o la que dejó solo su `__pycache__` al borrarse, se salta y se lista. `claude plugin validate . --strict` corre si `claude` está en el PATH, y
`actionlint` si está en el PATH o en `$(go env GOPATH)/bin`. Al final lista lo que pasó, lo que falló y lo que se saltó,
con cuántos tests se saltaron en cada carpeta, y sale con 1 si algo falló. Una herramienta que no está instalada se
salta sin fallar.

Seguro dentro de `git rebase --exec`: cada carpeta corre con GIT_DIR, GIT_WORK_TREE y GIT_INDEX_FILE apuntando a un
repositorio señuelo, y la carpeta falla si el señuelo cambia, porque un test que hereda el repositorio del entorno
escribiría en él. `claude` y `actionlint` corren sin esas variables.
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
import aislar_git  # después de apagar el bytecode, para no dejar __pycache__ en tests/

TESTS = Path(__file__).resolve().parent
RAIZ = TESTS.parent


def carpetas():
    return sorted(p for p in TESTS.iterdir() if p.is_dir() and not p.name.startswith((".", "__")))


def tiene_tests(carpeta):
    return any(p.is_file() for p in carpeta.glob("test*.py"))


def saltados(salida):
    """Los tests saltados según la última línea de unittest, `OK (skipped=N)` o `FAILED (..., skipped=N)`."""
    finales = [linea for linea in salida.splitlines() if re.match(r"(OK|FAILED)\b", linea)]
    m = re.search(r"skipped=(\d+)", finales[-1]) if finales else None
    return int(m[1]) if m else 0


def huella(directorio):
    h = hashlib.sha256()
    for p in sorted(directorio.rglob("*")):
        h.update(p.relative_to(directorio).as_posix().encode() + b"\0")
        if p.is_file() and not p.is_symlink():
            h.update(p.read_bytes())
    return h.hexdigest()


def senuelo(directorio, entorno):
    subprocess.run(["git", "init", "-q", str(directorio)], check=True, capture_output=True, env=entorno)
    subprocess.run(["git", "-C", str(directorio), "-c", "user.name=senuelo", "-c", "user.email=senuelo@example.com",
                    "-c", "commit.gpgsign=false", "commit", "-q", "--allow-empty", "-m", "senuelo"],
                   check=True, capture_output=True, env=entorno)
    git_dir = directorio / ".git"
    return {"GIT_DIR": str(git_dir), "GIT_WORK_TREE": str(directorio), "GIT_INDEX_FILE": str(git_dir / "index")}


def correr_carpeta(carpeta, entorno):
    nombre = carpeta.relative_to(RAIZ).as_posix()
    if not tiene_tests(carpeta):
        return f"{nombre} (sin test*.py)", "saltado"
    print(f"\n== {nombre}", flush=True)
    with tempfile.TemporaryDirectory() as tmp:
        repositorio = Path(tmp) / "senuelo"
        variables = senuelo(repositorio, entorno)
        antes = huella(repositorio)
        # unittest escribe su informe en stderr: se copia a la consola línea a línea y se guarda para el resumen.
        proceso = subprocess.Popen([sys.executable, "-m", "unittest", "discover", "-s", nombre], cwd=RAIZ,
                                   env={**entorno, **variables, "PYTHONDONTWRITEBYTECODE": "1"},
                                   stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
        lineas = []
        for linea in proceso.stderr:
            sys.stderr.write(linea)
            sys.stderr.flush()
            lineas.append(linea)
        rc = proceso.wait()
        if huella(repositorio) != antes:
            print(f"{nombre}: un test escribió en el repositorio señuelo de GIT_DIR; dentro de `git rebase --exec` "
                  "habría escrito en el repositorio del rebase", flush=True)
            return nombre, "falló"
    if rc != 0:
        return nombre, "falló"
    n = saltados("".join(lineas))
    return nombre, f"ok ({n} saltado{'s' if n != 1 else ''})" if n else "ok"


def buscar_actionlint(entorno):
    ruta = shutil.which("actionlint", path=entorno.get("PATH"))
    if ruta:
        return ruta
    go = shutil.which("go", path=entorno.get("PATH"))
    if not go:
        return None
    gopath = subprocess.run([go, "env", "GOPATH"], capture_output=True, text=True, env=entorno).stdout.strip()
    for directorio in filter(None, gopath.split(os.pathsep)):
        ruta = shutil.which("actionlint", path=str(Path(directorio) / "bin"))
        if ruta:
            return ruta
    return None


def correr_herramienta(paso, orden, entorno):
    if orden[0] is None:
        return f"{paso} (no está instalado)", "saltado"
    print(f"\n== {paso}", flush=True)
    rc = subprocess.run(orden, cwd=RAIZ, env=entorno).returncode
    return paso, "ok" if rc == 0 else "falló"


def main():
    if len(sys.argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    entorno = aislar_git.sin_repositorio(os.environ)
    resultados = [correr_carpeta(carpeta, entorno) for carpeta in carpetas()]
    claude = shutil.which("claude", path=entorno.get("PATH"))
    resultados.append(correr_herramienta("claude plugin validate . --strict",
                                         [claude, "plugin", "validate", ".", "--strict"], entorno))
    resultados.append(correr_herramienta("actionlint", [buscar_actionlint(entorno)], entorno))
    print("\n== Resumen")
    for paso, estado in resultados:
        print(f"{estado}: {paso}")
    return 1 if any(estado == "falló" for _, estado in resultados) else 0


if __name__ == "__main__":
    sys.exit(main())
