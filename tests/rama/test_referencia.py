"""Pruebas de conducta de `references/rama.md` y de la excepción del `.gitignore` de `spec-a-tickets`: las órdenes de git
que dan esos textos se leen de los bloques de código y se corren en repositorios reales con un servidor local, como las
correría la skill, y después la skill guarda como dice su `SKILL.md`.

Los casos (issue 42, revisión): A1, trabajo sin guardar en la principal o en una rama del flujo que no debe entrar al
commit de la skill; A2, archivos nuevos que el apartado guarda; M1, una principal local adelantada que no se sube con
el push (Q158); M2, la vuelta a la rama del flujo (Q143); M3, la excepción del `.gitignore` con distintas reglas (Q157).
Uso: python3 -m unittest discover -s tests/rama -v
"""
import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SKILLS = RAIZ / "skills"
SCRIPT = SKILLS / "grilling-es" / "scripts" / "rama.py"
RAMA_MD = SKILLS / "grilling-es" / "references" / "rama.md"

spec = importlib.util.spec_from_file_location("aislar_git", Path(__file__).resolve().parents[1] / "aislar_git.py")
aislar_git = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aislar_git)

ENTORNO = {**aislar_git.sin_repositorio(os.environ), "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
IDENTIDAD = ["-c", "user.name=prueba", "-c", "user.email=prueba@example.com", "-c", "commit.gpgsign=false"]


def git(*args, cwd, check=True, entorno=None):
    return subprocess.run(["git", *IDENTIDAD, *args], cwd=cwd, env=entorno or ENTORNO, check=check,
                          capture_output=True, text=True, encoding="utf-8")


def seccion(texto, titulo):
    m = re.search(rf"^## {re.escape(titulo)}\n(.*?)(?=^## |\Z)", texto, flags=re.S | re.M)
    if not m:
        raise AssertionError(f"no hay sección ## {titulo}")
    return m.group(1)


def bloques(texto):
    """Las líneas de cada bloque ``` del texto, con o sin sangría."""
    return [[l.strip() for l in b.splitlines() if l.strip()]
            for b in re.findall(r"^[ \t]*```[^\n]*\n(.*?)^[ \t]*```", texto, flags=re.S | re.M)]


def bloque_con(texto, comienzo):
    """El bloque cuya primera línea empieza con `comienzo`."""
    encontrados = [b for b in bloques(texto) if b and b[0].startswith(comienzo)]
    if len(encontrados) != 1:
        raise AssertionError(f"no hay un bloque que empiece con {comienzo!r}: {bloques(texto)}")
    return encontrados[0]


class Repositorio(unittest.TestCase):
    """Un servidor bare con `main`, que tiene `design/vistas/alertas/a.html` y `specs/alertas/spec.md`, y la copia de
    quien usa la skill."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.servidor = self.tmp / "servidor.git"
        self.copia = self.tmp / "copia"
        semilla = self.tmp / "semilla"
        git("init", "-q", "--bare", "--initial-branch=main", str(self.servidor), cwd=self.tmp)
        git("clone", "-q", str(self.servidor), str(semilla), cwd=self.tmp)
        self.escribir(semilla, "design/vistas/alertas/a.html", "<p>a</p>\n")
        self.escribir(semilla, "specs/alertas/spec.md", "# Spec\n")
        git("add", "-A", cwd=semilla)
        git("commit", "-q", "-m", "inicio", cwd=semilla)
        git("push", "-q", "origin", "HEAD:main", cwd=semilla)
        git("clone", "-q", str(self.servidor), str(self.copia), cwd=self.tmp)
        self.rama_md = RAMA_MD.read_text(encoding="utf-8")

    @staticmethod
    def escribir(repo, ruta, texto):
        destino = Path(repo) / ruta
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")

    def rama(self, *nombre):
        nombre = nombre or ("--epica", "alertas")
        r = subprocess.run([sys.executable, "-B", str(SCRIPT), "revisar", "--tipo", "diseno", *nombre,
                            "--repo", str(self.copia)], env=ENTORNO, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def rutas(self):
        """`<rutas>` de `references/rama.md`: las que existen de las que agrega la skill."""
        return [r for r in ("design/", "specs/", ".gitignore", ".claude/pm-conventions.md") if (self.copia / r).exists()]

    def correr(self, lineas, **valores):
        """Corre cada orden de git del bloque con los valores en lugar de `<...>`. `<rutas>` se expande a varias."""
        salidas = []
        for linea in lineas:
            self.assertTrue(linea.startswith("git "), linea)
            argv = []
            for parte in shlex.split(linea)[1:]:
                if parte == "<rutas>":
                    argv += self.rutas()
                    continue
                if parte == "<agregadas>":
                    argv += valores["agregadas"]
                    continue
                for clave, valor in valores.items():
                    if isinstance(valor, str):
                        parte = parte.replace(f"<{clave}>", valor)
                self.assertNotRegex(parte, r"<[^>]+>", f"falta un valor en {linea!r}")
                argv.append(parte)
            nada = git("diff", "--cached", "--quiet", cwd=self.copia, check=False).returncode == 0
            if argv == ["diff", "--cached", "--quiet"]:
                # B5: la compuerta del bloque. Sin nada preparado, lo que sigue no va, salvo con `sin-rama`.
                if nada and not valores.get("sin_rama"):
                    break
                continue
            if argv[0] == "commit" and nada and "apartado" in linea.lower():
                continue  # "Si no hay cambios ..., no hagas el commit."
            salidas.append(git(*argv, cwd=self.copia).stdout)
        return salidas

    def seccion(self, titulo):
        return seccion(self.rama_md, titulo)

    def estado(self):
        """Todo lo que responde el primer bloque de "Antes de guardar": vacío si no hay nada que apartar."""
        return "".join(self.correr(bloque_con(self.seccion("Antes de guardar"), "git status --porcelain")))

    def adelantada(self, principal="main"):
        return int(self.correr(bloque_con(self.seccion("Antes de guardar"), "git rev-list --count"),
                               principal=principal)[0].strip())

    def apartar(self, rama, **valores):
        seccion_ = self.seccion("Otra rama o trabajo sin guardar")
        bloque = next(b for b in bloques(seccion_) if any(l.startswith("git switch -c apartado/") for l in b))
        self.correr(bloque, rama=rama.replace("/", "-"), **valores)

    def ramas_vivas(self, nombre="alertas"):
        bloque = bloque_con(self.seccion("Otra rama o trabajo sin guardar"), "git branch -r --list")
        return self.correr(bloque, tipo="diseno", nombre=nombre)[0].split()

    def guardar_como_la_skill(self):
        """Lo que hace `spec-a-html` al guardar: escribe su vista, `git add design/`, commit y push."""
        self.escribir(self.copia, "design/vistas/alertas/nueva.html", "<p>nueva</p>\n")
        git("add", "design/", cwd=self.copia)
        # A3: el commit va con las rutas que la skill agregó, como dice "El commit de la skill".
        self.correr(bloque_con(self.seccion("El commit de la skill"), "git commit"), mensaje="diseno(alertas): nueva",
                    agregadas=["design/"])
        git("push", "-q", "origin", "HEAD", cwd=self.copia)
        return set(git("show", "--name-only", "--format=", "HEAD", cwd=self.copia).stdout.split())

    def archivos_de(self, ref):
        return set(git("show", "--name-status", "--format=", ref, cwd=self.copia).stdout.split())


class TrabajoSinGuardar(Repositorio):
    def test_a1_en_la_principal_el_trabajo_ajeno_no_entra_al_commit_de_la_skill(self):
        self.escribir(self.copia, "design/vistas/alertas/a.html", "<p>a de otra persona</p>\n")
        self.assertEqual(self.rama()["accion"], "guardar")
        self.assertTrue(self.estado().strip(), "Antes de guardar no ve el trabajo sin guardar")
        self.apartar("main")
        git("switch", "main", cwd=self.copia)  # paso 2: la rama de `guardar` era la del flujo
        self.assertEqual(self.rama()["accion"], "guardar")
        self.assertEqual(self.estado().strip(), "")
        self.assertEqual(self.adelantada(), 0)
        self.assertEqual(self.guardar_como_la_skill(), {"design/vistas/alertas/nueva.html"})
        self.assertIn("design/vistas/alertas/a.html", self.archivos_de("apartado/main"))

    def test_a1_en_una_rama_viva_del_flujo_el_trabajo_ajeno_no_entra_al_commit(self):
        git("switch", "-q", "-c", "diseno/alertas", cwd=self.copia)
        git("push", "-q", "-u", "origin", "diseno/alertas", cwd=self.copia)
        self.escribir(self.copia, "specs/alertas/spec.md", "# Spec cambiado\n")
        self.assertEqual(self.rama(), {"accion": "guardar", "rama": "diseno/alertas"})
        self.assertTrue(self.estado().strip())
        self.apartar("diseno/alertas")
        git("switch", "diseno/alertas", cwd=self.copia)
        self.assertEqual(self.rama()["accion"], "guardar")
        self.assertEqual(self.estado().strip(), "")
        commit = self.guardar_como_la_skill()
        self.assertNotIn("specs/alertas/spec.md", commit)
        self.assertIn("specs/alertas/spec.md", self.archivos_de("apartado/diseno-alertas"))

    def test_a2_el_apartado_guarda_tambien_los_archivos_nuevos(self):
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.escribir(self.copia, "design/vistas/alertas/a.html", "<p>a cambiado</p>\n")
        self.escribir(self.copia, "design/vistas/alertas/borrador.html", "<p>borrador</p>\n")
        self.escribir(self.copia, ".agents/skills/x/SKILL.md", "instalación de las skills\n")
        self.assertEqual(self.rama()["motivo"], "otra-rama")
        self.apartar("experimento")
        apartado = self.archivos_de("apartado/experimento")
        self.assertIn("design/vistas/alertas/borrador.html", apartado)
        self.assertIn("design/vistas/alertas/a.html", apartado)
        self.assertNotIn(".agents/skills/x/SKILL.md", apartado)
        self.assertEqual(self.ramas_vivas(), [])
        git("switch", "-q", "main", cwd=self.copia)
        git("pull", "-q", "--ff-only", cwd=self.copia)
        self.assertEqual(self.rama()["accion"], "guardar")
        self.assertEqual(self.guardar_como_la_skill(), {"design/vistas/alertas/nueva.html"})


class TrabajoAjenoFueraDeLasRutas(Repositorio):
    def test_a3_un_archivo_ajeno_en_el_indice_se_ve_y_no_entra_al_commit(self):
        self.escribir(self.copia, "notas.txt", "de otra persona\n")
        git("add", "notas.txt", cwd=self.copia)
        self.assertEqual(self.rama()["accion"], "guardar")
        self.assertIn("notas.txt", self.estado(), "Antes de guardar no mira el índice entero")
        self.assertNotIn("notas.txt", self.guardar_como_la_skill())
        self.assertIn("notas.txt", git("diff", "--cached", "--name-only", cwd=self.copia).stdout)

    def test_a3_con_volver_tambien(self):
        git("switch", "-q", "-c", "diseno/alertas", cwd=self.copia)
        git("push", "-q", "-u", "origin", "diseno/alertas", cwd=self.copia)
        git("push", "-q", "origin", "--delete", "diseno/alertas", cwd=self.copia)
        self.escribir(self.copia, "notas.txt", "de otra persona\n")
        git("add", "notas.txt", cwd=self.copia)
        self.assertEqual(self.rama()["accion"], "volver")
        git("switch", "-q", "main", cwd=self.copia)
        git("pull", "-q", "--ff-only", cwd=self.copia)
        self.assertIn("notas.txt", self.estado())

    def test_b5_sin_nada_que_apartar_no_crea_una_rama_vacia(self):
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.escribir(self.copia, ".agents/skills/x/SKILL.md", "instalación de las skills\n")
        self.assertEqual(self.rama()["motivo"], "otra-rama")
        self.apartar("experimento")
        self.assertEqual(git("branch", "--list", "apartado/*", cwd=self.copia).stdout.strip(), "")

    def test_b6_un_submodulo_con_cambios_adentro_no_manda_a_apartar(self):
        modulo = self.tmp / "modulo"
        git("init", "-q", "--initial-branch=main", str(modulo), cwd=self.tmp)
        self.escribir(modulo, "a.css", "a {}\n")
        git("add", "-A", cwd=modulo)
        git("commit", "-q", "-m", "modulo", cwd=modulo)
        git("-c", "protocol.file.allow=always", "submodule", "add", "-q", str(modulo), "design/lib", cwd=self.copia)
        git("commit", "-q", "-m", "submódulo", cwd=self.copia)
        git("push", "-q", "origin", "HEAD:main", cwd=self.copia)
        self.escribir(self.copia, "design/lib/suelto.txt", "x\n")
        self.assertEqual(self.rama()["accion"], "guardar")
        self.assertEqual(self.estado().strip(), "")


class Ofrecer(Repositorio):
    """A4: `ofrecer` de `html-a-vista` pasa por "Antes de guardar" y "Principal adelantada" antes de la rama nueva.
    `rama.py` mira los cambios con `--untracked-files=no`, así que no ve un archivo nuevo bajo `design/`."""

    def test_a4_un_archivo_sin_seguimiento_que_rama_py_no_ve_lo_ve_antes_de_guardar(self):
        git("switch", "-q", "-c", "diseno/alertas", cwd=self.copia)
        git("push", "-q", "-u", "origin", "diseno/alertas", cwd=self.copia)
        self.escribir(self.copia, "design/vistas/alertas/borrador.html", "<p>borrador</p>\n")
        self.assertEqual(self.rama("--mockup", "panel", "--epicas", "alertas,riego")["accion"], "ofrecer")
        self.assertIn("design/vistas/alertas/borrador.html", self.estado())
        texto = (SKILLS / "html-a-vista" / "SKILL.md").read_text(encoding="utf-8")
        ofrecer = next(l for l in texto.splitlines() if l.startswith("- `ofrecer`: "))
        antes, adelantada, nueva = (ofrecer.index('"Antes de guardar"'), ofrecer.index('"Principal adelantada"'),
                                    ofrecer.index("`git switch -c <rama_nueva>`"))
        self.assertLess(antes, nueva)
        self.assertLess(adelantada, nueva)


class PrincipalAdelantada(Repositorio):
    def test_m1_los_commits_locales_de_la_principal_se_apartan_y_no_se_suben(self):
        self.escribir(self.copia, "design/vistas/alertas/local.html", "<p>local</p>\n")
        git("add", "design/", cwd=self.copia)
        git("commit", "-q", "-m", "commit local de otra sesión", cwd=self.copia)
        git("pull", "-q", "--ff-only", cwd=self.copia)  # pasa: no divergió
        self.assertEqual(self.rama()["accion"], "guardar")
        self.assertEqual(self.estado().strip(), "")
        self.assertEqual(self.adelantada(), 1)
        self.correr(bloque_con(self.seccion("Principal adelantada"), "git branch apartado/"), principal="main")
        self.assertEqual(self.adelantada(), 0)
        self.assertEqual(self.rama()["accion"], "guardar")
        self.guardar_como_la_skill()
        en_el_servidor = git("log", "--format=%s", "origin/main", cwd=self.copia).stdout
        self.assertNotIn("commit local de otra sesión", en_el_servidor)
        self.assertIn("commit local de otra sesión", git("log", "--format=%s", "apartado/main", cwd=self.copia).stdout)


class VueltaALaRamaDelFlujo(Repositorio):
    def test_m2_desde_otra_rama_vuelve_a_la_rama_viva_del_flujo_de_la_epica(self):
        otra = self.tmp / "otra"
        git("clone", "-q", str(self.servidor), str(otra), cwd=self.tmp)
        git("switch", "-q", "-c", "diseno/alertas", cwd=otra)
        self.escribir(otra, "design/vistas/alertas/b.html", "<p>b</p>\n")
        git("add", "design/", cwd=otra)
        git("commit", "-q", "-m", "diseno(alertas): b", cwd=otra)
        git("push", "-q", "-u", "origin", "diseno/alertas", cwd=otra)
        git("switch", "-q", "-c", "experimento", cwd=self.copia)
        self.assertEqual(self.rama()["motivo"], "otra-rama")
        self.apartar("experimento")
        self.assertEqual(self.ramas_vivas(), ["origin/diseno/alertas"])
        git("switch", "-q", "diseno/alertas", cwd=self.copia)
        self.assertEqual(self.rama(), {"accion": "guardar", "rama": "diseno/alertas"})
        self.assertIn("design/vistas/alertas/nueva.html", self.guardar_como_la_skill())

    def test_m9_el_sufijo_es_exacto_y_no_toma_otra_epica(self):
        otra = self.tmp / "otra"
        git("clone", "-q", str(self.servidor), str(otra), cwd=self.tmp)
        for rama in ("diseno/alertas-2fa", "diseno/alertas-2", "diseno/alertas-10", "diseno/alertas-push"):
            git("push", "-q", "origin", f"HEAD:refs/heads/{rama}", cwd=otra)
        git("fetch", "-q", cwd=self.copia)
        self.assertEqual(self.ramas_vivas(), ["origin/diseno/alertas-10", "origin/diseno/alertas-2"])
        self.assertEqual(self.ramas_vivas("alertas-2fa"), ["origin/diseno/alertas-2fa"])


if __name__ == "__main__":
    unittest.main()
