#!/usr/bin/env python3
"""Genera el mockup grande de las pruebas de html-a-vista: un shell y tres módulos, sobre 256 KB.

Uso: python3 pruebas/html-a-vista/generar.py <carpeta-de-salida>
Escribe <carpeta>/grande.html. Es determinista: la misma versión del script da el mismo archivo, así que
grade.py puede comparar el md5. Los módulos van como documentos completos en <script type="text/plain">
(con </script> escapado como <\\/script>) y el shell los monta en <iframe srcdoc>. Cada módulo tiene sus
propias variables CSS, abre en tema oscuro con el claro definido, y el shell sincroniza entre módulos el
escenario de la báscula desconectada desde un menú DEMO.
"""
import random
import sys
from pathlib import Path

NOMBRES = ["Tomás Aguilera", "Valentina Soto", "Joaquín Ferrada", "Isidora Muñoz", "Bruno Lagos", "Paula Rivas",
           "Martina Cáceres", "Benjamín Ortega", "Florencia Vidal", "Agustín Rojas", "Antonia Pizarro", "Vicente Lillo"]
CULTIVOS = ["Tomate cherry", "Lechuga costina", "Zapallo italiano", "Acelga", "Poroto verde", "Albahaca", "Cilantro",
            "Betarraga", "Zanahoria", "Haba", "Arveja", "Pimentón", "Kale", "Rúcula", "Cebollín"]
NOTAS = ["Guardar en frasco hermético y lejos de la luz", "Sembrar en almácigo antes de trasplantar", "Revisar humedad del sobre cada mes",
         "Variedad local adaptada a heladas suaves", "Germinación probada en marzo con buen resultado", "Separar 50 g para el intercambio de primavera"]
ORIGENES = ["Intercambio de otoño", "Donación de socio", "Cosecha propia", "Banco de semillas comunal", "Compra a vivero"]


def documento(titulo, variables, css, cuerpo, js, tema="dark"):
    return f"""<!doctype html>
<html lang="es" data-theme="{tema}">
<head>
<meta charset="utf-8">
<title>{titulo}</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;700&display=swap" rel="stylesheet">
<style>
{variables}
{css}
</style>
</head>
<body>
{cuerpo}
<script>
{js}
function toggleTheme() {{ var h = document.documentElement; h.dataset.theme = h.dataset.theme === 'dark' ? 'light' : 'dark'; }}
</script>
</body>
</html>
"""


def inventario(r):
    variables = """:root, [data-theme="dark"] { --bg: #111814; --card: #18221c; --txt: #e6eee8; --muted: #9fb0a4; --acc: #6cc28e; --line: #2c3a31; --warn: #e0a21f; }
[data-theme="light"] { --bg: #f6f7f2; --card: #ffffff; --txt: #1c2a21; --muted: #5a6b5f; --acc: #2f7d4f; --line: #d6dccf; --warn: #b26b00; }"""
    css = """/* cambio #12: tabla más compacta */
body { margin: 0; background: var(--bg); color: var(--txt); font-family: 'Nunito', sans-serif; }
.pagina { display: none; padding: 22px; } .pagina.activa { display: block; }
.cab { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.btn { padding: 9px 15px; border-radius: 7px; border: 1px solid var(--acc); background: var(--acc); color: #0d1410; cursor: pointer; }
.btn-sec { background: transparent; color: var(--acc); }
table { width: 100%; border-collapse: collapse; background: var(--card); }
th, td { padding: 9px 11px; border-bottom: 1px solid var(--line); font-size: 13px; text-align: left; }
.etq { padding: 2px 9px; border-radius: 999px; font-size: 11px; background: rgba(108, 194, 142, 0.16); color: var(--acc); }
.etq-baja { background: rgba(224, 162, 31, 0.18); color: var(--warn); }
.banner-bascula { display: none; padding: 11px 15px; border-radius: 7px; background: rgba(224, 162, 31, 0.18); color: var(--warn); margin-bottom: 12px; }
body.bascula-off .banner-bascula { display: block; }
.modal-fondo { display: none; position: fixed; inset: 0; background: rgba(5, 8, 6, 0.6); align-items: center; justify-content: center; }
.modal-fondo.abierto { display: flex; }
.modal { background: var(--card); border-radius: 13px; padding: 22px; width: 420px; }
.nuevo { animation: brillo 2s ease-in-out infinite; }
@keyframes brillo { 50% { box-shadow: 0 0 0 3px rgba(108, 194, 142, 0.35); } }"""
    filas = []
    for n in range(620):
        cultivo, origen = r.choice(CULTIVOS), r.choice(ORIGENES)
        gramos = r.randint(5, 900)
        estado = "Disponible" if r.random() > 0.15 else "Baja"
        clase = "etq" if estado == "Disponible" else "etq etq-baja"
        filas.append(f'<tr><td>L-{1000 + n}</td><td>{cultivo}</td><td>{origen}</td><td>{gramos} g</td>'
                     f'<td>{r.choice(NOMBRES)}</td><td><span class="{clase}">{estado}</span></td>'
                     f'<td>{r.choice(NOTAS)}</td>'
                     f'<td><button class="btn btn-sec" onclick="verLote(\'L-{1000 + n}\')">Ver lote</button></td></tr>')
    movs = "".join(f"<tr><td>{r.randint(1, 28)} de mayo</td><td>L-{1000 + r.randint(0, 359)}</td><td>{r.choice(['Entrada', 'Salida', 'Ajuste'])}</td>"
                   f"<td>{r.randint(5, 200)} g</td><td>{r.choice(NOMBRES)}</td></tr>" for _ in range(60))
    cuerpo = f"""<p class="banner-bascula">La báscula comunitaria está desconectada: los pesos se cargan a mano.</p>
<section id="lista-page" class="pagina activa">
  <div class="cab"><h1>Inventario de semillas</h1><button class="btn" onclick="abrir('nuevo-lote-modal')">Nuevo lote</button></div>
  <p>Banco de semillas del huerto: 620 lotes, ordenados por código.</p>
  <table><thead><tr><th>Código</th><th>Cultivo</th><th>Origen</th><th>Cantidad</th><th>Responsable</th><th>Estado</th><th>Notas</th><th></th></tr></thead>
  <tbody>
{chr(10).join(filas)}
</tbody></table>
</section>
<section id="detalle-page" class="pagina">
  <div class="cab"><h1>Detalle del lote</h1><button class="btn btn-sec" onclick="ver('lista-page')">Volver al inventario</button></div>
  <dl><dt>Código</dt><dd id="d-codigo">L-1000</dd><dt>Germinación esperada</dt><dd>85 %</dd><dt>Ubicación</dt><dd>Estante B, caja 4</dd></dl>
  <button class="btn" onclick="abrir('baja-modal')">Dar de baja</button>
</section>
<section id="movimientos-page" class="pagina">
  <div class="cab"><h1>Movimientos de semillas</h1></div>
  <table><thead><tr><th>Fecha</th><th>Lote</th><th>Tipo</th><th>Cantidad</th><th>Registró</th></tr></thead><tbody>{movs}</tbody></table>
</section>
<div class="modal-fondo" id="nuevo-lote-modal"><div class="modal">
  <h2>Nuevo lote</h2>
  <label>Cultivo <input id="nl-cultivo"></label>
  <label>Cantidad en gramos <input id="nl-gramos" type="number"></label>
  <p id="nl-error" hidden>La cantidad tiene que ser mayor que cero.</p>
  <button class="btn" onclick="guardarLote()">Guardar lote</button>
</div></div>
<div class="modal-fondo" id="baja-modal"><div class="modal">
  <h2>Dar de baja el lote</h2><p>El lote deja de estar disponible para intercambio.</p>
  <button class="btn" onclick="cerrar('baja-modal')">Confirmar baja</button>
</div></div>"""
    js = """function ver(id) { document.querySelectorAll('.pagina').forEach(function (p) { p.classList.toggle('activa', p.id === id); }); }
function verLote(c) { document.getElementById('d-codigo').textContent = c; ver('detalle-page'); }
function abrir(id) { document.getElementById(id).classList.add('abierto'); }
function cerrar(id) { document.getElementById(id).classList.remove('abierto'); }
// Valida que la cantidad sea mayor que cero antes de guardar
function guardarLote() { var g = Number(document.getElementById('nl-gramos').value); document.getElementById('nl-error').hidden = g > 0; if (g > 0) cerrar('nuevo-lote-modal'); }
window.__basculaCambio = function (off) { document.body.classList.toggle('bascula-off', off); };
setTimeout(function () { document.querySelector('tbody tr').classList.add('nuevo'); }, 800);"""
    return documento("Semilla · Inventario de semillas", variables, css, cuerpo, js)


def compostaje(r):
    variables = """:root, [data-theme="dark"] { --fondo: #101712; --tarjeta: #19231d; --texto: #e7efe9; --tenue: #9fb0a4; --verde: #6cc28e; --borde: #2f3d33; --calor: #e8743b; }
[data-theme="light"] { --fondo: #f6f7f2; --tarjeta: #ffffff; --texto: #1c2a21; --tenue: #5a6b5f; --verde: #2f7d4f; --borde: #d6dccf; --calor: #c4501b; }"""
    css = """body { margin: 0; background: var(--fondo); color: var(--texto); font-family: 'Nunito', sans-serif; }
.tabs { display: flex; gap: 6px; padding: 18px 22px 0; }
.tab { padding: 9px 14px; border: 0; border-radius: 7px 7px 0 0; background: none; color: var(--tenue); cursor: pointer; }
.tab.on { background: var(--tarjeta); color: var(--verde); }
.panel { display: none; padding: 22px; } .panel.on { display: block; }
.kpis { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.kpi { background: var(--tarjeta); border: 1px solid var(--borde); border-radius: 11px; padding: 15px; }
.kpi b { display: block; font-size: 27px; color: var(--verde); }
.grafico { background: var(--tarjeta); border: 1px solid var(--borde); border-radius: 11px; padding: 14px; margin-top: 14px; }
.aviso-bascula { display: none; padding: 10px 14px; border-radius: 7px; background: rgba(232, 116, 59, 0.16); color: var(--calor); margin: 12px 22px 0; }
body.bascula-off .aviso-bascula { display: block; }
.btn { padding: 9px 15px; border-radius: 7px; border: 0; background: var(--verde); color: #0d1410; cursor: pointer; }
.capa { display: none; position: fixed; inset: 0; background: rgba(5, 8, 6, 0.6); align-items: center; justify-content: center; }
.capa.on { display: flex; }
.caja { background: var(--tarjeta); border-radius: 13px; padding: 22px; width: 400px; }
.vivo { animation: latir 1.4s infinite; } @keyframes latir { 50% { opacity: .5; } }"""
    temperaturas = [round(38 + 25 * (1 - abs(30 - d) / 30) + r.uniform(-3, 3), 1) for d in range(60)]
    pilas = "".join(f"<tr><td>Pila {n + 1}</td><td>{r.randint(20, 70)} °C</td><td>{r.randint(40, 65)} %</td><td>Volteo en {r.randint(1, 9)} días</td></tr>"
                    for n in range(24))
    cuerpo = f"""<p class="aviso-bascula">Sin báscula: el peso de cada aporte se estima.</p>
<nav class="tabs"><button class="tab on" onclick="tab('resumen-tab', this)">Resumen</button><button class="tab" onclick="tab('pilas-tab', this)">Pilas</button></nav>
<section id="resumen-tab" class="panel on">
  <h1>Resumen de compostaje</h1>
  <div class="kpis"><div class="kpi"><b>1.240 kg</b>Residuos recibidos este mes</div><div class="kpi"><b>24</b>Pilas activas</div><div class="kpi"><b class="vivo">58 °C</b>Temperatura promedio</div></div>
  <div class="grafico"><h2>Temperatura de la pila 3, últimos 60 días</h2><svg id="grafico-temp" viewBox="0 0 600 200" width="100%" height="200"></svg></div>
  <button class="btn" onclick="document.getElementById('registrar-modal').classList.add('on')">Registrar aporte</button>
</section>
<section id="pilas-tab" class="panel">
  <h1>Pilas de compost</h1>
  <table><thead><tr><th>Pila</th><th>Temperatura</th><th>Humedad</th><th>Próximo volteo</th></tr></thead><tbody>{pilas}</tbody></table>
</section>
<div class="capa" id="registrar-modal"><div class="caja">
  <h2>Registrar aporte</h2><label>Socio <input></label><label>Peso en kilos <input type="number"></label>
  <button class="btn">Guardar aporte</button>
</div></div>"""
    js = f"""var TEMPS = {temperaturas};
function tab(id, b) {{ document.querySelectorAll('.panel').forEach(function (p) {{ p.classList.toggle('on', p.id === id); }}); document.querySelectorAll('.tab').forEach(function (t) {{ t.classList.toggle('on', t === b); }}); }}
// Dibuja la curva de temperatura con los datos de la pila
function dibujarTemperaturas() {{
  var pts = TEMPS.map(function (t, i) {{ return (i * 10) + ',' + (200 - (t - 20) * 3.5); }}).join(' ');
  document.getElementById('grafico-temp').innerHTML = '<polyline fill="none" stroke="#e8743b" stroke-width="2" points="' + pts + '"/>';
}}
dibujarTemperaturas();
window.__basculaCambio = function (off) {{ document.body.classList.toggle('bascula-off', off); }};"""
    return documento("Semilla · Compostaje", variables, css, cuerpo, js)


def socios(r):
    variables = """:root, [data-theme="dark"] { --surface-0: #0f1511; --surface-1: #172019; --ink: #e5ede7; --ink-2: #9db0a2; --brand: #74c795; --line: #2d3b32; }
[data-theme="light"] { --surface-0: #f6f7f2; --surface-1: #ffffff; --ink: #1c2a21; --ink-2: #5a6b5f; --brand: #2f7d4f; --line: #d6dccf; }"""
    css = """body { margin: 0; display: flex; background: var(--surface-0); color: var(--ink); font-family: 'Nunito', sans-serif; }
.lateral { width: 210px; padding: 18px; border-right: 1px solid var(--line); }
.lateral button { display: block; width: 100%; padding: 9px; border: 0; background: none; color: var(--ink-2); text-align: left; cursor: pointer; }
.lateral button.sel { color: var(--brand); background: var(--surface-1); border-radius: 7px; }
.contenido { flex: 1; padding: 22px; }
.panel { display: none; } .panel.sel { display: block; }
table { width: 100%; border-collapse: collapse; background: var(--surface-1); }
th, td { padding: 9px 11px; border-bottom: 1px solid var(--line); font-size: 13px; text-align: left; }
.btn { padding: 9px 15px; border-radius: 7px; border: 0; background: var(--brand); color: #0c120e; cursor: pointer; }
.sombra { display: none; position: fixed; inset: 0; background: rgba(5, 8, 6, 0.6); align-items: center; justify-content: center; }
.sombra.ver { display: flex; }
.dialogo { background: var(--surface-1); border-radius: 13px; padding: 22px; width: 420px; }
.al-dia { color: var(--brand); } .atrasada { color: #e07a1f; }"""
    filas = "\n".join(f"<tr><td>{r.choice(NOMBRES)} {chr(65 + n % 26)}.</td><td>socio{n}@example.com</td><td>Parcela P-{r.randint(1, 40):02d}</td>"
                    f"<td>{r.randint(2019, 2026)}</td><td class=\"{'al-dia' if r.random() > 0.2 else 'atrasada'}\">{'Al día' if r.random() > 0.2 else 'Atrasada'}</td></tr>"
                    for n in range(480))
    cuotas = "".join(f"<tr><td>{r.choice(NOMBRES)}</td><td>{m} 2026</td><td>$ {r.choice([4500, 6000, 7500]):,}</td><td>{r.choice(['Pagada', 'Pendiente'])}</td></tr>".replace(",", ".")
                     for m in ["Enero", "Febrero", "Marzo", "Abril", "Mayo"] for _ in range(12))
    cuerpo = f"""<aside class="lateral">
  <button class="sel" onclick="panel('panel-socios', this)">Socios</button>
  <button onclick="panel('panel-cuotas', this)">Cuotas</button>
  <button onclick="panel('panel-ajustes', this)">Ajustes</button>
</aside>
<main class="contenido">
  <section id="panel-socios" class="panel sel">
    <h1>Socios del huerto</h1><button class="btn" onclick="ver('invitar-modal')">Invitar socio</button>
    <table><thead><tr><th>Nombre</th><th>Correo</th><th>Parcela</th><th>Socio desde</th><th>Cuota</th></tr></thead><tbody>{filas}</tbody></table>
  </section>
  <section id="panel-cuotas" class="panel">
    <h1>Cuotas</h1><button class="btn" onclick="ver('cuota-modal')">Registrar pago de cuota</button>
    <table><thead><tr><th>Socio</th><th>Mes</th><th>Monto</th><th>Estado</th></tr></thead><tbody>{cuotas}</tbody></table>
  </section>
  <section id="panel-ajustes" class="panel">
    <h1>Ajustes del huerto</h1>
    <label>Nombre del huerto <input value="Huerto Los Aromos"></label>
    <label>Cuota mensual <input value="6000"></label>
    <button class="btn">Guardar ajustes</button>
  </section>
</main>
<div class="sombra" id="invitar-modal"><div class="dialogo"><h2>Invitar socio</h2><label>Correo <input placeholder="nombre@example.com"></label><button class="btn">Enviar invitación</button></div></div>
<div class="sombra" id="cuota-modal"><div class="dialogo"><h2>Registrar pago de cuota</h2><label>Monto <input type="number"></label><button class="btn">Registrar pago</button></div></div>"""
    js = """function panel(id, b) { document.querySelectorAll('.panel').forEach(function (p) { p.classList.toggle('sel', p.id === id); }); document.querySelectorAll('.lateral button').forEach(function (x) { x.classList.toggle('sel', x === b); }); }
function ver(id) { document.getElementById(id).classList.add('ver'); }"""
    return documento("Semilla · Socios", variables, css, cuerpo, js)


def shell(modulos):
    plantillas = "\n".join(f'<script type="text/plain" id="tpl-{n}">{t.replace("</script>", "<\\/script>")}</script>' for n, t in modulos)
    return f"""<!doctype html>
<html lang="es" data-theme="dark">
<head>
<meta charset="utf-8">
<title>Semilla · Integrado</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;700&display=swap" rel="stylesheet">
<style>
:root, [data-theme="dark"] {{ --bg: #0e1410; --side: #141c17; --txt: #e6eee8; --dim: #9fb0a4; --acc: #6cc28e; --line: #2c3a31; }}
[data-theme="light"] {{ --bg: #f6f7f2; --side: #ffffff; --txt: #1c2a21; --dim: #5a6b5f; --acc: #2f7d4f; --line: #d6dccf; }}
body {{ margin: 0; display: grid; grid-template-columns: 230px 1fr; grid-template-rows: 58px 1fr; height: 100vh; background: var(--bg); color: var(--txt); font-family: 'Nunito', sans-serif; }}
.top {{ grid-column: 1 / 3; display: flex; align-items: center; justify-content: space-between; padding: 0 18px; border-bottom: 1px solid var(--line); }}
.side {{ background: var(--side); padding: 14px; border-right: 1px solid var(--line); }}
.side a {{ display: block; padding: 10px 12px; border-radius: 7px; color: var(--dim); text-decoration: none; }}
.side a.on {{ background: rgba(108, 194, 142, 0.14); color: var(--acc); }}
#app-frames iframe {{ display: none; width: 100%; height: 100%; border: 0; }}
#app-frames iframe.on {{ display: block; }}
.demo-wrap {{ position: relative; }}
.demo-btn {{ padding: 4px 10px; border: 1px dashed #e0a21f; border-radius: 6px; background: transparent; color: #e0a21f; font-size: 12px; }}
.demo-menu {{ display: none; position: absolute; right: 0; top: 30px; background: var(--side); border: 1px solid var(--line); border-radius: 8px; padding: 6px; width: 250px; }}
.demo-wrap.open .demo-menu {{ display: block; }}
.drawer {{ position: fixed; top: 0; right: -360px; width: 340px; height: 100%; background: var(--side); border-left: 1px solid var(--line); transition: right .3s; padding: 18px; }}
.drawer.open {{ right: 0; }}
.overlay {{ display: none; position: fixed; inset: 0; background: rgba(5, 8, 6, 0.6); align-items: center; justify-content: center; }}
.overlay.open {{ display: flex; }}
</style>
</head>
<body>
<header class="top">
  <strong>Semilla · Huerto Los Aromos</strong>
  <div>
    <span class="demo-wrap" id="demo"><button class="demo-btn" onclick="document.getElementById('demo').classList.toggle('open')">DEMO ▾</button>
      <span class="demo-menu"><button onclick="aplicarBascula(true)">Simular báscula desconectada</button><button onclick="aplicarBascula(false)">Salir de demo</button></span></span>
    <button onclick="document.getElementById('notif-drawer').classList.add('open')">Notificaciones</button>
    <button onclick="document.getElementById('ayuda-overlay').classList.add('open')">Ayuda</button>
  </div>
</header>
<nav class="side">
  <a href="#inventario" class="on">Inventario</a>
  <a href="#compostaje">Compostaje</a>
  <a href="#socios">Socios</a>
</nav>
<div id="app-frames"></div>
<aside class="drawer" id="notif-drawer"><h2>Notificaciones</h2><p>La pila 7 superó los 70 °C.</p><p>Bruno Lagos pagó la cuota de mayo.</p></aside>
<div class="overlay" id="ayuda-overlay"><div><h2>Centro de ayuda</h2><p>Escríbenos a ayuda@example.com.</p></div></div>
{plantillas}
<script>
var RUTAS = ['inventario', 'compostaje', 'socios'];
function dec(s) {{ return s.replace(/<\\\\\\//g, '</'); }}
function montar(n) {{ var f = document.createElement('iframe'); f.id = 'f-' + n; f.srcdoc = dec(document.getElementById('tpl-' + n).textContent); document.getElementById('app-frames').appendChild(f); return f; }}
var frames = RUTAS.map(montar);
function mostrar() {{ var r = (location.hash || '#inventario').slice(1); frames.forEach(function (f) {{ f.classList.toggle('on', f.id === 'f-' + r); }}); }}
window.addEventListener('hashchange', mostrar); mostrar();
// Sincroniza el estado de la báscula en los módulos que pesan
function aplicarBascula(off) {{ frames.forEach(function (f) {{ try {{ f.contentWindow.__basculaCambio && f.contentWindow.__basculaCambio(off); }} catch (e) {{}} }}); document.getElementById('demo').classList.remove('open'); }}
</script>
</body>
</html>
"""


def generar():
    r = random.Random(14)
    return shell([("inventario", inventario(r)), ("compostaje", compostaje(r)), ("socios", socios(r))])


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    salida = Path(argv[1])
    salida.mkdir(parents=True, exist_ok=True)
    (salida / "grande.html").write_text(generar())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
