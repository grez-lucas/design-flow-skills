---
name: grilling-es
description: Entrevista a producto sobre un requerimiento, en rondas de preguntas con respuesta recomendada, hasta que no quede ninguna decisión sin tomar, y cierra con un spec en español sobre una plantilla fija (contexto, historias "Como, quiero, para" con escenarios "Dado, cuando, entonces", estados por vista, reglas, decisiones, fuera de alcance). Usa Lavish para las rondas cuando la sesión tiene terminal, y el chat cuando no. Úsala siempre que alguien de producto traiga una idea, un pedido, una funcionalidad nueva o un cambio a algo existente y haya que pensarlo antes de diseñar o escribir tickets, aunque no diga "grilling" - "quiero agregar recordatorios de pago", "el cliente pide exportar a Excel", "ayúdame a pensar esta funcionalidad", "arma el spec de...", "hazme preguntas sobre esto", "cambiemos cómo funciona el listado", "grilléame". No la uses para escribir tickets desde un spec ya hecho (spec-a-tickets) ni para diseñar pantallas (spec-a-html).
---

# Grilling en español

Entrevista a la persona de producto hasta llegar a un entendimiento compartido del requerimiento, y deja ese entendimiento escrito en un spec. El spec es la entrada de `spec-a-tickets` y de `spec-a-html`: lo que no quede decidido acá vuelve como boceto incompleto en el sprint o como discusión en la demo.

Quien usa esta skill suele ser de producto. Habla en español, en términos de lo que ve y hace el usuario, sin jerga técnica salvo que la persona la use primero.

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

Si el requerimiento cambia algo que ya tiene spec o tickets, busca primero el spec anterior y los tickets (en el tracker o en `specs/<épica>/`) y léelos: son hechos, no preguntas. Pregunta qué cambia y por qué.

Si el spec anterior está congelado, los tickets mandan sobre él. Si no los encuentras ni en el tracker ni en `specs/<épica>/tickets/`, pide que los peguen antes de la primera ronda. Si no aparecen, dilo y registra como pendiente "verificar que US-... coincide con el ticket vigente", con quién lo verifica.

- Si el cambio toca comportamiento, estados, flujo o alcance, haz el grilling completo sobre el requerimiento entero, no solo sobre la diferencia, y cierra con un spec nuevo completo que reemplaza al anterior. Las historias que siguen conservan su ID, las nuevas toman el siguiente libre, y las que se retiran van en "Decisiones del grilling" como "Se retira US-...", decidida.
- Si es cosmético (un texto, un color, un orden visual), no hace falta grilling: dilo y sugiere `spec-a-html` directo, con el por qué para el commit. Si el texto o el valor que cambia está escrito en un criterio de aceptación de un ticket, el ticket manda y se actualiza primero: muestra cómo queda el criterio, y pide que se aplique en el tracker, o edítalo en `specs/<épica>/tickets/` si no hay tracker. Si el ticket no aparece en ninguno de los dos, entrega el texto nuevo del criterio para que alguien con acceso lo aplique. Recién después va `spec-a-html`, para que el diseño y el ticket digan lo mismo.

## Cierre

La sesión termina cuando la frontera está vacía: cada rama visitada y nada asumido en silencio. Antes del resumen, recorre cada vista nombrada con los estados base (normal, vacío, cargando, error, sin permiso, muchos datos): cada uno queda decidido, "no aplica" dicho por la persona, o pendiente. Si falta alguno, la frontera no está vacía.

Antes de escribir, muestra un resumen de las decisiones, con una línea por rama del árbol que diga "visitada" o "no aplica", y pregunta si llegaron a un entendimiento compartido. No escribas el spec hasta que la persona lo confirme.

### Escribir el spec

Usa la plantilla de `references/plantilla-spec.md` tal cual. Cada historia sale de una decisión del grilling, y cada escenario dice solo lo que se decidió: un escenario que agregas por tu cuenta es una decisión que la persona no tomó. Lo pendiente va en "Decisiones del grilling" como pendiente, con quién decide.

Muestra el spec completo y ajusta hasta que la persona lo apruebe.

### Guardar

- Si el proyecto tiene tracker, guarda el spec como documento de la épica o del proyecto (en Linear, un documento del proyecto; en GitHub o GitLab, la descripción de la épica o un issue de spec). Usa la herramienta que tenga la sesión y verifica el acceso con una lectura antes de escribir.
- Si no hay tracker, guárdalo en `specs/<épica>/spec.md` del repositorio de diseño, con `<épica>` en minúsculas y con guiones. Haz commit y push a `main` después de mostrar el resumen y pedir confirmación. Agrega solo esa carpeta, con `git add specs/<épica>/`; nunca `git add -A` ni `git add .`: si las skills se instalaron en el proyecto con `npx skills`, `.agents/`, `.claude/skills/` y `skills-lock.json` quedan sin seguimiento y no van en el commit. El resumen lista solo los archivos que entran en el commit.

Si reemplaza a un spec anterior, agrega al inicio del anterior una línea `> Superado el <fecha> por <enlace o ruta al spec nuevo>.` y no toques el resto: el spec anterior es historia. Sin tracker, el spec nuevo ocupa `specs/<épica>/spec.md`, que es donde lo buscan `spec-a-tickets` y `spec-a-html`, y el anterior se mueve sin cambios, salvo esa línea, a `specs/<épica>/anteriores/spec-<fecha>.md`, con la fecha de su línea `Congelado`, o la de hoy si no tiene.

### Siguiente paso

Cierra diciendo dónde quedó el spec, qué quedó pendiente y con quién, y el siguiente paso: `spec-a-tickets` con este spec para escribir los tickets, y después, en una sesión nueva, `spec-a-html` para dibujar las vistas.
