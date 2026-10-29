# Contrato · panel

## Vista y origen
- Vista: panel, archivo `design/vistas/riego/panel.html`, épica riego (sin tickets: `<meta name="spec" content="specs/riego/spec.md">`; historias SEM-20 y SEM-21)
- Origen: parte documento, trozos `trozos/documento/markup/panel-page.html` (`#panel-page`, pestaña "Zonas") y `trozos/documento/markup/regar-modal.html` (`#regar-modal`), script `trozos/documento/script.js`; líneas del original no medidas (los trozos no las traen)

## Escenarios
| Escenario | Activador original | Qué cambia | data-state |
| :--- | :--- | :--- | :--- |
| normal | "Salir de demo" (`demoSet('')`) | tres zonas, chip Lleno, sin avisos | `normal` |
| vacio | no existe (spec: sin zonas configuradas) | `.empty-state` con texto | `vacio` |
| cargando | no existe (spec) | tres `.skeleton` en `.card-grid` | `cargando` |
| error | no existe (spec) | `.alert--danger` con botón Reintentar | `error` |
| sin-permiso | no existe (spec) | `.empty-state` con a quién pedir acceso | `sin-permiso` |
| muchos-datos | no existe (spec) | `data-repeat="50"` en `.card-grid` y una zona con nombre largo | `muchos-datos` |
| sensor-sin-senal | menú DEMO "Simular sensor sin señal" (`demoSet('sin-senal')`) | aviso `.alert--danger` y humedad de zona norte `.metric--muted` | `sensor-sin-senal` |
| tanque-vacio | menú DEMO "Simular tanque vacío" (`demoSet('tanque-vacio')`) | aviso de pausa y chip `.badge--danger` "Sin agua" | `tanque-vacio` |
| tanque-a-la-mitad | no existe como control (el mockup mostraba los tres chips juntos) | chip `.badge--warning` "A la mitad" | `tanque-a-la-mitad` |
| regar-ahora | botón "Regar ahora" de cada zona (`abrirRiego`) | `<dialog open>` con duración 15 | `regar-ahora` |
| duracion-invalida | "Iniciar riego" con duración fuera de 5 a 60 (`confirmarRiego`) | mismo modal, duración 3, `aria-invalid` y error | `duracion-invalida` |
- Base que no aplican, con motivo: ninguno; los seis base aplican.

## Componentes
| Clase original | Componente | Nuevo |
| :--- | :--- | :--- |
| `.marco`, `.cabecera`, `.pestanas`/`.pestana` | `.page`, `.page__header`, `.tabs`, `.tab`, `.tab--active` | no (de la ola 1) |
| `.zonas` | `.card-grid` | no (de la ola 1) |
| `.zona` | `.card` | no |
| `.zona h3` | `.card__title` | no (de la ola 1) |
| `.humedad` | `.metric` / `.metric--muted` | no (de la ola 1) |
| `.programado` | `.text-schedule` | no (de la ola 1) |
| `.chip` `full` / `partial` / `off` | `.badge--info` / `.badge--warning` / `.badge--danger` | no (`.badge--info` de la ola 1) |
| `.aviso` | `.alert` + `.alert--danger` | no |
| `.boton` | `.btn` + `.btn--primary` | no |
| botón "Cancelar" | `.btn` | no |
| `.modal` / `h2` / botones | `.dialog` / `.dialog__title` / `.dialog__actions` | no (de la ola 1) |
| `label` + `input`, `.error` | `.field`, `.field__error` | no |
| estados del spec | `.empty-state`, `.skeleton`, `.alert--danger` | no |
| `.modal-fondo` | no se convierte (velo sin token) | no |

Clases nuevas propias de esta vista: ninguna (todas existen en la `components.css` de la ola 1).

## Valores sin token
- #7b4fd6 en `.text-schedule` ("Próximo riego"): usa `--color-info`; pendiente de decisión (`--color-schedule`)
- #9a5b00 y #fff1d6 en chip "A la mitad": usa `--color-warning` y `--color-surface-alt`; pendiente de decisión
- #fde2e2 en chip "Sin agua" y avisos: usa `--color-surface-alt` / fondo de `.alert`; pendiente de decisión
- rgba(16,23,18,0.45) del velo del modal: no se aplica; pendiente de decisión (`--color-overlay`)
- 380px del modal: no se aplica; pendiente de decisión (`--size-dialog`)
- paddings 10/14/6/18px y radios 6/10px: token existente más cercano; pendientes de decisión

## Textos y datos
- Los `data-state="full|partial|off"` del chip del tanque se renombraron a `.badge--info|--warning|--danger` (data-state queda reservado para escenarios); en la vista va un solo chip por escenario.
- Sin nombres de personas ni datos reales en el mockup; zonas (norte, invernadero, aromáticas) se conservan.
- Textos nuevos escritos desde el spec: vacío, cargando, error, sin permiso, y una zona de nombre largo para muchos-datos.
- Sensor sin señal: la humedad de zona norte queda como en el mockup (42 %), atenuada.

## Interacciones como comentario
- "Regar ahora" (cada zona): abre el modal con el nombre de la zona (`abrirRiego`); comentario junto al botón.
- Nombre de zona del modal: lo pone `abrirRiego(zona)`; comentario junto al elemento.
- "Iniciar riego": `confirmarRiego` valida 5 a 60 minutos; válido cierra el modal e inicia el riego, inválido muestra el error (comentario en el modal).
- "Cancelar": cierra el modal (`cerrarRiego`).
- "Reintentar" (error): vuelve a pedir las zonas.
- Pestaña "Historial de riego": enlaza a `historial.html`.

## Lo que no pudo ver
- No abrí el mockup original ni usé navegador: el parecido visual no se verificó con render.
- Los controles DEMO (`demoToggleMenu`, `demoSet`) no pasan; los reemplaza el panel de `proto.js`.
- Con `tanque-vacio` el mockup solo mostraba aviso y chip: no vi si el CSS original (`body.tanque-vacio`) oculta algo más; no lo busqué en `estilos.css`.
- `data-repeat` sobre `.card-grid` depende de que `proto.js` clone los hijos como filas; si solo clona filas de tabla, habrá que ajustarlo.
