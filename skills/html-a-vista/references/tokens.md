# Mapeo a tokens

Cómo se llevan los valores del mockup a `design/tokens.css`, con o sin un design system existente.

## Contenido

- Umbrales
- Con tokens.css
- Sin tokens.css
- Tema oscuro
- Verificar antes de escribir

---

## Umbrales

`scripts/tokens.py` usa estos umbrales y los declara en su salida:

- **Color**: distancia en OKLab por 100, más la diferencia de opacidad por 100. Dentro del umbral si es 2,0 o menos, del orden de la diferencia mínima perceptible: dos colores a esa distancia se ven iguales y no justifican dos tokens.
- **Medida**: el token de la misma escala más cercano, según la propiedad (`padding`, `margin`, `gap` a `--space-*`; `font-size` a `--font-size-*`; `border-radius` a `--radius-*`; `width` y `height` a `--size-*`). Dentro si la diferencia es 1 px o el 10 % del paso, lo que sea mayor. Las medidas de 2 px o menos (bordes, anillos de foco) no se mapean.
- Las variables del mockup cuentan como valores: su categoría sale del nombre (`--pad` es espacio, `--r-sm` es radio).

## Con tokens.css

```
python3 -B <skill>/scripts/tokens.py mapear design/tokens.css <trabajo>/trozos/*/estilos*.css
```

1. Lo que está dentro del umbral va al token que el script indica, sin preguntar. Cuando la distancia no es 0, la tabla del script trae el valor del token al lado: una medida de 1100 px que va a un token de 1200 px cambia la pantalla, y el informe lo muestra igual.
2. Lo que queda fuera va a la tabla que muestras a producto: valor, ocurrencias, token más cercano, distancia, usos, selectores y una propuesta de token nuevo con nombre de la convención. Agrupa las filas por token más cercano y también por uso, y las variantes de opacidad de un mismo color, para que la tabla se lea de un vistazo. Cada fila nombra lo que ese valor pinta en el mockup, con el selector que da el script o con el texto de pantalla que lleva esa clase ("el texto de una cuota atrasada", no "texto de alerta"): dos valores que comparten token cercano pueden pintar cosas distintas, y producto decide por lo que ve.
3. Pregunta a producto y espera: elige por fila el token cercano o el token nuevo. Escribe en `tokens.css` solo los nuevos que aprobó.
4. Si producto acepta tu recomendación sin elegir, o no decide, usa el token más cercano entre los del mismo uso (fondo, texto, borde, superposición) y deja el valor como pendiente de decisión en el informe. El más cercano por distancia a veces cumple otro papel: el velo de un modal no es el color del texto, y un título verde no es texto secundario. Si ningún token sirve para ese uso, el valor no se aplica y el informe dice qué se pierde en pantalla. Nunca agregues un token que producto no aprobó.

## Sin tokens.css

```
python3 -B <skill>/scripts/tokens.py consolidar <trabajo>/trozos/*/estilos*.css
```

El script agrupa los colores por color base dentro del umbral y dentro de su tema (las opacidades quedan anotadas en cada grupo), lleva espacios, radios y medidas fijas a múltiplos de 4 px y junta tamaños de letra a 1 px o menos. Cada grupo dice su tema: `:root` (el tema por defecto, reglas que ningún selector de tema elige), `[data-theme="dark"]`, `[data-theme="light"]`, `.dark`, `@media (prefers-color-scheme: dark)`, o los dos cuando un bloque vale para dos (`:root, [data-theme="dark"]`, un mockup que abre en oscuro). El mismo valor en dos temas va en dos grupos: un blanco de fondo en el claro y un blanco de texto en el oscuro no son el mismo token. La sección "Un token con un valor por tema" lista cada rol del mockup (una variable, o un selector y su propiedad) que cambia de valor entre temas. Es la base mecánica; sobre ella:

1. Nombra cada grupo por uso con los prefijos de la convención (`references/design-system.md` de `spec-a-html`): `--color-bg`, `--color-surface`, `--color-text-muted`, `--color-primary`. Los usos que lista el script (`background`, `color`, `border-color`) ayudan a decidir.
2. Junta grupos que cumplen el mismo uso aunque estén fuera del umbral (diez grises para texto secundario son un token). Eso es una decisión de diseño: va en la tabla.
3. Una opacidad que se repite como fondo de superposición puede ser un token propio (`--color-overlay`); las demás se resuelven con el color base.
4. Un color con uso propio en pantalla (el morado de "Próximo riego") entra en la tabla como token, aunque quede lejos de los demás. "Pendiente de decisión" es solo para cuando hay un `tokens.css` previo que proteger; sin él, la tabla de consolidación es la decisión de producto, y un color que no entra en ella se pierde de la pantalla.
5. Cada fila de "Un token con un valor por tema" es un solo token con su valor en cada tema (`--color-bg` con el valor claro en `:root` y el oscuro en `[data-theme="dark"]`), no un token por tema. Si un rol tiene dos valores en el mismo tema (cada módulo con su fondo oscuro), el grupo de colores dice si se ven iguales.
6. Muestra la tabla de consolidación (tema, valor original, ocurrencias, token, y su valor en cada tema) antes de escribir `tokens.css`, y completa lo que el mockup no define con la plantilla `assets/tokens.css` de `spec-a-html`, diciéndolo.
7. Antes de escribir, revisa el archivo contra sí mismo:

   ```
   python3 -B <skill>/scripts/tokens.py verificar <trabajo>/ola-1/tokens/tokens.css
   ```

   Sale con 1 si dos tokens del mismo tema tienen valores distintos dentro del umbral, por ejemplo un fondo alterno que no se distingue del fondo (la plantilla de `spec-a-html` trae uno así). Resuelve cada par: o un token toma el valor del otro, o se separan hasta que se vean distintos. Los alias de igual valor (`--color-surface` y `--color-primary-contrast` en blanco) son intencionales y el script no los cuenta.

## Tema oscuro

Si el mockup tiene tema claro y oscuro (bloques `[data-theme="dark"]`, `.dark` o `prefers-color-scheme` en el manifiesto), el claro va en `:root` y el oscuro en `[data-theme="dark"]`, que redefine solo `--color-*`. El tema que trae cada valor en la salida de `tokens.py` dice a qué bloque va: uno con "dark" u "oscuro" al oscuro, los demás al claro. Mapea los valores del tema oscuro contra los tokens del bloque oscuro. Si el mockup abre en oscuro, igual el claro va en `:root`: `proto.js` abre en claro y suma el control de tema cuando `tokens.css` define el oscuro.

## Verificar antes de escribir

```
python3 -B <skill>/scripts/tokens.py verificar design/tokens.css <trabajo>/ola-1/tokens/tokens.css
```

Sale con 1 si un token nuevo queda dentro del umbral de uno existente. Si pasa, o lo reemplazas por el existente o producto lo aprobó sabiendo que es casi igual, y lo dices en el informe.
