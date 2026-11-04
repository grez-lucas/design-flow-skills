# Pedidos

Spec mínimo de la prueba: una lista de pedidos que abre un modal para anular uno.

### Escenario 1: Anular un pedido

```gherkin
Dado un pedido en la lista
Cuando la persona elige anularlo
Entonces ve un modal que pide confirmar la anulación
```

## Escenarios en pantalla

| Slug | Nombre | Alcance |
| :--- | :--- | :--- |
| `anular` | Anular un pedido | lista |
