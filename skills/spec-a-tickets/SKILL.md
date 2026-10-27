---
name: spec-a-tickets
description: Convierte un spec de producto con historias de usuario en tickets listos para construir, una story por historia, con descripción "Como, quiero, para", criterios de aceptación por escenario "Dado, cuando, entonces", pruebas E2E, enlace a la vista de diseño, casos borde y preguntas abiertas. Los publica en el tracker del proyecto (Linear, GitHub, GitLab u otro) o, si no hay tracker, como un archivo markdown por ticket en specs/<épica>/tickets/. Úsala siempre que producto quiera pasar un spec, una épica o unas historias a tickets, issues o stories, aunque no lo diga así - "crea los tickets de este spec", "pasa las historias a Linear", "arma las stories de la épica", "sube esto al tablero", "escribe los criterios de aceptación", "genera los issues para DEV". No la uses para hacer el grilling de un requerimiento (grilling-es), para diseñar pantallas (spec-a-html) ni para cortar trabajo técnico de ingeniería en subtareas.
---

# Spec a tickets

Convierte un spec en los tickets que DEV construye. Los tickets se escriben antes del HTML: el ticket es la fuente de lo que se acepta, y el diseño se dibuja después contra esos criterios.

Quien usa esta skill suele ser de producto. Habla en español, sin jerga técnica salvo que la persona la use primero.

La skill redacta. La persona de producto es dueña de los criterios de aceptación y aprueba antes de publicar. No es un trámite: los criterios son el contrato con el negocio, y un contrato inventado en nombre de alguien no es un contrato.

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

Busca `.claude/pm-conventions.md` en el repositorio de diseño y, si no está, en el repositorio de código si está a mano. Si existe, manda: usa su tracker, su plantilla, sus labels, su formato de título y su estado inicial.

Si no existe, usa la plantilla de `references/plantilla-story.md` y pregunta solo lo que no puedes ver: si hay tracker y cuál. Sin tracker, los tickets van como archivos markdown.

### 4. Cortar

Una historia del spec es un ticket. Es la unidad que producto entiende y acepta; las subtareas técnicas las agrega DEV después.

Propón partir una historia solo cuando es claramente demasiado grande, por ejemplo con más de cinco escenarios o con dos capacidades distintas en la misma frase. Cada parte tiene que poder aceptarse por sí sola. Dilo y espera la confirmación.

Si una historia depende de otra (no se puede ver el listado de invitaciones sin poder invitar), anótalo como dependencia.

### 5. Redactar

Sigue la plantilla del proyecto o la de `references/plantilla-story.md`. Lo esencial:

- **Título** con el identificador del spec si lo trae (`[US-REC-001] Ver facturas vencidas`). Si no lo trae, usa el formato de las convenciones; sin convenciones, `[US-<ÁREA>-NNN]`, con un código corto de la épica en mayúsculas.
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
2. Busca tickets que ya cubran estas historias. Si encuentras uno, muéstralo y pregunta si se extiende, se reemplaza o se omite. Nunca edites ni cierres un ticket que esta corrida no creó.
3. Crea los tickets en orden de dependencias, para que cada uno cite identificadores reales.
4. Si algo falla a mitad de camino, para y di qué quedó creado y qué no.

### 8. Congelar el spec

Agrega una línea al inicio del spec, en el tracker o en `specs/<épica>/spec.md`:

```
> Congelado el 2026-10-26: los tickets US-REC-001 y US-REC-002 mandan. Un cambio posterior pasa por grilling y actualiza los tickets.
```

Desde ahí, el spec no se reescribe: los tickets son la fuente de lo que se acepta.

### 9. Cerrar

Entrega la tabla de identificadores y títulos con sus enlaces, las preguntas abiertas que quedaron y el siguiente paso: en una sesión nueva, `spec-a-html` con el mismo spec para dibujar las vistas.
