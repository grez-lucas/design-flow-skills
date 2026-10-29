# Olas y contratos

Qué hace cada ola, qué recibe y qué devuelve cada subagente, y la plantilla del contrato de vista. Los tokens de la ola 1 y la integración de la ola 3 los haces tú, el agente que conversa con producto; lo demás, subagentes.

## Contenido

- Reglas para todos
- Ola 1
- Ola 2
- Contrato de vista
- Ola 3

---

## Reglas para todos

- Cada subagente escribe solo en su carpeta de `<trabajo>` y devuelve la ruta y un resumen de cinco líneas o menos. No pega el contenido en su respuesta.
- Ninguno escribe en el repositorio de diseño: eso lo haces tú al integrar, con lo que aprobó el revisor.
- Ninguno abre el mockup original ni una parte entera: lee los trozos que le tocan y busca con grep en el resto (`trozos/<parte>/script*.js`, `estilos*.css`) lo que le falte.
- Todos siguen la convención de vista de `spec-a-html`: `references/vista-html.md` y `references/design-system.md` de esa skill. Pásales esas rutas.
- Todos aplican `sin-equivalente.md` y `escenarios.md` de esta skill. Pásales esas rutas a todos, los de la ola 1 incluidos.

## Ola 1

Los tokens van primero, porque los dos subagentes usan sus nombres; cuando producto decide la tabla, los dos corren en paralelo.

**Tokens, a cargo tuyo** (`<trabajo>/ola-1/tokens/`). Con la ruta de `tokens.css` del repositorio si existe, los `estilos*.css` de cada parte y `references/tokens.md`, corres `tokens.py mapear` o `consolidar`, nombras los tokens con la convención de prefijos y escribes `tokens.css` propuesto y `tabla.md` con lo que producto decide. Las variables y valores por parte están en `manifiesto.json`; búscalos con grep si hace falta, sin leerlo entero.

**Componentes base** (`<trabajo>/ola-1/componentes/`). Recibe el CSS del shell o de la parte cuyas reglas más se repiten, el `tokens.css` decidido y `components.css` del repositorio si existe. Escribe `components.css` con los componentes compartidos (botones, campos, tablas, tarjetas, badges, alertas, navegación, estados vacíos, esqueletos), solo con variables de tokens, y `catalogo.md`: clase original del mockup y componente que la reemplaza. Recibe la ruta de `sin-equivalente.md`: un componente que en el mockup se anima queda quieto, sin `@keyframes` ni `animation`, y el catálogo dice qué animación tenía para que la vista lleve el comentario de intención. Lo mismo con `@import` y fuentes externas. `revisar.py` bloquea las dos cosas también en `components.css` y `tokens.css`.

**Escenarios globales** (`<trabajo>/ola-1/globales/`). Recibe el markup del resto o del shell, el JS del shell y las funciones de modo que lista el resumen (las que propagan estado entre módulos, los menús DEMO). Escribe `escenarios-globales.md` (nombre fijo de cada escenario global, qué lo activa en el mockup, qué módulos afecta) y `rutas.md` (rutas o pestañas y a qué vista lleva cada una). En un documento único sin marco común, escribe solo los escenarios globales. No escribe la vista del marco: el marco es una fila de la ola 2, con su subagente y su contrato, para que el revisor lo apruebe o lo devuelva como a cualquier vista.

## Ola 2

Un subagente por fila de la tabla pantalla a vista, en paralelo (`<trabajo>/ola-2/<vista>/`), nombrado `Ola 2: <vista>` con el nombre del archivo de la vista sin `.html`. El marco también: su fila tiene su subagente, `Ola 2: <vista del marco>`, que además recibe `rutas.md`. Uno por vista, nunca dos vistas en el mismo: el contrato, el revisor y la vuelta con notas van vista por vista. Si una vista sola pasaría unos 50 mil tokens de lectura, se parte en dos subagentes, `Ola 2: <vista> (parte 1)` y `(parte 2)`, que escriben un solo contrato; dos vistas no se juntan en uno. Recibe:

- su fila de la tabla y la sección del spec que le toca, con sus tickets si los hay;
- las rutas de sus trozos de markup (pantalla y superposiciones) y de los JS y CSS de su parte, para buscar con grep;
- `tokens.css`, `components.css`, `catalogo.md` y `escenarios-globales.md` de la ola 1, en vez del CSS entero del mockup;
- `trozos/iconos.html` si su markup cita `<svg data-icono>`.

Escribe `<vista>.html` (borrador con la convención de `spec-a-html`, enlazando `../../tokens.css`, `../../components.css` y `../../proto.js`) y `contrato.md`.

## Contrato de vista

Campos fijos, en este orden, en `contrato.md`:

```markdown
# Contrato · <vista>

## Vista y origen
- Vista: <id>, archivo `design/vistas/<épica>/<vista>.html`, épica <épica>
- Origen: parte <parte>, trozos <rutas>, líneas <a> a <b> del original

## Escenarios
| Escenario | Activador original | Qué cambia | data-state |
| :--- | :--- | :--- | :--- |
- Base que no aplican, con motivo:

## Componentes
| Clase original | Componente | Nuevo |
| :--- | :--- | :--- |

## Valores sin token
- <valor> en <selector>: token usado, o "pendiente de decisión"

## Textos y datos
- Textos que cambiaron respecto del original y por qué (dato real reemplazado por ficticio, dominio real a example.com)

## Interacciones como comentario
- <elemento>: <qué pasa al hacer clic, a qué vista lleva, qué valida o calcula>

## Lo que no pudo ver
- Contenido que el JS arma y no leyó, estados que no alcanzó, conflictos (data-state propio, tema sin control)
```

## Ola 3

**Integración, a cargo tuyo** (`<trabajo>/ola-3/`). Son copias y scripts de salida corta; no hace falta un subagente.

1. Copias el repositorio de diseño en `<trabajo>/ola-3/repo/`, agregas `tokens.css` de la ola 1, armas `components.css` final (base más lo nuevo de cada contrato, sin duplicar) y copias `proto.js` de `spec-a-html` sin modificar si no existe.
2. Pones cada borrador en `design/vistas/<épica>/<vista>.html` de la copia, unificas clases con el catálogo y los nombres de los escenarios globales.
3. Corres, por vista, `python3 -B <skill>/scripts/inventario.py <vista> <trozos de origen> --json --salida <trabajo>/ola-3/inventario/<vista>.json`, y `python3 -B <checklist-diseno>/scripts/revisar.py <trabajo>/ola-3/repo` sobre la copia. Lo que bloquea lo corriges tú antes de lanzar al revisor, porque la vista todavía va a pasar por él; lo que el revisor no aprobó ya no lo corriges tú (ver "Vuelta de una vista no aprobada").
4. Con navegador, sacas las capturas por escenario de cada vista de la copia y del original (`escenarios.md`, sección "Capturas") en `<trabajo>/capturas/`, antes de lanzar al revisor.
5. Escribes `integracion.md` con la lista de vistas, el resultado de `revisar.py` y lo que corregiste.

**Revisor**, un subagente que no armó ninguna vista (`<trabajo>/ola-3/revision.md`). Por vista lee el inventario, el contrato, la vista y la sección del spec, y con navegador las capturas del original y de la vista, cuyas rutas le pasas. Una diferencia que se ve en las capturas cuenta como un faltante del inventario. Un faltante del inventario con motivo en el contrato (dato real reemplazado, control de prototipo hecho escenario) no bloquea; uno sin motivo, sí. Decide aprobada o no, con lo que falta, y escribe un encabezado por vista con el nombre de su archivo sin `.html`:

```markdown
## <vista>: aprobada

## <vista>: no aprobada
- <lo que falta>
```

En la segunda revisión agrega al final del mismo archivo `## <vista>, segunda revisión: aprobada` (o `no aprobada`), sin borrar la primera. Vale el último veredicto de cada vista, y quien lea el archivo ve el recorrido completo.

**Vuelta de una vista no aprobada**. No la corriges tú, aunque sea una línea: el revisor es la única mirada que no armó la vista, y lo que arregla quien integra entra sin que nadie independiente lo vea. Vuelve a su subagente de la ola 2 con las notas del revisor (`SendMessage`, o un subagente nuevo `Ola 2: <vista>` con el borrador, el contrato y las notas si la sesión no puede continuar el primero), la integras de nuevo con los pasos 2 a 4 y lanzas al revisor para la segunda revisión. Una vuelta por vista; si sigue sin aprobarse, queda fuera y va al informe como pendiente.

**Integración, segundo paso**. Mueves al repositorio de diseño con `python3 -B <skill>/scripts/aprobadas.py <trabajo> <repo-de-diseño>`, no a mano. El script lee `revision.md` con el formato de arriba y copia de `<trabajo>/ola-3/repo/design/` solo las vistas nuevas o cambiadas cuyo último veredicto es "aprobada", más `tokens.css`, `components.css` y `proto.js` si cambiaron; deja fuera, y lo lista, lo no aprobado, lo que no tiene veredicto y cualquier otro archivo de la copia, y sale con 1 si dejó algo. Las secciones del spec que haya que actualizar (escenarios globales, épicas del mockup compuesto) las copias tú. Nada de `<trabajo>` más que eso: ni contratos, ni inventarios, ni el original.
