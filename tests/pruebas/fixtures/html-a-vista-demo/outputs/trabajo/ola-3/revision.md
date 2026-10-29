# Revisión · ola 3 (sin render, sin navegador)

## panel: APROBADA

Bloqueos: ninguno.

Verificado:
- Los 8 estados del spec (normal, vacío, cargando, error, sin permiso, muchos datos, sensor sin señal, tanque vacío) más tanque-a-la-mitad, regar-ahora y duracion-invalida están en `data-escenarios` y cada uno tiene su bloque.
- SEM-20: escenario 1 (cada zona con humedad y próximo riego), escenario 2 (aviso con zona y "hace 3 horas") y escenario 3 (pausa del riego automático) están. Regla del tanque: un solo chip por escenario (Lleno, A la mitad, Sin agua), sin mezclas entre escenarios.
- SEM-21: el modal muestra 5 a 60 en `min`/`max`; el texto del error es exacto: "La duración tiene que estar entre 5 y 60 minutos.". `duracion-invalida` usa valor 3, `aria-invalid` y `.field__error`. `regar-ahora` no muestra el error.
- `data-state`: la zona de nombre largo es solo de `muchos-datos`, y la humedad atenuada es solo de `sensor-sin-senal`. Ningún `data-state` original (full, partial, off) queda en la vista.
- Controles DEMO fuera de la vista (inventario: 0 en vista). Faltantes del inventario: ninguno (21/21, 5/5, 1/1).
- Todas las clases usadas existen en `components.css`. La vista no lleva `style`, `<style>` ni valores sueltos.
- `proto.js` clona los hijos de `.card-grid` con `data-repeat`, así que la duda del contrato sobre eso queda resuelta.
- Los valores fuera de umbral usan el token existente más cercano. El velo y los 380px no se aplican, como se acordó.

Observaciones no bloqueantes:
1. El mockup, con `body.sin-senal`, atenúa la humedad de las TRES zonas (`estilos.css` línea 28). La vista atenúa solo la de zona norte. Tiene sentido con el spec (el aviso nombra solo esa zona), pero el contrato dice que "queda como en el mockup". Corregir esa frase o decidir con producto cuál vale.
2. Resuelta la duda del contrato sobre `body.tanque-vacio`: `estilos.css` solo muestra el aviso, no oculta nada más.
3. La vista de `vacio` no ofrece acción. Es aceptable porque el spec no la pide.
4. Los avisos y el chip "Sin agua" usan el fondo `.alert` (surface) y no el rosado del mockup (#fde2e2). Está pendiente de decisión de producto.

## historial: NO APROBADA

Bloquea:
1. En `normal` se ve la cuarta fila ("11 de abril, 09:15", "Zona invernadero de almácigos y plantines nuevos", "60 min", "Manual, Valentina Fuentes-Montenegro de la Barra"). Esa fila es fixture de `muchos-datos` (inventario `textos_nuevos`; el mockup tiene 3 filas), pero el `<tr>` no tiene `data-state`, así que sale en `normal`. El panel sí lo hace bien (la zona larga lleva `data-state="muchos-datos"`).
   Arreglo: `<tr data-state="muchos-datos">` en esa fila. `proto.js` la conserva y la clona en `muchos-datos` (50 filas) y la oculta en `normal`.

Verificado, sin bloqueo:
- SEM-22 escenario 1: fecha, zona, duración y origen, con orden del más reciente al más antiguo.
- Los 6 escenarios del spec están.
- El único faltante del inventario, "Manual, Bruno Lagos" (17/18), tiene motivo en el contrato (persona real reemplazada por "Camila Rojas").
- Controles 2/2. Controles DEMO fuera de la vista.
- Las clases usadas existen en `components.css`.
- La vista no lleva `style` ni valores sueltos.
- `sensor-sin-senal` y `tanque-vacio` no aplican al historial: el original no cambia nada ahí.

Observaciones no bloqueantes:
1. El texto de `sin-permiso` ("quienes coordinan el riego... coordinadora del huerto") es propuesta de la ola; el spec no define quién accede. Confirmar con producto.
2. "Los últimos días" no tiene rango en el spec ni en el mockup; la paginación o el límite quedan como comentario pendiente.
3. El `h1` "Panel de riego" se repite en el historial por el marco; está bien, pero conviene confirmarlo.
4. `cargando` usa `.skeleton` sueltos y no filas de tabla (el comentario lo dice); aceptable.

## historial, segunda revisión: APROBADA

El bloqueo anterior queda resuelto. En `normal` solo se ven las 3 filas del mockup. El segundo `tbody` lleva `data-state="muchos-datos" data-repeat="47"`, así que `proto.js` lo oculta en los demás escenarios y, en `muchos-datos`, lo clona de 3 a 47 filas (50 con las 3 de arriba). El contrato coincide con la vista. No cambió nada más: sin clases nuevas, sin estilos propios, 6 escenarios, SEM-22 cubierto.

Observación no bloqueante: las filas clonadas repiten fechas y no quedan en orden descendente. Es aceptable para un fixture de volumen.
