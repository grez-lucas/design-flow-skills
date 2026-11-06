---
name: spec-a-tickets
description: Convierte un spec de producto con historias de usuario en tickets listos para construir, una story por historia, con la historia COMO, QUIERO, PARA, los escenarios del spec copiados tal cual como criterios de aceptación, pruebas E2E, enlace a la vista de diseño, casos borde y preguntas abiertas. Los publica en el tracker del proyecto (Linear, GitHub, GitLab u otro) o, si no hay tracker, como un archivo markdown por ticket en specs/<épica>/tickets/. Úsala siempre que producto quiera pasar un spec, una épica o unas historias a tickets, issues o stories, aunque no lo diga así - "crea los tickets de este spec", "pasa las historias a Linear", "arma las stories de la épica", "sube esto al tablero", "escribe los criterios de aceptación", "genera los issues para DEV". No la uses para hacer el grilling de un requerimiento (grilling-es), para diseñar pantallas (spec-a-html) ni para cortar trabajo técnico de ingeniería en subtareas.
---

# Spec a tickets

Convierte un spec en los tickets que DEV construye. Los tickets se escriben antes del HTML: el ticket es la fuente de lo que se acepta, y el diseño se dibuja después contra esos criterios.

Quien usa esta skill suele ser de producto. Habla en español, sin jerga técnica salvo que la persona la use primero.

La skill redacta. La persona de producto es dueña de los criterios de aceptación y aprueba antes de publicar. No es un trámite: los criterios son el contrato con el negocio, y un contrato inventado en nombre de alguien no es un contrato.

## Intérprete de Python

Al empezar, una sola vez, busca el intérprete: prueba `python3`, `python` y `py -3`, en ese orden, con `<intérprete> -c "import sys; assert sys.version_info >= (3, 9)"`, y usa el primero que sale sin error como `<intérprete>` en cada orden de esta skill y de sus `references/`, siempre con `-B`, para que Python no deje `__pycache__/` en la carpeta de la skill. Si ninguno pasa la prueba, no corras ninguna orden con Python y sigue lo que esta skill dice para cuando no encontraste intérprete.

## Skills hermanas

Esta skill es parte de un flujo de cinco: `grilling-es`, `spec-a-tickets`, `spec-a-html`, `html-a-vista` y `checklist-diseno`. Antes de seguir con una, comprueba que esté instalada: que figure en tu lista de skills, o que exista `../<hermana>/SKILL.md` junto a esta skill. Con `npx skills` se instalan de a una, y una puede faltar.

Detente. Si falta una hermana, propón instalar el plugin completo, que trae las cinco juntas. Con el sí, si esta skill está bajo `.claude/plugins/`, corre `claude plugin marketplace add grez-lucas/design-flow-skills` y `claude plugin install flujo-diseno@design-flow-skills`; si vino con `npx skills`, corre `npx skills@latest add grez-lucas/design-flow-skills -a <agente>` desde la carpeta donde se instaló, con `-g` si está a nivel de usuario. Las skills nuevas se cargan al abrir una sesión: pide reiniciar la sesión y, en la nueva, vuelve a probar que la hermana esté antes de seguir. Sin el sí, o si la instalación falla, queda detenida y di qué quedó sin hacer.

## Pasos

### 1. Conseguir el spec

El spec llega por enlace al tracker, adjunto o pegado en el chat, o como `specs/<épica>/spec.md` en el repositorio de diseño. Si la sesión no puede leer el enlace, pide que lo peguen. Sin spec no hay tickets, y no se reconstruye el requerimiento de memoria: búscalo antes en `specs/*/spec.md` del repositorio de diseño y en el tracker.

Detente. Si el spec no existe, propón armarlo con `grilling-es` en esta sesión (`flujo-diseno:grilling-es` si está instalada como plugin de Claude Code). Con el sí, sigue con `grilling-es`, o con "Skills hermanas" si no está, y vuelve a este paso con el spec que deje. Sin el sí, queda detenida y di qué quedó sin hacer: no se escribió ningún ticket.

El spec sigue una plantilla con contexto, historias COMO, QUIERO, PARA con sus escenarios `### Escenario N: <nombre>` en un bloque `gherkin`, estados por vista, reglas, decisiones, fuera de alcance, enlaces y la tabla `## Escenarios en pantalla`. La tabla es para las vistas: no pasa a los tickets, que ya llevan cada escenario con su nombre.

### 2. Revisar que el spec alcance

Un spec blando produce tickets prolijos y equivocados, y publicados se ven oficiales. Antes de redactar, revisa:

- Cada historia dice quién, qué y para qué.
- Cada historia tiene al menos un escenario con resultado observable.
- Las reglas que cambian el comportamiento tienen respuesta, o están marcadas como pendientes con quién decide.
- Está claro qué queda fuera de alcance.

Si falla uno, sigue y llévalo a "Open Questions" del ticket que corresponda.

Detente. Si fallan dos o más, di qué falta y por qué importa, y propón cerrarlo con `grilling-es` en esta sesión, sobre esos huecos. Con el sí, sigue con `grilling-es`, o con "Skills hermanas" si no está, y, con el spec que deje, vuelve a correr los cuatro controles. Sin el sí, queda detenida y di qué quedó sin hacer: no se escribió ningún ticket.

No rellenes un criterio con una suposición: una suposición publicada como criterio de aceptación es exactamente la falla que este paso evita.

### 3. Leer las convenciones del proyecto

Busca `.claude/pm-conventions.md` en el repositorio de diseño y, si no está, en el repositorio de código si está a mano. Si el archivo apunta a otro lugar, una ruta o una URL, lee las convenciones ahí; si la sesión no puede abrirlas, pide que las peguen. Las convenciones mandan: usa su tracker, su plantilla, sus labels, su formato de título y de ID y su estado inicial.

Si no las encuentras, no supongas que no hay: pregunta a la persona dónde están. Suelen vivir en otro repositorio del producto o en una wiki, con reglas que pesan, como qué documento manda sobre otro o el formato de ID del tracker. Acepta una ruta o una URL, aunque esté fuera del repositorio de diseño, léelas ahí y, con la rama revisada como dice el final de este paso, guarda el puntero en `.claude/pm-conventions.md` del repositorio de diseño, para que la próxima sesión las encuentre sin preguntar:

```markdown
# Convenciones de gestión

Las convenciones de gestión de este proyecto están en <ruta o URL>.
```

Una ruta local solo existe en las máquinas que la tienen: si las convenciones están en un repositorio con URL, guarda la URL. El puntero entra en el commit de los tickets (paso 9).

Si la persona dice que no hay convenciones, el puntero no va: usa la plantilla de `references/plantilla-story.md` y pregunta solo lo que no puedes ver: si hay tracker y cuál. Sin tracker, los tickets van como archivos markdown.

Si la sesión va a escribir en el repositorio de diseño (el puntero de este paso, los tickets como archivos del paso 7 o el spec congelado del paso 8), antes del primer archivo decide la rama: el paso 9 guarda en la rama actual, y cambiar de rama con archivos sin guardar puede fallar.

Detente. Si la sesión tiene que escribir en el repositorio de diseño y el producto no tiene uno, no lo crees tú, porque el TL decide el host y los accesos, y eso no se hace desde la sesión. Redacta el pedido al TL con `references/rama.md`, sección "Pedido al TL", y di qué quedó sin hacer: lo que iba al repositorio (el puntero, los tickets como archivos o el spec congelado) no se escribió. Cuando el TL lo cree, vuelve a correr este paso.

Corre, con la ruta absoluta de esta skill en lugar de `<ruta-de-esta-skill>` y desde el repositorio de diseño:

```
<intérprete> -B <ruta-de-esta-skill>/scripts/rama.py revisar --tipo tickets --epica <épica>
```

Si no encontraste intérprete, para y no guardes: explica en simple que falta Python 3.9 o superior y que se instala desde https://www.python.org/downloads/.

Detente. Si `rama.py` sale con error o no devuelve un JSON, aquí o tras un rechazo, no escribas en el repositorio y sigue `references/rama.md`, sección "Error de rama.py": si el nombre termina en guion y número, propón otro, por ejemplo `fase-dos` en lugar de `fase-2`, y con el sí vuelve a correrlo; sin el sí, queda detenida y di qué quedó sin hacer.

El script trae lo nuevo del servidor, no cambia de rama y devuelve un JSON con una `accion`:

- `guardar`: antes de escribir, sigue `references/rama.md`, sección "Antes de guardar": el trabajo sin guardar de otra persona, lo que dejó preparado en el índice y una principal adelantada entrarían en tu commit. Si pasa, guarda en la rama actual, con el commit de "El commit de la skill".
- `volver`: la rama ya no está en el servidor, por ejemplo porque el TL hizo el merge y la borró, y lo que tenía ya está en la principal. Corre `git switch <principal>`, con la `principal` del JSON, y `git pull --ff-only`, y guarda ahí, después de "Antes de guardar". Si uno falla, sigue `references/rama.md`, sección "Volver que falla".
- `parar`: Detente. Todavía no escribas en el repositorio: explica en simple el `detalle` y en qué rama estás, y sigue `references/rama.md`, que da el arreglo de cada `motivo`. Con `otra-rama`, `sin-rama`, `commits-sin-empujar` o `cambios-sin-guardar`, propón apartar lo que había en una rama propia y, con el sí, apártalo y vuelve a correr la misma orden de `rama.py`; cuando falta el servidor, eso no se arregla desde la sesión y va el pedido al TL. Sin el sí, di qué quedó sin hacer.

### 4. Cortar

Una historia del spec es un ticket. Es la unidad que producto entiende y acepta; las subtareas técnicas las agrega DEV después.

Propón partir una historia solo cuando es claramente demasiado grande, por ejemplo con más de cinco escenarios o con dos capacidades distintas en la misma frase. Cada parte tiene que poder aceptarse por sí sola. Dilo y espera la confirmación.

Si una historia depende de otra (no se puede ver el listado de invitaciones sin poder invitar), anótalo como dependencia.

### 5. Redactar

Sigue la plantilla del proyecto o la de `references/plantilla-story.md`. Lo esencial:

- **Título** con el formato de ID de las convenciones cuando lo definen (`INV-12: Registrar ingreso de mercadería`), también si el spec trae otro identificador: el ticket se busca en el tracker por ese ID. El identificador del spec queda en el cuerpo, junto al enlace al spec, para rastrear la historia. Si el tracker asigna el ID al crear el ticket, no lo inventes: el ticket queda con el que devuelve el tracker, y si los tickets van como archivos porque todavía no hay acceso al tracker, el título lleva el identificador del spec hasta que pasen. Sin formato en las convenciones, usa el identificador del spec si lo trae (`[US-REC-001] Ver facturas vencidas`) y, si no lo trae, `[US-<ÁREA>-NNN]`, con un código corto de la épica en mayúsculas.
- **Descripción**: la historia COMO, QUIERO, PARA como está en el spec y un párrafo de contexto tomado del spec.
- **Criterios de aceptación**: los escenarios de la historia, copiados tal cual del spec: el mismo `### Escenario N: <nombre>` y el mismo bloque `gherkin`. Afirman comportamiento y datos que se ven, nunca rutas de archivos ni detalles de implementación. Un estado de "Estados por vista" que no es escenario va a casos borde si el spec dice qué pasa, o a preguntas abiertas. Si el spec es anterior a esta plantilla y trae cada escenario en una línea, pásalo a `### Escenario N: <nombre>` con su bloque `gherkin` sin cambiar lo que dice, con un nombre que resuma su resultado.
- **Pruebas**: redacta los flujos E2E a partir de los escenarios. Deja las pruebas unitarias y de integración marcadas "Lo completa DEV": producto no tiene cómo validarlas.
- **Diseño**: la ruta donde va a quedar la vista, `design/vistas/<épica>/<vista>.html`, marcada "pendiente". Es la misma ruta que usa `spec-a-html`, así que el enlace queda bien sin volver a editar el ticket.
- **Casos borde**: tabla con los del spec y los que aparecen al redactar, cada uno con su comportamiento esperado. Si no sabes el comportamiento, va a preguntas abiertas, no a la tabla.
- **Preguntas abiertas**: todo lo que el spec no responde.

Un criterio de aceptación dice solo lo que el spec dice. Aunque un agregado parezca obvio ("el valor negativo no se guarda", "ordenado de mayor a menor"), si el spec no lo afirma va como pregunta abierta, no como criterio: la persona de producto lo confirma y recién ahí pasa a criterio.

Si la plantilla del proyecto no tiene sección de preguntas abiertas, casos borde o pruebas, no la agregues al ticket: deja las preguntas en el índice `specs/<épica>/tickets/README.md` o, con tracker, en un comentario del ticket, y dilo al cerrar.

### 6. Aprobación

Muestra el corte en una tabla (identificador, título, escenarios, dependencias) y el primer ticket completo con la plantilla aplicada. Es mucho más barato corregir la plantilla una vez que en diez tickets. Si pusiste nombre a escenarios que el spec no nombraba, muéstralos en la tabla del corte para que la persona los acepte o los cambie antes de publicar.

Si la sesión tiene terminal y `npx` disponible, muéstralo en Lavish para que la persona anote sobre el ticket:

```
npx -y lavish-axi <archivo.html>
npx -y lavish-axi poll <archivo.html>
```

Sin terminal, muéstralo en el chat. Ajusta hasta que la persona apruebe. Publica solo con un sí explícito.

### 7. Publicar

Sigue `references/trackers.md` según dónde van los tickets. En todos los casos:

1. Verifica el acceso con una lectura antes de escribir.
2. Busca tickets que ya cubran estas historias. Si el spec reemplaza a uno anterior (lo dice su sección "Enlaces"), los tickets que llevan el mismo identificador del spec, en el título o en el cuerpo, son de este spec: muestra qué cambia en cada uno y actualízalos con aprobación explícita; las historias que el spec retira se informan, no se cierran. Cualquier otro ticket que encuentres es ajeno: muéstralo y pregunta si se extiende, se reemplaza o se omite, y nunca lo edites ni lo cierres.
3. Crea los tickets en orden de dependencias, para que cada uno cite identificadores reales.
4. Detente. Si la creación de un ticket falla a mitad de camino, di qué quedó creado y qué no. Busca el que falló por su identificador, para no duplicarlo, y propón reintentarlo. Con el sí, reintenta, vuelve a leerlo para confirmar que quedó y sigue con los demás. Si falla de nuevo o la sesión perdió el acceso al tracker, eso no se arregla desde la sesión: deja los que faltan como archivos, como dice `references/trackers.md`, sección "Acceso", y di qué quedó sin hacer. Sin el sí, queda detenida y di qué quedó sin hacer.

### 8. Congelar el spec

Agrega una línea al inicio del spec, en el tracker o en `specs/<épica>/spec.md`:

```
> Congelado el 2026-10-26: los tickets US-REC-001 y US-REC-002 mandan. Un cambio posterior pasa por grilling y actualiza los tickets.
```

En la misma edición, completa "Tickets" en "Enlaces" con los identificadores reales. Desde ahí, el spec no se reescribe: los tickets son la fuente de lo que se acepta.

### 9. Guardar en el repositorio de diseño

Si la sesión escribió en el repositorio de diseño, haz commit y push a la rama actual después de mostrar el resumen y pedir la confirmación, con el mensaje `tickets(<épica>): <resumen>`, por ejemplo `tickets(recordatorios): US-REC-001 y US-REC-002 desde el spec`. Es un solo commit al final, para que todo llegue junto. El resumen lista solo los archivos que entran en el commit. Si la sesión no escribió nada en el repositorio, no hay commit.

Revisa que el `.gitignore` de la raíz del repositorio de diseño tenga la línea `.lavish/`; si no la tiene, agrégala, y crea el archivo si falta: las revisiones con Lavish escriben ahí archivos que no son diseño.

Agrega solo lo que escribiste:

- Los tickets sin tracker y el spec congelado: `git add specs/<épica>/`.
- El puntero a las convenciones, si lo escribiste en esta sesión: `git add .claude/pm-conventions.md`. Si git responde que la ruta está ignorada, sigue el párrafo de abajo.
- El `.gitignore`, si le agregaste `.lavish/`: `git add .gitignore`.

Si git responde que `.claude/pm-conventions.md` está ignorada, no la fuerces con `-f`: propón agregar la excepción al final del `.gitignore` de la raíz. Al final vale sobre cualquier regla anterior de ese archivo, del excludes global y de `.git/info/exclude`, sea `.claude/`, `.*`, `**/.claude/` o un `*.md`, y el resto de `.claude/`, como `.claude/skills/`, sigue ignorado:

```
!.claude/
.claude/*
!.claude/pm-conventions.md
```

Muestra el cambio y, con el sí, escríbelo, vuelve a correr `git check-ignore .claude/pm-conventions.md`, sin `-v`, que ya no debe responder nada, y agrégalo con `git add .claude/pm-conventions.md` y `git add .gitignore`. El cuerpo del mensaje del commit lo dice: `Excepción en .gitignore para .claude/pm-conventions.md.` Sin el sí, el puntero queda solo en esta máquina: dilo en el resumen.

Detente. Si `git check-ignore .claude/pm-conventions.md` sigue respondiendo, la regla está fuera del `.gitignore` de la raíz: muestra la línea que da `git check-ignore -v .claude/pm-conventions.md`, y como eso no se arregla desde la sesión, redacta el pedido al TL con `references/rama.md`, sección "Pedido al TL", y di qué quedó sin hacer: el puntero queda solo en esta máquina y lo demás se guarda. Cuando el TL cambie la regla, vuelve a correr `git check-ignore`.

Nunca `git add -A` ni `git add .`: si las skills se instalaron en el proyecto con `npx skills`, `.agents/`, `.claude/skills/` y `skills-lock.json` quedan sin seguimiento y no van en el commit.

La rama quedó revisada en el paso 3. El push va a la rama actual, con `git push`. Si falla por credenciales, porque el servidor no reconoce el usuario o el token, sigue `references/rama.md`, sección "Push sin credenciales": el TL es quien da los accesos, y el commit queda solo en esta máquina. Si lo rechaza por cualquier motivo que no sea de credenciales (la rama está protegida, o tiene cambios que tu copia no tiene), no lo arregles en esa rama, sin `git pull --rebase`, `git reset --hard` ni `--force`: el TL resuelve en el merge request. Pide la rama nueva, desde el repositorio de diseño, con `<intérprete> -B <ruta-de-esta-skill>/scripts/rama.py rechazo --tipo tickets --epica <épica>`.

- `rama-nueva`: explica en simple que el servidor no aceptó el cambio en esa rama y propón pasarlo a la rama nueva. Con el sí, pasa el commit con `git switch -c <rama_nueva>` y empújalo con `git push -u origin <rama_nueva>`; deja la `rama` de la que saliste como está en el servidor con `git branch -f <rama> origin/<rama>`. Explica que los tickets quedaron en la rama nueva y que el TL revisa y hace el merge request. Sin el sí, o si un comando falla, sigue `references/rama.md`, sección "Rama nueva".
- `parar`: explica en simple el `detalle` y que el TL es quien da los accesos, y sigue `references/rama.md`, sección "Rama nueva rechazada".

### 10. Cerrar

Entrega la tabla de identificadores y títulos con sus enlaces, las preguntas abiertas que quedaron y el siguiente paso. Si los tickets quedaron como archivos porque la sesión no llega al tracker, entrega la orden para el TL y di que en el tracker todavía no hay tickets. El siguiente paso es `spec-a-html` con el mismo spec, en una sesión nueva, para dibujar las vistas. Nombra la skill como figura en tu lista de skills: instalada como plugin de Claude Code es `flujo-diseno:spec-a-html`; con `npx skills`, `spec-a-html`.
