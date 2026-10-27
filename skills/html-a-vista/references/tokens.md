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

1. Lo que está dentro del umbral va al token que el script indica, sin preguntar.
2. Lo que queda fuera va a la tabla que muestras a producto: valor, ocurrencias, token más cercano, distancia, usos y una propuesta de token nuevo con nombre de la convención. Agrupa las filas que comparten token más cercano y las variantes de opacidad de un mismo color, para que la tabla se lea de un vistazo.
3. Pregunta a producto y espera: elige por fila el token cercano o el token nuevo. Escribe en `tokens.css` solo los nuevos que aprobó.
4. Si producto acepta tu recomendación sin elegir, o no decide, usa el token existente más cercano y deja el valor como pendiente de decisión en el informe. Nunca agregues un token que producto no aprobó.

## Sin tokens.css

```
python3 -B <skill>/scripts/tokens.py consolidar <trabajo>/trozos/*/estilos*.css
```

El script agrupa los colores por color base dentro del umbral (las opacidades quedan anotadas en cada grupo), lleva espacios, radios y medidas fijas a múltiplos de 4 px y junta tamaños de letra a 1 px o menos. Es la base mecánica; sobre ella:

1. Nombra cada grupo por uso con los prefijos de la convención (`references/design-system.md` de `spec-a-html`): `--color-bg`, `--color-surface`, `--color-text-muted`, `--color-primary`. Los usos que lista el script (`background`, `color`, `border-color`) ayudan a decidir.
2. Junta grupos que cumplen el mismo uso aunque estén fuera del umbral (diez grises para texto secundario son un token). Eso es una decisión de diseño: va en la tabla.
3. Una opacidad que se repite como fondo de superposición puede ser un token propio (`--color-overlay`); las demás se resuelven con el color base.
4. Muestra la tabla de consolidación (valor original, ocurrencias, token) antes de escribir `tokens.css`, y completa lo que el mockup no define con la plantilla `assets/tokens.css` de `spec-a-html`, diciéndolo.

## Tema oscuro

Si el mockup tiene tema claro y oscuro (bloques `[data-theme="dark"]`, `.dark` o `prefers-color-scheme` en el manifiesto), el claro va en `:root` y el oscuro en `[data-theme="dark"]`, que redefine solo `--color-*`. Mapea los valores del tema oscuro contra los tokens del bloque oscuro. Si el mockup abre en oscuro, igual el claro va en `:root`: `proto.js` abre en claro y suma el control de tema cuando `tokens.css` define el oscuro.

## Verificar antes de escribir

```
python3 -B <skill>/scripts/tokens.py verificar design/tokens.css <trabajo>/ola-1/tokens/tokens.css
```

Sale con 1 si un token nuevo queda dentro del umbral de uno existente. Si pasa, o lo reemplazas por el existente o producto lo aprobó sabiendo que es casi igual, y lo dices en el informe.
