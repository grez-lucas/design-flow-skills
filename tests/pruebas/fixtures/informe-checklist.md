Ana, revisé las tres vistas de `design/vistas/stock/` contra el spec congelado (`specs/stock/spec.md`) y los tickets BOD-1 y BOD-2. Editar producto se puede llevar a la planning. Reponer y Reponer por plan todavía no: les faltan cosas que DEV tendría que preguntar o inventar.

## Resultado

3 vistas revisadas: 1 lista (con avisos), 2 con bloqueos.

## design/vistas/stock/editar-producto.html · BOD-1

Conviene mirar:
- Marca "vacío" como no aplica ("siempre hay un producto abierto"). El spec no lo menciona. El motivo es razonable, pero conviene confirmarlo en la planning para que quede dicho.
- En el escenario de error, "Reintentar." es texto plano dentro del aviso, no un botón. DEV no va a saber si hay una acción para reintentar o si el usuario tiene que recargar la página.
- En "error-validacion" la etiqueta "Stock mínimo" apunta al campo del escenario normal, no al que muestra el error. Es un detalle de accesibilidad que DEV puede arrastrar si copia el HTML tal cual.

Los dos criterios de BOD-1 se ven: "guardado" muestra el mínimo guardado (5 unidades) y "error-validacion" muestra el error junto al campo con el valor -2.

## design/vistas/stock/reponer.html · BOD-2

Bloquea:
- Falta la columna "Proveedor". El escenario 1 de BOD-2 pide ver producto, stock actual, mínimo y proveedor, y la tabla solo tiene las tres primeras. DEV no sabría dónde ni cómo mostrar el proveedor.
- Falta el escenario "error", que el spec pide para Reponer. DEV no sabría qué mostrar si la lista no carga ni qué puede hacer el dueño.
- Falta el escenario "plan-gratis", que el spec pide en Reponer: solo 5 productos y una invitación a pasar al plan Almacén. Hoy no existe en esta vista (ver también Reponer por plan, más abajo).
- Tiene un escenario "sin-permiso" ("No tienes acceso a Reponer") que el spec descarta: solo el dueño usa la app. DEV podría construir un control de permisos que nadie pidió y que no tiene criterio de aceptación. Hay que sacarlo y marcarlo como no aplica con ese motivo.
- El rojo del stock que falta está escrito a mano (`#d93025`) en vez de usar el color de peligro del sistema de diseño (`--color-danger`, que es otro tono). DEV terminaría con un rojo distinto al del resto de la app.

Conviene mirar:
- La línea "Pedidos a: ventas@abastos-quiltraco.cl" usa un dominio que podría ser real; los datos de ejemplo van con `example.com`. Además ni el spec ni BOD-2 piden un correo de pedidos general: si la idea es mostrar el proveedor, eso va en la columna de cada producto.
- "Muchos datos" llega a 40 filas, pero repitiendo los mismos tres productos con nombres cortos. Conviene ver cómo se comporta con nombres largos y proveedores distintos.

## design/vistas/stock/reponer-plan.html · sin tickets

Bloquea:
- No cita ningún ticket. Y no hay ticket que cubra el plan Gratis: BOD-1 y BOD-2 no tienen criterios sobre el límite de 5 productos ni la invitación a Almacén, aunque el spec lo da por decidido. Como el spec está congelado y mandan los tickets, hoy esta funcionalidad no tiene criterio de aceptación. Hay que decidir en la planning si se agrega a BOD-2 o va en un ticket nuevo.
- Tiene un selector "Ver como: Plan Almacén / Plan Gratis" dentro de la pantalla. Es un control de prototipo, no del producto, y DEV lo construiría como si el usuario pudiera cambiar de plan desde ahí. Además no cambia nada en la vista.
- El contenido principal es texto de relleno (lorem ipsum): no muestra la lista de 5 productos ni la invitación a pasar a Almacén. DEV no tiene qué construir.
- Los textos de vacío, error y sin permiso son genéricos ("Sin productos.", "Mensaje de error", "Sin permiso."). DEV tendría que inventarlos.
- Repite el escenario "sin-permiso" que el spec descarta, igual que Reponer.

Conviene mirar:
- "Muchos datos" se ve igual que "normal".
- El spec pide el plan Gratis como un escenario de Reponer, no como una vista aparte. Lo más simple es llevarlo a `reponer.html` como escenario "plan-gratis" y eliminar esta vista, para que DEV no tenga dos versiones de la misma pantalla.

## Archivos compartidos

Sin hallazgos en `tokens.css`, `components.css` ni `proto.js`.

Un aviso sobre los tickets: BOD-1 y BOD-2 dicen "ver criterios en el spec" en vez de traer los escenarios escritos. Los criterios deberían vivir en el ticket, que es lo que DEV va a leer.

## Siguiente paso

Antes de la planning, corregir con spec-a-html en modo edición:

1. Reponer: agregar la columna Proveedor, el escenario de error y el escenario plan-gratis; sacar sin-permiso y marcarlo como no aplica; cambiar el rojo por `--color-danger`.
2. Reponer por plan: llevar su contenido real a Reponer como escenario plan-gratis y eliminar la vista.

En la planning, decidir dónde viven los criterios del plan Gratis (BOD-2 ampliado o un ticket nuevo) y confirmar que "vacío" no aplica en Editar producto. Editar producto ya se puede llevar tal como está.
