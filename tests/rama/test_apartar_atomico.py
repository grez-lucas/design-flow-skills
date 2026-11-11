"""Q170: `apartar` mira los choques en todos los caminos y es atómico.

Los choques se calculan también cuando la copia no cambia de rama pero `apartar` iguala la principal actual al
servidor (H1 y H2 de la revisión 2). Y si cualquier paso de git falla después de crear la rama del apartado, `apartar`
deja la copia en la rama de origen, con la carpeta (ignorados incluidos) y el índice como estaban, borra las ramas que
creó, devuelve las que movió a donde estaban y para con `error-de-git`.

Para hacer fallar cada paso, el PATH del ejecutable lleva primero un `git` que falla la vez número N que la orden
contiene un patrón y que corre el git real en las demás; un sh, así que esas pruebas no corren en Windows. Cada prueba
mira el JSON y una foto de la copia: rama, HEAD, ramas locales con su commit, upstream, el archivo del índice byte a
byte y cada archivo de la carpeta fuera de `.git`, byte a byte.
Uso: python3 -m unittest discover -s tests/rama -p 'test_apartar_atomico.py' -v
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
        return git("rev-parse", rama, cwd=self.copia).stdout == git("rev-parse", f"origin/{rama}", cwd=self.copia).stdout

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


@unittest.skipIf(os.name == "nt", "el git que falla es un sh")
class FallaEnCadaPaso(Base):
    """Q170: un paso de git que falla después de crear la rama del apartado deja la copia como estaba."""

    def git_que_falla(self, patron, vez):
        carpeta = self.tmp / "git-que-falla"
        carpeta.mkdir()
        real = shutil.which("git", path=ENTORNO.get("PATH"))
        (carpeta / "git").write_text(GIT_QUE_FALLA.format(git=real), encoding="utf-8")
        (carpeta / "git").chmod(0o755)
        self.marca = self.tmp / "fallo"
        return {"PATH": str(carpeta) + os.pathsep + ENTORNO.get("PATH", ""), "FALLA_PATRON": patron,
                "FALLA_VEZ": str(vez), "FALLA_CUENTA": str(self.tmp / "cuenta"), "FALLA_MARCA": str(self.marca)}

    def assertDeshecho(self, preparar, orden, patron, vez=1):
        desde = preparar()
        antes = self.foto()
        salida = self.parada(self.apartar(*orden, entorno=self.git_que_falla(patron, vez)), "error-de-git")
        self.assertTrue(self.marca.exists(), f"ninguna orden de git tuvo {patron!r} {vez} veces")
        self.assertIn("falla inyectada", salida["detalle"])
        self.assertEqual((salida["apartado"], salida["desde"], salida.get("rama")), ([], desde, desde), salida)
        despues = self.foto()
        for clave in antes:
            self.assertEqual(despues[clave], antes[clave], clave)
        # Sin el git que falla, la misma orden aparta y termina.
        self.assertNotEqual(self.apartar(*orden)["accion"], "parar")

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

    def test_desde_otra_rama(self):
        for patron, vez in (("commit", 1), ("add -u", 1), ("add --", 1), ("add -f", 1), ("commit", 2),
                            ("switch", 2)):
            with self.subTest(patron=patron, vez=vez):
                self.setUp()
                self.assertDeshecho(self.desde_otra_rama_con_todo, EPICA, patron, vez)

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
                self.assertDeshecho(self.principal_adelantada(False), EPICA, patron)

    def test_en_la_principal_adelantada_con_un_cambio(self):
        for patron, vez in (("add -u", 1), ("commit", 1), ("-f", 1), ("switch", 2)):
            with self.subTest(patron=patron, vez=vez):
                self.setUp()
                self.assertDeshecho(self.principal_adelantada(True), EPICA, patron, vez)

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
        for patron in ("branch apartado/spec-alertas", "reset", "--set-upstream-to=origin/spec/alertas"):
            with self.subTest(patron=patron):
                self.setUp()
                self.assertDeshecho(self.rama_del_flujo_sin_upstream(False), SPEC, patron)
        for patron, vez in (("-f", 1), ("--set-upstream-to=origin/spec/alertas", 1), ("switch", 2)):
            with self.subTest(patron=patron, vez=vez, con_cambio=True):
                self.setUp()
                self.assertDeshecho(self.rama_del_flujo_sin_upstream(True), SPEC, patron, vez)

    def hacia_una_rama_del_servidor(self):
        self.en_el_servidor("spec/alertas")
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.escribir(self.copia, "notas.txt", "cambio\n")
        return "experimento"

    def test_hacia_una_rama_del_flujo_que_no_esta_en_local(self):
        for patron, vez in (("--track", 1), ("switch", 2)):
            with self.subTest(patron=patron, vez=vez):
                self.setUp()
                self.assertDeshecho(self.hacia_una_rama_del_servidor, SPEC, patron, vez)


if __name__ == "__main__":
    unittest.main()
