#!/usr/bin/env python3
"""Decide en qué rama guarda una skill del flujo y protege el trabajo que la persona tenía en la copia.

Uso, desde el repositorio de diseño o con --repo:
  flujo rama revisar --tipo <spec|tickets|diseno> --epica <épica>
  flujo rama revisar --tipo diseno --mockup <mockup> --epicas <épica>,<épica>[,...]
  flujo rama apartar <los mismos --tipo y --epica, o --mockup y --epicas> [--rama <rama>]
  flujo rama volver <los mismos --tipo y --epica, o --mockup y --epicas> [--rama-nueva <rama>]
  flujo rama commit (-F <archivo> | -m <mensaje> [-m <párrafo>...]) -- <ruta>...
  flujo rama rechazo --tipo <spec|tickets|diseno> --epica <épica>
  flujo rama rechazo --tipo diseno --mockup <mockup>

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
         parar    cualquier otro caso, con `motivo` y `detalle`. Antes que nada, para con `copia-no-soportada` y
                  `rutas` si en el camino del cambio de rama hay un submódulo, de la copia o de la rama a la que va,
                  un repositorio git anidado en la carpeta, ignorado o no, o un enlace simbólico sin seguimiento,
                  apunte adonde apunte. Para un submódulo o un repositorio anidado, el camino son las rutas que
                  cambian entre la copia y la rama a la que va, las que `apartar` guardaría y las sin seguimiento que
                  el cambio de rama reemplaza o borra, y está en el camino si una de esas rutas es la suya, está
                  dentro de él o lo contiene. Un enlace está en el camino donde la rama a la que va tiene un archivo
                  o una carpeta de sus archivos, o dentro de una carpeta donde tiene un archivo. Uno fuera del camino
                  no detiene, tampoco una copia de `git worktree` de este repositorio fuera del camino; un
                  repositorio anidado dentro de `design/` o `specs/`, ignorado o no, detiene siempre (Q184). Se mira
                  contra la rama a la que va `apartar` y, con más de una rama viva para este trabajo, contra cada
                  una, también la que se elegiría con --rama: `revisar` lo dice antes del sí, y `apartar` para igual
                  antes de apartar o cambiar de rama. Se resuelve a mano (Q177, Q180, Q182, Q184).
                  Después, para con `rama-en-otra-copia` y `rutas`, las de esas copias, si la rama a la que van
                  `apartar` o `volver`, también la principal y, con más de una rama viva, cualquiera de ellas, está
                  puesta en otra copia de `git worktree` de este repositorio: git no la deja cambiar ni igualar desde
                  acá. Lo dice antes del sí y sin mover nada; se resuelve cambiando de rama en esa otra copia o
                  cerrándola (Q185).
                  En lugar de `guardar`, `ofrecer` o `volver`, para con `cambios-sin-guardar` si hay trabajo sin
                  guardar que entraría en el commit de la skill: en sus rutas, con los archivos nuevos, o preparado
                  en el índice, en cualquier ruta; con `ofrecer`, también cualquier cambio de un archivo con
                  seguimiento; con `volver` y `ofrecer`, también un archivo sin seguimiento en el camino del cambio
                  de rama, ignorado o no y aunque sea igual al de la principal, porque el cambio de rama no pasaría
                  (Q169, Q175).
                  Y para con `principal-adelantada` si se va a guardar desde la principal y la de esta copia tiene
                  commits que el servidor no tiene; ahí cuenta también lo que traería igualarla al servidor (Q170).
         Todas llevan `principal` cuando el servidor respondió y `rama` cuando la copia está en una. Con trabajo
         sin guardar, `archivos` trae sus líneas de `git status --porcelain`, con las rutas sin escapar: lo que
         `apartar` guardaría, y `!! <ruta>` para un ignorado en el camino del cambio de rama. Con la principal
         adelantada, `commits` trae esos commits.

apartar  con el sí de la persona, ante `otra-rama`, `sin-rama`, `commits-sin-empujar`, `cambios-sin-guardar` o
         `principal-adelantada`. Guarda en `apartado/<rama>` (cada `/` cambiada por `-`, `sin-rama` con HEAD separado,
         con el primer sufijo libre, o el de otra corrida que ya tiene lo mismo y que ninguna copia de `git worktree`
         tiene en uso) lo que había, con un índice temporal, antes de tocar la carpeta (Q171) y sin los hooks de commit
         ni de checkout (`reference-transaction` y `post-index-change` sí pueden correr, y si uno rechaza, para antes de
         tocar HEAD, el índice o la carpeta; Q174): primero lo que estaba preparado, tal cual, después los cambios de
         los archivos con seguimiento, los archivos nuevos de las rutas que no están ignorados y los archivos sin
         seguimiento que el cambio de rama pisaría o no dejaría pasar; los demás archivos sin seguimiento no se tocan.
         Con HEAD separado guarda también los commits que no están en ninguna rama. Si se va a guardar desde la
         principal y tiene commits que el servidor no tiene, los guarda en `apartado/<principal>` y la iguala al
         servidor. Vuelve después a la rama del flujo: la actual, si `revisar` daba `guardar`, `ofrecer` o `volver`; si
         no, la rama viva del servidor para este trabajo, `<tipo>/<nombre>` con sufijos exactos, o la principal. Si esa
         es la rama actual y no sigue a la del servidor, la iguala al servidor, con sus commits propios antes en
         `apartado/<rama>`, y la deja siguiéndola. Devuelve lo que devuelve `revisar` desde ahí, con `apartado` (las
         ramas donde quedó lo apartado) y `desde` (la rama donde estaba, o null). Con lo apartado, la copia pasa a
         `apartado/<rama>` sin tocar la carpeta y de ahí cambia a la rama del flujo con
         `git switch --no-overwrite-ignore`, que se niega ante un ignorado que la predicción no vio en lugar de borrarlo
         (Q172, Q175); igualar la principal sin cambiar de rama (`reset --keep`) no tiene esa opción y depende de la
         predicción. El último commit del apartado lleva `Destino: <rama>`, la rama del flujo a la que va (Q173). Con
         más de una rama viva para este trabajo devuelve `elegir`, con `ramas`, y --rama <una de ellas> vuelve a esa.

volver   con `volver`, o con `ofrecer` y el sí de la persona a `rama_nueva`, que va en --rama-nueva. Corre `revisar`
         otra vez: si devuelve eso, iguala la principal local al servidor, cambia a ella y, con `ofrecer`, crea
         `rama_nueva`. Devuelve `guardar` con la rama donde quedó. Con cualquier otra `accion`, o con `ofrecer` y
         otra `rama_nueva`, no cambia nada y la devuelve. Si el cambio de rama pisaría un cambio sin guardar, no
         cambia nada y para con `cambios-sin-guardar`.

commit   después de `git add` de lo que escribió la skill. Hace el commit solo con las rutas dadas, que tienen que
         estar dentro de las de la skill, con un -m por párrafo o con -F y el mensaje en un archivo UTF-8, con o sin
         BOM, relativo a donde corre la orden: así el mensaje no pasa por la línea de órdenes (Q162). Devuelve
         `empujar` con `rama` y `archivos` (estado y ruta de cada uno, separados por un tab), o `sin-cambios` si esas
         rutas no cambiaron. Si una ruta no está en la copia y no cambió, no hace el commit y para con
         `ruta-que-falta` y `rutas`.

rechazo  después de que el servidor rechazó el push a la rama actual por algo que no son credenciales. Devuelve
         `rama-nueva` con `rama`, la actual, y `rama_nueva`: `<tipo>/<épica>` o, si ya existe en local o en el
         servidor, el primer sufijo libre (`-2`, `-3`). Si la rama actual no está en el servidor, es la rama nueva,
         la de `rama-nueva` o la `rama_nueva` de `ofrecer`, aunque siga a otra rama, y para con
         `rama-nueva-rechazada`, sin otro sufijo.

Si git falla en `apartar`, `volver` o `commit`, para con `error-de-git` y el mensaje de git en `detalle`. `apartar` no
deshace nada: `apartado` lista las ramas donde ya quedó lo apartado y `rama` dice dónde quedó la copia. Si falla antes
del `git switch`, la carpeta está como estaba. Si falla el `git switch`, la copia queda en `apartado/<rama>` sin cambios
sin guardar, y otra corrida de `apartar`, sin nada nuevo que guardar, va a la rama de su `Destino:` sin volver a
calcularla y hace lo que faltaba para llegar, como igualarla al servidor (Q173). Lo hace solo si el último commit es uno
de los dos que escribe `apartar` y su `Destino:` es una rama a la que `revisar` podría mandar esta corrida: una rama viva
del servidor para este trabajo; otra rama, no la principal, donde daría `guardar`, `ofrecer` o `volver`, también una
local cuya copia en el servidor ya no está; o la principal, solo si el apartado salió de ella o si no hay una rama viva
del servidor para este trabajo; si no, la calcula otra vez, y `revisar` arma `archivos` contra esa misma rama (Q178,
Q179, Q181). El reintento sabe que la rama del `Destino:` es la de la que salió el apartado solo por el nombre del
apartado; un apartado sin commits propios, de HEAD separado solo con commits sueltos, no lleva `Destino:` y el reintento
calcula la rama otra vez; y si en una corrida que venía de `ofrecer` o `volver` falla igualar la principal adelantada,
el reintento no lo rehace y `revisar` vuelve a dar `principal-adelantada`, con otro sí (Q176). Si el índice está en uso
(`index.lock`), para antes de tocarlo, y otra corrida reusa el apartado; si no lo puede escribir, deja HEAD en la rama
de origen y no deja su `index.lock`.

`fetch` y `ls-remote` esperan al servidor `RAMA_TOPE` segundos (60 si no está); pasado eso, matan a git y a sus
hijos (`taskkill /T` en Windows) y paran con `sin-servidor`. git nunca pide credenciales por la terminal.

Escribe en stdout un objeto JSON con `accion` y sale con 0. Con uso incorrecto, una épica o un mockup que no sirve
como nombre de rama (con mayúsculas, o que termina en guion y número, como `fase-2`), o una ruta de commit que no es
de la skill, o un -F que no se puede leer, no es UTF-8 o tiene bytes nulos (Q167), sale con 2 sin escribir en
stdout y dice en stderr por qué. Si no encuentra git, sale con 1.
"""
import argparse
import json
import os
import posixpath
import re
import shutil
import signal
import subprocess
import sys
import tempfile

TIPOS = ("spec", "tickets", "diseno")
RUTAS = ("design/", "specs/", ".gitignore", ".claude/pm-conventions.md")
# Las carpetas de la skill donde todo repositorio anidado detiene (Q184).
CARPETAS_DE_LA_SKILL = ("design", "specs")
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
    def __init__(self, repo, indice=None):
        self.repo = repo
        self.indice = indice

    def correr(self, *args, tope=None):
        """Corre git en el repositorio, sin pedir credenciales por la terminal y con las rutas sin escapar. Con `tope`,
        en segundos, mata a git y a lo que haya lanzado si no termina a tiempo, y devuelve código 124."""
        orden = ["git", "-c", "core.quotePath=false", "-C", self.repo, *args]
        entorno = {**os.environ, "GIT_TERMINAL_PROMPT": "0", **({"GIT_INDEX_FILE": self.indice} if self.indice else {})}
        proceso = subprocess.Popen(orden, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                                   text=True, encoding="utf-8", errors="replace", env=entorno,
                                   start_new_session=os.name != "nt")
        try:
            salida, error = proceso.communicate(timeout=tope)
        except subprocess.TimeoutExpired:
            matar_arbol(proceso)
            try:
                proceso.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                # Un hijo que no murió sigue con la salida de git abierta: se deja de leer y se sigue (B2).
                for tubo in (proceso.stdout, proceso.stderr):
                    tubo.close()
            return subprocess.CompletedProcess(orden, 124, "", f"el servidor no respondió en {tope} segundos")
        return subprocess.CompletedProcess(orden, proceso.returncode, salida, error)

    def salida(self, *args):
        resultado = self.correr(*args)
        return resultado.stdout.strip() if resultado.returncode == 0 else None

    def lineas(self, *args):
        """Las líneas de la salida, sin quitar los espacios del comienzo, que en `git status` son datos."""
        resultado = self.correr(*args)
        return [l for l in resultado.stdout.split("\n") if l] if resultado.returncode == 0 else []

    def rutas(self, *args):
        """Las rutas de una orden con `-z`."""
        resultado = self.correr(*args)
        return [r for r in resultado.stdout.split("\0") if r] if resultado.returncode == 0 else []

    def hacer(self, *args):
        """Una orden que cambia la copia: si git falla, para con su mensaje."""
        resultado = self.correr(*args)
        if resultado.returncode != 0:
            raise Parada("error-de-git", f"`git {' '.join(args)}` falló: " + resultado.stderr.strip(), self.rama())

    def existe(self, ref):
        return self.correr("rev-parse", "--verify", "--quiet", ref).returncode == 0

    def rama(self):
        return self.salida("symbolic-ref", "--quiet", "--short", "HEAD")


def matar_arbol(proceso):
    """Mata a git y a los hijos que lanzó para hablar con el servidor: en Windows con `taskkill /T`, en los demás con
    el grupo de procesos que se le dio al lanzarlo."""
    if os.name == "nt":
        try:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(proceso.pid)], capture_output=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            pass
        proceso.kill()
    else:
        try:
            os.killpg(proceso.pid, signal.SIGKILL)
        except OSError:
            proceso.kill()


def tope():
    """Los segundos que se espera al servidor: `RAMA_TOPE` en el entorno, o 60."""
    try:
        return max(1, int(os.environ.get("RAMA_TOPE", "60")))
    except ValueError:
        return 60


def servidor(git):
    """`git fetch --prune` y lo que el servidor dice tener: su rama principal y el conjunto de sus ramas."""
    if git.salida("remote", "get-url", "origin") is None:
        raise Parada("sin-servidor", "El repositorio no tiene un servidor `origin` configurado.")
    for args in (("fetch", "--quiet", "--prune", "origin"),
                 ("ls-remote", "--symref", "origin", "HEAD", "refs/heads/*")):
        resultado = git.correr(*args, tope=tope())
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


def rama_del_flujo(git, args, principal, ramas, actual=None):
    """Lo que dice la rama actual, o `actual`, sin mirar el trabajo sin guardar: `guardar`, `ofrecer` o `volver`, o
    Parada."""
    actual = actual or git.rama()
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
        if trabajo_en_la_principal(git, principal, actual):
            return {"accion": "volver", "rama": actual, "principal": principal}
        raise Parada("commits-sin-empujar",
                     f"La rama {actual} ya no está en el servidor y tiene commits que el servidor no tiene.", actual,
                     principal=principal)
    if actual in ramas and es_del_flujo(actual, nombre(args), (args.tipo,)):
        raise Parada("otra-rama", f"La rama {actual} es de este trabajo y está en el servidor, pero no sigue a la del "
                     "servidor: `git push` no iría a ella.", actual, principal=principal)
    raise Parada("otra-rama", f"La rama {actual} no es la principal ni una rama de este trabajo en el servidor.", actual,
                 principal=principal)


def llega_a_la_principal(decision):
    """La skill va a guardar desde la principal: ahí, en la rama nueva que sale de ella, o al volver."""
    return decision["accion"] in ("ofrecer", "volver") or decision["rama"] == decision["principal"]


def destino_del_flujo(args, principal, ramas, elegida=None):
    """Adónde vuelve `apartar` desde una rama que no es de este trabajo: (rama o None si hay que elegir, candidatas).
    La rama viva del servidor para este trabajo, con sufijos exactos, o la principal."""
    candidatas = sorted(r for r in ramas if es_del_flujo(r, nombre(args), (args.tipo,)))
    if len(candidatas) == 1:
        return candidatas[0], candidatas
    if candidatas:
        return (elegida if elegida in candidatas else None), candidatas
    return principal, candidatas


def ref_de_llegada(git, rama, principal, al_servidor=False):
    """La ref a la que va de verdad el `git switch` a `rama`: la del servidor si la rama se iguala a él (la principal,
    o con `al_servidor`) o si la local no existe o avanza hasta él; si no, la local, con sus commits propios (M1)."""
    local, remota = f"refs/heads/{rama}", f"refs/remotes/origin/{rama}"
    if rama == principal or al_servidor or not git.existe(local):
        return remota
    return remota if git.correr("merge-base", "--is-ancestor", local, remota).returncode == 0 else local


def llegada(decision, destino, principal):
    """La rama a la que la copia va a cambiar, o None si se queda en la actual."""
    if decision is None:
        return destino
    return principal if decision["accion"] in ("ofrecer", "volver") else None


def revisar(git, args, del_servidor=None):
    principal, ramas = del_servidor or servidor(git)
    desde = git.rama()
    try:
        decision = rama_del_flujo(git, args, principal, ramas)
    except Parada as parada:
        if parada.motivo in APARTABLES:
            destino, candidatas, seguir = destino_de_apartar(git, args, principal, ramas, desde)
            # Antes del sí, contra cada rama a la que puede ir `apartar`, con lo que guardaría (Q180).
            no_soportada(git, finales(git, None, destino, candidatas, desde, principal, seguir), principal,
                         sin_guardar(git)[1])
            en_otra_copia(git, ramas_de_destino(None, destino, candidatas, principal), principal)
            amplio = sin_guardar(git, ref_final(git, None, destino, desde, principal, seguir))[1]
            if amplio:
                parada.salida["archivos"] = amplio
        raise
    destino = llegada(decision, None, principal)
    estrecho, amplio = sin_guardar(git, destino and f"refs/remotes/origin/{destino}")
    # `ofrecer` cambia de rama con lo que haya: cuenta cualquier cambio de un archivo con seguimiento.
    aparta = estrecho or (decision["accion"] == "ofrecer" and amplio)
    commits = adelantada(git, principal) if llega_a_la_principal(decision) else []
    # Sin nada que apartar, la skill guarda sin `apartar`, y lo que hay sin guardar no está en el camino (Q180).
    no_soportada(git, finales(git, decision, desde, [], desde, principal, False), principal,
                 amplio if aparta or commits else [])
    en_otra_copia(git, ramas_de_destino(decision, desde, [], principal), principal)
    if aparta:
        raise Parada("cambios-sin-guardar", f"La copia tiene trabajo sin guardar en la rama {decision['rama']} que "
                     "entraría en el commit de la skill o que el cambio de rama pisaría.", decision["rama"],
                     principal=principal, archivos=amplio)
    if commits:
        # `apartar` iguala la principal al servidor, que trae sus archivos aunque la copia no cambie de rama (Q170).
        raise Parada("principal-adelantada", f"La rama principal {principal} de esta copia tiene commits que el "
                     "servidor no tiene, y el push los subiría.", decision["rama"], principal=principal,
                     archivos=sin_guardar(git, f"refs/remotes/origin/{principal}")[1], commits=commits)
    return decision


def sin_guardar(git, destino=None):
    """El trabajo sin guardar, en líneas de `git status --porcelain`: (lo que entraría en el commit de la skill o el
    cambio a `destino` pisaría, lo que se aparta). Lo primero son las rutas de la skill, con sus archivos nuevos, lo
    preparado en el índice, en cualquier ruta, y los archivos sin seguimiento que `destino` tiene, en `choques`; lo
    segundo suma los cambios de cualquier archivo con seguimiento. Un submódulo con cambios adentro no cuenta: `apartar`
    no los guarda. Uno en el camino no llega acá: `revisar` y `apartar` paran antes con `copia-no-soportada` (Q180)."""
    en_rutas = estado(git, "--untracked-files=all", "--", *RUTAS)
    seguidos = estado(git, "--untracked-files=no")
    preparados = [l for l in seguidos if l[0] not in " ?"]
    chocan = choques(git, destino) if destino else []
    return unicas(en_rutas + preparados + chocan), unicas(en_rutas + seguidos + chocan)


def estado(git, *args):
    """Las líneas de `git status --porcelain`, `XY <ruta>` o `XY <antes> -> <después>`, con las rutas tal cual, sin
    comillas ni escapes aunque lleven espacios o tildes (N9)."""
    partes = git.rutas("status", "--porcelain", "-z", "--ignore-submodules=dirty", *args)
    lineas = []
    while partes:
        linea = partes.pop(0)
        if (linea[0] in "RC" or linea[1] in "RC") and partes:
            linea = f"{linea[:3]}{partes.pop(0)} -> {linea[3:]}"
        lineas.append(linea)
    return lineas


def choques(git, destino):
    return camino(git, destino)[0]


def camino(git, destino):
    """Lo que hay sin seguimiento en el camino de `git switch` a `destino`, lo que el `switch` reemplaza o borra: lo que
    `destino` tiene en la misma ruta, lo que no es una carpeta donde `destino` tiene una carpeta, y lo que hay dentro de
    una carpeta donde `destino` tiene un archivo (H1 de la revisión 4). Devuelve (las líneas de los archivos, los
    enlaces simbólicos). Un archivo va como `?? <ruta>` si no está ignorado y `!! <ruta>` si lo está, aunque el
    contenido sea el mismo: git se niega igual ante uno sin seguimiento (Q168), y ante un ignorado con
    `--no-overwrite-ignore` (Q175). Un enlace va aparte, apunte adonde apunte, porque hace parar con
    `copia-no-soportada` (Q177)."""
    raiz = git.salida("rev-parse", "--show-toplevel")
    if not raiz or not git.existe(destino):
        return [], []
    seguidos = set(git.rutas("ls-files", "-z"))
    en_destino, perdidos, enlaces, carpetas, vistas = set(), set(), set(), [], set()
    for entrada in git.rutas("ls-tree", "-r", "-z", "--full-tree", destino):
        datos, _, ruta = entrada.partition("\t")
        if datos.split(" ")[1] != "blob":
            continue
        # Una carpeta de `destino` que en la copia es un archivo o un enlace sin seguimiento: el `switch` lo reemplaza.
        partes = ruta.split("/")
        for i in range(1, len(partes)):
            carpeta = "/".join(partes[:i])
            if carpeta not in vistas:
                vistas.add(carpeta)
                lugar = os.path.join(raiz, carpeta)
                if carpeta in seguidos:
                    continue
                if os.path.islink(lugar):
                    enlaces.add(carpeta)
                elif os.path.lexists(lugar) and not os.path.isdir(lugar):
                    perdidos.add(carpeta)
        if ruta in seguidos:
            continue
        lugar = os.path.join(raiz, ruta)
        if os.path.islink(lugar):
            enlaces.add(ruta)
        elif os.path.isdir(lugar):
            carpetas.append(ruta)
        elif os.path.isfile(lugar):
            en_destino.add(ruta)
    # Un archivo de `destino` que en la copia es una carpeta: el `switch` borra lo que tiene sin seguimiento.
    if carpetas:
        for ruta in git.rutas("-C", raiz, "ls-files", "-z", "--others", "--", *carpetas):
            (enlaces if os.path.islink(os.path.join(raiz, ruta)) else perdidos).add(ruta)
    rutas = sorted(en_destino | perdidos)
    if not rutas:
        return [], sorted(enlaces)
    ignorados = set(git.rutas("-C", raiz, "ls-files", "-z", "--others", "--ignored", "--exclude-standard", "--", *rutas))
    return [("!! " + r) if r in ignorados else ("?? " + r) for r in rutas], sorted(enlaces)


def forma(git, finales, guardados=()):
    """Lo que `apartar` no sabe guardar sin riesgo de perder trabajo y está en el camino del cambio a alguna de las refs
    de `finales` (Q177, Q180), como {ruta: qué es}. El camino son las rutas que cambian entre la copia, HEAD y el
    índice, y cada ref; las de `guardados`, líneas de `git status --porcelain` de lo que `apartar` guardaría; y lo que
    `camino` encuentra sin seguimiento. Un submódulo de la copia o de una ref, o un repositorio git anidado, ignorado o
    no, está en el camino si una de esas rutas es la suya, está dentro de él o lo contiene; un enlace simbólico sin
    seguimiento, si `camino` lo encuentra (H5 de la revisión 5). Sin cambio de rama ni nada que guardar no hay camino.
    Aparte, todo repositorio anidado dentro de `design/` o `specs/`, ignorado o no, esté o no en el camino (Q184)."""
    raiz = git.salida("rev-parse", "--show-toplevel")
    if not raiz:
        return {}
    rutas, enlaces = rutas_de_estado(guardados), set()
    con_head = git.existe("HEAD")
    submodulos = submodulos_de(git, None) | (submodulos_de(git, "HEAD") if con_head else set())
    for final in finales:
        lineas, de_enlaces = camino(git, final)
        rutas.update(linea[3:].rstrip("/") for linea in lineas)
        enlaces.update(de_enlaces)
        rutas.update(git.rutas("diff-index", "--cached", "-z", "--name-only", "--no-renames", "--ignore-submodules=none",
                               final))
        if con_head:
            rutas.update(git.rutas("diff-tree", "-r", "-z", "--name-only", "--no-renames", "--ignore-submodules=none",
                                   "HEAD", final))
        submodulos |= submodulos_de(git, final)
    # Las rutas del camino y las carpetas que las contienen.
    cerca = {"/".join(partes[:i]) for partes in (r.split("/") for r in rutas) for i in range(1, len(partes) + 1)}

    def en_el_camino(ruta):
        partes = ruta.split("/")
        return ruta in cerca or any("/".join(partes[:i]) in rutas for i in range(1, len(partes)))

    encontradas = {ruta: "submódulo" for ruta in sorted(submodulos) if en_el_camino(ruta)}
    vinculadas = copias_vinculadas(git, raiz)
    # Q184: en las rutas de la skill, todo repositorio anidado, ignorado o no, esté o no en el camino. Un submódulo
    # (Q180) y una copia de `git worktree` de este repositorio (Q182) ahí siguen contando solo en el camino.
    en_la_skill = {r for r in anidados(raiz, set(), CARPETAS_DE_LA_SKILL)
                   if r not in submodulos and (r not in vinculadas or en_el_camino(r))}
    anidados_en_el_camino = anidados(raiz, cerca, rutas)
    for ruta in sorted(anidados_en_el_camino | en_la_skill):
        encontradas.setdefault(ruta, "copia de `git worktree` de este repositorio" if ruta in vinculadas
                               else "repositorio git anidado" if ruta in anidados_en_el_camino
                               else "repositorio git anidado en las rutas de la skill, Q184")
    for ruta in sorted(enlaces):
        encontradas.setdefault(ruta, "enlace simbólico en el camino del cambio de rama")
    return encontradas


def rutas_de_estado(lineas):
    """Las rutas de líneas de `git status --porcelain`, las dos de un renombrado, sin la `/` de una carpeta."""
    rutas = set()
    for linea in lineas:
        cuerpo = linea[3:]
        for ruta in (cuerpo.split(" -> ", 1) if set(linea[:2]) & set("RC") else [cuerpo]):
            rutas.add(ruta.rstrip("/"))
    return rutas


def submodulos_de(git, ref):
    """Las rutas de los submódulos de `ref`, o del índice con None."""
    entradas = (git.rutas("ls-tree", "-r", "-z", "--full-tree", ref) if ref
                else git.rutas("-C", git.salida("rev-parse", "--show-toplevel"), "ls-files", "-z", "--stage"))
    return {entrada.partition("\t")[2] for entrada in entradas if entrada.startswith("160000 ")}


def anidados(raiz, cerca, rutas):
    """Los repositorios git anidados en el camino, con `.git` como archivo o como carpeta: una carpeta de `cerca`, o una
    carpeta dentro de una ruta del camino que en la copia es una carpeta. Así se ven también los que git no lista como
    `<ruta>/` porque su carpeta tiene archivos con seguimiento (H1 de la revisión 6)."""
    encontrados = {c for c in cerca if os.path.lexists(os.path.join(raiz, c, ".git"))}
    for ruta in rutas:
        lugar = os.path.join(raiz, ruta)
        if os.path.isdir(lugar) and not os.path.islink(lugar):
            for carpeta, subcarpetas, archivos in os.walk(lugar):
                if ".git" in subcarpetas or ".git" in archivos:
                    encontrados.add(os.path.relpath(carpeta, raiz).replace(os.sep, "/"))
                    subcarpetas[:] = []
                subcarpetas.sort()
    return encontrados


def copias_vinculadas(git, raiz):
    """Las rutas, dentro de la carpeta, de las copias de `git worktree` de este repositorio (Q182)."""
    base = os.path.realpath(raiz)
    rutas = set()
    for linea in git.lineas("worktree", "list", "--porcelain"):
        if linea.startswith("worktree "):
            relativa = os.path.relpath(os.path.realpath(linea[len("worktree "):]), base).replace(os.sep, "/")
            if relativa != "." and not relativa.startswith("../") and relativa != "..":
                rutas.add(relativa)
    return rutas


def finales(git, decision, destino, candidatas, desde, principal, seguir):
    """Las refs a las que puede llevar la carpeta `apartar`, o la skill sin él: la de `ref_final` o, si hay que elegir,
    la de cada candidata, como si viniera con --rama, y la de la principal si la iguala sin cambiar de rama (Q180)."""
    if decision is not None or destino is not None:
        final = ref_final(git, decision, destino, desde, principal, seguir)
        return [final] if final else []
    refs = [ref_final(git, None, c, desde, principal, c == desde) for c in candidatas]
    return unicas([r for r in [*refs, ref_final(git, None, None, desde, principal, False)] if r])


def no_soportada(git, finales, principal, guardados=()):
    """Para con `copia-no-soportada` si en el camino hay algo que `apartar` no sabe guardar (Q177, Q180)."""
    encontradas = forma(git, finales, guardados)
    if encontradas:
        rutas = sorted(encontradas)
        raise Parada("copia-no-soportada", "La copia tiene en el camino del cambio de rama algo que `apartar` no sabe "
                     "guardar sin riesgo de perder trabajo, y se resuelve a mano (Q177, Q180): "
                     + ", ".join(f"{r} ({encontradas[r]})" for r in rutas) + ".", git.rama(), principal=principal,
                     rutas=rutas)


def ramas_de_destino(decision, destino, candidatas, principal):
    """Las ramas a las que cambia o que iguala `apartar`, o `volver` después de `revisar`: la principal con `ofrecer` y
    `volver`, el destino de `apartar` o, si hay que elegir, cada candidata (Q185)."""
    if decision is not None:
        return [principal] if decision["accion"] in ("ofrecer", "volver") else []
    return [destino] if destino is not None else list(candidatas)


def en_otra_copia(git, ramas_de_destino, principal):
    """Para con `rama-en-otra-copia` si alguna de `ramas_de_destino` está puesta en otra copia de `git worktree` de este
    repositorio, donde git no deja cambiarla ni igualarla (Q185)."""
    if not ramas_de_destino:
        return
    propia = os.path.realpath(git.salida("rev-parse", "--show-toplevel") or git.repo)
    puestas, ruta = {}, None
    for linea in git.lineas("worktree", "list", "--porcelain"):
        if linea.startswith("worktree "):
            ruta = linea[len("worktree "):]
        elif linea.startswith("branch refs/heads/") and ruta and os.path.realpath(ruta) != propia:
            rama = linea[len("branch refs/heads/"):]
            if rama in ramas_de_destino:
                puestas.setdefault(rama, ruta)
    if puestas:
        ramas = sorted(puestas)
        raise Parada("rama-en-otra-copia", "La rama a la que va `apartar` o `volver` está puesta en otra copia de "
                     "`git worktree` de este repositorio, y git no la deja cambiar ni igualar desde acá (Q185): "
                     + ", ".join(f"{r} en {puestas[r]}" for r in ramas) + ".", git.rama(), principal=principal,
                     rutas=unicas([puestas[r] for r in ramas]))


def unicas(lineas):
    return list(dict.fromkeys(lineas))


def adelantada(git, principal):
    """Los commits de la principal local que no están en la del servidor, como `<hash> <asunto>`."""
    if not git.existe(f"refs/heads/{principal}"):
        return []
    return git.lineas("log", "--format=%h %s", f"refs/remotes/origin/{principal}..refs/heads/{principal}")


def trabajo_en_la_principal(git, principal, rama):
    """Lo que `rama` tiene y no está en ninguna rama del servidor ya entró a la principal: no hay commits así, o los
    archivos que tocan desde la base común con la principal están iguales en ella (un squash merge)."""
    local = f"refs/heads/{rama}"
    pendientes = git.salida("rev-list", "--count", local, "--not", "--remotes=origin")
    if pendientes == "0":
        return True
    remota = f"refs/remotes/origin/{principal}"
    base = git.salida("merge-base", local, remota)
    if not pendientes or not base:
        return False
    tocados, distintos = archivos(git, base, local), archivos(git, local, remota)
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
            parada.salida.update({"apartado": creadas, "desde": desde, "rama": git.rama()})
        raise


def ruta_del_indice(git):
    ruta = git.salida("rev-parse", "--git-path", "index")
    return ruta and os.path.abspath(os.path.join(git.repo, ruta))


def guardar_aparte(git, ramas, donde, chocan, destino):
    """Arma el apartado de lo que hay en la copia sin tocar la carpeta, el índice ni HEAD y sin los hooks de commit ni de
    checkout (Q171, Q174): un índice temporal, copia del de la copia con sus marcas, `write-tree` y `commit-tree`.
    Primero lo preparado, tal cual, porque `git add -u` pisaría lo que está solo en el índice (H3); después los cambios
    de los archivos con seguimiento, los archivos nuevos de las rutas que no están ignorados (N1) y los sin seguimiento
    que el cambio de rama pisaría o no dejaría pasar (N2, N3). El último commit lleva `Destino: <destino>`, si lo hay
    (Q173). Crea `apartado/<rama>`, o reusa uno que ya tiene esos mismos commits, y devuelve (la rama, la ruta del
    índice temporal, que queda con el árbol del apartado)."""
    inicio = git.salida("rev-parse", "HEAD")
    real = ruta_del_indice(git)
    try:
        descriptor, ruta = tempfile.mkstemp(prefix="index.apartar-", dir=os.path.dirname(real))
        os.close(descriptor)
    except OSError as error:
        raise Parada("error-de-git", f"no se pudo crear el índice temporal: {error}", git.rama())
    try:
        try:
            shutil.copyfile(real, ruta)
        except FileNotFoundError:
            os.remove(ruta)
        except OSError as error:
            raise Parada("error-de-git", f"no se pudo copiar el índice: {error}", git.rama())
        temporal = Git(git.repo, indice=ruta)
        preparado = escribir_arbol(temporal)
        agregar(temporal, chocan)
        todo = escribir_arbol(temporal)
        commits = []
        if preparado != git.salida("rev-parse", "HEAD^{tree}"):
            commits.append((preparado, f"Apartado: lo que estaba preparado en {donde}"))
        if todo != preparado:
            commits.append((todo, f"Apartado: lo que había en {donde} antes de guardar"))
        padre = inicio
        for i, (arbol, mensaje) in enumerate(commits):
            # El último commit lleva el destino, que lee el reintento desde el apartado (Q173).
            final = destino is not None and i == len(commits) - 1
            padre = commit_tree(git, arbol, padre, mensaje, *([f"Destino: {destino}"] if final else []))
        arboles = [arbol for arbol, _ in commits]
        base = "apartado/" + donde.replace("/", "-")
        apartado = reusable(git, base, inicio, arboles, destino)
        if apartado is None:
            apartado = primera_libre(git, ramas, base)
            # Con el valor anterior vacío, update-ref falla si la rama ya existe.
            git.hacer("update-ref", f"refs/heads/{apartado}", padre, "")
        return apartado, ruta
    except BaseException:
        quitar(ruta)
        raise


def escribir_arbol(temporal):
    resultado = temporal.correr("write-tree")
    if resultado.returncode != 0:
        raise Parada("error-de-git", "`git write-tree` falló: " + resultado.stderr.strip(), temporal.rama())
    return resultado.stdout.strip()


def agregar(temporal, chocan):
    temporal.hacer("add", "-u")
    nuevos = temporal.rutas("ls-files", "-z", "--others", "--exclude-standard", "--", *RUTAS)
    if nuevos:
        temporal.hacer("add", "--", *nuevos)
    if chocan:
        temporal.hacer("-C", temporal.salida("rev-parse", "--show-toplevel"), "add", "-f", "--", *chocan)


def commit_tree(git, arbol, padre, *parrafos):
    args = ["commit-tree", arbol, "-p", padre, *(parte for p in parrafos for parte in ("-m", p))]
    resultado = git.correr(*args)
    if resultado.returncode != 0:
        raise Parada("error-de-git", f"`git {' '.join(args)}` falló: " + resultado.stderr.strip(), git.rama())
    return resultado.stdout.strip()


def destino_de(git, ref):
    """El `Destino: <rama>` del último commit de `ref`, que escribió `apartar` al guardar (Q173), o None."""
    lineas = git.lineas("log", "-1", "--format=%B", ref)
    return next((l[len("Destino: "):].strip() for l in reversed(lineas) if l.startswith("Destino: ")), None)


def reusable(git, base, inicio, arboles, destino):
    """Un `apartado/<base>` o `apartado/<base>-<n>` que ya tiene, sobre `inicio`, commits con estos mismos árboles y el
    mismo destino: lo dejó otra corrida que guardó y no alcanzó a pasar la copia al apartado (Q171). No uno que tiene
    en uso alguna copia de `git worktree` (H7 de la revisión 4)."""
    en_uso = {l[len("branch refs/heads/"):] for l in git.lineas("worktree", "list", "--porcelain")
              if l.startswith("branch refs/heads/")}
    for rama in apartados(git, base):
        if rama not in en_uso and (git.correr("merge-base", "--is-ancestor", inicio, rama).returncode == 0
                and git.lineas("log", "--reverse", "--format=%T", f"{inicio}..{rama}") == arboles
                and (not arboles or destino_de(git, rama) == destino)):
            return rama
    return None


def pasar_al_apartado(git, apartado, indice):
    """HEAD a `apartado/<rama>` y el árbol del apartado en el índice, sin tocar la carpeta (Q172): la copia queda como
    si hubiera hecho los commits ahí, y el `git switch` que sigue es el mismo de siempre. El índice se escribe con
    `index.lock`, como lo escribe git, así que otro git que lo esté usando lo frena. Si no se puede reemplazar el
    índice, HEAD vuelve adonde estaba y el candado se borra: la copia queda como estaba (H4 de la revisión 4)."""
    origen, inicio = git.rama(), git.salida("rev-parse", "HEAD")
    real = ruta_del_indice(git)
    candado = real + ".lock"
    try:
        with open(indice, "rb") as archivo:
            contenido = archivo.read()
    except OSError as error:
        raise Parada("error-de-git", f"no se pudo leer el índice temporal: {error}", git.rama())
    try:
        archivo = open(candado, "xb")
    except FileExistsError:
        raise Parada("error-de-git", f"`{candado}` existe: otro proceso de git está usando el índice.", git.rama())
    except OSError as error:
        raise Parada("error-de-git", f"no se pudo escribir `{candado}`: {error}", git.rama())
    try:
        with archivo:
            archivo.write(contenido)
    except OSError as error:
        quitar(candado)
        raise Parada("error-de-git", f"no se pudo escribir `{candado}`: {error}", git.rama())
    resultado = git.correr("symbolic-ref", "HEAD", f"refs/heads/{apartado}")
    if resultado.returncode != 0:
        quitar(candado)
        raise Parada("error-de-git", f"`git symbolic-ref HEAD refs/heads/{apartado}` falló: "
                     + resultado.stderr.strip(), git.rama())
    try:
        os.replace(candado, real)
    except OSError as error:
        if origen:
            git.correr("symbolic-ref", "HEAD", f"refs/heads/{origen}")
        else:
            git.correr("update-ref", "--no-deref", "HEAD", inicio)
        quitar(candado)
        raise Parada("error-de-git", f"no se pudo escribir `{real}`: {error}", git.rama())


def quitar(ruta):
    """Borra un archivo propio que quedó de un paso que falló; si tampoco se puede, sigue la parada de ese paso."""
    try:
        os.remove(ruta)
    except OSError:
        pass


def ref_final(git, decision, destino, desde, principal, seguir):
    """La ref cuyo árbol trae `apartar` a la carpeta, o None si la carpeta no cambia: la rama a la que cambia (con N4,
    `seguir`, se iguala al servidor; las demás van a la local si tiene commits propios, M1), o la principal del
    servidor si la copia se queda en la principal y la iguala a él (Q170)."""
    va_a = llegada(decision, destino, principal)
    if va_a:
        return ref_de_llegada(git, va_a, principal, seguir)
    if desde == principal and adelantada(git, principal):
        return f"refs/remotes/origin/{principal}"
    return None


# El mensaje del último commit de un apartado, como lo escribe `guardar_aparte`: el asunto de uno de sus dos commits,
# con la rama de la que salió, y el destino.
FORMA_DEL_APARTADO = re.compile(r"Apartado: lo que (?:estaba preparado en (?P<preparado>.+)|había en (?P<habia>.+) antes "
                                r"de guardar)\n\nDestino: (?P<destino>.+)")


def destino_guardado(git, args, desde, principal, ramas):
    """En el reintento, desde un `apartado/<rama>` sin nada nuevo que guardar, la rama del `Destino:` de su último
    commit, adonde iba la corrida que lo armó (Q173). Solo si ese commit tiene la forma de los de `apartar`, con la rama
    del nombre del apartado en el asunto (Q178), y si `revisar` podría mandar esta corrida a ese destino (Q179): una de
    las que daría `destino_del_flujo`; otra rama donde `rama_del_flujo` da `guardar`, `ofrecer` o `volver`; o la
    principal, solo si el apartado salió de ella o `destino_del_flujo` también da la principal (Q181); si no, None."""
    if not desde or not desde.startswith("apartado/") or sin_guardar(git)[1]:
        return None
    forma = FORMA_DEL_APARTADO.fullmatch(git.salida("log", "-1", "--format=%B", "HEAD") or "")
    if not forma:
        return None
    donde = forma["preparado"] or forma["habia"]
    if not re.fullmatch(rf"apartado/{re.escape(donde.replace('/', '-'))}(-[0-9]+)?", desde):
        return None
    destino = forma["destino"]
    candidatas = destino_del_flujo(args, principal, ramas)[1]
    if destino in candidatas:
        return destino
    if destino == principal:
        # Q181: la principal vale si esta corrida también iría ahí, porque salió de ella o no hay rama viva.
        return destino if donde == principal or not candidatas else None
    if git.existe(f"refs/heads/{destino}"):
        try:
            rama_del_flujo(git, args, principal, ramas, destino)
            return destino
        except Parada:
            pass
    return None


def destino_de_apartar(git, args, principal, ramas, desde):
    """Adónde va `apartar` desde una rama que no es de este trabajo: (la rama, o None si hay que elegir; las candidatas;
    si la iguala al servidor y le pone el upstream, N4). En el reintento desde un apartado, la de su `Destino:` (Q173,
    Q178); si no, la rama viva del servidor para este trabajo, o la principal."""
    destino = destino_guardado(git, args, desde, principal, ramas)
    if destino is None:
        destino, candidatas = destino_del_flujo(args, principal, ramas, getattr(args, "rama", None))
        # N4: la rama de este trabajo de la que salió `apartar` está en el servidor pero no lo sigue.
        return destino, candidatas, destino is not None and destino == desde
    # En el reintento desde `apartado/<rama>`, la rama de la que salió es la del nombre del apartado.
    seguir = (destino != principal and destino in ramas and upstream(git, destino) != destino
              and re.fullmatch(rf"apartado/{re.escape(destino.replace('/', '-'))}(-[0-9]+)?", desde) is not None)
    return destino, [], seguir


def apartar_y_volver(git, args, principal, ramas, desde, creadas):
    try:
        decision = rama_del_flujo(git, args, principal, ramas)
        destino, candidatas, seguir = desde, [], False
    except Parada as parada:
        if parada.motivo not in APARTABLES:
            raise
        decision = None
        destino, candidatas, seguir = destino_de_apartar(git, args, principal, ramas, desde)
    final = ref_final(git, decision, destino, desde, principal, seguir)
    # Antes de escribir nada: con un submódulo, un repositorio anidado o un enlace en el camino, no hace nada (Q177,
    # Q180).
    no_soportada(git, finales(git, decision, destino, candidatas, desde, principal, seguir), principal,
                 sin_guardar(git)[1])
    en_otra_copia(git, ramas_de_destino(decision, destino, candidatas, principal), principal)
    chocan = [l[3:] for l in choques(git, final)] if final else []

    sueltos = desde is None and git.salida("rev-list", "--count", "HEAD", "--not", "--branches", "--remotes") != "0"
    if sin_guardar(git)[1] or chocan or sueltos:
        apartado, indice = guardar_aparte(git, ramas, desde or "sin-rama", chocan, destino)
        creadas.append(apartado)
        try:
            pasar_al_apartado(git, apartado, indice)
        finally:
            quitar(indice)

    if (destino == principal or (decision and llega_a_la_principal(decision))) and adelantada(git, principal):
        apartar_commits(git, ramas, principal, creadas)
        igualar(git, principal)

    if destino is None:
        return {"accion": "elegir", "ramas": candidatas, "principal": principal, "apartado": creadas, "desde": desde}
    if seguir:
        seguir_al_servidor(git, ramas, destino, creadas)
    if git.rama() != destino:
        if destino != desde:
            al_dia(git, destino)
        # Con `--no-overwrite-ignore`, git se niega ante un ignorado que la predicción de choques no vio (Q175).
        git.hacer("switch", "--quiet", "--no-overwrite-ignore", destino)
    try:
        salida = revisar(git, args, (principal, ramas))
    except Parada as parada:
        salida = parada.salida
    return {**salida, "apartado": creadas, "desde": desde}


def igualar(git, rama):
    """La rama local igual a la del servidor, esté o no la copia en ella."""
    remota = f"refs/remotes/origin/{rama}"
    if git.rama() == rama:
        git.hacer("reset", "--quiet", "--keep", remota)
    else:
        git.hacer("branch", "--quiet", "-f", rama, remota)


def seguir_al_servidor(git, ramas, rama, creadas):
    """Una rama de este trabajo que está en el servidor pero no lo sigue pasa a seguirlo (N4). Si tiene commits que el
    servidor no tiene, quedan antes en `apartado/<rama>`, y la rama se iguala al servidor."""
    local, remota = f"refs/heads/{rama}", f"refs/remotes/origin/{rama}"
    if git.correr("merge-base", "--is-ancestor", local, remota).returncode != 0:
        apartar_commits(git, ramas, rama, creadas)
    # El upstream después de igualar: con upstream vivo, otra corrida tomaría esos commits como del flujo y los subiría.
    igualar(git, rama)
    git.hacer("branch", "--quiet", f"--set-upstream-to=origin/{rama}", rama)


def apartar_commits(git, ramas, rama, creadas):
    """Los commits de `rama` que el servidor no tiene, en `apartado/<rama>`: en el apartado recién creado si ya los
    tiene, en uno de otra corrida que los tiene (Q171), o en uno nuevo."""
    local = f"refs/heads/{rama}"
    if creadas and git.correr("merge-base", "--is-ancestor", local, creadas[-1]).returncode == 0:
        return
    base = "apartado/" + rama.replace("/", "-")
    apartado = next((r for r in apartados(git, base)
                     if git.correr("merge-base", "--is-ancestor", local, r).returncode == 0), None)
    if apartado is None:
        apartado = primera_libre(git, ramas, base)
        git.hacer("branch", apartado, local)
    creadas.append(apartado)


def apartados(git, base):
    """Las ramas locales `apartado/<base>` y `apartado/<base>-<n>`."""
    patron = re.compile(rf"{re.escape(base)}(-[0-9]+)?")
    return [r for r in git.lineas("for-each-ref", "--format=%(refname:short)", "refs/heads/apartado/")
            if patron.fullmatch(r)]


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
                     + resultado.stderr.strip(), decision["rama"], principal=principal,
                     archivos=sin_guardar(git, f"refs/remotes/origin/{principal}")[1])
    if decision["accion"] == "ofrecer":
        git.hacer("switch", "--quiet", "-c", decision["rama_nueva"])
        return {"accion": "guardar", "rama": decision["rama_nueva"], "principal": principal}
    return {"accion": "guardar", "rama": principal, "principal": principal}


def commit(git, args):
    actual = git.rama()
    # Una ruta que no está y no cambió: la escribió la skill y otra sesión la apartó o la guardó (N5, Q160).
    faltan = [r for r in args.rutas if not os.path.lexists(os.path.join(git.repo, r))
              and git.correr("diff", "--quiet", "HEAD", "--", r).returncode == 0]
    if faltan:
        raise Parada("ruta-que-falta", "Estos archivos de la skill no están en la copia ni cambiaron: "
                     + ", ".join(faltan), actual, rutas=faltan)
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
    # Sin -h de argparse: la ayuda es el contrato, y un -h que `pide_ayuda` no acepta es uso incorrecto.
    parser = argparse.ArgumentParser(description="Decide en qué rama guarda una skill del flujo.", add_help=False)
    sub = parser.add_subparsers(dest="orden", required=True)
    for orden in ("revisar", "apartar", "volver", "rechazo"):
        p = sub.add_parser(orden, add_help=False)
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
    p = sub.add_parser("commit", add_help=False)
    mensaje = p.add_mutually_exclusive_group(required=True)
    mensaje.add_argument("-m", dest="mensaje", action="append", help="un párrafo del mensaje")
    mensaje.add_argument("-F", dest="archivo", help="el archivo con el mensaje, UTF-8 con o sin BOM")
    p.add_argument("--repo", default=".")
    p.add_argument("rutas", nargs="+", help="después de --: las rutas de la skill que agregaste con git add")
    if argv[:1] == ["commit"] and "--" not in argv:
        parser.error("commit lleva las rutas después de --")
    args = parser.parse_args(argv)
    if args.orden == "commit":
        if args.archivo is not None:
            try:
                with open(args.archivo, encoding="utf-8-sig") as archivo:
                    texto = archivo.read().replace("\r\n", "\n").strip()
            except OSError as error:
                parser.error(f"no se puede leer el mensaje de -F {args.archivo!r}: {error}")
            except UnicodeDecodeError:
                # Q167: lo que escriben > y Out-File (UTF-16) o Set-Content sin -Encoding (ANSI) en PowerShell 5.1.
                parser.error(f"el mensaje de -F {args.archivo!r} no es UTF-8: escríbelo con la herramienta de archivos "
                             "de la sesión, no con > ni Out-File de PowerShell, que escriben UTF-16, ni con Set-Content "
                             "sin -Encoding UTF8")
            if "\0" in texto:
                # git no acepta un argumento con un byte nulo: UTF-16 sin BOM, o un archivo que no es texto (Q167).
                parser.error(f"el mensaje de -F {args.archivo!r} tiene bytes nulos, que git no acepta: escríbelo con la "
                             "herramienta de archivos de la sesión, en UTF-8")
            if not texto:
                parser.error(f"el mensaje de -F {args.archivo!r} está vacío")
            args.mensaje = [texto]
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


OPCIONES = {"commit": ("m", "F", "repo"), "rechazo": ("tipo", "epica", "mockup", "repo"),
            "apartar": ("tipo", "epica", "mockup", "epicas", "rama", "repo"),
            "volver": ("tipo", "epica", "mockup", "epicas", "rama-nueva", "repo"),
            "revisar": ("tipo", "epica", "mockup", "epicas", "repo")}


def pide_ayuda(argv):
    """-h o --help como los lee `flujo rama`: primero, o después de una orden conocida y antes de `--`, con cada opción
    anterior válida y con su valor. Si antes aparece algo que `flujo rama` rechaza, no es ayuda: argparse lo rechaza
    con 2."""
    if argv[:1] in (["-h"], ["--help"]):
        return True
    if not argv or argv[0] not in ORDENES or (argv[0] == "commit" and "--" not in argv):
        return False
    i = 1
    while i < len(argv) and argv[i] != "--":
        token = argv[i]
        if token in ("-h", "--help"):
            return True
        if token.startswith("--"):
            nombre, igual, _ = token[2:].partition("=")
        elif token[:2] in ("-m", "-F") and argv[0] == "commit":
            nombre, igual = token[1], "=" if len(token) > 2 else ""
        else:
            return False
        if nombre not in OPCIONES[argv[0]]:
            return False
        if not igual:
            if i + 1 >= len(argv) or (argv[i + 1].startswith("-") and argv[i + 1] != "-"):
                return False
            i += 1
        i += 1
    return False


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if pide_ayuda(argv):
        # El mismo contrato que imprime `flujo rama -h`, no el resumen de argparse.
        sys.stdout.write(__doc__)
        return 0
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
