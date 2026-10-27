# Spec · Reservas de parcelas

## Contexto

En Semilla, la coordinadora de un huerto comunitario asigna parcelas a socios por temporada. Hoy lo lleva en una planilla y no ve de un vistazo qué reservas están pendientes de confirmar. Queremos una lista de reservas con su estado. Funciona si las reservas pendientes se confirman en menos de una semana.

## Historias

### SEM-11 · Ver reservas de parcelas

Como coordinadora del huerto, quiero ver las reservas de parcelas con su estado, para confirmar las pendientes a tiempo.

- Escenario 1: Dado que hay reservas, cuando entro a "Reservas de parcelas", entonces veo socio, parcela, fecha de inicio y estado (confirmada, pendiente o cancelada).
- Escenario 2: Dado que elijo un estado en los filtros, cuando lo aplico, entonces veo solo las reservas de ese estado; "Todas" muestra todas.
- Escenario 3: Dado que no hay reservas del estado elegido, cuando filtro, entonces veo "No hay reservas con este estado.".

## Estados por vista

- Reservas: normal, vacío (sin reservas en la temporada), cargando, error, sin permiso (socio sin rol de coordinación), muchos datos.

## Reglas

- Las reservas pendientes se destacan para que se vean primero al recorrer la lista.

## Decisiones del grilling

| Decisión | Quién | Estado |
| :--- | :--- | :--- |
| La lista se ordena por fecha de inicio | Paula Rivas | decidida |
| Color propio para el estado pendiente | Paula Rivas | pendiente |

## Fuera de alcance

- Crear o editar una reserva.

## Enlaces

- Tickets: `specs/reservas/tickets/01-ver-reservas.md` (SEM-11)
- Vistas: `design/vistas/reservas/`
