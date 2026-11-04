"""Pruebas de instrucciones de las skills que fijan una decisión: el orden de un paso o un paso que no puede faltar.

Uso: python3 -m unittest discover -s tests/repositorio -v
"""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SKILLS = RAIZ / "skills"


def seccion(texto, titulo, nivel):
    """El cuerpo de la sección cuyo encabezado de `nivel` (##, ###) contiene `titulo`, hasta el siguiente del mismo
    nivel o uno mayor."""
    marca = "#" * nivel
    m = re.search(rf"^{marca} [^\n]*{re.escape(titulo)}[^\n]*\n", texto, flags=re.M)
    if not m:
        raise AssertionError(f"no hay sección {marca} con {titulo!r}")
    fin = re.search(rf"^#{{1,{nivel}}} ", texto[m.end():], flags=re.M)
    return texto[m.end():m.end() + fin.start()] if fin else texto[m.end():]


class DesignSystemDesdeLaZonaDelProducto(unittest.TestCase):
    """Las variables CSS de la parte del producto que se diseña van antes que las del framework. Las regex toman la
    oración entera que fija la decisión, para que una negación no pase."""

    def setUp(self):
        texto = (SKILLS / "spec-a-html" / "references" / "design-system.md").read_text(encoding="utf-8")
        self.extraer = seccion(texto, "Extraer del código", 2)
        self.antes_de_la_tabla = self.extraer.split("| Stack")[0]

    def test_busca_las_variables_css_de_la_zona_antes_de_la_tabla_por_framework(self):
        self.assertIn("| Stack", self.extraer)
        self.assertRegex(self.antes_de_la_tabla, r"Mira primero la parte del producto que se diseña, no el producto entero:")
        self.assertRegex(self.antes_de_la_tabla, r"Busca variables CSS \(`--\*`\) en las hojas globales y en los componentes de esa parte")
        self.assertRegex(self.antes_de_la_tabla, r"Si las hay, son el design system de esa parte, antes que las del framework:")

    def test_con_variables_propias_igual_compara_con_el_tema_del_framework(self):
        self.assertRegex(self.antes_de_la_tabla, r"Aunque haya variables propias, mira también el tema del framework[^.]*para compararlo")

    def test_pide_confirmar_la_fuente_cuando_hay_mas_de_una(self):
        self.assertRegex(self.antes_de_la_tabla, r"Cuando hay más de una fuente \([^)]*\), muestra a la persona de dónde sale "
                                                 r"cada valor y pídele que confirme de qué parte del producto sale el design system")


class CapturasEnSpecAHtml(unittest.TestCase):
    """Con navegador, capturas por escenario y ancho, revisadas contra el spec antes de pedir el visto bueno. Las regex
    toman la oración entera que fija la decisión, para que una negación no pase."""

    def setUp(self):
        self.texto = (SKILLS / "spec-a-html" / "SKILL.md").read_text(encoding="utf-8")
        self.pasos = re.findall(r"^### (\d+)\. (.+)$", self.texto, flags=re.M)
        self.capturas = seccion(self.texto, "Capturas", 3)

    def numero(self, titulo):
        return next(int(n) for n, t in self.pasos if titulo in t)

    def test_los_pasos_estan_numerados_en_orden(self):
        self.assertEqual([int(n) for n, _ in self.pasos], list(range(1, len(self.pasos) + 1)))

    def test_las_capturas_van_despues_de_escribir_y_antes_de_la_revision_y_el_visto_bueno(self):
        capturas = self.numero("Capturas")
        self.assertLess(self.numero("Escribir el HTML"), capturas)
        self.assertLess(capturas, self.numero("Revisión con la persona"))
        self.assertLess(capturas, self.numero("Guardar"))

    def test_una_captura_por_escenario_y_ancho_sin_panel(self):
        comandos = [l for l in self.capturas.splitlines() if "--screenshot=" in l]
        self.assertTrue(comandos, "el paso no da el comando de la captura")
        for comando in comandos:
            self.assertRegex(comando, r"--window-size=<ancho>,\d+ ")
            self.assertIn("?escenario=<escenario>", comando)
            self.assertIn("proto=0", comando)

    def test_las_vistas_largas_se_capturan_enteras(self):
        self.assertRegex(self.capturas, r"Si la vista es más larga que la ventana[^.]*repite la captura con `--window-size=<ancho>,3000`")
        self.assertIn("full_page=True", self.capturas)

    def test_dice_como_saber_si_hay_navegador(self):
        self.assertIn("command -v google-chrome chromium chromium-browser", self.capturas)
        self.assertRegex(self.capturas, r"`<intérprete> -B -c \"import playwright\"`")

    def test_las_capturas_quedan_en_la_carpeta_de_trabajo_fuera_del_repositorio(self):
        destinos = re.findall(r"--screenshot=(\S+)", self.capturas)
        self.assertTrue(destinos)
        for destino in destinos:
            self.assertTrue(destino.startswith("<trabajo>/"), destino)
        self.assertRegex(self.capturas, r"en una carpeta de trabajo fuera del repositorio[^.]*para que no entren al commit")

    def test_con_navegador_son_obligatorias_y_se_revisan_contra_el_spec(self):
        self.assertRegex(self.capturas, r"Con navegador en la sesión \([^)]*\), las capturas son obligatorias antes de mostrarle la vista a la persona\.")
        self.assertRegex(self.capturas, r"Mira cada captura y revísala contra el spec:")

    def test_un_cambio_en_un_archivo_compartido_se_vuelve_a_capturar_en_todas_las_vistas(self):
        self.assertRegex(self.capturas, r"Si corregiste `components\.css` o `tokens\.css`, vuelve a capturar todas las vistas")

    def test_el_tema_oscuro_se_captura_solo_si_hay_bloque_oscuro(self):
        self.assertRegex(self.capturas, r'Si `tokens\.css` define `\[data-theme="dark"\]`, repite cada escenario en un ancho con `&tema=oscuro`')

    def test_sin_navegador_lo_dice_y_sigue(self):
        self.assertRegex(self.capturas, r"Sin navegador en la sesión, dilo en una línea[^.]*y sigue\.")


class DatosFueraDelSpecEnElChecklist(unittest.TestCase):
    """El checklist tiene un paso explícito, y uno solo, para datos o textos de la vista que el spec no menciona."""

    def setUp(self):
        texto = (SKILLS / "checklist-diseno" / "SKILL.md").read_text(encoding="utf-8")
        self.vinetas = [l for l in seccion(texto, "Revisión de criterio", 3).splitlines() if l.startswith("- **")]

    def vineta(self, titulo):
        encontradas = [l for l in self.vinetas if l.startswith(f"- **{titulo}**")]
        self.assertEqual(len(encontradas), 1, f"no hay una viñeta {titulo!r}: {[l[:40] for l in self.vinetas]}")
        return encontradas[0]

    def test_la_revision_de_criterio_busca_datos_y_textos_que_el_spec_no_menciona(self):
        paso = self.vineta("Datos o textos fuera del spec")
        self.assertRegex(paso, r"Un dato que el spec no menciona \([^)]*\) bloquea:")
        self.assertRegex(paso, r"Un texto que contradice al spec o a otro texto del mismo escenario \([^)]*\) también bloquea\.")
        self.assertRegex(paso, r"Ante la duda, bloquea y se pregunta en la planificación\.")

    def test_lo_que_sobra_deja_los_datos_al_paso_de_datos_o_textos(self):
        sobra = self.vineta("Lo que sobra")
        self.assertNotIn("columna", sobra)
        self.assertRegex(sobra, r"Los datos y los textos se revisan en \"Datos o textos fuera del spec\"\.")

    def test_la_verosimilitud_de_los_datos_no_se_confunde_con_el_paso_de_datos_fuera_del_spec(self):
        self.assertFalse([l for l in self.vinetas if l.startswith("- **Datos**")])
        self.vineta("Datos ficticios")


class SlugsDeLaTablaDelSpec(unittest.TestCase):
    """spec-a-html y html-a-vista nombran los escenarios propios con los slugs de `## Escenarios en pantalla` del spec,
    los base con sus slugs fijos, y no inventan un slug para un estado que la tabla no tiene. Las regex toman la
    oración entera que fija la decisión, para que una negación no pase."""

    def leer(self, *ruta):
        return (SKILLS.joinpath(*ruta)).read_text(encoding="utf-8")

    def test_spec_a_html_planifica_con_los_slugs_de_la_tabla(self):
        plan = seccion(self.leer("spec-a-html", "SKILL.md"), "Plan de vistas", 3)
        self.assertRegex(plan, r"Para elegir los escenarios propios de cada vista, toma de `## Escenarios en pantalla` del "
                               r"spec las filas cuyo alcance es esa pantalla o `global`, y escribe sus slugs igual\.")
        self.assertRegex(plan, r"`checklist-diseno` cruza los slugs con la tabla, no el alcance\.")
        self.assertNotRegex(plan, r"(bloquea|revisa|cruza)[^.]*alcance[^.]*pantalla")
        self.assertRegex(plan, r"Un estado que la vista necesita y la tabla no tiene no lleva un slug inventado: "
                               r"es una decisión de producto[^.]*`grilling-es`[^.]*\.")
        self.assertRegex(plan, r"Si el spec no tiene la tabla[^.]*`checklist-diseno` lo avisa sin bloquear\.")

    def test_la_convencion_de_vista_nombra_los_slugs_de_la_tabla_y_los_base(self):
        escenarios = seccion(self.leer("spec-a-html", "references", "vista-html.md"), "Escenarios", 2)
        self.assertRegex(escenarios, r"Los escenarios propios del spec usan el slug que les da su tabla "
                                     r"`## Escenarios en pantalla`, letra por letra: `plan-expirado`, `pago-rechazado`\.")
        self.assertRegex(escenarios, r"Escenarios base: normal, vacio, cargando, error, sin-permiso, muchos-datos\.")

    def test_html_a_vista_toma_los_slugs_de_la_tabla_en_el_plan(self):
        plan = self.leer("html-a-vista", "references", "plan.md")
        self.assertRegex(plan, r"Con la tabla `## Escenarios en pantalla` en el spec, cada escenario del mockup que "
                               r"coincide con una fila toma su slug, y uno global toma el de la fila con alcance `global`\.")
        self.assertRegex(plan, r"Un estado del mockup que no está en la tabla va al plan como decisión pendiente de "
                               r"producto, no con un slug inventado:[^.]*`checklist-diseno` lo bloquearía\.")

    def test_html_a_vista_nombra_controles_y_globales_con_el_slug_de_la_tabla(self):
        escenarios = self.leer("html-a-vista", "references", "escenarios.md")
        self.assertRegex(escenarios, r"Cada estado que activa es un escenario en `data-escenarios`, con el slug de su fila "
                                     r"en `## Escenarios en pantalla` del spec")
        self.assertRegex(escenarios, r"lleva el mismo nombre en cada vista donde aplica: el slug de su fila con alcance "
                                     r"`global` en la tabla del spec")


class EscenariosDeSpecsAnteriores(unittest.TestCase):
    """Ante un spec con escenarios en una línea, spec-a-tickets los pasa al formato con un nombre y muestra esos nombres
    en la aprobación para que la persona los acepte o los cambie."""

    def test_muestra_los_nombres_nuevos_en_la_aprobacion(self):
        texto = (SKILLS / "spec-a-tickets" / "SKILL.md").read_text(encoding="utf-8")
        self.assertRegex(texto, r"Si el spec es anterior a esta plantilla y trae cada escenario en una línea, pásalo a "
                                r"`### Escenario N: <nombre>` con su bloque `gherkin` sin cambiar lo que dice, con un nombre "
                                r"que resuma su resultado\.")
        aprobacion = seccion(texto, "Aprobación", 3)
        self.assertRegex(aprobacion, r"Si pusiste nombre a escenarios que el spec no nombraba, muéstralos en la tabla del "
                                     r"corte para que la persona los acepte o los cambie antes de publicar\.")


class ReferenciaDeLosTicketsEnGrilling(unittest.TestCase):
    def test_la_oracion_de_la_tabla_no_corta_la_referencia_a_los_tickets(self):
        texto = (SKILLS / "grilling-es" / "SKILL.md").read_text(encoding="utf-8")
        self.assertRegex(texto, r"Si el spec anterior está congelado, los tickets mandan sobre él\. Si no los encuentras ni en el tracker")
        self.assertRegex(texto, r"con quién lo verifica\. Si el spec anterior no tiene `## Escenarios en pantalla`, el spec nuevo la lleva; "
                                r"un spec congelado no se reescribe solo para agregarla\.")


class CompartidosAlDiaEnHtmlAVista(unittest.TestCase):
    """Issue 39: html-a-vista pone al día los compartidos de un repositorio de diseño viejo antes de la ola 1, con el
    script de spec-a-html y por su mismo camino, y se detiene si la persona no acepta. Las regex toman la oración
    entera que fija la decisión, para que una negación no pase."""

    def setUp(self):
        self.texto = (SKILLS / "html-a-vista" / "SKILL.md").read_text(encoding="utf-8")
        self.pasos = re.findall(r"^### (\d+)\. (.+)$", self.texto, flags=re.M)
        self.paso = seccion(self.texto, "Compartidos al día", 3)

    def numero(self, titulo):
        return next(int(n) for n, t in self.pasos if titulo in t)

    def test_los_pasos_estan_numerados_en_orden(self):
        self.assertEqual([int(n) for n, _ in self.pasos], list(range(1, len(self.pasos) + 1)))

    def test_va_despues_del_plan_y_la_rama_y_antes_de_la_ola_1(self):
        self.assertEqual(self.numero("Compartidos al día"), self.numero("Plan y ok") + 1)
        self.assertEqual(self.numero("Ola 1"), self.numero("Compartidos al día") + 1)

    def test_compara_muestra_y_aplica_con_el_script_de_spec_a_html(self):
        for comando in ("comparar", "mostrar", "aplicar"):
            with self.subTest(comando=comando):
                self.assertRegex(self.paso, rf"(?m)^<intérprete> -B <ruta-de-esta-skill>/\.\./spec-a-html/scripts/"
                                            rf"compartidos\.py {comando} <repo-de-diseño>$")

    def test_nombra_las_reglas_que_cambian_lo_propio_y_aplica_solo_con_el_si(self):
        self.assertRegex(self.paso, r"Nombra una por una las reglas de `cambian_lo_propio`: no tienen clase, pintan "
                                    r"elementos que ya existen y cambian cómo se ven las vistas que el repositorio ya tiene\.")
        self.assertRegex(self.paso, r"Escribe solo con el sí de la persona:\n\n```\n<intérprete> -B [^\n]*compartidos\.py aplicar ")

    def test_sin_el_si_se_detiene_por_el_proto_js_viejo_y_las_reglas_que_cambian_lo_propio(self):
        """Q128, que supersede el motivo de Q124: la ola 1 ya copia `.modal`, así que el motivo no es el bloqueo."""
        self.assertRegex(self.paso, r"Sin el sí, detente antes de la ola 1 y no escribas en el repositorio: explica en "
                                    r"simple que sin la puesta al día queda un `proto.js` viejo y entran reglas que cambian "
                                    r"cómo se ven las vistas que el repositorio ya tiene, como `:where\(\[data-frame\]\)`, "
                                    r"sin que la persona las vea antes\.")
        self.assertNotIn("bloquear", self.paso)
        self.assertRegex(self.paso, r"Di qué quedó sin hacer: nombra los compartidos que siguen viejos[^\n]*? y que la "
                                    r"conversión no empezó\.")
        readme = (RAIZ / "README.md").read_text(encoding="utf-8")
        self.assertRegex(readme, r"`html-a-vista` hace lo mismo antes de la ola 1, con el script de `spec-a-html`, y si la "
                                 r"persona no acepta se detiene: sin la puesta al día queda un `proto.js` viejo y entran "
                                 r"reglas que cambian cómo se ven las vistas que ya existen, sin que la persona las vea antes\.")
        self.assertNotIn("bloquearía las vistas que usen lo que falta", readme)

    def test_design_a_medias_arma_tokens_css_desde_el_mockup_y_sigue(self):
        """Q132, que supersede Q129: `design/` con `components.css` o `proto.js` pero sin `tokens.css`."""
        self.assertRegex(self.paso, r"Si `design/` tiene `components.css` o `proto.js` pero no `tokens.css`, el repositorio "
                                    r"quedó a medias:[^\n]*? Detente antes de la ola 1, explícalo en simple y propón armar "
                                    r"`tokens.css` ahora desde el mockup")
        self.assertRegex(self.paso, r"(?m)^<intérprete> -B <ruta-de-esta-skill>/scripts/tokens\.py consolidar "
                                    r"<trabajo>/trozos/\*/estilos\*\.css --roles <repo-de-diseño>/design/components\.css$")
        self.assertRegex(self.paso, r"La tabla lleva también, como roles a llenar, los tokens que usa el `components.css` "
                                    r"viejo, cada uno con un valor del mockup[^\n]*?: así la puesta al día no los agrega con "
                                    r"los valores de la plantilla\.")
        self.assertRegex(self.paso, r"Con el sí a la tabla, escribe `tokens.css` en `design/` del repositorio, corre "
                                    r"`comparar` y sigue con la puesta al día desde ahí\.")
        self.assertRegex(self.paso, r"En la ola 1 ese `tokens.css` ya existe: los valores del mockup se llevan a sus tokens "
                                    r"con `<intérprete> -B <ruta-de-esta-skill>/scripts/tokens\.py mapear`, no se consolidan otra vez\.")
        # Hallazgo 8 de la tercera revisión: el sí de esta detención es el de la tabla, y va junto a él.
        self.assertRegex(self.paso, r"Con el sí a la tabla, escribe `tokens.css` en `design/` del repositorio, corre "
                                    r"`comparar` y sigue con la puesta al día desde ahí\. Sin el sí a la tabla, queda detenida "
                                    r"sin escribir en el repositorio y di qué quedó sin hacer: falta `tokens.css`[^\n]*? y la "
                                    r"conversión no empezó\.")
        # Hallazgo 7: Q136 por propiedad, todos los candidatos y un valor por tema.
        self.assertRegex(self.paso, r"Un rol para el que el mockup no tiene valor se propone con el valor por defecto del "
                                    r"navegador para la propiedad donde lo usa el `components.css`[^\n]*?; producto puede "
                                    r"cambiarlo\.")
        self.assertRegex(self.paso, r"Si el mockup tiene tema oscuro, cada rol lleva además el valor del mockup en ese tema, "
                                    r"que va al bloque del tema en `tokens.css`\.")
        tokens_md = (SKILLS / "html-a-vista" / "references" / "tokens.md").read_text(encoding="utf-8")
        self.assertIn("Roles del components.css del repositorio", tokens_md)
        self.assertIn("--roles", tokens_md)
        self.assertNotIn("deriva a `spec-a-html`", self.paso)
        # Q137: en el design/ a medias la puesta al día va con --solo-usados y agrega solo lo que usa algún compartido.
        for comando in ("comparar", "mostrar", "aplicar"):
            with self.subTest(comando=comando):
                self.assertRegex(self.paso, rf"(?m)^<intérprete> -B <ruta-de-esta-skill>/\.\./spec-a-html/scripts/"
                                            rf"compartidos\.py {comando} <repo-de-diseño> --solo-usados$")
        self.assertRegex(self.paso, r"Con `--solo-usados`, `faltan` trae solo los tokens de la plantilla que usa algún "
                                    r"compartido \(`components.css`, `tokens.css` o `proto.js`\), como `--color-overlay` y `--size-modal` "
                                    r"de las reglas del modal, con los "
                                    r"valores de la plantilla: nómbralos al pedir el sí\. El resto de la escala de la "
                                    r"plantilla queda en `omitidos` y no entra[^\n]*?\.")
        self.assertNotIn("Después de llenar los roles, `faltan` trae todavía", self.paso)
        # Hallazgo 3: si acepta la tabla y rechaza la puesta al día, el `tokens.css` nuevo ya quedó escrito.
        self.assertRegex(self.paso, r"Si en este paso ya escribiste `tokens.css` desde el mockup, di también que quedó "
                                    r"escrito en `design/` del repositorio, sin commit\.")

    def test_si_el_script_sale_con_error_propone_el_arreglo_y_vuelve_a_comparar(self):
        """Q125 con Q131: se detiene, propone corregir lo que el mensaje señala, lo aplica con el sí, vuelve a correr
        `comparar` y sigue; sin el sí queda detenida y dice qué quedó sin hacer."""
        self.assertRegex(self.paso, r"Si el script sale con error, detente antes de la ola 1: explica en simple qué dice el "
                                    r"error y propón corregirlo tú")
        self.assertRegex(self.paso, r"Muestra el cambio antes de escribirlo y, con el sí, corrígelo, vuelve a correr "
                                    r"`comparar` y sigue con la puesta al día desde ahí\.")
        self.assertRegex(self.paso, r"Sin el sí, o si el error no se puede corregir desde la sesión, queda detenida sin "
                                    r"escribir en el repositorio y di qué quedó sin hacer[^.]*\.")
        self.assertNotIn("sigue sin tocar los compartidos", self.paso)
        olas = (SKILLS / "html-a-vista" / "references" / "olas.md").read_text(encoding="utf-8")
        plan = (SKILLS / "html-a-vista" / "references" / "plan.md").read_text(encoding="utf-8")
        self.assertNotIn("Si la puesta al día salió con error", olas)
        self.assertNotIn("salió con error, que no se pusieron al día", plan)

    def test_la_ola_3_parte_del_repositorio_ya_al_dia(self):
        olas = (SKILLS / "html-a-vista" / "references" / "olas.md").read_text(encoding="utf-8")
        integracion = olas.split("## Ola 3")[1].split("**Revisor**")[0]
        self.assertRegex(integracion, r"1\. Copias el repositorio de diseño, ya al día con los compartidos de "
                                      r"`spec-a-html` \(paso 6 de `SKILL\.md`\), en `<trabajo>/ola-3/repo/`")
        self.assertNotIn("copias `proto.js` de `spec-a-html` sin modificar si no existe", integracion)

    def test_compartidos_que_faltan_en_la_ola_3_se_muestran_y_entran_con_el_si(self):
        """Q130 con Q131: quien integra corrige lo de las vistas convertidas; un compartido que no vino de la ola 1 ni de
        la puesta al día se muestra, entra con el sí y se vuelve a correr `revisar.py` antes de seguir."""
        olas = (SKILLS / "html-a-vista" / "references" / "olas.md").read_text(encoding="utf-8")
        integracion = olas.split("## Ola 3")[1].split("**Revisor**")[0]
        self.assertRegex(integracion, r"Lo que bloquea en las vistas convertidas lo corriges tú antes de lanzar al revisor")
        self.assertRegex(integracion, r"puesta al día que aprobó la persona, detente antes de agregarlos: muéstraselos[^.]*\.")
        self.assertRegex(integracion, r"Con el sí, agrégalos a la copia, vuelve a correr `revisar.py` y sigue desde ahí\.")
        self.assertRegex(integracion, r"Sin el sí, queda detenida antes del revisor y di qué vistas quedaron sin integrar "
                                      r"y por qué[^.]*\.")
        # Hallazgo 4: lo que ya está escrito en el repositorio.
        self.assertRegex(integracion, r"Di también que la puesta al día del paso 6 de `SKILL\.md`, y el `tokens.css` si ese "
                                      r"paso lo armó, ya quedaron escritos en el repositorio, sin commit\.")

    def test_lo_nuevo_de_los_contratos_entra_sin_un_si_aparte(self):
        """Q135: Q130 rige solo para lo que no viene de la ola 1, de los contratos ni de la puesta al día."""
        olas = (SKILLS / "html-a-vista" / "references" / "olas.md").read_text(encoding="utf-8")
        integracion = olas.split("## Ola 3")[1].split("**Revisor**")[0]
        self.assertRegex(integracion, r"Las reglas nuevas que piden los contratos de las olas 1 y 2 entran sin un sí aparte: "
                                      r"son parte de la conversión que la persona aprobó en el plan\.")
        self.assertRegex(integracion, r"Si para eso hacen falta reglas o tokens compartidos que no vienen de la ola 1, de los "
                                      r"contratos de la ola 2 ni de la puesta al día que aprobó la persona, detente")

    def test_el_informe_nombra_el_tokens_css_que_armo_el_paso_6(self):
        """Hallazgo 6: el informe dice cuándo el paso 6 armó `tokens.css` desde el mockup."""
        plan = (SKILLS / "html-a-vista" / "references" / "plan.md").read_text(encoding="utf-8")
        resultado = next(l for l in plan.splitlines() if l.startswith("1. **Resultado**"))
        self.assertRegex(resultado, r"Si el paso 6 armó `tokens.css` desde el mockup porque `design/` estaba a medias, dilo, "
                                    r"con los roles del `components.css` viejo que llenó[^\n]*? y los tokens de la plantilla "
                                    r"que entraron con la puesta al día\.")


if __name__ == "__main__":
    unittest.main()
