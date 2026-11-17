"""Pruebas de CLI de lo que protege el trabajo de la persona al guardar (Q143, Q158, Q159): `rama.py revisar` mira el
trabajo sin guardar y la principal adelantada, `apartar` lo guarda en `apartado/<rama>` y vuelve a la rama del flujo,
`volver` cambia a la principal o a la rama nueva de `ofrecer`, y `commit` guarda solo las rutas de la skill.

Cada prueba corre el ejecutable como proceso en repositorios reales con un servidor bare local y mira el JSON, el
código de salida y el estado de git después, así que corre igual contra el ejecutable en Go (`RAMA`, en `repos.py`).

Los casos: A1 a A4, B5, B6, M1, M2 y M9 de las revisiones del issue 42, que antes probaban las órdenes de la prosa de
`references/rama.md`, y H2 a H5 de la tercera revisión, con renombrados, borrados, `AD`, `MM`, la rama del flujo
borrada en el servidor, HEAD separado y submódulos.
Uso: python3 -m unittest discover -s tests/rama -v
"""
import os
import unittest
from pathlib import Path

from repos import Repositorio, git

EPICA = ("--tipo", "diseno", "--epica", "alertas")
SPEC = ("--tipo", "spec", "--epica", "alertas")
MOCKUP = ("--tipo", "diseno", "--mockup", "panel", "--epicas", "alertas,riego")


class Base(Repositorio):
    def revisar(self, *nombre):
        return self.correr("revisar", *(nombre or EPICA))

    def apartar(self, *nombre):
        return self.correr("apartar", *(nombre or EPICA))

    def volver(self, *nombre):
        return self.correr("volver", *(nombre or EPICA))

    def commit(self, *args):
        return self.correr("commit", *args)

    def guardar_como_la_skill(self):
        """Lo que hace `spec-a-html` al guardar: escribe su vista, `git add design/`, `rama.py commit` y push."""
        self.escribir(self.copia, "design/vistas/alertas/nueva.html", "<p>nueva</p>\n")
        git("add", "design/", cwd=self.copia)
        salida = self.commit("-m", "diseno(alertas): nueva", "--", "design/")
        self.assertEqual(salida["accion"], "empujar", salida)
        git("push", "-q", "origin", "HEAD", cwd=self.copia)
        return self.archivos_de("HEAD")

    def parada(self, salida, motivo):
        self.assertEqual((salida["accion"], salida.get("motivo")), ("parar", motivo), salida)
        self.assertTrue(salida["detalle"])
        return salida

    def versiones(self, rama, ruta, desde="origin/main"):
        """El contenido de `ruta` en cada commit de `desde..rama`: lo que el apartado deja recuperar."""
        commits = git("rev-list", f"{desde}..{rama}", cwd=self.copia).stdout.split()
        return {git("show", f"{c}:{ruta}", cwd=self.copia, check=False).stdout for c in commits} - {""}

    def igual_al_servidor(self, rama="main"):
        return (git("rev-parse", rama, cwd=self.copia).stdout == git("rev-parse", f"origin/{rama}", cwd=self.copia).stdout)


class Guardar(Base):
    """H2: `guardar` lleva la `principal` del servidor, como `volver` y `ofrecer`."""

    def test_en_la_principal_lleva_la_principal(self):
        self.assertEqual(self.revisar(), {"accion": "guardar", "rama": "main", "principal": "main"})

    def test_en_una_rama_viva_del_flujo_lleva_la_principal(self):
        self.trabajar_en("diseno/alertas")
        self.assertEqual(self.revisar(), {"accion": "guardar", "rama": "diseno/alertas", "principal": "main"})

    def test_un_cambio_fuera_de_las_rutas_sin_preparar_no_detiene(self):
        """El commit de la skill no lo toma: va con sus rutas."""
        self.escribir(self.copia, "notas.txt", "otra persona\n")
        self.escribir(self.copia, ".agents/skills/x/SKILL.md", "instalación\n")
        self.assertEqual(self.revisar()["accion"], "guardar")


class TrabajoSinGuardar(Base):
    """A1 a A3 y H3: lo que entraría en el commit de la skill detiene `revisar`, y `apartar` lo guarda en
    `apartado/<rama>` sin perder nada, también lo que estaba solo en el índice."""

    def test_a1_en_la_principal_aparta_y_el_trabajo_ajeno_no_entra_al_commit(self):
        self.escribir(self.copia, "design/vistas/alertas/a.html", "<p>a de otra persona</p>\n")
        salida = self.parada(self.revisar(), "cambios-sin-guardar")
        self.assertEqual((salida["rama"], salida["principal"]), ("main", "main"))
        self.assertEqual(salida["archivos"], [" M design/vistas/alertas/a.html"])
        self.assertEqual(self.apartar(), {"accion": "guardar", "rama": "main", "principal": "main",
                                          "apartado": ["apartado/main"], "desde": "main"})
        self.assertEqual(self.rama_actual(), "main")
        self.assertEqual(self.status(), "")
        self.assertEqual(self.contenido("apartado/main", "design/vistas/alertas/a.html"), "<p>a de otra persona</p>\n")
        self.assertEqual(self.guardar_como_la_skill(), {"A", "design/vistas/alertas/nueva.html"})

    def test_a1_en_una_rama_viva_del_flujo_vuelve_a_ella(self):
        self.trabajar_en("diseno/alertas")
        self.escribir(self.copia, "specs/alertas/spec.md", "# Spec cambiado\n")
        self.parada(self.revisar(), "cambios-sin-guardar")
        salida = self.apartar()
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"]),
                         ("guardar", "diseno/alertas", ["apartado/diseno-alertas"]))
        self.assertEqual(self.rama_actual(), "diseno/alertas")
        self.assertNotIn("specs/alertas/spec.md", self.guardar_como_la_skill())
        self.assertIn("specs/alertas/spec.md", self.archivos_de("apartado/diseno-alertas"))

    def test_a2_el_apartado_guarda_los_archivos_nuevos_de_las_rutas_y_no_la_instalacion(self):
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.escribir(self.copia, "design/vistas/alertas/a.html", "<p>a cambiado</p>\n")
        self.escribir(self.copia, "design/vistas/alertas/borrador.html", "<p>borrador</p>\n")
        self.escribir(self.copia, ".agents/skills/x/SKILL.md", "instalación de las skills\n")
        salida = self.parada(self.revisar(), "otra-rama")
        self.assertEqual(salida["archivos"], [" M design/vistas/alertas/a.html", "?? design/vistas/alertas/borrador.html"])
        salida = self.apartar()
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"], salida["desde"]),
                         ("guardar", "main", ["apartado/experimento"], "experimento"))
        apartado = self.archivos_de("apartado/experimento")
        self.assertIn("design/vistas/alertas/borrador.html", apartado)
        self.assertIn("design/vistas/alertas/a.html", apartado)
        self.assertNotIn(".agents/skills/x/SKILL.md", apartado)
        self.assertEqual(self.status(), "?? .agents/\n")
        self.assertEqual(self.guardar_como_la_skill(), {"A", "design/vistas/alertas/nueva.html"})

    def test_a3_un_archivo_ajeno_preparado_fuera_de_las_rutas_detiene(self):
        self.escribir(self.copia, "otro.txt", "de otra persona\n")
        git("add", "otro.txt", cwd=self.copia)
        self.assertEqual(self.parada(self.revisar(), "cambios-sin-guardar")["archivos"], ["A  otro.txt"])
        self.apartar()
        self.assertIn("otro.txt", self.archivos_de("apartado/main"))
        self.assertEqual(self.status(), "")

    def test_a3_con_volver_mira_el_indice_antes_de_cambiar_de_rama(self):
        """H4: `revisar` no devuelve `volver` con trabajo preparado; la copia sigue en la rama donde estaba."""
        self.trabajar_en("diseno/alertas")
        git("push", "-q", "origin", "--delete", "diseno/alertas", cwd=self.copia)
        self.escribir(self.copia, "otro.txt", "de otra persona\n")
        git("add", "otro.txt", cwd=self.copia)
        self.parada(self.revisar(), "cambios-sin-guardar")
        self.parada(self.volver(), "cambios-sin-guardar")
        self.assertEqual(self.rama_actual(), "diseno/alertas")
        self.assertEqual(self.status(), "A  otro.txt\n")

    def test_h3_un_archivo_nuevo_preparado_y_borrado_de_la_carpeta_queda_en_el_apartado(self):
        for ruta in ("design/vistas/alertas/borrador.html", "borrador.txt"):
            with self.subTest(ruta=ruta):
                git("switch", "-q", "main", cwd=self.copia)
                self.escribir(self.copia, ruta, "borrador preparado\n")
                git("add", ruta, cwd=self.copia)
                (self.copia / ruta).unlink()
                self.assertIn(f"AD {ruta}", self.parada(self.revisar(), "cambios-sin-guardar")["archivos"])
                apartado = self.apartar()["apartado"]
                self.assertEqual(len(apartado), 1)
                self.assertEqual(self.versiones(apartado[0], ruta), {"borrador preparado\n"})
                self.assertEqual(self.status(), "")

    def test_h3_la_version_preparada_y_la_de_la_carpeta_quedan_las_dos(self):
        ruta = "design/vistas/alertas/a.html"
        self.escribir(self.copia, ruta, "<p>preparada</p>\n")
        git("add", ruta, cwd=self.copia)
        self.escribir(self.copia, ruta, "<p>en la carpeta</p>\n")
        self.assertIn(f"MM {ruta}", self.parada(self.revisar(), "cambios-sin-guardar")["archivos"])
        self.apartar()
        self.assertEqual(self.versiones("apartado/main", ruta), {"<p>preparada</p>\n", "<p>en la carpeta</p>\n"})
        self.assertEqual(self.contenido("apartado/main", ruta), "<p>en la carpeta</p>\n")
        self.assertEqual((self.copia / ruta).read_text(encoding="utf-8"), "<p>a</p>\n")

    def test_un_renombrado_preparado_se_aparta(self):
        git("mv", "design/vistas/alertas/a.html", "design/vistas/alertas/b.html", cwd=self.copia)
        self.parada(self.revisar(), "cambios-sin-guardar")
        self.apartar()
        self.assertEqual(self.contenido("apartado/main", "design/vistas/alertas/b.html"), "<p>a</p>\n")
        self.assertTrue((self.copia / "design/vistas/alertas/a.html").is_file())
        self.assertFalse((self.copia / "design/vistas/alertas/b.html").exists())

    def test_un_renombrado_sin_preparar_se_aparta_con_el_borrado_y_el_nuevo(self):
        (self.copia / "design/vistas/alertas/a.html").rename(self.copia / "design/vistas/alertas/b.html")
        archivos = self.parada(self.revisar(), "cambios-sin-guardar")["archivos"]
        self.assertEqual(archivos, [" D design/vistas/alertas/a.html", "?? design/vistas/alertas/b.html"])
        self.apartar()
        self.assertEqual(self.archivos_de("apartado/main"),
                         {"D", "design/vistas/alertas/a.html", "A", "design/vistas/alertas/b.html"})
        self.assertEqual(self.status(), "")

    def test_un_archivo_movido_desde_fuera_de_las_rutas_hacia_adentro_detiene(self):
        (self.copia / "notas.txt").rename(self.copia / "design/notas.txt")
        self.assertIn("?? design/notas.txt", self.parada(self.revisar(), "cambios-sin-guardar")["archivos"])
        self.apartar()
        self.assertEqual(self.contenido("apartado/main", "design/notas.txt"), "notas\n")
        self.assertEqual(self.status(), "")

    def test_un_borrado_se_aparta_y_el_archivo_vuelve(self):
        (self.copia / "specs/alertas/spec.md").unlink()
        self.parada(self.revisar(), "cambios-sin-guardar")
        self.apartar()
        self.assertEqual(self.archivos_de("apartado/main"), {"D", "specs/alertas/spec.md"})
        self.assertTrue((self.copia / "specs/alertas/spec.md").is_file())

    def test_b5_sin_nada_que_apartar_no_crea_una_rama_vacia(self):
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.escribir(self.copia, ".agents/skills/x/SKILL.md", "instalación de las skills\n")
        salida = self.apartar()
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"], salida["desde"]),
                         ("guardar", "main", [], "experimento"))
        self.assertEqual(self.ramas_locales("apartado/*"), [])

    def test_el_apartado_usa_el_primer_sufijo_libre(self):
        """Q158."""
        git("branch", "apartado/main", cwd=self.copia)
        git("push", "-q", "origin", "HEAD:refs/heads/apartado/main-2", cwd=self.copia)
        self.escribir(self.copia, "design/vistas/alertas/a.html", "<p>cambio</p>\n")
        self.assertEqual(self.apartar()["apartado"], ["apartado/main-3"])


class FormaDeLaCopia(Base):
    """Q177 y Q180, que reemplazan la parada de Q176 con `error-de-git`: con un submódulo, de la copia o de la rama a la
    que va, un repositorio git anidado en la carpeta o un enlace simbólico en el camino del cambio de rama, `revisar`
    para con `copia-no-soportada` y las `rutas`, antes del sí, y `apartar` para igual antes de apartar o cambiar de
    rama. Cada revisión encontraba otra forma de perder trabajo con ellos (H3 de la revisión 4; H1, H2 y H5 de la
    revisión 5; H1 y H2 de la revisión 6). Uno fuera del camino no detiene (Q180), tampoco una copia de `git worktree`
    de este repositorio (Q182)."""

    def submodulo(self):
        modulo = self.tmp / "modulo"
        git("init", "-q", "--initial-branch=main", str(modulo), cwd=self.tmp)
        self.escribir(modulo, "a.css", "a {}\n")
        git("add", "-A", cwd=modulo)
        git("commit", "-q", "-m", "modulo", cwd=modulo)
        git("-c", "protocol.file.allow=always", "submodule", "add", "-q", str(modulo), "design/lib", cwd=self.copia)
        git("commit", "-q", "-m", "submódulo", cwd=self.copia)
        git("push", "-q", "origin", "HEAD:main", cwd=self.copia)
        return self.copia / "design/lib"

    def al_servidor(self, ruta, texto="del servidor\n", rama="main"):
        self.escribir(self.otra, ruta, texto)
        git("add", ruta, cwd=self.otra)
        git("commit", "-q", "-m", f"agrega {ruta}", cwd=self.otra)
        git("push", "-q", "origin", f"HEAD:{rama}", cwd=self.otra)

    def submodulo_en_el_servidor(self, ruta, rama="main"):
        """Un submódulo que llega solo con la rama `rama` del servidor: la copia no lo tiene (H2 de la revisión 6)."""
        modulo = self.tmp / "modulo-del-servidor"
        git("init", "-q", "--initial-branch=main", str(modulo), cwd=self.tmp)
        self.escribir(modulo, "a.css", "a {}\n")
        git("add", "-A", cwd=modulo)
        git("commit", "-q", "-m", "modulo", cwd=modulo)
        git("-c", "protocol.file.allow=always", "submodule", "add", "-q", str(modulo), ruta, cwd=self.otra)
        git("commit", "-q", "-m", "submódulo", cwd=self.otra)
        git("push", "-q", "origin", f"HEAD:{rama}", cwd=self.otra)

    def otra_rama_viva(self, rama, preparar):
        """`spec/alertas` viva y `rama` viva con lo que agrega `preparar` en la otra copia: `apartar` da `elegir`."""
        self.en_el_servidor("spec/alertas")
        git("switch", "-q", "-c", "otra-viva", cwd=self.otra)
        preparar(rama)
        git("switch", "-q", "main", cwd=self.otra)

    def repositorio_anidado(self, ruta):
        """Un clon dentro de la copia, con un commit, un cambio sin commit y un archivo nuevo."""
        anidado = self.copia / ruta
        anidado.mkdir(parents=True, exist_ok=True)
        git("init", "-q", str(anidado), cwd=self.copia)
        self.escribir(anidado, "x.txt", "commit\n")
        git("add", "-A", cwd=anidado)
        git("commit", "-q", "-m", "x", cwd=anidado)
        self.escribir(anidado, "x.txt", "MI TRABAJO SIN COMMIT\n")
        self.escribir(anidado, "nuevo.txt", "MI ARCHIVO NUEVO\n")
        return anidado

    def ignorar(self, regla):
        (self.copia / ".git" / "info").mkdir(exist_ok=True)
        (self.copia / ".git" / "info" / "exclude").write_text(regla + "\n", encoding="utf-8")

    def foto(self):
        return (self.rama_actual(), git("rev-parse", "HEAD", cwd=self.copia).stdout,
                git("for-each-ref", "--format=%(refname) %(objectname)", "refs/heads", cwd=self.copia).stdout,
                git("status", "--porcelain", "--ignored", "--untracked-files=all", cwd=self.copia).stdout,
                (self.copia / ".git" / "index").read_bytes())

    def no_soportada(self, rutas, *orden, elegidas=()):
        """`revisar` y dos `apartar`, y uno con `--rama` por cada una de `elegidas`, paran con `copia-no-soportada` y
        `rutas`, y `apartar` no cambia nada."""
        salida = self.parada(self.revisar(*orden), "copia-no-soportada")
        self.assertEqual(salida["rutas"], rutas, salida)
        self.assertEqual(salida["principal"], "main", salida)
        for ruta in rutas:
            self.assertIn(ruta, salida["detalle"])
        antes = self.foto()
        for extra in ((), (), *(("--rama", rama) for rama in elegidas)):
            self.assertEqual(self.parada(self.apartar(*(orden or EPICA), *extra), "copia-no-soportada"), salida)
            self.assertEqual(self.foto(), antes)
        self.assertEqual(self.ramas_locales("apartado/*"), [])
        return salida

    def sin_parar(self, *orden):
        """`revisar` no da `copia-no-soportada` y `apartar` aparta lo de la persona y llega a la principal."""
        self.assertNotEqual(self.revisar(*orden).get("motivo"), "copia-no-soportada")
        salida = self.apartar(*orden)
        self.assertEqual((salida["accion"], salida["rama"]), ("guardar", "main"), salida)
        self.assertEqual(self.rama_actual(), "main")
        return salida


class CopiaNoSoportada(FormaDeLaCopia):
    def test_q180_un_submodulo_fuera_del_camino_no_detiene(self):
        """En la principal, sin nada que apartar ni cambio de rama, se guarda; desde otra rama, la principal tiene el
        mismo submódulo en el mismo commit, y `apartar` aparta `notas.txt` sin tocarlo."""
        lib = self.submodulo()
        self.assertEqual(self.revisar()["accion"], "guardar")
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.escribir(self.copia, "notas.txt", "MI TRABAJO\n")
        self.escribir(lib, "a.css", "a { MI TRABAJO }\n")
        self.assertEqual(self.sin_parar()["apartado"], ["apartado/experimento"])
        self.assertEqual(self.contenido("apartado/experimento", "notas.txt"), "MI TRABAJO\n")
        self.assertEqual((lib / "a.css").read_text(encoding="utf-8"), "a { MI TRABAJO }\n")
        self.assertEqual(self.revisar()["accion"], "guardar")

    def test_un_submodulo_que_apunta_a_otro_commit(self):
        """En `design/`, el submódulo en otro commit es trabajo sin guardar: `apartar` lo guardaría y el cambio de rama
        lo movería, así que está en el camino aunque la copia no cambie de rama."""
        lib = self.submodulo()
        self.escribir(lib, "b.css", "b {}\n")
        git("add", "-A", cwd=lib)
        git("commit", "-q", "-m", "otro", cwd=lib)
        salida = self.no_soportada(["design/lib"])
        self.assertEqual(salida["rama"], "main")
        self.assertIn("submódulo", salida["detalle"])

    def test_r6_h2_un_submodulo_solo_en_la_rama_de_destino(self):
        """La principal del servidor trae un submódulo en `lib`, y la copia tiene `lib/mio.txt` sin seguimiento."""
        self.submodulo_en_el_servidor("lib")
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.escribir(self.copia, "notas.txt", "MI TRABAJO\n")
        self.escribir(self.copia, "lib/mio.txt", "MI ARCHIVO\n")
        salida = self.no_soportada(["lib"])
        self.assertEqual(salida["rama"], "experimento")
        self.assertIn("lib (submódulo)", salida["detalle"])
        self.assertEqual((self.copia / "lib/mio.txt").read_text(encoding="utf-8"), "MI ARCHIVO\n")
        self.assertIn("?? lib/", self.status())

    def test_r6_h2_un_submodulo_en_una_de_varias_ramas_vivas(self):
        """Con `spec/alertas` y `spec/alertas-2` vivas, `revisar` y `apartar` miran el camino a cada una antes del sí:
        `apartar --rama spec/alertas-2` iría a un submódulo."""
        self.otra_rama_viva("spec/alertas-2", lambda rama: self.submodulo_en_el_servidor("lib", rama))
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.escribir(self.copia, "notas.txt", "MI TRABAJO\n")
        self.no_soportada(["lib"], *SPEC, elegidas=("spec/alertas-2",))
        salida = self.apartar(*SPEC, "--rama", "spec/alertas")
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"]),
                         ("guardar", "spec/alertas", ["apartado/experimento"]), salida)

    def test_q180_varias_ramas_vivas_sin_nada_en_el_camino_dan_elegir(self):
        self.submodulo()
        git("pull", "-q", "--ff-only", cwd=self.otra)
        self.otra_rama_viva("spec/alertas-2", lambda rama: self.al_servidor("otro.txt", rama=rama))
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.escribir(self.copia, "notas.txt", "MI TRABAJO\n")
        self.parada(self.revisar(*SPEC), "otra-rama")
        salida = self.apartar(*SPEC)
        self.assertEqual((salida["accion"], salida["ramas"]), ("elegir", ["spec/alertas", "spec/alertas-2"]), salida)

    def test_q176_un_submodulo_con_cambios_adentro_que_el_cambio_de_rama_moveria(self):
        """El caso de la parada de Q176: ahora `revisar` lo dice antes del sí."""
        lib = self.submodulo()
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.escribir(lib, "a.css", "a { otro }\n")
        git("add", "-A", cwd=lib)
        git("commit", "-q", "-m", "otro", cwd=lib)
        self.escribir(lib, "a.css", "a { color: red }\n")
        self.assertEqual(self.no_soportada(["design/lib"])["rama"], "experimento")
        self.assertEqual((lib / "a.css").read_text(encoding="utf-8"), "a { color: red }\n")

    def submodulo_en_otro_commit_que_la_principal(self):
        """H2 de la revisión 5: `experimento` sale del commit A del submódulo, la principal del servidor lo lleva a B,
        `a.css` es igual en los dos, y adentro tiene un cambio sin guardar. La copia no tiene nada más que guardar."""
        lib = self.submodulo()
        inicio = git("rev-parse", "HEAD", cwd=self.copia).stdout.strip()
        a = git("rev-parse", "HEAD", cwd=lib).stdout.strip()
        self.escribir(lib, "b.css", "b {}\n")
        git("add", "-A", cwd=lib)
        git("commit", "-q", "-m", "B", cwd=lib)
        git("commit", "-q", "-am", "submódulo en B", cwd=self.copia)
        git("push", "-q", "origin", "HEAD:main", cwd=self.copia)
        return lib, inicio, a

    def test_r5_h2_nada_que_guardar_y_la_principal_adelantada(self):
        lib, inicio, a = self.submodulo_en_otro_commit_que_la_principal()
        self.escribir(self.copia, "specs/alertas/spec.md", "local\n")
        git("commit", "-q", "-am", "local sin empujar", cwd=self.copia)
        git("switch", "-q", "-c", "experimento", inicio, cwd=self.copia)
        git("checkout", "-q", a, cwd=lib)
        self.escribir(lib, "a.css", "a { MI TRABAJO }\n")
        self.no_soportada(["design/lib"])
        self.assertEqual((lib / "a.css").read_text(encoding="utf-8"), "a { MI TRABAJO }\n")
        self.assertFalse(self.igual_al_servidor())

    def test_r5_h2_nada_que_guardar_con_submodule_recurse(self):
        lib, inicio, a = self.submodulo_en_otro_commit_que_la_principal()
        git("switch", "-q", "-c", "experimento", inicio, cwd=self.copia)
        git("checkout", "-q", a, cwd=lib)
        git("config", "submodule.recurse", "true", cwd=self.copia)
        self.escribir(lib, "a.css", "a { MI TRABAJO }\n")
        self.no_soportada(["design/lib"])
        self.assertEqual((lib / "a.css").read_text(encoding="utf-8"), "a { MI TRABAJO }\n")

    def assertAnidadoIntacto(self, anidado):
        self.assertTrue((anidado / ".git").is_dir())
        self.assertEqual((anidado / "x.txt").read_text(encoding="utf-8"), "MI TRABAJO SIN COMMIT\n")
        self.assertEqual((anidado / "nuevo.txt").read_text(encoding="utf-8"), "MI ARCHIVO NUEVO\n")
        self.assertEqual(git("log", "--format=%s", cwd=anidado).stdout, "x\n")

    def test_r5_h1_un_repositorio_anidado_donde_la_principal_trae_un_archivo(self):
        for ignorado in (False, True):
            with self.subTest(ignorado=ignorado):
                self.setUp()
                self.al_servidor("vendor")
                git("switch", "-q", "-c", "experimento", cwd=self.copia)
                if ignorado:
                    self.ignorar("vendor/")
                anidado = self.repositorio_anidado("vendor")
                self.assertIn("repositorio git anidado", self.no_soportada(["vendor"])["detalle"])
                self.assertAnidadoIntacto(anidado)

    def test_r6_h1_un_repositorio_anidado_en_una_carpeta_con_archivos_con_seguimiento(self):
        """`experimento` sigue `design/lib/t.txt`, `design/lib` es además un repositorio, y la principal del servidor
        trae el archivo `design/lib`: git no lista ese repositorio como `design/lib/`, sino sus archivos."""
        self.al_servidor("design/lib")
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.escribir(self.copia, "design/lib/t.txt", "seguido\n")
        git("add", "design/lib/t.txt", cwd=self.copia)
        git("commit", "-q", "-m", "t", cwd=self.copia)
        anidado = self.repositorio_anidado("design/lib")
        self.assertIn("design/lib (repositorio git anidado)", self.no_soportada(["design/lib"])["detalle"])
        self.assertAnidadoIntacto(anidado)

    def test_q180_un_repositorio_anidado_fuera_del_camino_no_detiene(self):
        """Dentro de una carpeta ignorada o fuera de las rutas de la skill, `apartar` no lo guarda y el cambio de rama
        no lo toca."""
        for ruta, regla, rama in (("cache/profundo/clon", "cache/", None), ("clon", None, "experimento")):
            with self.subTest(ruta=ruta):
                self.setUp()
                if regla:
                    self.ignorar(regla)
                if rama:
                    git("switch", "-q", "-c", rama, cwd=self.copia)
                anidado = self.repositorio_anidado(ruta)
                self.escribir(self.copia, "design/vistas/alertas/a.html", "<p>MI TRABAJO</p>\n")
                apartado = f"apartado/{rama or 'main'}"
                self.assertEqual(self.sin_parar()["apartado"], [apartado])
                self.assertEqual(self.contenido(apartado, "design/vistas/alertas/a.html"), "<p>MI TRABAJO</p>\n")
                self.assertAnidadoIntacto(anidado)
                self.assertEqual(self.revisar()["accion"], "guardar")

    def test_un_repositorio_anidado_en_las_rutas_de_la_skill(self):
        """En `design/` es un archivo nuevo de las rutas, que `apartar` guardaría: está en el camino."""
        anidado = self.repositorio_anidado("design/clon")
        self.no_soportada(["design/clon"])
        self.assertAnidadoIntacto(anidado)

    def test_volver_con_un_repositorio_anidado_fuera_del_camino(self):
        self.trabajar_en("tickets/alertas")
        git("push", "-q", "origin", "--delete", "tickets/alertas", cwd=self.copia)
        anidado = self.repositorio_anidado("clon")
        orden = ("--tipo", "tickets", "--epica", "alertas")
        self.assertEqual(self.revisar(*orden)["accion"], "volver")
        self.assertEqual(self.volver(*orden), {"accion": "guardar", "rama": "main", "principal": "main"})
        self.assertAnidadoIntacto(anidado)

    def test_volver_con_un_repositorio_anidado_en_el_camino(self):
        self.trabajar_en("tickets/alertas")
        git("push", "-q", "origin", "--delete", "tickets/alertas", cwd=self.copia)
        self.al_servidor("clon")
        anidado = self.repositorio_anidado("clon")
        orden = ("--tipo", "tickets", "--epica", "alertas")
        self.parada(self.revisar(*orden), "copia-no-soportada")
        self.parada(self.volver(*orden), "copia-no-soportada")
        self.assertEqual(self.rama_actual(), "tickets/alertas")
        self.assertAnidadoIntacto(anidado)

    def test_varias_a_la_vez(self):
        lib = self.submodulo()
        git("pull", "-q", "--ff-only", cwd=self.otra)
        self.al_servidor("clon")
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.escribir(lib, "b.css", "b {}\n")
        git("add", "-A", cwd=lib)
        git("commit", "-q", "-m", "otro", cwd=lib)
        self.repositorio_anidado("clon")
        self.assertEqual(self.revisar()["rutas"], ["clon", "design/lib"])

    def test_r7_h1_un_anidado_en_design_que_solo_la_rama_actual_ignora(self):
        """Q184: `experimento` ignora `design/vendor/` en su `.gitignore` y la principal no; con las reglas de la rama
        actual no está en el camino, pero con las de la principal `apartar` lo guardaría. Para antes del sí."""
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.escribir(self.copia, ".gitignore", "design/vendor/\n")
        git("add", ".gitignore", cwd=self.copia)
        git("commit", "-q", "-m", "ignora vendor", cwd=self.copia)
        anidado = self.repositorio_anidado("design/vendor")
        self.escribir(self.copia, "notas.txt", "MI TRABAJO\n")
        self.assertEqual(self.no_soportada(["design/vendor"])["rama"], "experimento")
        self.assertEqual((self.copia / "notas.txt").read_text(encoding="utf-8"), "MI TRABAJO\n")
        self.assertAnidadoIntacto(anidado)

    def test_q184_un_anidado_ignorado_en_las_rutas_de_la_skill_detiene_siempre(self):
        for ruta in ("design/cache/clon", "specs/clon"):
            with self.subTest(ruta=ruta):
                self.setUp()
                self.ignorar(ruta.rsplit("/", 1)[0] + "/")
                anidado = self.repositorio_anidado(ruta)
                self.no_soportada([ruta])
                self.assertAnidadoIntacto(anidado)

    def test_q187_una_copia_vinculada_ignorada_en_design_detiene(self):
        """Q187: una copia de `git worktree` de este repositorio dentro de `design/` o `specs/` cuenta como repositorio
        anidado, esté o no en el camino."""
        for ruta in ("design/wt", "specs/wt"):
            with self.subTest(ruta=ruta):
                self.setUp()
                vinculada = self.copia_vinculada(ruta)
                self.assertIn(f"{ruta} (copia de `git worktree` de este repositorio)", self.no_soportada([ruta])["detalle"])
                self.assertVinculadaIntacta(vinculada)

    def test_r7_r1_una_copia_vinculada_en_design_que_solo_la_rama_actual_ignora(self):
        """R1 del recheck de la revisión 7: `experimento` ignora `design/wt/` en su `.gitignore` y la principal no."""
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.escribir(self.copia, ".gitignore", "design/wt/\n")
        git("add", ".gitignore", cwd=self.copia)
        git("commit", "-q", "-m", "ignora wt", cwd=self.copia)
        git("worktree", "add", "-q", "-b", "tarea", str(self.copia / "design/wt"), "main", cwd=self.copia)
        self.escribir(self.copia, "design/wt/notas.txt", "TRABAJO EN LA OTRA COPIA\n")
        self.escribir(self.copia, "notas.txt", "MI TRABAJO\n")
        self.assertEqual(self.no_soportada(["design/wt"])["rama"], "experimento")
        self.assertEqual((self.copia / "notas.txt").read_text(encoding="utf-8"), "MI TRABAJO\n")
        self.assertVinculadaIntacta(self.copia / "design/wt")
        self.assertEqual(git("-C", "design/wt", "branch", "--show-current", cwd=self.copia).stdout, "tarea\n")

    def copia_vinculada(self, ruta):
        """Una copia de `git worktree` de este repositorio dentro de la carpeta, ignorada, con un cambio sin commit."""
        self.ignorar(ruta + "/")
        git("worktree", "add", "-q", ruta, cwd=self.copia)
        self.escribir(self.copia, f"{ruta}/notas.txt", "TRABAJO EN LA OTRA COPIA\n")
        return self.copia / ruta

    def assertVinculadaIntacta(self, vinculada):
        self.assertTrue((vinculada / ".git").is_file())
        self.assertEqual((vinculada / "notas.txt").read_text(encoding="utf-8"), "TRABAJO EN LA OTRA COPIA\n")
        # git da la ruta real: sin enlaces simbólicos y, en Windows, la larga con `/` (`runneradmin`, no `RUNNER~1`).
        # Se compara la ruta resuelta de los dos lados, no el texto.
        copias = [Path(l[len("worktree "):]).resolve()
                  for l in git("worktree", "list", "--porcelain", cwd=self.copia).stdout.splitlines()
                  if l.startswith("worktree ")]
        self.assertIn(vinculada.resolve(), copias)

    def test_q182_una_copia_vinculada_fuera_del_camino_no_detiene(self):
        vinculada = self.copia_vinculada(".claude/worktrees/tarea")
        self.assertEqual(self.revisar()["accion"], "guardar")
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.escribir(self.copia, "notas.txt", "MI TRABAJO\n")
        self.assertEqual(self.sin_parar()["apartado"], ["apartado/experimento"])
        self.assertVinculadaIntacta(vinculada)

    def test_q182_una_copia_vinculada_en_el_camino(self):
        self.al_servidor("tarea")
        vinculada = self.copia_vinculada("tarea")
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.escribir(self.copia, "notas.txt", "MI TRABAJO\n")
        self.assertIn("tarea (copia de `git worktree` de este repositorio)", self.no_soportada(["tarea"])["detalle"])
        self.assertVinculadaIntacta(vinculada)


@unittest.skipIf(os.name == "nt", "crear un enlace simbólico en Windows pide permisos")
class EnlaceEnElCamino(FormaDeLaCopia):
    """Q177 y H5 de la revisión 5: un enlace simbólico sin seguimiento está en el camino del cambio de rama si el
    `git switch` lo reemplaza o lo borra, apunte adonde apunte: donde la rama a la que va tiene un archivo, donde tiene
    una carpeta de sus archivos, o dentro de una carpeta de la copia donde tiene un archivo. Ignorado o no."""

    def enlace(self, ruta, apunta):
        lugar = self.copia / ruta
        lugar.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(apunta, lugar)
        return lugar

    def assertEnlace(self, lugar, apunta):
        self.assertTrue(lugar.is_symlink())
        self.assertEqual(os.readlink(lugar), apunta)

    def test_r5_h5_donde_la_principal_trae_un_archivo(self):
        for apunta in ("no-existe", "design", "notas.txt"):
            for ignorado in (False, True):
                with self.subTest(apunta=apunta, ignorado=ignorado):
                    self.setUp()
                    self.al_servidor("enlace")
                    git("switch", "-q", "-c", "experimento", cwd=self.copia)
                    if ignorado:
                        self.ignorar("enlace")
                    lugar = self.enlace("enlace", apunta)
                    self.assertIn("enlace simbólico", self.no_soportada(["enlace"])["detalle"])
                    self.assertEnlace(lugar, apunta)

    def test_donde_la_principal_trae_una_carpeta(self):
        self.al_servidor("doc/nuevo.md")
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        lugar = self.enlace("doc", "design")
        self.no_soportada(["doc"])
        self.assertEnlace(lugar, "design")

    def test_dentro_de_una_carpeta_donde_la_principal_trae_un_archivo(self):
        self.al_servidor("vendor")
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.escribir(self.copia, "vendor/x.txt", "MI TRABAJO\n")
        lugar = self.enlace("vendor/enlace", "../notas.txt")
        self.no_soportada(["vendor/enlace"])
        self.assertEnlace(lugar, "../notas.txt")

    def test_al_igualar_la_principal_adelantada(self):
        self.al_servidor("enlace")
        self.escribir(self.copia, "specs/alertas/spec.md", "local\n")
        git("commit", "-q", "-am", "local sin empujar", cwd=self.copia)
        lugar = self.enlace("enlace", "no-existe")
        self.no_soportada(["enlace"])
        self.assertEnlace(lugar, "no-existe")

    def test_fuera_del_camino_no_detiene(self):
        """Un enlace que la rama a la que va no toca queda donde está, como cualquier sin seguimiento."""
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        lugar = self.enlace("enlace", "no-existe")
        self.escribir(self.copia, "notas.txt", "MI TRABAJO\n")
        self.parada(self.revisar(), "otra-rama")
        salida = self.apartar()
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"]),
                         ("guardar", "main", ["apartado/experimento"]), salida)
        self.assertEnlace(lugar, "no-existe")
        self.assertEqual(self.revisar()["accion"], "guardar")

    def test_en_la_principal_sin_cambio_de_rama_no_detiene(self):
        self.enlace("enlace", "no-existe")
        self.assertEqual(self.revisar()["accion"], "guardar")

    def test_r6_h2_en_el_camino_de_una_de_varias_ramas_vivas(self):
        """`build` es un enlace ignorado donde `spec/alertas-2` tiene `build/x.txt`: con las dos vivas, `revisar` y
        `apartar` lo dicen antes del sí, también con `--rama spec/alertas-2`."""
        self.otra_rama_viva("spec/alertas-2", lambda rama: self.al_servidor("build/x.txt", rama=rama))
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.escribir(self.copia, "notas.txt", "MI TRABAJO\n")
        self.ignorar("build")
        lugar = self.enlace("build", "no-existe")
        self.no_soportada(["build"], *SPEC, elegidas=("spec/alertas-2",))
        self.assertEnlace(lugar, "no-existe")


class RamaEnOtraCopia(FormaDeLaCopia):
    """Q185 y H2 de la revisión 7: si la rama a la que van `apartar` o `volver` está puesta en otra copia de
    `git worktree` de este repositorio, `revisar`, `apartar` y `volver` paran con `rama-en-otra-copia` y la ruta de esa
    copia, antes del sí y sin mover nada; git no deja cambiar ni igualar esa rama desde acá."""

    def otra_copia(self, ruta, rama):
        git("worktree", "add", "-q", str(ruta), rama, cwd=self.copia)
        return next(l[len("worktree "):] for l in git("worktree", "list", "--porcelain", cwd=self.copia).stdout.splitlines()
                    if l.startswith("worktree ") and l.endswith(ruta.name))

    def en_otra_copia(self, ruta, *orden, con_volver=False):
        salida = self.parada(self.revisar(*orden), "rama-en-otra-copia")
        self.assertEqual(salida["rutas"], [ruta], salida)
        self.assertIn(ruta, salida["detalle"])
        antes = self.foto()
        for _ in range(2):
            self.assertEqual(self.parada(self.apartar(*(orden or EPICA)), "rama-en-otra-copia"), salida)
            self.assertEqual(self.foto(), antes)
        if con_volver:
            self.assertEqual(self.parada(self.volver(*orden), "rama-en-otra-copia"), salida)
            self.assertEqual(self.foto(), antes)
        self.assertEqual(self.ramas_locales("apartado/*"), [])
        return salida

    def test_r7_h2_la_rama_viva_puesta_en_una_copia_de_claude_worktrees(self):
        self.en_el_servidor("spec/alertas")
        git("fetch", "-q", cwd=self.copia)
        git("branch", "-q", "--track", "spec/alertas", "origin/spec/alertas", cwd=self.copia)
        self.ignorar(".claude/worktrees/")
        ruta = self.otra_copia(self.copia / ".claude/worktrees/tarea", "spec/alertas")
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.escribir(self.copia, "notas.txt", "MI TRABAJO\n")
        self.assertEqual(self.en_otra_copia(ruta, *SPEC)["rama"], "experimento")
        self.assertEqual((self.copia / "notas.txt").read_text(encoding="utf-8"), "MI TRABAJO\n")

    def test_r7_h2_la_principal_puesta_en_otra_copia_fuera_de_la_carpeta(self):
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.escribir(self.copia, "notas.txt", "MI TRABAJO\n")
        ruta = self.otra_copia(self.tmp / "otra-sesion", "main")
        self.en_otra_copia(ruta, *SPEC)

    def test_volver_con_la_principal_en_otra_copia(self):
        self.trabajar_en("tickets/alertas")
        git("push", "-q", "origin", "--delete", "tickets/alertas", cwd=self.copia)
        ruta = self.otra_copia(self.tmp / "otra-sesion", "main")
        self.en_otra_copia(ruta, "--tipo", "tickets", "--epica", "alertas", con_volver=True)

    def test_una_rama_que_no_es_el_destino_en_otra_copia_no_detiene(self):
        git("branch", "-q", "otra", cwd=self.copia)
        self.otra_copia(self.tmp / "otra-sesion", "otra")
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.escribir(self.copia, "notas.txt", "MI TRABAJO\n")
        self.assertEqual(self.sin_parar()["apartado"], ["apartado/experimento"])


class PrincipalAdelantada(Base):
    """M1 y Q158: los commits locales de la principal se apartan en `apartado/<principal>` y la principal se iguala
    al servidor, para que el push no los suba."""

    def commit_local(self, mensaje="commit local de otra sesión"):
        self.escribir(self.copia, f"design/{mensaje.replace(' ', '-')}.html", "<p>local</p>\n")
        git("add", "design/", cwd=self.copia)
        git("commit", "-q", "-m", mensaje, cwd=self.copia)

    def test_m1_se_aparta_y_no_se_sube(self):
        self.commit_local()
        salida = self.parada(self.revisar(), "principal-adelantada")
        self.assertEqual((salida["rama"], salida["principal"]), ("main", "main"))
        self.assertEqual([c.split(" ", 1)[1] for c in salida["commits"]], ["commit local de otra sesión"])
        self.assertEqual(self.apartar(), {"accion": "guardar", "rama": "main", "principal": "main",
                                          "apartado": ["apartado/main"], "desde": "main"})
        self.assertTrue(self.igual_al_servidor())
        self.guardar_como_la_skill()
        en_el_servidor = git("log", "--format=%s", "origin/main", cwd=self.copia).stdout
        self.assertNotIn("commit local de otra sesión", en_el_servidor)
        self.assertIn("commit local de otra sesión", git("log", "--format=%s", "apartado/main", cwd=self.copia).stdout)

    def test_con_trabajo_sin_guardar_y_adelantada_un_solo_apartado_guarda_los_dos(self):
        self.commit_local()
        self.escribir(self.copia, "design/vistas/alertas/a.html", "<p>cambio</p>\n")
        salida = self.apartar()
        self.assertEqual((salida["accion"], salida["apartado"]), ("guardar", ["apartado/main"]))
        log = git("log", "--format=%s", "apartado/main", cwd=self.copia).stdout
        self.assertIn("commit local de otra sesión", log)
        self.assertEqual(self.contenido("apartado/main", "design/vistas/alertas/a.html"), "<p>cambio</p>\n")
        self.assertTrue(self.igual_al_servidor())

    def test_con_el_apartado_ocupado_usa_el_primer_sufijo_libre(self):
        git("branch", "apartado/main", cwd=self.copia)
        self.commit_local()
        self.assertEqual(self.apartar()["apartado"], ["apartado/main-2"])
        self.assertIn("commit local de otra sesión", git("log", "--format=%s", "apartado/main-2", cwd=self.copia).stdout)

    def test_en_una_rama_viva_del_flujo_la_principal_adelantada_no_detiene(self):
        """El push va a la rama del flujo: los commits de la principal no suben."""
        self.commit_local()
        self.trabajar_en("diseno/alertas")
        self.assertEqual(self.revisar()["accion"], "guardar")

    def test_h2_sin_origin_head_ve_la_principal_del_servidor(self):
        """Una copia clonada con el servidor vacío, o armada con `git init` y `git remote add`, no tiene
        `origin/HEAD`; la principal sale del servidor."""
        git("remote", "set-head", "origin", "--delete", cwd=self.copia)
        self.commit_local()
        salida = self.parada(self.revisar(), "principal-adelantada")
        self.assertEqual(salida["principal"], "main")

    def test_h2_con_origin_head_desactualizado_ve_la_principal_del_servidor(self):
        git("push", "-q", "origin", "HEAD:refs/heads/trunk", cwd=self.otra)
        git("symbolic-ref", "HEAD", "refs/heads/trunk", cwd=self.servidor)
        git("fetch", "-q", cwd=self.copia)
        git("switch", "-q", "trunk", cwd=self.copia)
        self.commit_local()
        salida = self.parada(self.revisar(), "principal-adelantada")
        self.assertEqual((salida["rama"], salida["principal"]), ("trunk", "trunk"))
        self.assertEqual(self.apartar()["apartado"], ["apartado/trunk"])
        self.assertTrue(self.igual_al_servidor("trunk"))

    def test_h2_armada_con_git_init_y_remote_add(self):
        copia = self.tmp / "armada"
        git("init", "-q", "--initial-branch=main", str(copia), cwd=self.tmp)
        git("remote", "add", "origin", str(self.servidor), cwd=copia)
        git("fetch", "-q", "origin", cwd=copia)
        git("switch", "-q", "main", cwd=copia)
        self.copia = copia
        git("config", "user.name", "producto", cwd=copia)
        git("config", "user.email", "producto@example.com", cwd=copia)
        self.commit_local()
        self.parada(self.revisar(), "principal-adelantada")
        self.apartar()
        self.assertTrue(self.igual_al_servidor())


class Volver(Base):
    """`volver` cambia a la principal del servidor, con lo nuevo, solo si `revisar` devuelve `volver`."""

    def rama_borrada(self):
        self.trabajar_en("diseno/alertas")
        git("push", "-q", "origin", "--delete", "diseno/alertas", cwd=self.copia)
        self.escribir(self.otra, "design/vistas/alertas/c.html", "<p>c</p>\n")
        git("add", "-A", cwd=self.otra)
        git("commit", "-q", "-m", "otro cambio en la principal", cwd=self.otra)
        git("push", "-q", "origin", "HEAD:main", cwd=self.otra)

    def test_vuelve_a_la_principal_al_dia(self):
        self.rama_borrada()
        self.assertEqual(self.revisar()["accion"], "volver")
        self.assertEqual(self.volver(), {"accion": "guardar", "rama": "main", "principal": "main"})
        self.assertEqual(self.rama_actual(), "main")
        self.assertTrue(self.igual_al_servidor())
        self.assertEqual(self.revisar()["accion"], "guardar")

    def test_sin_volver_no_cambia_nada(self):
        self.trabajar_en("diseno/alertas")
        self.assertEqual(self.volver(), {"accion": "guardar", "rama": "diseno/alertas", "principal": "main"})
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.parada(self.volver(), "otra-rama")
        self.assertEqual(self.rama_actual(), "experimento")

    def test_h4_un_cambio_que_choca_con_la_principal_detiene_antes_de_cambiar(self):
        self.rama_borrada()
        self.escribir(self.otra, "notas.txt", "notas del servidor\n")
        git("commit", "-q", "-am", "notas", cwd=self.otra)
        git("push", "-q", "origin", "HEAD:main", cwd=self.otra)
        self.escribir(self.copia, "notas.txt", "notas sin guardar\n")
        self.assertEqual(self.revisar()["accion"], "volver")
        salida = self.parada(self.volver(), "cambios-sin-guardar")
        self.assertIn(" M notas.txt", salida["archivos"])
        self.assertEqual(self.rama_actual(), "diseno/alertas")
        self.assertEqual((self.copia / "notas.txt").read_text(encoding="utf-8"), "notas sin guardar\n")
        salida = self.apartar()
        self.assertEqual((salida["accion"], salida["apartado"]), ("volver", ["apartado/diseno-alertas"]))
        self.assertEqual(self.volver()["rama"], "main")
        self.assertTrue(self.igual_al_servidor())
        self.assertEqual(self.contenido("apartado/diseno-alertas", "notas.txt"), "notas sin guardar\n")

    def test_con_la_principal_adelantada_no_vuelve(self):
        self.rama_borrada()
        git("switch", "-q", "main", cwd=self.copia)
        self.escribir(self.copia, "design/local.html", "<p>local</p>\n")
        git("add", "design/", cwd=self.copia)
        git("commit", "-q", "-m", "local", cwd=self.copia)
        git("switch", "-q", "diseno/alertas", cwd=self.copia)
        self.parada(self.revisar(), "principal-adelantada")
        self.parada(self.volver(), "principal-adelantada")
        self.assertEqual(self.rama_actual(), "diseno/alertas")
        self.assertEqual(self.apartar()["accion"], "volver")
        self.assertEqual(self.volver()["rama"], "main")
        self.assertTrue(self.igual_al_servidor())
        self.assertIn("local", git("log", "--format=%s", "apartado/main", cwd=self.copia).stdout)


class Ofrecer(Base):
    """A4 y H5: `ofrecer` mira también los archivos nuevos de las rutas, y después de apartar sigue siendo
    `ofrecer`, así que la rama nueva aceptada no se pierde."""

    def test_a4_un_archivo_nuevo_en_design_detiene(self):
        self.trabajar_en("diseno/alertas")
        self.escribir(self.copia, "design/vistas/alertas/borrador.html", "<p>borrador</p>\n")
        salida = self.parada(self.revisar(*MOCKUP), "cambios-sin-guardar")
        self.assertEqual(salida["archivos"], ["?? design/vistas/alertas/borrador.html"])

    def test_h5_despues_de_apartar_sigue_con_la_rama_nueva(self):
        self.trabajar_en("diseno/alertas")
        self.escribir(self.copia, "design/vistas/alertas/a.html", "<p>cambio</p>\n")
        self.parada(self.revisar(*MOCKUP), "cambios-sin-guardar")
        salida = self.apartar(*MOCKUP)
        self.assertEqual((salida["accion"], salida["rama"], salida["rama_nueva"], salida["apartado"]),
                         ("ofrecer", "diseno/alertas", "diseno/panel", ["apartado/diseno-alertas"]))
        self.assertEqual(self.volver(*MOCKUP, "--rama-nueva", "diseno/panel"),
                         {"accion": "guardar", "rama": "diseno/panel", "principal": "main"})
        self.assertEqual(self.rama_actual(), "diseno/panel")
        self.assertEqual(git("rev-parse", "HEAD", cwd=self.copia).stdout,
                         git("rev-parse", "origin/main", cwd=self.copia).stdout)

    def test_h5_con_la_principal_adelantada_sigue_con_la_rama_nueva(self):
        self.escribir(self.copia, "design/local.html", "<p>local</p>\n")
        git("add", "design/", cwd=self.copia)
        git("commit", "-q", "-m", "local", cwd=self.copia)
        git("switch", "-q", "-c", "diseno/alertas", "origin/main", cwd=self.copia)
        git("push", "-q", "-u", "origin", "diseno/alertas", cwd=self.copia)
        self.parada(self.revisar(*MOCKUP), "principal-adelantada")
        self.assertEqual(self.apartar(*MOCKUP)["accion"], "ofrecer")
        self.assertEqual(self.volver(*MOCKUP, "--rama-nueva", "diseno/panel")["rama"], "diseno/panel")
        self.assertNotIn("local", git("log", "--format=%s", "HEAD", cwd=self.copia).stdout.split("\n"))

    def test_sin_el_si_volver_no_crea_la_rama_nueva(self):
        """Sin `--rama-nueva`, o con un nombre que ya no es el libre, devuelve `ofrecer` y no cambia nada."""
        self.trabajar_en("diseno/alertas")
        self.assertEqual(self.volver(*MOCKUP)["accion"], "ofrecer")
        self.en_el_servidor("diseno/panel")
        salida = self.volver(*MOCKUP, "--rama-nueva", "diseno/panel")
        self.assertEqual((salida["accion"], salida["rama_nueva"]), ("ofrecer", "diseno/panel-2"))
        self.assertEqual(self.rama_actual(), "diseno/alertas")


class VueltaALaRamaDelFlujo(Base):
    """M2 y M9: desde una rama que no es del flujo, `apartar` vuelve a la rama viva del servidor para este trabajo,
    con sufijos exactos, o a la principal."""

    def test_m2_vuelve_a_la_rama_viva_del_flujo_de_la_epica(self):
        git("switch", "-q", "-c", "diseno/alertas", cwd=self.otra)
        self.escribir(self.otra, "design/vistas/alertas/b.html", "<p>b</p>\n")
        git("add", "design/", cwd=self.otra)
        git("commit", "-q", "-m", "diseno(alertas): b", cwd=self.otra)
        git("push", "-q", "-u", "origin", "diseno/alertas", cwd=self.otra)
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.parada(self.revisar(), "otra-rama")
        salida = self.apartar()
        self.assertEqual((salida["accion"], salida["rama"]), ("guardar", "diseno/alertas"))
        self.assertTrue(self.igual_al_servidor("diseno/alertas"))
        self.assertIn("design/vistas/alertas/nueva.html", self.guardar_como_la_skill())

    def test_m9_con_varias_pregunta_y_el_sufijo_es_exacto(self):
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.escribir(self.copia, "design/vistas/alertas/a.html", "<p>cambio</p>\n")
        self.en_el_servidor("diseno/alertas-2fa", "diseno/alertas-2", "diseno/alertas-10", "diseno/alertas-push",
                            "diseno/alertas-02", "spec/alertas")
        salida = self.apartar()
        self.assertEqual((salida["accion"], salida["ramas"], salida["apartado"]),
                         ("elegir", ["diseno/alertas-10", "diseno/alertas-2"], ["apartado/experimento"]))
        self.assertEqual(self.rama_actual(), "apartado/experimento")
        self.assertEqual(self.correr("apartar", *EPICA, "--rama", "spec/alertas")["accion"], "elegir")
        salida = self.correr("apartar", *EPICA, "--rama", "diseno/alertas-2")
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"]), ("guardar", "diseno/alertas-2", []))
        self.assertEqual(self.rama_actual(), "diseno/alertas-2")

    def test_m9_otra_epica_que_empieza_igual_no_cuenta(self):
        self.en_el_servidor("diseno/alertas-2fa", "diseno/alertas-2fa-3", "diseno/alertas-2")
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        salida = self.apartar("--tipo", "diseno", "--epica", "alertas-2fa")
        self.assertEqual(salida["accion"], "elegir")
        self.assertEqual(salida["ramas"], ["diseno/alertas-2fa", "diseno/alertas-2fa-3"])

    def test_rama_del_flujo_borrada_con_un_commit_sin_push_y_un_cambio_sin_guardar(self):
        self.trabajar_en("spec/alertas")
        self.escribir(self.copia, "specs/alertas/spec.md", "# Spec con commit\n")
        git("commit", "-q", "-am", "commit sin push", cwd=self.copia)
        git("push", "-q", "origin", "--delete", "spec/alertas", cwd=self.copia)
        self.escribir(self.copia, "specs/alertas/spec.md", "# Spec sin guardar\n")
        orden = ("--tipo", "spec", "--epica", "alertas")
        self.assertIn(" M specs/alertas/spec.md", self.parada(self.revisar(*orden), "commits-sin-empujar")["archivos"])
        salida = self.apartar(*orden)
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"], salida["desde"]),
                         ("guardar", "main", ["apartado/spec-alertas"], "spec/alertas"))
        self.assertEqual(self.contenido("apartado/spec-alertas", "specs/alertas/spec.md"), "# Spec sin guardar\n")
        self.assertEqual(self.contenido("spec/alertas", "specs/alertas/spec.md"), "# Spec con commit\n")

    def test_head_separado_con_un_commit_suelto(self):
        git("switch", "-q", "--detach", cwd=self.copia)
        self.escribir(self.copia, "design/suelto.html", "<p>suelto</p>\n")
        git("add", "design/", cwd=self.copia)
        git("commit", "-q", "-m", "commit suelto", cwd=self.copia)
        salida = self.parada(self.revisar(), "sin-rama")
        self.assertEqual(salida["principal"], "main")
        salida = self.apartar()
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"], salida["desde"]),
                         ("guardar", "main", ["apartado/sin-rama"], None))
        self.assertIn("commit suelto", git("log", "--format=%s", "apartado/sin-rama", cwd=self.copia).stdout)

    def test_head_separado_sin_nada_suelto_no_crea_rama(self):
        git("switch", "-q", "--detach", cwd=self.copia)
        salida = self.apartar()
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"]), ("guardar", "main", []))


class Commit(Base):
    """El commit de la skill lleva solo sus rutas, aunque otra persona haya dejado algo preparado fuera de ellas."""

    def test_a3_lo_preparado_fuera_de_las_rutas_no_entra_y_sigue_preparado(self):
        self.escribir(self.copia, "otro.txt", "de otra persona\n")
        git("add", "otro.txt", cwd=self.copia)
        self.escribir(self.copia, "design/vistas/alertas/nueva.html", "<p>nueva</p>\n")
        git("add", "design/", cwd=self.copia)
        salida = self.commit("-m", "diseno(alertas): nueva", "-m", "Segundo párrafo.", "--", "design/")
        self.assertEqual(salida, {"accion": "empujar", "rama": "main",
                                  "archivos": ["A\tdesign/vistas/alertas/nueva.html"]})
        self.assertEqual(git("log", "-1", "--format=%B", cwd=self.copia).stdout.strip(),
                         "diseno(alertas): nueva\n\nSegundo párrafo.")
        self.assertEqual(self.status(), "A  otro.txt\n")

    def test_un_borrado_un_archivo_nuevo_y_un_gitignore_recreado(self):
        git("rm", "-q", "specs/alertas/spec.md", cwd=self.copia)
        self.escribir(self.copia, "design/vistas/alertas/nueva.html", "<p>nueva</p>\n")
        self.escribir(self.copia, ".gitignore", ".lavish/\n")
        git("add", "design/", ".gitignore", cwd=self.copia)
        salida = self.commit("-m", "spec(alertas): cambio", "--", "design/", "specs/alertas/", ".gitignore")
        self.assertEqual(sorted(salida["archivos"]), ["A\t.gitignore", "A\tdesign/vistas/alertas/nueva.html",
                                                      "D\tspecs/alertas/spec.md"])
        self.assertEqual(self.status(), "")

    def test_sin_cambios_en_las_rutas_no_hace_commit(self):
        antes = git("rev-parse", "HEAD", cwd=self.copia).stdout
        self.assertEqual(self.commit("-m", "nada", "--", "design/"), {"accion": "sin-cambios", "rama": "main"})
        self.assertEqual(git("rev-parse", "HEAD", cwd=self.copia).stdout, antes)

    def test_solo_rutas_de_la_skill(self):
        for rutas in ((".",), ("notas.txt",), ("design/", "-A"), ("../fuera",), ("design/../notas.txt",), ()):
            with self.subTest(rutas=rutas):
                self.correr("commit", "-m", "x", "--", *rutas, codigo=2)
        self.correr("commit", "--", "design/", codigo=2)


class MensajeDesdeArchivo(Base):
    """Q162: `commit -F <archivo>` toma el mensaje de un archivo, para que no pase por la línea de órdenes de
    PowerShell, que pierde las comillas dobles. El archivo es UTF-8, con o sin BOM (el de `Set-Content -Encoding UTF8`
    de PowerShell 5.1) y con LF o CRLF, y su ruta es relativa a donde corre `rama`, no al repositorio."""

    MENSAJE = 'diseno(alertas): "comillas" & a^b | %PATH% ñandú\n\nSegundo párrafo con `código`.'

    def preparar(self):
        self.escribir(self.copia, "design/vistas/alertas/nueva.html", "<p>nueva</p>\n")
        git("add", "design/", cwd=self.copia)

    def test_el_mensaje_es_el_del_archivo(self):
        self.preparar()
        (self.tmp / "mensaje.txt").write_text(self.MENSAJE + "\n", encoding="utf-8")
        salida = self.commit("-F", str(self.tmp / "mensaje.txt"), "--", "design/")
        self.assertEqual(salida["accion"], "empujar", salida)
        self.assertEqual(git("log", "-1", "--format=%B", cwd=self.copia).stdout.strip(), self.MENSAJE)

    def test_con_bom_y_crlf(self):
        self.preparar()
        (self.tmp / "mensaje.txt").write_bytes(b"\xef\xbb\xbf" + self.MENSAJE.replace("\n", "\r\n").encode() + b"\r\n")
        self.commit("-F", str(self.tmp / "mensaje.txt"), "--", "design/")
        self.assertEqual(git("log", "-1", "--format=%B", cwd=self.copia).stdout.strip(), self.MENSAJE)

    def test_la_ruta_relativa_es_la_de_donde_corre(self):
        self.preparar()
        afuera = self.tmp / "afuera"
        afuera.mkdir()
        (afuera / "mensaje.txt").write_text(self.MENSAJE, encoding="utf-8")
        salida = self.correr("commit", "--repo", str(self.copia), "-F", "mensaje.txt", "--", "design/", cwd=afuera)
        self.assertEqual(salida["accion"], "empujar", salida)
        self.assertEqual(git("log", "-1", "--format=%B", cwd=self.copia).stdout.strip(), self.MENSAJE)

    def test_uso_incorrecto(self):
        self.preparar()
        (self.tmp / "mensaje.txt").write_text(self.MENSAJE, encoding="utf-8")
        antes = git("rev-parse", "HEAD", cwd=self.copia).stdout
        for args in (("-F", str(self.tmp / "no-existe.txt")), ("-F", str(self.tmp / "mensaje.txt"), "-m", "x"),
                     ("-F",)):
            with self.subTest(args=args):
                self.correr("commit", *args, "--", "design/", codigo=2)
        self.assertEqual(git("rev-parse", "HEAD", cwd=self.copia).stdout, antes)

    def test_un_archivo_que_no_es_utf8_sale_con_2_sin_commit(self):
        """Q167: lo que escriben `>` y `Out-File` (UTF-16 LE con BOM) y `Set-Content` sin `-Encoding` (Latin-1) en
        PowerShell 5.1 no es UTF-8: sale con 2, no hace commit, no toca la copia y stderr dice qué pasa y cómo
        escribirlo."""
        self.preparar()
        antes = (git("rev-parse", "HEAD", cwd=self.copia).stdout, self.status(),
                 git("ls-files", "-s", cwd=self.copia).stdout)
        for nombre, contenido in (("utf-16-le", b"\xff\xfe" + self.MENSAJE.encode("utf-16-le")),
                                  ("latin-1", self.MENSAJE.encode("latin-1", errors="replace"))):
            with self.subTest(encoding=nombre):
                archivo = self.tmp / f"mensaje-{nombre}.txt"
                archivo.write_bytes(contenido)
                error = self.correr("commit", "-F", str(archivo), "--", "design/", codigo=2)
                self.assertIn("no es UTF-8", error)
                self.assertIn("herramienta de archivos", error)
                self.assertEqual((git("rev-parse", "HEAD", cwd=self.copia).stdout, self.status(),
                                  git("ls-files", "-s", cwd=self.copia).stdout), antes)

    def test_un_archivo_con_bytes_nulos_sale_con_2_sin_commit(self):
        """Q167: un mensaje con un byte nulo es UTF-8 válido pero git no lo acepta como argumento. Sale de UTF-16 sin
        BOM, como el de `UnicodeEncoding($false, $false)` de .NET, o de un archivo que no es texto."""
        self.preparar()
        antes = (git("rev-parse", "HEAD", cwd=self.copia).stdout, self.status(),
                 git("ls-files", "-s", cwd=self.copia).stdout)
        for nombre, contenido in (("utf-16-le-sin-bom", "Agrega la vista".encode("utf-16-le")),
                                  ("nulo", b"Agrega\x00 la vista")):
            with self.subTest(archivo=nombre):
                archivo = self.tmp / f"mensaje-{nombre}.txt"
                archivo.write_bytes(contenido)
                error = self.correr("commit", "-F", str(archivo), "--", "design/", codigo=2)
                self.assertIn("bytes nulos", error)
                self.assertIn("herramienta de archivos", error)
                self.assertEqual((git("rev-parse", "HEAD", cwd=self.copia).stdout, self.status(),
                                  git("ls-files", "-s", cwd=self.copia).stdout), antes)


class RutasIgnoradas(Base):
    """N1 y N2: una ruta de la skill ignorada, como el puntero que queda solo en esta máquina cuando la persona no
    acepta la excepción de Q157, no rompe `apartar`, y un cambio de rama no la pisa sin guardarla antes."""

    def ignorar(self, regla):
        self.escribir(self.otra, ".gitignore", regla)
        git("add", ".gitignore", cwd=self.otra)
        git("commit", "-q", "-m", "ignorar", cwd=self.otra)
        git("push", "-q", "origin", "HEAD:main", cwd=self.otra)
        git("pull", "-q", "--ff-only", cwd=self.copia)

    def test_n1_con_claude_ignorado_y_el_puntero_en_disco_aparta(self):
        self.ignorar(".claude/\n")
        self.escribir(self.copia, ".claude/pm-conventions.md", "puntero local\n")
        self.escribir(self.copia, "design/vistas/alertas/a.html", "<p>cambio</p>\n")
        salida = self.apartar()
        self.assertEqual((salida["accion"], salida["apartado"]), ("guardar", ["apartado/main"]), salida)
        self.assertEqual(self.archivos_de("apartado/main"), {"M", "design/vistas/alertas/a.html"})
        self.assertEqual((self.copia / ".claude/pm-conventions.md").read_text(encoding="utf-8"), "puntero local\n")
        self.assertEqual(self.ramas_locales("apartado/*"), ["apartado/main"])

    def test_n1_con_design_ignorado_aparta(self):
        self.ignorar("design/\n")
        self.escribir(self.copia, "design/vistas/alertas/a.html", "<p>cambio</p>\n")
        self.escribir(self.copia, "design/ignorado.html", "<p>ignorado</p>\n")
        salida = self.apartar()
        self.assertEqual((salida["accion"], salida["apartado"]), ("guardar", ["apartado/main"]), salida)
        self.assertEqual(self.archivos_de("apartado/main"), {"M", "design/vistas/alertas/a.html"})
        self.assertTrue((self.copia / "design/ignorado.html").is_file())

    def test_n2_volver_no_pisa_el_puntero_ignorado_que_la_principal_trae(self):
        self.ignorar(".claude/\n")
        self.trabajar_en("tickets/alertas")
        git("push", "-q", "origin", "--delete", "tickets/alertas", cwd=self.copia)
        self.escribir(self.copia, ".claude/pm-conventions.md", "puntero local\n")
        self.escribir(self.otra, ".claude/pm-conventions.md", "puntero del servidor\n")
        git("add", "-f", ".claude/pm-conventions.md", cwd=self.otra)
        git("commit", "-q", "-m", "puntero", cwd=self.otra)
        git("push", "-q", "origin", "HEAD:main", cwd=self.otra)
        orden = ("--tipo", "tickets", "--epica", "alertas")
        salida = self.parada(self.revisar(*orden), "cambios-sin-guardar")
        self.assertIn("!! .claude/pm-conventions.md", salida["archivos"])
        self.parada(self.volver(*orden), "cambios-sin-guardar")
        self.assertEqual((self.copia / ".claude/pm-conventions.md").read_text(encoding="utf-8"), "puntero local\n")
        salida = self.apartar(*orden)
        self.assertEqual((salida["accion"], salida["apartado"]), ("volver", ["apartado/tickets-alertas"]), salida)
        self.assertEqual(self.volver(*orden)["rama"], "main")
        self.assertEqual(self.contenido("apartado/tickets-alertas", ".claude/pm-conventions.md"), "puntero local\n")

    def test_n2_apartar_no_pisa_el_puntero_ignorado_de_la_rama_de_destino(self):
        self.ignorar(".claude/\n")
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.escribir(self.otra, ".claude/pm-conventions.md", "puntero del servidor\n")
        git("add", "-f", ".claude/pm-conventions.md", cwd=self.otra)
        git("commit", "-q", "-m", "puntero", cwd=self.otra)
        git("push", "-q", "origin", "HEAD:main", cwd=self.otra)
        self.escribir(self.copia, ".claude/pm-conventions.md", "puntero local\n")
        salida = self.apartar()
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"]), ("guardar", "main", ["apartado/experimento"]))
        self.assertEqual(self.contenido("apartado/experimento", ".claude/pm-conventions.md"), "puntero local\n")
        self.assertEqual(self.status(), "")

    def test_un_ignorado_igual_al_de_la_rama_de_destino_detiene_y_se_aparta(self):
        """Q175, que reemplaza lo que este test pedía antes (no detener): un ignorado igual al de la rama de destino
        está en el camino del cambio de rama, `revisar` lo lista como `!!` y `apartar` lo guarda."""
        self.ignorar(".claude/\n")
        self.trabajar_en("tickets/alertas")
        git("push", "-q", "origin", "--delete", "tickets/alertas", cwd=self.copia)
        for repo in (self.copia, self.otra):
            self.escribir(repo, ".claude/pm-conventions.md", "el mismo puntero\n")
        git("add", "-f", ".claude/pm-conventions.md", cwd=self.otra)
        git("commit", "-q", "-m", "puntero", cwd=self.otra)
        git("push", "-q", "origin", "HEAD:main", cwd=self.otra)
        salida = self.parada(self.revisar("--tipo", "tickets", "--epica", "alertas"), "cambios-sin-guardar")
        self.assertEqual(salida["archivos"], ["!! .claude/pm-conventions.md"])
        salida = self.apartar("--tipo", "tickets", "--epica", "alertas")
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"]),
                         ("volver", "tickets/alertas", ["apartado/tickets-alertas"]), salida)
        self.assertEqual(self.contenido("apartado/tickets-alertas", ".claude/pm-conventions.md"), "el mismo puntero\n")
        # El ignorado sale de la carpeta con el apartado, y `volver` trae el de la principal.
        puntero = self.copia / ".claude/pm-conventions.md"
        self.assertFalse(puntero.exists())
        self.assertEqual(self.volver("--tipo", "tickets", "--epica", "alertas")["rama"], "main")
        self.assertEqual(puntero.read_text(encoding="utf-8"), "el mismo puntero\n")


class SinSeguimientoQueChoca(Base):
    """N3: un archivo sin seguimiento fuera de las rutas que la rama de destino tiene no deja un ciclo: `revisar` lo
    nombra y `apartar` lo guarda."""

    def con_informe_en_el_servidor(self):
        self.escribir(self.otra, "informe.txt", "del servidor\n")
        git("add", "informe.txt", cwd=self.otra)
        git("commit", "-q", "-m", "informe", cwd=self.otra)
        git("push", "-q", "origin", "HEAD:main", cwd=self.otra)
        self.escribir(self.copia, "informe.txt", "local\n")

    def test_n3_con_volver(self):
        self.trabajar_en("diseno/alertas")
        git("push", "-q", "origin", "--delete", "diseno/alertas", cwd=self.copia)
        self.con_informe_en_el_servidor()
        self.assertIn("?? informe.txt", self.parada(self.revisar(), "cambios-sin-guardar")["archivos"])
        salida = self.apartar()
        self.assertEqual((salida["accion"], salida["apartado"]), ("volver", ["apartado/diseno-alertas"]), salida)
        self.assertEqual(self.volver()["rama"], "main")
        self.assertEqual(self.contenido("apartado/diseno-alertas", "informe.txt"), "local\n")

    def test_n3_desde_otra_rama(self):
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.con_informe_en_el_servidor()
        self.assertIn("?? informe.txt", self.parada(self.revisar(), "otra-rama")["archivos"])
        salida = self.apartar()
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"]), ("guardar", "main", ["apartado/experimento"]), salida)
        self.assertEqual(self.contenido("apartado/experimento", "informe.txt"), "local\n")

    def test_un_sin_seguimiento_que_la_rama_de_destino_no_tiene_se_queda(self):
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.escribir(self.copia, "informe.txt", "local\n")
        salida = self.apartar()
        self.assertEqual((salida["accion"], salida["apartado"]), ("guardar", []))
        self.assertEqual(self.status(), "?? informe.txt\n")

    def test_un_sin_seguimiento_igual_al_de_la_principal_no_deja_apartar_a_medias(self):
        """Q168: `git switch` no deja pasar un archivo sin seguimiento que la rama de destino tiene aunque el contenido
        sea idéntico. `revisar` lo nombra y `apartar` lo guarda y termina en la principal, en lugar de quedar en
        `apartado/otra` con `error-de-git`."""
        git("switch", "-q", "-c", "otra", cwd=self.copia)
        self.escribir(self.copia, "notas.txt", "cambio local\n")
        for repo in (self.otra, self.copia):
            self.escribir(repo, "doc/nuevo.md", "# Nuevo\n")
        git("add", "doc/nuevo.md", cwd=self.otra)
        git("commit", "-q", "-m", "nuevo", cwd=self.otra)
        git("push", "-q", "origin", "HEAD:main", cwd=self.otra)
        archivos = self.parada(self.revisar(), "otra-rama")["archivos"]
        self.assertEqual(sorted(archivos), [" M notas.txt", "?? doc/nuevo.md"])
        salida = self.apartar()
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"], salida["desde"]),
                         ("guardar", "main", ["apartado/otra"], "otra"), salida)
        self.assertEqual(self.status(), "")
        self.assertTrue(self.igual_al_servidor())
        self.assertEqual(self.contenido("apartado/otra", "notas.txt"), "cambio local\n")
        self.assertEqual((self.copia / "doc/nuevo.md").read_text(encoding="utf-8"), "# Nuevo\n")
        self.assertEqual(self.revisar()["accion"], "guardar")

    def con_el_mismo_archivo_que_trae_la_principal(self):
        for repo in (self.otra, self.copia):
            self.escribir(repo, "doc/nuevo.md", "# Nuevo\n")
        git("add", "doc/nuevo.md", cwd=self.otra)
        git("commit", "-q", "-m", "nuevo", cwd=self.otra)
        git("push", "-q", "origin", "HEAD:main", cwd=self.otra)

    def test_volver_con_un_sin_seguimiento_igual_al_de_la_principal(self):
        """Q168 y Q169: `volver` cambia a la principal, que no deja pasar el archivo igual. `revisar` lo nombra,
        `apartar` lo guarda y `volver` termina en la principal, en lugar de un ciclo de `cambios-sin-guardar`."""
        self.trabajar_en("diseno/alertas")
        git("push", "-q", "origin", "--delete", "diseno/alertas", cwd=self.copia)
        self.con_el_mismo_archivo_que_trae_la_principal()
        self.assertEqual(self.parada(self.revisar(), "cambios-sin-guardar")["archivos"], ["?? doc/nuevo.md"])
        salida = self.apartar()
        self.assertEqual((salida["accion"], salida["apartado"]), ("volver", ["apartado/diseno-alertas"]), salida)
        self.assertEqual(self.volver(), {"accion": "guardar", "rama": "main", "principal": "main"})
        self.assertEqual((self.status(), (self.copia / "doc/nuevo.md").read_text(encoding="utf-8")), ("", "# Nuevo\n"))

    def test_ofrecer_con_un_sin_seguimiento_igual_al_de_la_principal(self):
        """Q168 y Q169: lo mismo con `ofrecer`, que cambia a la rama nueva desde la principal."""
        self.trabajar_en("diseno/alertas")
        self.con_el_mismo_archivo_que_trae_la_principal()
        self.assertEqual(self.parada(self.revisar(*MOCKUP), "cambios-sin-guardar")["archivos"], ["?? doc/nuevo.md"])
        salida = self.apartar(*MOCKUP)
        self.assertEqual((salida["accion"], salida["rama_nueva"], salida["apartado"]),
                         ("ofrecer", "diseno/panel", ["apartado/diseno-alertas"]), salida)
        self.assertEqual(self.volver(*MOCKUP, "--rama-nueva", "diseno/panel"),
                         {"accion": "guardar", "rama": "diseno/panel", "principal": "main"})
        self.assertEqual((self.status(), (self.copia / "doc/nuevo.md").read_text(encoding="utf-8")), ("", "# Nuevo\n"))

    def test_un_archivo_sacado_del_indice_igual_al_de_la_principal_no_deja_apartar_a_medias(self):
        """Q168, con `git rm --cached`: el borrado preparado queda en el primer commit del apartado y el archivo, que
        la principal tiene igual, no frena el cambio de rama."""
        git("switch", "-q", "-c", "otra", cwd=self.copia)
        git("rm", "-q", "--cached", "notas.txt", cwd=self.copia)
        self.assertIn("?? notas.txt", self.parada(self.revisar(), "otra-rama")["archivos"])
        salida = self.apartar()
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"]), ("guardar", "main", ["apartado/otra"]),
                         salida)
        self.assertEqual(self.status(), "")
        self.assertEqual(self.archivos_de("apartado/otra~1"), {"D", "notas.txt"})
        self.assertEqual((self.copia / "notas.txt").read_text(encoding="utf-8"), "notas\n")


class RamaDelFlujoSinUpstream(Base):
    """N4: una rama del flujo que está en el servidor pero no lo sigue queda siguiéndolo después de `apartar`."""

    def test_n4_sin_upstream(self):
        git("switch", "-q", "-c", "spec/alertas", cwd=self.copia)
        git("push", "-q", "origin", "spec/alertas", cwd=self.copia)
        orden = ("--tipo", "spec", "--epica", "alertas")
        salida = self.parada(self.revisar(*orden), "otra-rama")
        self.assertIn("no sigue", salida["detalle"])
        salida = self.apartar(*orden)
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"]), ("guardar", "spec/alertas", []), salida)
        self.assertEqual(git("rev-parse", "--abbrev-ref", "spec/alertas@{upstream}", cwd=self.copia).stdout.strip(),
                         "origin/spec/alertas")

    def test_n4_siguiendo_a_otra_rama(self):
        git("switch", "-q", "-c", "spec/alertas", "origin/main", cwd=self.copia)
        git("push", "-q", "origin", "spec/alertas", cwd=self.copia)
        orden = ("--tipo", "spec", "--epica", "alertas")
        self.parada(self.revisar(*orden), "otra-rama")
        self.assertEqual(self.apartar(*orden)["accion"], "guardar")

    def test_n4_con_commits_que_el_servidor_no_tiene_los_aparta(self):
        git("switch", "-q", "-c", "spec/alertas", cwd=self.copia)
        git("push", "-q", "origin", "spec/alertas", cwd=self.copia)
        self.escribir(self.copia, "specs/alertas/spec.md", "# local\n")
        git("commit", "-q", "-am", "commit local", cwd=self.copia)
        orden = ("--tipo", "spec", "--epica", "alertas")
        salida = self.apartar(*orden)
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"]),
                         ("guardar", "spec/alertas", ["apartado/spec-alertas"]), salida)
        self.assertTrue(self.igual_al_servidor("spec/alertas"))
        self.assertIn("commit local", git("log", "--format=%s", "apartado/spec-alertas", cwd=self.copia).stdout)


class CommitDeLosArchivosDeLaSkill(Base):
    """N5 y Q160: la skill pasa a `commit` los archivos que escribió; si uno no está y no cambió, porque otra sesión
    lo apartó o lo guardó, `commit` para con su motivo y no dice `sin-cambios`. N6: con `--repo`, desde otra carpeta."""

    def test_n5_un_archivo_de_la_skill_que_ya_no_esta(self):
        self.escribir(self.copia, "design/vistas/alertas/b.html", "<p>b</p>\n")
        git("add", "design/vistas/alertas/b.html", cwd=self.copia)
        salida = self.parada(self.commit("-m", "x", "--", "design/vistas/alertas/nueva.html",
                                         "design/vistas/alertas/b.html"), "ruta-que-falta")
        self.assertEqual(salida["rutas"], ["design/vistas/alertas/nueva.html"])
        self.assertEqual(git("log", "-1", "--format=%s", cwd=self.copia).stdout.strip(), "inicio")

    def test_n5_un_archivo_borrado_por_la_skill_si_cambio(self):
        git("rm", "-q", "specs/alertas/spec.md", cwd=self.copia)
        self.assertEqual(self.commit("-m", "x", "--", "specs/alertas/spec.md")["accion"], "empujar")

    def test_n6_con_repo_desde_otra_carpeta(self):
        afuera = self.tmp / "afuera"
        git("init", "-q", str(afuera), cwd=self.tmp)
        self.escribir(self.copia, "design/vistas/alertas/nueva.html", "<p>nueva</p>\n")
        git("add", "design/", cwd=self.copia)
        salida = self.correr("commit", "--repo", str(self.copia), "-m", "x", "--", "design/vistas/alertas/nueva.html",
                             cwd=afuera)
        self.assertEqual(salida["accion"], "empujar")


class Detalles(Base):
    def test_n9_las_rutas_con_tildes_salen_legibles(self):
        self.escribir(self.copia, "design/señales/vista ñ.html", "<p>x</p>\n")
        self.assertIn("?? design/señales/vista ñ.html", self.parada(self.revisar(), "cambios-sin-guardar")["archivos"])

    def test_n10_un_servidor_que_no_responde_para_con_sin_servidor(self):
        lento = self.tmp / "lento.sh"
        lento.write_text("#!/bin/sh\nsleep 30\n", encoding="utf-8")
        lento.chmod(0o755)
        git("config", "remote.origin.uploadpack", str(lento), cwd=self.copia)
        antes = self.status(), self.rama_actual()
        for orden in ("revisar", "apartar"):
            with self.subTest(orden=orden):
                salida = self.correr(orden, *EPICA, entorno={"RAMA_TOPE": "2"}, tope=20)
                self.parada(salida, "sin-servidor")
                self.assertEqual((self.status(), self.rama_actual()), antes)

    def test_n11_un_error_de_git_al_apartar_no_deja_un_apartado_vacio(self):
        for clave in ("user.name", "user.email"):
            git("config", "--unset", clave, cwd=self.copia)
        git("config", "user.useConfigOnly", "true", cwd=self.copia)
        self.escribir(self.copia, "design/vistas/alertas/a.html", "<p>cambio</p>\n")
        git("add", "design/", cwd=self.copia)
        salida = self.parada(self.apartar(), "error-de-git")
        self.assertEqual((salida["apartado"], salida["desde"]), ([], "main"))
        self.assertEqual(self.rama_actual(), "main")
        self.assertEqual(self.ramas_locales("apartado/*"), [])
        self.assertEqual(self.status(), "M  design/vistas/alertas/a.html\n")
        git("config", "user.name", "producto", cwd=self.copia)
        git("config", "user.email", "producto@example.com", cwd=self.copia)
        salida = self.apartar()
        self.assertEqual((salida["accion"], salida["apartado"], salida["desde"]), ("guardar", ["apartado/main"], "main"))


class LlegadaALaRamaLocal(Base):
    """M1: `apartar` mira los archivos sin seguimiento contra la rama a la que cambia de verdad: la local del flujo,
    si tiene un commit que no llegó al servidor, no la del servidor."""

    def rama_local_adelantada(self, ruta, texto, forzar=False):
        self.trabajar_en("tickets/alertas")
        self.escribir(self.copia, ruta, texto)
        git("add", *(("-f",) if forzar else ()), ruta, cwd=self.copia)
        git("commit", "-q", "-m", "commit sin push", cwd=self.copia)
        git("switch", "-q", "-c", "experimento", "origin/main", cwd=self.copia)

    def test_m1_un_ignorado_que_solo_la_rama_local_tiene_se_aparta(self):
        self.escribir(self.otra, ".gitignore", ".claude/\n")
        git("add", ".gitignore", cwd=self.otra)
        git("commit", "-q", "-m", "ignorar", cwd=self.otra)
        git("push", "-q", "origin", "HEAD:main", cwd=self.otra)
        git("pull", "-q", "--ff-only", cwd=self.copia)
        self.rama_local_adelantada(".claude/pm-conventions.md", "puntero en la rama\n", forzar=True)
        self.escribir(self.copia, ".claude/pm-conventions.md", "puntero local\n")
        orden = ("--tipo", "tickets", "--epica", "alertas")
        self.assertIn("!! .claude/pm-conventions.md", self.parada(self.revisar(*orden), "otra-rama")["archivos"])
        salida = self.apartar(*orden)
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"]),
                         ("guardar", "tickets/alertas", ["apartado/experimento"]), salida)
        self.assertEqual(self.contenido("apartado/experimento", ".claude/pm-conventions.md"), "puntero local\n")

    def test_m1_un_sin_seguimiento_que_solo_la_rama_local_tiene_no_deja_un_ciclo(self):
        self.rama_local_adelantada("informe.txt", "de la rama\n")
        self.escribir(self.copia, "informe.txt", "local\n")
        orden = ("--tipo", "tickets", "--epica", "alertas")
        salida = self.apartar(*orden)
        self.assertEqual((salida["accion"], salida["rama"], salida["apartado"]),
                         ("guardar", "tickets/alertas", ["apartado/experimento"]), salida)
        self.assertEqual(self.contenido("apartado/experimento", "informe.txt"), "local\n")


class IndiceTalCual(Base):
    """B1: si el commit del apartado falla, el índice queda como estaba, también sin nada preparado, y el apartado
    de después no dice que el script preparó lo que la persona no preparó."""

    def sin_identidad(self):
        for clave in ("user.name", "user.email"):
            git("config", "--unset", clave, cwd=self.copia)
        git("config", "user.useConfigOnly", "true", cwd=self.copia)

    def test_b1_sin_nada_preparado(self):
        self.sin_identidad()
        self.escribir(self.copia, "design/vistas/alertas/a.html", "<p>cambio</p>\n")
        self.escribir(self.copia, "design/nueva.html", "<p>nueva</p>\n")
        antes = self.status()
        salida = self.parada(self.apartar(), "error-de-git")
        self.assertEqual((salida["apartado"], self.rama_actual(), self.status()), ([], "main", antes))
        git("config", "user.name", "producto", cwd=self.copia)
        git("config", "user.email", "producto@example.com", cwd=self.copia)
        self.assertEqual(self.apartar()["apartado"], ["apartado/main"])
        self.assertEqual(git("log", "--format=%s", "origin/main..apartado/main", cwd=self.copia).stdout,
                         "Apartado: lo que había en main antes de guardar\n")

    def test_b1_con_un_ignorado_que_el_cambio_de_rama_pisaria(self):
        self.escribir(self.otra, ".claude/pm-conventions.md", "del servidor\n")
        self.escribir(self.otra, ".gitignore", ".claude/\n")
        git("add", "-f", ".gitignore", ".claude/pm-conventions.md", cwd=self.otra)
        git("commit", "-q", "-m", "puntero", cwd=self.otra)
        git("push", "-q", "origin", "HEAD:main", cwd=self.otra)
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.escribir(self.copia, ".gitignore", ".claude/\n")
        self.escribir(self.copia, ".claude/pm-conventions.md", "local\n")
        self.sin_identidad()
        antes = self.status()
        self.parada(self.apartar(), "error-de-git")
        self.assertEqual((self.rama_actual(), self.status()), ("experimento", antes))


    def test_b4_vuelve_la_marca_de_add_n(self):
        self.sin_identidad()
        self.escribir(self.copia, "design/nueva.html", "<p>nueva</p>\n")
        git("add", "-N", "design/nueva.html", cwd=self.copia)
        antes = self.status()
        self.parada(self.apartar(), "error-de-git")
        self.assertEqual((self.rama_actual(), self.status()), ("main", antes))
        self.assertEqual(antes, " A design/nueva.html\n")

    def test_b4_vuelve_skip_worktree_del_sparse_checkout(self):
        self.escribir(self.otra, "otros/o.txt", "otro\n")
        git("add", "otros/o.txt", cwd=self.otra)
        git("commit", "-q", "-m", "otros", cwd=self.otra)
        git("push", "-q", "origin", "HEAD:main", cwd=self.otra)
        git("pull", "-q", "--ff-only", cwd=self.copia)
        git("sparse-checkout", "set", "design", "specs", cwd=self.copia)
        self.assertTrue(git("ls-files", "-v", "otros/o.txt", cwd=self.copia).stdout.startswith("S "))
        self.sin_identidad()
        self.escribir(self.copia, "design/vistas/alertas/a.html", "<p>cambio</p>\n")
        antes = self.status()
        self.parada(self.apartar(), "error-de-git")
        self.assertEqual(self.status(), antes)
        self.assertTrue(git("ls-files", "-v", "otros/o.txt", cwd=self.copia).stdout.startswith("S "))


class RenombradoEnLaCarpeta(Base):
    def test_b3_un_renombrado_en_la_segunda_columna_es_una_linea(self):
        (self.copia / "design/vistas/alertas/a.html").rename(self.copia / "design/vistas/alertas/movido.html")
        git("add", "-N", "design/vistas/alertas/movido.html", cwd=self.copia)
        archivos = self.parada(self.revisar(), "cambios-sin-guardar")["archivos"]
        self.assertEqual(archivos, [" R design/vistas/alertas/a.html -> design/vistas/alertas/movido.html"])


if __name__ == "__main__":
    unittest.main()
