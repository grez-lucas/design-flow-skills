# HTML de una vista

Plantilla y reglas para `design/vistas/<épica>/<vista>.html`.

## Plantilla

Parte de `assets/vista.html`. La estructura es:

```html
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Alertas · Listado</title>
  <meta name="tickets" content="US-ALERT-002, US-ALERT-003">
  <link rel="stylesheet" href="../../tokens.css">
  <link rel="stylesheet" href="../../components.css">
  <script src="../../proto.js" defer></script>
  <style>
    .alertas-filtros { display: flex; gap: var(--space-3); }
  </style>
</head>
<body data-escenarios="normal, vacio, cargando, error, sin-permiso, muchos-datos, plan-expirado">
  <main data-frame>
    <section data-state="normal muchos-datos">...</section>
    <section data-state="vacio" class="empty-state">...</section>
  </main>
</body>
</html>
```

## Escenarios

- `<body data-escenarios>` lista los escenarios de la vista, separados por coma. El primero es el que se ve al abrir.
- `<body data-no-aplica>` lista los escenarios base que no aplican, cada uno con su motivo: `data-no-aplica="sin-permiso: todos los roles ven esta vista; muchos-datos: la pantalla tiene pocas opciones fijas"`. Escenarios base: normal, vacio, cargando, error, sin-permiso, muchos-datos.
- Un elemento con `data-state="a b"` se ve solo en los escenarios `a` o `b`. Un elemento sin `data-state` se ve siempre. Así, el header y la navegación se escriben una vez y solo cambia lo que de verdad cambia.
- Cuando un bloque cambia poco entre dos escenarios (un texto, un botón deshabilitado), escribe el bloque una vez por escenario, cada copia con su `data-state`. No hay variantes dentro de un bloque: DEV lee cada escenario completo, sin reconstruirlo.
- `muchos-datos` muestra la versión con volumen real: textos largos, nombres que no caben, tablas de 50 filas. Para no inflar el archivo, escribe tres o cuatro filas variadas y marca el contenedor con `data-repeat="50"`: `proto.js` clona las filas en ese escenario. Para que las copias no repitan los mismos nombres, pon en la celda una lista de valores separados por `;`: `<td data-valores="Bruno Díaz; Carla Ruiz; Diego Soto">Ana Pérez</td>`. También sirve en la fila misma, como un `<li>`. La fila escrita muestra su texto, y cada copia de esa fila toma el valor siguiente de la lista; al acabarse, la lista vuelve a empezar. El valor reemplaza todo el contenido del elemento: ponlo en el que tiene solo el texto, no en uno que además lleva un avatar o un ícono. Úsalo en las columnas que más se notan repetidas (nombres, montos, fechas); el resto puede repetirse.
- `cargando` usa `.skeleton`, no spinners sueltos.
- `sin-permiso` muestra lo que ve un usuario sin acceso, no una pantalla en blanco.
- Los escenarios propios del spec se nombran en minúsculas con guiones: `plan-expirado`, `pago-rechazado`.

`proto.js` arma un panel fuera del frame con los escenarios y los anchos (390, 1280 y 1440), y lee `?escenario=` y `?ancho=` de la URL. El panel abre abajo a la izquierda, lejos de los avisos, que van abajo a la derecha; su botón "Cambiar de lado" lo pasa a la derecha cuando tapa algo de la pantalla, y la URL lo recuerda con `?panel=derecha`. Si `tokens.css` define un tema oscuro, el panel suma un grupo "Tema" con `claro` y `oscuro`, y la URL acepta `?tema=claro|oscuro`; la vista abre en claro salvo `?tema=oscuro`. `?proto=0` esconde el panel para una captura limpia y respeta `?tema=`. No escribas otros controles de prototipo, tampoco un selector de tema propio.

## Modales y avisos

El frame (`<main data-frame>`) es la pantalla: `components.css` lo deja con posición relativa y al menos el alto de la ventana. Un modal o un aviso se posiciona dentro del frame, no de la ventana, para que el selector de ancho de `proto.js` también lo achique y la captura a 390 muestre lo que ve un teléfono. Nada de `position: fixed` en la vista: un elemento fijo se mide contra la ventana y queda fuera del frame.

```html
<main data-frame>
  ...
  <!-- al confirmar: anula el pedido y vuelve al listado con un aviso de éxito -->
  <div class="modal" data-state="confirmar-anulacion">
    <dialog open class="modal__dialog" aria-labelledby="titulo-anular">
      <h2 id="titulo-anular">¿Anular el pedido 10482?</h2>
      <p>El cliente recibe un correo con el detalle.</p>
      <div class="modal__actions">
        <button type="button" class="btn">Cancelar</button>
        <button type="button" class="btn btn--danger">Anular pedido</button>
      </div>
    </dialog>
  </div>
  <div class="toast-region" data-state="anulado">
    <p class="alert alert--success" role="status">Pedido 10482 anulado.</p>
  </div>
</main>
```

- El modal es un escenario de la vista que lo abre, con su nombre (`confirmar-anulacion`), y va al final del frame. `.modal` es el velo que cubre el frame, y `<dialog open>` el cuadro, que mide `--size-modal` como máximo y nunca más que el frame.
- Los avisos van en `.toast-region`, abajo a la derecha del frame, con los componentes de `.alert`.
- Un drawer o un popover sigue la misma idea: posición absoluta dentro del frame. Si se repite entre vistas, va a `components.css` como `.modal`.

## Reglas

- Valores visuales solo con `var(--...)` de `tokens.css`. El `<style>` de la vista es para layout propio de esa vista (grids, posiciones) y sigue la misma regla.
- Componentes de `components.css` antes que estilos nuevos. Si falta uno que se va a repetir, agrégalo allá.
- HTML semántico: `header`, `nav`, `main`, `section`, `table`, `form`, `label`, `button`. Ayuda a DEV a leer la intención y le da accesibilidad básica a la vista.
- La vista enlaza `../../tokens.css`, `../../components.css` y `../../proto.js`, y nada más: ni otra hoja de estilo (tampoco con `@import`), ni otro script. Lo que va en otro archivo no lo ve la revisión de `checklist-diseno`.
- Sin frameworks, sin CDN, sin imágenes externas. Íconos como SVG inline cortos o un carácter, y avatares como iniciales.
- La fuente del producto, si tiene una propia, va como archivo en el repositorio de diseño: el `.woff2` en `design/fuentes/` y su `@font-face` en `tokens.css`, con una `url()` relativa (`src: url("fuentes/marca-regular.woff2") format("woff2")`), y la familia en `--font-family-base` con un respaldo del sistema. Nunca desde Google Fonts ni otro CDN: la vista tiene que verse igual sin red. La vista no escribe su propio `@font-face`.
- Sin animaciones (`@keyframes`): DEV no lee una duración en CSS como un requisito. El movimiento va como comentario de intención junto al elemento (`<!-- el indicador late mientras el riego está activo -->`), y si el tiempo importa, como un escenario (`cargando`).
- Datos ficticios y verosímiles: nombres inventados, dominios `example.com`, montos y fechas creíbles. Nada de clientes reales.
- Textos de la interfaz completos, no "Lorem ipsum": el texto es parte del diseño y DEV lo copia.
- Un flujo de varios pasos puede ir en un solo archivo con un escenario por paso (`paso-1`, `paso-2`) o en un archivo por paso; elige lo que deje cada archivo más corto y dilo en el plan.
- Interacciones que el HTML no muestra (qué pasa al hacer clic, validaciones, tiempos) van como comentario corto junto al elemento: `<!-- al confirmar: vuelve al listado con un aviso de éxito -->`. No escribas JavaScript de comportamiento, tampoco en un `href="javascript:..."` ni en un `onclick`.

## Tamaño

Una vista típica debería quedar bajo 300 líneas. Si crece más, casi siempre hay estilos repetidos que son componentes, o markup duplicado por escenario que debería ser un solo bloque con `data-state`.
