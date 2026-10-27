#!/usr/bin/env python3
"""Prepara una iteración de pruebas de una skill.

Uso: python3 pruebas/preparar.py <skill> <directorio-de-la-iteración>
Por cada prueba de pruebas/<skill>/evals.json y cada configuración (with_skill,
without_skill) copia el repositorio de diseño del fixture en
<iteración>/eval-<id>-<nombre>/<configuración>/run-1/outputs/repo y lo deja como
repositorio git con un commit inicial. Los archivos de entrada (`files` de cada
prueba) van a <iteración>/insumos/; si la skill tiene pruebas/<skill>/generar.py,
corre antes con esa carpeta de salida, para los insumos que se generan. Después,
el agente corre el prompt y las reglas de cada prueba con <outputs> apuntando a
outputs/ e <insumos> a <iteración>/insumos, y grade.py califica.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

CONFIGURACIONES = ("with_skill", "without_skill")


def git(repo, *args):
    env = {"GIT_AUTHOR_NAME": "fixture", "GIT_AUTHOR_EMAIL": "f@example.com",
           "GIT_COMMITTER_NAME": "fixture", "GIT_COMMITTER_EMAIL": "f@example.com", "PATH": "/usr/bin:/bin"}
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=env)


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    base = Path(__file__).resolve().parent / sys.argv[1]
    iteracion = Path(sys.argv[2])
    pruebas = json.loads((base / "evals.json").read_text())["evals"]
    insumos = iteracion / "insumos"
    if (base / "generar.py").exists():
        subprocess.run([sys.executable, str(base / "generar.py"), str(insumos)], check=True)
    for archivo in sorted({f for prueba in pruebas for f in prueba.get("files", [])}):
        origen, destino = base / archivo, insumos / Path(archivo).name
        if origen.is_file():
            insumos.mkdir(parents=True, exist_ok=True)
            shutil.copy(origen, destino)
        elif not destino.is_file():
            print(f"No existe el insumo {archivo} ni lo generó generar.py")
            return 1
    for prueba in pruebas:
        for config in CONFIGURACIONES:
            repo = iteracion / f"eval-{prueba['id']}-{prueba['name']}" / config / "run-1" / "outputs" / "repo"
            if repo.exists():
                print(f"Ya existe, no se toca: {repo}")
                continue
            shutil.copytree(base / prueba["repo"], repo)
            git(repo, "init", "-q", "-b", "main")
            git(repo, "add", "-A")
            git(repo, "commit", "-q", "-m", "estado inicial")
            print(repo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
