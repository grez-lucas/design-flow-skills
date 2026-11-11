"""Q170 a Q172: `apartar` mira los choques en todos los caminos, guarda antes de tocar la carpeta y la cambia una sola
vez, al final.

Los choques se calculan también cuando la copia no cambia de rama pero `apartar` iguala la principal actual al
servidor (H1 y H2 de la revisión 2). El apartado se arma con un índice temporal, `write-tree`, `commit-tree` y
`update-ref`, sin tocar la carpeta, el índice ni HEAD y sin correr hooks (Q171); después HEAD pasa a
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
        # servidor: la primera corrida vuelve a ella y para con `otra-rama`, y la segunda la iguala, reusando el apartado.
        for patron, corridas in (("update-ref", 1), ("-f", 2), ("--set-upstream-to=origin/spec/alertas", 2),
                                 ("switch", 1)):
            with self.subTest(patron=patron, con_cambio=True):
                self.setUp()
                self.assertSeguro(self.rama_del_flujo_sin_upstream(True), SPEC, patron,
                                  apartado="apartado/spec-alertas", corridas=corridas)
                self.assertEqual(self.contenido("apartado/spec-alertas", "notas.txt"), "cambio local\n")
                self.assertTrue(self.igual_al_servidor("spec/alertas"))

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


class SinHooksAlGuardar(Base):
    """Q171: guardar no corre hooks. H3 de la revisión 3 desaparece: un `pre-commit` que reescribe un archivo y falla
    no corre, y lo apartado es lo que había en la carpeta."""

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
