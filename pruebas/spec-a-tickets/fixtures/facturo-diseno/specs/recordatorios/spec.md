# Spec · Recordatorios de facturas vencidas

## Contexto

Facturo es un SaaS de facturación para pymes. Hoy el usuario no sabe qué facturas emitidas están vencidas sin exportar a Excel. Queremos un listado de vencidas y recordatorios automáticos por correo al cliente.

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
Y las facturas están ordenadas por días de atraso
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

### US-REC-002 · Configurar recordatorio

**COMO** administrador
**QUIERO** configurar cuándo se envía el recordatorio
**PARA** no escribir correos a mano

### Escenario 1: Guardar los días de envío

```gherkin
Dado que estoy en la configuración
Cuando elijo enviar a los 3, 7 y 15 días de atraso
Y guardo
Entonces veo una confirmación
```

### Escenario 2: Asunto vacío

```gherkin
Dado que dejo el asunto vacío
Cuando guardo
Entonces veo el error junto al campo
```

## Estados por vista

- Vencidas: normal, vacío, cargando, error, sin permiso (rol contador sin acceso a cobranza), muchos datos.
- Configurar recordatorio: normal.

## Reglas

- Solo administradores configuran recordatorios.
- Montos en pesos chilenos, sin decimales.

## Fuera de alcance

- Pagos en línea.

## Enlaces

- Tickets: US-REC-001, US-REC-002.

## Escenarios en pantalla

| Slug | Nombre | Alcance |
| :--- | :--- | :--- |
| `normal` | Hay facturas vencidas | Vencidas |
| `vacio` | No hay facturas vencidas | Vencidas |
| `plan-basico` | Plan Básico | Vencidas |
| `guardado` | Guardar los días de envío | Configurar recordatorio |
| `asunto-vacio` | Asunto vacío | Configurar recordatorio |
