# Spec · Semilla integrado

## Contexto

Semilla reúne en una sola aplicación la gestión de un huerto comunitario: el banco de semillas, el compostaje y los socios con sus cuotas. Este spec es general: describe lo que hace el prototipo integrado, módulo por módulo. Los tickets se escriben solo para lo que se vaya a construir.

## Historias

### SEM-30 · Marco de la aplicación

Como socio del huerto, quiero moverme entre inventario, compostaje y socios desde un menú lateral, para no perderme entre módulos.

- Escenario 1: Dado que entro a Semilla, cuando abro la aplicación, entonces veo el menú lateral con Inventario, Compostaje y Socios, y el inventario abierto.
- Escenario 2: Dado que tengo notificaciones, cuando las abro, entonces veo la lista en un panel lateral.

### SEM-31 · Inventario de semillas

Como encargado del banco de semillas, quiero ver los lotes con su cultivo, origen, cantidad y estado, para saber qué hay para intercambiar.

- Escenario 1: Dado que hay lotes, cuando entro al inventario, entonces veo la tabla de lotes y puedo abrir el detalle de cada uno.
- Escenario 2: Dado que agrego un lote, cuando la cantidad no es mayor que cero, entonces veo "La cantidad tiene que ser mayor que cero.".
- Escenario 3: Dado que un lote se agotó, cuando lo doy de baja, entonces deja de estar disponible para intercambio.

### SEM-32 · Compostaje

Como encargada del compostaje, quiero ver los residuos recibidos, las pilas activas y la temperatura de cada pila, para saber cuándo voltear.

- Escenario 1: Dado que hay pilas activas, cuando entro a compostaje, entonces veo el resumen del mes y la curva de temperatura de una pila.
- Escenario 2: Dado que registro un aporte, cuando guardo, entonces el aporte suma a los residuos del mes.

### SEM-33 · Socios y cuotas

Como tesorera, quiero ver los socios, sus cuotas y los ajustes del huerto, para cobrar a tiempo.

- Escenario 1: Dado que hay socios, cuando entro a socios, entonces veo nombre, correo, parcela, antigüedad y estado de la cuota.
- Escenario 2: Dado que registro el pago de una cuota, cuando guardo, entonces la cuota queda pagada.

## Estados por vista

- Marco: normal, sin-permiso (no aplica, todos los socios ven el marco).
- Inventario, detalle de lote, movimientos: normal, vacío, cargando, error, sin permiso, muchos datos.
- Resumen y pilas de compostaje: normal, vacío, cargando, error, sin permiso, muchos datos.
- Socios, cuotas y ajustes: normal, vacío, cargando, error, sin permiso, muchos datos.

## Reglas

- Cuando la báscula comunitaria está desconectada, el inventario carga los pesos a mano y el compostaje estima el peso de cada aporte.

## Decisiones del grilling

| Decisión | Quién | Estado |
| :--- | :--- | :--- |
| El prototipo integrado reemplaza a los mockups sueltos de cada módulo | Paula Rivas | decidida |

## Fuera de alcance

- Pagos en línea de cuotas.

## Enlaces

- Tickets: ninguno todavía
- Vistas: `design/vistas/<módulo>/`
