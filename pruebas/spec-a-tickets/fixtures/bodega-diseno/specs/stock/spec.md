# Spec · Alertas de stock bajo

## Contexto

Bodega es un sistema de inventario para almacenes de barrio. Los dueños se enteran de que se acabó un producto cuando un cliente lo pide.

## Historias

### Configurar mínimo de stock

Como dueño, quiero definir un stock mínimo por producto, para saber cuándo reponer.

- Dado que edito un producto, cuando ingreso un mínimo de 5 y guardo, entonces el producto muestra el mínimo.
- Dado que ingreso un mínimo negativo, cuando guardo, entonces veo un error junto al campo.

### Ver productos bajo el mínimo

Como dueño, quiero ver qué productos están bajo su mínimo, para hacer el pedido al proveedor.

- Dado que hay productos bajo el mínimo, cuando entro a "Reponer", entonces veo producto, stock actual, mínimo y proveedor, ordenados por cuánto faltan.
- Dado que ningún producto está bajo el mínimo, cuando entro, entonces veo un mensaje que lo confirma.

## Estados por vista

- Editar producto: normal, error de validación, guardado.
- Reponer: normal, vacío, cargando, error, muchos datos.

## Reglas

- Un producto sin mínimo no aparece en "Reponer".

## Fuera de alcance

- Pedido automático al proveedor.
