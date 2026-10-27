# Plantilla del spec

Se copia tal cual. Las secciones son las que leen `spec-a-tickets` y `spec-a-html`: una sección vacía se deja con "Ninguno" o "No aplica", no se borra.

## Plantilla

```markdown
# Spec · <nombre del requerimiento>

## Contexto

<qué pasa hoy, a quién le pasa, qué se quiere lograr y cómo se sabe que funcionó>

## Historias

### <ID> · <título corto>

Como <rol>, quiero <capacidad>, para <beneficio>.

- Escenario 1: Dado que <contexto>, cuando <acción>, entonces <resultado>.
- Escenario 2: ...

## Estados por vista

- <Vista>: normal, vacío, cargando, error, sin permiso, muchos datos, <propios del caso>.

## Reglas

- <regla de negocio, límite, cálculo o plazo>

## Decisiones del grilling

| Decisión | Quién | Estado |
| :--- | :--- | :--- |
| <qué se decidió> | <persona> | decidida |
| <qué falta decidir> | <quién decide> | pendiente |

## Fuera de alcance

- <lo que no entra>

## Enlaces

- Tickets: los escribe spec-a-tickets al congelar el spec
- Vistas: `design/vistas/<épica>/`
- Spec anterior: <enlace, si reemplaza a uno>
```

## Reglas de redacción

- Un ID por historia. Si el proyecto tiene formato de ID (por ejemplo en su `.claude/pm-conventions.md`), úsalo; si no, `US-<ÁREA>-NNN` con un código corto de la épica en mayúsculas.
- Una historia es una capacidad. Si la frase lleva "y" entre dos acciones distintas ("reservar y pagar"), son dos historias.
- Cada escenario tiene un resultado que se ve: un mensaje, un dato, una pantalla, un correo. "Funciona bien" no es un resultado.
- En "Estados por vista", si un estado base no aplica, dilo: "sin permiso: no aplica, todos los roles ven esta vista".
- Lo que no se decidió no va como escenario ni como regla: va como pendiente en "Decisiones del grilling".
- Si una decisión fue una recomendación aceptada sin cambios, "Quién" dice "<persona> (recomendación aceptada)".
- Todo pendiente tiene un nombre en "Quién": quien decide o, si no se sabe, quien lo averigua.

## Ejemplo corto

```markdown
# Spec · Recordatorios de facturas vencidas

## Contexto

El administrador de una pyme no sabe qué facturas emitidas están vencidas sin exportar a una planilla, y cobra tarde. Queremos un listado de vencidas y recordatorios automáticos por correo al cliente. Funciona si baja el atraso promedio de cobro.

## Historias

### US-REC-001 · Ver facturas vencidas

Como administrador, quiero ver las facturas emitidas que están vencidas, para cobrar a tiempo.

- Escenario 1: Dado que tengo facturas vencidas, cuando entro a "Vencidas", entonces veo cliente, número, monto, días de atraso y estado del recordatorio, de mayor a menor atraso.
- Escenario 2: Dado que no tengo facturas vencidas, cuando entro, entonces veo un mensaje que lo confirma y un acceso a "Emitir factura".

## Estados por vista

- Vencidas: normal, vacío, cargando, error, sin permiso (rol contador), muchos datos, plan básico.

## Reglas

- Solo administradores configuran recordatorios.

## Decisiones del grilling

| Decisión | Quién | Estado |
| :--- | :--- | :--- |
| El plan Básico ve el listado pero no los recordatorios | Camila (producto) | decidida |
| Si el correo de recordatorio se puede editar | Dueño | pendiente |

## Fuera de alcance

- Pagos en línea.

## Enlaces

- Tickets: los escribe spec-a-tickets al congelar el spec
- Vistas: `design/vistas/recordatorios/`
```
