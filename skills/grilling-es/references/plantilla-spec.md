# Plantilla del spec

Se copia tal cual. Las secciones son las que leen `spec-a-tickets`, `spec-a-html`, `html-a-vista` y `checklist-diseno`: una sección vacía se deja con "Ninguno" o "No aplica", no se borra.

## Plantilla

````markdown
# Spec · <nombre del requerimiento>

## Contexto

<qué pasa hoy, a quién le pasa, qué se quiere lograr y cómo se sabe que funcionó>

## Historias

### <ID> · <título corto>

**COMO** <rol>
**QUIERO** <capacidad>
**PARA** <beneficio>

### Escenario 1: <nombre>

```gherkin
Dado que <contexto>
Cuando <acción>
Entonces <resultado>
Y <resultado adicional>
```

### Escenario 2: <nombre>

...

## Estados por vista

- <Vista>: normal, vacío, cargando, error, sin permiso, muchos datos.

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

## Escenarios en pantalla

| Slug | Nombre | Alcance |
| :--- | :--- | :--- |
| `<slug>` | <nombre de un ### Escenario N de arriba> | <pantalla> |
| `<slug>` | <nombre de un ### Escenario N de arriba> | global |
````

## Reglas de redacción

- Un ID por historia. Si el proyecto tiene formato de ID (por ejemplo en su `.claude/pm-conventions.md` o en las convenciones a las que ese archivo apunta), úsalo; si no, `US-<ÁREA>-NNN` con un código corto de la épica en mayúsculas.
- Una historia es una capacidad. Si la frase lleva "y" entre dos acciones distintas ("reservar y pagar"), son dos historias.
- Los escenarios van después de su historia, numerados desde 1 en cada historia, cada uno con un nombre que no se repite en el spec y su bloque `gherkin` con `Dado`, `Cuando`, `Entonces` y `Y`. `spec-a-tickets` los copia tal cual al ticket.
- Las variantes de un mismo escenario van en uno solo, con `Esquema del escenario` y `Ejemplos`:

  ### Escenario 2: Recordatorio según atraso

  ```gherkin
  Esquema del escenario: Recordatorio según atraso
  Dado que una factura tiene <dias> días de atraso
  Cuando llega la hora del envío
  Entonces el cliente recibe el recordatorio <tipo>

  Ejemplos:
  | dias | tipo |
  | 3 | amable |
  | 15 | firme |
  ```

- Cada escenario tiene un resultado que se ve: un mensaje, un dato, una pantalla, un correo. "Funciona bien" no es un resultado.
- En "Estados por vista", si un estado base no aplica, dilo: "sin permiso: no aplica, todos los roles ven esta vista". Los estados propios del caso (plan vencido, pago rechazado) no van ahí: son escenarios.
- `## Escenarios en pantalla` va siempre, con la tabla aunque sea solo el encabezado; "Ninguno" también vale como tabla vacía. Lista cada escenario con estado visible, uno por fila; el que no cambia la pantalla, como un correo que se envía, no va. El nombre es el de su `### Escenario N`, letra por letra. El alcance es el nombre de la pantalla, o `global` si cambia todas las pantallas, como una conexión caída.
- El slug va en minúsculas, sin tildes y con guiones (`plan-basico`), y es el nombre con que la vista declara el escenario en `data-escenarios` y `data-state`. Un escenario que muestra un estado base usa su slug fijo: `normal`, `vacio`, `cargando`, `error`, `sin-permiso` o `muchos-datos`. Un slug no se repite en la misma pantalla.
- Lo que no se decidió no va como escenario ni como regla: va como pendiente en "Decisiones del grilling".
- Si una decisión fue una recomendación aceptada sin cambios, "Quién" dice "<persona> (recomendación aceptada)".
- Todo pendiente tiene un nombre en "Quién": quien decide o, si no se sabe, quien lo averigua.

## Ejemplo corto

````markdown
# Spec · Recordatorios de facturas vencidas

## Contexto

El administrador de una pyme no sabe qué facturas emitidas están vencidas sin exportar a una planilla, y cobra tarde. Queremos un listado de vencidas y recordatorios automáticos por correo al cliente. Funciona si baja el atraso promedio de cobro.

## Historias

### US-REC-001 · Ver facturas vencidas

**COMO** administrador de la empresa
**QUIERO** ver las facturas emitidas que están vencidas
**PARA** cobrar a tiempo

### Escenario 1: Hay facturas vencidas

```gherkin
Dado que tengo facturas vencidas
Cuando entro a "Vencidas"
Entonces veo cliente, número, monto, días de atraso y estado del recordatorio
Y la lista está ordenada de mayor a menor atraso
```

### Escenario 2: No hay facturas vencidas

```gherkin
Dado que no tengo facturas vencidas
Cuando entro a "Vencidas"
Entonces veo un mensaje que lo confirma
Y veo un acceso a "Emitir factura"
```

### Escenario 3: Plan Básico

```gherkin
Dado que mi plan es Básico
Cuando entro a "Vencidas"
Entonces veo el listado
Y los recordatorios aparecen bloqueados con una invitación a pasar a plan Pro
```

## Estados por vista

- Vencidas: normal, vacío, cargando, error, sin permiso (rol contador), muchos datos.

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

## Escenarios en pantalla

| Slug | Nombre | Alcance |
| :--- | :--- | :--- |
| `normal` | Hay facturas vencidas | Vencidas |
| `vacio` | No hay facturas vencidas | Vencidas |
| `plan-basico` | Plan Básico | Vencidas |
````
