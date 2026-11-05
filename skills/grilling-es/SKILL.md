---
name: grilling-es
description: Entrevista a producto sobre un requerimiento, en rondas de preguntas con respuesta recomendada, hasta que no quede ninguna decisión sin tomar, y cierra con un spec en español sobre una plantilla fija (contexto, historias COMO, QUIERO, PARA con escenarios con nombre en gherkin, estados por vista, reglas, decisiones, fuera de alcance y la tabla de escenarios en pantalla con su slug). Usa Lavish para las rondas cuando la sesión tiene terminal, y el chat cuando no. Úsala siempre que alguien de producto traiga una idea, un pedido, una funcionalidad nueva o un cambio a algo existente y haya que pensarlo antes de diseñar o escribir tickets, aunque no diga "grilling" - "quiero agregar recordatorios de pago", "el cliente pide exportar a Excel", "ayúdame a pensar esta funcionalidad", "arma el spec de...", "hazme preguntas sobre esto", "cambiemos cómo funciona el listado", "grilléame". No la uses para escribir tickets desde un spec ya hecho (spec-a-tickets) ni para diseñar pantallas (spec-a-html).
---

# Grilling en español

Entrevista a la persona de producto hasta llegar a un entendimiento compartido del requerimiento, y deja ese entendimiento escrito en un spec. El spec es la entrada de `spec-a-tickets` y de `spec-a-html`: lo que no quede decidido acá vuelve como boceto incompleto en el sprint o como discusión en la demo.

Quien usa esta skill suele ser de producto. Habla en español, en términos de lo que ve y hace el usuario, sin jerga técnica salvo que la persona la use primero.

## Intérprete de Python

Al empezar, una sola vez, busca el intérprete: prueba `python3`, `python` y `py -3`, en ese orden, con `<intérprete> -c "import sys; assert sys.version_info >= (3, 9)"`, y usa el primero que sale sin error como `<intérprete>` en cada orden de esta skill y de sus `references/`, siempre con `-B`, para que Python no deje `__pycache__/` en la carpeta de la skill. Si ninguno pasa la prueba, no corras ninguna orden con Python y sigue lo que esta skill dice para cuando no encontraste intérprete.

## Árbol de decisiones

Trabaja el requerimiento como un árbol: cada decisión abre las que dependen de ella. Las ramas que casi todo requerimiento tiene:

- Problema: qué pasa hoy, a quién le pasa y cuánto cuesta.
- Resultado: qué es verdad cuando esto está hecho, y cómo se sabe.
- Usuarios y roles: quién lo usa, quién no puede, qué ve cada uno.
- Historias: qué quiere hacer cada rol y para qué.
- Flujo: qué pantallas hay y cómo se pasa de una a otra.
- Estados por vista: normal, vacío, cargando, error, sin permiso, muchos datos, y los propios del caso (plan vencido, pago rechazado).
- Reglas de negocio: límites, cálculos, plazos, qué se permite y qué no.
- Datos: qué se muestra y de dónde sale.
- Avisos: correos, notificaciones o mensajes que el sistema manda.
- Fuera de alcance: lo que se deja para después, dicho explícitamente.
- Dependencias: otros equipos, proveedores o decisiones de terceros.

No todas aplican siempre, y aparecen otras. Sigue las que el requerimiento abre.

## Rondas

La frontera es cada decisión cuyos requisitos ya están resueltos: lo que se puede preguntar ahora sin adivinar respuestas que todavía no existen. En cada ronda pregunta toda la frontera, numerada, cada pregunta con tu respuesta recomendada. Una pregunta que depende de otra abierta en la misma ronda va en la ronda siguiente.

No toda pregunta lleva recomendación:

- Las preguntas sobre hechos que solo conoce la persona (el problema, cuánto cuesta hoy, cómo se mide el éxito) van sin recomendación: `➡️ Sin recomendación: es un dato tuyo.` Recomendar ahí es poner palabras en su boca.
- Las que tocan dinero, planes, contabilidad, lo legal o lo que recibe otra persona (el cliente final, un contador, un proveedor: qué datos, qué documentos, qué filtros, qué mensajes) llevan recomendación solo si la persona es quien decide. Si no, pregunta primero quién decide.
- No propongas textos exactos de botones o mensajes ni nombres de archivo, salvo que la persona los traiga. El escenario dice qué comunica ("un texto que explica que no hay facturas en el período") y el texto lo fija `spec-a-html`.

Formato de cada pregunta:

```
❓ P1 - <título corto>: <la pregunta, con opciones si las hay>

➡️ <respuesta recomendada y por qué, en una o dos frases>
```

Los hechos los buscas tú, las decisiones son de la persona. Si una pregunta necesita un dato que está en el código, en el repositorio de diseño, en el tracker o en un spec anterior, búscalo (con un subagente si la sesión los tiene, para no frenar la ronda) en vez de preguntarlo. Solo las preguntas que dependen de ese dato esperan. Lo que tomes de un spec anterior o del código va en el spec como dato de esa fuente, no como algo que dijo la persona; si no lo confirmó, no lo presentes como decidido.

Cuando una decisión no es de la persona (la toma el dueño, finanzas, legal, otro equipo), no la fuerces ni la inventes: regístrala como pendiente con quién decide y sigue con el resto. Si la persona no sabe quién decide, pregúntale quién lo averigua y regístralo como "por definir, lo averigua <persona>". Un pendiente sin nombre no lo resuelve nadie.

Una pregunta que la persona deja sin responder sigue abierta. No la deduzcas de la respuesta vecina.

### Con terminal: Lavish

Si la sesión tiene terminal y `npx`, cada ronda va en un artefacto de Lavish, para que la persona responda con formularios y anote en vez de escribir largo en el chat. Sigue `references/rondas-lavish.md`: trae la plantilla `assets/ronda.html` y los comandos.

Cuando el requerimiento tiene un flujo de varias pantallas, agrega al artefacto un diagrama del flujo entre pantallas: qué pantallas hay y qué acción lleva de una a otra. Sin bocetos de pantalla: cómo se ve cada una lo decide `spec-a-html` después, y un boceto acá ancla el diseño antes de tiempo.

### Sin terminal: chat

Escribe la ronda en el chat con el formato de arriba y pide que respondan por número, o con "ok" las recomendaciones que aceptan.

## Cambio a algo que ya existe

Si el requerimiento cambia algo que ya tiene spec o tickets, busca primero el spec anterior y los tickets (en el tracker, en `specs/<épica>/` y en su historial, con `git log --oneline -- specs/<épica>/`) y léelos: son hechos, no preguntas. Pregunta qué cambia y por qué.

Si el spec anterior está congelado, los tickets mandan sobre él. Si no los encuentras ni en el tracker ni en `specs/<épica>/tickets/`, pide que los peguen antes de la primera ronda. Si no aparecen, dilo y registra como pendiente "verificar que US-... coincide con el ticket vigente", con quién lo verifica. Si el spec anterior no tiene `## Escenarios en pantalla`, el spec nuevo la lleva; un spec congelado no se reescribe solo para agregarla.

- Si el cambio toca comportamiento, estados, flujo o alcance, haz el grilling completo sobre el requerimiento entero, no solo sobre la diferencia, y cierra con un spec nuevo completo que reemplaza al anterior. Las historias que siguen conservan su ID, las nuevas toman el siguiente libre, y las que se retiran van en "Decisiones del grilling" como "Se retira US-...", decidida.
- Si es cosmético (un texto, un color, un orden visual), no hace falta grilling: dilo y sugiere `spec-a-html` directo, con el por qué para el commit. Si el texto o el valor que cambia está escrito en un criterio de aceptación de un ticket, el ticket manda y se actualiza primero: muestra cómo queda el criterio y propón aplicarlo tú. Con el sí, aplícalo en el tracker con la herramienta de la sesión, o en `specs/<épica>/tickets/` si no hay tracker, y vuelve a leer el ticket para confirmar que dice lo nuevo. Si la sesión no llega al tracker o el ticket no aparece en ninguno de los dos, eso no se arregla desde la sesión: entrega el texto nuevo del criterio para que alguien con acceso lo aplique, y di que el ticket sigue con el criterio anterior. Recién después va `spec-a-html`, para que el diseño y el ticket digan lo mismo.

## Cierre

La sesión termina cuando la frontera está vacía: cada rama visitada y nada asumido en silencio. Antes del resumen, recorre cada vista nombrada con los estados base (normal, vacío, cargando, error, sin permiso, muchos datos): cada uno queda decidido, "no aplica" dicho por la persona, o pendiente. Si falta alguno, la frontera no está vacía. Cada escenario que cambia lo que se ve queda con su pantalla, o como global si cambia todas.

Antes de escribir, muestra un resumen de las decisiones, con una línea por rama del árbol que diga "visitada" o "no aplica", y pregunta si llegaron a un entendimiento compartido. No escribas el spec hasta que la persona lo confirme.

### Escribir el spec

Usa la plantilla de `references/plantilla-spec.md` tal cual. Cada historia sale de una decisión del grilling, y cada escenario dice solo lo que se decidió: un escenario que agregas por tu cuenta es una decisión que la persona no tomó. Lo pendiente va en "Decisiones del grilling" como pendiente, con quién decide.

El spec cierra con `## Escenarios en pantalla`: un slug por escenario con estado visible, con el nombre de su `### Escenario N` y su alcance. Las vistas declaran esos slugs y `checklist-diseno` bloquea un escenario de una vista que no está ahí ni es base, así que un nombre mal copiado se nota en la revisión.

Muestra el spec completo y ajusta hasta que la persona lo apruebe.

### Guardar

- Si el proyecto tiene tracker, guarda el spec como documento de la épica o del proyecto (en Linear, un documento del proyecto; en GitHub o GitLab, la descripción de la épica o un issue de spec). Usa la herramienta que tenga la sesión y verifica el acceso con una lectura antes de escribir. Si la lectura falla, la sesión no llega al tracker, y eso no detiene el guardado: guarda el spec en `specs/<épica>/spec.md` del repositorio de diseño por el camino sin tracker de la viñeta siguiente, como `spec-a-tickets` con los tickets, entrega su texto para que el TL lo suba al tracker, y di al cerrar que el documento del tracker quedó sin crear.
- Si no hay tracker, guárdalo en `specs/<épica>/spec.md` del repositorio de diseño, con `<épica>` en minúsculas y con guiones. Haz commit y push a la rama actual después de mostrar el resumen y pedir confirmación, con el mensaje `spec(<épica>): <resumen>`, por ejemplo `spec(recordatorios): recordatorio por correo antes del vencimiento`. Revisa que el `.gitignore` de la raíz del repositorio de diseño tenga la línea `.lavish/`; si no la tiene, agrégala, y crea el archivo si falta: las rondas con Lavish escriben ahí archivos que no son diseño. Agrega solo esa carpeta, con `git add specs/<épica>/`, y `git add .gitignore` si le agregaste `.lavish/`; nunca `git add -A` ni `git add .`: si las skills se instalaron en el proyecto con `npx skills`, `.agents/`, `.claude/skills/` y `skills-lock.json` quedan sin seguimiento y no van en el commit. El resumen lista solo los archivos que entran en el commit.

Si el producto no tiene repositorio de diseño, detente: no lo crees tú, porque el TL decide el host y los accesos, y eso no se hace desde la sesión. Redacta el pedido al TL con `references/rama.md`, sección "Pedido al TL", y di qué quedó sin hacer: el spec aprobado está solo en el chat, así que entrégalo completo. Cuando el TL lo cree, vuelve a correr este paso.

Sin tracker, antes de escribir el spec en el repositorio de diseño, no recién al hacer el commit, decide la rama, porque cambiar de rama con archivos sin guardar puede fallar. Corre, con la ruta absoluta de esta skill en lugar de `<ruta-de-esta-skill>` y desde el repositorio de diseño:

```
<intérprete> -B <ruta-de-esta-skill>/scripts/rama.py revisar --tipo spec --epica <épica>
```

Si no encontraste intérprete, para y no guardes: explica en simple que falta Python 3.9 o superior y que se instala desde https://www.python.org/downloads/.

Si `rama.py` sale con error o no devuelve un JSON, aquí o tras un rechazo, detente sin escribir en el repositorio y sigue `references/rama.md`, sección "Error de rama.py": si el nombre termina en guion y número, propón otro, por ejemplo `fase-dos` en lugar de `fase-2`, y con el sí vuelve a correrlo; sin el sí, queda detenida y di qué quedó sin hacer.

El script trae lo nuevo del servidor, no cambia de rama y devuelve un JSON con una `accion`:

- `guardar`: antes de escribir, sigue `references/rama.md`, sección "Antes de guardar": el trabajo sin guardar de otra persona y una principal adelantada entrarían en tu commit. Si pasa, guarda en la rama actual.
- `volver`: la rama ya no está en el servidor, por ejemplo porque el TL hizo el merge y la borró, y lo que tenía ya está en la principal. Corre `git switch <principal>`, con la `principal` del JSON, y `git pull --ff-only`, y guarda ahí, después de "Antes de guardar". Si uno falla, sigue `references/rama.md`, sección "Volver que falla".
- `parar`: no escribas todavía en el repositorio. Explica en simple el `detalle` y en qué rama estás, y sigue `references/rama.md`, que da el arreglo de cada `motivo`: apartar lo que había en una rama propia y guardar desde la principal, o redactar el pedido al TL cuando falta el servidor.

El push va a la rama actual, con `git push`. Si falla por credenciales, porque el servidor no reconoce el usuario o el token, sigue `references/rama.md`, sección "Push sin credenciales": el TL es quien da los accesos, y el commit queda solo en esta máquina. Si lo rechaza por cualquier motivo que no sea de credenciales (la rama está protegida, o tiene cambios que tu copia no tiene), no lo arregles en esa rama, sin `git pull --rebase`, `git reset --hard` ni `--force`: el TL resuelve en el merge request. Pide la rama nueva, desde el repositorio de diseño, con `<intérprete> -B <ruta-de-esta-skill>/scripts/rama.py rechazo --tipo spec --epica <épica>`.

- `rama-nueva`: explica en simple que el servidor no aceptó el cambio en esa rama y propón pasarlo a la rama nueva. Con el sí, pasa el commit con `git switch -c <rama_nueva>` y empújalo con `git push -u origin <rama_nueva>`; deja la `rama` de la que saliste como está en el servidor con `git branch -f <rama> origin/<rama>`. Explica que el spec quedó en la rama nueva y que el TL revisa y hace el merge request. Sin el sí, o si un comando falla, sigue `references/rama.md`, sección "Rama nueva".
- `parar`: explica en simple el `detalle` y que el TL es quien da los accesos, y sigue `references/rama.md`, sección "Rama nueva rechazada".

Si reemplaza a un spec anterior, agrega al inicio del anterior una línea `> Superado el <fecha> por <enlace o ruta al spec nuevo>.` y no toques el resto: el spec anterior es historia. Sin tracker, el spec nuevo ocupa `specs/<épica>/spec.md`, que es donde lo buscan `spec-a-tickets` y `spec-a-html`, y el anterior se mueve sin cambios, salvo esa línea, a `specs/<épica>/anteriores/spec-<fecha>.md`, con la fecha de su línea `Congelado`, o la de hoy si no tiene.

### Siguiente paso

Cierra diciendo dónde quedó el spec, qué quedó pendiente y con quién, y el siguiente paso: `spec-a-tickets` con este spec para escribir los tickets, y después, en una sesión nueva, `spec-a-html` para dibujar las vistas. Nombra cada skill como figura en tu lista de skills: instaladas como plugin de Claude Code son `flujo-diseno:spec-a-tickets` y `flujo-diseno:spec-a-html`; con `npx skills`, `spec-a-tickets` y `spec-a-html`.
