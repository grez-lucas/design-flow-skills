# Plan e informe

Cómo se arma el plan que producto aprueba antes de lanzar subagentes, y cómo se escribe el informe final.

## Contenido

- Leer el resumen
- Tabla pantalla a vista
- Subagentes por ola
- Ejemplo de plan
- Informe

---

## Leer el resumen

`resumen.md` trae por parte su origen (líneas del archivo original), su título, los tokens de su CSS, JS y markup, los bloques de variables, las animaciones, las pantallas y superposiciones con su trozo y el título que muestran, los controles candidatos a prototipo, los `data-state` existentes, los valores sueltos más frecuentes y los recursos externos.

- **Pantalla**: un trozo de clase `pantalla` es candidato a vista. Uno que dice "contiene" tiene subpantallas: decide si son pestañas de una vista (escenarios) o vistas propias según el spec.
- **Superposición**: modal, drawer, popover u overlay. Es un escenario de la vista que lo abre. Para saber cuál lo abre, busca su id en el JS y en los `onclick` con grep.
- **Resto**: el markup fuera de pantallas, normalmente el marco (cabecera, navegación lateral). En un documento único va en cada vista; en un mockup compuesto es el shell.
- **El JS arma markup**: si el resumen lo dice, parte del contenido (modales, reportes, filas) solo se ve leyendo el JS. Asigna esos strings a la vista que los muestra.
- **Controles candidatos**: son candidatos, no certezas. Un texto como "Simulación de ataques" puede ser una función del producto. Confírmalo leyendo el control.

Un trozo que pasa el tope de lectura ya viene partido por el script (`.1`, `.2`, o una pantalla separada en sus subpantallas más un `.marco`). Si un subagente necesitaría leer más que el tope sumando trozos, parte su trabajo en dos antes de mostrar el plan.

## Tabla pantalla a vista

| Pantalla | Vista | Archivo | Épica | Escenarios | Origen |
| :--- | :--- | :--- | :--- | :--- | :--- |
| "Panel de riego" | Panel | `design/vistas/riego/panel.html` | riego (spec) | normal, vacio, cargando, error, sin-permiso, muchos-datos, sensor-sin-senal (DEMO), confirmar-riego (modal `riego-modal`) | `documento/markup/panel-page.html`, `riego-modal.html` |

- La columna "Pantalla" lleva, entre comillas, el título que la pantalla muestra en el mockup, el que `resumen.md` pone junto a su trozo ("Inventario de semillas", no "Lista de lotes"). La fila del marco lleva el nombre del producto que muestra la cabecera, el título del `_resto`. Así producto reconoce cada fila sin abrir el mockup; un nombre inventado obliga a adivinar a qué pantalla se refiere.
- La épica sale del spec. En un mockup compuesto, una por módulo.
- Escenarios: los base (normal, vacio, cargando, error, sin-permiso, muchos-datos), los de controles de prototipo, uno por superposición que se muestre, y los del spec que el mockup no tiene, que la vista escribe desde el spec. Un base que no aplica se dice con su motivo.
- Un escenario que el mockup sincroniza entre módulos (por ejemplo, el estado de una integración que el shell propaga) lleva el mismo nombre en cada vista donde aplica, y el spec lo lista una vez como global.
- Variantes A, B y C de una pantalla: una fila, con la variante que producto elija.

## Subagentes por ola

| Ola | Quién | Lee | Tokens estimados |
| :--- | :--- | :--- | :--- |
| 1 | Tokens: tú, con `tokens.py` | salida de `tokens.py` | suma de lo que lee |
| 1 | Subagente de componentes base | CSS del shell o de la parte más compartida | |
| 1 | Subagente del shell y escenarios globales | markup y JS del shell o del resto, funciones de modo | |
| 2 | Subagente de la vista `<vista>`, una fila por vista | sus trozos, tokens y componentes de la ola 1 | |
| 3 | Integración: tú | salida de `inventario.py` y `revisar.py`, capturas | |
| 3 | Subagente revisor | inventario, contrato, capturas y spec de cada vista | |

La ola 2 tiene tantas filas como vistas tiene la tabla pantalla a vista: así producto ve que nadie arma dos vistas a la vez. Los tokens estimados salen del manifiesto (bytes/4, con el margen que declara). Ningún subagente debería pasar unos 50 mil tokens de lectura; si una vista pasa, se parte en dos subagentes.

## Ejemplo de plan

```
Mockup: panel-riego.html, 1 parte, 2 pantallas, 1 modal, 3 controles DEMO.

| Pantalla | Vista | ... |

Olas: 1) tokens (yo, con el script), componentes y marco (2 subagentes); 2) panel e historial (2 subagentes, uno por vista); 3) integración (yo) y revisor (1 subagente).
Tokens: el mockup tiene 41 colores; 30 van a tokens existentes, 11 quedan para que elijas.
Sin equivalente: el pulso del indicador queda como comentario; el filtro por zona, como criterio para SEM-14.
¿Sigo?
```

## Informe

En el chat, en este orden. En las pruebas, el mismo texto va a `notas.md`.

1. **Resultado**: vistas creadas por épica, archivos de design system que cambiaron, commit.
2. **Plan ejecutado**: la tabla final y las olas, con cambios respecto del plan aprobado. Cada pantalla se nombra con el título que muestra el mockup, como en el plan.
3. **Tokens**: el mapa o la consolidación, en una tabla corta. Cuando un valor va a un token que no es igual, la fila dice el valor del token (1100px a `--size-content-max`, 1200px): producto ve cuánto cambia la pantalla. Cada valor fuera del umbral que producto no decidió va como un ítem que empieza por "Pendiente de decisión:", con el valor, el token que se usó mientras tanto y la propuesta de token nuevo.
4. **Escenarios**: los que salieron de controles de prototipo, con su control original; los `data-state` del mockup renombrados; los del spec que el mockup no tenía.
5. **Sin equivalente**: cómo quedó cada cosa. Cada lógica JS va como un ítem que empieza por "Criterio para el ticket:", con la regla en forma de "Dado, cuando, entonces" y la vista donde quedó el comentario.
6. **Fidelidad**: el inventario por vista (textos, controles, campos y estados presentes sobre el total, y lo que falta con su motivo), quién lo revisó, y las capturas lado a lado o la frase "la verificación se hizo sin render".
7. **Lo que no se pudo ver**: contenido que solo aparece interactuando, estados de un framework por CDN que no se alcanzaron.
8. **Siguiente paso**: correr `checklist-diseno` antes de la planificación, y `spec-a-tickets` para las vistas sin ticket que se vayan a construir.
