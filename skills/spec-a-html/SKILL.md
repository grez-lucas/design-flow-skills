---
name: spec-a-html
description: Toma un spec de producto con historias de usuario y genera el HTML de cada vista o flujo, la fuente de verdad visual que DEV construye, sobre un design system liviano (design/tokens.css y design/components.css) que busca en el repositorio de diseño o crea si no existe. También edita una vista existente cuando cambia el diseño. Úsala siempre que alguien de producto o diseño quiera pasar un spec, una épica o unas historias a pantallas, mockups, prototipos o HTML, aunque no diga "HTML" - "arma las pantallas de este spec", "haz el mockup de la épica de alertas", "dibuja la vista de listado", "genera el diseño de este flujo", "cambia el botón de la vista de pagos", "crea el design system del producto". No la uses para escribir tickets (spec-a-tickets), para hacer el grilling de un requerimiento (grilling-es) ni para revisar un HTML contra la definición de listo (checklist-diseno).
---

# Spec a HTML

Convierte un spec en el HTML de sus vistas, sobre el design system del producto. El HTML es una especificación de pantalla y estados para DEV, no un oráculo de píxel: lo que importa es que muestre todas las vistas y todos los estados que el spec pide, con los valores visuales del design system y nada inventado por fuera.

Quien usa esta skill suele ser de producto o de diseño, no de desarrollo. Habla en español, sin jerga de git ni de CSS salvo que la persona la use primero, y explica cada decisión en términos de lo que se ve en pantalla.

Todo vive en el repositorio de diseño del producto, separado del repositorio de código:

```
design/
  tokens.css        design system: variables CSS
  components.css    componentes compartidos, solo con variables de tokens.css
  proto.js          cambia escenarios y anchos; lo copia esta skill
  vistas/<épica>/<vista>.html
specs/<épica>/spec.md   cuando el proyecto no tiene tracker
```

## Por qué el formato es liviano

Los agentes leen estos archivos en cada tarea, y un mockup autocontenido de los de antes cuesta entre 50 y 160 mil tokens y redefine sus propios colores en cada pantalla. Por eso cada vista enlaza `tokens.css`, `components.css` y `proto.js` en vez de copiar estilos, y cada estado se escribe una sola vez. Si te ves escribiendo el mismo bloque de estilos en dos vistas, es un componente: va a `components.css`.

## Pasos

### 1. Conseguir el spec

El spec es la entrada obligatoria. Llega de una de dos formas:

- Un enlace al tracker (Linear, GitHub, GitLab u otro). Léelo con la herramienta que tenga la sesión para ese tracker.
- Un archivo adjunto o pegado en el chat, o `specs/<épica>/spec.md` en el repositorio.

Si la sesión no tiene herramienta para leer el enlace, pide que peguen o adjunten el spec. Sin spec no avances: un HTML sin spec es exactamente el boceto incompleto que este flujo quiere evitar. Pide el spec en vez de inventar el requerimiento.

El spec sigue una plantilla con contexto, historias "Como, quiero, para" con criterios "Dado, cuando, entonces", estados por vista, reglas, decisiones, fuera de alcance y enlaces a los tickets. Si falta la sección de estados por vista, dedúcelos de las historias y los criterios, y muéstraselos a la persona para que confirme antes de dibujar. Anota los identificadores de los tickets: cada vista los cita.

### 2. Ubicar el repositorio de diseño

Trabaja en el repositorio de diseño, que tiene `design/` o `specs/` en la raíz. Si el directorio actual no lo es, pregunta dónde está. Si el producto todavía no tiene repositorio de diseño, para y pide que el TL lo cree: no lo crees tú, porque el TL decide el host y los accesos.

### 3. Crear o editar

Si la vista ya existe en `design/vistas/<épica>/`, es una edición. Antes de tocarla pregunta qué cambia y por qué:

- Si cambia comportamiento, estados, flujo o alcance, el cambio necesita grilling y tickets actualizados antes que el HTML. Dilo, sugiere `grilling-es` y `spec-a-tickets`, y no edites hasta que el spec o los tickets reflejen el cambio. Un HTML que se adelanta a sus tickets vuelve a abrir la brecha entre lo que se aceptó y lo que se dibujó.
- Si es cosmético (color, texto, espaciado, orden visual sin cambio de comportamiento), sigue, y guarda el por qué para el mensaje del commit. Si el texto o el valor que cambia figura en un criterio de aceptación de un ticket, el ticket manda: se actualiza primero, y recién después la vista.

### 4. Design system

Busca el design system en este orden y para en el primero que exista:

1. `design/tokens.css` en el repositorio de diseño. Si está, úsalo tal cual; no agregues tokens sin preguntar.
2. El código del producto, si está en la máquina. Extrae los valores siguiendo `references/design-system.md`, sección "Extraer del código".
3. Una marca, una guía o un mockup que entregue producto o diseño. Extrae los valores de ahí.
4. Desde cero, con la plantilla `assets/tokens.css`.

Antes de crear o cambiar `tokens.css`, muestra la propuesta (colores con su uso, tipografía, escala de espacios) y pide confirmación. Un cambio en el design system afecta a todas las vistas y lo revisa diseño en la planificación; dilo cuando ocurra.

Si `design/components.css` o `design/proto.js` no existen, créalos desde `assets/components.css` y `assets/proto.js`. `proto.js` se copia sin modificar.

La convención de nombres y las reglas de los tokens están en `references/design-system.md`. Léela antes de escribir o extender `tokens.css` o `components.css`.

### 5. Plan de vistas

Antes de escribir HTML, propone la lista de vistas con sus escenarios, en una tabla corta:

| Vista | Archivo | Escenarios | Tickets |
| :--- | :--- | :--- | :--- |
| Listado de alertas | `design/vistas/alertas/listado.html` | normal, vacio, cargando, error, sin-permiso, muchos-datos | US-ALERT-002 |

Todas las vistas llevan los escenarios base: normal, vacío, cargando, error, sin permiso y muchos datos, más los propios del caso que pida el spec (por ejemplo, plan expirado). Si un escenario base no aplica a una vista, dilo en la tabla en vez de omitirlo en silencio. Espera la confirmación de la persona.

### 6. Escribir el HTML

Sigue `references/vista-html.md`, que trae la plantilla y las reglas. Lo esencial:

- Un archivo por vista o flujo, que enlaza `../../tokens.css`, `../../components.css` y `../../proto.js`.
- Cada valor visual sale de una variable de `tokens.css`. Sin colores, tamaños ni sombras sueltos.
- Los escenarios se declaran en `<body data-escenarios="...">` y cada bloque que depende del escenario lleva `data-state`. Nunca metas controles de prototipo dentro de la pantalla: el panel lo arma `proto.js` fuera del frame, para que DEV no confunda andamio con producto.
- Datos ficticios y verosímiles, sin nombres, dominios ni marcas de clientes reales.
- La vista cita sus tickets en `<meta name="tickets">`.

### 7. Revisión con la persona

Si la sesión tiene terminal y `npx` disponible, abre la vista con Lavish para que la persona anote sobre la pantalla:

```
npx -y lavish-axi design/vistas/<épica>/<vista>.html
npx -y lavish-axi poll design/vistas/<épica>/<vista>.html
```

Aplica cada anotación y vuelve a esperar con `poll --agent-reply "<qué cambiaste>"` hasta que la persona cierre la revisión. Recuérdale que el panel de escenarios permite ver cada estado y cada ancho.

Sin terminal, indica la ruta del archivo para abrirlo en el navegador, y cómo ver un escenario: `listado.html?escenario=vacio`.

### 8. Guardar

Cuando la persona dé el visto bueno, haz commit y push a `main` del repositorio de diseño. El historial de commits reemplaza la revisión: el mensaje dice qué vista cambió, qué tickets cubre y, en una edición, por qué.

```
diseno(alertas): listado con estados vacío, error y muchos datos

Tickets: US-ALERT-002
```

Muestra el resumen de archivos antes de hacer push y pide la confirmación. Si el push falla por permisos, explica el error en simple y que el TL es quien da los accesos.

### 9. Siguiente paso

Cierra diciendo qué quedó (vistas, escenarios, si cambió el design system) y que antes de la planificación del sprint conviene correr `checklist-diseno` sobre las vistas nuevas. Si el design system cambió, avisa que diseño lo revisa en la planificación.
