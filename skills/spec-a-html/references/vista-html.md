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
- `muchos-datos` muestra la versión con volumen real: textos largos, nombres que no caben, tablas de 50 filas. Para no inflar el archivo, escribe tres o cuatro filas variadas y marca el contenedor con `data-repeat="50"`: `proto.js` clona las filas en ese escenario.
- `cargando` usa `.skeleton`, no spinners sueltos.
- `sin-permiso` muestra lo que ve un usuario sin acceso, no una pantalla en blanco.
- Los escenarios propios del spec se nombran en minúsculas con guiones: `plan-expirado`, `pago-rechazado`.

`proto.js` arma un panel fuera del frame con los escenarios y los anchos (390, 1280 y 1440), y lee `?escenario=` y `?ancho=` de la URL. Si `tokens.css` define un tema oscuro, el panel suma un grupo "Tema" con `claro` y `oscuro`, y la URL acepta `?tema=claro|oscuro`; la vista abre en claro salvo `?tema=oscuro`. `?proto=0` esconde el panel para una captura limpia y respeta `?tema=`. No escribas otros controles de prototipo, tampoco un selector de tema propio.

## Reglas

- Valores visuales solo con `var(--...)` de `tokens.css`. El `<style>` de la vista es para layout propio de esa vista (grids, posiciones) y sigue la misma regla.
- Componentes de `components.css` antes que estilos nuevos. Si falta uno que se va a repetir, agrégalo allá.
- HTML semántico: `header`, `nav`, `main`, `section`, `table`, `form`, `label`, `button`. Ayuda a DEV a leer la intención y le da accesibilidad básica a la vista.
- La vista enlaza `../../tokens.css`, `../../components.css` y `../../proto.js`, y nada más: ni otra hoja de estilo (tampoco con `@import`), ni otro script. Lo que va en otro archivo no lo ve la revisión de `checklist-diseno`.
- Sin frameworks, sin CDN, sin imágenes externas. Íconos como SVG inline cortos o un carácter, y avatares como iniciales.
- Sin animaciones (`@keyframes`): DEV no lee una duración en CSS como un requisito. El movimiento va como comentario de intención junto al elemento (`<!-- el indicador late mientras el riego está activo -->`), y si el tiempo importa, como un escenario (`cargando`).
- Datos ficticios y verosímiles: nombres inventados, dominios `example.com`, montos y fechas creíbles. Nada de clientes reales.
- Textos de la interfaz completos, no "Lorem ipsum": el texto es parte del diseño y DEV lo copia.
- Un flujo de varios pasos puede ir en un solo archivo con un escenario por paso (`paso-1`, `paso-2`) o en un archivo por paso; elige lo que deje cada archivo más corto y dilo en el plan.
- Interacciones que el HTML no muestra (qué pasa al hacer clic, validaciones, tiempos) van como comentario corto junto al elemento: `<!-- al confirmar: vuelve al listado con un aviso de éxito -->`. No escribas JavaScript de comportamiento, tampoco en un `href="javascript:..."` ni en un `onclick`.

## Tamaño

Una vista típica debería quedar bajo 300 líneas. Si crece más, casi siempre hay estilos repetidos que son componentes, o markup duplicado por escenario que debería ser un solo bloque con `data-state`.
