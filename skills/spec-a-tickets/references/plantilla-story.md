# Plantilla de story

Plantilla por defecto cuando el proyecto no tiene `.claude/pm-conventions.md`. Se copia tal cual: los encabezados, los emojis y el orden son los que DEV espera encontrar.

## Plantilla

```markdown
## 📝 Description

Como <rol>, quiero <capacidad>, para <beneficio>.

<párrafo de contexto que explica el comportamiento, tomado del spec>

## ✅ Acceptance Criteria

- [ ] **Escenario 1: <nombre>**

> **Dado** que <contexto>
> **Cuando** <acción>
> **Entonces** <resultado>
> **Y** <resultado adicional>

## 🧪 Testing Requirements (TDD)

- [ ] **Pruebas E2E (flujo principal):**
  - <flujo de punta a punta, uno por escenario relevante>
- [ ] **Pruebas unitarias:** lo completa DEV.
- [ ] **Pruebas de integración:** lo completa DEV.
- [ ] **Cobertura de edge cases:** según la tabla.

## 🎨 Designs & Mockups

* Vista: `design/vistas/<épica>/<vista>.html` (pendiente)
* Key Screens: <vistas y estados que cubre este ticket>

## 🧠 Additional Notes & Considerations

### 🔗 Dependencies

* <identificadores reales de los tickets de los que depende, o "ninguna">

### 🧰 Technical Notes

* Lo completa DEV.

### ⚠️ Edge Cases

| Escenario | Comportamiento Esperado |
| -- | -- |
| <caso> | <esperado> |

### ❓ Open Questions

- [ ] <pregunta sin responder, con quién la responde si se sabe>
```

## Ejemplo

Título: `[US-REC-001] Ver facturas vencidas`

```markdown
## 📝 Description

Como administrador de la empresa, quiero ver las facturas emitidas que están vencidas, para cobrar a tiempo.

Hoy el administrador solo sabe qué facturas están vencidas exportando a una planilla. La vista "Vencidas" las muestra ordenadas por días de atraso, con el estado del recordatorio de cada una.

## ✅ Acceptance Criteria

- [ ] **Escenario 1: Hay facturas vencidas**

> **Dado** que tengo facturas vencidas
> **Cuando** entro a "Vencidas"
> **Entonces** veo cliente, número, monto, días de atraso y estado del recordatorio
> **Y** la lista está ordenada de mayor a menor atraso

- [ ] **Escenario 2: No hay facturas vencidas**

> **Dado** que no tengo facturas vencidas
> **Cuando** entro a "Vencidas"
> **Entonces** veo un mensaje que lo confirma
> **Y** veo un acceso a "Emitir factura"

- [ ] **Escenario 3: Plan Básico**

> **Dado** que mi plan es Básico
> **Cuando** entro a "Vencidas"
> **Entonces** veo el listado
> **Y** los recordatorios aparecen bloqueados con una invitación a pasar a plan Pro

## 🧪 Testing Requirements (TDD)

- [ ] **Pruebas E2E (flujo principal):**
  - Con tres facturas vencidas de distinto atraso, el listado las muestra de mayor a menor atraso con sus cinco datos.
  - Sin facturas vencidas, se ve el mensaje y el acceso a "Emitir factura".
  - Con plan Básico, el listado se ve y los recordatorios aparecen bloqueados.
- [ ] **Pruebas unitarias:** lo completa DEV.
- [ ] **Pruebas de integración:** lo completa DEV.
- [ ] **Cobertura de edge cases:** según la tabla.

## 🎨 Designs & Mockups

* Vista: `design/vistas/recordatorios/vencidas.html` (pendiente)
* Key Screens: Vencidas en normal, vacío, plan Básico y muchos datos

## 🧠 Additional Notes & Considerations

### 🔗 Dependencies

* Ninguna

### 🧰 Technical Notes

* Lo completa DEV.

### ⚠️ Edge Cases

| Escenario | Comportamiento Esperado |
| -- | -- |
| Usuario con rol contador sin acceso a cobranza | Ve el mensaje de falta de permiso, no el listado |
| Monto con decimales | Se muestra en pesos chilenos sin decimales |

### ❓ Open Questions

- [ ] ¿Cuántas facturas se muestran por página cuando hay muchas? Lo decide producto.
```

## Archivo markdown sin tracker

Cuando no hay tracker, cada ticket es un archivo `specs/<épica>/tickets/NN-<titulo-corto>.md`, numerado desde `01` en orden de dependencias. Abre con el título como encabezado y dos líneas que un tracker llevaría como campos:

```markdown
# [US-REC-001] Ver facturas vencidas

**Depende de:** ninguno
**Estado:** borrador

<cuerpo de la plantilla>
```

Estados: `borrador` hasta que la persona aprueba, `listo` cuando se aprueba, `construido` cuando DEV lo termina. No hay campo de aprobación.
