# Spec · Cosechas de la semana

## Contexto

Cada semana los socios de Semilla registran lo que cosechan por parcela. La coordinadora quiere ver el total de la semana y el detalle por cultivo para repartir excedentes.

## Historias

### SEM-40 · Ver cosechas de la semana

Como coordinadora, quiero ver las cosechas de la semana con su cultivo, parcela, kilos y socio, y el total, para repartir excedentes.

- Escenario 1: Dado que hay cosechas, cuando entro a "Cosechas de la semana", entonces veo la tabla y el total en kilos.
- Escenario 2: Dado que no hubo cosechas, cuando entro, entonces veo "Esta semana no se registraron cosechas.".

## Estados por vista

- Cosechas de la semana: normal, vacío, cargando, error, sin permiso, muchos datos.

## Reglas

- El total suma los kilos de todas las cosechas de la semana, con un decimal.

## Decisiones del grilling

| Decisión | Quién | Estado |
| :--- | :--- | :--- |
| Registrar cosecha queda fuera de este spec | Paula Rivas | decidida |

## Fuera de alcance

- Registrar una cosecha.

## Enlaces

- Tickets: ninguno todavía
- Vistas: `design/vistas/cosechas/`
