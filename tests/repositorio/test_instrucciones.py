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

    def test_sin_navegador_propone_instalarlo_y_repite_la_prueba(self):
        """Q153: propone instalar lo que falta, lo instala con el sí y repite la prueba; sin el sí, sigue como antes."""
        self.assertRegex(self.capturas, r"Sin navegador en la sesión, propón instalar Playwright: con el sí, corre "
                                        r"`pip install playwright` y `playwright install chromium`, y repite la prueba de "
                                        r"`<intérprete> -B -c \"import playwright\"`\.")
        self.assertRegex(self.capturas, r"Sin el sí, o si la prueba sigue fallando, dilo en una línea[^.]*y sigue\.")

    def test_si_la_captura_falla_prueba_con_otro_navegador(self):
        self.assertRegex(self.capturas, r"Si la captura falla o sale vacía, prueba con el otro binario o con Playwright")


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
                                    r"navegador para la propiedad donde lo usa el `components.css`[^\n]*?, solo si todas las "
                                    r"propiedades donde se usa comparten ese valor; producto puede cambiarlo\. Si no lo comparten, "
                                    r"o la propiedad no tiene un valor por defecto claro[^\n]*?, la fila dice \"producto decide\" "
                                    r"y no propone nada\.")
        self.assertRegex(self.paso, r"Si el mockup tiene tema oscuro, cada rol lleva además el valor del mockup en ese tema, "
                                    r"que va al bloque del tema en `tokens.css`\.")
        # Q140: el valor por defecto solo donde el token es el valor entero, o el color de un abreviado de borde.
        self.assertRegex(self.paso, r"Ese valor se propone solo donde el token es el valor entero de la declaración, o el "
                                    r"color de un abreviado de borde o de contorno para un `--color-\*`; en otra posición, "
                                    r"como dentro de `calc\(\)`, de una lista de sombras o en el ancho de un abreviado, la "
                                    r"fila dice \"producto decide\", y un token que ocupa solo una parte del valor no recibe "
                                    r"el valor entero del mockup\.")
        tokens_md = (SKILLS / "html-a-vista" / "references" / "tokens.md").read_text(encoding="utf-8")
        self.assertIn("valor entero de la declaración", tokens_md)
        self.assertIn("Roles del components.css del repositorio", tokens_md)
        self.assertIn("--roles", tokens_md)
        # Q141: el límite de los candidatos de medida dentro de calc().
        self.assertRegex(tokens_md, r"Un token de medida dentro de `calc\(\)`, como divisor o multiplicado por otro "
                                    r"`var\(\)`, recibe igual los candidatos del mockup de su propiedad, y ahí pueden ser "
                                    r"CSS inválido[^\n]*?: revisa esa fila antes de elegir\.")
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


class DetencionesConArreglo(unittest.TestCase):
    """Issue 42, criterio 4, con Q131: cada detención que escribe un `SKILL.md` o un `references/*.md` trae su arreglo.

    Cómo se verifica, sobre el texto y sin interpretarlo:
    - Una detención se escribe con "detente", "queda detenida" o "se detiene". Las formas viejas ("para y", "para:",
      "para aquí", "no sigas", "no avances", "no conviertas") no pasan, para que una detención nueva no quede fuera del
      chequeo por estar escrita de otra forma.
    - Cada párrafo, viñeta o paso numerado con una detención dice qué quedó sin hacer, y dice también qué pasa con el
      sí o sin el sí de la persona, o que el arreglo no se puede hacer desde la sesión.
    - Si la detención depende del sí, la sección donde está (hasta el siguiente encabezado) propone el arreglo.
    - Toda sección con una detención vuelve a correr o a probar el chequeo que la detuvo.
    La excepción es Python ausente, que resuelve el issue 45: esas oraciones quedan como están, cada una sola en su
    párrafo, y el test las nombra una por una."""

    BARRIDAS = ("grilling-es", "spec-a-tickets", "spec-a-html", "html-a-vista")
    DETENCION = re.compile(r"\b(?:detente|detenerte|queda detenida|se detiene)\b", re.I)
    FORMA_VIEJA = re.compile(r"\b(?:para y|para aquí|para:|no sigas|no avances|no conviertas)", re.I)
    SIN_HACER = re.compile(r"\bqu[ée]\b[^.]{0,40}?\bqued(?:ó|aron)\b[^.]{0,20}?\bsin\b", re.I)
    SI_O_NO = re.compile(r"\b(?:con|sin) el sí\b|desde la sesión", re.I)
    PROPONE = re.compile(r"\b(?:propón|propone|proponle|ofrece|ofrécele)\b", re.I)
    REPITE = re.compile(r"\bvuelve a (?:correr|probar|leer|mirar|este paso)|\bvuelves a correr|\brepite\b", re.I)
    # Issue 45: sin Python, cada skill sigue como hoy hasta que los scripts pasen a Go (Q151, Q152).
    SIN_PYTHON = {
        "Si no encontraste intérprete, para y no guardes: explica en simple que falta Python 3.9 o superior y que se "
        "instala desde https://www.python.org/downloads/.",
        "Si no encontraste intérprete, para aquí y no escribas en el repositorio: explica en simple que falta Python "
        "3.9 o superior y que se instala desde https://www.python.org/downloads/.",
    }

    @staticmethod
    def unidades(texto):
        """[(sección, unidad)]: cada párrafo y cada viñeta o paso numerado fuera de los bloques de código. La sección es
        el número del encabezado bajo el que está, para no juntar dos secciones con el mismo título."""
        unidades, actual, seccion, bloque = [], [], 0, False

        def cerrar():
            if actual:
                unidades.append((seccion, " ".join(actual)))
                actual.clear()

        for linea in texto.splitlines():
            limpia = linea.strip()
            if limpia.startswith("```"):
                cerrar()
                bloque = not bloque
            elif bloque:
                continue
            elif re.match(r"#{1,6} ", limpia):
                cerrar()
                seccion += 1
            elif not limpia or limpia == "---":
                cerrar()
            elif re.match(r"(?:- |\d+\. )", limpia):
                cerrar()
                actual.append(limpia)
            else:
                actual.append(limpia)
        cerrar()
        return unidades

    @classmethod
    def hallazgos(cls, texto):
        unidades = cls.unidades(texto)
        secciones = {}
        for seccion, unidad in unidades:
            secciones[seccion] = secciones.get(seccion, "") + " " + unidad
        hallazgos = []
        for seccion, unidad in unidades:
            if unidad in cls.SIN_PYTHON:
                continue
            corta = unidad[:90]
            if cls.FORMA_VIEJA.search(unidad):
                hallazgos.append(f"detención escrita de otra forma, usa detente o queda detenida: {corta}")
            if not cls.DETENCION.search(unidad):
                continue
            if not cls.SIN_HACER.search(unidad):
                hallazgos.append(f"no dice qué quedó sin hacer: {corta}")
            if not cls.SI_O_NO.search(unidad):
                hallazgos.append(f"no dice qué pasa con o sin el sí, ni que no se arregla desde la sesión: {corta}")
            elif re.search(r"\b(?:con|sin) el sí\b", unidad, re.I) and not cls.PROPONE.search(secciones[seccion]):
                hallazgos.append(f"su sección no propone el arreglo: {corta}")
            if not cls.REPITE.search(secciones[seccion]):
                hallazgos.append(f"su sección no vuelve a correr el chequeo: {corta}")
        return hallazgos

    def archivos(self, skill):
        return [SKILLS / skill / "SKILL.md", *sorted((SKILLS / skill / "references").glob("*.md"))]

    def test_el_chequeo_encuentra_una_detencion_sin_arreglo(self):
        self.assertTrue(self.hallazgos("Si falta el archivo, detente y explica qué falta."))
        self.assertTrue(self.hallazgos("Si falta el archivo, para y explica qué falta."))
        self.assertTrue(self.hallazgos("Si falta, no sigas: di qué quedó sin hacer."))
        self.assertTrue(self.hallazgos("Si falta el archivo, detente y propón crearlo. Con el sí, créalo y sigue. "
                                       "Sin el sí, queda detenida y di qué quedó sin hacer."), "no repite el chequeo")

    def test_el_chequeo_acepta_una_detencion_con_arreglo(self):
        self.assertEqual(self.hallazgos("Si falta el archivo, detente y propón crearlo. Con el sí, créalo, vuelve a "
                                        "correr el chequeo y sigue. Sin el sí, queda detenida y di qué quedó sin hacer."), [])
        self.assertEqual(self.hallazgos("Si el servidor no responde, el arreglo no se puede hacer desde la sesión: "
                                        "detente y di qué quedó sin hacer. Cuando vuelva, vuelve a correr la orden."), [])
        self.assertEqual(self.hallazgos("## A\n\nSi falta, propón crearlo. Con el sí, créalo y vuelve a correr "
                                        "el chequeo.\n\n- Sin el sí, queda detenida y di qué vistas quedaron sin integrar."), [])

    def test_el_chequeo_no_cuenta_los_bloques_de_codigo(self):
        self.assertEqual(self.hallazgos("```\ndetente\n```"), [])

    def test_cada_detencion_de_las_skills_barridas_trae_su_arreglo(self):
        for skill in self.BARRIDAS:
            for ruta in self.archivos(skill):
                with self.subTest(archivo=str(ruta.relative_to(RAIZ))):
                    self.assertEqual(self.hallazgos(ruta.read_text(encoding="utf-8")), [])


class ReferenciaDeRama(unittest.TestCase):
    """Q143 y Q144: lo que hace una skill cuando `rama.py` o `git` no la dejan guardar vive en `references/rama.md`,
    igual en cada skill que guarda, porque `npx skills` instala cada una por separado (como `rama.py`, Q99)."""

    CON_REFERENCIA = ("grilling-es", "spec-a-tickets", "spec-a-html", "html-a-vista")
    ORIGINAL = SKILLS / "grilling-es" / "references" / "rama.md"

    def setUp(self):
        self.texto = self.ORIGINAL.read_text(encoding="utf-8")

    def test_las_copias_son_iguales_a_la_de_grilling_es(self):
        for skill in self.CON_REFERENCIA:
            with self.subTest(skill=skill):
                ruta = SKILLS / skill / "references" / "rama.md"
                self.assertTrue(ruta.is_file(), "falta la copia")
                self.assertEqual(ruta.read_bytes(), self.ORIGINAL.read_bytes(), "cópiala de skills/grilling-es/references/rama.md")

    def test_cada_skill_lee_la_referencia_al_parar(self):
        for skill in self.CON_REFERENCIA:
            with self.subTest(skill=skill):
                skill_md = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
                parar = [l for l in skill_md.splitlines() if l.startswith("- `parar`: ")]
                self.assertEqual(len(parar), 2, "una viñeta de `parar` tras revisar y otra tras rechazo")
                for linea in parar:
                    self.assertIn("`references/rama.md`", linea)
                self.assertNotIn("el TL dice cómo seguir", skill_md)

    def test_otra_rama_o_trabajo_sin_guardar_se_aparta_en_una_rama_propia_sin_stash(self):
        """Q143."""
        seccion_ = seccion(self.texto, "Otra rama o trabajo sin guardar", 2)
        for motivo in ("otra-rama", "sin-rama", "commits-sin-empujar", "cambios-sin-guardar"):
            self.assertIn(f"`{motivo}`", seccion_)
        self.assertRegex(seccion_, r"propón apartarlo en una rama propia y guardar desde la principal\.")
        self.assertRegex(seccion_, r"No uses `git stash`: lo que se aparta así no queda en ninguna rama y producto no lo "
                                   r"encuentra después\.")
        self.assertIn("`git switch -c apartado/<rama>`", seccion_)
        self.assertIn("`git add -u`", seccion_)
        self.assertIn("`git switch <principal>`", seccion_)
        self.assertIn("`git pull --ff-only`", seccion_)
        self.assertRegex(seccion_, r"Vuelve a correr la misma orden de `rama\.py` y sigue con la `accion` que devuelva\.")
        self.assertRegex(seccion_, r"Di dónde quedó lo anterior:")
        self.assertNotRegex(seccion_, r"`git stash (?:push|pop|apply)")

    def test_sin_servidor_ni_principal_redacta_el_pedido_al_tl(self):
        """Q144."""
        sin_servidor = seccion(self.texto, "Sin servidor", 2)
        self.assertRegex(sin_servidor, r"Detente, redacta el pedido al TL \(sección \"Pedido al TL\"\) y di qué quedó sin hacer\.")
        self.assertRegex(sin_servidor, r"Propón probar de nuevo, y con el sí vuelve a correr la misma orden de `rama\.py`\.")
        self.assertIn("redacta el pedido al TL", seccion(self.texto, "Sin rama principal", 2))
        pedido = seccion(self.texto, "Pedido al TL", 2)
        self.assertRegex(pedido, r"Redáctalo listo para copiar")
        self.assertRegex(pedido, r"No propongas host ni permisos: los decide el TL\.")
        for caso in ("Sin repositorio de diseño", "Sin `origin`", "Sin rama principal", "Credenciales", "Rama nueva rechazada"):
            self.assertIn(f"- {caso}:", pedido)

    def test_las_credenciales_dicen_que_el_commit_quedo_solo_en_esta_maquina(self):
        push = seccion(self.texto, "Push sin credenciales", 2)
        self.assertRegex(push, r"el arreglo no se puede hacer desde la sesión: los accesos los da el TL\.")
        self.assertRegex(push, r"el commit existe solo en esta máquina")
        self.assertRegex(push, r"Cuando el TL dé el acceso, vuelve a correr `git push`")

    def test_la_rama_nueva_va_con_el_si(self):
        nueva = seccion(self.texto, "Rama nueva", 2)
        self.assertRegex(nueva, r"Sin el sí a la rama nueva, queda detenida y di qué quedó sin hacer")


class DetencionesDeGrilling(unittest.TestCase):
    """Issue 42 en `grilling-es`: sin acceso al tracker, sin repositorio de diseño y el criterio de un ticket."""

    def setUp(self):
        self.texto = (SKILLS / "grilling-es" / "SKILL.md").read_text(encoding="utf-8")
        self.guardar = seccion(self.texto, "Guardar", 3)

    def test_sin_acceso_al_tracker_propone_guardar_el_spec_en_el_repositorio(self):
        self.assertRegex(self.guardar, r"Si la lectura falla, detente: explica en simple que la sesión no llega al tracker "
                                       r"y propón guardar el spec en `specs/<épica>/spec\.md` del repositorio de diseño")
        self.assertRegex(self.guardar, r"Sin el sí, queda detenida y di qué quedó sin hacer: el spec aprobado está solo en el chat")

    def test_sin_repositorio_de_diseno_redacta_el_pedido_al_tl(self):
        """Q144."""
        self.assertRegex(self.guardar, r"Si el producto no tiene repositorio de diseño, detente: no lo crees tú, porque el TL "
                                       r"decide el host y los accesos, y eso no se hace desde la sesión\.")
        self.assertRegex(self.guardar, r"Redacta el pedido al TL con `references/rama\.md`, sección \"Pedido al TL\"")

    def test_el_criterio_de_un_ticket_lo_aplica_con_el_si(self):
        cambio = seccion(self.texto, "Cambio a algo que ya existe", 2)
        self.assertRegex(cambio, r"muestra cómo queda el criterio y propón aplicarlo tú\. Con el sí, aplícalo")
        self.assertRegex(cambio, r"vuelve a leer el ticket para confirmar que dice lo nuevo")
        self.assertNotIn("pide que se aplique en el tracker", cambio)


class DetencionesDeSpecATickets(unittest.TestCase):
    """Issue 42 en `spec-a-tickets`: sin spec, spec blando, publicación a medias, tracker sin acceso (Q145) y label que
    no existe en Linear (Q150)."""

    def setUp(self):
        self.texto = (SKILLS / "spec-a-tickets" / "SKILL.md").read_text(encoding="utf-8")
        self.trackers = (SKILLS / "spec-a-tickets" / "references" / "trackers.md").read_text(encoding="utf-8")

    def test_sin_spec_propone_armarlo_con_grilling_y_vuelve(self):
        paso = seccion(self.texto, "1. Conseguir el spec", 3)
        self.assertRegex(paso, r"Si no existe, detente y propón armarlo con `grilling-es` en esta sesión")
        self.assertRegex(paso, r"Con el sí, sigue con `grilling-es` y vuelve a este paso con el spec que deje\.")
        self.assertRegex(paso, r"Sin el sí, queda detenida y di qué quedó sin hacer: no se escribió ningún ticket\.")

    def test_un_spec_blando_vuelve_a_grilling_con_el_si_y_repite_los_controles(self):
        paso = seccion(self.texto, "2. Revisar que el spec alcance", 3)
        self.assertRegex(paso, r"Si fallan dos o más, detente: di qué falta y por qué importa, y propón cerrarlo con "
                               r"`grilling-es` en esta sesión, sobre esos huecos\.")
        self.assertRegex(paso, r"Con el sí, sigue con `grilling-es` y, con el spec que deje, vuelve a correr los cuatro controles\.")
        self.assertNotIn("sugiere volver a `grilling-es`", paso)

    def test_sin_repositorio_de_diseno_redacta_el_pedido_al_tl(self):
        """Q144. El paso 3 trae un bloque con `# Convenciones de gestión`, que corta `seccion`: se busca en el archivo."""
        paso = self.texto
        self.assertRegex(paso, r"Si la sesión tiene que escribir en el repositorio de diseño y el producto no tiene uno, "
                               r"detente: no lo crees tú, porque el TL decide el host y los accesos")
        self.assertRegex(paso, r"Redacta el pedido al TL con `references/rama\.md`, sección \"Pedido al TL\"")

    def test_una_publicacion_a_medias_reintenta_sin_duplicar(self):
        paso = seccion(self.texto, "7. Publicar", 3)
        self.assertRegex(paso, r"Si la creación de un ticket falla a mitad de camino, detente y di qué quedó creado y qué no\.")
        self.assertRegex(paso, r"Busca el que falló por su identificador, para no duplicarlo, y propón reintentarlo\.")
        self.assertRegex(paso, r"Con el sí, reintenta, vuelve a leerlo para confirmar que quedó y sigue con los demás\.")
        self.assertNotIn("para y di qué quedó creado", paso)

    def test_sin_acceso_al_tracker_deja_archivos_y_la_orden_para_el_tl(self):
        """Q145."""
        acceso = seccion(self.trackers, "Acceso", 2)
        self.assertRegex(acceso, r"Nada de lo anterior, o la lectura falla: no pidas credenciales ni las escribas en archivos\. "
                                 r"Publica los tickets como archivos markdown \(sección \"Sin tracker\"\) y deja la orden "
                                 r"lista para que el TL los suba \(sección \"Para que el TL los suba\"\): la persona no queda bloqueada\.")
        subir = seccion(self.trackers, "Para que el TL los suba", 3)
        self.assertIn('`gh issue create --title "<título>" --body-file specs/<épica>/tickets/<archivo> --label "<label>"`', subir)
        self.assertRegex(subir, r"en el orden de la tabla")
        cierre = seccion(self.texto, "10. Cerrar", 3)
        self.assertRegex(cierre, r"Si los tickets quedaron como archivos porque la sesión no llega al tracker, entrega la orden "
                                 r"para el TL y di que en el tracker todavía no hay tickets\.")

    def test_un_label_que_no_existe_en_linear_se_ofrece_crear(self):
        """Q150."""
        linear = seccion(self.trackers, "Linear", 2)
        self.assertRegex(linear, r"Un label de las convenciones que no existe en Linear se ofrece crear: muéstralo y créalo "
                                 r"solo con el sí, como en GitHub\.")
        self.assertNotIn("no un label que se inventa", linear)


class DetencionesDeSpecAHtml(unittest.TestCase):
    """Issue 42 en `spec-a-html`: sin spec, sin repositorio (Q144), cambio de comportamiento, criterio de un ticket,
    puesta al día rechazada (Q147), `compartidos.py` con error y Node ausente (Q153)."""

    def setUp(self):
        self.texto = (SKILLS / "spec-a-html" / "SKILL.md").read_text(encoding="utf-8")

    def test_sin_spec_propone_armarlo_con_grilling_y_vuelve(self):
        paso = seccion(self.texto, "1. Conseguir el spec", 3)
        self.assertRegex(paso, r"Si no existe, detente y propón armarlo con `grilling-es` en esta sesión")
        self.assertRegex(paso, r"Con el sí, sigue con `grilling-es` y vuelve a este paso con el spec que deje\.")
        self.assertNotIn("Sin spec no avances", paso)

    def test_sin_repositorio_de_diseno_redacta_el_pedido_al_tl(self):
        """Q144."""
        paso = seccion(self.texto, "2. Ubicar el repositorio de diseño", 3)
        self.assertRegex(paso, r"Si el producto todavía no tiene repositorio de diseño, detente: no lo crees tú, porque el "
                               r"TL decide el host y los accesos, y eso no se hace desde la sesión\.")
        self.assertRegex(paso, r"Redacta el pedido al TL con `references/rama\.md`, sección \"Pedido al TL\"")

    def test_un_cambio_de_comportamiento_sigue_con_grilling_y_tickets_con_el_si(self):
        paso = seccion(self.texto, "3. Crear o editar", 3)
        self.assertRegex(paso, r"Detente antes de editar y propón seguir en esta sesión con `grilling-es` y después con "
                               r"`spec-a-tickets`")
        self.assertRegex(paso, r"Con el sí, síguelas y vuelve a este paso cuando el spec o los tickets digan el cambio\.")
        self.assertRegex(paso, r"Sin el sí, queda detenida y di qué quedó sin hacer: la vista no se editó\.")

    def test_el_criterio_de_un_ticket_se_aplica_con_el_si_antes_de_la_vista(self):
        paso = seccion(self.texto, "3. Crear o editar", 3)
        self.assertRegex(paso, r"el ticket manda: muestra cómo queda el criterio y propón aplicarlo tú antes de la vista\.")
        self.assertRegex(paso, r"vuelve a leer el ticket para confirmar que dice lo nuevo")

    def test_sin_el_si_a_la_puesta_al_dia_queda_detenida(self):
        """Q147, como `html-a-vista` por Q128."""
        paso = seccion(self.texto, "4. Design system", 3)
        self.assertRegex(paso, r"Sin el sí, detente antes del plan de vistas y no escribas vistas: explica en simple que "
                               r"las vistas que usen lo que falta se verían sin estilo y `checklist-diseno` las bloquearía\.")
        self.assertRegex(paso, r"Di qué quedó sin hacer: nombra los compartidos que siguen viejos[^\n]*? y que no se "
                               r"escribió ninguna vista\.")
        self.assertNotIn("Sin el sí, sigue con lo que hay", paso)

    def test_si_el_script_sale_con_error_propone_el_arreglo_y_vuelve_a_comparar(self):
        paso = seccion(self.texto, "4. Design system", 3)
        self.assertRegex(paso, r"Si el script sale con error, detente: explica en simple qué dice el error y propón corregirlo tú\.")
        self.assertRegex(paso, r"Muestra el cambio antes de escribirlo y, con el sí, corrígelo, vuelve a correr `comparar` "
                               r"y sigue con la puesta al día desde ahí\.")
        self.assertNotIn("sigue sin tocar los compartidos", paso)

    def test_sin_npx_propone_instalar_node_y_repite_la_prueba(self):
        """Q153."""
        paso = seccion(self.texto, "8. Revisión con la persona", 3)
        self.assertRegex(paso, r"Con terminal pero sin `npx`, propón instalar Node\.js, que trae `npx`")
        self.assertIn("`winget install OpenJS.NodeJS.LTS`", paso)
        self.assertRegex(paso, r"Con el sí, instálalo y vuelve a probar `npx --version`")


class DetencionesDeHtmlAVista(unittest.TestCase):
    """Issue 42 en `html-a-vista`: hermanas que faltan (Q154), sin subagentes (Q148), sin repositorio (Q144), mockup que
    no se desarma (Q150), sin navegador (Q153), sin spec, vista sin aprobar tras la segunda revisión (Q149) y las
    comprobaciones antes del commit."""

    def setUp(self):
        self.texto = (SKILLS / "html-a-vista" / "SKILL.md").read_text(encoding="utf-8")
        self.requisitos = seccion(self.texto, "1. Requisitos antes de abrir nada", 3)
        self.olas = (SKILLS / "html-a-vista" / "references" / "olas.md").read_text(encoding="utf-8")

    def test_si_faltan_las_hermanas_ofrece_instalar_el_plugin_completo(self):
        """Q154."""
        pasos = seccion(self.texto, "Pasos", 2).split("### 1.")[0]
        self.assertRegex(pasos, r"Si no están, detente y propón instalar el plugin completo")
        for orden in ("`claude plugin marketplace add grez-lucas/design-flow-skills`",
                      "`claude plugin install flujo-diseno@design-flow-skills`",
                      "`npx skills@latest add grez-lucas/design-flow-skills -a <agente>`"):
            self.assertIn(orden, pasos)
        self.assertRegex(pasos, r"pide reiniciar la sesión y, en la nueva, vuelve a probar")
        self.assertNotIn("pide instalar el flujo completo antes de seguir", pasos)

    def test_sin_subagentes_explica_en_que_cliente_si_los_hay(self):
        """Q148: no deriva a `spec-a-html`."""
        self.assertRegex(self.requisitos, r"detente antes de leer el mockup: la herramienta de subagentes es del cliente, así "
                                          r"que no se arregla desde la sesión\.")
        self.assertRegex(self.requisitos, r"Claude Code, en la terminal o en la app de escritorio, lanza subagentes")
        self.assertRegex(self.requisitos, r"No derives a `spec-a-html`")

    def test_sin_repositorio_de_diseno_redacta_el_pedido_al_tl(self):
        """Q144."""
        self.assertRegex(self.requisitos, r"Si el producto no tiene repositorio de diseño, detente: no lo crees tú, porque el "
                                          r"TL decide el host y los accesos, y eso no se hace desde la sesión\.")
        self.assertIn("`references/rama.md`, sección \"Pedido al TL\"", self.requisitos)

    def test_un_script_sin_cierre_se_repara_en_una_copia_con_el_si(self):
        """Q150."""
        paso = seccion(self.texto, "2. Desarmar", 3)
        self.assertRegex(paso, r"propón reparar una copia en la carpeta de trabajo: el original no se toca\.")
        self.assertRegex(paso, r"Con el sí, copia el mockup a `<trabajo>/reparado/`[^\n]*?muéstrale a la persona qué "
                               r"cerraste y dónde, y vuelve a correr `desarmar\.py` sobre la copia")
        self.assertRegex(paso, r"Una carpeta de trabajo con un manifiesto previo no se pregunta: vuelve a correr con una "
                               r"carpeta nueva")
        self.assertNotIn("no sigas", paso)

    def test_sin_navegador_propone_instalarlo_y_con_framework_sin_el_si_se_detiene(self):
        """Q153."""
        paso = seccion(self.texto, "3. Framework por CDN", 3)
        self.assertRegex(paso, r"Sin navegador en la sesión \(Chrome, Chromium o Playwright\), detente antes de lanzar "
                               r"subagentes: este mockup no se convierte sin render\. Propón instalar Playwright: con el "
                               r"sí, corre `pip install playwright` y `playwright install chromium`, y repite la prueba")
        self.assertRegex(paso, r"Sin el sí, o si la prueba sigue fallando, queda detenida sin escribir en el repositorio y "
                               r"di qué quedó sin hacer")
        self.assertRegex(paso, r"Sin framework por CDN, el navegador sirve para las capturas de la ola 3: si no hay, "
                               r"propón instalarlo igual")
        escenarios = (SKILLS / "html-a-vista" / "references" / "escenarios.md").read_text(encoding="utf-8")
        self.assertRegex(seccion(escenarios, "Capturas", 2), r"Sin navegador, y sin el sí a instalarlo \(paso 3 de "
                                                             r"`SKILL\.md`\), el inventario es la única verificación")

    def test_sin_spec_propone_cerrarlo_con_grilling_desde_el_borrador(self):
        paso = seccion(self.texto, "4. Spec y tickets", 3)
        self.assertRegex(paso, r"\*\*Sin spec\*\*: detente antes de convertir\.")
        self.assertRegex(paso, r"propón cerrarlo con `grilling-es` en esta sesión, con el borrador como punto de partida\.")
        self.assertRegex(paso, r"Con el sí, sigue con `grilling-es`[^.]*? y, cuando exista `specs/<épica>/spec\.md`, vuelve a este paso\.")
        self.assertNotIn("no conviertas", paso)

    def test_una_vista_sin_aprobar_tras_la_segunda_revision_queda_pendiente_con_como_retomarla(self):
        """Q149: no hay tercera vuelta."""
        paso = seccion(self.texto, "9. Ola 3", 3)
        self.assertRegex(paso, r"Si en esa segunda revisión sigue sin aprobarse, no hay tercera vuelta: queda pendiente")
        self.assertRegex(paso, r"va al informe con lo que falta y cómo retomarla en otra corrida")
        self.assertRegex(self.olas, r"Una vuelta por vista, sin tercera: si sigue sin aprobarse, queda pendiente")
        plan = (SKILLS / "html-a-vista" / "references" / "plan.md").read_text(encoding="utf-8")
        pendientes = next((l for l in plan.splitlines() if "**Pendientes**" in l), "")
        self.assertRegex(pendientes, r"cómo retomarla en otra corrida: correr `html-a-vista` de nuevo con el mismo mockup y "
                                     r"pedir solo esa pantalla")

    def test_las_comprobaciones_antes_del_commit_dicen_que_hacer_si_fallan(self):
        paso = seccion(self.texto, "10. Guardar", 3)
        self.assertRegex(paso, r"Si `revisar\.py` bloquea en una vista de esta conversión, esa vista vuelve a su subagente "
                               r"de la ola 2 y al revisor, como una no aprobada")
        self.assertRegex(paso, r"Si falta una pantalla, propón agregarla al plan: con el sí, abre una fila nueva y repite "
                               r"las olas 2 y 3 solo para esa pantalla")
        self.assertIn("`git restore --staged <archivo>`", paso)


if __name__ == "__main__":
    unittest.main()
