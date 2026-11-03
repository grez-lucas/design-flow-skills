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
  proto.js          cambia escenarios, anchos y tema; lo copia esta skill
  fuentes/          la fuente del producto en .woff2, si tiene una propia
  vistas/<épica>/<vista>.html
specs/<épica>/spec.md   cuando el proyecto no tiene tracker
.gitignore          con `.lavish/`, donde Lavish guarda sus archivos de revisión
```

## Intérprete de Python

Al empezar, una sola vez, busca el intérprete: prueba `python3`, `python` y `py -3`, en ese orden, con `<intérprete> -c "import sys; assert sys.version_info >= (3, 9)"`, y usa el primero que sale sin error como `<intérprete>` en cada orden de esta skill y de sus `references/`, siempre con `-B`, para que Python no deje `__pycache__/` en la carpeta de la skill. Si ninguno pasa la prueba, no corras ninguna orden con Python y sigue lo que esta skill dice para cuando no encontraste intérprete.

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

Con el repositorio ubicado, antes de escribir en él, decide la rama: el paso 9 guarda en la rama actual, y cambiar de rama con archivos sin guardar puede fallar. Corre, con la ruta absoluta de esta skill en lugar de `<ruta-de-esta-skill>` y desde el repositorio de diseño:

```
<intérprete> -B <ruta-de-esta-skill>/scripts/rama.py revisar --tipo diseno --epica <épica>
```

Si no encontraste intérprete, para y no guardes: explica en simple que falta Python 3.9 o superior y que se instala desde https://www.python.org/downloads/. Si `rama.py` sale con error o no devuelve un JSON, aquí o tras un rechazo, para y no guardes: explica el error en simple; si dice que el nombre termina en guion y número, pide a la persona otro, por ejemplo `fase-dos` en lugar de `fase-2`, y vuelve a correrlo. El script trae lo nuevo del servidor, no cambia de rama y devuelve un JSON con una `accion`:

- `guardar`: guarda en la rama actual.
- `volver`: la rama ya no está en el servidor, por ejemplo porque el TL hizo el merge y la borró, y lo que tenía ya está en la principal. Corre `git switch <principal>`, con la `principal` del JSON, y `git pull --ff-only`, y guarda ahí. Si uno falla, para y explica en qué rama quedaste.
- `parar`: no escribas en el repositorio. Explica en simple el `detalle`, en qué rama estás y que el TL dice cómo seguir.

### 3. Crear o editar

Si la vista ya existe en `design/vistas/<épica>/`, es una edición. Antes de tocarla pregunta qué cambia y por qué:

- Si cambia comportamiento, estados, flujo o alcance, el cambio necesita grilling y tickets actualizados antes que el HTML. Dilo, sugiere `grilling-es` y `spec-a-tickets`, y no edites hasta que el spec o los tickets reflejen el cambio. Un HTML que se adelanta a sus tickets vuelve a abrir la brecha entre lo que se aceptó y lo que se dibujó.
- Si es cosmético (color, texto, espaciado, orden visual sin cambio de comportamiento), sigue, y guarda el por qué para el mensaje del commit. Si el texto o el valor que cambia figura en un criterio de aceptación de un ticket, el ticket manda: se actualiza primero, y recién después la vista.

### 4. Design system

Busca el design system en este orden y para en el primero que exista:

1. `design/tokens.css` en el repositorio de diseño. Si está, úsalo tal cual; no agregues tokens sin preguntar.
2. El código del producto, si está en la máquina. Extrae los valores de la parte del producto que se diseña, siguiendo `references/design-system.md`, sección "Extraer del código".
3. Una marca, una guía o un mockup que entregue producto o diseño. Extrae los valores de ahí.
4. Desde cero, con la plantilla `assets/tokens.css`.

Antes de crear o cambiar `tokens.css`, muestra la propuesta (colores con su uso, tipografía, escala de espacios) y pide confirmación. Un cambio en el design system afecta a todas las vistas y lo revisa diseño en la planificación; dilo cuando ocurra.

Si `design/components.css` o `design/proto.js` no existen, créalos desde `assets/components.css` y `assets/proto.js`. `proto.js` se copia sin modificar.

Si `design/` ya existía, compara sus compartidos con los de esta skill: un repositorio creado con una versión anterior no tiene las reglas, los tokens ni el `proto.js` nuevos, y una vista que los usa (un modal, un aviso) sale sin estilo y `checklist-diseno` la bloquea.

```
<intérprete> -B <ruta-de-esta-skill>/scripts/compartidos.py comparar <repo-de-diseño>
```

Si el JSON trae `"cambios": true`, muestra el cambio antes de escribirlo, con `<intérprete> -B <ruta-de-esta-skill>/scripts/compartidos.py mostrar <repo-de-diseño>`, y explícalo en simple: qué reglas y tokens se suman (`faltan`), cuáles quedan fuera y por qué (`omitidos`) y, si `proto.js` difiere, que se reemplaza por el de la skill. Nombra una por una las reglas de `cambian_lo_propio`: no tienen clase, pintan elementos que ya existen y cambian cómo se ven las vistas que el repositorio ya tiene. El resto solo pinta las clases nuevas. Escribe solo con el sí de la persona, con `<intérprete> -B <ruta-de-esta-skill>/scripts/compartidos.py aplicar <repo-de-diseño>`. Sin el sí, sigue con lo que hay y avisa que las vistas que usen lo que falta se verán sin estilo y `checklist-diseno` las bloqueará. Si el script sale con error, explícalo en simple y sigue sin tocar los compartidos.

Revisa también que el `.gitignore` de la raíz del repositorio de diseño tenga la línea `.lavish/`; si no la tiene, agrégala, y crea el archivo si falta. Lavish guarda ahí los archivos de cada revisión, que no son diseño: sin esa línea, producto los ve como cambios sin guardar después de cada commit.

La convención de nombres y las reglas de los tokens están en `references/design-system.md`. Léela antes de escribir o extender `tokens.css` o `components.css`.

### 5. Plan de vistas

Antes de escribir HTML, propone la lista de vistas con sus escenarios, en una tabla corta:

| Vista | Archivo | Escenarios | Tickets |
| :--- | :--- | :--- | :--- |
| Listado de alertas | `design/vistas/alertas/listado.html` | normal, vacio, cargando, error, sin-permiso, muchos-datos | US-ALERT-002 |

Todas las vistas llevan los escenarios base: normal, vacío, cargando, error, sin permiso y muchos datos, más los propios del caso que pida el spec (por ejemplo, plan expirado). Si un escenario base no aplica a una vista, dilo en la tabla y déjalo escrito en la vista con `data-no-aplica` (ver `references/vista-html.md`), en vez de omitirlo en silencio.

Para elegir los escenarios propios de cada vista, toma de `## Escenarios en pantalla` del spec las filas cuyo alcance es esa pantalla o `global`, y escribe sus slugs igual. `checklist-diseno` cruza los slugs con la tabla, no el alcance. Un estado que la vista necesita y la tabla no tiene no lleva un slug inventado: es una decisión de producto, que se pregunta y entra al spec con `grilling-es`. Si el spec no tiene la tabla, nombra los propios en minúsculas y con guiones, y `checklist-diseno` lo avisa sin bloquear.

Espera la confirmación de la persona.

### 6. Escribir el HTML

Sigue `references/vista-html.md`, que trae la plantilla y las reglas. Lo esencial:

- Un archivo por vista o flujo, que enlaza `../../tokens.css`, `../../components.css` y `../../proto.js`.
- Cada valor visual sale de una variable de `tokens.css`. Sin colores, tamaños ni sombras sueltos.
- Los escenarios se declaran en `<body data-escenarios="...">` y cada bloque que depende del escenario lleva `data-state`. Nunca metas controles de prototipo dentro de la pantalla: el panel lo arma `proto.js` fuera del frame, para que DEV no confunda andamio con producto.
- Datos ficticios y verosímiles, sin nombres, dominios ni marcas de clientes reales.
- La vista cita sus tickets en `<meta name="tickets">`.

### 7. Capturas

`revisar.py` de `checklist-diseno` no ve lo que se ve mal: un modal que no se achica en móvil, un texto que contradice a otro en el mismo escenario. Una captura sí. Con navegador en la sesión (Google Chrome o Chromium, o Playwright), las capturas son obligatorias antes de mostrarle la vista a la persona. Para saber si hay navegador: `command -v google-chrome chromium chromium-browser`, o `<intérprete> -B -c "import playwright"` para Playwright.

Saca una por escenario y por ancho de referencia (los del comentario de `tokens.css`, por defecto 390, 1280 y 1440) en una carpeta de trabajo fuera del repositorio, por ejemplo la que da `mktemp -d`, para que no entren al commit:

```
google-chrome --headless=new --disable-gpu --window-size=<ancho>,900 --screenshot=<trabajo>/<vista>-<escenario>-<ancho>.png "file://<ruta-absoluta-del-repo>/design/vistas/<épica>/<vista>.html?escenario=<escenario>&proto=0"
```

El binario puede llamarse `chromium` o `chromium-browser`. `proto=0` saca el panel de la captura. Chrome captura solo lo que entra en la ventana. Si la vista es más larga que la ventana (muchos datos, un formulario largo, el pie de un modal), repite la captura con `--window-size=<ancho>,3000`. Con Playwright, la misma URL con `page.set_viewport_size({"width": <ancho>, "height": 900})`, `page.goto(...)` y `page.screenshot(path=..., full_page=True)`, que ya sale entera.

Si `tokens.css` define `[data-theme="dark"]`, repite cada escenario en un ancho con `&tema=oscuro`. Un producto solo oscuro no lo necesita: su tema base ya es el oscuro.

Mira cada captura y revísala contra el spec: que cada escenario muestre lo que piden "Estados por vista" y los criterios, que nada se corte, se superponga ni se salga de la pantalla en 390, que los textos de un mismo escenario no se contradigan, y que no aparezcan datos o textos que el spec no menciona. Corrige y vuelve a capturar lo que cambió. Si corregiste `components.css` o `tokens.css`, vuelve a capturar todas las vistas del pedido, porque el cambio las toca a todas. Al pasar a la revisión, dile a la persona cuántas capturas revisaste y qué corregiste.

Sin navegador en la sesión, dilo en una línea, que la revisión visual queda en manos de la persona en el paso siguiente, y sigue.

### 8. Revisión con la persona

Si la sesión tiene terminal y `npx` disponible, abre la vista con Lavish para que la persona anote sobre la pantalla:

```
npx -y lavish-axi design/vistas/<épica>/<vista>.html
npx -y lavish-axi poll design/vistas/<épica>/<vista>.html
```

Aplica cada anotación y vuelve a esperar con `poll --agent-reply "<qué cambiaste>"` hasta que la persona cierre la revisión. Recuérdale que el panel de escenarios permite ver cada estado y cada ancho.

Sin terminal, indica la ruta del archivo para abrirlo en el navegador, y cómo ver un escenario: `listado.html?escenario=vacio`.

### 9. Guardar

Cuando la persona dé el visto bueno, haz commit y push a la rama actual del repositorio de diseño, con el mensaje `diseno(<épica>): <resumen>`. El historial de commits reemplaza la revisión: el mensaje dice qué vista cambió, qué tickets cubre y, en una edición, por qué.

```
diseno(alertas): listado con estados vacío, error y muchos datos

Tickets: US-ALERT-002
```

Agrega solo lo que está bajo `design/` y `specs/`: `git add design/`, `git add specs/<épica>/` si tocaste algo ahí, y `git add .gitignore` si le agregaste `.lavish/`; nunca `git add -A` ni `git add .`: si las skills se instalaron en el proyecto con `npx skills`, `.agents/`, `.claude/skills/` y `skills-lock.json` quedan sin seguimiento y no van en el commit.

Muestra el resumen de archivos antes de hacer push, solo con los que entran en el commit, y pide la confirmación.

La rama quedó revisada en el paso 2. El push va a la rama actual, con `git push`. Si falla por credenciales, porque el servidor no reconoce el usuario o el token, explica el error en simple y que el TL es quien da los accesos. Si lo rechaza por cualquier motivo que no sea de credenciales (la rama está protegida, o tiene cambios que tu copia no tiene), no lo arregles en esa rama, sin `git pull --rebase`, `git reset --hard` ni `--force`: el TL resuelve en el merge request. Pide la rama nueva, desde el repositorio de diseño, con `<intérprete> -B <ruta-de-esta-skill>/scripts/rama.py rechazo --tipo diseno --epica <épica>`.

- `rama-nueva`: pasa el commit con `git switch -c <rama_nueva>` y empújalo con `git push -u origin <rama_nueva>`; deja la `rama` de la que saliste como está en el servidor con `git branch -f <rama> origin/<rama>`. Explica en simple que el servidor no aceptó el cambio en esa rama, que las vistas quedaron en la rama nueva y que el TL revisa y hace el merge request.
- `parar`: explica en simple el `detalle` y que el TL es quien da los accesos.

### 10. Siguiente paso

Cierra diciendo qué quedó (vistas, escenarios, si cambió el design system) y que antes de la planificación del sprint conviene correr `checklist-diseno` sobre las vistas nuevas. Si el design system cambió, avisa que diseño lo revisa en la planificación. Nombra la skill como figura en tu lista de skills: instalada como plugin de Claude Code es `flujo-diseno:checklist-diseno`; con `npx skills`, `checklist-diseno`.
