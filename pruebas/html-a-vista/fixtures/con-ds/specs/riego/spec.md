# Spec · Panel de riego

## Contexto

Los socios de Semilla riegan el huerto con un sistema automático por zonas y sensores de humedad. Hoy no saben si un sensor dejó de enviar datos o si el tanque se vació hasta que una zona se seca. Queremos un panel con la humedad de cada zona, el próximo riego, el historial y la opción de regar a mano.

## Historias

### SEM-20 · Ver el estado del riego

Como socio de turno, quiero ver la humedad y el próximo riego de cada zona, para saber si hay que intervenir.

- Escenario 1: Dado que los sensores envían datos, cuando entro al panel, entonces veo cada zona con su humedad y su próximo riego.
- Escenario 2: Dado que un sensor no envía datos hace más de una hora, cuando entro, entonces veo un aviso con la zona y desde cuándo.
- Escenario 3: Dado que el tanque está vacío, cuando entro, entonces veo que el riego automático quedó en pausa.

### SEM-21 · Regar una zona a mano

Como socio de turno, quiero regar una zona ahora por los minutos que elija, para corregir una zona seca.

- Escenario 1: Dado que elijo una duración entre 5 y 60 minutos, cuando inicio el riego, entonces el riego empieza.
- Escenario 2: Dado que elijo una duración fuera de ese rango, cuando inicio, entonces veo "La duración tiene que estar entre 5 y 60 minutos.".

### SEM-22 · Historial de riego

Como coordinadora, quiero ver los riegos de los últimos días, para saber cuánta agua usa cada zona.

- Escenario 1: Dado que hubo riegos, cuando abro el historial, entonces veo fecha, zona, duración y origen (programado o manual, con el socio).

## Estados por vista

- Panel de riego: normal, vacío (sin zonas configuradas), cargando, error, sin permiso, muchos datos, sensor sin señal, tanque vacío.
- Historial de riego: normal, vacío, cargando, error, sin permiso, muchos datos.

## Reglas

- El nivel del tanque se muestra como lleno, a la mitad o sin agua.

## Decisiones del grilling

| Decisión | Quién | Estado |
| :--- | :--- | :--- |
| El riego manual dura entre 5 y 60 minutos | Bruno Lagos | decidida |

## Fuera de alcance

- Programar riegos.

## Enlaces

- Tickets: ninguno todavía
- Vistas: `design/vistas/riego/`
