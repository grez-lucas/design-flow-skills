# Design system

Cómo se escriben `design/tokens.css` y `design/components.css`, y cómo se extraen los valores de un producto que ya existe.

## Contenido

- Convención de tokens
- Temas
- Reglas de components.css
- Extraer del código
- Extraer de una marca o un mockup

---

## Convención de tokens

`tokens.css` declara variables CSS en `:root`. Es un solo nivel, semántico y en inglés: el nombre dice para qué sirve el valor, no cómo se ve. CSS no tiene tipos, así que el prefijo hace ese papel y es lo que permite revisar el archivo de forma mecánica.

| Prefijo | Para qué | Ejemplos |
| :--- | :--- | :--- |
| `--color-` | Colores por uso | `--color-bg`, `--color-surface`, `--color-surface-alt`, `--color-border`, `--color-text`, `--color-text-muted`, `--color-primary`, `--color-primary-contrast`, `--color-success`, `--color-warning`, `--color-danger`, `--color-info` |
| `--font-family-` | Familias | `--font-family-base`, `--font-family-mono` |
| `--font-size-` | Escala de tamaños | `--font-size-xs`, `--font-size-sm`, `--font-size-md`, `--font-size-lg`, `--font-size-xl`, `--font-size-2xl` |
| `--font-weight-` | Pesos | `--font-weight-regular`, `--font-weight-medium`, `--font-weight-bold` |
| `--line-height-` | Interlineado | `--line-height-tight`, `--line-height-base` |
| `--space-` | Escala de espacios, base 4 px | `--space-1` (4px) a `--space-8` (32px), más `--space-12`, `--space-16` si hacen falta |
| `--radius-` | Radios | `--radius-sm`, `--radius-md`, `--radius-lg`, `--radius-full` |
| `--shadow-` | Elevación | `--shadow-1`, `--shadow-2`, `--shadow-3` |
| `--size-` | Medidas fijas de layout | `--size-sidebar`, `--size-topbar`, `--size-content-max` |

Reglas:

- Un valor por uso, no un uso por pantalla. Si dos vistas necesitan "un gris para texto secundario", es `--color-text-muted` para las dos.
- Antes de agregar un token, revisa si uno existente sirve. Cada token nuevo es algo más que DEV tiene que trasladar a su stack.
- Los anchos de referencia van como comentario al inicio del archivo, porque las variables CSS no funcionan dentro de `@media`: `/* anchos: 390 móvil, 1280 escritorio, 1440 escritorio amplio */`.
- Sin valores derivados con `calc()` dentro de `tokens.css`: el archivo es una lista que se lee de un vistazo y se traslada a otros stacks.

## Temas

El tema claro va en `:root`. Un tema oscuro, si el producto lo tiene, va en `[data-theme="dark"]` y redefine solo los `--color-*`. Los demás tokens no cambian entre temas.

Con el tema oscuro definido, el panel de `proto.js` suma un grupo "Tema" y la vista acepta `?tema=oscuro`, que pone `data-theme="dark"` en `<html>`. `proto.js` detecta el tema comparando `--color-bg`, `--color-surface` y `--color-text` con y sin `data-theme`, así que el bloque oscuro redefine al menos uno de esos tres. No lee las reglas de `tokens.css` porque Chrome las bloquea cuando la vista se abre como `file://`.

## Reglas de components.css

`components.css` tiene los componentes que se repiten entre vistas: botones, campos, tablas, tarjetas, badges, alertas, navegación, estados vacíos, esqueletos de carga.

- Solo variables de `tokens.css` para color, tipografía, espacio, radio y sombra. Se admiten `0`, `1px` y `2px` en bordes y anillos de foco, `100%`, `auto` y porcentajes de layout.
- Nombres de clase cortos con modificadores: `.btn`, `.btn--primary`, `.btn--danger`, `.field`, `.field--error`, `.card`, `.table`, `.badge--success`, `.alert--warning`, `.empty-state`, `.skeleton`, `.topbar`, `.sidebar`.
- Un componente entra cuando lo usa más de una vista o cuando es claramente reutilizable. Lo que es propio de una vista se queda en el `<style>` de esa vista.
- Al agregar un componente, agrega también sus estados visibles en la misma regla: `:hover`, `:focus-visible`, `[disabled]`, `[aria-invalid="true"]`.
- Sin `@keyframes` ni `@import` o `url()` a recursos externos, igual que en las vistas: un componente animado se escribe con su estado quieto, y el movimiento va como comentario junto al elemento en la vista que lo usa. `revisar.py` de `checklist-diseno` lo bloquea también aquí y en `tokens.css`.

## Extraer del código

Si el código del producto está en la máquina, los valores reales están ahí. Busca en este orden según el stack y traslada cada valor al token que corresponde por uso:

| Stack | Dónde mirar |
| :--- | :--- |
| Tailwind v4 | Bloque `@theme` en el CSS principal |
| Tailwind v3 | `tailwind.config.js` o `.ts`, en `theme.extend` |
| Quasar | `src/css/quasar.variables.scss` o `.sass` (`$primary`, `$secondary`, `$positive`, `$negative`, `$warning`, `$info`) y `quasar.config` en `brand` |
| Vue o React con CSS propio | Variables `--*` en `:root` del CSS global; si no hay, los colores más repetidos en los estilos |
| Librería de componentes interna | Su archivo de tema o de tokens, por ejemplo un paquete `ui` en un monorepo |
| Flutter | `ThemeData`, `ColorScheme` y `TextTheme`, en el paquete de UI o en `theme.dart` |

Cuando el código tiene valores sueltos repetidos (diez tonos de gris parecidos), propón consolidarlos en pocos tokens y muestra la tabla de equivalencias a la persona antes de escribir. No traslades el desorden.

## Extraer de una marca o un mockup

Con una guía de marca, toma sus colores, tipografías y, si los define, espacios y radios. Con un mockup HTML existente, lee primero sus variables CSS y después los valores más repetidos, igual que con el código. Un mockup grande no se lee entero: busca las variables y los colores con grep y lee solo esas líneas.

Si la fuente no define algo (sombras, escala de espacios), completa con la plantilla `assets/tokens.css` y dilo.
