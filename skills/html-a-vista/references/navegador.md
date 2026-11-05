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

Hay navegador si `<trabajo>/prueba.png` existe y no está vacío. En las órdenes de captura y de render de `SKILL.md` y de sus `references/`, `<navegador>` va donde dice `google-chrome`.

Si no hay binario pero la sesión tiene Playwright para Python, la prueba es abrir su Chromium, porque el paquete puede estar instalado sin el navegador:

```
<intérprete> -B -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); p.chromium.launch().close(); p.stop()"
```

Si sale sin error, hay navegador por Playwright.

## Instalar

Sin navegador, propón instalar Chromium o Google Chrome con el gestor del sistema. No uses `pip`: en Debian, en Ubuntu y en el Python de Homebrew rechaza instalar paquetes fuera de un entorno virtual. La orden según la plataforma:

- Debian: `sudo apt install chromium`.
- Ubuntu: `sudo snap install chromium`.
- Fedora: `sudo dnf install chromium`.
- macOS: `brew install --cask google-chrome`.
- Windows: `winget install Google.Chrome`.

Con el sí, instálalo y repite la prueba de "Probar". Si pasa, sigue con el paso que te trajo. Si la orden pide una contraseña de administrador que la sesión no puede dar, o la prueba sigue fallando después de instalar, eso no se arregla desde la sesión: di qué quedó sin hacer y sigue lo que `SKILL.md` dice para cuando no hay navegador. Cuando la persona lo instale por su cuenta, vuelve a correr la prueba.
