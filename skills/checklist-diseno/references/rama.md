# Rama y push

Qué hacer cuando `rama.py` o `git` no dejan guardar: el arreglo que propones, la orden de `rama.py` que lo aplica con el sí de la persona y qué vuelves a correr antes de seguir. Lo lees desde el paso de `SKILL.md` que corre `rama.py`.

## Contenido

- Antes de proponer
- Error de rama.py
- Trabajo por apartar
- El commit de la skill
- Sin servidor
- Sin rama principal
- Push sin credenciales
- Rama nueva
- Rama nueva rechazada
- Pedido al TL

---

## Antes de proponer

Quien opera la skill es de producto o de diseño y no arregla git a mano: cada caso de abajo trae un arreglo, y nada se escribe en el repositorio hasta que `rama.py` devuelva `guardar`. Explica en simple el `detalle`, propón el arreglo y aplícalo solo con el sí. Sin el sí, o si el arreglo no se puede hacer desde la sesión, di qué quedó sin hacer: qué iba a guardar la skill y dónde está ahora, en el chat, en la carpeta de trabajo o en un commit que existe solo en esta máquina.

Hasta el commit, los cambios de rama, los apartados y el commit mismo los hace `rama.py`, no tú: no corras `git switch`, `git stash`, `git reset` ni `git commit` por tu cuenta. Después del commit, el push y la rama nueva van como dice `SKILL.md`. `apartar` y `volver` van con los mismos argumentos que la orden de `revisar` que corriste (`--tipo`, `--epica` o `--mockup` y `--epicas`, y `--repo` si la llevaba), y devuelven un JSON con una `accion`, como `revisar`: sigue con esa.

## Error de rama.py

Si `rama.py` sale con error o no devuelve un JSON, antes de escribir nada en el repositorio corre `git --version`: el error de un `git` que falta no siempre lo nombra, como en Windows, donde dice solo que no encontró un archivo.

- Si `git --version` no responde, falta git: propón instalarlo, con `winget install Git.Git` en Windows, `brew install git` en macOS (o `xcode-select --install` sin Homebrew), y el gestor del sistema en Linux, como `sudo apt install git` o `sudo dnf install git`. Con el sí, instálalo y repite `git --version`; si responde, vuelve a correr la orden de `rama.py`. En Windows la terminal ve `git` recién al reabrirla: si la prueba sigue fallando después de instalar, di que hay que reabrir la sesión y qué quedó sin hacer. Sin el sí, di qué quedó sin hacer.
- Si el error es del nombre (mayúsculas, espacios, `/`, o un final en guion y número como `fase-2`, que se confunde con el sufijo de la rama), propón uno que sirva, en minúsculas y con guiones, por ejemplo `fase-dos` en lugar de `fase-2`, y úsalo también en las rutas de la épica, como `specs/<épica>/`. Con el sí, vuelve a correr la orden con ese nombre. Sin el sí, di qué quedó sin hacer.
- Detente. Con otro error, o con el motivo `error-de-git`, explica en simple qué dice; con `error-de-git`, di también en qué rama quedaste y qué quedó apartado (`apartado`). Si tiene arreglo, como una identidad de git que falta, propón cómo y, con el sí, arréglalo y vuelve a correr la orden. Si el error no se puede arreglar desde la sesión, di qué quedó sin hacer y, si es del servidor, redacta el pedido al TL; cuando esté resuelto, vuelve a correr la orden. Sin el sí, di qué quedó sin hacer.

## Trabajo por apartar

Detente. Con los motivos `cambios-sin-guardar`, `otra-rama`, `sin-rama`, `commits-sin-empujar` y `principal-adelantada`, lo que hay en la copia entraría en el commit o en el push de la skill, o la copia no está en una rama de este trabajo. Explica en simple en qué rama estás y qué hay ahí que no está en el servidor, con los `archivos` y los `commits` del JSON, y propón apartarlo en una rama propia y guardar desde la rama del flujo. Con el sí, corre la misma orden de `rama.py` con `apartar` en lugar de `revisar`: guarda lo que había en `apartado/<rama>`, vuelve a la rama del flujo y vuelve a correr la revisión desde ahí. Sin el sí, queda detenida sin escribir en el repositorio y di qué quedó sin hacer. No uses `git stash`: lo que se aparta así no queda en ninguna rama y producto no lo encuentra después.

Di dónde quedó lo anterior: en las ramas de `apartado`, que existen solo en esta máquina, o, si la lista viene vacía, en `desde`, donde siguen sus commits.

Con `elegir`, el servidor tiene más de una rama de este trabajo: muestra las `ramas`, pregunta en cuál guardar y corre otra vez `apartar` con `--rama <la elegida>`.

## El commit de la skill

Después de `git add` de lo que escribió la skill, haz el commit con `rama.py`, con un `-m` por párrafo del mensaje y, después de `--`, las mismas rutas que pasaste a `git add`:

```
<intérprete> -B <ruta-de-esta-skill>/scripts/rama.py commit -m "<mensaje>" -- <agregadas>
```

El commit lleva solo esas rutas, que tienen que estar dentro de `design/`, `specs/`, `.gitignore` o `.claude/pm-conventions.md`: un archivo que otra persona dejó preparado fuera de ellas no entra. Con `empujar`, los `archivos` son los del commit, los que lista el resumen; sigue con el push. Con `sin-cambios`, no hubo nada que guardar: no hay commit ni push, y el resumen lo dice.

## Sin servidor

Detente. Con el motivo `sin-servidor`, si el `detalle` dice que el repositorio no tiene un servidor `origin` configurado, la skill no tiene adónde guardar, y dónde vive el repositorio y quién tiene acceso lo decide el TL: el arreglo no se puede hacer desde la sesión. Redacta el pedido al TL (sección "Pedido al TL") y di qué quedó sin hacer. Cuando el TL configure el servidor, vuelve a correr la misma orden de `rama.py`.

Detente. Si el `detalle` dice que git no pudo hablar con el servidor, explica en simple el mensaje de git: suele ser la red, la VPN o el certificado del servidor. Propón probar de nuevo, y con el sí vuelve a correr la misma orden de `rama.py`. Si sigue fallando, el arreglo no se puede hacer desde la sesión: redacta el pedido al TL con el mensaje de git y di qué quedó sin hacer; cuando el TL lo resuelva, vuelve a correr la orden.

## Sin rama principal

Detente. Con el motivo `sin-principal`, el servidor no dice cuál es su rama principal, y eso se configura en el servidor: no se puede hacer desde la sesión. Redacta el pedido al TL y di qué quedó sin hacer. Cuando el TL lo configure, vuelve a correr la misma orden de `rama.py`.

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
