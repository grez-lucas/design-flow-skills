# Spec · Invitar miembros

## Contexto

Equipo es una app de gestión de equipos. Hoy solo el soporte agrega miembros. Queremos que un administrador invite por correo.

## Historias

### EQ-021 · Invitar por correo

Como administrador, quiero invitar a una persona por correo con un rol, para sumarla sin pedirle a soporte.

- Escenario 1: Dado que abro "Invitar", cuando ingreso un correo válido y elijo rol Miembro, entonces la invitación queda pendiente y la veo en el listado de invitaciones.
- Escenario 2: Dado que el correo ya es miembro, cuando invito, entonces veo un error junto al campo.
- Escenario 3: Dado que llegué al límite de 10 miembros del plan, cuando abro "Invitar", entonces veo el aviso del límite y el acceso a mejorar plan, sin el formulario.

### EQ-022 · Ver invitaciones pendientes

Como administrador, quiero ver las invitaciones pendientes, para reenviarlas o cancelarlas.

- Escenario 1: Dado que hay invitaciones, cuando entro a "Invitaciones", entonces veo correo, rol, fecha de envío y acciones Reenviar y Cancelar.
- Escenario 2: Dado que no hay invitaciones, cuando entro, entonces veo un mensaje y el botón "Invitar".

## Estados por vista

- Invitar (modal): normal, error de correo, límite de plan, enviando.
- Invitaciones: normal, vacío, cargando, error, muchos datos.

## Reglas

- Roles: Admin y Miembro.
- Una invitación vence a los 7 días.

## Fuera de alcance

- Invitación masiva por CSV.

## Enlaces

- Tickets: EQ-021, EQ-022.
