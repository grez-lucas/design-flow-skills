import json
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SKILLS = RAIZ / "skills"


class RevisarSinBytecode(unittest.TestCase):
    def test_checklist_diseno_corre_revisar_py_con_python3_b(self):
        texto = (SKILLS / "checklist-diseno" / "SKILL.md").read_text(encoding="utf-8")
        llamadas = [l for l in texto.splitlines() if "revisar.py" in l and "python" in l]
        self.assertTrue(llamadas, "SKILL.md no corre revisar.py")
        for linea in llamadas:
            self.assertRegex(linea, r"\bpython3 -B ", linea)

    def test_html_a_vista_corre_sus_scripts_con_python3_b(self):
        for ruta in [SKILLS / "html-a-vista" / "SKILL.md", *sorted((SKILLS / "html-a-vista" / "references").glob("*.md"))]:
            texto = ruta.read_text(encoding="utf-8")
            llamadas = re.findall(r"python3?[^`\n]*\.py", texto)
            with self.subTest(archivo=ruta.name):
                for llamada in llamadas:
                    self.assertRegex(llamada, r"^python3 -B ", llamada)
        texto = (SKILLS / "html-a-vista" / "SKILL.md").read_text(encoding="utf-8")
        for script in ("desarmar.py", "tokens.py", "inventario.py", "revisar.py", "aprobadas.py"):
            self.assertRegex(texto, rf"python3 -B [^`\n]*{script}", script)


class CommitSoloDeDesignYSpecs(unittest.TestCase):
    SKILLS_CON_COMMIT = ("grilling-es", "html-a-vista", "spec-a-html", "spec-a-tickets")
    # Q87: el puntero a las convenciones de gestión entra en el commit de los tickets, y solo ese archivo de .claude/.
    FUERA_DE_DESIGN_Y_SPECS = {"spec-a-tickets": {".claude/pm-conventions.md"}}
    PROHIBIDOS = {"-A", "."}

    def archivos_con_commit(self, skill):
        return [
            ruta
            for ruta in sorted((SKILLS / skill).rglob("*.md"))
            if re.search(r"\bcommit y push\b", ruta.read_text(encoding="utf-8"))
        ]

    def test_cada_skill_que_hace_commit_lo_dice_en_algun_archivo(self):
        for skill in self.SKILLS_CON_COMMIT:
            with self.subTest(skill=skill):
                self.assertTrue(self.archivos_con_commit(skill))

    def test_el_commit_agrega_solo_design_y_specs(self):
        for skill in self.SKILLS_CON_COMMIT:
            for ruta in self.archivos_con_commit(skill):
                with self.subTest(archivo=str(ruta.relative_to(RAIZ))):
                    texto = ruta.read_text(encoding="utf-8")
                    permitidos = []
                    for linea in texto.splitlines():
                        for argumentos in re.findall(r"`git add ([^`]*)`", linea):
                            rutas = [a for a in argumentos.split() if a != "--"]
                            if rutas and all(r.startswith(("design/", "specs/")) or r == ".gitignore" for r in rutas):
                                permitidos.append(argumentos)
                            elif set(rutas) <= self.PROHIBIDOS:
                                self.assertIn("nunca", linea.lower(), linea)
                            else:
                                extra = self.FUERA_DE_DESIGN_Y_SPECS.get(skill, set())
                                fuera = [r for r in rutas if not r.startswith(("design/", "specs/"))]
                                self.assertTrue(set(fuera) <= extra, argumentos)
                                permitidos.append(argumentos)
                    self.assertTrue(permitidos, "no da un git add limitado a design/ y specs/")

    def test_el_resumen_antes_del_push_lista_solo_lo_que_entra_al_commit(self):
        for skill in self.SKILLS_CON_COMMIT:
            for ruta in self.archivos_con_commit(skill):
                with self.subTest(archivo=str(ruta.relative_to(RAIZ))):
                    texto = ruta.read_text(encoding="utf-8")
                    self.assertIn("skills-lock.json", texto)
                    self.assertIn("el resumen", texto.lower())


class LavishFueraDelCommit(unittest.TestCase):
    """Las skills que hacen commit dejan `.lavish/` en el `.gitignore` del repositorio de diseño y lo suben."""

    def test_agregan_lavish_al_gitignore_y_lo_suben_en_el_commit(self):
        for skill in CommitSoloDeDesignYSpecs.SKILLS_CON_COMMIT:
            texto = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
            with self.subTest(skill=skill):
                self.assertRegex(texto, r"`\.lavish/`[^\n]*`\.gitignore`|`\.gitignore`[^\n]*`\.lavish/`")
                self.assertRegex(texto, r"`\.gitignore`[^\n]*tenga la línea `\.lavish/`")
                self.assertIn("`git add .gitignore`", texto)


class OlaUnoConModalYAvisos(unittest.TestCase):
    """La ola 1 de html-a-vista arma components.css y tokens.css con las piezas que la convención de vista da por
    hechas: la regla del frame, el modal, los avisos y sus tokens."""

    def test_la_ola_1_nombra_el_frame_el_modal_los_avisos_y_sus_tokens(self):
        texto = (SKILLS / "html-a-vista" / "references" / "olas.md").read_text(encoding="utf-8")
        ola_1 = texto.split("## Ola 2")[0]
        for pieza in ("`:where([data-frame])`", "`.modal`", "`.modal__dialog`", "`.modal__actions`", "`.toast-region`",
                      "`--color-overlay`", "`--size-modal`"):
            with self.subTest(pieza=pieza):
                self.assertIn(pieza, ola_1)


class MensajeYRamaDelCommit(unittest.TestCase):
    """Q86: mensaje `<tipo>(<épica>): <resumen>`, push a la rama actual y `<tipo>/<épica>` si la protección rechaza."""

    TIPOS = {"grilling-es": "spec", "spec-a-tickets": "tickets", "spec-a-html": "diseno", "html-a-vista": "diseno"}
    ENCABEZADO = re.compile(r"(?<![\w/-])([a-z]+)\((<?[\w.,é-]+>?)\): \S")

    def textos(self, skill):
        return {str(r.relative_to(RAIZ)): r.read_text(encoding="utf-8") for r in sorted((SKILLS / skill).rglob("*.md"))}

    def test_cada_skill_que_hace_commit_da_el_formato_con_su_tipo(self):
        self.assertEqual(set(self.TIPOS), set(CommitSoloDeDesignYSpecs.SKILLS_CON_COMMIT))
        for skill, tipo in self.TIPOS.items():
            with self.subTest(skill=skill):
                texto = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
                self.assertIn(f"`{tipo}(<épica>): <resumen>`", texto)

    SIN_ATAJOS = "sin `git pull --rebase`, `git reset --hard` ni `--force`"

    def readme(self):
        # Del README cuenta lo que describe a las skills; "## Pruebas" habla del CI de este repositorio.
        return (RAIZ / "README.md").read_text(encoding="utf-8").split("\n## Estado")[0]

    def test_los_ejemplos_de_commit_usan_el_tipo_de_su_skill(self):
        for skill, tipo in self.TIPOS.items():
            for archivo, texto in self.textos(skill).items():
                for encontrado in self.ENCABEZADO.finditer(texto):
                    with self.subTest(archivo=archivo, encabezado=encontrado.group(0)):
                        self.assertEqual(encontrado.group(1), tipo)
        for encontrado in self.ENCABEZADO.finditer(self.readme()):
            with self.subTest(archivo="README.md", encabezado=encontrado.group(0)):
                self.assertIn(encontrado.group(1), set(self.TIPOS.values()))

    def test_el_push_va_a_la_rama_actual_y_a_tipo_epica_si_la_proteccion_rechaza(self):
        for skill, tipo in self.TIPOS.items():
            with self.subTest(skill=skill):
                texto = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
                self.assertIn("rama actual", texto)
                self.assertIn(f"git switch -c {tipo}/<épica>", texto)
                self.assertIn(f"git push -u origin {tipo}/<épica>", texto)
                self.assertIn("merge request", texto)
                # El camino del rechazo deja la rama de origen como en el servidor y no reescribe nada.
                self.assertIn("`git branch -f <rama> origin/<rama>`", texto)
                self.assertIn(self.SIN_ATAJOS, texto)
                self.assertRegex(texto, r"no sea de credenciales")

    def test_antes_de_guardar_revisa_la_rama_actual(self):
        """Q90: fetch, principal o rama viva de la misma épica; upstream borrado sin commits pendientes vuelve a la principal."""
        for skill, tipo in self.TIPOS.items():
            with self.subTest(skill=skill):
                texto = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
                for fragmento in ("`git fetch`", f"`{tipo}/<épica>-<n>`", "`git ls-remote --exit-code --heads origin <rama>`",
                                  "`git log --oneline @{upstream}..HEAD`", "`git switch <principal>` y `git pull --ff-only`",
                                  "para y explica"):
                    self.assertIn(fragmento, texto)
                self.assertLess(texto.index("`git fetch`"), texto.index(f"git switch -c {tipo}/<épica>"))

    def test_la_rama_nueva_toma_el_primer_sufijo_libre(self):
        """Q91: si `<tipo>/<épica>` ya existe en local o en el servidor, `-2`, `-3`."""
        for skill, tipo in self.TIPOS.items():
            with self.subTest(skill=skill):
                texto = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
                self.assertIn(f"`{tipo}/<épica>-2`", texto)
                self.assertIn("`git branch -a --list", texto)
                self.assertNotIn("no la reemplaces", texto)

    def test_nada_asume_push_a_la_rama_principal_ni_lo_fuerza(self):
        archivos = {"README.md": self.readme()}
        for skill in self.TIPOS:
            archivos.update(self.textos(skill))
        pushes = {"git push", "git push --dry-run"} | {f"git push -u origin {t}/<épica>" for t in self.TIPOS.values()}
        for archivo, texto in archivos.items():
            with self.subTest(archivo=archivo):
                self.assertNotRegex(texto, r"push a (`(main|master)`|(main|master)\b|la rama principal)")
                resto = texto.replace(self.SIN_ATAJOS, "")
                self.assertNotRegex(resto, r"--force|push -f\b|pull --rebase|reset --hard|git push [^`\n]*\+|`git pull(?! --ff-only`)")
                for llamada in re.findall(r"`(git push[^`]*)`", texto):
                    self.assertIn(llamada, pushes)

    def test_el_readme_explica_la_rama_actual_y_el_camino_del_rechazo(self):
        readme = (RAIZ / "README.md").read_text(encoding="utf-8")
        self.assertIn("rama actual", readme)
        self.assertIn("merge request", readme)
        for tipo in sorted(set(self.TIPOS.values())):
            with self.subTest(tipo=tipo):
                self.assertIn(f"`{tipo}/<épica>`", readme)


class PunteroALasConvenciones(unittest.TestCase):
    """Q87: el puntero a las convenciones va en `.claude/pm-conventions.md`, en el mismo commit que los tickets."""

    PUNTERO = ".claude/pm-conventions.md"

    def adds(self, ruta):
        return re.findall(r"`git add ([^`]*)`", ruta.read_text(encoding="utf-8"))

    def paso(self, numero):
        texto = (SKILLS / "spec-a-tickets" / "SKILL.md").read_text(encoding="utf-8")
        return re.search(rf"^### {numero}\. .*?(?=^### )", texto, re.S | re.M).group(0)

    def test_spec_a_tickets_agrega_el_puntero_en_el_commit_de_los_tickets(self):
        paso = self.paso(9)
        self.assertIn(self.PUNTERO, [a for a in re.findall(r"`git add ([^`]*)`", paso)])
        self.assertIn("specs/<épica>/", re.findall(r"`git add ([^`]*)`", paso))

    def test_sin_convenciones_pregunta_donde_estan_y_guarda_el_puntero(self):
        paso = self.paso(3)
        self.assertIn("pregunta a la persona dónde están", paso)
        self.assertIn("una ruta o una URL", paso)
        bloque = re.search(r"```markdown\n(.*?)```", paso, re.S)
        self.assertTrue(bloque, "no da el contenido del puntero")
        self.assertIn("<ruta o URL>", bloque.group(1))
        self.assertLess(paso.index("pregunta a la persona dónde están"), paso.index("references/plantilla-story.md"))

    def test_el_formato_de_id_de_las_convenciones_manda_sobre_el_del_spec(self):
        titulo = next(l for l in self.paso(5).splitlines() if l.startswith("- **Título**"))
        self.assertLess(titulo.index("formato de ID de las convenciones"), titulo.index("identificador del spec"))

    def test_los_tickets_existentes_se_emparejan_por_el_identificador_del_spec(self):
        self.assertIn("el mismo identificador del spec", self.paso(7))

    def test_ninguna_otra_skill_agrega_el_puntero(self):
        for skill in CommitSoloDeDesignYSpecs.SKILLS_CON_COMMIT:
            if skill == "spec-a-tickets":
                continue
            for ruta in sorted((SKILLS / skill).rglob("*.md")):
                with self.subTest(archivo=str(ruta.relative_to(RAIZ))):
                    self.assertFalse([a for a in self.adds(ruta) if ".claude/" in a])


class NombreDelSiguientePaso(unittest.TestCase):
    PLUGIN = "flujo-diseno"

    def skills(self):
        return sorted(p.name for p in SKILLS.iterdir() if (p / "SKILL.md").is_file())

    def test_el_cierre_da_el_nombre_con_y_sin_prefijo_del_plugin(self):
        nombres = self.skills()
        for skill in nombres:
            texto = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
            cierre = re.split(r"^#{2,3} ", texto, flags=re.M)[-1]
            nombrados = [n for n in nombres if n != skill and f"`{n}`" in cierre]
            with self.subTest(skill=skill):
                self.assertTrue(nombrados, "el cierre no nombra el siguiente paso")
                for nombre in nombrados:
                    self.assertIn(f"`{self.PLUGIN}:{nombre}`", cierre)

    def test_el_readme_da_los_dos_nombres_de_cada_skill(self):
        readme = (RAIZ / "README.md").read_text(encoding="utf-8")
        for skill in self.skills():
            with self.subTest(skill=skill):
                self.assertIn(f"`{skill}`", readme)
                self.assertIn(f"`{self.PLUGIN}:{skill}`", readme)


class VersionDelPlugin(unittest.TestCase):
    def test_plugin_y_marketplace_declaran_la_misma_version_semver(self):
        manifiestos = RAIZ / ".claude-plugin"
        plugin = json.loads((manifiestos / "plugin.json").read_text(encoding="utf-8"))
        marketplace = json.loads((manifiestos / "marketplace.json").read_text(encoding="utf-8"))
        entrada = next(p for p in marketplace["plugins"] if p["name"] == plugin["name"])
        self.assertRegex(plugin.get("version", ""), r"^\d+\.\d+\.\d+$")
        self.assertEqual(entrada.get("version"), plugin["version"])


if __name__ == "__main__":
    unittest.main()
