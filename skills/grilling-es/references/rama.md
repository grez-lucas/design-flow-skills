# Rama y push

Qué hacer cuando `rama.py` o `git` no dejan guardar: el arreglo que propones, cómo lo aplicas con el sí de la persona y qué chequeo repites antes de seguir. Lo lees desde el paso de `SKILL.md` que corre `rama.py`.

## Contenido

- Antes de proponer
- Error de rama.py
- Antes de guardar
- El commit de la skill
- Otra rama o trabajo sin guardar
- Principal adelantada
- Sin servidor
- Sin rama principal
- Volver que falla
- Push sin credenciales
- Rama nueva
- Rama nueva rechazada
- Pedido al TL

---

## Antes de proponer

Quien opera la skill es de producto o de diseño y no arregla git a mano: cada caso de abajo trae un arreglo que haces tú, y nada se escribe en el repositorio hasta que `rama.py` devuelva `guardar` o `volver` y pase "Antes de guardar". Explica en simple qué pasa, propón el arreglo y aplícalo solo con el sí; después vuelve a correr la misma orden de `rama.py` y sigue con lo que devuelva. Sin el sí, o si el arreglo no se puede hacer desde la sesión, di qué quedó sin hacer: qué iba a guardar la skill y dónde está ahora, en el chat, en la carpeta de trabajo o en un commit que existe solo en esta máquina.

Donde dice `<rutas>`, van las que existen de `design/`, `specs/`, `.gitignore` y `.claude/pm-conventions.md`, las que la skill agrega a su commit. `<tipo>` y `<nombre>` son los de la orden de `rama.py` que corriste: el `--tipo`, y la `--epica` o, con `--mockup`, el mockup.

## Error de rama.py

Si `rama.py` sale con error o no devuelve un JSON, antes de escribir nada en el repositorio corre `git --version`: el error de un `git` que falta no siempre lo nombra, como en Windows, donde dice solo que no encontró un archivo.

- Si `git --version` no responde, falta git: propón instalarlo, con `winget install Git.Git` en Windows, `brew install git` en macOS (o `xcode-select --install` sin Homebrew), y el gestor del sistema en Linux, como `sudo apt install git` o `sudo dnf install git`. Con el sí, instálalo y repite `git --version`; si responde, vuelve a correr la orden de `rama.py`. En Windows la terminal ve `git` recién al reabrirla: si la prueba sigue fallando después de instalar, di que hay que reabrir la sesión y qué quedó sin hacer. Sin el sí, di qué quedó sin hacer.
- Si el error es del nombre (mayúsculas, espacios, `/`, o un final en guion y número como `fase-2`, que se confunde con el sufijo de la rama), propón uno que sirva, en minúsculas y con guiones, por ejemplo `fase-dos` en lugar de `fase-2`, y úsalo también en las rutas de la épica, como `specs/<épica>/`. Con el sí, vuelve a correr la orden con ese nombre. Sin el sí, di qué quedó sin hacer.
- Detente. Con otro error, explica en simple qué dice. Si tiene arreglo, propón cómo y, con el sí, arréglalo y vuelve a correr la orden. Si el error no se puede arreglar desde la sesión, di qué quedó sin hacer y, si es del servidor, redacta el pedido al TL; cuando esté resuelto, vuelve a correr la orden. Sin el sí, di qué quedó sin hacer.

## Antes de guardar

Con `guardar`, con `ofrecer` antes de crear la rama nueva, o después de volver a la principal con `volver`, mira dos cosas antes de escribir, porque las dos entrarían en el commit de la skill con su mensaje. Primero, si hay trabajo sin guardar en lo que la skill va a agregar, también archivos sin seguimiento, y si hay algo preparado en el índice, en cualquier ruta:

```
git status --porcelain --ignore-submodules=dirty -- <rutas>
git diff --cached --name-only
```

Un submódulo con cambios adentro no cuenta, porque la skill no lo agrega; uno que apunta a otro commit, sí.

Detente. Si alguna de las dos responde algo, es trabajo de otra persona o de una sesión anterior: explica qué archivos son y propón apartarlos como dice "Otra rama o trabajo sin guardar". Con el sí, apártalos y vuelve a correr la misma orden de `rama.py`. Sin el sí, queda detenida sin escribir en el repositorio y di qué quedó sin hacer.

Después, si la rama actual es la principal (la de `git symbolic-ref --short refs/remotes/origin/HEAD`, sin el `origin/` del comienzo), mira si tiene commits que el servidor no tiene:

```
git rev-list --count origin/<principal>..<principal>
```

Si da más de 0, sigue "Principal adelantada". Si no responde nada y da 0, guarda como dice "El commit de la skill".

## El commit de la skill

Haz el commit solo con las rutas que pasaste a `git add`, `<agregadas>`, para que un archivo que otra persona dejó preparado fuera de ellas no entre, aunque "Antes de guardar" no lo haya visto. El cuerpo del mensaje va con un `-m` más por párrafo:

```
git commit -m "<mensaje>" -- <agregadas>
```

## Otra rama o trabajo sin guardar

Detente. Con los motivos `otra-rama`, `sin-rama`, `commits-sin-empujar` y `cambios-sin-guardar`, y con el trabajo sin guardar de "Antes de guardar", la copia está en una rama que no es la principal ni una de este trabajo, en ninguna rama, en una rama que ya no está en el servidor y tiene commits que el servidor no tiene, o con cambios sin guardar. Explica en simple en qué rama estás y qué hay ahí que no está en el servidor, y propón apartarlo en una rama propia y guardar desde la rama del flujo. Con el sí, sigue los pasos de abajo y vuelve a correr la misma orden de `rama.py`. Sin el sí, queda detenida sin escribir en el repositorio y di qué quedó sin hacer. No uses `git stash`: lo que se aparta así no queda en ninguna rama y producto no lo encuentra después.

Con el sí, desde el repositorio de diseño:

1. Prepara lo que había y guárdalo en una rama propia. Los cambios de archivos que el repositorio ya sigue van con `git add -u`, y los archivos nuevos (`??`) de `<rutas>` con `git add -A`; los demás `??` no se agregan, porque pueden ser la instalación de las skills (`.agents/`, `.claude/skills/`, `skills-lock.json`). Lo que ya estaba en el índice entra también:

   ```
   git add -u
   git add -A -- <rutas>
   git diff --cached --quiet
   git switch -c apartado/<rama>
   git commit -m "Apartado: lo que había en <rama> antes de guardar"
   ```

   `git diff --cached --quiet` es la compuerta: si sale con 0, no quedó nada preparado, y las dos órdenes de después no van, así que no queda una rama vacía; sus commits siguen en la rama donde estabas. Con `sin-rama` la rama va igual, sin el commit si no hay nada preparado, porque guarda los commits que no están en ninguna rama. `<rama>` es la rama actual con cada `/` cambiada por `-`, o `sin-rama`, y si ese nombre ya existe, usa el primer sufijo libre (`-2`, `-3`).
2. Vuelve a la rama del flujo. Si saliste de una rama donde `rama.py` había dicho `guardar`, la del flujo es esa: vuelve con `git switch <rama>`, con su nombre de antes del apartado. Si no, mira si el servidor tiene una rama del flujo de este trabajo:

   ```
   git branch -r --list "origin/<tipo>/<nombre>" "origin/<tipo>/<nombre>-[2-9]" "origin/<tipo>/<nombre>-[1-9][0-9]" "origin/<tipo>/<nombre>-[1-9][0-9][0-9]"
   ```

   Los patrones toman la rama y sus sufijos (`-2`, `-10`) y nada más, para que otra épica que empieza igual, como `alertas-2fa` frente a `alertas`, no cuente.

   Si responde una, vuelve a ella con `git switch <tipo>/<nombre>`, sin el `origin/`: git la crea siguiendo la del servidor. Si responde más de una, muéstralas y pregunta en cuál guardar. Si no responde ninguna, la rama del flujo es la principal (la de `git symbolic-ref --short refs/remotes/origin/HEAD`, sin el `origin/`; si no responde, la nombra la línea de HEAD de `git remote show origin`): corre `git switch <principal>` y `git pull --ff-only`. Si `git pull --ff-only` falla porque la principal de esta copia tiene commits que el servidor no tiene, sigue "Principal adelantada".
3. Vuelve a correr la misma orden de `rama.py`, sigue con la `accion` que devuelva y repite "Antes de guardar".

Di dónde quedó lo anterior: en `apartado/<rama>` con sus archivos, o en `<rama>` si no hubo que apartar nada, y que una rama que creaste tú existe solo en esta máquina.

Detente. Si un comando falla y el arreglo no se puede hacer desde la sesión, di en qué rama quedaste, qué quedó apartado y qué quedó sin hacer, y vuelve a correr la misma orden de `rama.py` cuando se resuelva.

## Principal adelantada

Detente. La principal de esta copia tiene commits que el servidor no tiene, y `git push` los subiría junto con lo de la skill: muéstralos con `git log --oneline origin/<principal>..<principal>` y propón apartarlos. Con el sí, guárdalos primero en una rama propia, con el primer sufijo libre si `apartado/<principal>` ya existe, y después iguala la principal al servidor; nada se pierde, porque esos commits quedan en el apartado. Vuelve a correr `git rev-list --count origin/<principal>..<principal>`, que ahora da 0, y la misma orden de `rama.py`, y di dónde quedaron. Sin el sí, queda detenida sin escribir en el repositorio y di qué quedó sin hacer.

```
git branch apartado/<principal>
git switch -C <principal> origin/<principal>
```

## Sin servidor

Detente. Con el motivo `sin-servidor`, si el `detalle` dice que el repositorio no tiene un servidor `origin` configurado, la skill no tiene adónde guardar, y dónde vive el repositorio y quién tiene acceso lo decide el TL: el arreglo no se puede hacer desde la sesión. Redacta el pedido al TL (sección "Pedido al TL") y di qué quedó sin hacer. Cuando el TL configure el servidor, vuelve a correr la misma orden de `rama.py`.

Detente. Si el `detalle` dice que git no pudo hablar con el servidor, explica en simple el mensaje de git: suele ser la red, la VPN o el certificado del servidor. Propón probar de nuevo, y con el sí vuelve a correr la misma orden de `rama.py`. Si sigue fallando, el arreglo no se puede hacer desde la sesión: redacta el pedido al TL con el mensaje de git y di qué quedó sin hacer; cuando el TL lo resuelva, vuelve a correr la orden.

## Sin rama principal

Detente. Con el motivo `sin-principal`, el servidor no dice cuál es su rama principal, y eso se configura en el servidor: no se puede hacer desde la sesión. Redacta el pedido al TL y di qué quedó sin hacer. Cuando el TL lo configure, vuelve a correr la misma orden de `rama.py`.

## Volver que falla

Detente. Con `volver`, si `git switch <principal>` falla porque hay cambios sin guardar que chocan con la principal, propón apartarlos como dice "Otra rama o trabajo sin guardar". Con el sí, apártalos con el paso 1, vuelve a la principal y vuelve a correr la misma orden de `rama.py`. Sin el sí, queda detenida sin escribir en el repositorio y di qué quedó sin hacer.

Si `git pull --ff-only` falla porque la principal de esta copia tiene commits que el servidor no tiene, es "Principal adelantada": apártalos con el sí y vuelve a correr la misma orden de `rama.py`. Si falla por otro motivo, como la red, sigue "Sin servidor".

## Push sin credenciales

Detente. Si `git push` falla por credenciales, porque el servidor no reconoce el usuario o el token, el arreglo no se puede hacer desde la sesión: los accesos los da el TL. Di qué quedó sin hacer: el commit existe solo en esta máquina, en la rama actual, con los archivos que lista `git show --stat --oneline HEAD`. Redacta el pedido al TL con el mensaje de git. Cuando el TL dé el acceso, vuelve a correr `git push` y confirma con `git status -sb` que la rama quedó igual que en el servidor.

## Rama nueva

Detente. Con `rama-nueva`, `SKILL.md` dice qué comandos pasan el commit a la rama nueva. Antes de correrlos, explica en simple que el servidor no aceptó el cambio en esa rama y propón pasarlo a `rama_nueva`, donde el TL lo revisa en un merge request. Con el sí, córrelos y vuelve a correr `git status -sb` para confirmar que la rama nueva quedó igual que en el servidor. Sin el sí a la rama nueva, di qué quedó sin hacer: el commit existe solo en esta máquina, en la rama actual.

Detente. Si `git switch -c <rama_nueva>` falla porque esa rama ya existe en esta copia, propón pedir otra: con el sí, vuelve a correr la orden de `rama.py` con `rechazo`, que da el primer nombre libre. Si `git push -u origin <rama_nueva>` falla por credenciales, sigue "Push sin credenciales". Con cualquier otro fallo que no se puede arreglar desde la sesión, di en qué rama quedó el commit y qué quedó sin hacer, y vuelve a correr el comando que falló cuando se resuelva.

## Rama nueva rechazada

Detente. Con `parar` después de un rechazo, y el motivo `rama-nueva-rechazada`, el servidor no aceptó tampoco la rama nueva. Crear ramas en el servidor es un permiso que da el TL, y eso no se puede hacer desde la sesión. Di qué quedó sin hacer (el commit existe solo en esta máquina, en la rama actual) y redacta el pedido al TL. Cuando el TL dé el permiso, vuelve a correr `git push -u origin <rama_nueva>`, con la rama actual como `<rama_nueva>`.

## Pedido al TL

Redáctalo listo para copiar, en un bloque, en palabras que la persona pueda explicar si el TL pregunta. No propongas host ni permisos: los decide el TL.

```
Hola, <TL>. Estoy usando <skill> para guardar <qué> de la épica <épica> en el repositorio de diseño, y necesito:

- <qué falta, en una línea>
- El mensaje de git: <mensaje, si hubo>

Quedó sin guardar: <qué y dónde está ahora>. Cuando esté, vuelvo a correr la skill.
```

Qué falta, según el caso:

- Sin repositorio de diseño: un repositorio para el diseño del producto, con `design/` y `specs/` en la raíz, y acceso para empujar a quien usa la skill.
- Sin `origin`: el servidor del repositorio de diseño, configurado como `origin` en esta copia, o su dirección para configurarlo.
- Sin rama principal: que el servidor declare cuál es su rama principal.
- Credenciales: acceso para empujar al repositorio de diseño con el usuario de esta máquina.
- Rama nueva rechazada: permiso para crear ramas en el repositorio de diseño, o para empujar a la rama actual.
- Una regla que ignora `.claude/pm-conventions.md` fuera del `.gitignore` de la raíz: que deje de ignorarlo, con la línea que mostró `git check-ignore -v`.
