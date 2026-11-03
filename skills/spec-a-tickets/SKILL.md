---
name: spec-a-tickets
description: Convierte un spec de producto con historias de usuario en tickets listos para construir, una story por historia, con descripción "Como, quiero, para", criterios de aceptación por escenario "Dado, cuando, entonces", pruebas E2E, enlace a la vista de diseño, casos borde y preguntas abiertas. Los publica en el tracker del proyecto (Linear, GitHub, GitLab u otro) o, si no hay tracker, como un archivo markdown por ticket en specs/<épica>/tickets/. Úsala siempre que producto quiera pasar un spec, una épica o unas historias a tickets, issues o stories, aunque no lo diga así - "crea los tickets de este spec", "pasa las historias a Linear", "arma las stories de la épica", "sube esto al tablero", "escribe los criterios de aceptación", "genera los issues para DEV". No la uses para hacer el grilling de un requerimiento (grilling-es), para diseñar pantallas (spec-a-html) ni para cortar trabajo técnico de ingeniería en subtareas.
---

# Spec a tickets

Convierte un spec en los tickets que DEV construye. Los tickets se escriben antes del HTML: el ticket es la fuente de lo que se acepta, y el diseño se dibuja después contra esos criterios.

Quien usa esta skill suele ser de producto. Habla en español, sin jerga técnica salvo que la persona la use primero.

La skill redacta. La persona de producto es dueña de los criterios de aceptación y aprueba antes de publicar. No es un trámite: los criterios son el contrato con el negocio, y un contrato inventado en nombre de alguien no es un contrato.

## Intérprete de Python

Al empezar, una sola vez, busca el intérprete: prueba `python3`, `python` y `py -3`, en ese orden, con `<intérprete> -c "import sys; assert sys.version_info >= (3, 9)"`, y usa el primero que sale sin error como `<intérprete>` en cada orden de esta skill y de sus `references/`, siempre con `-B`, para que Python no deje `__pycache__/` en la carpeta de la skill. Si ninguno responde, no corras ninguna orden con Python y sigue lo que esta skill dice para cuando no encontraste intérprete.

## Pasos

### 1. Conseguir el spec

El spec llega por enlace al tracker, adjunto o pegado en el chat, o como `specs/<épica>/spec.md` en el repositorio de diseño. Si la sesión no puede leer el enlace, pide que lo peguen. Sin spec no hay tickets: pide el spec en vez de reconstruir el requerimiento de memoria.

El spec sigue una plantilla con contexto, historias "Como, quiero, para" con escenarios "Dado, cuando, entonces", estados por vista, reglas, decisiones, fuera de alcance y enlaces.

### 2. Revisar que el spec alcance

Un spec blando produce tickets prolijos y equivocados, y publicados se ven oficiales. Antes de redactar, revisa:

- Cada historia dice quién, qué y para qué.
- Cada historia tiene al menos un escenario con resultado observable.
- Las reglas que cambian el comportamiento tienen respuesta, o están marcadas como pendientes con quién decide.
- Está claro qué queda fuera de alcance.

Si falla uno, sigue y llévalo a "Open Questions" del ticket que corresponda. Si fallan dos o más, para: di qué falta y por qué importa, y sugiere volver a `grilling-es`. No rellenes un criterio con una suposición: una suposición publicada como criterio de aceptación es exactamente la falla que este paso evita.

### 3. Leer las convenciones del proyecto

Busca `.claude/pm-conventions.md` en el repositorio de diseño y, si no está, en el repositorio de código si está a mano. Si el archivo apunta a otro lugar, una ruta o una URL, lee las convenciones ahí; si la sesión no puede abrirlas, pide que las peguen. Las convenciones mandan: usa su tracker, su plantilla, sus labels, su formato de título y de ID y su estado inicial.

Si no las encuentras, no supongas que no hay: pregunta a la persona dónde están. Suelen vivir en otro repositorio del producto o en una wiki, con reglas que pesan, como qué documento manda sobre otro o el formato de ID del tracker. Acepta una ruta o una URL, aunque esté fuera del repositorio de diseño, léelas ahí y, con la rama revisada como dice el final de este paso, guarda el puntero en `.claude/pm-conventions.md` del repositorio de diseño, para que la próxima sesión las encuentre sin preguntar:

```markdown
# Convenciones de gestión

Las convenciones de gestión de este proyecto están en <ruta o URL>.
```

Una ruta local solo existe en las máquinas que la tienen: si las convenciones están en un repositorio con URL, guarda la URL. El puntero entra en el commit de los tickets (paso 9).

Si la persona dice que no hay convenciones, no escribas el puntero: usa la plantilla de `references/plantilla-story.md` y pregunta solo lo que no puedes ver: si hay tracker y cuál. Sin tracker, los tickets van como archivos markdown.

Si la sesión va a escribir en el repositorio de diseño (el puntero de este paso, los tickets como archivos del paso 7 o el spec congelado del paso 8), antes del primer archivo decide la rama: el paso 9 guarda en la rama actual, y cambiar de rama con archivos sin guardar puede fallar. Corre, con la ruta absoluta de esta skill en lugar de `<ruta-de-esta-skill>` y desde el repositorio de diseño:

```
<intérprete> -B <ruta-de-esta-skill>/scripts/rama.py revisar --tipo tickets --epica <épica>
```

Si no encontraste intérprete, para y no guardes: explica en simple que falta Python 3.9 o superior y que se instala desde https://www.python.org/downloads/. Si `rama.py` sale con error o no devuelve un JSON, aquí o tras un rechazo, para y no guardes: explica el error en simple; si dice que el nombre termina en guion y número, pide a la persona otro, por ejemplo `fase-dos` en lugar de `fase-2`, y vuelve a correrlo. El script trae lo nuevo del servidor, no cambia de rama y devuelve un JSON con una `accion`:

- `guardar`: guarda en la rama actual.
- `volver`: la rama ya no está en el servidor, por ejemplo porque el TL hizo el merge y la borró, y lo que tenía ya está en la principal. Corre `git switch <principal>`, con la `principal` del JSON, y `git pull --ff-only`, y guarda ahí. Si uno falla, para y explica en qué rama quedaste.
- `parar`: no escribas en el repositorio. Explica en simple el `detalle`, en qué rama estás y que el TL dice cómo seguir.

### 4. Cortar

Una historia del spec es un ticket. Es la unidad que producto entiende y acepta; las subtareas técnicas las agrega DEV después.

Propón partir una historia solo cuando es claramente demasiado grande, por ejemplo con más de cinco escenarios o con dos capacidades distintas en la misma frase. Cada parte tiene que poder aceptarse por sí sola. Dilo y espera la confirmación.

Si una historia depende de otra (no se puede ver el listado de invitaciones sin poder invitar), anótalo como dependencia.

### 5. Redactar

Sigue la plantilla del proyecto o la de `references/plantilla-story.md`. Lo esencial:

- **Título** con el formato de ID de las convenciones cuando lo definen (`INV-12: Registrar ingreso de mercadería`), también si el spec trae otro identificador: el ticket se busca en el tracker por ese ID. El identificador del spec queda en el cuerpo, junto al enlace al spec, para rastrear la historia. Si el tracker asigna el ID al crear el ticket, no lo inventes: el ticket queda con el que devuelve el tracker, y si los tickets van como archivos porque todavía no hay acceso al tracker, el título lleva el identificador del spec hasta que pasen. Sin formato en las convenciones, usa el identificador del spec si lo trae (`[US-REC-001] Ver facturas vencidas`) y, si no lo trae, `[US-<ÁREA>-NNN]`, con un código corto de la épica en mayúsculas.
- **Descripción**: la historia "Como, quiero, para" y un párrafo de contexto tomado del spec.
- **Criterios de aceptación**: un escenario por bloque, con "Dado, cuando, entonces" y "Y" para resultados adicionales. Afirman comportamiento y datos que se ven, nunca rutas de archivos ni detalles de implementación: las rutas envejecen y el comportamiento no. Los estados del spec (vacío, error, sin permiso, plan expirado) se vuelven escenarios cuando el spec dice qué pasa en ellos.
- **Pruebas**: redacta los flujos E2E a partir de los escenarios. Deja las pruebas unitarias y de integración marcadas "Lo completa DEV": producto no tiene cómo validarlas.
- **Diseño**: la ruta donde va a quedar la vista, `design/vistas/<épica>/<vista>.html`, marcada "pendiente". Es la misma ruta que usa `spec-a-html`, así que el enlace queda bien sin volver a editar el ticket.
- **Casos borde**: tabla con los del spec y los que aparecen al redactar, cada uno con su comportamiento esperado. Si no sabes el comportamiento, va a preguntas abiertas, no a la tabla.
- **Preguntas abiertas**: todo lo que el spec no responde.

Un criterio de aceptación dice solo lo que el spec dice. Aunque un agregado parezca obvio ("el valor negativo no se guarda", "ordenado de mayor a menor"), si el spec no lo afirma va como pregunta abierta, no como criterio: la persona de producto lo confirma y recién ahí pasa a criterio.

Si la plantilla del proyecto no tiene sección de preguntas abiertas, casos borde o pruebas, no la agregues al ticket: deja las preguntas en el índice `specs/<épica>/tickets/README.md` o, con tracker, en un comentario del ticket, y dilo al cerrar.

### 6. Aprobación

Muestra el corte en una tabla (identificador, título, escenarios, dependencias) y el primer ticket completo con la plantilla aplicada. Es mucho más barato corregir la plantilla una vez que en diez tickets.

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
4. Si algo falla a mitad de camino, para y di qué quedó creado y qué no.

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
- El puntero a las convenciones, si lo escribiste en esta sesión: `git add .claude/pm-conventions.md`. Si git responde que la ruta está ignorada por el `.gitignore`, no la fuerces: dilo, el puntero queda solo en esta máquina, y el TL decide si cambia el `.gitignore`.
- El `.gitignore`, si le agregaste `.lavish/`: `git add .gitignore`.

Nunca `git add -A` ni `git add .`: si las skills se instalaron en el proyecto con `npx skills`, `.agents/`, `.claude/skills/` y `skills-lock.json` quedan sin seguimiento y no van en el commit.

La rama quedó revisada en el paso 3. El push va a la rama actual, con `git push`. Si falla por credenciales, porque el servidor no reconoce el usuario o el token, explica el error en simple y que el TL es quien da los accesos. Si lo rechaza por cualquier motivo que no sea de credenciales (la rama está protegida, o tiene cambios que tu copia no tiene), no lo arregles en esa rama, sin `git pull --rebase`, `git reset --hard` ni `--force`: el TL resuelve en el merge request. Pide la rama nueva, desde el repositorio de diseño, con `<intérprete> -B <ruta-de-esta-skill>/scripts/rama.py rechazo --tipo tickets --epica <épica>`.

- `rama-nueva`: pasa el commit con `git switch -c <rama_nueva>` y empújalo con `git push -u origin <rama_nueva>`; deja la `rama` de la que saliste como está en el servidor con `git branch -f <rama> origin/<rama>`. Explica en simple que el servidor no aceptó el cambio en esa rama, que los tickets quedaron en la rama nueva y que el TL revisa y hace el merge request.
- `parar`: explica en simple el `detalle` y que el TL es quien da los accesos.

### 10. Cerrar

Entrega la tabla de identificadores y títulos con sus enlaces, las preguntas abiertas que quedaron y el siguiente paso: en una sesión nueva, `spec-a-html` con el mismo spec para dibujar las vistas. Nombra la skill como figura en tu lista de skills: instalada como plugin de Claude Code es `flujo-diseno:spec-a-html`; con `npx skills`, `spec-a-html`.
