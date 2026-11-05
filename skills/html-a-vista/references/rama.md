# Rama y push

Qué hacer cuando `rama.py` o `git` no dejan guardar: el arreglo que propones, cómo lo aplicas con el sí de la persona y qué chequeo repites antes de seguir. Lo lees desde el paso de `SKILL.md` que corre `rama.py`.

## Contenido

- Antes de proponer
- Error de rama.py
- Otra rama o trabajo sin guardar
- Sin servidor
- Sin rama principal
- Volver que falla
- Push sin credenciales
- Rama nueva
- Rama nueva rechazada
- Pedido al TL

---

## Antes de proponer

Quien opera la skill es de producto o de diseño y no arregla git a mano: cada caso de abajo es una detención con un arreglo que haces tú. No escribas en el repositorio hasta que `rama.py` devuelva `guardar` o `volver`. Explica en simple qué pasa, propón el arreglo y aplícalo solo con el sí; después vuelve a correr la misma orden de `rama.py` y sigue con lo que devuelva. Sin el sí, o si el arreglo no se puede hacer desde la sesión, queda detenida y di qué quedó sin hacer: qué iba a guardar la skill y dónde está ahora, en el chat, en la carpeta de trabajo o en un commit que existe solo en esta máquina.

## Error de rama.py

Si `rama.py` sale con error o no devuelve un JSON, detente sin escribir en el repositorio. Si el error es del nombre (mayúsculas, espacios, `/`, o un final en guion y número como `fase-2`, que se confunde con el sufijo de la rama), propón uno que sirva, en minúsculas y con guiones, por ejemplo `fase-dos` en lugar de `fase-2`, y úsalo también en las rutas de la épica, como `specs/<épica>/`. Con el sí, vuelve a correr la orden con ese nombre. Si el error dice que no encuentra `git`, o `git --version` no responde, propón instalarlo: `winget install Git.Git` en Windows, `brew install git` en macOS (o `xcode-select --install` sin Homebrew), y el gestor del sistema en Linux, como `sudo apt install git` o `sudo dnf install git`. Con el sí, instálalo y repite `git --version`; si responde, vuelve a correr la orden de `rama.py`. En Windows la terminal ve `git` recién al reabrirla: si la prueba sigue fallando después de instalar, di que hay que reabrir la sesión. Con otro error, explica en simple qué dice; si se puede arreglar desde la sesión, propón cómo y, con el sí, arréglalo y vuelve a correr la orden. Sin el sí, o si no se puede arreglar desde la sesión, queda detenida y di qué quedó sin hacer.

## Otra rama o trabajo sin guardar

Motivos `otra-rama`, `sin-rama`, `commits-sin-empujar` y `cambios-sin-guardar`: la copia está en una rama que no es la principal ni una de este trabajo, en ninguna rama, en una rama que ya no está en el servidor y tiene commits que el servidor no tiene, o con cambios sin guardar. Detente, explica en simple en qué rama estás y qué hay ahí que no está en el servidor, y propón apartarlo en una rama propia y guardar desde la principal. Sin el sí, queda detenida sin escribir en el repositorio y di qué quedó sin hacer. No uses `git stash`: lo que se aparta así no queda en ninguna rama y producto no lo encuentra después.

Con el sí, desde el repositorio de diseño:

1. Mira los cambios con `git status --short`. Los que no empiezan con `??` son de archivos que el repositorio ya sigue; los que empiezan con `??` no se agregan, porque no son del repositorio y pueden ser la instalación de las skills (`.agents/`, `.claude/skills/`).
2. Si hay cambios de archivos que el repositorio sigue, o el motivo es `sin-rama`, crea la rama del apartado donde estás, con `git switch -c apartado/<rama>`: `<rama>` es la rama actual con cada `/` cambiada por `-`, o `sin-rama`, y si ese nombre ya existe, agrega `-2`, `-3`. Si hay cambios, guárdalos ahí con `git add -u` y `git commit -m "Apartado: lo que había en <rama> antes de guardar"`. Si no hay cambios y la copia está en una rama, no hace falta apartar nada: sus commits siguen en esa rama.
3. Busca la rama principal del servidor con `git symbolic-ref --short refs/remotes/origin/HEAD`, sin el `origin/` del comienzo; si no responde, la nombra la línea de HEAD de `git remote show origin`. Corre `git switch <principal>` y `git pull --ff-only`.
4. Vuelve a correr la misma orden de `rama.py` y sigue con la `accion` que devuelva.

Di dónde quedó lo anterior: en `apartado/<rama>` con sus archivos, o en `<rama>` si no hubo que apartar nada, y que una rama que creaste tú existe solo en esta máquina. Si un comando falla y el arreglo no se puede hacer desde la sesión, queda detenida: di en qué rama quedaste, qué quedó apartado y qué quedó sin hacer.

## Sin servidor

Motivo `sin-servidor`. Si el `detalle` dice que el repositorio no tiene un servidor `origin` configurado, la skill no tiene adónde guardar, y dónde vive el repositorio y quién tiene acceso lo decide el TL: el arreglo no se puede hacer desde la sesión. Detente, redacta el pedido al TL (sección "Pedido al TL") y di qué quedó sin hacer. Cuando el TL configure el servidor, vuelve a correr la misma orden de `rama.py`.

Si el `detalle` dice que git no pudo hablar con el servidor, explica en simple el mensaje de git: suele ser la red, la VPN o el certificado del servidor. Propón probar de nuevo, y con el sí vuelve a correr la misma orden de `rama.py`. Si sigue fallando, el arreglo no se puede hacer desde la sesión: queda detenida, redacta el pedido al TL con el mensaje de git y di qué quedó sin hacer.

## Sin rama principal

Motivo `sin-principal`: el servidor no dice cuál es su rama principal, y eso se configura en el servidor, no desde la sesión. Detente, redacta el pedido al TL y di qué quedó sin hacer. Cuando el TL lo configure, vuelve a correr la misma orden de `rama.py`.

## Volver que falla

Con `volver`, si `git switch <principal>` falla porque hay cambios sin guardar que chocan con la principal, es el caso de "Otra rama o trabajo sin guardar": detente y propón apartarlos con esos pasos, y con el sí sigue desde el paso 1. Sin el sí, queda detenida y di qué quedó sin hacer.

Si `git pull --ff-only` falla porque la principal de esta copia tiene commits que el servidor no tiene, detente y propón apartarlos. Con el sí, `git branch apartado/<principal>` los deja en una rama propia, `git switch -C <principal> origin/<principal>` deja la principal como está en el servidor, y vuelves a correr la misma orden de `rama.py`. Sin el sí, queda detenida y di qué quedó sin hacer. Si falla por otro motivo, como la red, sigue "Sin servidor".

## Push sin credenciales

Si `git push` falla por credenciales, porque el servidor no reconoce el usuario o el token, el arreglo no se puede hacer desde la sesión: los accesos los da el TL. Detente y di qué quedó sin hacer: el commit existe solo en esta máquina, en la rama actual, con los archivos que lista `git show --stat --oneline HEAD`. Redacta el pedido al TL con el mensaje de git. Cuando el TL dé el acceso, vuelve a correr `git push` y confirma con `git status -sb` que la rama quedó igual que en el servidor.

## Rama nueva

Con `rama-nueva`, `SKILL.md` dice qué comandos pasan el commit a la rama nueva. Antes de correrlos, explica en simple que el servidor no aceptó el cambio en esa rama y propón pasarlo a `rama_nueva`, donde el TL lo revisa en un merge request. Con el sí, córrelos y vuelve a correr `git status -sb` para confirmar que la rama nueva quedó igual que en el servidor. Sin el sí a la rama nueva, queda detenida y di qué quedó sin hacer: el commit existe solo en esta máquina, en la rama actual. Si `git switch -c <rama_nueva>` o `git push -u origin <rama_nueva>` fallan, queda detenida, di en qué rama quedó el commit y qué quedó sin hacer; si es por credenciales, sigue "Push sin credenciales", que no se arregla desde la sesión.

## Rama nueva rechazada

`parar` después de un rechazo, con el motivo `rama-nueva-rechazada`: el servidor no aceptó tampoco la rama nueva, y crear ramas en el servidor es un permiso que da el TL, no algo que se arregla desde la sesión. Detente, di qué quedó sin hacer (el commit existe solo en esta máquina, en la rama actual) y redacta el pedido al TL. Cuando el TL dé el permiso, vuelve a correr `git push -u origin <rama_nueva>`, con la rama actual como `<rama_nueva>`.

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
