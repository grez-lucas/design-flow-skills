> Congelado el 2026-10-26.

# Spec · Proveedores

## Contexto

El dueño anota a mano a quién le compra cada producto y pierde el teléfono del proveedor cuando cambia de cuaderno.

## Historias

### Ver proveedores

Como dueño, quiero ver la lista de mis proveedores con su contacto, para llamarlos cuando tengo que reponer.

- Escenario 1: Dado que tengo proveedores, cuando entro a "Proveedores", entonces veo nombre, contacto, teléfono y cuántos productos le compro a cada uno.
- Escenario 2: Dado que no tengo proveedores, cuando entro, entonces veo un mensaje que lo confirma.

## Estados por vista

- Proveedores: normal, vacío, cargando, error, sin permiso (no aplica: solo el dueño usa la app), muchos datos.

## Reglas

- Un proveedor sin productos se muestra igual, con 0 productos.

## Fuera de alcance

- Agregar o editar proveedores: queda para una épica posterior.

## Enlaces

- Tickets: ninguno todavía. La vista viene del mockup general y se construye cuando haya ticket.
- Vistas: `design/vistas/proveedores/`
