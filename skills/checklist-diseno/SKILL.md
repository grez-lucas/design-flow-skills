---
name: checklist-diseno
description: Revisa las vistas HTML del repositorio de diseño contra la definición de listo antes de la planificación del sprint - escenarios completos (vacío, cargando, error, sin permiso, muchos datos y los del spec), controles de prototipo fuera de la pantalla, valores visuales solo desde tokens.css, datos ficticios, tickets o spec citados - y cruza cada vista con los criterios de aceptación de sus tickets, o con su spec si no tiene tickets. Entrega un informe en el chat con lo que bloquea y lo que conviene mirar. Úsala siempre que producto o diseño quiera saber si un diseño está listo para construir, aunque no diga "checklist" - "revisa si las vistas están listas", "¿esto pasa la definición de listo?", "chequea el diseño antes de la planning", "revisa el HTML de alertas", "¿le falta algo a esta vista?". No la uses para crear o editar vistas (spec-a-html) ni para escribir tickets (spec-a-tickets).
---

# Checklist de diseño

Revisa si las vistas de `design/vistas/` están listas para construir. El resultado es un informe en el chat que producto lleva a la planificación del sprint, donde TL y producto dan el diseño por listo. La skill no aprueba ni bloquea nada por su cuenta: dice qué falta y por qué importa.

Quien la usa suele ser de producto. Habla en español y explica cada hallazgo por lo que DEV no podría construir o construiría mal, no por la regla que incumple.

## Pasos

### 1. Qué revisar

Trabaja en el repositorio de diseño (tiene `design/` en la raíz). Si la persona nombra una épica o una vista, revisa esas; si no, pregunta si revisas todo `design/vistas/` o solo lo que cambió desde la última planificación. Para lo que cambió, `git log` y `git diff` del repositorio de diseño lo muestran.

### 2. Revisión mecánica

Corre el script incluido:

```
python3 <ruta-de-esta-skill>/scripts/revisar.py <repo-de-diseño> [vistas...]
```

Confirma cada BLOQUEA leyendo la línea antes de pasarlo al informe: el script puede equivocarse con SVG, consultas de contenedor o comentarios. Si descartas un hallazgo, dilo en una línea con el motivo.

Si no hay Python en la máquina, revisa a mano, y dilo en el informe. Una vista grande no se lee entera: busca con grep los atributos y los valores. Lo que hay que revisar:

- Que la vista enlace `tokens.css`, `components.css` y `proto.js`, y que no tenga otro JavaScript.
- Que declare los escenarios base (normal, vacio, cargando, error, sin-permiso, muchos-datos) o los marque en `data-no-aplica`, cada uno con su motivo y separados por `;`.
- Que cada `data-state` corresponda a un escenario declarado.
- Que no haya colores ni medidas sueltas ni variables que `tokens.css` no define, en `<style>`, en `style=` ni en atributos de SVG.
- Que no cargue recursos externos, tampoco desde CSS (`@import`, `url()`).
- Que cite sus tickets en `<meta name="tickets">` o, si es una vista sin ticket, su spec en `<meta name="spec">`, con la ruta del spec relativa a la raíz del repositorio (`specs/<épica>/spec.md`). Si trae los dos, mandan los tickets y el spec es contexto. Un `<meta name="spec">` declarado tiene que apuntar a un archivo que existe dentro del repositorio, aunque haya tickets.
- Que no tenga dominios que parezcan reales ni texto de relleno.

### 3. Revisión de criterio

Lo que el script no puede ver, lo revisas tú, vista por vista:

- **Tickets**: lee los tickets que la vista cita (en el tracker o en `specs/<épica>/tickets/`). Cada escenario "Dado, cuando, entonces" tiene que poder verse en algún escenario de la vista. Un criterio que la vista no muestra es lo primero que DEV va a preguntar. Una vista que cita solo `<meta name="spec">` no tiene tickets: no la marques por eso, crúzala contra el spec.
- **Spec**: compara los escenarios de la vista con "Estados por vista" del spec. Uno que el spec pide y la vista no tiene bloquea. En una vista con solo spec, este cruce reemplaza al de tickets: además de "Estados por vista", cada historia y cada regla del spec que toque la vista tiene que poder verse en algún escenario.
- **Escenarios que se ven iguales**: abre cada escenario mentalmente (o en el navegador si la sesión puede, con `?escenario=<nombre>`): vacío, error y sin permiso tienen que decir qué pasa y qué puede hacer el usuario, no mostrar una pantalla en blanco.
- **Controles de prototipo**: busca selectores, pestañas o botones dentro de la pantalla que solo sirven para cambiar de caso ("plan vigente / plan expirado"). DEV no distingue andamio de producto. El script solo detecta los que tienen un manejador `on...` o un enlace a `?escenario=`; los demás los ves tú.
- **Lo que sobra**: un escenario, una columna o una acción que ni el spec ni los tickets piden; en una vista con solo spec, lo que el spec no pide. Si implica comportamiento nuevo, bloquea, porque DEV lo construiría sin criterio de aceptación; si es cosmético, va en "Conviene mirar".
- **No aplica**: cada motivo de `data-no-aplica` tiene que coincidir con el spec o ser evidente. Un escenario base marcado como no aplica que el spec no menciona se pregunta en la planificación.
- **Textos**: completos y en el idioma del producto. Un texto genérico ("Mensaje de error") obliga a DEV a inventarlo.
- **Interacciones**: lo que pasa al hacer clic, validar o esperar, como comentario junto al elemento cuando no es obvio.
- **Datos**: verosímiles y de volumen real en muchos datos (nombres largos, montos grandes, decenas de filas).

### 4. Informe

Entrega el informe en el chat, en este orden:

```
## Resultado

<N> vistas revisadas: <M> listas (con o sin avisos), <K> con bloqueos.

## <ruta de la vista> · <tickets, o Spec: <ruta> si la vista no cita tickets>

Bloquea:
- <qué falta> - <qué no podría construir DEV sin esto>

Conviene mirar:
- <aviso>

Lista.   (cuando no tiene hallazgos)

## Archivos compartidos

<hallazgos de tokens.css, components.css y proto.js, si hay>

## Siguiente paso

<qué corregir con spec-a-html antes de la planificación, o "listo para llevar a la planificación">
```

Bloquea lo que impide construir sin preguntar: un escenario del spec o un criterio de un ticket que no se ve, valores visuales sueltos o variables sin definir, controles de prototipo dentro de la pantalla, una vista que no cita tickets ni spec o declara un spec que no existe o está fuera del repositorio, aunque cite tickets, recursos externos, texto de relleno, y dominios o marcas que confirmaste que son reales (el script los marca como aviso porque no puede saberlo; tú sí, mirando si el nombre existe fuera del ejemplo). Lo demás va en "Conviene mirar".

No corrijas las vistas: el informe es para decidir en la planificación. Si la persona quiere corregir, el siguiente paso es `spec-a-html` en modo edición, con la lista de hallazgos.
