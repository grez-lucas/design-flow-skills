---
name: html-a-vista
description: Convierte un mockup HTML que ya existe - un prototipo autocontenido, un HTML de otra herramienta, un mockup compuesto con módulos en iframes o una galería de variantes - en vistas del repositorio de diseño con la misma convención de spec-a-html (design/tokens.css, components.css, proto.js y una vista por pantalla con sus escenarios). Desarma el archivo con un script, muestra un plan, reparte la conversión entre subagentes en tres olas, mapea cada valor a los tokens y verifica la fidelidad con un inventario por vista. Úsala siempre que alguien quiera llevar un HTML hecho al repositorio de diseño, aunque no diga "convertir" - "pasa este mockup al repo de diseño", "convierte el prototipo a vistas", "este HTML lo vamos a tocar en el próximo ticket, súbelo", "trae el mockup de Figma exportado", "migra el mockup al design system", "el mockup pesa demasiado, pártelo en vistas". No la uses para diseñar desde un spec sin HTML (spec-a-html), para revisar vistas ya convertidas (checklist-diseno) ni para escribir el spec (grilling-es).
---

# HTML a vista

Convierte un mockup HTML hecho en vistas del repositorio de diseño. El resultado es el mismo que deja `spec-a-html`: `design/tokens.css`, `design/components.css`, `design/proto.js` y un HTML por pantalla en `design/vistas/<épica>/<vista>.html`, con sus escenarios en `data-escenarios` y `data-state`. Lo que cambia es la entrada: en vez de un spec, un archivo que ya tiene pantallas, estilos propios, controles de prototipo y JavaScript.

Quien la usa suele ser de producto o de diseño. Habla en español, sin jerga de git ni de CSS salvo que la persona la use primero, y explica cada decisión por lo que se ve en pantalla.

## Por qué hay subagentes, olas y un script

Un mockup real pesa entre 50 mil y 500 mil tokens, redefine colores en cada pantalla y arma parte de su contenido con JavaScript al abrir un modal. Ningún agente lo lee entero, y `revisar.py` o un render por línea de comandos ven solo el envoltorio de un mockup compuesto. Por eso:

- Un script desarma el archivo en partes y trozos chicos, con un manifiesto que dice cuánto pesa cada uno. Con eso se reparte el trabajo sin que nadie abra el mockup entero.
- Tres olas de subagentes: primero tokens, componentes base y el marco común; después una vista por subagente, con esos tokens ya fijados; al final un integrador y un revisor. Repartir solo por pantalla deja que cada subagente invente su design system.
- Cada subagente escribe en una carpeta de trabajo fuera del repositorio y devuelve solo la ruta y un resumen. Así tu contexto no crece con cada vista y el repositorio no recibe borradores.

## Pasos

Esta skill usa archivos de sus hermanas, instaladas junto a ella: `../spec-a-html/` (convención de vista, design system, plantillas y `proto.js`) y `../checklist-diseno/scripts/revisar.py`. Si no están, pide instalar el flujo completo antes de seguir.

### 1. Requisitos antes de abrir nada

- **Subagentes**: esta skill los necesita. Si la sesión no tiene herramienta para lanzarlos, detente antes de leer el mockup, dilo en una línea (un mockup grande no cabe en un contexto y convertirlo por partes en la misma sesión pierde la consistencia entre vistas) y no escribas en el repositorio.
- **Un mockup por pedido**: un archivo HTML, o una carpeta cuando es una galería (un `index.html` que muestra los demás en iframes). Si te pasan dos mockups, pide elegir uno y convierte ese.
- **Repositorio de diseño**: el que tiene `design/` o `specs/` en la raíz. Si el directorio actual no lo es, pregunta dónde está. Si el producto no tiene repositorio de diseño, para y pide que el TL lo cree.
- **Carpeta de trabajo**: fuera del repositorio. Por defecto una carpeta temporal nueva (`mktemp -d`); si la persona o las reglas de la sesión indican otra, esa.

### 2. Desarmar

```
python3 -B <ruta-de-esta-skill>/scripts/desarmar.py <mockup.html | carpeta> <trabajo>
```

El script escribe en `<trabajo>` las partes decodificadas (`partes/`), los trozos de CSS, JS y markup por pantalla o superposición (`trozos/`), `resumen.md` y `manifiesto.json`. Lee `resumen.md`: tiene lo que necesitas para el plan en una lectura. No leas el mockup ni el manifiesto enteros; para un dato puntual del manifiesto, busca con grep o con `python3 -c`.

Si el script sale con error, dile a la persona qué no entendió (el mensaje lo dice) y no sigas: un mockup que no se puede desarmar no se puede repartir.

### 3. Framework por CDN

Si `resumen.md` dice "requiere render: sí" (React, Vue, Babel o Tailwind por CDN), el fuente no tiene la pantalla: su `<body>` es un `<div id="root">` y los colores viven en clases utilitarias.

- Sin navegador en la sesión (Chrome, Chromium o Playwright), detente antes de lanzar subagentes: di que hace falta instalar Google Chrome o Chromium, o Playwright con `pip install playwright` y `playwright install chromium`, y que el render necesita red para bajar el framework. No escribas en el repositorio.
- Con navegador, renderiza el estado inicial y convierte desde el DOM, con `references/escenarios.md`, sección "Render". Los estados que solo se alcanzan interactuando con el framework quedan fuera, salvo los que el código deja leer; dilo en el informe.

### 4. Spec y tickets

La conversión exige spec, como `spec-a-html`. Búscalo en `specs/<épica>/spec.md`, en el pedido o en el tracker.

- **Sin spec**: no conviertas. Lanza un subagente que lea los trozos y arme un borrador de spec general del mockup con la plantilla de `grilling-es` (lo que hace cada pantalla, sus estados y reglas, y como pendientes lo que el HTML no decide), y que lo escriba en `<trabajo>/borrador-spec.md`. Muéstraselo a la persona y deriva a `grilling-es` para cerrarlo (`flujo-diseno:grilling-es` si está instalada como plugin de Claude Code). El spec del mockup entero es general: un documento funcional, no la lista de lo que se va a construir.
- **Con spec**: anota los tickets que existan. Una vista con ticket lleva `<meta name="tickets">`; una sin ticket lleva `<meta name="spec" content="specs/<épica>/spec.md">`. Los tickets se escriben solo para lo que se va a construir, con `spec-a-tickets`.

### 5. Plan y ok

Con `resumen.md` y el spec, arma el plan siguiendo `references/plan.md` y muéstralo antes de lanzar subagentes:

- pantallas detectadas, por parte;
- tabla pantalla a vista: vista, archivo, épica, escenarios (con su origen: control DEMO, función, superposición), trozos de origen;
- subagentes por ola y tokens estimados de lo que lee cada uno;
- lo que no tiene equivalente y cómo queda (`references/sin-equivalente.md`).

Reglas de la tabla: una vista por pantalla, panel o ruta; modales, drawers y subvistas son escenarios de la vista que los abre, no vistas propias; un asistente de pasos es un flujo con un escenario por paso, o un archivo por paso si la vista pasaría las 300 líneas. En un mockup compuesto (shell más módulos), cada módulo es una sección del spec y una épica, y el shell es una vista propia con los escenarios globales.

Espera el ok. Sin ok no lances subagentes ni escribas en el repositorio. Producto puede cambiar la tabla; rehazla y vuelve a mostrarla.

### 6. Ola 1: tokens, componentes base y shell

Sigue `references/olas.md`, sección "Ola 1". Primero el subagente de tokens, con `references/tokens.md`:

- Con `design/tokens.css`: corre `python3 -B <ruta-de-esta-skill>/scripts/tokens.py mapear`. Cada valor dentro del umbral va al token más cercano. Lo que queda fuera va a una tabla con el token más cercano y la propuesta de token nuevo: muéstrala y pregunta a producto, fila por fila, si usa el token cercano o aprueba el nuevo, y espera la respuesta antes de escribir `tokens.css`. Si producto acepta tu recomendación sin elegir, o no puede decidir ahora, usa el token existente más cercano y deja ese valor marcado como pendiente de decisión en el informe. Nunca agregues un token nuevo que producto no aprobó.
- Sin `design/tokens.css`: corre `python3 -B <ruta-de-esta-skill>/scripts/tokens.py consolidar` y muestra la tabla de consolidación (valor original, ocurrencias, token propuesto) antes de escribir.

Con los tokens decididos, lanza en paralelo el de componentes base y el del shell con los escenarios globales. Los tres escriben en `<trabajo>/ola-1/`.

### 7. Ola 2: una vista por subagente

Un subagente por fila de la tabla, en paralelo, con `references/olas.md`, sección "Ola 2". Cada uno recibe las rutas de sus trozos, los tokens y componentes de la ola 1 (no el CSS entero del mockup), los nombres de los escenarios globales y la plantilla del contrato. Escribe el borrador de su vista y su contrato en `<trabajo>/ola-2/` y devuelve solo la ruta y un resumen de cinco líneas.

### 8. Ola 3: integrar, inventariar y revisar

Con `references/olas.md`, sección "Ola 3":

1. Un integrador arma `components.css` final con lo nuevo de cada contrato, deja las vistas en `<trabajo>/ola-3/repo/` (una copia del repositorio con los cambios), corre `python3 -B <ruta-de-esta-skill>/scripts/inventario.py` por vista y `python3 -B <ruta-de-esta-skill>/../checklist-diseno/scripts/revisar.py` sobre esa copia.
2. Un revisor que no armó ninguna vista lee el inventario de cada vista, su contrato y el spec, y decide vista por vista: aprobada, o con lo que falta. Con navegador, mira además las capturas lado a lado.
3. El integrador mueve al repositorio solo lo aprobado. Una vista no aprobada vuelve una vez a su subagente de la ola 2 con las notas del revisor; si sigue sin aprobarse, queda fuera y va al informe como pendiente.

Con navegador, saca capturas por escenario, original y vista lado a lado (`references/escenarios.md`, sección "Capturas"). Sin navegador, la verificación queda en el inventario y el informe lo dice.

### 9. Guardar

Antes del commit, comprueba:

- `python3 -B <ruta-de-esta-skill>/../checklist-diseno/scripts/revisar.py <repo-de-diseño>` sin hallazgos que bloquean.
- Todas las pantallas del mockup están convertidas, como vista o como escenario.
- El archivo original no está en el repositorio, ni copiado ni renombrado, y ningún archivo de la carpeta de trabajo entró.

Cuando la persona dé el visto bueno, haz commit y push a `main` del repositorio de diseño. El mensaje dice qué mockup se convirtió, qué épicas y vistas quedaron y qué tickets cubre.

Agrega solo lo que está bajo `design/` y `specs/`: `git add design/`, y `git add specs/<épica>/` si tocaste algo ahí; nunca `git add -A` ni `git add .`: si las skills se instalaron en el proyecto con `npx skills`, `.agents/`, `.claude/skills/` y `skills-lock.json` quedan sin seguimiento y no van en el commit, y tampoco va el mockup original si está en el repositorio. Revisa con `git status` que no quede nada más en el área de preparación.

Muestra el resumen de archivos antes de hacer push, solo con los que entran en el commit, y pide la confirmación. Si el push falla por permisos, explica en simple que el TL da los accesos.

```
diseno(riego): convierte el mockup del panel de riego

Vistas: design/vistas/riego/panel.html, design/vistas/riego/historial.html
Tickets: SEM-14
```

### 10. Informe

Cierra con el informe en el chat, con `references/plan.md`, sección "Informe": plan ejecutado, decisiones de tokens y los valores pendientes de decisión, escenarios que salieron de controles de prototipo, lo que no tiene equivalente y cómo quedó (cada lógica JS como criterio para su ticket), variante elegida si había varias, inventario por vista con quién lo revisó, capturas o la mención de que se verificó sin render, y lo que no se pudo ver. Termina sugiriendo correr `checklist-diseno` sobre las vistas nuevas antes de la planificación, y `spec-a-tickets` para las vistas sin ticket que se vayan a construir. Nombra las skills como figuran en tu lista de skills: instaladas como plugin de Claude Code son `flujo-diseno:checklist-diseno` y `flujo-diseno:spec-a-tickets`; con `npx skills`, `checklist-diseno` y `spec-a-tickets`.
