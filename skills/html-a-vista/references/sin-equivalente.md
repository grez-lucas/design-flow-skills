# Lo que no tiene equivalente

Qué pasa con lo que el mockup tiene y la convención de vista no admite. Una vista no lleva JavaScript propio, ni animaciones, ni recursos externos: lo que no se puede mostrar se escribe.

| En el mockup | En la vista | En el informe |
| :--- | :--- | :--- |
| `@keyframes`, transiciones largas, `setTimeout` o `setInterval` que simulan tiempos | Sin `@keyframes` ni JS. Un comentario de intención junto al elemento: `<!-- el indicador late mientras el riego está activo -->`. Si el tiempo importa, un escenario (`cargando`) | Lista de animaciones y tiempos convertidos en comentario |
| Lógica JS: filtros, validaciones, cálculos, ordenamientos | Comentario junto al elemento: `<!-- filtra la lista por zona; "Todas" muestra todo -->` | Un ítem "Criterio para el ticket:" por regla, en "Dado, cuando, entonces" |
| Gráfico dibujado por JS o por una librería (canvas, Chart.js, SVG armado en un string) | SVG estático con datos ficticios, colores con `var(--color-*)` en `fill` o `stroke` | Qué gráfico era y de qué datos sale |
| Modal, drawer, popover | `<dialog open>` o el bloque dentro de un escenario de la vista que lo abre | |
| Tema claro y oscuro | `[data-theme="dark"]` en `tokens.css`, solo `--color-*`. Nada en la vista: el control de tema lo pone `proto.js` | |
| `toggleTheme()` u otra función definida y nunca llamada | Nada | Se menciona como conflicto en "Lo que no se pudo ver" |
| Variantes A, B y C de una pantalla | Solo la elegida | Cuál se eligió y quién la eligió |
| Imágenes, fotos, avatares | Marcador: un bloque con la proporción y un texto ("Foto de la parcela") o iniciales | |
| Fuentes externas (Google Fonts) | La familia en `--font-family-base` con respaldo del sistema, sin `<link>` ni `@import` | Qué fuente tenía el mockup |
| Recursos por CDN | Nada | |
| Historial dentro del archivo ("cambio #21", "v4.3", versiones en comentarios o ids) | Nada: git lo reemplaza | |
| Navegación entre pantallas | Enlace a la otra vista (`href="historial.html"`) o comentario | |
| Enlaces profundos (`#connect`, `?plan=`) | Un escenario si muestran otro estado; si no, comentario | |
| Datos reales: nombres, correos, dominios | Ficticios y verosímiles, dominios `example.com` | Qué se reemplazó |

Una vista convertida sigue pasando `revisar.py` sin bloqueos: si para no perder algo del mockup hace falta romper una regla de la convención, no se rompe; se escribe como comentario y va al informe.
