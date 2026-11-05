#!/usr/bin/env python3
"""Decide en qué rama guarda una skill del flujo. Solo decide: no cambia de rama, no hace commit ni push.

Uso, desde el repositorio de diseño o con --repo:
  python3 -B rama.py revisar --tipo <spec|tickets|diseno> --epica <épica>
  python3 -B rama.py revisar --tipo diseno --mockup <mockup> --epicas <épica>,<épica>[,...]
  python3 -B rama.py rechazo --tipo <spec|tickets|diseno> --epica <épica>
  python3 -B rama.py rechazo --tipo diseno --mockup <mockup>

--mockup es de html-a-vista cuando las vistas quedan en más de una épica: el nombre del archivo del mockup sin
extensión, en minúsculas y con guiones, reemplaza a la épica en la rama.

revisar  antes de la primera escritura. Corre `git fetch`, mira la rama actual en el servidor y devuelve:
         guardar  la rama actual es la principal del servidor, o una rama del flujo de la épica con upstream vivo,
                  la rama del mismo nombre en origin: `spec/`, `tickets/` o `diseno/<épica>`, con o sin sufijo
                  (`-2`, `-3`). Con --mockup, la rama del flujo es `diseno/<mockup>`, con o sin sufijo.
         ofrecer  solo con --mockup: la rama actual es una rama del flujo viva de una sola de las épicas, aunque el
                  mockup se llame como ella, y `git status --porcelain --untracked-files=no` no muestra nada. Con
                  el sí de la persona: volver a `principal` con `git switch` y `git pull --ff-only`, y crear
                  `rama_nueva`, `diseno/<mockup>` o su primer sufijo libre. Con cambios, para.
         volver   el upstream de la rama actual ya no está en el servidor y lo suyo entró a la principal: todos sus
                  commits están en alguna rama del servidor, o los archivos que tocan los que no están, desde la
                  base común con la principal, están iguales en ella (squash merge). Volver a `principal` con
                  `git switch` y `git pull --ff-only`, y guardar ahí.
         parar    cualquier otro caso, con `motivo` y `detalle`.

rechazo  después de que el servidor rechazó el push a la rama actual por algo que no son credenciales. Devuelve
         `rama-nueva` con `rama`, la actual, y `rama_nueva`: `<tipo>/<épica>` o, si ya existe en local o en el
         servidor, el primer sufijo libre (`-2`, `-3`). Si la rama actual no está en el servidor, es la rama nueva,
         la de `rama-nueva` o la `rama_nueva` de `ofrecer`, aunque siga a otra rama, y para con
         `rama-nueva-rechazada`, sin otro sufijo.

Escribe en stdout un objeto JSON con `accion` y sale con 0. Con uso incorrecto, o una épica o un mockup que no sirve
como nombre de rama (con mayúsculas, o que termina en guion y número, como `fase-2`), sale con 2 sin escribir en
stdout y dice en stderr por qué.
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
    """`git fetch --prune` y lo que el servidor dice tener: su rama principal y el conjunto de sus ramas."""
    if git.salida("remote", "get-url", "origin") is None:
        raise Parada("sin-servidor", "El repositorio no tiene un servidor `origin` configurado.")
    for args in (("fetch", "--quiet", "--prune", "origin"),
                 ("ls-remote", "--symref", "origin", "HEAD", "refs/heads/*")):
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
    actual = rama_actual(git)
    if actual == principal:
        return {"accion": "guardar", "rama": actual}
    sigue = upstream(git, actual)
    # Viva: sigue a la rama del mismo nombre en el servidor, la que recibe `git push`.
    vivo = sigue == actual and sigue in ramas
    if vivo and args.epicas and any(es_del_flujo(actual, epica) for epica in args.epicas):
        if git.salida("status", "--porcelain", "--untracked-files=no") != "":
            raise Parada("cambios-sin-guardar", f"La rama {actual} es de una sola de las épicas del mockup y la copia "
                                                "tiene cambios sin guardar.", actual)
        return {"accion": "ofrecer", "rama": actual, "principal": principal,
                "rama_nueva": primera_libre(git, ramas, f"diseno/{args.mockup}")}
    propia = es_del_flujo(actual, args.mockup, ("diseno",)) if args.epicas else es_del_flujo(actual, args.epica)
    if vivo and propia:
        return {"accion": "guardar", "rama": actual}
    if sigue is not None and sigue not in ramas:
        if trabajo_en_la_principal(git, principal):
            return {"accion": "volver", "rama": actual, "principal": principal}
        raise Parada("commits-sin-empujar",
                     f"La rama {actual} ya no está en el servidor y tiene commits que el servidor no tiene.", actual)
    raise Parada("otra-rama", f"La rama {actual} no es la principal ni una rama de este trabajo en el servidor.", actual)


def trabajo_en_la_principal(git, principal):
    """Lo que la rama actual tiene y no está en ninguna rama del servidor ya entró a la principal: no hay commits
    así, o los archivos que tocan desde la base común con la principal están iguales en ella (un squash merge)."""
    pendientes = git.salida("rev-list", "--count", "HEAD", "--not", "--remotes=origin")
    if pendientes == "0":
        return True
    remota = f"refs/remotes/origin/{principal}"
    base = git.salida("merge-base", "HEAD", remota)
    if not pendientes or not base:
        return False
    tocados, distintos = archivos(git, base, "HEAD"), archivos(git, "HEAD", remota)
    return bool(tocados) and distintos is not None and not tocados & distintos


def archivos(git, desde, hasta):
    """Las rutas que cambian entre dos commits, o None si git falla."""
    salida = git.salida("diff", "--name-only", "--no-renames", "-z", desde, hasta)
    return None if salida is None else {ruta for ruta in salida.split("\0") if ruta}


def rama_actual(git):
    actual = git.salida("symbolic-ref", "--quiet", "--short", "HEAD")
    if not actual:
        raise Parada("sin-rama", "La copia no está en ninguna rama.")
    return actual


def primera_libre(git, ramas_del_servidor, base):
    """`base`, o `base-2`, `base-3`... la primera que no existe en local ni en el servidor."""
    locales = set((git.salida("for-each-ref", "--format=%(refname:short)", "refs/heads") or "").splitlines())
    ocupadas = locales | ramas_del_servidor
    if base not in ocupadas:
        return base
    n = 2
    while f"{base}-{n}" in ocupadas:
        n += 1
    return f"{base}-{n}"


def rechazo(git, args):
    _, ramas = servidor(git)
    actual = rama_actual(git)
    if actual not in ramas:
        # Las ramas a las que se guarda ya están en el servidor; la que no está es la rama nueva, aunque siga a otra.
        raise Parada("rama-nueva-rechazada", f"El servidor rechazó también la rama nueva {actual}.", actual)
    nombre = args.mockup or args.epica
    return {"accion": "rama-nueva", "rama": actual, "rama_nueva": primera_libre(git, ramas, f"{args.tipo}/{nombre}")}


def problema_del_nombre(valor):
    """Por qué `valor` no sirve como épica o mockup, o None: letras minúsculas, con o sin tilde, y números,
    separados por guiones, sin terminar en guion y número, y que git lo acepte como rama."""
    if not re.fullmatch(r"[^\W_]+(?:-[^\W_]+)*", valor) or valor != valor.lower():
        return "minúsculas y guiones, sin espacios ni /"
    if re.search(r"-[0-9]+$", valor):
        return "termina en guion y número, que se confunde con el sufijo de la rama; usa otro, por ejemplo fase-dos"
    if subprocess.run(["git", "check-ref-format", f"refs/heads/spec/{valor}"], capture_output=True).returncode != 0:
        return "git no lo acepta como nombre de rama"
    return None


def argumentos(argv):
    parser = argparse.ArgumentParser(description="Decide en qué rama guarda una skill del flujo.")
    sub = parser.add_subparsers(dest="orden", required=True)
    for orden in ("revisar", "rechazo"):
        p = sub.add_parser(orden)
        p.add_argument("--tipo", required=True, choices=TIPOS)
        nombre = p.add_mutually_exclusive_group(required=True)
        nombre.add_argument("--epica")
        nombre.add_argument("--mockup", help="solo html-a-vista, cuando el mockup cubre varias épicas")
        if orden == "revisar":
            p.add_argument("--epicas", help="con --mockup: las épicas del mockup, separadas por comas")
        p.add_argument("--repo", default=".")
    args = parser.parse_args(argv)
    args.epicas = args.epicas.split(",") if getattr(args, "epicas", None) is not None else None
    for valor in [args.mockup if args.epica is None else args.epica, *(args.epicas or [])]:
        problema = problema_del_nombre(valor)
        if problema:
            parser.error(f"{valor!r} no sirve como nombre de rama: {problema}")
    if args.mockup and args.tipo != "diseno":
        parser.error("--mockup va solo con --tipo diseno")
    if args.orden == "revisar" and bool(args.mockup) != bool(args.epicas):
        parser.error("--mockup y --epicas van juntos")
    if args.epicas and (len(args.epicas) < 2 or len(set(args.epicas)) != len(args.epicas)):
        parser.error("--epicas lleva dos o más épicas distintas; con una sola, usa --epica")
    return args


def main(argv=None):
    args = argumentos(argv)
    git = Git(args.repo)
    try:
        salida = (revisar if args.orden == "revisar" else rechazo)(git, args)
    except Parada as parada:
        salida = parada.salida
    print(json.dumps(salida))
    return 0


if __name__ == "__main__":
    sys.exit(main())
