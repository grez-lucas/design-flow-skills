#!/usr/bin/env python3
"""Decide en qué rama guarda una skill del flujo y protege el trabajo que la persona tenía en la copia.

Uso, desde el repositorio de diseño o con --repo:
  python3 -B rama.py revisar --tipo <spec|tickets|diseno> --epica <épica>
  python3 -B rama.py revisar --tipo diseno --mockup <mockup> --epicas <épica>,<épica>[,...]
  python3 -B rama.py apartar <los mismos --tipo y --epica, o --mockup y --epicas> [--rama <rama>]
  python3 -B rama.py volver <los mismos --tipo y --epica, o --mockup y --epicas> [--rama-nueva <rama>]
  python3 -B rama.py commit -m <mensaje> [-m <párrafo>...] -- <ruta>...
  python3 -B rama.py rechazo --tipo <spec|tickets|diseno> --epica <épica>
  python3 -B rama.py rechazo --tipo diseno --mockup <mockup>

--mockup es de html-a-vista cuando las vistas quedan en más de una épica: el nombre del archivo del mockup sin
extensión, en minúsculas y con guiones, reemplaza a la épica en la rama.

Las rutas de la skill son `design/`, `specs/`, `.gitignore` y `.claude/pm-conventions.md`: lo único que una skill
agrega a su commit. La principal es la que dice el servidor (`git ls-remote --symref`), no `origin/HEAD`.

revisar  antes de la primera escritura. Corre `git fetch`, no cambia nada más y devuelve:
         guardar  la rama actual es la principal del servidor, o una rama del flujo de la épica con upstream vivo,
                  la rama del mismo nombre en origin: `spec/`, `tickets/` o `diseno/<épica>`, con o sin sufijo
                  (`-2`, `-3`). Con --mockup, la rama del flujo es `diseno/<mockup>`, con o sin sufijo.
         ofrecer  solo con --mockup: la rama actual es una rama del flujo viva de una sola de las épicas, aunque el
                  mockup se llame como ella. Lleva `rama_nueva`, `diseno/<mockup>` o su primer sufijo libre.
         volver   el upstream de la rama actual ya no está en el servidor y lo suyo entró a la principal: todos sus
                  commits están en alguna rama del servidor, o los archivos que tocan los que no están, desde la
                  base común con la principal, están iguales en ella (squash merge).
         parar    cualquier otro caso, con `motivo` y `detalle`. En lugar de `guardar`, `ofrecer` o `volver`, para
                  con `cambios-sin-guardar` si hay trabajo sin guardar que entraría en el commit de la skill: en sus
                  rutas, con los archivos nuevos, o preparado en el índice, en cualquier ruta; con `ofrecer`, también
                  cualquier cambio de un archivo con seguimiento. Y para con `principal-adelantada` si se va a
                  guardar desde la principal y la de esta copia tiene commits que el servidor no tiene.
         Todas llevan `principal` cuando el servidor respondió y `rama` cuando la copia está en una. Con trabajo
         sin guardar, `archivos` trae sus líneas de `git status --porcelain`: lo que `apartar` guardaría. Con la
         principal adelantada, `commits` trae esos commits.

apartar  con el sí de la persona, ante `otra-rama`, `sin-rama`, `commits-sin-empujar`, `cambios-sin-guardar` o
         `principal-adelantada`. Guarda en `apartado/<rama>` (cada `/` cambiada por `-`, `sin-rama` con HEAD
         separado, con el primer sufijo libre) lo que había: primero lo que estaba preparado en el índice, tal cual,
         después los cambios de los archivos con seguimiento y los archivos nuevos de las rutas; los demás archivos sin
         seguimiento no se tocan. Con HEAD separado guarda también los commits que no están en ninguna rama. Si se va
         a guardar desde la principal y tiene commits que el servidor no tiene, los guarda en `apartado/<principal>`
         y la iguala al servidor. Vuelve después a la rama del flujo: la actual, si `revisar` daba `guardar`,
         `ofrecer` o `volver`; si no, la rama viva del servidor para este trabajo, `<tipo>/<nombre>` con sufijos
         exactos, o la principal. Devuelve lo que devuelve `revisar` desde ahí, con `apartado` (las ramas que creó)
         y `desde` (la rama donde estaba, o null). Con más de una rama viva para este trabajo devuelve `elegir`, con
         `ramas`, y --rama <una de ellas> vuelve a esa.

volver   con `volver`, o con `ofrecer` y el sí de la persona a `rama_nueva`, que va en --rama-nueva. Corre `revisar`
         otra vez: si devuelve eso, iguala la principal local al servidor, cambia a ella y, con `ofrecer`, crea
         `rama_nueva`. Devuelve `guardar` con la rama donde quedó. Con cualquier otra `accion`, o con `ofrecer` y
         otra `rama_nueva`, no cambia nada y la devuelve. Si el cambio de rama pisaría un cambio sin guardar, no
         cambia nada y para con `cambios-sin-guardar`.

commit   después de `git add` de lo que escribió la skill. Hace el commit solo con las rutas dadas, que tienen que
         estar dentro de las de la skill, con un -m por párrafo. Devuelve `empujar` con `rama` y `archivos` (estado
         y ruta de cada uno, separados por un tab), o `sin-cambios` si esas rutas no cambiaron.

rechazo  después de que el servidor rechazó el push a la rama actual por algo que no son credenciales. Devuelve
         `rama-nueva` con `rama`, la actual, y `rama_nueva`: `<tipo>/<épica>` o, si ya existe en local o en el
         servidor, el primer sufijo libre (`-2`, `-3`). Si la rama actual no está en el servidor, es la rama nueva,
         la de `rama-nueva` o la `rama_nueva` de `ofrecer`, aunque siga a otra rama, y para con
         `rama-nueva-rechazada`, sin otro sufijo.

Si git falla en `apartar`, `volver` o `commit`, para con `error-de-git`, el mensaje de git en `detalle` y, en
`apartar`, `apartado` y `desde` con lo que alcanzó a apartar.

Escribe en stdout un objeto JSON con `accion` y sale con 0. Con uso incorrecto, una épica o un mockup que no sirve
como nombre de rama (con mayúsculas, o que termina en guion y número, como `fase-2`), o una ruta de commit que no es
de la skill, sale con 2 sin escribir en stdout y dice en stderr por qué.
"""
import argparse
import json
import os
import posixpath
import re
import subprocess
import sys

TIPOS = ("spec", "tickets", "diseno")
RUTAS = ("design/", "specs/", ".gitignore", ".claude/pm-conventions.md")
APARTABLES = ("otra-rama", "sin-rama", "commits-sin-empujar", "cambios-sin-guardar", "principal-adelantada")


class Parada(Exception):
    def __init__(self, motivo, detalle, rama=None, **extra):
        super().__init__(motivo)
        self.motivo = motivo
        self.salida = {"accion": "parar", "motivo": motivo, "detalle": detalle}
        if rama:
            self.salida["rama"] = rama
        self.salida.update({clave: valor for clave, valor in extra.items() if valor})


class Git:
    def __init__(self, repo):
        self.repo = repo

    def correr(self, *args):
        return subprocess.run(["git", "-C", self.repo, *args], capture_output=True, text=True, encoding="utf-8",
                              errors="replace", stdin=subprocess.DEVNULL)

    def salida(self, *args):
        resultado = self.correr(*args)
        return resultado.stdout.strip() if resultado.returncode == 0 else None

    def lineas(self, *args):
        """Las líneas de la salida, sin quitar los espacios del comienzo, que en `git status` son datos."""
        resultado = self.correr(*args)
        return [l for l in resultado.stdout.split("\n") if l] if resultado.returncode == 0 else []

    def hacer(self, *args):
        """Una orden que cambia la copia: si git falla, para con su mensaje."""
        resultado = self.correr(*args)
        if resultado.returncode != 0:
            raise Parada("error-de-git", f"`git {' '.join(args)}` falló: " + resultado.stderr.strip(), self.rama())

    def existe(self, ref):
        return self.correr("rev-parse", "--verify", "--quiet", ref).returncode == 0

    def rama(self):
        return self.salida("symbolic-ref", "--quiet", "--short", "HEAD")


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


def nombre(args):
    return args.mockup or args.epica


def rama_del_flujo(git, args, principal, ramas):
    """Lo que dice la rama actual, sin mirar el trabajo sin guardar: `guardar`, `ofrecer` o `volver`, o Parada."""
    actual = git.rama()
    if not actual:
        raise Parada("sin-rama", "La copia no está en ninguna rama.", principal=principal)
    if actual == principal:
        return {"accion": "guardar", "rama": actual, "principal": principal}
    sigue = upstream(git, actual)
    # Viva: sigue a la rama del mismo nombre en el servidor, la que recibe `git push`.
    vivo = sigue == actual and sigue in ramas
    if vivo and args.epicas and any(es_del_flujo(actual, epica) for epica in args.epicas):
        return {"accion": "ofrecer", "rama": actual, "principal": principal,
                "rama_nueva": primera_libre(git, ramas, f"diseno/{args.mockup}")}
    if vivo and es_del_flujo(actual, nombre(args), ("diseno",) if args.epicas else TIPOS):
        return {"accion": "guardar", "rama": actual, "principal": principal}
    if sigue is not None and sigue not in ramas:
        if trabajo_en_la_principal(git, principal):
            return {"accion": "volver", "rama": actual, "principal": principal}
        raise Parada("commits-sin-empujar",
                     f"La rama {actual} ya no está en el servidor y tiene commits que el servidor no tiene.", actual,
                     principal=principal)
    raise Parada("otra-rama", f"La rama {actual} no es la principal ni una rama de este trabajo en el servidor.", actual,
                 principal=principal)


def llega_a_la_principal(decision):
    """La skill va a guardar desde la principal: ahí, en la rama nueva que sale de ella, o al volver."""
    return decision["accion"] in ("ofrecer", "volver") or decision["rama"] == decision["principal"]


def revisar(git, args, del_servidor=None):
    principal, ramas = del_servidor or servidor(git)
    estrecho, amplio = sin_guardar(git)
    try:
        decision = rama_del_flujo(git, args, principal, ramas)
    except Parada as parada:
        if parada.motivo in APARTABLES and amplio:
            parada.salida["archivos"] = amplio
        raise
    # `ofrecer` cambia de rama con lo que haya: cuenta cualquier cambio de un archivo con seguimiento.
    if estrecho or (decision["accion"] == "ofrecer" and amplio):
        raise Parada("cambios-sin-guardar", f"La copia tiene trabajo sin guardar en la rama {decision['rama']} que "
                     "entraría en el commit de la skill o en el cambio de rama.", decision["rama"],
                     principal=principal, archivos=amplio)
    commits = adelantada(git, principal) if llega_a_la_principal(decision) else []
    if commits:
        raise Parada("principal-adelantada", f"La rama principal {principal} de esta copia tiene commits que el "
                     "servidor no tiene, y el push los subiría.", decision["rama"], principal=principal,
                     commits=commits)
    return decision


def sin_guardar(git):
    """El trabajo sin guardar, en líneas de `git status --porcelain`: (lo que entraría en el commit de la skill, lo
    que se aparta). Lo primero son las rutas de la skill, con sus archivos nuevos, y lo preparado en el índice, en
    cualquier ruta; lo segundo suma los cambios de cualquier archivo con seguimiento. Un submódulo con cambios adentro
    no cuenta, porque la skill no lo agrega; uno que apunta a otro commit, sí."""
    en_rutas = git.lineas("status", "--porcelain", "--ignore-submodules=dirty", "--untracked-files=all", "--", *RUTAS)
    seguidos = git.lineas("status", "--porcelain", "--ignore-submodules=dirty", "--untracked-files=no")
    preparados = [l for l in seguidos if l[0] not in " ?"]
    return unicas(en_rutas + preparados), unicas(en_rutas + seguidos)


def unicas(lineas):
    return list(dict.fromkeys(lineas))


def adelantada(git, principal):
    """Los commits de la principal local que no están en la del servidor, como `<hash> <asunto>`."""
    if not git.existe(f"refs/heads/{principal}"):
        return []
    return git.lineas("log", "--format=%h %s", f"refs/remotes/origin/{principal}..refs/heads/{principal}")


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


def apartar(git, args):
    principal, ramas = servidor(git)
    desde = git.rama()
    creadas = []
    try:
        return apartar_y_volver(git, args, principal, ramas, desde, creadas)
    except Parada as parada:
        if parada.motivo == "error-de-git":
            parada.salida.update({"apartado": creadas, "desde": desde})
        raise


def apartar_y_volver(git, args, principal, ramas, desde, creadas):
    try:
        decision = rama_del_flujo(git, args, principal, ramas)
        destino, candidatas = desde, []
    except Parada as parada:
        if parada.motivo not in APARTABLES:
            raise
        decision = None
        candidatas = sorted(r for r in ramas if es_del_flujo(r, nombre(args), (args.tipo,)))
        if len(candidatas) == 1:
            destino = candidatas[0]
        elif candidatas:
            destino = args.rama if args.rama in candidatas else None
        else:
            destino = principal

    sueltos = desde is None and git.salida("rev-list", "--count", "HEAD", "--not", "--branches", "--remotes") != "0"
    if sin_guardar(git)[1] or sueltos:
        donde = desde or "sin-rama"
        apartado = primera_libre(git, ramas, "apartado/" + donde.replace("/", "-"))
        git.hacer("switch", "--quiet", "-c", apartado)
        creadas.append(apartado)
        # Primero lo preparado, tal cual: `git add -u` pisaría lo que está solo en el índice (H3).
        if git.correr("diff", "--cached", "--quiet").returncode == 1:
            git.hacer("commit", "--quiet", "-m", f"Apartado: lo que estaba preparado en {donde}")
        git.hacer("add", "-u")
        nuevos = [r for r in RUTAS if os.path.exists(os.path.join(git.repo, r))]
        if nuevos:
            git.hacer("add", "-A", "--", *nuevos)
        if git.correr("diff", "--cached", "--quiet").returncode == 1:
            git.hacer("commit", "--quiet", "-m", f"Apartado: lo que había en {donde} antes de guardar")

    if (destino == principal or (decision and llega_a_la_principal(decision))) and adelantada(git, principal):
        local = f"refs/heads/{principal}"
        if not (creadas and git.correr("merge-base", "--is-ancestor", local, creadas[-1]).returncode == 0):
            apartado = primera_libre(git, ramas, "apartado/" + principal.replace("/", "-"))
            git.hacer("branch", apartado, local)
            creadas.append(apartado)
        if git.rama() == principal:
            git.hacer("reset", "--quiet", "--keep", f"refs/remotes/origin/{principal}")
        else:
            git.hacer("branch", "--quiet", "-f", principal, f"refs/remotes/origin/{principal}")

    if destino is None:
        return {"accion": "elegir", "ramas": candidatas, "principal": principal, "apartado": creadas, "desde": desde}
    if git.rama() != destino:
        if destino != desde:
            al_dia(git, destino)
        # Con un submódulo apartado, la copia vuelve también al commit del submódulo que tiene la rama del flujo.
        git.hacer("switch", "--quiet", *(("--recurse-submodules",) if creadas else ()), destino)
    try:
        salida = revisar(git, args, (principal, ramas))
    except Parada as parada:
        salida = parada.salida
    return {**salida, "apartado": creadas, "desde": desde}


def al_dia(git, rama):
    """La rama local `rama` igual a la del servidor, sin cambiar de rama: se crea siguiéndola, o avanza si está
    atrás. Una que tiene commits propios queda como está, y `revisar` dice qué pasa con ella."""
    remota = f"refs/remotes/origin/{rama}"
    if not git.existe(f"refs/heads/{rama}"):
        git.hacer("branch", "--quiet", "--track", rama, remota)
    elif git.correr("merge-base", "--is-ancestor", f"refs/heads/{rama}", remota).returncode == 0:
        git.hacer("branch", "--quiet", "-f", rama, remota)


def volver(git, args):
    principal, ramas = servidor(git)
    decision = revisar(git, args, (principal, ramas))
    if not (decision["accion"] == "volver"
            or (decision["accion"] == "ofrecer" and args.rama_nueva == decision["rama_nueva"])):
        return decision
    al_dia(git, principal)
    # Un solo `git switch`: si pisaría un cambio sin guardar, git no cambia nada.
    resultado = git.correr("switch", "--quiet", principal)
    if resultado.returncode != 0:
        raise Parada("cambios-sin-guardar", "Volver a la principal pisaría trabajo sin guardar: "
                     + resultado.stderr.strip(), decision["rama"], principal=principal, archivos=sin_guardar(git)[1])
    if decision["accion"] == "ofrecer":
        git.hacer("switch", "--quiet", "-c", decision["rama_nueva"])
        return {"accion": "guardar", "rama": decision["rama_nueva"], "principal": principal}
    return {"accion": "guardar", "rama": principal, "principal": principal}


def commit(git, args):
    actual = git.rama()
    if git.correr("diff", "--quiet", "HEAD", "--", *args.rutas).returncode == 0:
        return {"accion": "sin-cambios", "rama": actual}
    git.hacer("commit", "--quiet", *(parte for m in args.mensaje for parte in ("-m", m)), "--", *args.rutas)
    return {"accion": "empujar", "rama": actual,
            "archivos": git.lineas("show", "--name-status", "--format=", "--no-renames", "HEAD")}


def rechazo(git, args):
    _, ramas = servidor(git)
    actual = git.rama()
    if not actual:
        raise Parada("sin-rama", "La copia no está en ninguna rama.")
    if actual not in ramas:
        # Las ramas a las que se guarda ya están en el servidor; la que no está es la rama nueva, aunque siga a otra.
        raise Parada("rama-nueva-rechazada", f"El servidor rechazó también la rama nueva {actual}.", actual)
    return {"accion": "rama-nueva", "rama": actual,
            "rama_nueva": primera_libre(git, ramas, f"{args.tipo}/{nombre(args)}")}


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


def es_ruta_de_la_skill(ruta):
    """`ruta` es una de las rutas de la skill o está dentro de una, sin salir con `..` ni usar la magia de git."""
    limpia = posixpath.normpath(ruta.replace("\\", "/"))
    if ruta.startswith(("-", "/", ":")) or limpia.startswith(".."):
        return False
    return any(limpia == r.rstrip("/") or (r.endswith("/") and limpia.startswith(r)) for r in RUTAS)


def argumentos(argv):
    parser = argparse.ArgumentParser(description="Decide en qué rama guarda una skill del flujo.")
    sub = parser.add_subparsers(dest="orden", required=True)
    for orden in ("revisar", "apartar", "volver", "rechazo"):
        p = sub.add_parser(orden)
        p.add_argument("--tipo", required=True, choices=TIPOS)
        grupo = p.add_mutually_exclusive_group(required=True)
        grupo.add_argument("--epica")
        grupo.add_argument("--mockup", help="solo html-a-vista, cuando el mockup cubre varias épicas")
        if orden != "rechazo":
            p.add_argument("--epicas", help="con --mockup: las épicas del mockup, separadas por comas")
        if orden == "apartar":
            p.add_argument("--rama", help="con `elegir`: la rama del flujo donde guardar")
        if orden == "volver":
            p.add_argument("--rama-nueva", help="con `ofrecer` y el sí de la persona: la `rama_nueva` aceptada")
        p.add_argument("--repo", default=".")
    p = sub.add_parser("commit")
    p.add_argument("-m", dest="mensaje", action="append", required=True, help="un párrafo del mensaje")
    p.add_argument("--repo", default=".")
    p.add_argument("rutas", nargs="+", help="después de --: las rutas de la skill que agregaste con git add")
    if argv[:1] == ["commit"] and "--" not in argv:
        parser.error("commit lleva las rutas después de --")
    args = parser.parse_args(argv)
    if args.orden == "commit":
        for ruta in args.rutas:
            if not es_ruta_de_la_skill(ruta):
                parser.error(f"{ruta!r} no es una ruta de la skill: van {', '.join(RUTAS)} o rutas dentro de ellas")
        return args
    args.epicas = args.epicas.split(",") if getattr(args, "epicas", None) is not None else None
    for valor in [args.mockup if args.epica is None else args.epica, *(args.epicas or [])]:
        problema = problema_del_nombre(valor)
        if problema:
            parser.error(f"{valor!r} no sirve como nombre de rama: {problema}")
    if args.mockup and args.tipo != "diseno":
        parser.error("--mockup va solo con --tipo diseno")
    if args.orden != "rechazo" and bool(args.mockup) != bool(args.epicas):
        parser.error("--mockup y --epicas van juntos")
    if args.epicas and (len(args.epicas) < 2 or len(set(args.epicas)) != len(args.epicas)):
        parser.error("--epicas lleva dos o más épicas distintas; con una sola, usa --epica")
    return args


ORDENES = {"revisar": revisar, "apartar": apartar, "volver": volver, "commit": commit, "rechazo": rechazo}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    args = argumentos(argv)
    git = Git(args.repo)
    try:
        salida = ORDENES[args.orden](git, args)
    except Parada as parada:
        salida = parada.salida
    print(json.dumps(salida))
    return 0


if __name__ == "__main__":
    sys.exit(main())
