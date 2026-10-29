# Panel de riego: mockup convertido a vistas

Paula, el mockup `demo.html` ("Semilla · Panel de riego (prototipo v3)") ya está en el repositorio de diseño como dos vistas de la épica riego. El commit es local y no lo subí. Quedan 12 valores de color y medida sin decidir: los detallo en "Tokens".

## 1. Resultado

- **Vistas nuevas (épica riego)**:
  - `design/vistas/riego/panel.html`: pantalla "Zonas", con 11 escenarios.
  - `design/vistas/riego/historial.html`: pantalla "Historial de riego", con 6 escenarios.
- **Design system**:
  - `design/components.css` suma estos componentes: pestañas (`.tabs`, `.tab`, `.tab--active`), marco de página (`.page`, `.page__header`), grilla de tarjetas (`.card-grid`, `.card__title`), métrica grande (`.metric`, `.metric--muted`), texto de próximo riego (`.text-schedule`), diálogo (`.dialog`, `__title`, `__actions`) y las variantes `.badge--info` y `.alert--info`.
  - `design/tokens.css` y `design/proto.js` no cambian.
- **Commit**: `0572d20 diseno(riego): convierte el mockup del panel de riego (demo.html)`, en `main` del repositorio de diseño, sin push. Solo entraron `design/components.css` y las dos vistas. El mockup original no entró al repositorio y no lo modifiqué.
- **Tickets**: la épica todavía no tiene. Por eso cada vista cita el spec con `<meta name="spec" content="specs/riego/spec.md">`. El spec nombra las historias SEM-20, SEM-21 y SEM-22, pero no existe `specs/riego/tickets/`.

## 2. Plan ejecutado

| Pantalla | Vista | Archivo | Épica | Escenarios | Origen |
| :--- | :--- | :--- | :--- | :--- | :--- |
| "Zonas" | Panel | `design/vistas/riego/panel.html` | riego (spec) | normal, vacio, cargando, error, sin-permiso, muchos-datos, sensor-sin-senal (DEMO), tanque-vacio (DEMO), tanque-a-la-mitad (regla del spec), regar-ahora (modal `regar-modal`), duracion-invalida (función `confirmarRiego`) | `panel-page.html`, `regar-modal.html` |
| "Historial de riego" | Historial | `design/vistas/riego/historial.html` | riego (spec) | normal, vacio, cargando, error, sin-permiso, muchos-datos | `historial-page.html` |
| "Panel de riego" (marco) | va dentro de cada vista | - | - | - | `_resto.html` |

El mockup es un solo documento. Por eso el marco (cabecera "Panel de riego" y pestañas) no es una vista aparte: va repetido en cada vista, y las pestañas pasan a ser enlaces entre `panel.html` e `historial.html`.

Olas:
1. **Ola 1**:
   - Los tokens los mapeé yo con `tokens.py mapear`.
   - Un subagente armó los componentes base y otro el marco con los escenarios globales.
2. **Ola 2**: dos subagentes, uno por vista (`Ola 2: panel` y `Ola 2: historial`).
3. **Ola 3**:
   - Hice la integración en una copia del repositorio y corrí el inventario y `revisar.py`.
   - Un subagente revisor, que no armó ninguna vista, decidió vista por vista.

Cambios respecto del plan aprobado:
- **Marco**: su borrador usaba clases que no existían (`.app-header`, `.tabs__item`). Lo unifiqué con el catálogo de componentes antes de la ola 2.
- **Historial**: en la primera revisión **no se aprobó**. La fila de nombre largo, que es solo para el escenario "muchos datos", también se veía en "normal". Volvió una vez a su subagente, que la corrigió, y en la segunda revisión se aprobó.
- **Panel**: se aprobó en la primera revisión.

## 3. Tokens

El mockup tenía 7 variables propias y unos 37 valores sueltos. Los que están dentro del umbral (color 2,0 en OKLab; medida 1 px o 10 % del paso) van al token sin preguntar:

| Valor del mockup | Qué pinta | Token | Valor del token |
| :--- | :--- | :--- | :--- |
| #f6f7f2, #ffffff, #1c2a21, #1f6f8b, #d6dccf, #c62828 | fondo, tarjetas, texto, color agua, bordes, alertas | --color-bg, --color-surface, --color-text, --color-info, --color-border, --color-danger | iguales |
| #5b6b60 | pestaña inactiva, humedad sin señal | --color-text-muted | #5a6b5f |
| #e6f0f3 | fondo del chip "Lleno" | --color-surface-alt | #eef1e9 |
| 1180px | ancho máximo del panel | --size-content-max | 1200px |
| 17px | nombre de la zona | --font-size-md | 16px |
| 30px | porcentaje de humedad | --font-size-2xl | 28px |
| 13px | error de duración | --font-size-xs | 12px |
| 4, 8, 12, 16, 20, 24 px; letra 12 y 14 px; radios 8 y 12 px | espacios, letra y esquinas | --space-*, --font-size-*, --radius-* | iguales |

Mostré la tabla de los valores fuera del umbral, pero no elegiste entre el token existente y uno nuevo. No agregué ningún token: cada valor usa el token existente más cercano del mismo uso y queda pendiente.

- Pendiente de decisión: #7b4fd6, el morado de "Próximo riego: hoy 19:00". Mientras tanto usa --color-info (#1f6f8b, el mismo azul agua de la humedad), así que el próximo riego ya no se distingue por color. Propuesta: `--color-schedule: #7b4fd6`.
- Pendiente de decisión: #9a5b00, el texto del chip "A la mitad". Mientras tanto usa --color-warning (#b26b00). Propuesta: `--color-warning-strong: #9a5b00`.
- Pendiente de decisión: #fff1d6, el fondo amarillo del chip "A la mitad". Mientras tanto usa --color-surface-alt (#eef1e9, gris verdoso): se pierde el fondo amarillo y el texto sigue en tono de advertencia. Propuesta: `--color-warning-subtle: #fff1d6`.
- Pendiente de decisión: #fde2e2, el fondo rosado del chip "Sin agua" y de los avisos de sensor sin señal y tanque vacío. Mientras tanto el chip usa --color-surface-alt, y los avisos usan el componente `.alert--danger` (fondo blanco, borde y texto rojos): se pierde el rosado. Propuesta: `--color-danger-subtle: #fde2e2`.
- Pendiente de decisión: rgba(16, 23, 18, 0.45), el velo oscuro detrás del modal "Regar ahora". Ningún token sirve para una superposición, así que no se aplica: el modal se ve sobre el panel sin oscurecerlo. Propuesta: `--color-overlay: rgba(16, 23, 18, 0.45)`.
- Pendiente de decisión: 380px, el ancho del modal "Regar ahora". Ningún token de tamaño sirve, así que no se aplica y el modal toma el ancho de su contenido. Propuesta: `--size-dialog: 380px`.
- Pendiente de decisión: 10px, el relleno de las pestañas y de las celdas de la tabla. Mientras tanto usa --space-2 (8px). Propuesta: `--space-2-5: 10px`.
- Pendiente de decisión: 14px, el relleno lateral de las pestañas y del botón. Mientras tanto usa --space-3 (12px), y el botón usa el `.btn` del sistema (8px por 16px). Propuesta: `--space-3-5: 14px`.
- Pendiente de decisión: 6px, el espacio bajo el nombre de la zona. Mientras tanto usa --space-1 (4px). Propuesta: `--space-1-5: 6px`.
- Pendiente de decisión: 18px, el margen de las pestañas. Mientras tanto usa --space-4 (16px). Propuesta: `--space-4-5: 18px`.
- Pendiente de decisión: 6px, las esquinas de los chips del tanque. Mientras tanto usa el `.badge` del sistema, con esquinas redondas (--radius-full). Propuesta: `--radius-sm-md: 6px`.
- Pendiente de decisión: 10px, las esquinas de la tarjeta de zona. Mientras tanto usa el `.card` del sistema, con --radius-lg (12px). Propuesta: `--radius-md-lg: 10px`.

Si apruebas algún token nuevo, se agrega a `tokens.css` y se cambia la clase que lo usa. Las vistas no cambian.

## 4. Escenarios

Salieron de controles de prototipo:
- `sensor-sin-senal`: menú "DEMO ▾", opción "Simular sensor sin señal" (`demoSet('sin-senal')`).
- `tanque-vacio`: menú "DEMO ▾", opción "Simular tanque vacío" (`demoSet('tanque-vacio')`).
- "Salir de demo" (`demoSet('')`) equivale a volver a `normal`. El menú DEMO no está en las vistas: el selector de escenarios lo pone `proto.js`, fuera de la pantalla.
- `regar-ahora`: el modal `regar-modal`, que abre el botón "Regar ahora" de cada zona (`abrirRiego`).
- `duracion-invalida`: el modal con el error de la función `confirmarRiego`.

`data-state` del mockup renombrados (en las vistas, `data-state` queda solo para escenarios):
- `full` → `badge--info` ("Lleno")
- `partial` → `badge--warning` ("A la mitad")
- `off` → `badge--danger` ("Sin agua")

Escenarios del spec que el mockup no tenía y que las vistas escriben desde el spec:
- **Panel**:
  - vacio: "Todavía no hay zonas configuradas".
  - cargando: tarjetas esqueleto.
  - error: aviso y "Reintentar".
  - sin-permiso.
  - muchos-datos: 50 tarjetas, una con un nombre de zona largo.
  - tanque-a-la-mitad. El mockup mostraba los tres chips del tanque juntos; la regla del spec dice que el tanque está lleno, a la mitad o sin agua, así que cada escenario muestra uno solo.
- **Historial**:
  - vacio: "Todavía no hay riegos registrados".
  - cargando.
  - error.
  - sin-permiso.
  - muchos-datos: 50 filas, con zona y socio de nombre largo.

## 5. Sin equivalente

- **Pestañas con JS** (`verPestana`): pasan a enlaces entre `panel.html` e `historial.html`.
- **Menú DEMO**: pasa a los escenarios del punto anterior.
- **Velo y ancho del modal**: no se aplican, por falta de token. Ver "Tokens".
- **Dato real reemplazado**: "Manual, Bruno Lagos" (persona del equipo que figura en el spec) pasa a "Manual, Camila Rojas", un socio ficticio.
- Criterio para el ticket: Dado que la socia de turno toca "Regar ahora" en una zona, cuando se abre el modal, entonces el modal muestra el nombre de esa zona (`abrirRiego`). Queda como comentario en `panel.html`, junto a cada botón "Regar ahora" y en el modal.
- Criterio para el ticket: Dado que la duración está entre 5 y 60 minutos, cuando toca "Iniciar riego", entonces el riego empieza y el modal se cierra; dado que está fuera de ese rango, cuando toca "Iniciar riego", entonces ve "La duración tiene que estar entre 5 y 60 minutos." y el modal sigue abierto (`confirmarRiego`, SEM-21). Queda como comentario en `panel.html`, junto al campo y al botón "Iniciar riego".
- Criterio para el ticket: Dado que el modal está abierto, cuando toca "Cancelar", entonces el modal se cierra sin regar (`cerrarRiego`). Queda como comentario en `panel.html`, junto a "Cancelar".

## 6. Fidelidad

La verificación se hizo sin render: la sesión no tenía navegador, así que no hay capturas del original ni de las vistas. Lo que se compara es el inventario (textos, controles y campos del original contra la vista), y el revisor leyó cada vista contra su contrato y el spec.

| Vista | Textos | Controles | Campos | Lo que falta y por qué | Revisor |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Panel | 21 de 21 | 5 de 5 | 1 de 1 | nada | aprobada en la primera revisión |
| Historial | 17 de 18 | 2 de 2 | 0 de 0 | "Manual, Bruno Lagos": persona real reemplazada por un nombre ficticio | aprobada en la segunda revisión |

En las dos vistas no queda ningún `data-state` del mockup ni ningún control DEMO. `revisar.py` sobre el repositorio: 0 hallazgos que bloquean.

Observaciones del revisor que no bloquean, para que decidas:
- **Panel, humedad sin señal**: con sensor sin señal, el mockup atenúa la humedad de las **tres** zonas. La vista atenúa solo la de la zona norte, que es la que nombra el aviso. Lo de la vista concuerda con el spec, pero se aparta del mockup: confirma cuál vale.
- **Panel, zonas vacías**: el escenario vacío no ofrece ninguna acción (el spec no pide una).
- **Historial, sin permiso**: el texto del escenario sin permiso ("Esta sección es para quienes coordinan el riego…") es una propuesta. El spec no dice quién puede ver el historial.
- **Historial, rango de fechas**: "Los últimos días" no tiene rango en el spec ni en el mockup. La paginación o el límite de filas quedan como comentario pendiente.

## 7. Lo que no se pudo ver

- No se vio ninguna pantalla renderizada: no hay capturas lado a lado y no se comparó cómo se ven el original y las vistas.
- El mockup no arma contenido con JS más allá del nombre de la zona en el modal, y eso quedó cubierto. No tiene animaciones ni recursos externos.

## 8. Siguiente paso

- Corre `flujo-diseno:checklist-diseno` sobre `design/vistas/riego/` antes de la planificación.
- Corre `flujo-diseno:spec-a-tickets` con `specs/riego/spec.md` para escribir los tickets SEM-20, SEM-21 y SEM-22. Después, cada vista puede cambiar su `<meta name="spec">` por `<meta name="tickets">`.
- Decide los 12 valores pendientes de la sección "Tokens".
