# Contrato · Historial

## Vista y origen
- Vista: historial, archivo `design/vistas/riego/historial.html`, épica riego
- Origen: parte documento, trozos `trozos/documento/markup/historial-page.html` (tabla) y `trozos/documento/markup/_resto.html` (pestaña, línea 15 del trozo; marco), líneas del original no disponibles en los trozos (el trozo de la tabla ocupa 10 líneas; el `<script>` de `verPestana` está en `trozos/documento/script.js`, líneas 9 a 12)

## Escenarios
| Escenario | Activador original | Qué cambia | data-state |
| :--- | :--- | :--- | :--- |
| normal | pestaña "Historial de riego" (`verPestana('historial-page', this)`) | tabla con fecha, zona, duración y origen (SEM-22, escenario 1) | `normal muchos-datos` |
| vacio | no existe en el mockup; sale del spec | mensaje "Todavía no hay riegos registrados" y enlace a las zonas | `vacio` |
| cargando | no existe en el mockup; sale del spec | cinco bloques `.skeleton` | `cargando` |
| error | no existe en el mockup; sale del spec | `.alert--danger` con "Reintentar" | `error` |
| sin-permiso | no existe en el mockup; sale del spec | mensaje de acceso y enlace de vuelta a las zonas | `sin-permiso` |
| muchos-datos | no existe en el mockup; sale del spec | misma tabla más un segundo `tbody` (`data-state="muchos-datos" data-repeat="47"`, 3 filas base, una con zona y socio de nombre largo) que `proto.js` clona hasta 50 filas en total; en normal solo se ven las 3 filas del mockup; crece en la página, sin paginación ni scroll interno | tabla: `normal muchos-datos`; `tbody` extra: `muchos-datos` |
- Base que no aplican, con motivo: ninguno. Los escenarios globales `sensor-sin-senal` y `tanque-vacio` no se listan: el mockup no cambia el historial con esos modos (`escenarios-globales.md`); no se encontró nada oculto en este trozo.

## Componentes
| Clase original | Componente | Nuevo |
| :--- | :--- | :--- |
| `section#historial-page[hidden]` | `section` con `data-state` | no |
| `table`, `th`, `td` | `.table` | no |
| `.marco` | `.page` (con `data-frame`) | no (ola 1) |
| `.cabecera` | `.page__header` | no (ola 1) |
| `.pestanas` / `.pestana` / `.pestana.activa` | `.tabs` / `.tab` / `.tab--active`, como enlaces con `aria-current="page"` | no (ola 1) |
| sin equivalente (vacío, sin permiso) | `.empty-state` | no |
| sin equivalente (cargando) | `.skeleton` | no |
| sin equivalente (error) | `.alert` + `.alert--danger` | no |
| botón / enlace de acción | `.btn` | no |

No se agregó ninguna clase nueva a `components.css`.

## Valores sin token
- Ninguno. La vista no lleva `<style>` ni `style=""`. Los valores de la tabla (paddings, bordes) los resuelve `.table`.

## Textos y datos
- "Bruno Lagos" (persona real del equipo, aparece en el spec) reemplazado por el socio ficticio "Camila Rojas" en la fila "Manual" del escenario normal.
- Fila extra de muchos-datos: "Valentina Fuentes-Montenegro de la Barra" y "Zona invernadero de almácigos y plantines nuevos" son datos ficticios largos para probar el desborde.
- Textos nuevos escritos desde el spec (no existen en el mockup): vacío, cargando, error, sin permiso. El de sin permiso asume que "coordinadora" (SEM-22) es quien tiene acceso; confirmar con producto.
- Pestañas: de `<button onclick="verPestana(...)">` a enlaces (`panel.html`, `historial.html`). El título `h1` "Panel de riego" viene del marco.
- La vista no lleva `<meta name="tickets">`: SEM-22 no tiene ticket todavía; lleva `<meta name="spec" content="specs/riego/spec.md">`.

## Interacciones como comentario
- Pestaña "Zonas": enlace a `panel.html`. "Historial de riego": la vista actual (`aria-current="page"`).
- "Reintentar" (error): vuelve a pedir el historial y muestra el escenario cargando (comentario en la vista).
- "Volver a las zonas" (sin-permiso) e "Ir a las zonas" (vacio): enlazan a `panel.html`.
- Tabla en muchos-datos: sin paginación ni scroll interno; paginar o limitar a "los últimos días" queda pendiente de decisión de producto (comentario en la vista).
- Criterio para el ticket: Dado que hubo riegos, cuando abro el historial, entonces veo fecha, zona, duración y origen (programado o manual, con el socio) (SEM-22, escenario 1; ya está en el spec).

## Lo que no pudo ver
- No se leyó el original ni se renderizó; el orden de las filas (más reciente primero) se deduce de los datos del trozo.
- El mockup no muestra cuántos días abarca "los últimos días"; el spec tampoco. Sin dato para el comentario de rango.
- `verPestana` oculta todas las `section` del documento con `hidden`: al ser dos vistas, el panel y el historial no comparten estado; no hay conflicto de `data-state` en este trozo.
- Textos de vacío, error y sin permiso, y el texto de acceso, son propuesta de esta ola, no del mockup.
