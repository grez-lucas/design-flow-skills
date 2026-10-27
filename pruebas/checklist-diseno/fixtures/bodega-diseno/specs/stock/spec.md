> Congelado el 2026-10-25: los tickets BOD-1 y BOD-2 mandan.

# Spec · Alertas de stock bajo

## Contexto

Los dueños de almacenes de barrio se enteran de que se acabó un producto cuando un cliente lo pide.

## Historias

### BOD-1 · Configurar mínimo de stock

Como dueño, quiero definir un stock mínimo por producto, para saber cuándo reponer.

- Escenario 1: Dado que edito un producto, cuando ingreso un mínimo de 5 y guardo, entonces el producto muestra el mínimo.
- Escenario 2: Dado que ingreso un mínimo negativo, cuando guardo, entonces veo un error junto al campo.

### BOD-2 · Ver productos bajo el mínimo

Como dueño, quiero ver qué productos están bajo su mínimo, para hacer el pedido al proveedor.

- Escenario 1: Dado que hay productos bajo el mínimo, cuando entro a "Reponer", entonces veo producto, stock actual, mínimo y proveedor.
- Escenario 2: Dado que ningún producto está bajo el mínimo, cuando entro, entonces veo un mensaje que lo confirma.

## Estados por vista

- Editar producto: normal, error-validacion, guardado, cargando, error, sin permiso (no aplica: solo el dueño usa la app), muchos datos (no aplica: un solo producto).
- Reponer: normal, vacío, cargando, error, sin permiso (no aplica: solo el dueño usa la app), muchos datos.
- Plan: la app tiene plan Gratis y plan Almacén; en Gratis, "Reponer" muestra solo 5 productos y una invitación a pasar a Almacén. Estado plan-gratis en Reponer.

## Reglas

- Un producto sin mínimo no aparece en "Reponer".

## Decisiones del grilling

| Decisión | Quién | Estado |
| :--- | :--- | :--- |
| Plan Gratis limita Reponer a 5 productos | Ana (producto) | decidida |

## Fuera de alcance

- Pedido automático al proveedor.

## Enlaces

- Tickets: BOD-1, BOD-2
- Vistas: `design/vistas/stock/`
