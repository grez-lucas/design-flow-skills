#!/usr/bin/env python3
"""Decide en qué rama guarda una skill del flujo. Solo decide: no cambia de rama, no hace commit ni push.

Uso, desde el repositorio de diseño o con --repo:
  python3 -B rama.py revisar --tipo <spec|tickets|diseno> --epica <épica>
  python3 -B rama.py rechazo --tipo <spec|tickets|diseno> --epica <épica>

revisar  antes de la primera escritura. Corre `git fetch`, mira la rama actual en el servidor y devuelve:
         guardar  la rama actual es la principal del servidor, o una rama del flujo de la épica con upstream vivo:
                  `spec/`, `tickets/` o `diseno/<épica>`, con o sin sufijo (`-2`, `-3`).
         volver   el upstream de la rama actual ya no está en el servidor y todos sus commits están en alguna rama
                  de origin: volver a `principal` con `git switch` y `git pull --ff-only`, y guardar ahí.
         parar    cualquier otro caso, con `motivo` y `detalle`.

rechazo  después de que el servidor rechazó el push por algo que no son credenciales. Devuelve `rama-nueva` con el
         nombre libre.

Escribe en stdout un objeto JSON con `accion` y sale con 0. Con uso incorrecto, o una épica que no sirve como nombre
de rama, sale con 2 sin escribir en stdout.
"""
import argparse
import json
import re
import subprocess
import sys

TIPOS = ("spec", "tickets", "diseno")


class Parada(Exception):
    def __init__(self, motivo, detalle, rama=None):
        super().__init__(motivo)
        self.salida = {"accion": "parar", "motivo": motivo, "detalle": detalle}
        if rama:
            self.salida["rama"] = rama


class Git:
    def __init__(self, repo):
        self.repo = repo

    def correr(self, *args):
        return subprocess.run(["git", "-C", self.repo, *args], capture_output=True, text=True, encoding="utf-8",
                              errors="replace", stdin=subprocess.DEVNULL)

    def salida(self, *args):
        resultado = self.correr(*args)
        return resultado.stdout.strip() if resultado.returncode == 0 else None


def servidor(git):
    """`git fetch` y lo que el servidor dice tener: su rama principal y el conjunto de sus ramas."""
    if git.salida("remote", "get-url", "origin") is None:
        raise Parada("sin-servidor", "El repositorio no tiene un servidor `origin` configurado.")
    for args in (("fetch", "--quiet", "origin"), ("ls-remote", "--symref", "origin", "HEAD", "refs/heads/*")):
        resultado = git.correr(*args)
        if resultado.returncode != 0:
            raise Parada("sin-servidor", "git no pudo hablar con el servidor: " + resultado.stderr.strip())
    principal, ramas = None, set()
    for linea in resultado.stdout.splitlines():
        izquierda, _, ref = linea.partition("\t")
        if izquierda.startswith("ref: refs/heads/") and ref == "HEAD":
            principal = izquierda[len("ref: refs/heads/"):]
        elif ref.startswith("refs/heads/"):
            ramas.add(ref[len("refs/heads/"):])
    if principal not in ramas:
        raise Parada("sin-principal", "El servidor no dice cuál es su rama principal.")
    return principal, ramas


def upstream(git, rama):
    """El nombre de la rama de origin que sigue `rama`, o None si no sigue una de origin."""
    if git.salida("config", "--get", f"branch.{rama}.remote") != "origin":
        return None
    merge = git.salida("config", "--get", f"branch.{rama}.merge") or ""
    return merge[len("refs/heads/"):] if merge.startswith("refs/heads/") else None


SUFIJO = r"(?:-(?:[2-9]|[1-9][0-9]+))?"


def es_del_flujo(rama, nombre, tipos=TIPOS):
    """`rama` es `<tipo>/<nombre>`, con o sin sufijo (`-2`, `-3`), para alguno de `tipos`."""
    return re.fullmatch(rf"(?:{'|'.join(tipos)})/{re.escape(nombre)}{SUFIJO}", rama) is not None


def revisar(git, args):
    principal, ramas = servidor(git)
    actual = git.salida("symbolic-ref", "--quiet", "--short", "HEAD")
    if not actual:
        raise Parada("sin-rama", "La copia no está en ninguna rama.")
    if actual == principal:
        return {"accion": "guardar", "rama": actual}
    sigue = upstream(git, actual)
    if sigue in ramas and es_del_flujo(actual, args.epica):
        return {"accion": "guardar", "rama": actual}
    if sigue is not None and sigue not in ramas:
        pendientes = git.salida("rev-list", "--count", "HEAD", "--not", "--remotes=origin")
        if pendientes == "0":
            return {"accion": "volver", "rama": actual, "principal": principal}
        raise Parada("commits-sin-empujar",
                     f"La rama {actual} ya no está en el servidor y tiene commits que el servidor no tiene.", actual)
    raise Parada("otra-rama", f"La rama {actual} no es la principal ni una rama de esta épica en el servidor.", actual)


def nombre_valido(valor):
    """Letras, con o sin tilde, y números, separados por guiones; y que git lo acepte como rama."""
    if not re.fullmatch(r"[^\W_]+(?:-[^\W_]+)*", valor):
        return False
    return subprocess.run(["git", "check-ref-format", f"refs/heads/spec/{valor}"], capture_output=True).returncode == 0


def argumentos(argv):
    parser = argparse.ArgumentParser(description="Decide en qué rama guarda una skill del flujo.")
    sub = parser.add_subparsers(dest="orden", required=True)
    for orden in ("revisar", "rechazo"):
        p = sub.add_parser(orden)
        p.add_argument("--tipo", required=True, choices=TIPOS)
        p.add_argument("--epica", required=True)
        p.add_argument("--repo", default=".")
    args = parser.parse_args(argv)
    if not nombre_valido(args.epica):
        parser.error(f"la épica {args.epica!r} no sirve como nombre de rama: minúsculas y guiones, sin espacios ni /")
    return args


def main(argv=None):
    args = argumentos(argv)
    git = Git(args.repo)
    try:
        salida = revisar(git, args)
    except Parada as parada:
        salida = parada.salida
    print(json.dumps(salida))
    return 0


if __name__ == "__main__":
    sys.exit(main())
