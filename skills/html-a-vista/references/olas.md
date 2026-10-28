# Olas y contratos

Qué recibe y qué devuelve cada subagente, y la plantilla del contrato de vista.

## Contenido

- Reglas para todos
- Ola 1
- Ola 2
- Contrato de vista
- Ola 3

---

## Reglas para todos

- Cada subagente escribe solo en su carpeta de `<trabajo>` y devuelve la ruta y un resumen de cinco líneas o menos. No pega el contenido en su respuesta.
- Ninguno escribe en el repositorio de diseño, salvo el integrador en el último paso.
- Ninguno abre el mockup original ni una parte entera: lee los trozos que le tocan y busca con grep en el resto (`trozos/<parte>/script*.js`, `estilos*.css`) lo que le falte.
- Todos siguen la convención de vista de `spec-a-html`: `references/vista-html.md` y `references/design-system.md` de esa skill. Pásales esas rutas.
- Todos aplican `sin-equivalente.md` y `escenarios.md` de esta skill.

## Ola 1

Tres subagentes. El de tokens va primero, porque los otros dos usan sus nombres; cuando producto decide la tabla, los otros dos corren en paralelo.

**Tokens** (`<trabajo>/ola-1/tokens/`). Recibe la ruta de `tokens.css` del repositorio si existe, `manifiesto.json` (variables y valores por parte), los `estilos*.css` de cada parte y `references/tokens.md`. Corre `tokens.py mapear` o `consolidar`, nombra los tokens con la convención de prefijos y escribe `tokens.css` propuesto y `tabla.md` con lo que producto decide. Devuelve cuántos valores van a tokens existentes, cuántos quedan fuera y la ruta de la tabla.

**Componentes base** (`<trabajo>/ola-1/componentes/`). Recibe el CSS del shell o de la parte cuyas reglas más se repiten, el `tokens.css` decidido y `components.css` del repositorio si existe. Escribe `components.css` con los componentes compartidos (botones, campos, tablas, tarjetas, badges, alertas, navegación, estados vacíos, esqueletos), solo con variables de tokens, y `catalogo.md`: clase original del mockup y componente que la reemplaza.

**Shell y escenarios globales** (`<trabajo>/ola-1/shell/`). Recibe el markup del resto o del shell, el JS del shell y las funciones de modo que lista el resumen (las que propagan estado entre módulos, los menús DEMO). Escribe el borrador de la vista del marco, `escenarios-globales.md` (nombre fijo de cada escenario global, qué lo activa en el mockup, qué módulos afecta) y `rutas.md` (rutas o pestañas y a qué vista lleva cada una). En un documento único sin marco común, escribe solo los escenarios globales.

## Ola 2

Un subagente por fila de la tabla pantalla a vista, en paralelo (`<trabajo>/ola-2/<vista>/`). Recibe:

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

**Integrador** (`<trabajo>/ola-3/`).

1. Copia el repositorio de diseño en `<trabajo>/ola-3/repo/`, agrega `tokens.css` de la ola 1, arma `components.css` final (base más lo nuevo de cada contrato, sin duplicar) y copia `proto.js` de `spec-a-html` sin modificar si no existe.
2. Pone cada borrador en `design/vistas/<épica>/<vista>.html` de la copia, unifica clases con el catálogo y los nombres de los escenarios globales.
3. Corre, por vista, `python3 -B <skill>/scripts/inventario.py <vista> <trozos de origen> --json --salida <trabajo>/ola-3/inventario/<vista>.json`, y `python3 -B <checklist-diseno>/scripts/revisar.py <trabajo>/ola-3/repo` sobre la copia. Corrige lo que bloquea.
4. Escribe `integracion.md` con la lista de vistas, el resultado de `revisar.py` y lo que corrigió.

**Revisor**, otro subagente que no armó ninguna vista (`<trabajo>/ola-3/revision.md`). Por vista lee el inventario, el contrato, la vista y la sección del spec. Un faltante del inventario con motivo en el contrato (dato real reemplazado, control de prototipo hecho escenario) no bloquea; uno sin motivo, sí. Decide aprobada o no, con lo que falta.

**Integrador, segundo paso**. Copia al repositorio de diseño solo las vistas aprobadas y los archivos de `design/` que usan, y las secciones del spec que haya que actualizar (escenarios globales, épicas del mockup compuesto). Nada de `<trabajo>` más que eso: ni contratos, ni inventarios, ni el original.
