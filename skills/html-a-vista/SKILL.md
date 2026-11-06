---
name: html-a-vista
description: Convierte un mockup HTML que ya existe - un prototipo autocontenido, un HTML de otra herramienta, un mockup compuesto con módulos en iframes o una galería de variantes - en vistas del repositorio de diseño con la convención de spec-a-html (tokens.css, components.css, proto.js y una vista por pantalla). Desarma el archivo con un script, muestra un plan, reparte la conversión entre subagentes en tres olas, mapea cada valor a los tokens y verifica la fidelidad con un inventario por vista. Úsala siempre que alguien quiera llevar un HTML hecho al repositorio de diseño, aunque no diga "convertir" - "pasa este mockup al repo de diseño", "convierte el prototipo a vistas", "este HTML lo vamos a tocar en el próximo ticket, súbelo", "trae el mockup de Figma exportado", "migra el mockup al design system", "el mockup pesa demasiado, pártelo en vistas". No la uses para diseñar desde un spec sin HTML (spec-a-html), para revisar vistas ya convertidas (checklist-diseno) ni para escribir el spec (grilling-es).
---

# HTML a vista

Convierte un mockup HTML hecho en vistas del repositorio de diseño. El resultado es el mismo que deja `spec-a-html`: `design/tokens.css`, `design/components.css`, `design/proto.js` y un HTML por pantalla en `design/vistas/<épica>/<vista>.html`, con sus escenarios en `data-escenarios` y `data-state`. Lo que cambia es la entrada: en vez de un spec, un archivo que ya tiene pantallas, estilos propios, controles de prototipo y JavaScript.

Quien la usa suele ser de producto o de diseño. Habla en español, sin jerga de git ni de CSS salvo que la persona la use primero, y explica cada decisión por lo que se ve en pantalla.

## Intérprete de Python

Al empezar, una sola vez, busca el intérprete: prueba `python3`, `python` y `py -3`, en ese orden, con `<intérprete> -c "import sys; assert sys.version_info >= (3, 9)"`, y usa el primero que sale sin error como `<intérprete>` en cada orden de esta skill y de sus `references/`, siempre con `-B`, para que Python no deje `__pycache__/` en la carpeta de la skill. Si ninguno pasa la prueba, no corras ninguna orden con Python y sigue lo que esta skill dice para cuando no encontraste intérprete.

## Skills hermanas

Esta skill es parte de un flujo de cinco: `grilling-es`, `spec-a-tickets`, `spec-a-html`, `html-a-vista` y `checklist-diseno`. Antes de seguir con una, comprueba que esté instalada: que figure en tu lista de skills, o que exista `../<hermana>/SKILL.md` junto a esta skill. Con `npx skills` se instalan de a una, y una puede faltar.

Detente. Si falta una hermana, propón instalar el plugin completo, que trae las cinco juntas. Con el sí, si esta skill está bajo `.claude/plugins/`, corre `claude plugin marketplace add grez-lucas/design-flow-skills` y `claude plugin install flujo-diseno@design-flow-skills`; si vino con `npx skills`, corre `npx skills@latest add grez-lucas/design-flow-skills -a <agente>` desde la carpeta donde se instaló, con `-g` si está a nivel de usuario. Las skills nuevas se cargan al abrir una sesión: pide reiniciar la sesión y, en la nueva, vuelve a probar que la hermana esté antes de seguir. Sin el sí, o si la instalación falla, queda detenida y di qué quedó sin hacer.

## Por qué hay subagentes, olas y un script

Un mockup real pesa entre 50 mil y 500 mil tokens, redefine colores en cada pantalla y arma parte de su contenido con JavaScript al abrir un modal. Ningún agente lo lee entero, y `revisar.py` o un render por línea de comandos ven solo el envoltorio de un mockup compuesto. Por eso:

- Un script desarma el archivo en partes y trozos chicos, con un manifiesto que dice cuánto pesa cada uno. Con eso se reparte el trabajo sin que nadie abra el mockup entero.
- Tres olas. En la primera decides tú los tokens con `tokens.py`, y dos subagentes arman los componentes base y los escenarios globales. En la segunda, un subagente por vista, el marco incluido, con esos tokens ya fijados. En la tercera integras tú y un subagente que no armó ninguna vista revisa. Repartir solo por pantalla deja que cada subagente invente su design system.
- Los tokens y la integración los haces tú porque son pasos mecánicos de salida corta (scripts, copias, la tabla que producto decide en esta conversación) y necesitan la terminal, que un subagente puede no tener. Leer trozos y escribir vistas sí cuesta contexto: eso va a subagentes.
- Cada subagente escribe en una carpeta de trabajo fuera del repositorio y devuelve solo la ruta y un resumen. Así tu contexto no crece con cada vista y el repositorio no recibe borradores.
- Cada subagente te avisa cuando termina. Espera esos avisos y no programes recordatorios ni esperas con temporizador: un recordatorio de respaldo que nadie cancela deja la sesión abierta sin hacer nada hasta que vence.

## Pasos

Esta skill usa archivos de sus hermanas, instaladas junto a ella: `../spec-a-html/` (convención de vista, design system, plantillas y `proto.js`) y `../checklist-diseno/scripts/revisar.py`. Si no están, sigue "Skills hermanas": sin ellas no hay conversión, así que no leas el mockup hasta que estén `../spec-a-html/` y `../checklist-diseno/scripts/revisar.py`.

Donde dice `<ruta-de-esta-skill>`, escribe la ruta absoluta de esta carpeta, no una variable de shell, y corre una orden por llamada. Las órdenes compuestas (`S=...; ls $S && ...`) o con variables piden un permiso aparte y la sesión suele rechazarlas, y cada rechazo es un turno perdido.

### 1. Requisitos antes de abrir nada

- **Subagentes**: Detente. Esta skill los necesita: si la sesión no tiene herramienta para lanzarlos, no leas el mockup: la herramienta de subagentes es del cliente, así que no se arregla desde la sesión. Dilo en simple (un mockup grande no cabe en un contexto y convertirlo por partes en la misma sesión pierde la consistencia entre vistas) y explica dónde sí se puede: Claude Code, en la terminal o en la app de escritorio, lanza subagentes. Para abrir la conversión ahí, se abre Claude Code en la carpeta del repositorio de diseño, con estas skills instaladas, y se pide convertir el mockup con `html-a-vista`; en esa sesión la skill vuelve a probar este requisito. No derives a `spec-a-html`: rehacer las vistas desde el spec pierde lo que el mockup ya decidió. Di qué quedó sin hacer: no se leyó el mockup ni se escribió en el repositorio.
- **Un mockup por pedido**: un archivo HTML, o una carpeta cuando es una galería (un `index.html` que muestra los demás en iframes). Si te pasan dos mockups, pide elegir uno y convierte ese.
- **Repositorio de diseño**: el que tiene `design/` o `specs/` en la raíz. Si el directorio actual no lo es, pregunta dónde está.
- Detente. Si el producto no tiene repositorio de diseño, no lo crees tú, porque el TL decide el host y los accesos, y eso no se hace desde la sesión. Redacta el pedido al TL con `references/rama.md`, sección "Pedido al TL", y di qué quedó sin hacer: no se leyó el mockup. Cuando el TL lo cree, vuelve a correr este paso.
- **Carpeta de trabajo**: fuera del repositorio. Por defecto una carpeta temporal nueva (`mktemp -d`); si la persona o las reglas de la sesión indican otra, esa.

### 2. Desarmar

Si no encontraste intérprete, para aquí y no escribas en el repositorio: explica en simple que falta Python 3.9 o superior y que se instala desde https://www.python.org/downloads/.

```
<intérprete> -B <ruta-de-esta-skill>/scripts/desarmar.py <mockup.html | carpeta> <trabajo>
```

El script escribe en `<trabajo>` las partes decodificadas (`partes/`), los trozos de CSS, JS y markup por pantalla o superposición (`trozos/`), `resumen.md` y `manifiesto.json`. Lee `resumen.md`: tiene lo que necesitas para el plan en una lectura. No leas el mockup ni el manifiesto enteros; para un dato puntual del manifiesto, busca con grep o con `<intérprete> -B -c`.

Detente. Si el script sale con error, el mockup no se puede repartir, porque no se pudo desarmar. Explica en simple qué no entendió, que el mensaje lo dice, y propón el arreglo que corresponde, sin tocar nunca el original. Con el sí, aplícalo y vuelve a correr `desarmar.py`. Sin el sí, o si el arreglo no se puede hacer desde la sesión, queda detenida y di qué quedó sin hacer: no se convirtió nada y el repositorio no cambió.

- Un `<script>` sin cierre (el mensaje dice "sin cierre"): propón reparar una copia en la carpeta de trabajo: el original no se toca. Con el sí, copia el mockup a `<trabajo>/reparado/`, o la carpeta entera si es una galería, cierra en la copia cada `<script>` que nombra el mensaje con un `</script>` al final de su código, antes de la etiqueta que sigue, muéstrale a la persona qué cerraste y dónde, y vuelve a correr `desarmar.py` sobre la copia, con una carpeta de trabajo nueva. El informe dice qué se reparó.
- Un archivo que no es UTF-8: propón convertir una copia. Con el sí, escribe en `<trabajo>/reparado/` una copia en UTF-8 desde la codificación que declara su `<meta charset>` (Windows-1252 si no declara ninguna), di de qué codificación salió y vuelve a correr `desarmar.py` sobre la copia, con una carpeta de trabajo nueva.
- Una carpeta sin `index.html`: lista sus HTML, pregunta cuál es la entrada y vuelve a correr `desarmar.py` sobre ese archivo.
- Un archivo que no se puede leer: busca el mockup por su nombre cerca de la ruta que te dieron, confirma con la persona cuál es y vuelve a correr `desarmar.py` sobre él.
- Una carpeta de trabajo con un manifiesto previo no se pregunta: vuelve a correr con una carpeta nueva (`mktemp -d`).
- Detente. Con un archivo sin marcado HTML, o partes con el mismo id, no hay una reparación que no suponga lo que el mockup quiso decir, así que no se arregla desde la sesión: pide el mockup exportado de nuevo como HTML y di qué quedó sin hacer; con el archivo nuevo, vuelve a correr `desarmar.py`.

### 3. Framework por CDN

Si `resumen.md` dice "requiere render: sí" (React, Vue, Babel o Tailwind por CDN), el fuente no tiene la pantalla: su `<body>` es un `<div id="root">` y los colores viven en clases utilitarias.

- Detente. Sin navegador en la sesión, no lances subagentes: este mockup no se convierte sin render. Propón instalarlo como dice `references/navegador.md`, sección "Instalar": con el sí, instálalo y repite la prueba de su sección "Probar"; el render necesita además red para bajar el framework. Si pasa, sigue con el render. Sin el sí, o si la prueba sigue fallando, queda detenida sin escribir en el repositorio y di qué quedó sin hacer: no se convirtió nada.
- Con navegador, renderiza el estado inicial y convierte desde el DOM, con `references/escenarios.md`, sección "Render". Los estados que solo se alcanzan interactuando con el framework quedan fuera, salvo los que el código deja leer; dilo en el informe.

Después de cada render, comprueba que no quedó vacío: el contenedor donde monta el framework (`#root`, o `#app` en Vue) tiene que tener contenido.

```
<intérprete> -B -c "import re, sys; t = open(sys.argv[1], encoding='utf-8').read(); sys.exit(0 if re.search(r'<div[^>]*id=.(?:root|app).[^>]*>\s*<[^/]', t) else 1)" <trabajo>/render/<parte>.html
```

Detente. Si sale con 1, el render quedó vacío: casi siempre falta red para bajar el framework, y eso no se arregla desde la sesión. No lances subagentes, dilo en simple, di qué quedó sin hacer (no se convirtió nada) y, cuando haya red, vuelve a correr el render y esta prueba.

Sin framework por CDN, el navegador sirve para las capturas de la ola 3: si no hay, propón instalarlo igual, como dice `references/navegador.md`. Para saber si hay navegador, en los dos casos, sigue su sección "Probar". Sin el sí, sigue: la verificación queda en el inventario y el informe lo dice.

### 4. Spec y tickets

La conversión exige spec, como `spec-a-html`. Búscalo en `specs/<épica>/spec.md`, en el pedido o en el tracker.

- **Sin spec**: Detente. No conviertas todavía. Lanza un subagente que lea los trozos y arme un borrador de spec general del mockup con la plantilla de `grilling-es` (lo que hace cada pantalla, sus estados y reglas, y como pendientes lo que el HTML no decide), y que lo escriba en `<trabajo>/borrador-spec.md`. Muéstraselo a la persona y propón cerrarlo con `grilling-es` en esta sesión, con el borrador como punto de partida. Con el sí, sigue con `grilling-es` (`flujo-diseno:grilling-es` si está instalada como plugin de Claude Code; si no está, "Skills hermanas") y, cuando exista `specs/<épica>/spec.md`, vuelve a este paso. Sin el sí, queda detenida y di qué quedó sin hacer: el borrador está en `<trabajo>/borrador-spec.md` y no se convirtió nada. El spec del mockup entero es general: un documento funcional, no la lista de lo que se va a construir.
- **Con spec**: anota los tickets que existan. Una vista con ticket lleva `<meta name="tickets">`; una sin ticket lleva `<meta name="spec" content="specs/<épica>/spec.md">`. Los tickets se escriben solo para lo que se va a construir, con `spec-a-tickets`.

### 5. Plan y ok

Con `resumen.md` y el spec, arma el plan siguiendo `references/plan.md` y muéstralo antes de lanzar subagentes:

- pantallas detectadas, por parte, con el título que muestran en el mockup (el que trae `resumen.md`), para que producto las reconozca;
- tabla pantalla a vista: pantalla con ese título, vista, archivo, épica, escenarios (con su origen: control DEMO, función, superposición), trozos de origen;
- subagentes por ola y tokens estimados de lo que lee cada uno, con al menos una fila por vista en la ola 2, la del marco incluida;
- lo que no tiene equivalente y cómo queda (`references/sin-equivalente.md`).

Reglas de la tabla: una vista por pantalla, panel o ruta; modales, drawers y subvistas son escenarios de la vista que los abre, no vistas propias; un asistente de pasos es un flujo con un escenario por paso, o un archivo por paso si la vista pasaría las 300 líneas. En un mockup compuesto (shell más módulos), cada módulo es una sección del spec y una épica, y el shell es una vista propia con los escenarios globales.

Espera el ok: los subagentes y la escritura en el repositorio van recién con él. Producto puede cambiar la tabla; rehazla y vuelve a mostrarla.

Con el ok, antes de lanzar la ola 1, decide la rama del repositorio de diseño: el paso 10 guarda en la rama actual, los pasos 6 y 9 ya escriben en el repositorio, y cambiar de rama con archivos sin guardar puede fallar. La épica es la del plan; si el plan reparte las vistas en más de una, pasa `--mockup <mockup> --epicas <épica>,<épica>` en lugar de `--epica <épica>`, con todas las épicas del plan y `<mockup>` como en el paso 10. Corre, con la ruta absoluta de esta skill en lugar de `<ruta-de-esta-skill>`:

```
<intérprete> -B <ruta-de-esta-skill>/scripts/rama.py revisar --tipo diseno --epica <épica> --repo <repo-de-diseño>
```

Si no encontraste intérprete, para y no guardes: explica en simple que falta Python 3.9 o superior y que se instala desde https://www.python.org/downloads/.

Detente. Si `rama.py` sale con error o no devuelve un JSON, aquí o tras un rechazo, no escribas en el repositorio y sigue `references/rama.md`, sección "Error de rama.py": si el nombre termina en guion y número, propón otro, por ejemplo `fase-dos` en lugar de `fase-2`, y con el sí vuelve a correrlo; sin el sí, queda detenida y di qué quedó sin hacer.

El script trae lo nuevo del servidor, no cambia de rama y devuelve un JSON con una `accion`:

- `guardar`: nada de lo que había en la copia entraría en tu commit: guarda en la rama actual, con el commit de `rama.py` que dice `references/rama.md`, sección "El commit de la skill".
- `ofrecer`: Detente. La conversión es de varias épicas y estás en la rama de una sola de ellas: guardar ahí no sirve, porque el merge request de esa épica no revisa las demás. Antes de escribir nada, explica en qué rama estás y por qué, y ofrece volver a la principal y guardar en `rama_nueva`. Solo con el sí de la persona, corre la misma orden de `rama.py` con `volver` en lugar de `revisar` y `--rama-nueva <rama_nueva>`: vuelve a correr la revisión, porque la copia pudo cambiar mientras esperabas, y crea la rama nueva desde la principal al día con el servidor. Sigue con la `accion` que devuelva. Si devuelve `ofrecer` con otra `rama_nueva`, porque esa ya existe, ofrécela de nuevo. Si `apartar` devuelve `ofrecer`, ya tienes el sí: corre `volver` con `--rama-nueva <rama_nueva>` sin preguntar otra vez. Sin el sí, queda detenida sin escribir en el repositorio y di en qué rama estás y qué quedó sin hacer: la conversión no empezó.
- `volver`: la rama ya no está en el servidor, por ejemplo porque el TL hizo el merge y la borró, y lo que tenía ya está en la principal. Corre la misma orden de `rama.py` con `volver` en lugar de `revisar`, que cambia a la principal al día con el servidor, y sigue con la `accion` que devuelva.
- `parar`: Detente. Todavía no escribas en el repositorio: explica en simple el `detalle` y en qué rama estás, y sigue `references/rama.md`, que da el arreglo de cada `motivo`. Con `cambios-sin-guardar`, `otra-rama`, `sin-rama`, `commits-sin-empujar` o `principal-adelantada`, propón apartar lo que había en una rama propia y, con el sí, corre la misma orden de `rama.py` con `apartar` en lugar de `revisar`, que lo aparta y vuelve a correr la revisión; cuando falta el servidor, eso no se arregla desde la sesión y va el pedido al TL. Sin el sí, di qué quedó sin hacer.

### 6. Compartidos al día

Un repositorio de diseño creado con una versión anterior de las skills no tiene las reglas, los tokens ni el `proto.js` de hoy. La ola 1 trae por su cuenta la regla del frame, las del modal y los avisos y sus tokens cuando el mockup los tiene, pero no `proto.js`: sin la puesta al día, las vistas se arman y se revisan con el `proto.js` viejo, que `revisar.py` solo avisa, y lo que copia la ola 1 entra sin que la persona vea antes que `:where([data-frame])` cambia cómo se ven las vistas que el repositorio ya tiene. Por eso los compartidos se ponen al día antes de la ola 1, con el script de `spec-a-html`: las tres olas trabajan sobre el repositorio ya al día, y los tokens de la ola 1 y las huellas del revisor parten de los compartidos que van a quedar.

Si el repositorio no tiene `design/`, o su `design/` no tiene `tokens.css`, `components.css` ni `proto.js`, no hay compartidos que poner al día: la ola 1 los arma desde los de `spec-a-html`. Si `design/` tiene `components.css` o `proto.js` pero no `tokens.css`, el repositorio quedó a medias: `compartidos.py` no compara un `design/` sin `tokens.css`, y la ola 1 partiría de compartidos viejos que la persona no vio.

Detente. Con un `design/` a medias, no empieces la ola 1: explícalo en simple y propón armar `tokens.css` ahora desde el mockup, como lo armaría la ola 1 en un repositorio sin tokens, para que conserve los valores del mockup; con el sí a la tabla lo escribes, vuelves a correr `comparar` y sigues, y sin el sí queda detenida y di qué quedó sin hacer, como dice el párrafo siguiente:

```
<intérprete> -B <ruta-de-esta-skill>/scripts/tokens.py consolidar <trabajo>/trozos/*/estilos*.css --roles <repo-de-diseño>/design/components.css
```

Sigue `references/tokens.md` para la consolidación: la tabla que decide producto, los nombres con la convención de prefijos y `<intérprete> -B <ruta-de-esta-skill>/scripts/tokens.py verificar` antes de escribir. La tabla lleva también, como roles a llenar, los tokens que usa el `components.css` viejo, cada uno con un valor del mockup que producto elige entre los que lista la sección "Roles del components.css del repositorio", todos, del más usado al menos (los valores que el mockup da en las mismas propiedades exactas, también por sus propias variables): así la puesta al día no los agrega con los valores de la plantilla. Un rol para el que el mockup no tiene valor se propone con el valor por defecto del navegador para la propiedad donde lo usa el `components.css`, que es lo que el mockup muestra (`normal` para `line-height`, `none` para `box-shadow`, `currentColor` para un borde, `transparent` para un fondo, `0` para un relleno o un radio, `medium` para `font-size`, `inherit` para `font-family`), solo si todas las propiedades donde se usa comparten ese valor; producto puede cambiarlo. Si no lo comparten, o la propiedad no tiene un valor por defecto claro (`opacity`, `transform`, un color dentro de `box-shadow`), la fila dice "producto decide" y no propone nada. Ese valor se propone solo donde el token es el valor entero de la declaración, o el color de un abreviado de borde o de contorno para un `--color-*`; en otra posición, como dentro de `calc()`, de una lista de sombras o en el ancho de un abreviado, la fila dice "producto decide", y un token que ocupa solo una parte del valor no recibe el valor entero del mockup. Si el mockup tiene tema oscuro, cada rol lleva además el valor del mockup en ese tema, que va al bloque del tema en `tokens.css`. Con el sí a la tabla, escribe `tokens.css` en `design/` del repositorio, corre `comparar` y sigue con la puesta al día desde ahí. Sin el sí a la tabla, el repositorio queda como estaba; di qué quedó sin hacer: falta `tokens.css`, `components.css` y `proto.js` siguen viejos y la conversión no empezó. En este caso las tres órdenes de la puesta al día de abajo van con `--solo-usados`, y lo demás sigue igual:

```
<intérprete> -B <ruta-de-esta-skill>/../spec-a-html/scripts/compartidos.py comparar <repo-de-diseño> --solo-usados
<intérprete> -B <ruta-de-esta-skill>/../spec-a-html/scripts/compartidos.py mostrar <repo-de-diseño> --solo-usados
<intérprete> -B <ruta-de-esta-skill>/../spec-a-html/scripts/compartidos.py aplicar <repo-de-diseño> --solo-usados
```

Con `--solo-usados`, `faltan` trae solo los tokens de la plantilla que usa algún compartido (`components.css`, `tokens.css` o `proto.js`), como `--color-overlay` y `--size-modal` de las reglas del modal, con los valores de la plantilla: nómbralos al pedir el sí. El resto de la escala de la plantilla queda en `omitidos` y no entra, para que `tokens.css` no mezcle la escala del mockup con la de la plantilla. En la ola 1 ese `tokens.css` ya existe: los valores del mockup se llevan a sus tokens con `<intérprete> -B <ruta-de-esta-skill>/scripts/tokens.py mapear`, no se consolidan otra vez.

Si `design/tokens.css` ya existía, compara:

```
<intérprete> -B <ruta-de-esta-skill>/../spec-a-html/scripts/compartidos.py comparar <repo-de-diseño>
```

Si el JSON trae `"cambios": false`, sigue con la ola 1. Si trae `"cambios": true`, muestra el cambio antes de escribirlo:

```
<intérprete> -B <ruta-de-esta-skill>/../spec-a-html/scripts/compartidos.py mostrar <repo-de-diseño>
```

Explícalo en simple: qué reglas y tokens se suman (`faltan`), cuáles quedan fuera y por qué (`omitidos`) y, si `proto.js` difiere, que se reemplaza por el de la skill. Nombra una por una las reglas de `cambian_lo_propio`: no tienen clase, pintan elementos que ya existen y cambian cómo se ven las vistas que el repositorio ya tiene. El resto solo pinta las clases nuevas. Escribe solo con el sí de la persona:

```
<intérprete> -B <ruta-de-esta-skill>/../spec-a-html/scripts/compartidos.py aplicar <repo-de-diseño>
```

Detente. Sin el sí a la puesta al día, no empieces la ola 1 ni escribas en el repositorio: propón de nuevo la puesta al día cuando la persona quiera, y con el sí vuelve a correr `comparar`. Explica en simple que sin la puesta al día queda un `proto.js` viejo y entran reglas que cambian cómo se ven las vistas que el repositorio ya tiene, como `:where([data-frame])`, sin que la persona las vea antes. Di qué quedó sin hacer: nombra los compartidos que siguen viejos, los de `faltan` y `proto.js` si difiere, y que la conversión no empezó. Si en este paso ya escribiste `tokens.css` desde el mockup, di también que quedó escrito en `design/` del repositorio, sin commit.

Detente. Si el script sale con error, no empieces la ola 1: explica en simple qué dice el error y propón corregirlo tú. El mensaje nombra el archivo y lo que no entendió, por ejemplo una llave sin cerrar en `components.css` o un comentario sin cerrar en `tokens.css`, con su posición: busca ahí la regla rota y propón el arreglo más chico que la cierra, sin cambiar lo que pinta. Muestra el cambio antes de escribirlo y, con el sí, corrígelo, vuelve a correr `comparar` y sigue con la puesta al día desde ahí. Sin el sí, o si el error no se puede corregir desde la sesión, queda detenida sin escribir en el repositorio y di qué quedó sin hacer: los compartidos siguen viejos y la conversión no empezó.

### 7. Ola 1: tokens, componentes base y escenarios globales

Sigue `references/olas.md`, sección "Ola 1". Primero los tokens, que decides tú con `references/tokens.md`, sin subagente: la salida de `tokens.py` es corta y la tabla se decide con producto en esta conversación.

- Con `design/tokens.css`: corre `<intérprete> -B <ruta-de-esta-skill>/scripts/tokens.py mapear`. Cada valor dentro del umbral va al token más cercano. Lo que queda fuera va a una tabla con el token más cercano y la propuesta de token nuevo: muéstrala y pregunta a producto, fila por fila, si usa el token cercano o aprueba el nuevo, y espera la respuesta antes de escribir `tokens.css`. Si producto acepta tu recomendación sin elegir, o no puede decidir ahora, usa el token existente más cercano entre los del mismo uso (fondo, texto, borde, superposición) y deja ese valor marcado como pendiente de decisión en el informe; si ninguno sirve para ese uso, el valor no se aplica y el informe dice qué se pierde. Nunca agregues un token nuevo que producto no aprobó.
- Sin `design/tokens.css`: corre `<intérprete> -B <ruta-de-esta-skill>/scripts/tokens.py consolidar` y muestra la tabla de consolidación (tema, valor original, ocurrencias, token propuesto, y un solo token con su valor en cada tema cuando el mockup cambia un color entre temas) antes de escribir. Un color con uso propio entra como token, no como pendiente. Los grupos de reglas sin tema que conviven con uno de un tema y se ven iguales (`tokens.py` los lista) se resuelven en esa tabla. Antes de escribir, `<intérprete> -B <ruta-de-esta-skill>/scripts/tokens.py verificar` con el `tokens.css` propuesto como único archivo encuentra los pares que se ven iguales; resuélvelos.

Deja la tabla y el `tokens.css` decidido en `<trabajo>/ola-1/tokens/`. Con los tokens decididos, lanza en paralelo dos subagentes, el de componentes base y el de los escenarios globales, que escriben en `<trabajo>/ola-1/`. El marco no se arma aquí: es una vista más y va a la ola 2.

### 8. Ola 2: una vista por subagente

Un subagente por fila de la tabla, en paralelo, con `references/olas.md`, sección "Ola 2". El marco es una fila como las demás: tiene su subagente y su contrato, y si el revisor no lo aprueba vuelve a ese subagente. No juntes vistas en un subagente, aunque sean chicas o del mismo módulo: cada borrador sale de un contexto propio, su contrato es independiente y el revisor aprueba o devuelve vista por vista. Un subagente con dos vistas mezcla sus decisiones, y si una vuelve con notas, vuelven las dos. Nombra cada uno con su ola y su vista (`Ola 2: <vista>`), así se coteja con el plan. Cada uno recibe las rutas de sus trozos, los tokens y componentes de la ola 1 (no el CSS entero del mockup), los nombres de los escenarios globales y la plantilla del contrato. Escribe el borrador de su vista y su contrato en `<trabajo>/ola-2/<épica>/<vista>/` y devuelve solo la ruta y un resumen de cinco líneas.

### 9. Ola 3: integrar, inventariar y revisar

Con `references/olas.md`, sección "Ola 3":

1. Integras tú, sin subagente: copias el repositorio, ya al día desde el paso 6, en `<trabajo>/ola-3/repo/`, armas ahí `components.css` final con lo nuevo de cada contrato, dejas las vistas en la copia, corres `<intérprete> -B <ruta-de-esta-skill>/scripts/inventario.py` por vista, con `--salida` para que el inventario quede en disco, y `<intérprete> -B <ruta-de-esta-skill>/../checklist-diseno/scripts/revisar.py` sobre esa copia. Con navegador, sacas aquí las capturas por escenario, del original y de la vista (`references/escenarios.md`, sección "Capturas"): tienen que existir antes de que el revisor empiece. Sin navegador, la verificación queda en el inventario y el informe lo dice.
2. Un revisor que no armó ninguna vista lee el inventario de cada vista, su contrato y el spec, y decide vista por vista: aprobada, o con lo que falta. Con navegador, le pasas las rutas de las capturas del original y de la vista por escenario, y las compara lado a lado. Deja cada veredicto en `<trabajo>/ola-3/revision.md` con el formato fijo de `references/olas.md`, por la ruta de la vista (`## <épica>/<vista>: ...`), para que se lea sin interpretar y dos vistas con el mismo nombre en épicas distintas no se confundan, y cada aprobación con la huella de lo que aprobó (`<intérprete> -B <ruta-de-esta-skill>/scripts/aprobadas.py huella <vista>`): si la vista o un compartido cambia después, ya no es lo que el revisor vio.
3. Una vista no aprobada no la corriges tú, aunque el arreglo sea de una línea: vuelve una vez a su subagente de la ola 2 con las notas del revisor, la integras de nuevo y el revisor la mira otra vez. El revisor es la única mirada que no armó la vista; si la corrige quien integra, entra al repositorio sin que nadie independiente la haya visto. Si en esa segunda revisión sigue sin aprobarse, no hay tercera vuelta: queda pendiente, la nombras con `--pendientes` en el paso siguiente y va al informe con lo que falta y cómo retomarla en otra corrida (`references/plan.md`, sección "Informe").
4. Mueves al repositorio con el script, no copiando a mano:

   ```
   <intérprete> -B <ruta-de-esta-skill>/scripts/aprobadas.py mover <trabajo> <repo-de-diseño>
   ```

   Copia de `<trabajo>/ola-3/repo/` solo las vistas cuyo último veredicto en `revision.md` es "aprobada" con la huella que tienen hoy en la copia y que tienen en disco su contrato y su inventario, lo que el revisor tuvo que leer, y `tokens.css`, `components.css` y `proto.js` si cambiaron. Si una sola vista queda fuera (no aprobada, sin veredicto, sin huella o con otra, sin contrato o inventario), no mueve nada y sale con 1: esa vista vuelve a su subagente y a la segunda revisión, o al revisor si solo cambió su huella. Así una vista no aprobada no se pierde en silencio entre las que sí entraron.

   Cuando una vista ya tuvo su segunda revisión y sigue sin aprobarse, nómbrala como pendiente para mover las demás:

   ```
   <intérprete> -B <ruta-de-esta-skill>/scripts/aprobadas.py mover <trabajo> <repo-de-diseño> --pendientes <épica>/<vista>[,<épica>/<vista>...]
   ```

   Con `--pendientes` mueve las aprobadas solo si las vistas que quedan fuera son exactamente las nombradas; si sobra o falta una, no mueve nada y dice cuál. Tampoco mueve nada si una nombrada no tiene su veredicto de segunda revisión (`## <épica>/<vista>, segunda revisión: no aprobada`) o si su último veredicto no es `no aprobada`: esa vista vuelve a su subagente, o al revisor si su huella cambió. Cada pendiente va al informe con lo que el revisor dijo que falta. Las secciones del spec que haya que actualizar las copias tú.

### 10. Guardar

Antes del commit, comprueba:

- `<intérprete> -B <ruta-de-esta-skill>/../checklist-diseno/scripts/revisar.py <repo-de-diseño>` sin hallazgos que bloquean.
- Todas las pantallas del mockup están convertidas, como vista o como escenario.
- El archivo original no está en el repositorio, ni copiado ni renombrado, y ningún archivo de la carpeta de trabajo entró.

Si `revisar.py` bloquea en una vista de esta conversión, esa vista vuelve a su subagente de la ola 2 y al revisor, como una no aprobada, y repites `mover` y esta comprobación; si ya tuvo su segunda revisión, queda pendiente. Lo que bloquea en vistas que ya estaban en el repositorio no lo corriges tú: va al informe. Si falta una pantalla, propón agregarla al plan: con el sí, abre una fila nueva y repite las olas 2 y 3 solo para esa pantalla; sin el sí, va al informe como pendiente. Si el original o un archivo de la carpeta de trabajo quedó en el área de preparación, sácalo con `git restore --staged <archivo>` y vuelve a mirar `git status`; si ya estaba en un commit anterior, dilo en el informe: retirarlo pide un commit aparte.

Cuando la persona dé el visto bueno, haz commit y push a la rama actual del repositorio de diseño, con el mensaje `diseno(<épica>): <resumen>`. El mensaje dice qué mockup se convirtió, qué épicas y vistas quedaron y qué tickets cubre. Si las vistas quedaron en más de una épica, en lugar de `<épica>` va `<mockup>`, el nombre del archivo del mockup sin extensión, en minúsculas y con guiones, en el mensaje y en la rama (`diseno(<mockup>): <resumen>` y `diseno/<mockup>`, por ejemplo `diseno(panel-general): ...` y `diseno/panel-general`), y las épicas van en el cuerpo: es una sola conversión y un solo merge request la revisa entera.

Revisa que el `.gitignore` de la raíz del repositorio de diseño tenga la línea `.lavish/`, como lo deja `spec-a-html`; si no la tiene, agrégala, y crea el archivo si falta: las revisiones con Lavish de las otras skills escriben ahí archivos que no son diseño.

Agrega solo lo que está bajo `design/` y `specs/`: `git add design/`, `git add specs/<épica>/` si tocaste algo ahí, y `git add .gitignore` si le agregaste `.lavish/`; nunca `git add -A` ni `git add .`: si las skills se instalaron en el proyecto con `npx skills`, `.agents/`, `.claude/skills/` y `skills-lock.json` quedan sin seguimiento y no van en el commit, y tampoco va el mockup original si está en el repositorio. Revisa con `git status` que no quede nada más en el área de preparación.

Muestra el resumen de archivos antes de hacer push, solo con los que entran en el commit, y pide la confirmación.

La rama quedó revisada en el paso 5. El push va a la rama actual, con `git push`; si el paso 5 creó la rama de `ofrecer`, con `git push -u origin <rama_nueva>`. Si falla por credenciales, porque el servidor no reconoce el usuario o el token, sigue `references/rama.md`, sección "Push sin credenciales": el TL es quien da los accesos, y el commit queda solo en esta máquina. Si lo rechaza por cualquier motivo que no sea de credenciales (la rama está protegida, o tiene cambios que tu copia no tiene), no lo arregles en esa rama, sin `git pull --rebase`, `git reset --hard` ni `--force`: el TL resuelve en el merge request. Pide la rama nueva con `<intérprete> -B <ruta-de-esta-skill>/scripts/rama.py rechazo --tipo diseno --epica <épica> --repo <repo-de-diseño>`. Si la conversión es de varias épicas, pasa `--mockup <mockup>` en lugar de `--epica <épica>`.

- `rama-nueva`: explica en simple que el servidor no aceptó el cambio en esa rama y propón pasarlo a la rama nueva. Con el sí, pasa el commit con `git switch -c <rama_nueva>` y empújalo con `git push -u origin <rama_nueva>`; deja la `rama` de la que saliste como está en el servidor con `git branch -f <rama> origin/<rama>`. Explica que las vistas quedaron en la rama nueva y que el TL revisa y hace el merge request. Sin el sí, o si un comando falla, sigue `references/rama.md`, sección "Rama nueva".
- `parar`: explica en simple el `detalle` y que el TL es quien da los accesos, y sigue `references/rama.md`, sección "Rama nueva rechazada".

```
diseno(riego): convierte el mockup del panel de riego

Vistas: design/vistas/riego/panel.html, design/vistas/riego/historial.html
Tickets: SEM-14
```

### 11. Informe

Cierra con el informe en el chat, con `references/plan.md`, sección "Informe": plan ejecutado, decisiones de tokens y los valores pendientes de decisión, escenarios que salieron de controles de prototipo, lo que no tiene equivalente y cómo quedó (cada lógica JS como criterio para su ticket), variante elegida si había varias, inventario por vista con quién lo revisó, capturas o la mención de que se verificó sin render, y lo que no se pudo ver. Termina sugiriendo correr `checklist-diseno` sobre las vistas nuevas antes de la planificación, y `spec-a-tickets` para las vistas sin ticket que se vayan a construir. Nombra las skills como figuran en tu lista de skills: instaladas como plugin de Claude Code son `flujo-diseno:checklist-diseno` y `flujo-diseno:spec-a-tickets`; con `npx skills`, `checklist-diseno` y `spec-a-tickets`.
