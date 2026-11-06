# Navegador

Cómo saber si la sesión tiene un navegador que de verdad abre, y cómo instalarlo con el sí de la persona cuando falta. Lo lees desde el paso de `SKILL.md` que saca capturas o renderiza.

## Probar

Un navegador cuenta solo si abre y saca una captura: que el paquete esté instalado no alcanza. Busca el binario, en este orden, y usa el primero que exista como `<navegador>`:

- `command -v google-chrome chromium chromium-browser`, que en Linux nombra el que está.
- En macOS, `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`, entre comillas en cada orden.
- En Windows, `C:\Program Files\Google\Chrome\Application\chrome.exe`, entre comillas en cada orden.

Con él, saca una captura de prueba en la carpeta de trabajo:

```
<navegador> --headless=new --disable-gpu --window-size=390,900 --screenshot=<trabajo>/prueba.png "about:blank"
```

Hay navegador si `<trabajo>/prueba.png` existe y no está vacío. El Chromium de snap (`/snap/bin/chromium`), el que Ubuntu instala con `apt install chromium`, no ve `/tmp`, donde suele estar la carpeta de trabajo: ahí la captura no sale, y lo que falta es el navegador de "Instalar". En las órdenes de captura y de render de `SKILL.md` y de sus `references/`, `<navegador>` va donde dice `google-chrome`.

Si no hay binario pero la sesión tiene Playwright para Python, la prueba es abrir su Chromium, porque el paquete puede estar instalado sin el navegador:

```
<intérprete> -B -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); p.chromium.launch().close(); p.stop()"
```

Si sale sin error, hay navegador por Playwright.

## Instalar

Sin navegador, propón instalar Chromium o Google Chrome con el gestor del sistema. No uses `pip`: en Debian, en Ubuntu y en el Python de Homebrew rechaza instalar paquetes fuera de un entorno virtual. La orden según la plataforma:

- Debian: `sudo apt install chromium`.
- Ubuntu: Google Chrome en `.deb`, porque el Chromium de Ubuntu viene por snap y no ve `/tmp`. Bájalo con `wget -O <trabajo>/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb` e instálalo con `sudo apt install <trabajo>/chrome.deb`, que deja `google-chrome` en el PATH. El `.deb` es solo para equipos x86 de 64 bits; en ARM, la carpeta de trabajo va en una carpeta no oculta de `$HOME`, que el Chromium de snap sí ve.
- Fedora: `sudo dnf install chromium`.
- macOS: `brew install --cask google-chrome`.
- Windows: `winget install Google.Chrome`.

Con el sí, instálalo y repite la prueba de "Probar". Si pasa, sigue con el paso que te trajo.

Detente. Si la orden lleva `sudo` y pide una contraseña que la sesión no puede escribir, o la prueba sigue fallando después de instalar, eso no se arregla desde la sesión: entrégale a la persona la orden lista para copiar, para que la corra en su terminal, di qué quedó sin hacer y sigue lo que `SKILL.md` dice para cuando no hay navegador; cuando la haya corrido, vuelve a correr la prueba.
