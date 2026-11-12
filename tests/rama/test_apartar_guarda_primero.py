"""Q170 a Q172: `apartar` mira los choques en todos los caminos, guarda antes de tocar la carpeta y la cambia una sola
vez, al final.

Los choques se calculan también cuando la copia no cambia de rama pero `apartar` iguala la principal actual al
servidor (H1 y H2 de la revisión 2). El apartado se arma con un índice temporal, `write-tree`, `commit-tree` y
`update-ref`, sin tocar la carpeta, el índice ni HEAD y sin los hooks de commit (Q171, Q174); después HEAD pasa a
`apartado/<rama>` con su árbol en el índice, sin tocar la carpeta, y corre el `git switch` de siempre (Q172). No hay
vuelta atrás: si un paso falla, `apartar` para con el motivo, la carpeta sigue como estaba y `apartado` lista las
ramas donde quedó el trabajo, que existen; si falla el `switch`, la copia queda en `apartado/<rama>` sin cambios sin
guardar, y el reintento solo vuelve a cambiar de rama, sin crear `-2`.

Para hacer fallar cada paso, el PATH del ejecutable lleva primero un `git` que falla la vez número N que la orden
contiene un patrón y que corre el git real en las demás; un sh, así que esas pruebas no corren en Windows. Las de los
hooks y de `index.lock` corren en todos lados.
Uso: python3 -m unittest discover -s tests/rama -p 'test_apartar_guarda_primero.py' -v
"""
import os
import shutil
import unittest

from repos import ENTORNO, Repositorio, git

EPICA = ("--tipo", "diseno", "--epica", "alertas")
SPEC = ("--tipo", "spec", "--epica", "alertas")
MOCKUP = ("--tipo", "diseno", "--mockup", "panel", "--epicas", "alertas,riego")

GIT_QUE_FALLA = """#!/bin/sh
# git que falla la vez número $FALLA_VEZ que la orden contiene $FALLA_PATRON, y deja $FALLA_MARCA al fallar.
case " $* " in
  *" $FALLA_PATRON "*)
    echo x >> "$FALLA_CUENTA"
    if [ "$(wc -l < "$FALLA_CUENTA")" -eq "$FALLA_VEZ" ]; then
      : > "$FALLA_MARCA"
      echo "falla inyectada en git $*" >&2
      exit 1
    fi ;;
esac
exec '{git}' "$@"
"""


class Base(Repositorio):
    def apartar(self, *orden, entorno=None):
        return self.correr("apartar", *(orden or EPICA), entorno=entorno)

    def revisar(self, *orden):
        return self.correr("revisar", *(orden or EPICA))

    def parada(self, salida, motivo):
        self.assertEqual((salida["accion"], salida.get("motivo")), ("parar", motivo), salida)
        self.assertTrue(salida["detalle"])
        return salida

    def igual_al_servidor(self, rama="main"):
        local, remota = (git("rev-parse", r, cwd=self.copia).stdout for r in (rama, f"origin/{rama}"))
        return local == remota

    def al_servidor(self, ruta, texto, forzar=False):
        self.escribir(self.otra, ruta, texto)
        git("add", *(("-f",) if forzar else ()), ruta, cwd=self.otra)
        git("commit", "-q", "-m", f"agrega {ruta}", cwd=self.otra)
        git("push", "-q", "origin", "HEAD:main", cwd=self.otra)

    def commit_local(self):
        self.escribir(self.copia, "specs/alertas/spec.md", "# Spec local\n")
        git("commit", "-q", "-am", "commit sin push", cwd=self.copia)

    def foto(self):
        """La copia como la ve la persona. El índice va primero, antes de que otra orden de git lo refresque."""
        indice = (self.copia / ".git" / "index").read_bytes()
        carpeta = {}
        for raiz, carpetas, archivos in os.walk(self.copia):
            if ".git" in carpetas and os.path.samefile(raiz, self.copia):
                carpetas.remove(".git")
            for archivo in archivos:
                ruta = os.path.join(raiz, archivo)
                with open(ruta, "rb") as f:
                    carpeta[os.path.relpath(ruta, self.copia)] = f.read()
        return {
            "indice": indice,
            "rama": self.rama_actual(),
            "HEAD": git("rev-parse", "HEAD", cwd=self.copia).stdout,
            "ramas": git("for-each-ref", "--format=%(refname) %(objectname)", "refs/heads", cwd=self.copia).stdout,
            "upstream": git("config", "--get-regexp", r"^branch\.", cwd=self.copia, check=False).stdout,
            "carpeta": carpeta,
        }


class ChoquesAlIgualarLaPrincipal(Base):
    """H1 y H2: en la principal con commits que el servidor no tiene, `apartar` la iguala al servidor sin cambiar de
    rama, y ese paso también trae los archivos del servidor."""

    def test_h1_un_sin_seguimiento_igual_al_del_servidor(self):
        self.commit_local()
        self.al_servidor("doc/nuevo.md", "# Nuevo\n")
        self.escribir(self.copia, "doc/nuevo.md", "# Nuevo\n")
        salida = self.parada(self.revisar(), "principal-adelantada")
        self.assertEqual(salida["archivos"], ["?? doc/nuevo.md"])
        salida = self.apartar()
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"], salida["desde"]),
                         ("guardar", "main", ["apartado/main"], "main"), salida)
        self.assertTrue(self.igual_al_servidor())
        self.assertEqual(self.status(), "")
        self.assertIn("commit sin push", git("log", "--format=%s", "apartado/main", cwd=self.copia).stdout)
        self.assertEqual(self.contenido("apartado/main", "doc/nuevo.md"), "# Nuevo\n")
        self.assertEqual(self.apartar()["apartado"], [])
        self.assertEqual(self.ramas_locales("apartado/*"), ["apartado/main"])

    def test_h1_con_un_cambio_sin_guardar(self):
        self.commit_local()
        self.al_servidor("doc/nuevo.md", "# Nuevo\n")
        self.escribir(self.copia, "doc/nuevo.md", "# Nuevo\n")
        self.escribir(self.copia, "notas.txt", "cambio local\n")
        self.assertEqual(sorted(self.parada(self.revisar(), "principal-adelantada")["archivos"]),
                         [" M notas.txt", "?? doc/nuevo.md"])
        salida = self.apartar()
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"]), ("guardar", "main", ["apartado/main"]),
                         salida)
        self.assertEqual((self.status(), self.contenido("apartado/main", "notas.txt")), ("", "cambio local\n"))
        self.assertTrue(self.igual_al_servidor())

    def test_h2_un_ignorado_de_otro_contenido_se_aparta_antes_de_igualar(self):
        (self.copia / ".git" / "info").mkdir(exist_ok=True)
        (self.copia / ".git" / "info" / "exclude").write_text("doc/\n", encoding="utf-8")
        self.commit_local()
        self.al_servidor("doc/nuevo.md", "# Nuevo\n")
        self.escribir(self.copia, "doc/nuevo.md", "# Mio\n")
        self.assertEqual(self.parada(self.revisar(), "principal-adelantada")["archivos"], ["!! doc/nuevo.md"])
        salida = self.apartar()
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"]), ("guardar", "main", ["apartado/main"]),
                         salida)
        self.assertEqual(self.contenido("apartado/main", "doc/nuevo.md"), "# Mio\n")
        self.assertEqual((self.copia / "doc/nuevo.md").read_text(encoding="utf-8"), "# Nuevo\n")
        self.assertTrue(self.igual_al_servidor())


class ChoquesDeArchivoContraCarpeta(Base):
    """H1 de la revisión 4: donde la principal trae un archivo, la copia tiene una carpeta con archivos sin seguimiento,
    o al revés. Con un ignorado, `git switch` lo borraba sin avisar y no quedaba en ningún commit; sin ignorar, el
    `switch` se negaba en cada reintento. Los dos entran al apartado, `!!` el ignorado y `??` el otro."""

    def caso(self, del_servidor, excluir, local, linea):
        self.al_servidor(del_servidor, "del servidor\n")
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        if excluir:
            (self.copia / ".git" / "info").mkdir(exist_ok=True)
            (self.copia / ".git" / "info" / "exclude").write_text(excluir + "\n", encoding="utf-8")
        self.escribir(self.copia, local, "MI TRABAJO\n")
        salida = self.parada(self.revisar(), "otra-rama")
        self.assertEqual(salida.get("archivos"), [linea], salida)
        salida = self.apartar()
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"]),
                         ("guardar", "main", ["apartado/experimento"]), salida)
        self.assertEqual(self.contenido("apartado/experimento", local), "MI TRABAJO\n")
        self.assertEqual((self.copia / del_servidor).read_text(encoding="utf-8"), "del servidor\n")
        self.assertEqual(self.ramas_locales("apartado/*"), ["apartado/experimento"])

    def test_una_carpeta_ignorada_donde_la_principal_trae_un_archivo(self):
        self.caso("cache", "cache/", "cache/mio.txt", "!! cache/mio.txt")

    def test_un_archivo_ignorado_donde_la_principal_trae_una_carpeta(self):
        self.caso("build/x.txt", "build", "build", "!! build")

    def test_un_archivo_sin_seguimiento_donde_la_principal_trae_una_carpeta(self):
        self.caso("build/x.txt", None, "build", "?? build")

    def test_una_carpeta_sin_seguimiento_donde_la_principal_trae_un_archivo(self):
        self.caso("cache", None, "cache/mio.txt", "?? cache/mio.txt")

    def test_una_carpeta_ignorada_dentro_de_otra(self):
        self.caso("a/b", "a/", "a/b/c/mio.txt", "!! a/b/c/mio.txt")

    def test_al_igualar_la_principal_adelantada(self):
        self.commit_local()
        self.al_servidor("cache", "del servidor\n")
        (self.copia / ".git" / "info").mkdir(exist_ok=True)
        (self.copia / ".git" / "info" / "exclude").write_text("cache/\n", encoding="utf-8")
        self.escribir(self.copia, "cache/mio.txt", "MI TRABAJO\n")
        self.assertEqual(self.parada(self.revisar(), "principal-adelantada")["archivos"], ["!! cache/mio.txt"])
        salida = self.apartar()
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"]), ("guardar", "main", ["apartado/main"]),
                         salida)
        self.assertEqual(self.contenido("apartado/main", "cache/mio.txt"), "MI TRABAJO\n")
        self.assertEqual((self.copia / "cache").read_text(encoding="utf-8"), "del servidor\n")
        self.assertTrue(self.igual_al_servidor())


class IgnoradoIgualAlDelDestino(Base):
    """Q175: con `--no-overwrite-ignore`, git se niega también ante un ignorado igual al del destino, así que entra al
    apartado como `!!`, como un sin seguimiento igual (Q169), y el reintento no queda dando vueltas."""

    def ignorar(self, ruta):
        (self.copia / ".git" / "info").mkdir(exist_ok=True)
        (self.copia / ".git" / "info" / "exclude").write_text(ruta + "\n", encoding="utf-8")

    def test_desde_otra_rama(self):
        self.al_servidor("cache.txt", "del servidor\n")
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.ignorar("cache.txt")
        self.escribir(self.copia, "cache.txt", "del servidor\n")
        self.assertEqual(self.parada(self.revisar(), "otra-rama").get("archivos"), ["!! cache.txt"])
        salida = self.apartar()
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"]),
                         ("guardar", "main", ["apartado/experimento"]), salida)
        self.assertEqual(self.contenido("apartado/experimento", "cache.txt"), "del servidor\n")
        self.assertEqual((self.copia / "cache.txt").read_text(encoding="utf-8"), "del servidor\n")
        salida = self.apartar()
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"]), ("guardar", "main", []), salida)
        self.assertEqual(self.ramas_locales("apartado/*"), ["apartado/experimento"])

    def test_al_igualar_la_principal_adelantada(self):
        """El camino de `reset --keep` no tiene `--no-overwrite-ignore` y depende de la predicción: el ignorado igual
        entra al apartado, la copia pasa a `apartado/main` y llega a la principal con el `switch`."""
        self.commit_local()
        self.al_servidor("cache.txt", "del servidor\n")
        self.ignorar("cache.txt")
        self.escribir(self.copia, "cache.txt", "del servidor\n")
        self.assertEqual(self.parada(self.revisar(), "principal-adelantada")["archivos"], ["!! cache.txt"])
        salida = self.apartar()
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"]), ("guardar", "main", ["apartado/main"]),
                         salida)
        self.assertEqual(self.contenido("apartado/main", "cache.txt"), "del servidor\n")
        self.assertTrue(self.igual_al_servidor())
        self.assertEqual(self.status(), "")


GIT_QUE_NO_VE = """#!/bin/sh
# git que, con `ls-tree -r`, no devuelve nada: la predicción de choques no ve el destino.
case " $* " in
  *" ls-tree -r "*) exit 0 ;;
esac
exec '{git}' "$@"
"""


@unittest.skipIf(os.name == "nt", "el git que no ve es un sh")
class RedDeSeguridad(Base):
    """Q175: si la predicción de choques no ve un ignorado en el camino, el `git switch --no-overwrite-ignore` final
    se niega en lugar de borrarlo, y `apartar` para con `error-de-git` con el ignorado en la carpeta."""

    def test_un_choque_que_la_prediccion_no_vio(self):
        self.al_servidor("build/x.txt", "del servidor\n")
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        (self.copia / ".git" / "info").mkdir(exist_ok=True)
        (self.copia / ".git" / "info" / "exclude").write_text("build\n", encoding="utf-8")
        self.escribir(self.copia, "build", "MI TRABAJO\n")
        carpeta = self.tmp / "git-que-no-ve"
        carpeta.mkdir()
        (carpeta / "git").write_text(GIT_QUE_NO_VE.format(git=shutil.which("git", path=ENTORNO.get("PATH"))),
                                     encoding="utf-8")
        (carpeta / "git").chmod(0o755)
        salida = self.parada(self.apartar(entorno={"PATH": str(carpeta) + os.pathsep + ENTORNO.get("PATH", "")}),
                             "error-de-git")
        self.assertIn("build", salida["detalle"])
        self.assertEqual(salida["rama"], "experimento", salida)
        self.assertEqual((self.copia / "build").read_text(encoding="utf-8"), "MI TRABAJO\n")
        salida = self.apartar()
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"]),
                         ("guardar", "main", ["apartado/experimento"]), salida)
        self.assertEqual(self.contenido("apartado/experimento", "build"), "MI TRABAJO\n")


class GitQueFalla(Base):
    def git_que_falla(self, patron, vez):
        carpeta = self.tmp / "git-que-falla"
        carpeta.mkdir()
        real = shutil.which("git", path=ENTORNO.get("PATH"))
        (carpeta / "git").write_text(GIT_QUE_FALLA.format(git=real), encoding="utf-8")
        (carpeta / "git").chmod(0o755)
        self.marca = self.tmp / "fallo"
        return {"PATH": str(carpeta) + os.pathsep + ENTORNO.get("PATH", ""), "FALLA_PATRON": patron,
                "FALLA_VEZ": str(vez), "FALLA_CUENTA": str(self.tmp / "cuenta"), "FALLA_MARCA": str(self.marca)}

    def apartar_con_falla(self, orden, patron, vez=1):
        salida = self.parada(self.apartar(*orden, entorno=self.git_que_falla(patron, vez)), "error-de-git")
        self.assertTrue(self.marca.exists(), f"ninguna orden de git tuvo {patron!r} {vez} veces")
        self.assertIn("falla inyectada", salida["detalle"])
        return salida

    def desde_otra_rama_con_todo(self):
        """En `experimento`, con algo preparado y otro cambio encima, un cambio sin preparar, un archivo nuevo de las
        rutas, un sin seguimiento igual al de la principal, otro distinto y un ignorado de otro contenido."""
        self.al_servidor(".gitignore", ".claude/\n")
        self.al_servidor(".claude/pm-conventions.md", "del servidor\n", forzar=True)
        self.al_servidor("doc/nuevo.md", "# Nuevo\n")
        self.al_servidor("informe.txt", "del servidor\n")
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.escribir(self.copia, ".gitignore", ".claude/\n")
        self.escribir(self.copia, ".claude/pm-conventions.md", "local\n")
        self.escribir(self.copia, "design/vistas/alertas/a.html", "<p>preparado</p>\n")
        git("add", "design/", cwd=self.copia)
        self.escribir(self.copia, "design/vistas/alertas/a.html", "<p>encima</p>\n")
        self.escribir(self.copia, "notas.txt", "cambio\n")
        self.escribir(self.copia, "design/nueva.html", "<p>nueva</p>\n")
        self.escribir(self.copia, "doc/nuevo.md", "# Nuevo\n")
        self.escribir(self.copia, "informe.txt", "local\n")
        return "experimento"

    def todo_apartado(self, rama="apartado/experimento"):
        """Lo de `desde_otra_rama_con_todo`, en el apartado: lo preparado en el primer commit y lo demás encima."""
        self.assertEqual(self.contenido(f"{rama}~1", "design/vistas/alertas/a.html"), "<p>preparado</p>\n")
        for ruta, texto in (("design/vistas/alertas/a.html", "<p>encima</p>\n"), ("notas.txt", "cambio\n"),
                            ("design/nueva.html", "<p>nueva</p>\n"), ("doc/nuevo.md", "# Nuevo\n"),
                            ("informe.txt", "local\n"), (".claude/pm-conventions.md", "local\n")):
            self.assertEqual(self.contenido(rama, ruta), texto, ruta)


@unittest.skipIf(os.name == "nt", "el git que falla es un sh")
class FallaEnCadaPaso(GitQueFalla):
    """Q171 y Q172: un paso que falla deja la carpeta como estaba, y `apartado` lista las ramas que existen (H2 de la
    revisión 3 desaparece: no hay ramas que se borren a medias). Antes de pasar la copia al apartado, la copia sigue
    en su rama con su índice; después, en `apartado/<rama>` sin cambios sin guardar. El reintento sin la falla
    termina y no crea `-2`."""

    def assertSeguro(self, preparar, orden, patron, vez=1, apartado=None, corridas=1, igualada=False):
        desde = preparar()
        antes = self.foto()
        salida = self.apartar_con_falla(orden, patron, vez)
        despues = self.foto()
        if igualada:
            # El `reset --keep` que iguala la rama al servidor es el último paso que toca la carpeta, y ya corrió.
            self.assertEqual(git("status", "--porcelain", cwd=self.copia).stdout, "")
        else:
            self.assertEqual(despues["carpeta"], antes["carpeta"], "la carpeta cambió")
        self.assertEqual(salida["apartado"], self.ramas_locales("apartado/*"))
        self.assertEqual((salida["desde"], salida.get("rama")), (desde, despues["rama"]), salida)
        if despues["rama"] == desde:
            if not igualada:
                self.assertEqual((despues["indice"], despues["HEAD"]), (antes["indice"], antes["HEAD"]))
        else:
            self.assertEqual(despues["rama"], salida["apartado"][0])
            self.assertEqual(git("status", "--porcelain", "--untracked-files=no", cwd=self.copia).stdout, "")
        # El reintento reusa el apartado que quedó, o crea el que faltó, pero nunca `-2`.
        quedaron = self.ramas_locales("apartado/*")
        for _ in range(corridas - 1):
            self.apartar(*orden)
        self.assertNotEqual(self.apartar(*orden)["accion"], "parar")
        self.assertEqual(self.ramas_locales("apartado/*"), quedaron if quedaron or not apartado else [apartado])

    def test_desde_otra_rama(self):
        for patron, vez in (("write-tree", 1), ("commit-tree", 1), ("add -u", 1), ("add --", 1), ("add -f", 1),
                            ("write-tree", 2), ("commit-tree", 2), ("update-ref", 1), ("symbolic-ref HEAD", 1),
                            ("switch", 1)):
            with self.subTest(patron=patron, vez=vez):
                self.setUp()
                self.assertSeguro(self.desde_otra_rama_con_todo, EPICA, patron, vez, "apartado/experimento")
                self.todo_apartado()
                self.assertEqual(self.rama_actual(), "main")

    def principal_adelantada(self, con_cambio):
        def preparar():
            self.commit_local()
            self.al_servidor("doc/nuevo.md", "# Nuevo\n")
            if con_cambio:
                self.escribir(self.copia, "notas.txt", "cambio local\n")
            return "main"
        return preparar

    def test_en_la_principal_adelantada_sin_nada_que_apartar(self):
        for patron in ("branch apartado/main", "reset"):
            with self.subTest(patron=patron):
                self.setUp()
                self.assertSeguro(self.principal_adelantada(False), EPICA, patron, apartado="apartado/main")
                self.assertIn("commit sin push", git("log", "--format=%s", "apartado/main", cwd=self.copia).stdout)
                self.assertTrue(self.igual_al_servidor())

    def test_en_la_principal_adelantada_con_un_cambio(self):
        for patron in ("add -u", "commit-tree", "update-ref", "symbolic-ref HEAD", "-f", "switch"):
            with self.subTest(patron=patron):
                self.setUp()
                self.assertSeguro(self.principal_adelantada(True), EPICA, patron, apartado="apartado/main")
                self.assertEqual(self.contenido("apartado/main", "notas.txt"), "cambio local\n")
                self.assertIn("commit sin push", git("log", "--format=%s", "apartado/main", cwd=self.copia).stdout)
                self.assertTrue(self.igual_al_servidor())

    def rama_del_flujo_sin_upstream(self, con_cambio):
        def preparar():
            git("switch", "-q", "-c", "spec/alertas", cwd=self.copia)
            git("push", "-q", "origin", "spec/alertas", cwd=self.copia)
            self.commit_local()
            if con_cambio:
                self.escribir(self.copia, "notas.txt", "cambio local\n")
            return "spec/alertas"
        return preparar

    def test_en_una_rama_del_flujo_sin_upstream(self):
        for patron, igualada in (("branch apartado/spec-alertas", False), ("reset", False),
                                 ("--set-upstream-to=origin/spec/alertas", True)):
            with self.subTest(patron=patron):
                self.setUp()
                self.assertSeguro(self.rama_del_flujo_sin_upstream(False), SPEC, patron,
                                  apartado="apartado/spec-alertas", igualada=igualada)
                self.assertTrue(self.igual_al_servidor("spec/alertas"))
        # Con el `branch -f` o el upstream fallados, la copia queda en el apartado y la rama del flujo sin seguir al
        # servidor. El reintento lee el destino del apartado (Q173) y hace lo que faltaba: iguala la rama, le pone el
        # upstream y vuelve a ella, en una sola corrida, reusando el apartado.
        for patron in ("update-ref", "-f", "--set-upstream-to=origin/spec/alertas", "switch"):
            with self.subTest(patron=patron, con_cambio=True):
                self.setUp()
                self.assertSeguro(self.rama_del_flujo_sin_upstream(True), SPEC, patron,
                                  apartado="apartado/spec-alertas")
                self.assertEqual(self.contenido("apartado/spec-alertas", "notas.txt"), "cambio local\n")
                self.assertTrue(self.igual_al_servidor("spec/alertas"))
                self.assertEqual(self.rama_actual(), "spec/alertas")

    def hacia_una_rama_del_servidor(self):
        self.en_el_servidor("spec/alertas")
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.escribir(self.copia, "notas.txt", "cambio\n")
        return "experimento"

    def test_hacia_una_rama_del_flujo_que_no_esta_en_local(self):
        for patron in ("--track", "switch"):
            with self.subTest(patron=patron):
                self.setUp()
                self.assertSeguro(self.hacia_una_rama_del_servidor, SPEC, patron, apartado="apartado/experimento")
                self.assertEqual(self.contenido("apartado/experimento", "notas.txt"), "cambio\n")
                self.assertEqual(self.rama_actual(), "spec/alertas")


@unittest.skipIf(os.name == "nt", "el git que falla es un sh")
class QuedaEnElApartado(GitQueFalla):
    """Q172: después de un `switch` que falla, la copia está en `apartado/<rama>`. `revisar` lo dice como otra rama,
    sin `archivos`, y `apartar` no guarda nada nuevo: solo vuelve a cambiar a la rama del flujo."""

    def test_revisar_y_el_reintento(self):
        self.desde_otra_rama_con_todo()
        self.apartar_con_falla(EPICA, "switch")
        salida = self.parada(self.revisar(), "otra-rama")
        self.assertEqual(salida["rama"], "apartado/experimento")
        self.assertNotIn("archivos", salida)
        salida = self.apartar()
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"], salida["desde"]),
                         ("guardar", "main", [], "apartado/experimento"), salida)
        self.assertEqual(self.ramas_locales("apartado/*"), ["apartado/experimento"])
        self.todo_apartado()


@unittest.skipIf(os.name == "nt", "el git que falla es un sh")
class ReintentoAlMismoDestino(GitQueFalla):
    """Q173 y H6 de la revisión 4: el commit del apartado lleva `Destino: <rama>`, la rama a la que iba `apartar`. El
    reintento desde `apartado/<rama>`, sin nada nuevo que guardar, va ahí sin volver a calcularla: termina donde habría
    terminado la primera corrida sin la falla, aunque el servidor tenga otra rama viva de este trabajo."""

    def mismo_final(self, preparar, orden, patron="switch"):
        finales = []
        for falla in (False, True):
            with self.subTest(falla=falla):
                self.setUp()
                preparar()
                if falla:
                    salida = self.apartar_con_falla(orden, patron)
                    self.assertTrue(salida["rama"].startswith("apartado/"), salida)
                    mensaje = git("log", "-1", "--format=%B", salida["rama"], cwd=self.copia).stdout
                    self.assertEqual(mensaje.strip().splitlines()[-1], f"Destino: {finales[0][1]}")
                salida = self.apartar(*orden)
                self.assertNotEqual(salida["accion"], "parar", salida)
                finales.append((salida["accion"], salida["rama"], self.rama_actual()))
        self.assertEqual(finales[1], finales[0])
        return finales[0]

    def test_una_rama_viva_y_la_copia_en_la_principal(self):
        def preparar():
            self.en_el_servidor("spec/alertas")
            self.commit_local()
            self.escribir(self.copia, "notas.txt", "MI TRABAJO\n")
        self.assertEqual(self.mismo_final(preparar, SPEC), ("guardar", "main", "main"))
        self.assertEqual(self.contenido("apartado/main", "notas.txt"), "MI TRABAJO\n")

    def test_varias_ramas_vivas_y_la_copia_en_una(self):
        def preparar():
            self.trabajar_en("spec/alertas")
            self.en_el_servidor("spec/alertas-2")
            self.escribir(self.copia, "specs/alertas/spec.md", "# MI TRABAJO\n")
        self.assertEqual(self.mismo_final(preparar, SPEC), ("guardar", "spec/alertas", "spec/alertas"))

    def test_volver_con_otra_rama_viva(self):
        def preparar():
            self.trabajar_en("spec/alertas")
            self.en_el_servidor("spec/alertas-2")
            git("push", "-q", "origin", "--delete", "spec/alertas", cwd=self.otra)
            self.escribir(self.copia, "specs/alertas/spec.md", "# MI TRABAJO\n")
        self.assertEqual(self.mismo_final(preparar, SPEC), ("volver", "spec/alertas", "spec/alertas"))

    def test_q179_ofrecer_desde_la_rama_de_una_epica(self):
        """Q179: con --mockup, la rama viva de una de las épicas da `ofrecer`, y el reintento vuelve a ella aunque no
        sea `diseno/<mockup>`."""
        def preparar():
            self.trabajar_en("diseno/alertas")
            self.escribir(self.copia, "design/vistas/alertas/a.html", "<p>MI TRABAJO</p>\n")
        self.assertEqual(self.mismo_final(preparar, MOCKUP), ("ofrecer", "diseno/alertas", "diseno/alertas"))

    def test_q179_guardar_en_la_rama_viva_de_otro_tipo(self):
        """Q179: con --tipo diseno --epica alertas, una `spec/alertas` viva da `guardar`, y el reintento vuelve ahí."""
        def preparar():
            self.trabajar_en("spec/alertas")
            self.escribir(self.copia, "specs/alertas/spec.md", "# MI TRABAJO\n")
        self.assertEqual(self.mismo_final(preparar, EPICA), ("guardar", "spec/alertas", "spec/alertas"))

    def test_una_rama_del_flujo_sin_upstream(self):
        def preparar():
            git("switch", "-q", "-c", "spec/alertas", cwd=self.copia)
            git("push", "-q", "origin", "spec/alertas", cwd=self.copia)
            self.commit_local()
            self.escribir(self.copia, "notas.txt", "cambio local\n")
        for patron in ("switch", "-f", "--set-upstream-to=origin/spec/alertas"):
            with self.subTest(patron=patron):
                self.assertEqual(self.mismo_final(preparar, SPEC, patron), ("guardar", "spec/alertas", "spec/alertas"))
                self.assertTrue(self.igual_al_servidor("spec/alertas"))
                self.assertEqual(self.ramas_locales("apartado/*"), ["apartado/spec-alertas"])

    def test_con_algo_nuevo_en_el_apartado_no_es_un_reintento(self):
        """Quien volvió a un apartado y siguió editando ahí aparta lo nuevo en otro apartado, y el destino se calcula
        de nuevo; sin nada nuevo, el destino es el del apartado. El apartado sale de la principal, así que su
        `Destino: main` vale aunque después aparezca `spec/alertas` (Q181)."""
        self.escribir(self.copia, "specs/alertas/spec.md", "# MI TRABAJO\n")
        self.assertEqual(self.apartar(*SPEC)["apartado"], ["apartado/main"])
        self.en_el_servidor("spec/alertas")
        git("switch", "-q", "apartado/main", cwd=self.copia)
        salida = self.apartar(*SPEC)
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"]), ("guardar", "main", []), salida)
        git("switch", "-q", "apartado/main", cwd=self.copia)
        self.escribir(self.copia, "notas.txt", "SEGUI TRABAJANDO\n")
        salida = self.apartar(*SPEC)
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"]),
                         ("guardar", "spec/alertas", ["apartado/apartado-main"]), salida)
        self.assertEqual(self.contenido("apartado/apartado-main", "notas.txt"), "SEGUI TRABAJANDO\n")


@unittest.skipIf(os.name == "nt", "el git que falla es un sh")
class DestinoDelApartado(GitQueFalla):
    """Q178 y Q179, que precisan Q173: el reintento va al `Destino:` solo si el último commit de `apartado/*` es uno de
    los dos que escribe `apartar` y el destino es una rama a la que `revisar` podría mandar esta corrida; si no, lo
    calcula otra vez. `revisar` arma `archivos` contra ese mismo destino (H3 y H4 de la revisión 5)."""

    def apartado_hacia(self, viva=None):
        """La primera corrida, `--epica alertas` desde `experimento`, falla en el `switch` y deja la copia en
        `apartado/experimento` con `Destino: <viva>`, o `Destino: main` si no hay una rama viva de alertas."""
        if viva:
            self.en_el_servidor(viva)
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.escribir(self.copia, "notas.txt", "MI TRABAJO\n")
        salida = self.apartar_con_falla(SPEC, "switch")
        self.assertEqual(salida["rama"], "apartado/experimento", salida)
        self.assertEqual(git("log", "-1", "--format=%B", "HEAD", cwd=self.copia).stdout.strip().splitlines()[-1],
                         f"Destino: {viva or 'main'}")

    def test_r5_h3_el_destino_de_otra_epica_se_calcula_otra_vez(self):
        self.apartado_hacia("spec/alertas")
        self.en_el_servidor("spec/pagos")
        pagos = ("--tipo", "spec", "--epica", "pagos")
        salida = self.parada(self.revisar(*pagos), "otra-rama")
        self.assertNotIn("archivos", salida)
        salida = self.apartar(*pagos)
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"]), ("guardar", "spec/pagos", []), salida)
        self.assertEqual(self.rama_actual(), "spec/pagos")

    def test_q181_otra_epica_con_el_destino_en_la_principal_va_a_su_rama_viva(self):
        """H3 de la revisión 6: la principal vale solo si esta corrida también iría ahí. Con `spec/pagos` viva, la
        misma orden sin la falla previa termina en `spec/pagos`, y el reintento también."""
        self.apartado_hacia()
        self.en_el_servidor("spec/pagos")
        salida = self.apartar("--tipo", "spec", "--epica", "pagos")
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"]), ("guardar", "spec/pagos", []), salida)
        self.assertEqual(self.rama_actual(), "spec/pagos")

    def test_q181_el_destino_en_la_principal_vale_sin_rama_viva(self):
        self.apartado_hacia()
        salida = self.apartar("--tipo", "spec", "--epica", "pagos")
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"]), ("guardar", "main", []), salida)

    def test_r5_h3_un_commit_de_la_persona_con_una_linea_destino(self):
        for destino in ("personal", "main"):
            with self.subTest(destino=destino):
                self.setUp()
                self.en_el_servidor("spec/alertas")
                git("switch", "-q", "-c", "personal", cwd=self.copia)
                git("switch", "-q", "-c", "apartado/mio", cwd=self.copia)
                self.escribir(self.copia, "notas.txt", "MIO\n")
                git("commit", "-q", "-am", f"mi nota\n\nDestino: {destino}", cwd=self.copia)
                salida = self.apartar(*SPEC)
                self.assertEqual((salida["accion"], salida["rama"], salida["apartado"]),
                                 ("guardar", "spec/alertas", []), salida)

    def test_un_commit_de_apartar_en_un_apartado_de_otro_nombre(self):
        """La forma incluye la rama del asunto: un commit de `apartar` copiado a otro `apartado/*` no es un reintento."""
        self.apartado_hacia()
        git("switch", "-q", "-c", "apartado/otro", cwd=self.copia)
        self.en_el_servidor("spec/alertas")
        salida = self.apartar(*SPEC)
        self.assertEqual((salida["accion"], salida["rama"]), ("guardar", "spec/alertas"), salida)

    def test_r5_h4_archivos_contra_el_destino_del_apartado(self):
        """El `Destino:` es `main` y después aparece `spec/alertas`: con Q181 la corrida ya no iría a `main`, así que
        `apartar` va a `spec/alertas`, y `revisar` lista `x.txt` si choca con `spec/alertas` y no si choca solo con
        `main`."""
        for choca_con in ("spec/alertas", "main"):
            with self.subTest(choca_con=choca_con):
                self.setUp()
                self.apartado_hacia()
                self.en_el_servidor("spec/alertas")
                if choca_con == "main":
                    self.al_servidor("x.txt", "del servidor\n")
                else:
                    git("switch", "-q", "-c", "alertas", cwd=self.otra)
                    self.escribir(self.otra, "x.txt", "del servidor\n")
                    git("add", "x.txt", cwd=self.otra)
                    git("commit", "-q", "-m", "x", cwd=self.otra)
                    git("push", "-q", "origin", "HEAD:spec/alertas", cwd=self.otra)
                self.escribir(self.copia, "x.txt", "MI x\n")
                revisado = self.parada(self.revisar(*SPEC), "otra-rama")
                salida = self.apartar(*SPEC)
                self.assertEqual((salida["accion"], salida["rama"]), ("guardar", "spec/alertas"), salida)
                if choca_con == "spec/alertas":
                    self.assertEqual(revisado.get("archivos"), ["?? x.txt"])
                    self.assertEqual(salida["apartado"], ["apartado/apartado-experimento"])
                    self.assertEqual(self.contenido("apartado/apartado-experimento", "x.txt"), "MI x\n")
                else:
                    self.assertNotIn("archivos", revisado)
                    self.assertEqual(salida["apartado"], [])
                    self.assertEqual((self.copia / "x.txt").read_text(encoding="utf-8"), "MI x\n")


class SinHooksAlGuardar(Base):
    """Q171 y Q174: al guardar no corren los hooks de commit. H3 de la revisión 3 desaparece: un `pre-commit` que
    reescribe un archivo y falla no corre, y lo apartado es lo que había en la carpeta."""

    def test_un_pre_commit_que_reescribe_y_falla_no_corre(self):
        hooks = self.copia / ".git" / "hooks"
        marca = self.tmp / "corrio"
        for nombre in ("pre-commit", "commit-msg", "post-commit"):
            (hooks / nombre).write_text(f"#!/bin/sh\necho formateado > notas.txt\n: > '{marca.as_posix()}'\nexit 1\n",
                                        encoding="utf-8")
            (hooks / nombre).chmod(0o755)
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.escribir(self.copia, "notas.txt", "MI TRABAJO\n")
        salida = self.apartar()
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"]),
                         ("guardar", "main", ["apartado/experimento"]), salida)
        self.assertFalse(marca.exists(), "corrió un hook al guardar")
        self.assertEqual(self.contenido("apartado/experimento", "notas.txt"), "MI TRABAJO\n")
        self.assertEqual((self.copia / "notas.txt").read_text(encoding="utf-8"), "notas\n")


class HooksQueSiCorren(Base):
    """Q174 y H5 de la revisión 4: `reference-transaction` corre con el `update-ref` del apartado. Si rechaza, `apartar`
    para antes de tocar HEAD, el índice o la carpeta, y no quedan ramas ni índices temporales."""

    def test_un_reference_transaction_que_rechaza_el_apartado(self):
        hook = self.copia / ".git" / "hooks" / "reference-transaction"
        hook.write_text('#!/bin/sh\nwhile read viejo nuevo ref; do\n  case "$1 $ref" in\n    "prepared refs/heads/apartado/"*)'
                        ' echo rt rechaza >&2; exit 1 ;;\n  esac\ndone\nexit 0\n', encoding="utf-8")
        hook.chmod(0o755)
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.escribir(self.copia, "notas.txt", "MI TRABAJO\n")
        antes = self.foto()
        salida = self.parada(self.apartar(), "error-de-git")
        self.assertIn("rt rechaza", salida["detalle"])
        self.assertEqual((salida["apartado"], salida["rama"]), ([], "experimento"), salida)
        despues = self.foto()
        for clave in ("indice", "rama", "HEAD", "ramas", "carpeta"):
            self.assertEqual(despues[clave], antes[clave], clave)
        self.assertEqual([p.name for p in (self.copia / ".git").iterdir() if p.name.startswith("index")], ["index"])


class SwitchQueFallaDespuesDeEscribir(Base):
    """H1 de la revisión 3: un `post-checkout` que sale con 1 hace que `git switch` falle después de cambiar la
    carpeta. No hay vuelta atrás que lo confunda: lo apartado sigue en `apartado/experimento` y el JSON dice dónde
    quedó la copia."""

    def test_post_checkout_que_falla_hacia_una_rama_que_no_estaba_en_local(self):
        self.escribir(self.otra, "notas.txt", "del servidor\n")
        git("switch", "-q", "-c", "spec/alertas", cwd=self.otra)
        git("commit", "-q", "-am", "del servidor", cwd=self.otra)
        git("push", "-q", "origin", "spec/alertas", cwd=self.otra)
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.escribir(self.copia, "notas.txt", "MI TRABAJO\n")
        hook = self.copia / ".git" / "hooks" / "post-checkout"
        hook.write_text('#!/bin/sh\n[ "$(git branch --show-current)" = spec/alertas ] && '
                        '{ echo post-checkout falla >&2; exit 1; }\nexit 0\n', encoding="utf-8")
        hook.chmod(0o755)
        salida = self.parada(self.apartar(*SPEC), "error-de-git")
        self.assertIn("post-checkout falla", salida["detalle"])
        self.assertEqual((salida["rama"], salida["apartado"], salida["desde"]),
                         ("spec/alertas", ["apartado/experimento"], "experimento"), salida)
        self.assertEqual(self.contenido("apartado/experimento", "notas.txt"), "MI TRABAJO\n")
        self.assertEqual(self.ramas_locales("apartado/*"), ["apartado/experimento"])
        self.assertEqual(self.revisar(*SPEC)["accion"], "guardar")


class ApartadoEnOtraCopia(Base):
    """H7 de la revisión 4: `apartar` no reusa un `apartado/<rama>` que otra copia de `git worktree` tiene en uso,
    aunque tenga lo mismo: `symbolic-ref` no lo frena como `git switch`, y las dos copias quedarían en la misma rama."""

    def test_crea_otro_apartado(self):
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        vinculada = self.tmp / "vinculada"
        git("worktree", "add", "-q", "--detach", str(vinculada), "experimento", cwd=self.copia)
        self.escribir(self.copia, "notas.txt", "MI TRABAJO\n")
        self.assertEqual(self.apartar()["apartado"], ["apartado/experimento"])
        git("switch", "-q", "apartado/experimento", cwd=self.copia)
        git("switch", "-q", "experimento", cwd=vinculada)
        self.escribir(vinculada, "notas.txt", "MI TRABAJO\n")
        salida = self.correr("apartar", *EPICA, cwd=vinculada)
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"]),
                         ("guardar", "main", ["apartado/experimento-2"]), salida)
        self.assertEqual(self.rama_actual(), "apartado/experimento")
        self.assertEqual(self.contenido("apartado/experimento-2", "notas.txt"), "MI TRABAJO\n")
        en_uso = [l for l in git("worktree", "list", "--porcelain", cwd=self.copia).stdout.splitlines()
                  if l.startswith("branch ")]
        self.assertEqual(sorted(en_uso), ["branch refs/heads/apartado/experimento", "branch refs/heads/main"])


class IndiceEnUso(Base):
    """Q172: con `index.lock`, otro git está usando el índice. `apartar` para antes de tocar HEAD, el índice o la
    carpeta; lo guardado queda en `apartado/<rama>` y el reintento lo reusa."""

    def test_con_index_lock(self):
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.escribir(self.copia, "notas.txt", "MI TRABAJO\n")
        candado = self.copia / ".git" / "index.lock"
        candado.write_bytes(b"")
        antes = self.foto()
        salida = self.parada(self.apartar(), "error-de-git")
        self.assertIn("index.lock", salida["detalle"])
        despues = self.foto()
        for clave in ("indice", "rama", "HEAD", "carpeta"):
            self.assertEqual(despues[clave], antes[clave], clave)
        self.assertEqual((salida["apartado"], salida["rama"]), (["apartado/experimento"], "experimento"))
        candado.unlink()
        salida = self.apartar()
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"]),
                         ("guardar", "main", ["apartado/experimento"]), salida)
        self.assertEqual(self.ramas_locales("apartado/*"), ["apartado/experimento"])
        self.assertEqual(self.contenido("apartado/experimento", "notas.txt"), "MI TRABAJO\n")


GIT_QUE_TRABA = """#!/bin/sh
# git que, después de la orden que contiene $TRABA_PATRON por $TRABA_VEZ vez, deja `.git` sin poder escribir el
# índice: con `carpeta`, `.git/index` pasa a ser una carpeta y `rename` sobre él falla; con `permisos`, `.git` queda
# sin escritura y crear `index.lock` falla. La orden de git siguiente, la que sea, lo devuelve como estaba.
gitdir='{gitdir}'
if [ -e "$gitdir/traba" ]; then
  if [ -d "$gitdir/index" ]; then rmdir "$gitdir/index"; mv "$gitdir/index.real" "$gitdir/index"; fi
  chmod u+w "$gitdir"
  rm "$gitdir/traba"
  : > '{marca}'
fi
'{git}' "$@"
codigo=$?
case " $* " in
  *" $TRABA_PATRON "*)
    echo x >> '{cuenta}'
    if [ "$(wc -l < '{cuenta}')" -eq "$TRABA_VEZ" ]; then
      : > "$gitdir/traba"
      if [ "$TRABA_MODO" = carpeta ]; then mv "$gitdir/index" "$gitdir/index.real"; mkdir "$gitdir/index"; fi
      if [ "$TRABA_MODO" = permisos ]; then chmod a-w "$gitdir"; fi
    fi ;;
esac
exit $codigo
"""


@unittest.skipIf(os.name == "nt", "el git que traba es un sh")
class IndiceQueNoSeEscribe(Base):
    """H4 de la revisión 4: si no se puede crear `index.lock` o reemplazar el índice con él, `apartar` sale con su JSON,
    como `flujo rama`, sin traceback. No deja su `index.lock`, que el reintento tomaría por otro git, y la copia sigue
    en su rama con su índice: HEAD vuelve a la rama de origen si ya se había movido. Lo guardado queda en
    `apartado/<rama>` y el reintento lo reusa."""

    def apartar_trabado(self, modo, patron, vez):
        carpeta = self.tmp / "git-que-traba"
        carpeta.mkdir()
        real = shutil.which("git", path=ENTORNO.get("PATH"))
        marca = self.tmp / "trabado"
        (carpeta / "git").write_text(GIT_QUE_TRABA.format(git=real, gitdir=(self.copia / ".git").as_posix(),
                                                          marca=marca.as_posix(),
                                                          cuenta=(self.tmp / "cuenta").as_posix()), encoding="utf-8")
        (carpeta / "git").chmod(0o755)
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.escribir(self.copia, "notas.txt", "MI TRABAJO\n")
        antes = self.foto()
        salida = self.parada(self.apartar(entorno={"PATH": str(carpeta) + os.pathsep + ENTORNO.get("PATH", ""),
                                                   "TRABA_MODO": modo, "TRABA_PATRON": patron,
                                                   "TRABA_VEZ": str(vez)}), "error-de-git")
        self.assertTrue(marca.exists(), "el índice no se trabó")
        despues = self.foto()
        for clave in ("indice", "rama", "HEAD", "carpeta"):
            self.assertEqual(despues[clave], antes[clave], clave)
        self.assertFalse((self.copia / ".git" / "index.lock").exists(), "quedó index.lock")
        self.assertEqual([p.name for p in (self.copia / ".git").iterdir() if p.name.startswith("index.apartar-")], [])
        self.assertEqual((salida["apartado"], salida["rama"], salida["desde"]),
                         (["apartado/experimento"], "experimento", "experimento"), salida)
        self.assertEqual(self.status(), " M notas.txt\n")
        salida = self.apartar()
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"]),
                         ("guardar", "main", ["apartado/experimento"]), salida)
        self.assertEqual(self.ramas_locales("apartado/*"), ["apartado/experimento"])
        self.assertEqual(self.contenido("apartado/experimento", "notas.txt"), "MI TRABAJO\n")

    def test_el_indice_no_se_puede_reemplazar(self):
        self.apartar_trabado("carpeta", "symbolic-ref HEAD", 1)

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root escribe en una carpeta sin permisos")
    def test_index_lock_no_se_puede_crear(self):
        # La segunda `--git-path index` es la de pasar la copia al apartado; la primera es la de guardar.
        self.apartar_trabado("permisos", "--git-path index", 2)


if __name__ == "__main__":
    unittest.main()
