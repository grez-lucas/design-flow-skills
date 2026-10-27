#!/usr/bin/env python3
"""Revisa las salidas de una iteración de html-a-vista y escribe grading.json por corrida.

Regla: el contenido esperado del informe (notas.md) se busca en todo el texto, sin depender de una sección
ni de un formato, y la severidad (pendiente de decisión, criterio para el ticket) se verifica en un chequeo
aparte, solo sobre la primera oración de cada hallazgo. El repositorio y la carpeta de trabajo se revisan
con chequeos propios: revisar.py, commits, archivos, vistas, tokens y contratos.
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

PRUEBAS = Path(__file__).resolve().parent
SKILLS = PRUEBAS.parents[1] / "skills"
REVISAR = SKILLS / "checklist-diseno" / "scripts" / "revisar.py"
sys.dont_write_bytecode = True
sys.path.insert(0, str(SKILLS / "html-a-vista" / "scripts"))
import tokens as T  # noqa: E402
from desarmar import DEMO  # noqa: E402

LIMITE = 256 * 1024
PENDIENTE = r"pendiente|por decidir|a decidir|sin decidir|falta decidir|queda abiert"
MOCKUPS = {
    "chico": {
        "pantallas": {"Reservas de parcelas": r"reservas de parcelas"},
        "superposiciones": {},
        "fuera": r"#e07a1f",
        "logica": r"filtr",
        "ticket": "SEM-11",
    },
    "grande": {
        "pantallas": {"Marco": r"huerto los aromos", "Inventario de semillas": r"inventario de semillas",
                      "Detalle del lote": r"detalle del lote", "Movimientos de semillas": r"movimientos de semillas",
                      "Resumen de compostaje": r"resumen de compostaje", "Pilas de compost": r"pilas de compost",
                      "Socios del huerto": r"socios del huerto", "Cuotas": r"\bcuotas\b", "Ajustes del huerto": r"ajustes del huerto"},
        "superposiciones": {"Nuevo lote": r"nuevo lote", "Dar de baja": r"dar de baja", "Registrar aporte": r"registrar aporte",
                            "Invitar socio": r"invitar socio", "Registrar pago de cuota": r"registrar pago", "Notificaciones": r"notificaciones",
                            "Centro de ayuda": r"centro de ayuda"},
        "fuera": r"#e07a1f",
        "logica": r"mayor que cero|cantidad",
        "global": r"b[aá]scula",
    },
    "demo": {
        "pantallas": {"Panel de riego": r"panel de riego", "Historial de riego": r"historial de riego"},
        "superposiciones": {"Regar ahora": r"regar ahora|iniciar riego"},
        "fuera": r"#7b4fd6",
        "logica": r"duraci[oó]n",
        "demo": {"sensor sin señal": r"sin.?se[ñn]al", "tanque vacío": r"tanque.?vac[ií]o"},
        "ajenos": ["full", "partial", "off"],
    },
    "react": {
        "pantallas": {"Cosechas de la semana": r"cosechas de la semana"},
        "superposiciones": {},
        "fuera": r"#dc2626|text-red-600|rgb\(220, ?38, ?38\)",
        "logica": r"total|suma",
        "prototipo": r"escenario:",
    },
}


def check(text, ok, evidence=""):
    return {"text": text, "passed": bool(ok), "evidence": str(evidence)[:300]}


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True).stdout


def commits(repo):
    return int(git(repo, "rev-list", "--count", "HEAD").strip() or 0)


def cambiados(repo):
    raiz = git(repo, "rev-list", "--max-parents=0", "HEAD").split()
    return [l for l in git(repo, "diff", "--name-only", raiz[0], "HEAD").splitlines() if l] if raiz else []


def archivos(carpeta, patron="*"):
    return [p for p in carpeta.rglob(patron) if p.is_file() and ".git" not in p.parts] if carpeta.is_dir() else []


def vistas(repo):
    return sorted((repo / "design" / "vistas").rglob("*.html")) if (repo / "design" / "vistas").is_dir() else []


def visible(html):
    s = re.sub(r"<!--.*?-->|<script\b.*?</script\s*>|<style\b.*?</style\s*>", " ", html, flags=re.S | re.I)
    return " ".join(re.sub(r"<[^>]+>", " ", s).split()).lower()


def escenarios(html):
    m = re.search(r"""data-escenarios\s*=\s*["']([^"']*)""", html)
    return [e.strip() for e in m.group(1).split(",") if e.strip()] if m else []


def hallazgos(informe):
    """(primera oración, etiqueta) de cada ítem del informe. Una fila de tabla cuenta entera; la etiqueta es el
    encabezado o la línea corta terminada en dos puntos bajo la que está el ítem."""
    out, etiqueta = [], ""
    for linea in informe.splitlines():
        s = linea.strip()
        if not s or re.fullmatch(r"\|?[\s:|-]+\|?", s):
            continue
        plano = re.sub(r"[*_`]", "", s).strip()
        if s.startswith("#") or (not re.match(r"^([-*+]\s|\d+\.|\|)", s) and len(plano) < 80 and plano.endswith(":")):
            etiqueta = plano.lstrip("# ").lower()
            continue
        if s.startswith("|"):
            out.append((" · ".join(c.strip() for c in s.strip("|").split("|")).lower(), etiqueta))
            continue
        s = re.sub(r"^([-*+]|\d+\.)\s+", "", plano)
        m = re.search(r"[.!?]\s", s)
        out.append(((s[:m.start() + 1] if m else s).lower(), etiqueta))
    return out


def con_marca(its, contenido, marca):
    """Hallazgos cuya primera oración nombra el contenido y que llevan la marca en esa oración o en su etiqueta."""
    return [h for h, e in its if re.search(contenido, h) and (re.search(marca, h) or re.search(marca, e))]


def md5(path):
    return hashlib.md5(path.read_bytes()).hexdigest()


def informe(out, cfg, navegador):
    notas = (out / "notas.md").read_text(errors="ignore")
    low, its = notas.lower(), hallazgos(notas)
    res = []
    faltan = [n for n, p in cfg["pantallas"].items() if not re.search(p, low)]
    res.append(check("El informe nombra cada pantalla del mockup", not faltan, f"faltan: {faltan}"))
    if navegador:
        res.append(check("El informe trae capturas lado a lado", re.search(r"captura", low), ""))
    else:
        res.append(check("El informe dice que la verificación se hizo sin render", re.search(r"sin render|sin navegador", low), ""))
    for nombre, p in cfg.get("demo", {}).items():
        res.append(check(f"El informe nombra el escenario DEMO {nombre}", re.search(p, low), ""))
    if cfg.get("ajenos"):
        res.append(check("El informe dice que renombró el data-state ajeno", re.search(r"data-state", low) and re.search(r"renombr", low), ""))
    criterio = con_marca(its, cfg["logica"], r"criterio|ticket")
    res.append(check("La lógica JS figura como criterio para el ticket", criterio, criterio[:1]))
    return res, low, its


def chequeos_fuera(cfg, low, its, repo, con_ds):
    if not (con_ds and cfg["fuera"]):
        return []
    pend = con_marca(its, cfg["fuera"], PENDIENTE)
    tok = (repo / "design" / "tokens.css").read_text(errors="ignore").lower() if (repo / "design" / "tokens.css").exists() else ""
    return [
        check("El informe menciona el valor fuera de umbral", re.search(cfg["fuera"], low), ""),
        check("El valor fuera de umbral figura como pendiente de decisión", pend, pend[:1]),
        check("tokens.css no agrega el valor que producto no decidió", not re.search(cfg["fuera"], tok), ""),
    ]


def repositorio(out, cfg, iteracion, mockup, con_ds, fixture_repo):
    repo, trabajo = out / "repo", out / "trabajo"
    vs = vistas(repo)
    htmls = {v: v.read_text(errors="ignore") for v in vs}
    textos = " ".join(visible(h) for h in htmls.values())
    res = [check("Hay al menos un commit nuevo", commits(repo) >= 2, f"commits: {commits(repo)}")]
    fuera = [f for f in cambiados(repo) if not f.startswith(("design/", "specs/"))]
    res.append(check("Los commits nuevos tocan solo design/ y specs/", commits(repo) >= 2 and not fuera, fuera[:5]))
    r = subprocess.run([sys.executable, "-B", str(REVISAR), str(repo)], capture_output=True, text=True)
    bloqueos = [l for l in r.stdout.splitlines() if "BLOQUEA" in l]
    res.append(check("revisar.py no tiene hallazgos que bloquean", vs and r.returncode == 0, bloqueos[:3] or r.stdout[-200:]))
    original = iteracion / "insumos" / f"{mockup}.html"
    huella = md5(original) if original.exists() else None
    pesados = [str(p.relative_to(repo)) for p in archivos(repo) if p.stat().st_size > LIMITE or md5(p) == huella]
    res.append(check("Ningún archivo del repositorio es el original ni pasa 256 KB", not pesados, pesados[:3]))
    de_trabajo = [str(p.relative_to(repo)) for p in archivos(repo)
                  if p.name in ("manifiesto.json", "resumen.md") or "contrato" in p.name.lower() or "partes" in p.parts or "trozos" in p.parts]
    res.append(check("El repositorio no tiene archivos de la carpeta de trabajo", not de_trabajo, de_trabajo[:3]))
    faltan = [n for n, p in cfg["pantallas"].items() if not re.search(p, textos)]
    res.append(check("Cada pantalla del mockup está en una vista", vs and not faltan, f"faltan: {faltan}"))
    if cfg["superposiciones"]:
        faltan = [n for n, p in cfg["superposiciones"].items() if not re.search(p, textos)]
        res.append(check("Cada superposición del mockup está en un escenario", vs and not faltan, f"faltan: {faltan}"))
    proto = [str(v.relative_to(repo)) for v, h in htmls.items()
             if DEMO.search(visible(h)) or (cfg.get("prototipo") and re.search(cfg["prototipo"], visible(h)))]
    res.append(check("Las vistas no tienen controles de prototipo", vs and not proto, proto[:3]))
    if cfg.get("ajenos"):
        usados = {s for h in htmls.values() for g in re.findall(r"""data-state\s*=\s*["']([^"']*)""", h) for s in g.split()}
        ajenos = sorted(usados & set(cfg["ajenos"]))
        res.append(check("Las vistas no usan el data-state ajeno del mockup", vs and not ajenos, ajenos))
    for nombre, p in cfg.get("demo", {}).items():
        con = [v.name for v, h in htmls.items() if any(re.search(p, e) for e in escenarios(h))]
        res.append(check(f"El escenario DEMO {nombre} está en data-escenarios", con, con[:2]))
    css = [p for p in archivos(repo / "design", "*.css")]
    sucio = [str(p.relative_to(repo)) for p in list(htmls) + css if "@keyframes" in p.read_text(errors="ignore")]
    cdn = [str(v.relative_to(repo)) for v, h in htmls.items() if re.search(r"""(?:src|href)\s*=\s*["'](?:https?:)?//|@import|url\(\s*["']?(?:https?:)?//""", h)]
    js = [str(v.relative_to(repo)) for v, h in htmls.items()
          if [s for s in re.findall(r"<script\b([^>]*)>(.*?)</script\s*>", h, flags=re.S | re.I) if not re.search(r"src\s*=\s*[\"'][^\"']*proto\.js", s[0])]]
    res.append(check("Sin @keyframes, CDN ni JS fuera de proto.js", vs and not (sucio or cdn or js), {"keyframes": sucio[:2], "cdn": cdn[:2], "js": js[:2]}))
    tok = repo / "design" / "tokens.css"
    if con_ds:
        v = T.verificar(fixture_repo / "design" / "tokens.css", tok) if tok.exists() else {"casi_iguales": ["sin tokens.css"]}
        res.append(check("tokens.css no tiene colores nuevos dentro del umbral de uno existente", not v["casi_iguales"], v["casi_iguales"][:2]))
    else:
        espacios = re.findall(r"(--space-[\w-]+)\s*:\s*([^;]+);", tok.read_text()) if tok.exists() else []
        malos = [(n, x) for n, x in espacios if (T.leer_medida(x.strip()) or 1) % 4]
        res.append(check("Crea tokens.css con las medidas en escala de 4 px", espacios and not malos, malos[:3] or f"{len(espacios)} espacios"))
    contratos = [p for p in archivos(trabajo, "*.md") if "contrato" in p.name.lower() or p.read_text(errors="ignore").lstrip().lower().startswith("# contrato")]
    res.append(check("Hay un contrato por vista en la carpeta de trabajo", vs and len(contratos) >= len(vs), f"{len(contratos)} contratos, {len(vs)} vistas"))
    res.append(check("El manifiesto del script está en la carpeta de trabajo", archivos(trabajo, "manifiesto.json"), ""))
    if cfg.get("ticket"):
        cita = [v.name for v, h in htmls.items() if re.search(rf"""<meta\s+name=["']tickets["']\s+content=["'][^"']*{cfg['ticket']}""", h)]
        res.append(check(f"La vista cita {cfg['ticket']} en <meta name=\"tickets\">", cita, cita))
    else:
        sin = [v.name for v, h in htmls.items() if not re.search(r"""<meta\s+name=["'](spec|tickets)["']""", h)]
        res.append(check("Las vistas sin ticket citan su spec en <meta name=\"spec\">", vs and not sin, sin[:3]))
    return res, htmls, tok


def extra_grande(out, htmls, tok):
    repo = out / "repo"
    t = tok.read_text(errors="ignore") if tok.exists() else ""
    oscuro = re.search(r"\[data-theme=[\"']?dark[\"']?\]\s*\{([^}]*)\}", t)
    no_color = [n for n in re.findall(r"(--[\w-]+)\s*:", oscuro.group(1))] if oscuro else []
    no_color = [n for n in no_color if not n.startswith("--color-")]
    epicas = {v.parent.name for v in htmls}
    globales = {}
    for v, h in htmls.items():
        for e in escenarios(h):
            if re.search(MOCKUPS["grande"]["global"], e):
                globales.setdefault(e, set()).add(v.parent.name)
    compartido = [e for e, ep in globales.items() if len(ep) >= 2]
    spec = "\n".join(p.read_text(errors="ignore") for p in archivos(repo / "specs", "*.md"))
    svg = [v.name for v, h in htmls.items() if re.search(r"<svg\b", h) and re.search(r"<(polyline|path|line|rect)\b", h) and re.search(r"temperatura", visible(h))]
    notas = (out / "notas.md").read_text(errors="ignore").lower()
    pngs = archivos(out / "trabajo", "*.png")
    return [
        check("tokens.css define el tema oscuro en [data-theme=\"dark\"] solo con --color-*", oscuro and not no_color, no_color[:3]),
        check("Una épica por módulo, más el marco", len(epicas) >= 4, sorted(epicas)),
        check("El escenario de la báscula tiene el mismo nombre en vistas de dos módulos o más", compartido, globales),
        check("El spec lista el escenario global", compartido and any(e in spec for e in compartido), compartido),
        check("El gráfico de temperatura es un SVG estático", svg, svg[:2]),
        check("El informe describe las tres olas", re.search(r"\bola", notas), ""),
        check("Hay capturas en la carpeta de trabajo", pngs, f"{len(pngs)} png"),
    ]


def sin_conversion(out, fixture_repo, motivo):
    repo, trabajo = out / "repo", out / "trabajo"
    notas = (out / "notas.md").read_text(errors="ignore").lower()
    estado = git(repo, "status", "--porcelain").strip()
    res = [check("Ningún commit nuevo", commits(repo) == 1, f"commits: {commits(repo)}"),
           check("No escribe en el repositorio", not estado and len(vistas(repo)) == len(vistas(fixture_repo)), estado[:200])]
    if motivo == "navegador":
        res.append(check("Dice qué instalar para renderizar", re.search(r"chrome|chromium|playwright", notas), ""))
    elif motivo == "spec":
        borradores = [str(p.relative_to(out)) for p in archivos(trabajo, "*.md") if re.search(r"^# spec|## historias", p.read_text(errors="ignore"), re.I | re.M)]
        res.append(check("Deja un borrador de spec en la carpeta de trabajo", borradores, borradores[:2]))
        res.append(check("Deriva a grilling-es", "grilling" in notas, ""))
    else:
        res.append(check("Dice que se detiene por falta de subagentes", re.search(r"subagente", notas), ""))
    return res


def calificar(name, out, iteracion):
    prueba = next(p for p in json.loads((PRUEBAS / "evals.json").read_text())["evals"] if f"eval-{p['id']}-{p['name']}" == name)
    mockup, fixture_repo, reglas = prueba["mockup"], PRUEBAS / prueba["repo"], prueba["reglas"]
    if prueba["name"].endswith("sin-navegador"):
        return sin_conversion(out, fixture_repo, "navegador")
    if prueba["name"].endswith("sin-spec"):
        return sin_conversion(out, fixture_repo, "spec")
    if prueba["name"].endswith("sin-subagentes"):
        return sin_conversion(out, fixture_repo, "subagentes")
    cfg, con_ds = MOCKUPS[mockup], prueba["repo"].endswith("con-ds")
    navegador = "Con navegador" in reglas
    res, low, its = informe(out, cfg, navegador)
    res += chequeos_fuera(cfg, low, its, out / "repo", con_ds)
    rep, htmls, tok = repositorio(out, cfg, iteracion, mockup, con_ds, fixture_repo)
    res += rep
    if mockup == "grande":
        res += extra_grande(out, htmls, tok)
    if mockup == "chico" and not con_ds:
        t = tok.read_text(errors="ignore") if tok.exists() else ""
        fam = re.search(r"--font-family-base\s*:\s*([^;]+);", t)
        res.append(check("La fuente del mockup va en el token de familia", fam and "nunito" in fam.group(1).lower(), fam.group(1) if fam else ""))
    return res


REQUERIDO = "notas.md"


def falta(out):
    """Una corrida sin salidas o sin notas.md falla entera, en vez de pasar chequeos negativos por omisión."""
    if not out.is_dir() or not any(out.iterdir()):
        return "la carpeta outputs está vacía o no existe"
    f = out / REQUERIDO
    if not f.is_file() or not f.read_text(errors="ignore").strip():
        return f"falta {REQUERIDO} o está vacío"
    return None


def main(iteration):
    iteracion = Path(iteration)
    runs = sorted(iteracion.glob("eval-*/*/run-*"))
    if not runs:
        print(f"No hay corridas en {iteration}")
        return 1
    fallidas = 0
    for run in runs:
        name, config, out = run.parent.parent.name, run.parent.name, run / "outputs"
        error = falta(out)
        if error:
            fallidas += 1
            g = {"error": error, "expectations": [], "summary": {"passed": 0, "failed": 0, "total": 0, "pass_rate": 0.0}}
            print(f"{name}/{config}: ERROR, {error}")
        else:
            res = calificar(name, out, iteracion)
            passed = sum(r["passed"] for r in res)
            g = {"expectations": res, "summary": {"passed": passed, "failed": len(res) - passed, "total": len(res),
                                                  "pass_rate": round(passed / len(res), 2)}}
            print(f"{name}/{config}: {passed}/{len(res)}")
        (run / "grading.json").write_text(json.dumps(g, ensure_ascii=False, indent=1))
    return 1 if fallidas else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
