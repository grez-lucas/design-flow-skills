# Rondas en Lavish

Cómo llevar cada ronda del grilling en un artefacto de Lavish.

## Archivo

Un archivo por requerimiento, que se actualiza en cada ronda: `.lavish/grilling-<épica>.html` en el directorio de trabajo. Parte de `assets/ronda.html`, que ya trae los estilos, una tarjeta de pregunta de ejemplo y el botón para copiar respuestas.

Antes de escribir el primer artefacto, abre la guía de formularios de Lavish:

```
npx -y lavish-axi playbook input
```

Y si vas a dibujar el flujo entre pantallas, también la de diagramas:

```
npx -y lavish-axi playbook diagram
```

## Contenido de cada ronda

1. Arriba, las decisiones de las rondas anteriores, en una línea por ronda, para que la persona vea qué quedó fijado.
2. El diagrama del flujo entre pantallas, si el requerimiento tiene flujo. Cajas con el nombre de la pantalla y flechas con la acción que lleva de una a otra. Nada de bocetos de pantalla.
3. Las preguntas de la ronda, numeradas, una tarjeta por pregunta, con sus opciones como radio o casillas, la recomendada marcada, un campo de nota y un botón "Encolar P<n>".
4. Al final, la instrucción de encolar y enviar con "Send to Agent", y el botón "Copiar todas las respuestas" para cuando se abre sin Lavish.

En la ronda de cierre, reemplaza las preguntas por el resumen de decisiones y una tarjeta "¿Llegamos a un entendimiento compartido?" con dos opciones: confirmar, o decir qué falta.

## Comandos

Abre la sesión:

```
npx -y lavish-axi .lavish/grilling-<épica>.html
```

Espera las respuestas. El comando queda en silencio hasta que la persona envía: no lo mates. Si la herramienta tiene límite de tiempo para comandos, córrelo en segundo plano; si se corta, vuelve a correrlo, las respuestas no se pierden.

```
npx -y lavish-axi poll .lavish/grilling-<épica>.html
```

Aplica las respuestas, actualiza el mismo archivo con la ronda siguiente y responde dentro de Lavish mientras vuelves a esperar:

```
npx -y lavish-axi poll .lavish/grilling-<épica>.html --agent-reply "Ronda 2 aplicada; recarga para la ronda 3."
```

Cuando la persona confirma el entendimiento compartido, cierra:

```
npx -y lavish-axi end .lavish/grilling-<épica>.html
```

Si la persona cierra la sesión desde el navegador, no la reabras por tu cuenta: sigue en el chat.

## Si Lavish no arranca

Dilo en una línea y sigue en el chat con el formato de preguntas de `SKILL.md`. No reintentes en bucle.
