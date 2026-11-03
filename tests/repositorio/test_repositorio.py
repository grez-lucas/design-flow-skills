import json
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SKILLS = RAIZ / "skills"
PYTHON_EN_EL_README = "| Python 3.9 o superior (`python3`, `python` o `py -3`)"


class RevisarSinBytecode(unittest.TestCase):
    def test_checklist_diseno_corre_revisar_py_con_el_interprete_y_b(self):
        texto = (SKILLS / "checklist-diseno" / "SKILL.md").read_text(encoding="utf-8")
        llamadas = [l for l in texto.splitlines() if "revisar.py" in l and "intérprete" in l]
        self.assertTrue(llamadas, "SKILL.md no corre revisar.py")
        for linea in llamadas:
            self.assertRegex(linea, r"(?:^|`)<intérprete> -B ", linea)

    def test_html_a_vista_corre_sus_scripts_con_el_interprete_y_b(self):
        for ruta in [SKILLS / "html-a-vista" / "SKILL.md", *sorted((SKILLS / "html-a-vista" / "references").glob("*.md"))]:
            with self.subTest(archivo=ruta.name):
                for orden in Interprete.ordenes(ruta.read_text(encoding="utf-8").replace(Interprete.PARRAFO, "")):
                    Interprete.revisar_orden(self, orden)
        texto = (SKILLS / "html-a-vista" / "SKILL.md").read_text(encoding="utf-8")
        for script in ("desarmar.py", "tokens.py", "inventario.py", "revisar.py", "aprobadas.py"):
            self.assertRegex(texto, rf"<intérprete> -B [^`\n]*{script}", script)


class Interprete(unittest.TestCase):
    """Q105 y Q106: cada skill que corre scripts busca el intérprete al empezar, con el mismo párrafo, y cada orden
    lo usa con `-B`; sin intérprete, cada skill sigue su propio caso."""

    SKILLS_CON_SCRIPTS = ("checklist-diseno", "grilling-es", "html-a-vista", "spec-a-html", "spec-a-tickets")
    PARRAFO = ("Al empezar, una sola vez, busca el intérprete: prueba `python3`, `python` y `py -3`, en ese orden, con "
               "`<intérprete> -c \"import sys; assert sys.version_info >= (3, 9)\"`, y usa el primero que sale sin error "
               "como `<intérprete>` en cada orden de esta skill y de sus `references/`, siempre con `-B`, para que Python "
               "no deje `__pycache__/` en la carpeta de la skill. Si ninguno responde, no corras ninguna orden con Python "
               "y sigue lo que esta skill dice para cuando no encontraste intérprete.")
    SIN_PYTHON_AL_GUARDAR = ("Si no encontraste intérprete, para y no guardes: explica en simple que falta Python 3.9 o "
                             "superior y que se instala desde https://www.python.org/downloads/.")
    # Q106: el caso sin intérprete de cada skill, en el paso donde corre su primer script.
    SIN_PYTHON = {
        "grilling-es": ("Guardar", SIN_PYTHON_AL_GUARDAR),
        "spec-a-tickets": ("3", SIN_PYTHON_AL_GUARDAR),
        "spec-a-html": ("2", SIN_PYTHON_AL_GUARDAR),
        "html-a-vista": ("2", "Si no encontraste intérprete, para aquí y no escribas en el repositorio: explica en simple "
                              "que falta Python 3.9 o superior y que se instala desde https://www.python.org/downloads/."),
        "checklist-diseno": ("2", "Si no encontraste intérprete, revisa a mano, y dilo en el informe."),
    }
    # Una orden es un trozo de código que llama a un `.py` con argumentos, o que empieza con un intérprete.
    LLAMA_A_UN_PY = re.compile(r"\.py\s+\S")
    EMPIEZA_CON_INTERPRETE = re.compile(r"^(?:<intérprete>|python3?|py)\s")
    ORDEN_BIEN = r"^<intérprete> -B \S+\.py(?:\s|$)"
    FIJO = re.compile(r"(?<![\w./<-])(?:python3?|py)\s+(?:-|\S+\.py\b)")

    @classmethod
    def trozos(cls, texto):
        """Cada trozo en `código` y cada línea de un bloque ``` del texto."""
        trozos, bloque = [], False
        for linea in texto.splitlines():
            if linea.strip().startswith("```"):
                bloque = not bloque
            elif bloque:
                trozos.append(linea.strip())
            else:
                trozos += re.findall(r"`([^`\n]+)`", linea)
        return trozos

    @classmethod
    def ordenes(cls, texto):
        return [t for t in cls.trozos(texto) if cls.LLAMA_A_UN_PY.search(t) or cls.EMPIEZA_CON_INTERPRETE.match(t)]

    def revisar_orden(self, orden):
        """Una orden que llama a un `.py` va con `<intérprete> -B`; una sin script solo puede ser `<intérprete> -B -c`."""
        if ".py" in orden:
            self.assertRegex(orden, Interprete.ORDEN_BIEN, orden)
        else:
            self.assertRegex(orden, r"^<intérprete> -B -c(?:\s|$)", orden)

    def archivos(self, skill):
        return [SKILLS / skill / "SKILL.md", *sorted((SKILLS / skill / "references").glob("*.md"))]

    def test_son_las_skills_que_tienen_scripts(self):
        con_scripts = {r.parents[1].name for r in SKILLS.glob("*/scripts/*.py")}
        self.assertEqual(con_scripts, set(self.SKILLS_CON_SCRIPTS))

    def test_la_busqueda_es_el_mismo_parrafo_al_empezar_cada_skill(self):
        for skill in self.SKILLS_CON_SCRIPTS:
            with self.subTest(skill=skill):
                texto = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
                secciones = re.findall(r"^## (.+)$", texto, re.M)
                self.assertEqual(secciones[:1], ["Intérprete de Python"], "no es la primera sección")
                cuerpo = re.search(r"^## Intérprete de Python\n(.*?)(?=^#)", texto, re.S | re.M).group(1)
                self.assertEqual(cuerpo.strip(), self.PARRAFO)

    def test_la_busqueda_va_antes_de_la_primera_orden_con_python(self):
        for skill in self.SKILLS_CON_SCRIPTS:
            with self.subTest(skill=skill):
                texto = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
                ordenes = self.ordenes(texto.replace(self.PARRAFO, ""))
                self.assertTrue(ordenes, "no corre ningún script")
                self.assertIn(self.PARRAFO, texto)
                self.assertLess(texto.index(self.PARRAFO), texto.index(ordenes[0]))

    def test_ninguna_orden_usa_un_interprete_fijo_ni_va_sin_b(self):
        for skill in sorted(p.name for p in SKILLS.iterdir() if p.is_dir()):
            for ruta in self.archivos(skill):
                texto = ruta.read_text(encoding="utf-8").replace(self.PARRAFO, "")
                with self.subTest(archivo=str(ruta.relative_to(RAIZ))):
                    self.assertEqual(self.FIJO.findall(texto), [])
                    for orden in self.ordenes(texto):
                        self.revisar_orden(orden)

    def test_cada_skill_conserva_su_caso_sin_python(self):
        for skill, (paso, frase) in self.SIN_PYTHON.items():
            with self.subTest(skill=skill):
                texto = MensajeYRamaDelCommit.paso(self, skill, paso)
                self.assertIn(frase, texto)
                ordenes = self.ordenes(texto)
                self.assertTrue(ordenes, "el paso no corre su primer script")
        self.assertEqual(set(self.SIN_PYTHON), set(self.SKILLS_CON_SCRIPTS))


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

    def test_el_readme_explica_que_guarda_en_cualquier_rama_del_flujo_de_la_misma_epica(self):
        """Q96 en el README; la regla la prueba tests/rama."""
        self.assertIn("cualquier rama del flujo de esa misma épica", self.readme())

    def test_nada_asume_push_a_la_rama_principal_ni_lo_fuerza(self):
        archivos = {"README.md": self.readme()}
        for skill in self.TIPOS:
            archivos.update(self.textos(skill))
        pushes = {"git push", "git push --dry-run", "git push -u origin <rama_nueva>"}
        for archivo, texto in archivos.items():
            with self.subTest(archivo=archivo):
                self.assertNotRegex(texto, r"push a (`(main|master)`|(main|master)\b|la rama principal)")
                resto = texto.replace(self.SIN_ATAJOS, "")
                self.assertNotRegex(resto, r"--force|push -f\b|pull --rebase|reset --hard|git push [^`\n]*\+|`git pull(?! --ff-only`)")
                for llamada in re.findall(r"`(git push[^`]*)`", texto):
                    self.assertIn(llamada, pushes)

    # Paso donde la skill ubica el repositorio de diseño, antes de cualquier escritura, y paso donde guarda.
    PASO_DE_LA_RAMA = {"grilling-es": "Guardar", "spec-a-tickets": "3", "spec-a-html": "2", "html-a-vista": "5"}
    PASO_GUARDAR = {"grilling-es": "Guardar", "spec-a-tickets": "9", "spec-a-html": "9", "html-a-vista": "9"}

    def paso(self, skill, nombre):
        texto = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
        titulo = rf"### {re.escape(nombre)}\n" if not nombre.isdigit() else rf"### {nombre}\. [^\n]*\n"
        return re.search(rf"^{titulo}.*?(?=^##)", texto, re.S | re.M).group(0)

    def test_solo_las_credenciales_quedan_fuera_de_la_rama_nueva(self):
        """Q90: todo rechazo que no sea de credenciales va por la rama nueva; "acceso" no amplía la excepción."""
        archivos = {"README.md": self.readme()}
        for skill in self.TIPOS:
            archivos[skill] = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
        for archivo, texto in archivos.items():
            with self.subTest(archivo=archivo):
                self.assertNotRegex(texto, r"credenciales o (de|por falta de|sin) acceso")

    def test_html_a_vista_nombra_commit_y_rama_por_el_mockup_si_cubre_varias_epicas(self):
        """Q92: `diseno(<mockup>)` y `diseno/<mockup>`, con las épicas en el cuerpo; esa rama sirve como rama del flujo."""
        texto = (SKILLS / "html-a-vista" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("`diseno(<mockup>): <resumen>`", texto)
        self.assertIn("`diseno/<mockup>`", texto)
        self.assertRegex(texto, r"las épicas van en el cuerpo")
        for skill in ("grilling-es", "spec-a-tickets", "spec-a-html"):
            with self.subTest(skill=skill):
                self.assertNotIn("<mockup>", (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8"))

    def test_el_readme_explica_la_rama_de_una_sola_de_varias_epicas(self):
        """Q97 en el README: no guarda, para, ofrece la principal y cambia solo con el sí y el árbol sin cambios."""
        readme = self.readme()
        self.assertIn("no guarda ahí: para, lo explica y ofrece volver a la principal y guardar en `diseno/<mockup>`",
                      readme)
        self.assertIn("cambia de rama solo con el sí de la persona y sin cambios sin guardar", readme)

    def test_ningun_ejemplo_usa_otro_tipo_de_commit(self):
        """Q86: un ejemplo `feat: ...` o `docs(x): ...` contradice el tipo fijo de cada skill, con o sin paréntesis."""
        otros = r"(?<![\w/-])(feat|fix|docs|chore|refactor|test|style|perf|build|ci)(\([^)\n]*\))?!?: \S"
        archivos = {"README.md": self.readme()}
        for skill in self.TIPOS:
            archivos.update(self.textos(skill))
        for archivo, texto in archivos.items():
            with self.subTest(archivo=archivo):
                self.assertNotRegex(texto, otros)

    def test_el_readme_explica_la_rama_actual_y_el_camino_del_rechazo(self):
        readme = (RAIZ / "README.md").read_text(encoding="utf-8")
        self.assertIn("rama actual", readme)
        self.assertIn("merge request", readme)
        for tipo in sorted(set(self.TIPOS.values())):
            with self.subTest(tipo=tipo):
                self.assertIn(f"`{tipo}/<épica>`", readme)


class CopiasDeRama(unittest.TestCase):
    """Q99: cada skill que hace commit lleva su copia de `scripts/rama.py`, porque `npx skills` instala cada skill
    por separado, y las copias son iguales byte a byte a la de `grilling-es`, la que prueba `tests/rama`."""

    ORIGINAL = SKILLS / "grilling-es" / "scripts" / "rama.py"

    def test_cada_skill_que_hace_commit_tiene_su_copia_igual(self):
        original = self.ORIGINAL.read_bytes()
        for skill in CommitSoloDeDesignYSpecs.SKILLS_CON_COMMIT:
            ruta = SKILLS / skill / "scripts" / "rama.py"
            with self.subTest(skill=skill):
                self.assertTrue(ruta.is_file(), "falta la copia")
                self.assertEqual(ruta.read_bytes(), original, "copia distinta; cópiala de skills/grilling-es/scripts/rama.py")

    def test_ninguna_otra_skill_tiene_copia(self):
        con_copia = {r.parents[1].name for r in SKILLS.rglob("rama.py")}
        self.assertEqual(con_copia, set(CommitSoloDeDesignYSpecs.SKILLS_CON_COMMIT))


class LlamadaARama(unittest.TestCase):
    """Q100 a Q105: la skill corre `rama.py`, hace lo que dice cada acción y, sin Python, para sin guardar. Las
    reglas de la rama las prueba `tests/rama` contra repositorios git reales."""

    TIPOS = MensajeYRamaDelCommit.TIPOS
    PASO_DE_LA_RAMA = MensajeYRamaDelCommit.PASO_DE_LA_RAMA
    PASO_GUARDAR = MensajeYRamaDelCommit.PASO_GUARDAR
    INTERPRETE = Interprete.SIN_PYTHON_AL_GUARDAR
    SI_FALLA = "Si `rama.py` sale con error o no devuelve un JSON, aquí o tras un rechazo, para y no guardes"

    def paso(self, skill, nombre):
        return MensajeYRamaDelCommit.paso(self, skill, nombre)

    def tras(self, skill, nombre, orden):
        """Lo que la skill dice después de correr `rama.py <orden>`, hasta la siguiente llamada al script."""
        texto = self.paso(skill, nombre)
        inicio = texto.index(f"/scripts/rama.py {orden} ")
        fin = texto.find("/scripts/rama.py ", inicio + 1)
        return texto[inicio:fin if fin != -1 else len(texto)]

    def accion(self, texto, accion):
        lineas = [l for l in texto.splitlines() if l.startswith(f"- `{accion}`: ")]
        self.assertEqual(len(lineas), 1, f"no hay una viñeta para `{accion}`")
        return lineas[0]

    def test_revisa_la_rama_con_el_script_antes_de_la_primera_escritura(self):
        for skill, tipo in self.TIPOS.items():
            with self.subTest(skill=skill):
                rama = self.paso(skill, self.PASO_DE_LA_RAMA[skill])
                self.assertIn(f"<intérprete> -B <ruta-de-esta-skill>/scripts/rama.py revisar --tipo {tipo} --epica <épica>", rama)
                guardar = self.paso(skill, self.PASO_GUARDAR[skill])
                if rama != guardar:
                    self.assertNotIn("rama.py revisar", guardar)

    def test_dice_que_hacer_con_cada_accion_de_revisar(self):
        for skill in self.TIPOS:
            with self.subTest(skill=skill):
                rama = self.tras(skill, self.PASO_DE_LA_RAMA[skill], "revisar")
                self.assertIn("guarda en la rama actual", self.accion(rama, "guardar"))
                volver = self.accion(rama, "volver")
                for fragmento in ("`git switch <principal>`", "`git pull --ff-only`", "Si uno falla, para y explica"):
                    self.assertIn(fragmento, volver)
                parar = self.accion(rama, "parar")
                for fragmento in ("no escribas", "`detalle`", "el TL dice cómo seguir"):
                    self.assertIn(fragmento, parar)

    def test_sin_python_para_y_no_guarda(self):
        """Q105: `python3`, `python` y `py -3`, en ese orden, el primero con Python 3.9 o superior; si ninguno, para."""
        for skill in self.TIPOS:
            with self.subTest(skill=skill):
                rama = self.paso(skill, self.PASO_DE_LA_RAMA[skill])
                self.assertIn(self.INTERPRETE, rama)
                self.assertLess(rama.index(self.INTERPRETE), rama.index("- `guardar`: "))
                texto = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
                self.assertIn(Interprete.PARRAFO, texto)

    def test_la_busqueda_del_interprete_es_igual_en_las_cuatro(self):
        parrafos = set()
        for skill in self.TIPOS:
            texto = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
            parrafos.add(next((l for l in texto.splitlines() if l.startswith("Al empezar, una sola vez, busca el intérprete")), ""))
        self.assertEqual(len(parrafos), 1, parrafos)
        self.assertEqual(Interprete.PARRAFO, parrafos.pop())

    def test_si_el_script_falla_o_no_da_json_para(self):
        for skill in self.TIPOS:
            with self.subTest(skill=skill):
                rama = self.paso(skill, self.PASO_DE_LA_RAMA[skill])
                self.assertIn(self.SI_FALLA, rama)
                self.assertLess(rama.index(self.SI_FALLA), rama.index("- `guardar`: "))

    def test_si_el_nombre_termina_en_guion_y_numero_pide_otro(self):
        """Q104: `rama.py` rechaza `fase-2` y la skill pide otro nombre."""
        for skill in self.TIPOS:
            with self.subTest(skill=skill):
                rama = self.paso(skill, self.PASO_DE_LA_RAMA[skill])
                self.assertIn("si dice que el nombre termina en guion y número, pide a la persona otro, por ejemplo "
                              "`fase-dos` en lugar de `fase-2`, y vuelve a correrlo", rama)

    def test_tras_un_rechazo_pide_la_rama_nueva_al_script(self):
        for skill, tipo in self.TIPOS.items():
            with self.subTest(skill=skill):
                guardar = self.paso(skill, self.PASO_GUARDAR[skill])
                orden = f"<intérprete> -B <ruta-de-esta-skill>/scripts/rama.py rechazo --tipo {tipo} --epica <épica>"
                self.assertIn(orden, guardar)
                for fragmento in ("El push va a la rama actual, con `git push`", "no sea de credenciales",
                                  MensajeYRamaDelCommit.SIN_ATAJOS):
                    self.assertIn(fragmento, guardar)
                self.assertLess(guardar.index("no sea de credenciales"), guardar.index(orden))
                guardar = self.tras(skill, self.PASO_GUARDAR[skill], "rechazo")
                nueva = self.accion(guardar, "rama-nueva")
                for fragmento in ("`git switch -c <rama_nueva>`", "`git push -u origin <rama_nueva>`",
                                  "`git branch -f <rama> origin/<rama>`", "merge request"):
                    self.assertIn(fragmento, nueva)
                parar = self.accion(guardar, "parar")
                self.assertIn("el TL es quien da los accesos", parar)
                self.assertIn("`detalle`", parar)
                self.assertNotIn("rechazó también", parar)

    def test_rechazo_corre_desde_el_repositorio_de_diseno_como_revisar(self):
        for skill, tipo in self.TIPOS.items():
            with self.subTest(skill=skill):
                guardar = self.paso(skill, self.PASO_GUARDAR[skill])
                if skill == "html-a-vista":
                    self.assertIn(f"rama.py rechazo --tipo {tipo} --epica <épica> --repo <repo-de-diseño>`", guardar)
                else:
                    self.assertIn("Pide la rama nueva, desde el repositorio de diseño, con `<intérprete> -B ", guardar)

    def test_las_reglas_viven_en_el_script_y_no_en_el_texto(self):
        for skill in self.TIPOS:
            with self.subTest(skill=skill):
                texto = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
                for regla in ("`git fetch`", "git ls-remote", "git for-each-ref", "@{upstream}", "--untracked-files"):
                    self.assertNotIn(regla, texto)

    def test_html_a_vista_pasa_el_mockup_y_las_epicas_si_son_varias(self):
        rama = self.paso("html-a-vista", "5")
        self.assertIn("`--mockup <mockup> --epicas <épica>,<épica>`", rama)
        self.assertIn("pasa `--mockup <mockup>` en lugar de `--epica <épica>`", self.paso("html-a-vista", "9"))
        for skill in ("grilling-es", "spec-a-tickets", "spec-a-html"):
            with self.subTest(skill=skill):
                texto = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
                self.assertNotIn("--mockup", texto)
                self.assertNotIn("`ofrecer`", texto)

    def test_html_a_vista_cambia_de_rama_con_ofrecer_solo_con_el_si(self):
        """Q97: antes de escribir nada explica y ofrece; sin el sí o con un fallo, para y dice dónde quedó."""
        ofrecer = self.accion(self.tras("html-a-vista", "5", "revisar"), "ofrecer")
        for fragmento in ("no guardes ahí", "Antes de escribir nada", "ofrece volver a la principal y guardar en `rama_nueva`",
                          "Solo con el sí de la persona", "`git switch <principal>`", "`git pull --ff-only`",
                          "`git switch -c <rama_nueva>`",
                          "Sin el sí, o si un comando falla, para y explica en qué rama quedaste y que el TL dice cómo seguir."):
            self.assertIn(fragmento, ofrecer)
        self.assertLess(ofrecer.index("Solo con el sí de la persona"), ofrecer.index("`git switch <principal>`"))

    def test_html_a_vista_vuelve_a_revisar_el_arbol_tras_el_si(self):
        """Q97: el árbol pudo cambiar mientras la persona contestaba; se revisa otra vez antes de `git switch`."""
        ofrecer = self.accion(self.tras("html-a-vista", "5", "revisar"), "ofrecer")
        revisa = "vuelve a correr la misma orden de `rama.py`"
        self.assertIn(revisa, ofrecer)
        self.assertIn("si no devuelve otra vez `ofrecer`, para y explica por qué", ofrecer)
        self.assertLess(ofrecer.index("Solo con el sí de la persona"), ofrecer.index(revisa))
        self.assertLess(ofrecer.index(revisa), ofrecer.index("`git switch <principal>`"))

    def test_html_a_vista_empuja_con_upstream_la_rama_de_ofrecer(self):
        """Q98: la rama de `ofrecer` se empuja con `-u`; si el servidor la rechaza, `rechazo` devuelve `parar`."""
        guardar = self.paso("html-a-vista", "9")
        self.assertIn("si el paso 5 creó la rama de `ofrecer`, con `git push -u origin <rama_nueva>`", guardar)

    def test_el_readme_pide_python_para_guardar(self):
        readme = (RAIZ / "README.md").read_text(encoding="utf-8")
        requisitos = re.search(r"^## Requisitos\n.*?(?=^## )", readme, re.S | re.M).group(0)
        fila = next((l for l in requisitos.splitlines() if l.startswith(PYTHON_EN_EL_README) and "rama.py" in l), "")
        self.assertTrue(fila, "Requisitos no lista Python para rama.py")
        self.assertNotIn("| `python3`", requisitos)
        for skill in self.TIPOS:
            self.assertIn(f"`{skill}`", fila)
        self.assertIn("Python 3.9 o superior", fila)

    def test_el_primer_setup_en_windows_instala_python(self):
        """Q105: el primer setup en Windows suma Python para guardar."""
        readme = (RAIZ / "README.md").read_text(encoding="utf-8")
        windows = re.search(r"^### Primer setup en Windows\n.*?(?=^### )", readme, re.S | re.M).group(0)
        self.assertIn("winget install Python.Python.3.12", windows)
        self.assertIn("py -3 --version", windows)


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
        agregados = re.findall(r"`git add ([^`]*)`", paso)
        self.assertIn(self.PUNTERO, agregados)
        self.assertIn("specs/<épica>/", agregados)

    def test_es_un_solo_commit_al_final(self):
        self.assertIn("Es un solo commit al final", self.paso(9))
        for numero in range(1, 9):
            with self.subTest(paso=numero):
                self.assertNotRegex(self.paso(numero), r"haz commit|git commit")

    def test_sin_convenciones_no_escribe_el_puntero(self):
        paso = self.paso(3)
        self.assertIn("Si la persona dice que no hay convenciones, no escribas el puntero", paso)
        self.assertIn("si lo escribiste en esta sesión", self.paso(9))

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
