> Congelado el 2026-10-20: los tickets US-REC-001 y US-REC-002 mandan.

# Spec · Recordatorios de facturas vencidas

## Contexto

Facturo es un SaaS de facturación para pymes. Hoy el usuario no sabe qué facturas emitidas están vencidas sin exportar a Excel. Queremos un listado de vencidas y recordatorios automáticos por correo al cliente.

## Historias

### US-REC-001 · Ver facturas vencidas

Como administrador de la empresa, quiero ver las facturas emitidas que están vencidas, para cobrar a tiempo.

- Escenario 1: Dado que tengo facturas vencidas, cuando entro a "Vencidas", entonces veo cliente, número, monto, días de atraso y estado del recordatorio, ordenadas por días de atraso.
- Escenario 2: Dado que no tengo facturas vencidas, cuando entro, entonces veo un mensaje que lo confirma y un acceso a "Emitir factura".
- Escenario 3: Dado que mi plan es Básico, cuando entro, entonces veo el listado pero los recordatorios aparecen bloqueados con una invitación a pasar a plan Pro.

### US-REC-002 · Configurar recordatorio

Como administrador, quiero configurar cuándo se envía el recordatorio, para no escribir correos a mano.

- Escenario 1: Dado que estoy en la configuración, cuando elijo enviar a los 3, 7 y 15 días de atraso y guardo, entonces veo una confirmación.
- Escenario 2: Dado que dejo el asunto vacío, cuando guardo, entonces veo el error junto al campo.

## Estados por vista

- Vencidas: normal, vacío, cargando, error, sin permiso (rol contador sin acceso a cobranza), muchos datos, plan-basico.
- Configurar recordatorio: normal, guardado, error de validación.

## Reglas

- Solo administradores configuran recordatorios.
- Montos en pesos chilenos, sin decimales.

## Fuera de alcance

- Pagos en línea.

## Enlaces

- Tickets: US-REC-001, US-REC-002.
