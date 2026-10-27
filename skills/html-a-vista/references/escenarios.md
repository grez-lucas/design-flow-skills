# Escenarios, render y capturas

Cómo los estados del mockup pasan a escenarios de la vista, y cómo se usa el navegador cuando la sesión lo tiene.

## Contenido

- Controles de prototipo
- data-state del mockup
- Escenarios base y globales
- Render
- Capturas

---

## Controles de prototipo

Un control de prototipo es un botón, menú, selector o barra dentro de la pantalla que solo sirve para cambiar de caso: "DEMO", "Simular espera", "Salir de demo", "ver como persona natural", un `<select>` de "plan vigente / plan expirado". El script los lista como candidatos por texto y por nombre de función (`demoSet`, `simularError`, `DEMO_MODES`, `setMode`).

- Cada estado que activa es un escenario en `data-escenarios`, con nombre en minúsculas y guiones (`sensor-sin-senal`, `plan-vencido`), y los bloques que cambian llevan `data-state`.
- Para saber qué cambia, lee la función que el control llama: qué clases pone en `<body>`, qué textos reemplaza, qué bloques muestra.
- El control no pasa a la vista. Los escenarios se cambian desde el panel de `proto.js`, fuera de la pantalla, para que DEV no confunda andamio con producto.
- Si el texto es una función del producto ("Simulación de ataques" como servicio que se vende), no es un control de prototipo: queda.

## data-state del mockup

Si el mockup ya usa `data-state` con otro significado (el estado de un chip, "full", "partial", "off"), renómbralo en la vista (`data-nivel`, una clase o un modificador del componente) y no lo uses como escenario: `proto.js` lee todo `data-state` como escenario y escondería ese elemento.

## Escenarios base y globales

- Los base que el mockup no tiene (vacío, cargando, error, sin permiso, muchos datos) se escriben desde el spec, con textos completos. Uno que no aplica va en `data-no-aplica` con su motivo.
- Un escenario que el mockup sincroniza entre módulos lleva el mismo nombre en cada vista donde aplica, el que fijó la ola 1 en `escenarios-globales.md`. `proto.js` no cambia: con el nombre compartido, `?escenario=<nombre>` abre cada vista en el mismo caso.

## Render

Con navegador, para un framework por CDN o para el inventario contra el DOM:

```
google-chrome --headless=new --disable-gpu --virtual-time-budget=10000 --dump-dom "file://<trabajo>/partes/<parte>.html" > <trabajo>/render/<parte>.html
```

`--dump-dom` no entra a los iframes: renderiza cada parte suelta, que el script dejó abrible sola. Con Playwright, `page.content()` después de cargar, o `page.frames` para un mockup compuesto sin partir.

Para un framework por CDN, después del render vuelve a desarmar el DOM en otra carpeta (`desarmar.py <trabajo>/render/<parte>.html <trabajo>/render-desarmado`) y convierte desde ahí: el estado inicial renderizado es la pantalla. Los colores de las clases utilitarias se leen con `getComputedStyle` en el navegador o se deducen del nombre de la clase (`text-red-600`), y van a tokens como cualquier valor. La vista no lleva el framework, ni CDN, ni JS propio.

## Capturas

Con navegador, una captura por escenario de cada vista y una del original en el estado más cercano:

```
google-chrome --headless=new --disable-gpu --window-size=1440,900 --screenshot=<trabajo>/capturas/<vista>-<escenario>.png "file://<repo>/design/vistas/<épica>/<vista>.html?escenario=<escenario>&proto=0"
google-chrome --headless=new --disable-gpu --window-size=1440,900 --screenshot=<trabajo>/capturas/<vista>-original.png "file://<trabajo>/partes/<parte>.html"
```

El original solo se captura en su estado inicial, salvo que la sesión tenga Playwright para hacer clic en el control que abre cada estado. El informe pone las capturas lado a lado (ruta del original y de la vista por escenario) y dice qué estados del original no se capturaron.

Sin navegador, el inventario es la única verificación y el informe dice "la verificación se hizo sin render".
