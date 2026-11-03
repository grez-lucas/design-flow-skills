"""Pruebas de scripts/rama.py, la decisión de la rama antes de guardar, contra repositorios git reales.

Cada prueba arma un servidor (repositorio bare con un hook `pre-receive` que simula la protección), una copia de quien
usa la skill y, si hace falta, otra copia de alguien más. Las cuatro copias de rama.py son iguales (tests/repositorio).
Uso: python3 -m unittest discover -s tests/rama -v
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "skills" / "grilling-es" / "scripts" / "rama.py"

# Sin la configuración global ni la del sistema, para que local y CI corran igual.
ENTORNO = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}

# Rechaza cualquier ref listada en el archivo `protegidas` del servidor, como una rama protegida.
HOOK = """#!/bin/sh
while read viejo nuevo ref; do
  if grep -qxF "$ref" protegidas 2>/dev/null; then
    echo "rama protegida: $ref" >&2
    exit 1
  fi
done
"""


def git(*args, cwd, check=True):
    return subprocess.run(["git", "-c", "user.name=prueba", "-c", "user.email=prueba@example.com", *args],
                          cwd=cwd, env=ENTORNO, check=check, capture_output=True, text=True, encoding="utf-8")


class Base(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.servidor = self.tmp / "servidor.git"
        self.otra = self.tmp / "otra"
        self.copia = self.tmp / "copia"
        git("init", "-q", "--bare", "--initial-branch=main", str(self.servidor), cwd=self.tmp)
        hook = self.servidor / "hooks" / "pre-receive"
        hook.write_text(HOOK, encoding="utf-8")
        hook.chmod(0o755)
        git("clone", "-q", str(self.servidor), str(self.otra), cwd=self.tmp)
        self.commit(self.otra, "inicio")
        git("push", "-q", "origin", "HEAD:main", cwd=self.otra)
        git("clone", "-q", str(self.servidor), str(self.copia), cwd=self.tmp)

    def commit(self, repo, nombre):
        (Path(repo) / f"{nombre}.md").write_text(nombre, encoding="utf-8")
        git("add", f"{nombre}.md", cwd=repo)
        git("commit", "-q", "-m", nombre, cwd=repo)

    def en_el_servidor(self, *ramas):
        """Crea las ramas en el servidor desde la otra copia, sin que la copia de quien usa la skill las vea."""
        for rama in ramas:
            git("push", "-q", "origin", f"HEAD:refs/heads/{rama}", cwd=self.otra)

    def borrar_del_servidor(self, rama):
        git("push", "-q", "origin", "--delete", rama, cwd=self.otra)

    def trabajar_en(self, rama):
        """La copia de quien usa la skill en `rama`, publicada en el servidor y con upstream."""
        git("switch", "-q", "-c", rama, cwd=self.copia)
        git("push", "-q", "-u", "origin", rama, cwd=self.copia)

    def proteger(self, *ramas):
        with (self.servidor / "protegidas").open("a", encoding="utf-8") as f:
            for rama in ramas:
                f.write(f"refs/heads/{rama}\n")

    def rama(self, *args, cwd=None):
        resultado = subprocess.run([sys.executable, "-B", str(SCRIPT), *args], cwd=cwd or self.copia, env=ENTORNO,
                                   capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        return json.loads(resultado.stdout)

    def revisar(self, tipo, epica, cwd=None):
        return self.rama("revisar", "--tipo", tipo, "--epica", epica, cwd=cwd)

    def rama_actual(self):
        return git("branch", "--show-current", cwd=self.copia).stdout.strip()

    def estado(self):
        """Lo que el script no puede tocar: la rama, las ramas locales y el árbol."""
        return (self.rama_actual(),
                git("for-each-ref", "--format=%(refname) %(objectname)", "refs/heads", cwd=self.copia).stdout,
                git("status", "--porcelain", cwd=self.copia).stdout)


class AntesDeEscribir(Base):
    """Q90: fetch, guardar en la principal o en la rama viva de la épica, volver si el upstream se borró sin
    commits pendientes, parar en cualquier otro caso."""

    def test_en_la_principal_guarda_ahi(self):
        self.assertEqual(self.revisar("spec", "riego"), {"accion": "guardar", "rama": "main"})

    def test_la_principal_es_la_del_servidor_aunque_no_se_llame_main(self):
        git("push", "-q", "origin", "HEAD:refs/heads/trunk", cwd=self.otra)
        git("symbolic-ref", "HEAD", "refs/heads/trunk", cwd=self.servidor)
        git("fetch", "-q", cwd=self.copia)
        git("switch", "-q", "trunk", cwd=self.copia)
        self.assertEqual(self.revisar("spec", "riego"), {"accion": "guardar", "rama": "trunk"})
        git("switch", "-q", "main", cwd=self.copia)
        self.assertEqual(self.revisar("spec", "riego")["motivo"], "otra-rama")

    def test_en_la_rama_viva_de_la_misma_epica_guarda_ahi(self):
        self.trabajar_en("spec/riego")
        self.assertEqual(self.revisar("spec", "riego"), {"accion": "guardar", "rama": "spec/riego"})

    def test_rama_borrada_en_el_servidor_sin_commits_pendientes_vuelve_a_la_principal(self):
        self.trabajar_en("spec/riego")
        self.borrar_del_servidor("spec/riego")
        self.assertEqual(self.revisar("spec", "riego"), {"accion": "volver", "rama": "spec/riego", "principal": "main"})

    def test_rama_borrada_tras_un_merge_y_la_copia_podada_vuelve_igual(self):
        """Con `fetch.prune` el upstream desaparece de la copia; los commits siguen en la principal del servidor."""
        self.trabajar_en("diseno/riego")
        self.commit(self.copia, "vista")
        git("push", "-q", cwd=self.copia)
        git("fetch", "-q", cwd=self.otra)
        git("merge", "-q", "--no-ff", "-m", "merge", "origin/diseno/riego", cwd=self.otra)
        git("push", "-q", "origin", "HEAD:main", cwd=self.otra)
        self.borrar_del_servidor("diseno/riego")
        git("fetch", "-q", "--prune", cwd=self.copia)
        self.assertEqual(self.revisar("diseno", "riego")["accion"], "volver")

    def test_rama_borrada_en_el_servidor_con_commits_pendientes_para(self):
        self.trabajar_en("spec/riego")
        self.commit(self.copia, "sin-empujar")
        self.borrar_del_servidor("spec/riego")
        resultado = self.revisar("spec", "riego")
        self.assertEqual((resultado["accion"], resultado["motivo"]), ("parar", "commits-sin-empujar"))
        self.assertEqual(resultado["rama"], "spec/riego")
        self.assertTrue(resultado["detalle"])

    def test_rama_borrada_y_podada_con_commits_que_no_estan_en_el_servidor_para(self):
        self.trabajar_en("spec/riego")
        self.commit(self.copia, "empujado")
        git("push", "-q", cwd=self.copia)
        self.commit(self.copia, "sin-empujar")
        self.borrar_del_servidor("spec/riego")
        git("fetch", "-q", "--prune", cwd=self.copia)
        self.assertEqual(self.revisar("spec", "riego")["motivo"], "commits-sin-empujar")

    def test_rama_local_sin_upstream_para(self):
        git("switch", "-q", "-c", "spec/riego", cwd=self.copia)
        resultado = self.revisar("spec", "riego")
        self.assertEqual((resultado["accion"], resultado["motivo"]), ("parar", "otra-rama"))

    def test_en_otra_rama_viva_para(self):
        self.trabajar_en("arreglo-menu")
        resultado = self.revisar("spec", "riego")
        self.assertEqual((resultado["accion"], resultado["motivo"], resultado["rama"]), ("parar", "otra-rama", "arreglo-menu"))

    def test_sin_rama_para(self):
        git("switch", "-q", "--detach", cwd=self.copia)
        resultado = self.revisar("spec", "riego")
        self.assertEqual((resultado["accion"], resultado["motivo"]), ("parar", "sin-rama"))

    def test_sin_conexion_al_servidor_para(self):
        git("remote", "set-url", "origin", str(self.tmp / "no-existe.git"), cwd=self.copia)
        resultado = self.revisar("spec", "riego")
        self.assertEqual((resultado["accion"], resultado["motivo"]), ("parar", "sin-servidor"))
        self.assertTrue(resultado["detalle"])

    def test_sin_origin_para(self):
        git("remote", "remove", "origin", cwd=self.copia)
        self.assertEqual(self.revisar("spec", "riego")["motivo"], "sin-servidor")

    def test_si_el_servidor_no_dice_su_rama_principal_para(self):
        git("symbolic-ref", "HEAD", "refs/heads/no-existe", cwd=self.servidor)
        self.assertEqual(self.revisar("spec", "riego")["motivo"], "sin-principal")

    def test_trae_lo_nuevo_del_servidor(self):
        self.en_el_servidor("diseno/riego")
        self.revisar("spec", "riego")
        self.assertIn("origin/diseno/riego", git("branch", "-r", cwd=self.copia).stdout)

    def test_no_cambia_de_rama_ni_toca_el_arbol(self):
        self.trabajar_en("spec/riego")
        (self.copia / "inicio.md").write_text("cambio", encoding="utf-8")
        self.borrar_del_servidor("spec/riego")
        antes = self.estado()
        self.assertEqual(self.revisar("spec", "riego")["accion"], "volver")
        self.assertEqual(self.estado(), antes)

    def test_corre_desde_otra_carpeta_con_repo(self):
        resultado = self.rama("revisar", "--tipo", "spec", "--epica", "riego", "--repo", str(self.copia), cwd=self.tmp)
        self.assertEqual(resultado, {"accion": "guardar", "rama": "main"})


class RamasDelFlujoDeLaMismaEpica(Base):
    """Q96: `spec/`, `tickets/` o `diseno/` de la misma épica, con o sin sufijo, con upstream vivo."""

    def test_guarda_en_cualquier_rama_del_flujo_de_la_epica(self):
        for rama in ("spec/riego", "tickets/riego", "diseno/riego", "spec/riego-2", "diseno/riego-12"):
            for tipo in ("spec", "tickets", "diseno"):
                with self.subTest(rama=rama, tipo=tipo):
                    git("switch", "-q", "main", cwd=self.copia)
                    if not git("rev-parse", "--verify", "--quiet", rama, cwd=self.copia, check=False).stdout:
                        self.trabajar_en(rama)
                    git("switch", "-q", rama, cwd=self.copia)
                    self.assertEqual(self.revisar(tipo, "riego"), {"accion": "guardar", "rama": rama})

    def test_un_prefijo_comun_no_es_la_misma_epica(self):
        for rama in ("diseno/riegos", "diseno/riego-norte", "diseno/riego-1", "diseno/riego-02", "riego", "spec/riego/x"):
            with self.subTest(rama=rama):
                git("switch", "-q", "main", cwd=self.copia)
                self.trabajar_en(rama)
                resultado = self.revisar("diseno", "riego")
                self.assertEqual((resultado["accion"], resultado["motivo"]), ("parar", "otra-rama"))

    def test_la_rama_de_otra_epica_para(self):
        self.trabajar_en("tickets/cosechas")
        self.assertEqual(self.revisar("tickets", "riego")["motivo"], "otra-rama")

    def test_epica_con_tilde(self):
        self.trabajar_en("tickets/señales-de-riego")
        self.assertEqual(self.revisar("diseno", "señales-de-riego"),
                         {"accion": "guardar", "rama": "tickets/señales-de-riego"})
        self.assertEqual(self.revisar("diseno", "senales-de-riego")["motivo"], "otra-rama")


class RamaNuevaTrasUnRechazo(Base):
    """Q86 y Q91: si el servidor rechaza el push a la rama actual, `<tipo>/<épica>` o el primer sufijo libre."""

    def rechazo(self, tipo, epica):
        return self.rama("rechazo", "--tipo", tipo, "--epica", epica)

    def empujar_rechazado(self):
        """Un commit nuevo en la rama actual que el servidor no acepta."""
        self.commit(self.copia, "trabajo")
        empuje = git("push", "-q", cwd=self.copia, check=False)
        self.assertNotEqual(empuje.returncode, 0, "el servidor aceptó el push")

    def test_principal_protegida_da_tipo_epica(self):
        self.proteger("main")
        self.empujar_rechazado()
        self.assertEqual(self.rechazo("spec", "riego"), {"accion": "rama-nueva", "rama": "main", "rama_nueva": "spec/riego"})

    def test_rama_viva_con_cambios_que_la_copia_no_tiene(self):
        self.trabajar_en("spec/riego")
        git("fetch", "-q", cwd=self.otra)
        git("switch", "-q", "spec/riego", cwd=self.otra)
        self.commit(self.otra, "de-otra-persona")
        git("push", "-q", cwd=self.otra)
        self.empujar_rechazado()
        self.assertEqual(self.rechazo("tickets", "riego"),
                         {"accion": "rama-nueva", "rama": "spec/riego", "rama_nueva": "tickets/riego"})

    def test_ocupada_en_local(self):
        self.proteger("main")
        git("branch", "spec/riego", cwd=self.copia)
        self.empujar_rechazado()
        self.assertEqual(self.rechazo("spec", "riego")["rama_nueva"], "spec/riego-2")

    def test_ocupada_solo_en_el_servidor(self):
        self.proteger("main")
        self.en_el_servidor("spec/riego")
        self.empujar_rechazado()
        self.assertNotIn("origin/spec/riego", git("branch", "-a", cwd=self.copia).stdout)
        self.assertEqual(self.rechazo("spec", "riego")["rama_nueva"], "spec/riego-2")

    def test_primer_sufijo_libre_entre_local_y_servidor(self):
        self.proteger("main")
        self.en_el_servidor("diseno/riego", "diseno/riego-3")
        git("branch", "diseno/riego-2", cwd=self.copia)
        self.empujar_rechazado()
        self.assertEqual(self.rechazo("diseno", "riego")["rama_nueva"], "diseno/riego-4")

    def test_un_hueco_en_los_sufijos_se_usa(self):
        self.proteger("main")
        self.en_el_servidor("diseno/riego", "diseno/riego-3")
        self.empujar_rechazado()
        self.assertEqual(self.rechazo("diseno", "riego")["rama_nueva"], "diseno/riego-2")

    def test_un_prefijo_comun_no_ocupa_el_nombre(self):
        self.proteger("main")
        self.en_el_servidor("spec/riegos", "spec/riegos-2")
        git("branch", "spec/riego-norte", cwd=self.copia)
        self.empujar_rechazado()
        self.assertEqual(self.rechazo("spec", "riego")["rama_nueva"], "spec/riego")

    def test_otro_tipo_no_ocupa_el_nombre(self):
        self.proteger("main")
        self.en_el_servidor("spec/riego")
        self.empujar_rechazado()
        self.assertEqual(self.rechazo("tickets", "riego")["rama_nueva"], "tickets/riego")

    def test_epica_con_tilde(self):
        self.proteger("main")
        self.en_el_servidor("diseno/señales")
        self.empujar_rechazado()
        self.assertEqual(self.rechazo("diseno", "señales")["rama_nueva"], "diseno/señales-2")

    def test_la_rama_nueva_se_puede_crear_y_empujar(self):
        self.proteger("main")
        self.en_el_servidor("spec/riego")
        self.empujar_rechazado()
        antes = self.estado()
        nueva = self.rechazo("spec", "riego")["rama_nueva"]
        self.assertEqual(self.estado(), antes)
        git("switch", "-q", "-c", nueva, cwd=self.copia)
        git("push", "-q", "-u", "origin", nueva, cwd=self.copia)
        git("branch", "-f", "main", "origin/main", cwd=self.copia)
        self.assertIn(f"refs/heads/{nueva}", git("ls-remote", "--heads", "origin", cwd=self.copia).stdout)


class VariasEpicas(Base):
    """Q92 y Q97: un mockup de varias épicas se guarda en la principal o en `diseno/<mockup>`, nunca en la rama de
    una sola de ellas: ahí ofrece volver a la principal y `diseno/<mockup>`, si el árbol no tiene cambios."""

    def revisar_varias(self, mockup="panel-general", epicas="riego,cosechas"):
        return self.rama("revisar", "--tipo", "diseno", "--mockup", mockup, "--epicas", epicas)

    def test_en_la_principal_guarda_ahi(self):
        self.assertEqual(self.revisar_varias(), {"accion": "guardar", "rama": "main"})

    def test_en_diseno_mockup_vivo_guarda_ahi(self):
        for rama in ("diseno/panel-general", "diseno/panel-general-2"):
            with self.subTest(rama=rama):
                git("switch", "-q", "main", cwd=self.copia)
                self.trabajar_en(rama)
                self.assertEqual(self.revisar_varias(), {"accion": "guardar", "rama": rama})

    def test_solo_diseno_mockup_es_la_rama_del_flujo_del_mockup(self):
        self.trabajar_en("spec/panel-general")
        self.assertEqual(self.revisar_varias()["motivo"], "otra-rama")

    def test_en_la_rama_de_una_sola_epica_ofrece_la_principal_y_diseno_mockup(self):
        for rama in ("spec/riego", "tickets/cosechas", "diseno/riego-2"):
            with self.subTest(rama=rama):
                git("switch", "-q", "main", cwd=self.copia)
                self.trabajar_en(rama)
                antes = self.estado()
                self.assertEqual(self.revisar_varias(), {"accion": "ofrecer", "rama": rama, "principal": "main",
                                                         "rama_nueva": "diseno/panel-general"})
                self.assertEqual(self.estado(), antes)

    def test_ofrece_el_primer_sufijo_libre_de_diseno_mockup(self):
        self.en_el_servidor("diseno/panel-general")
        git("branch", "diseno/panel-general-2", cwd=self.copia)
        self.trabajar_en("spec/riego")
        self.assertEqual(self.revisar_varias()["rama_nueva"], "diseno/panel-general-3")

    def test_gana_aunque_el_mockup_se_llame_como_la_epica(self):
        self.trabajar_en("diseno/riego")
        self.assertEqual(self.revisar_varias(mockup="riego"),
                         {"accion": "ofrecer", "rama": "diseno/riego", "principal": "main", "rama_nueva": "diseno/riego-2"})

    def test_con_cambios_sin_guardar_solo_explica(self):
        self.trabajar_en("spec/riego")
        (self.copia / "inicio.md").write_text("cambio", encoding="utf-8")
        resultado = self.revisar_varias()
        self.assertEqual((resultado["accion"], resultado["motivo"], resultado["rama"]),
                         ("parar", "cambios-sin-guardar", "spec/riego"))
        git("add", "inicio.md", cwd=self.copia)
        self.assertEqual(self.revisar_varias()["motivo"], "cambios-sin-guardar")

    def test_lo_que_no_tiene_seguimiento_no_cuenta_como_cambio(self):
        """`npx skills` y el mockup dejan archivos sin seguimiento en la copia."""
        self.trabajar_en("spec/riego")
        (self.copia / "skills-lock.json").write_text("{}", encoding="utf-8")
        (self.copia / "panel-general.html").write_text("<html></html>", encoding="utf-8")
        self.assertEqual(self.revisar_varias()["accion"], "ofrecer")

    def test_la_rama_de_una_sola_epica_borrada_vuelve_a_la_principal(self):
        self.trabajar_en("spec/riego")
        self.borrar_del_servidor("spec/riego")
        self.assertEqual(self.revisar_varias(), {"accion": "volver", "rama": "spec/riego", "principal": "main"})

    def test_la_rama_de_una_epica_que_no_es_del_mockup_para(self):
        self.trabajar_en("diseno/semilla")
        self.assertEqual(self.revisar_varias()["motivo"], "otra-rama")

    def test_con_una_sola_epica_guarda_en_su_rama(self):
        self.trabajar_en("spec/riego")
        self.assertEqual(self.revisar("diseno", "riego"), {"accion": "guardar", "rama": "spec/riego"})

    def test_el_rechazo_da_diseno_mockup(self):
        self.trabajar_en("diseno/panel-general")
        self.proteger("diseno/panel-general")
        self.commit(self.copia, "vistas")
        self.assertNotEqual(git("push", "-q", cwd=self.copia, check=False).returncode, 0)
        self.assertEqual(self.rama("rechazo", "--tipo", "diseno", "--mockup", "panel-general"),
                         {"accion": "rama-nueva", "rama": "diseno/panel-general", "rama_nueva": "diseno/panel-general-2"})


class RechazoDeLaRamaNueva(Base):
    """Q90 y Q98: si el servidor rechaza también la rama nueva, o la `diseno/<mockup>` creada tras el sí, para sin
    probar otro sufijo."""

    def test_rechazo_de_diseno_mockup_creada_tras_el_si_para(self):
        self.trabajar_en("spec/riego")
        oferta = self.rama("revisar", "--tipo", "diseno", "--mockup", "panel-general", "--epicas", "riego,cosechas")
        self.assertEqual(oferta["accion"], "ofrecer")
        git("switch", "-q", oferta["principal"], cwd=self.copia)
        git("pull", "-q", "--ff-only", cwd=self.copia)
        git("switch", "-q", "-c", oferta["rama_nueva"], cwd=self.copia)
        self.proteger(oferta["rama_nueva"])
        self.commit(self.copia, "vistas")
        self.assertNotEqual(git("push", "-q", "-u", "origin", oferta["rama_nueva"], cwd=self.copia, check=False).returncode, 0)
        resultado = self.rama("rechazo", "--tipo", "diseno", "--mockup", "panel-general")
        self.assertEqual((resultado["accion"], resultado["motivo"], resultado["rama"]),
                         ("parar", "rama-nueva-rechazada", "diseno/panel-general"))
        self.assertNotIn("rama_nueva", resultado)

    def test_rechazo_de_la_rama_nueva_tras_otro_rechazo_para(self):
        self.proteger("main", "spec/riego")
        self.commit(self.copia, "spec")
        self.assertNotEqual(git("push", "-q", cwd=self.copia, check=False).returncode, 0)
        nueva = self.rama("rechazo", "--tipo", "spec", "--epica", "riego")["rama_nueva"]
        git("switch", "-q", "-c", nueva, cwd=self.copia)
        self.assertNotEqual(git("push", "-q", "-u", "origin", nueva, cwd=self.copia, check=False).returncode, 0)
        self.assertEqual(self.rama("rechazo", "--tipo", "spec", "--epica", "riego")["motivo"], "rama-nueva-rechazada")

    def test_la_rama_nueva_que_hereda_el_upstream_de_la_principal_para(self):
        """Con `branch.autoSetupMerge=inherit`, `git switch -c` deja la rama nueva siguiendo a origin/main."""
        git("config", "branch.autoSetupMerge", "inherit", cwd=self.copia)
        self.test_rechazo_de_la_rama_nueva_tras_otro_rechazo_para()
        self.assertEqual(git("rev-parse", "--abbrev-ref", "@{upstream}", cwd=self.copia).stdout.strip(), "origin/main")

    def test_diseno_mockup_que_hereda_el_upstream_de_la_rama_de_la_epica_para(self):
        git("config", "branch.autoSetupMerge", "inherit", cwd=self.copia)
        self.test_rechazo_de_diseno_mockup_creada_tras_el_si_para()
        self.assertEqual(git("rev-parse", "--abbrev-ref", "@{upstream}", cwd=self.copia).stdout.strip(), "origin/main")

    def test_principal_sin_upstream_da_la_rama_nueva(self):
        """Una principal sin upstream no empuja con `git push`; es la principal del servidor, no una rama nueva."""
        git("branch", "--unset-upstream", cwd=self.copia)
        self.commit(self.copia, "spec")
        self.assertNotEqual(git("push", "-q", cwd=self.copia, check=False).returncode, 0)
        self.assertEqual(self.rama("rechazo", "--tipo", "spec", "--epica", "riego"),
                         {"accion": "rama-nueva", "rama": "main", "rama_nueva": "spec/riego"})


class Uso(Base):
    def falla(self, *args):
        resultado = subprocess.run([sys.executable, "-B", str(SCRIPT), *args], cwd=self.copia, env=ENTORNO,
                                   capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(resultado.returncode, 2, resultado.stdout)
        self.assertEqual(resultado.stdout, "")

    def test_tipo_desconocido(self):
        self.falla("revisar", "--tipo", "feat", "--epica", "riego")

    def test_epica_que_no_sirve_como_rama(self):
        for epica in ("", "riego nuevo", "riego/norte", "riego..x", "-riego", "riego-", "riego.lock"):
            with self.subTest(epica=epica):
                self.falla("revisar", "--tipo", "spec", f"--epica={epica}")

    def test_mockup_solo_con_diseno_y_con_varias_epicas(self):
        self.falla("revisar", "--tipo", "spec", "--mockup", "panel", "--epicas", "riego,cosechas")
        self.falla("revisar", "--tipo", "diseno", "--mockup", "panel")
        self.falla("revisar", "--tipo", "diseno", "--mockup", "panel", "--epicas", "riego")
        self.falla("revisar", "--tipo", "diseno", "--mockup", "panel", "--epicas", "riego,riego")
        self.falla("revisar", "--tipo", "diseno", "--mockup", "panel", "--epicas", "riego,cosechas nuevas")
        self.falla("revisar", "--tipo", "diseno", "--mockup", "Panel General", "--epicas", "riego,cosechas")
        self.falla("revisar", "--tipo", "diseno", "--epica", "riego", "--mockup", "panel", "--epicas", "riego,cosechas")
        self.falla("revisar", "--tipo", "diseno", "--epica", "riego", "--epicas", "riego,cosechas")

    def test_sin_epica_ni_mockup(self):
        self.falla("revisar", "--tipo", "spec")
        self.falla("rechazo", "--tipo", "spec")


if __name__ == "__main__":
    unittest.main()
