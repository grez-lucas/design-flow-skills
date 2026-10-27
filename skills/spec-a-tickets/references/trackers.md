# Publicar en el tracker

Cómo publicar los tickets según dónde viven. Lee solo la sección que corresponde.

## Contenido

- Acceso
- Linear
- GitHub
- GitLab
- Otro tracker
- Sin tracker

---

## Acceso

Antes de escribir, averigua con qué herramienta llegas al tracker y dilo:

1. Un servidor MCP del tracker. Carga su esquema antes de llamarlo: los nombres y los parámetros cambian entre versiones y no se adivinan.
2. Una CLI autenticada (`gh`, `glab`). Verifica con una lectura.
3. Nada de lo anterior: no pidas credenciales ni las escribas en archivos. Ofrece publicar como archivos markdown (sección "Sin tracker") y que alguien con acceso los suba.

Una lectura antes de la primera escritura confirma el acceso, el espacio de trabajo correcto y los identificadores que vas a necesitar.

## Linear

1. Ubica el equipo y el proyecto o épica donde van los tickets. Si el proyecto no existe, pregunta antes de crearlo.
2. Lee los labels y los estados del equipo. Un label de las convenciones que no existe en Linear es una diferencia que se reporta, no un label que se inventa.
3. Busca tickets existentes en el proyecto con el título o el identificador de cada historia.
4. Crea cada ticket con la descripción en markdown con saltos de línea reales, no `\n` escapados.
5. Las dependencias van con la relación nativa de bloqueo si la herramienta la tiene; si no, como "Dependencies" en el cuerpo, y avisa cuáles hay que enlazar a mano.
6. Adjunta el spec al proyecto si no está, como documento del proyecto.

## GitHub

1. Confirma el repositorio: `gh repo view --json nameWithOwner`.
2. Lee los labels: `gh label list --limit 100`. Crear labels cambia el repositorio: pregunta antes.
3. Busca existentes: `gh issue list --search "<identificador o título>" --state all`.
4. Escribe cada cuerpo en un archivo temporal y crea con `gh issue create --title "<título>" --body-file <archivo> --label "<label>"`. `--body` en línea rompe el markdown largo.
5. Guarda el número que devuelve cada creación para citarlo en las dependencias de los siguientes.

## GitLab

1. Confirma el proyecto: `glab repo view`.
2. Lee los labels: `glab label list`.
3. Busca existentes: `glab issue list --search "<identificador o título>" --all`.
4. Crea con `glab issue create --title "<título>" --description "$(cat <archivo>)" --label "<label>"`.
5. Las dependencias van como "Dependencies" con referencias `#<número>`; las relaciones nativas de bloqueo dependen del plan de GitLab, así que verifica antes de usarlas.

## Otro tracker

Jira, Azure DevOps u otro: usa la herramienta que la sesión tenga y mapea cada pieza a su equivalente (contenedor, ticket, dependencia, label, estado inicial). Si el tracker pide un campo obligatorio que las convenciones no mencionan, como el tipo de issue en Jira, pregunta: si lo adivinas, todos los tickets heredan la suposición.

## Sin tracker

Escribe un archivo por ticket en `specs/<épica>/tickets/NN-<titulo-corto>.md` del repositorio de diseño, con el formato de la sección "Archivo markdown sin tracker" de `plantilla-story.md`. Numera desde `01` en orden de dependencias, para que el número también diga el orden de trabajo.

Agrega o actualiza `specs/<épica>/tickets/README.md` con la tabla:

```markdown
| # | Ticket | Depende de | Estado |
| :--- | :--- | :--- | :--- |
| 01 | [US-REC-001] Ver facturas vencidas | ninguno | listo |
```

Haz commit y push a `main` del repositorio de diseño con un mensaje que nombre la épica y los tickets, después de mostrar el resumen y pedir la confirmación. Los archivos quedan listos para pasar a un tracker más adelante, uno a uno.
