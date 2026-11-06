---
name: checklist-diseno
description: Revisa las vistas HTML del repositorio de diseño contra la definición de listo antes de la planificación del sprint - escenarios completos (vacío, cargando, error, sin permiso, muchos datos y los del spec), controles de prototipo fuera de la pantalla, valores visuales solo desde tokens.css, datos ficticios, tickets o spec citados - y cruza cada vista con los criterios de aceptación de sus tickets, o con su spec si no tiene tickets. Corrige con el sí los bloqueos mecánicos (enlaces, valores sueltos, animaciones, clases sin regla) y entrega un informe en el chat con lo que bloquea y lo que conviene mirar. Úsala siempre que producto o diseño quiera saber si un diseño está listo para construir, aunque no diga "checklist" - "revisa si las vistas están listas", "¿esto pasa la definición de listo?", "chequea el diseño antes de la planning", "revisa el HTML de alertas", "¿le falta algo a esta vista?". No la uses para crear o editar vistas (spec-a-html) ni para escribir tickets (spec-a-tickets).
---

# Checklist de diseño

Revisa si las vistas de `design/vistas/` están listas para construir. El resultado es un informe en el chat que producto lleva a la planificación del sprint, donde TL y producto dan el diseño por listo. La skill no aprueba ni bloquea nada por su cuenta: dice qué falta y por qué importa. Los bloqueos que tienen un solo arreglo correcto los corrige ella misma con el sí de la persona y los guarda en el repositorio de diseño, para que no lleguen a la planificación; lo demás va al informe.

Quien la usa suele ser de producto. Habla en español y explica cada hallazgo por lo que DEV no podría construir o construiría mal, no por la regla que incumple.

## Intérprete de Python

Al empezar, una sola vez, busca el intérprete: prueba `python3`, `python` y `py -3`, en ese orden, con `<intérprete> -c "import sys; assert sys.version_info >= (3, 9)"`, y usa el primero que sale sin error como `<intérprete>` en cada orden de esta skill y de sus `references/`, siempre con `-B`, para que Python no deje `__pycache__/` en la carpeta de la skill. Si ninguno pasa la prueba, no corras ninguna orden con Python y sigue lo que esta skill dice para cuando no encontraste intérprete.

## Skills hermanas

Esta skill es parte de un flujo de cinco: `grilling-es`, `spec-a-tickets`, `spec-a-html`, `html-a-vista` y `checklist-diseno`. Antes de seguir con una, comprueba que esté instalada: que figure en tu lista de skills, o que exista `../<hermana>/SKILL.md` junto a esta skill. Con `npx skills` se instalan de a una, y una puede faltar.

Detente. Si falta una hermana, propón instalar el plugin completo, que trae las cinco juntas. Con el sí, si esta skill está bajo `.claude/plugins/`, corre `claude plugin marketplace add grez-lucas/design-flow-skills` y `claude plugin install flujo-diseno@design-flow-skills`; si vino con `npx skills`, corre `npx skills@latest add grez-lucas/design-flow-skills -a <agente>` desde la carpeta donde se instaló, con `-g` si está a nivel de usuario. Las skills nuevas se cargan al abrir una sesión: pide reiniciar la sesión y, en la nueva, vuelve a probar que la hermana esté antes de seguir. Sin el sí, o si la instalación falla, queda detenida y di qué quedó sin hacer.

## Pasos

### 1. Qué revisar

Trabaja en el repositorio de diseño (tiene `design/` en la raíz). Si el directorio actual no lo es, pregunta dónde está.

Detente. Si el producto no tiene repositorio de diseño, no hay vistas que revisar, y crearlo lo decide el TL, así que no se hace desde la sesión. Redacta el pedido al TL con `references/rama.md`, sección "Pedido al TL", y di qué quedó sin hacer: no se revisó nada. Cuando exista, vuelve a correr este paso.

Si la persona nombra una épica o una vista, revisa esas; si no, pregunta si revisas todo `design/vistas/` o solo lo que cambió desde la última planificación. Para lo que cambió, `git log` y `git diff` del repositorio de diseño lo muestran.

### 2. Revisión mecánica

Corre el script incluido:

```
<intérprete> -B <ruta-de-esta-skill>/scripts/revisar.py <repo-de-diseño> [vistas...]
```

Detente. Si `revisar.py` dice que no hay vistas en `design/vistas/<épica>/`, no hay qué revisar. Si hay archivos HTML sueltos en `design/` o en la raíz del repositorio, propón moverlos a `design/vistas/<épica>/`; con el sí, muévelos y vuelve a correr `revisar.py`. Si no hay ninguno, propón dibujarlas con `spec-a-html`, si la épica tiene spec, o convertirlas con `html-a-vista`, si hay un mockup; con el sí, sigue con esa skill, o con "Skills hermanas" si no está, y vuelve a este paso. Sin el sí, queda detenida y di qué quedó sin hacer: no se revisó ninguna vista.

Si `revisar.py` lista vistas fuera del repositorio, no las revisa: propón la ruta equivalente dentro del repositorio de diseño, la misma `design/vistas/<épica>/<vista>.html`, o abrir el repositorio correcto. Con el sí, vuelve a correr `revisar.py` con esa ruta. Sin el sí, el informe las nombra como no revisadas.

Confirma cada BLOQUEA leyendo la línea antes de pasarlo al informe: el script puede equivocarse con SVG, consultas de contenedor o comentarios. Si descartas un hallazgo, dilo en una línea con el motivo.

Si no encontraste intérprete, revisa a mano, y dilo en el informe. Una vista grande no se lee entera: busca con grep los atributos y los valores. Lo que hay que revisar:

- Que la vista enlace `tokens.css`, `components.css` y `proto.js` de `design/` (`../../tokens.css` desde `design/vistas/<épica>/`), y nada más: ni otra hoja de estilo local, enlazada o con `@import`, ni otro script (`../../mi-proto.js` no es `proto.js`), ni `javascript:` en un enlace o formulario, ni manejadores `on...`. Lo que no se enlaza desde esos tres archivos no lo ve la revisión.
- Que no haya `@keyframes`, con o sin prefijo (`@-webkit-keyframes`, `@-o-keyframes`), en la vista, en `components.css` ni en `tokens.css`, y que esos dos no importen otras hojas con `@import`. Un comentario que nombra la animación no cuenta: es el comentario de intención que la reemplaza.
- Que declare los escenarios base (normal, vacio, cargando, error, sin-permiso, muchos-datos) o los marque en `data-no-aplica`, cada uno con su motivo y separados por `;`.
- Que cada `data-state` corresponda a un escenario declarado.
- Que cada escenario que no es base esté en la tabla `## Escenarios en pantalla` de su spec, el de `<meta name="spec">` o, sin él, `specs/<épica>/spec.md`, y que cada nombre de esa tabla sea, letra por letra, el de un `### Escenario N: <nombre>` del spec. Una tabla mal formada bloquea, y el cruce sigue con las filas que se leen; "Ninguno" o "No aplica" es una tabla vacía. Una fila que ninguna vista declara, un spec sin la sección o una vista sin spec van en "Conviene mirar". El alcance de la fila no se cruza con la vista.
- Que no haya colores ni medidas sueltas ni variables que `tokens.css` no define, en `<style>`, en `style=` ni en atributos de SVG.
- Que cada clase que la vista usa en `class=` tenga regla en `components.css` o en el `<style>` de la vista. Una clase sin regla no se ve, y DEV no sabe cómo construirla.
- Que no cargue recursos externos, tampoco desde CSS (`@import`, `url()`), ni la vista ni `components.css` ni `tokens.css`. La fuente del producto sí puede ser local: un `.woff2` que existe directo en `design/fuentes/`, cargado con `@font-face` en `tokens.css` y una `url()` relativa. Ninguna otra `url()` local ni `data:` en los compartidos, y ningún `@font-face` en la vista.
- Que cite sus tickets en `<meta name="tickets">` o, si es una vista sin ticket, su spec en `<meta name="spec">`, con la ruta del spec relativa a la raíz del repositorio (`specs/<épica>/spec.md`). Si trae los dos, mandan los tickets y el spec es contexto. Un `<meta name="spec">` declarado tiene que apuntar a un archivo que existe dentro del repositorio, aunque haya tickets.
- Que no tenga dominios que parezcan reales ni texto de relleno.
- Que, si el tema de `:root` en `tokens.css` es oscuro (`--color-bg` más oscuro que `--color-text`), declare ahí `color-scheme: dark`: sin eso las barras de desplazamiento y los controles nativos salen claros. Si `--color-bg` o `--color-text` faltan en `:root` o no tienen un color escrito, no se puede comprobar, y eso también se avisa. Los dos van en "Conviene mirar".

### 3. Revisión de criterio

Lo que el script no puede ver, lo revisas tú, vista por vista:

- **Tickets**: lee los tickets que la vista cita (en el tracker o en `specs/<épica>/tickets/`). Cada escenario "Dado, cuando, entonces" tiene que poder verse en algún escenario de la vista. Un criterio que la vista no muestra es lo primero que DEV va a preguntar. Una vista que cita solo `<meta name="spec">` no tiene tickets: no la marques por eso, crúzala contra el spec.
- **Spec**: el script ya cruzó los slugs con `## Escenarios en pantalla`; tú compara los escenarios de la vista con "Estados por vista" del spec. Uno que el spec pide y la vista no tiene bloquea. En una vista con solo spec, este cruce reemplaza al de tickets: además de "Estados por vista", cada historia y cada regla del spec que toque la vista tiene que poder verse en algún escenario.
- **Escenarios que se ven iguales**: abre cada escenario mentalmente (o en el navegador si la sesión puede, con `?escenario=<nombre>`): vacío, error y sin permiso tienen que decir qué pasa y qué puede hacer el usuario, no mostrar una pantalla en blanco.
- **Controles de prototipo**: busca selectores, pestañas o botones dentro de la pantalla que solo sirven para cambiar de caso ("plan vigente / plan expirado"). DEV no distingue andamio de producto. El script solo detecta los que tienen un manejador `on...` o un enlace a `?escenario=`; los demás los ves tú.
- **Lo que sobra**: un escenario o una acción que ni el spec ni los tickets piden; en una vista con solo spec, lo que el spec no pide. Si implica comportamiento nuevo, bloquea, porque DEV lo construiría sin criterio de aceptación; si es cosmético, va en "Conviene mirar". Los datos y los textos se revisan en "Datos o textos fuera del spec".
- **Datos o textos fuera del spec**: recorre cada escenario y anota los datos (columnas, campos, cifras, etiquetas con un valor) y los textos (títulos, mensajes, botones) que se ven, y búscalos en el spec y en los tickets. Un dato que el spec no menciona (el cargo de cada persona en una lista que el spec define solo con el nombre) bloquea: DEV tendría que sacar un campo o una consulta sin criterio de aceptación. Un texto que contradice al spec o a otro texto del mismo escenario ("Elige un destino" junto a "No hay destinos disponibles") también bloquea. Una etiqueta que solo nombra lo que el spec ya pide va en "Conviene mirar". Ante la duda, bloquea y se pregunta en la planificación.
- **No aplica**: cada motivo de `data-no-aplica` tiene que coincidir con el spec o ser evidente. Un escenario base marcado como no aplica que el spec no menciona se pregunta en la planificación.
- **Textos**: completos y en el idioma del producto. Un texto genérico ("Mensaje de error") obliga a DEV a inventarlo.
- **Interacciones**: lo que pasa al hacer clic, validar o esperar, como comentario junto al elemento cuando no es obvio.
- **Datos ficticios**: verosímiles y de volumen real en muchos datos (nombres largos, montos grandes, decenas de filas).

### 4. Corregir lo mecánico

Algunos bloqueos tienen un solo arreglo correcto, que no decide nada de producto. Esos los corriges tú con el sí de la persona, en vez de dejarlos para la planificación, porque quien usa la skill no arregla archivos a mano.

Antes de escribir la primera corrección, decide la rama: el paso 5 guarda en la rama actual, y cambiar de rama con archivos sin guardar puede fallar. La épica es la de las vistas que vas a corregir; si son de más de una, una épica a la vez (paso 5). Corre, con la ruta absoluta de esta skill en lugar de `<ruta-de-esta-skill>` y desde el repositorio de diseño:

```
<intérprete> -B <ruta-de-esta-skill>/scripts/rama.py revisar --tipo diseno --epica <épica>
```

Si no encontraste intérprete, para y no guardes: explica en simple que falta Python 3.9 o superior y que se instala desde https://www.python.org/downloads/.

Detente. Si `rama.py` sale con error o no devuelve un JSON, aquí o tras un rechazo, no escribas en el repositorio y sigue `references/rama.md`, sección "Error de rama.py": si el nombre termina en guion y número, propón otro, por ejemplo `fase-dos` en lugar de `fase-2`, y con el sí vuelve a correrlo; sin el sí, queda detenida y di qué quedó sin hacer.

El script trae lo nuevo del servidor, no cambia de rama y devuelve un JSON con una `accion`:

- `guardar`: nada de lo que había en la copia entraría en tu commit: guarda en la rama actual, con el commit de `rama.py` que dice `references/rama.md`, sección "El commit de la skill".
- `volver`: la rama ya no está en el servidor, por ejemplo porque el TL hizo el merge y la borró, y lo que tenía ya está en la principal. Corre la misma orden de `rama.py` con `volver` en lugar de `revisar`, que cambia a la principal al día con el servidor, y sigue con la `accion` que devuelva.
- `parar`: Detente. Todavía no escribas en el repositorio: explica en simple el `detalle` y en qué rama estás, y sigue `references/rama.md`, que da el arreglo de cada `motivo`. Con `cambios-sin-guardar`, `otra-rama`, `sin-rama`, `commits-sin-empujar` o `principal-adelantada`, propón apartar lo que había en una rama propia y, con el sí, corre la misma orden de `rama.py` con `apartar` en lugar de `revisar`, que lo aparta y vuelve a correr la revisión; cuando falta el servidor, eso no se arregla desde la sesión y va el pedido al TL. Sin el sí, di qué quedó sin hacer.

Sin Python no hay cómo guardar: las correcciones van al informe como bloqueos, cada una con el arreglo que propones.

Los bloqueos mecánicos:

- **Enlaces**: la vista no enlaza `tokens.css`, `components.css` o `proto.js`. Agrega el `<link>` o el `<script>` que falta, con la ruta relativa desde su carpeta (`../../tokens.css`). Una hoja o un script ajeno no se borra: pinta o mueve algo, y va al informe.
- **Valores sueltos**: un color o una medida igual al valor de un solo token de `tokens.css`, y ese token es de la familia de la propiedad (un color con un `--color-*`, un margen o un relleno con un `--space-*`, un radio con un `--radius-*`, un tamaño de letra con un `--font-size-*`), se reemplaza por su `var(--token)`. Un valor con un solo token de otra familia, como un `margin: 16px` cuyo único `16px` es `--radius-lg`, va al informe: usar un radio como margen lo decide producto. Si dos o más tokens tienen ese valor (`--space-4` y `--radius-lg` en `16px`), elegir es de producto: va al informe. Un valor sin token igual va al informe: elegir el token más cercano o crear uno es una decisión de producto.
- **Animaciones**: un `@keyframes` se quita, con la propiedad `animation` que lo usa, y en su lugar queda un comentario que dice qué se mueve y cuándo, como pide la convención de vista.
- **Clases sin regla**: si la clase es de los compartidos de `spec-a-html` (`.modal`, `.toast-region` y las demás de su `assets/components.css`), la trae la puesta al día de `spec-a-html`, con su script y como en su paso 4: compara, muestra el cambio y escribe solo con el sí. Una clase que no es de los compartidos va al informe: su regla es diseño.
- **Tabla de escenarios del spec**: un error de formato de `## Escenarios en pantalla` (las columnas, el separador, una fila sin tres columnas) se corrige en el formato, sin cambiar ningún slug, nombre ni alcance. Si el spec está congelado (abre con su línea `Congelado`), es la única edición que se le hace, como excepción, y el mensaje del commit la dice (paso 5). Un slug inválido o repetido, o un nombre que no es el de un `### Escenario` del spec, cambia lo que dice el spec: va al informe.

El JavaScript propio, los recursos externos y las metas de tickets y spec no son mecánicos: siguen en el informe. Quitar un script o un recurso cambia lo que la vista hace o muestra, y los tickets o el spec que cita una vista los sabe producto.

La puesta al día de los compartidos:

```
<intérprete> -B <ruta-de-esta-skill>/../spec-a-html/scripts/compartidos.py comparar <repo-de-diseño>
<intérprete> -B <ruta-de-esta-skill>/../spec-a-html/scripts/compartidos.py mostrar <repo-de-diseño>
<intérprete> -B <ruta-de-esta-skill>/../spec-a-html/scripts/compartidos.py aplicar <repo-de-diseño>
```

Si `../spec-a-html/` no está junto a esta skill, sigue "Skills hermanas"; sin el sí, esas clases van al informe.

Muestra cada cambio antes de escribirlo, vista por vista, y pide el sí. Con el sí, escríbelo y vuelve a correr `revisar.py` sobre las vistas que tocaste; lo que siga bloqueando va al informe. Sin el sí, el cambio queda en el informe como bloqueo, con el arreglo que propusiste.

### 5. Guardar

Si corregiste algo, haz commit y push a la rama actual del repositorio de diseño después de mostrar el resumen y pedir la confirmación, con el mensaje `diseno(<épica>): <resumen>`, por ejemplo `diseno(alertas): enlaces y valores sueltos del listado`. El mensaje dice qué vistas cambiaron y qué se corrigió en cada una. Si corregiste el formato de la tabla de un spec congelado, el cuerpo del mensaje lo dice como excepción: `Excepción: formato de ## Escenarios en pantalla en specs/<épica>/spec.md, congelado, sin cambiar lo que dice.` Si no corregiste nada, no hay commit.

Si corregiste vistas de más de una épica, guarda una épica por commit: decide la rama del paso 4 para cada una antes de escribir sus correcciones, y guárdala antes de pasar a la siguiente, para que el merge request de cada épica revise solo lo suyo. Lo que trae la puesta al día de los compartidos (`tokens.css`, `components.css`, `proto.js`) es de todas las épicas: entra en el commit de la primera, y su mensaje lo dice.

Agrega solo lo que corregiste: `git add design/`, y `git add specs/<épica>/` si corregiste la tabla de un spec; nunca `git add -A` ni `git add .`: si las skills se instalaron en el proyecto con `npx skills`, `.agents/`, `.claude/skills/` y `skills-lock.json` quedan sin seguimiento y no van en el commit. El resumen lista solo los archivos que entran en el commit.

La rama quedó revisada en el paso 4. El push va a la rama actual, con `git push`. Si falla por credenciales, porque el servidor no reconoce el usuario o el token, sigue `references/rama.md`, sección "Push sin credenciales": el TL es quien da los accesos, y el commit queda solo en esta máquina. Si lo rechaza por cualquier motivo que no sea de credenciales (la rama está protegida, o tiene cambios que tu copia no tiene), no lo arregles en esa rama, sin `git pull --rebase`, `git reset --hard` ni `--force`: el TL resuelve en el merge request. Pide la rama nueva, desde el repositorio de diseño, con `<intérprete> -B <ruta-de-esta-skill>/scripts/rama.py rechazo --tipo diseno --epica <épica>`.

- `rama-nueva`: explica en simple que el servidor no aceptó el cambio en esa rama y propón pasarlo a la rama nueva. Con el sí, pasa el commit con `git switch -c <rama_nueva>` y empújalo con `git push -u origin <rama_nueva>`; deja la `rama` de la que saliste como está en el servidor con `git branch -f <rama> origin/<rama>`. Explica que las correcciones quedaron en la rama nueva y que el TL revisa y hace el merge request. Sin el sí, o si un comando falla, sigue `references/rama.md`, sección "Rama nueva".
- `parar`: explica en simple el `detalle` y que el TL es quien da los accesos, y sigue `references/rama.md`, sección "Rama nueva rechazada".

### 6. Informe

Entrega el informe en el chat, en este orden:

```
## Resultado

<N> vistas revisadas: <M> listas (con o sin avisos), <K> con bloqueos. <S> specs con bloqueos en su tabla de escenarios.

## <ruta de la vista> · <tickets, o Spec: <ruta> si la vista no cita tickets>

Bloquea:
- <qué falta> - <qué no podría construir DEV sin esto>

Conviene mirar:
- <aviso>

Lista.   (cuando no tiene hallazgos)

## Archivos compartidos

<hallazgos de tokens.css, components.css y proto.js, si hay>

## Escenarios del spec · <ruta del spec>

Bloquea:
- <error de la tabla `## Escenarios en pantalla`> - <qué vista queda sin escenario que la respalde>

Conviene mirar:
- <fila que ninguna vista declara, o el spec no tiene la sección>

Sin hallazgos.   (cuando no tiene)

## Corregido

- <archivo> - <qué se corrigió>
- <spec congelado> - formato de `## Escenarios en pantalla`, como excepción dicha en el commit

Commit: <hash corto> en <rama>

## Siguiente paso

<qué corregir con spec-a-html antes de la planificación, o "listo para llevar a la planificación">
```

Bloquea lo que impide construir sin preguntar: un escenario del spec o un criterio de un ticket que no se ve, valores visuales sueltos, variables sin definir o clases sin regla en `components.css` ni en el `<style>` de la vista, un escenario de la vista que no es base ni está en `## Escenarios en pantalla` del spec, una fila de esa tabla que no nombra un `### Escenario` del spec, controles de prototipo dentro de la pantalla, JavaScript propio, hojas de estilo que no son las del repositorio o animaciones con `@keyframes`, una vista que no cita tickets ni spec o declara un spec que no existe o está fuera del repositorio, aunque cite tickets, recursos externos, texto de relleno, y dominios o marcas que confirmaste que son reales (el script los marca como aviso porque no puede saberlo; tú sí, mirando si el nombre existe fuera del ejemplo). Lo demás va en "Conviene mirar".

Lo que no es mecánico no lo corrijas: el informe es para decidir en la planificación. Si la persona quiere corregirlo, el siguiente paso es `spec-a-html` en modo edición, con la lista de hallazgos. Nombra la skill como figura en tu lista de skills: instalada como plugin de Claude Code es `flujo-diseno:spec-a-html`; con `npx skills`, `spec-a-html`.
