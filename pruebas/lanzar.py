#!/usr/bin/env python3
"""Corre las pruebas de una iteración con `claude -p`, en serie y reanudable.

Uso: python3 pruebas/lanzar.py <skill> <directorio-de-la-iteración> [opciones]

La iteración se arma antes con preparar.py. Por cada prueba de pruebas/<skill>/evals.json y cada
configuración, corre el prompt con sus reglas en outputs/, deja outputs/transcript.jsonl y anota en
<iteración>/corridas.tsv: prueba, configuración, código de salida, costo en USD a precio de lista,
segundos y permisos denegados.

- Reanuda: salta lo que ya tiene código 0 en algún corridas*.tsv de la iteración, y antes de repetir
  una corrida deja su salida como al preparar (sale "SUCIO" y no la toca si el repositorio cambió).
- Tope: no lanza una corrida si lo gastado en todas las iteraciones de la skill más lo que se estima
  que cuesta pasaría --tope. La estimación es el mayor costo de esa prueba y configuración con
  código 0 en iteraciones anteriores, o --por-corrida si no hay.
- Límite de uso de la cuenta: lee la última medición de la ventana de 5 horas y de la semanal que
  dejó un transcript (rate_limit_event) y lanza solo si la corrida entra en lo que queda. Si no
  entra en la de 5 horas, espera a que se reinicie (o sale con 3 con --no-esperar); si no entra
  en la semanal, sale con 3. --ventana-5h y --ventana-7d dicen cuántos USD a precio de lista caben
  en cada ventana; se miden con la subida de `utilization` que deja una corrida sola.
- Plugin: la primera vez copia .claude-plugin/ y skills/ a <iteración>/plugin y todas las corridas
  con la skill usan esa copia; si skills/ cambió después, sale con 2: es otra iteración.
- Arnés: "arnes" en evals.json quita herramientas. "sin-subagentes" niega Agent y Task;
  "sin-navegador" niega Chrome, node y npx y los saca del PATH.
"""
import argparse
import filecmp
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

PRUEBAS = Path(__file__).resolve().parent
RAIZ = PRUEBAS.parent
CONFIGURACIONES = ("with_skill", "without_skill")
PERMITIDAS = ["Agent", "Task", "Skill", "Read", "Write", "Edit", "Glob", "Grep",
              "Bash(python3:*)", "Bash(git:*)", "Bash(google-chrome:*)", "Bash(ls:*)", "Bash(mkdir:*)",
              "Bash(cp:*)", "Bash(cat:*)", "Bash(find:*)", "Bash(wc:*)",
              "Bash(cd:*)", "Bash(head:*)", "Bash(cmp:*)", "Bash(diff:*)", "Bash(echo:*)",
              "Bash(grep:*)", "Bash(sed:*)", "Bash(rsync:*)", "Bash(tail:*)", "Bash(sort:*)"]
NEGADAS = {"sin-subagentes": ["Agent", "Task"],
           "sin-navegador": ["Bash(google-chrome:*)", "Bash(npx:*)", "Bash(node:*)"]}


def comando(prueba, config, out, insumos, plugin, presupuesto):
    prompt = prueba["prompt"] + "\n\n" + prueba["reglas"].replace("<outputs>", str(out)).replace("<insumos>", str(insumos))
    cmd = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
           "--permission-mode", "acceptEdits", "--add-dir", str(insumos), "--max-budget-usd", f"{presupuesto:g}",
           "--strict-mcp-config", "--allowedTools", *PERMITIDAS]
    if config == "with_skill":
        cmd += ["--plugin-dir", str(plugin)]
    negadas = [h for r in prueba.get("arnes", []) for h in NEGADAS[r]]
    if negadas:
        cmd += ["--disallowedTools", *negadas]
    return cmd


def entorno(prueba, iteracion, env, claude):
    """El entorno de la corrida; sin navegador, un PATH con claude y /usr/bin sin Chrome ni Playwright."""
    if "sin-navegador" not in prueba.get("arnes", []):
        return env
    falso = iteracion / ".bin-sin-navegador"
    if not falso.exists():
        falso.mkdir()
        for p in Path("/usr/bin").iterdir():
            if "chrom" not in p.name and "playwright" not in p.name:
                (falso / p.name).symlink_to(p)
    return dict(env, PATH=f"{Path(claude).parent}:{falso}", PLAYWRIGHT_BROWSERS_PATH=str(iteracion / ".sin-playwright"))


def filas(iteraciones):
    return [l.split("\t") for it in iteraciones for t in sorted(Path(it).glob("corridas*.tsv")) for l in t.read_text().splitlines() if l]


def hechas(f):
    return {(x[0], x[1]) for x in f if x[2] == "0"}


def gastado(f):
    return sum(float(x[3] or 0) for x in f)


def estimado(f, nombre, config, defecto):
    costos = [float(x[3]) for x in f if x[0] == nombre and x[1] == config and x[2] == "0" and x[3]]
    return max(costos, default=defecto)


def pendientes(pruebas, configs, ids, ya):
    trabajos = [(f"eval-{p['id']}-{p['name']}", c) for p in pruebas if ids is None or p["id"] in ids for c in configs]
    return [t for t in trabajos if t not in ya]


def uso(transcripts):
    """La última medición de las ventanas de uso, del transcript modificado más tarde que tenga una."""
    for t in sorted(transcripts, key=lambda p: p.stat().st_mtime, reverse=True):
        ultima = None
        for linea in t.read_text().splitlines():
            if '"rate_limit_event"' not in linea:
                continue
            ventanas = json.loads(linea)["rate_limit_info"].get("unifiedWindows")
            if ventanas:
                ultima = {k: (ventanas[k]["utilization"], ventanas[k]["resetsAt"]) for k in ("five_hour", "seven_day")}
        if ultima:
            return ultima
    return None


def decidir(medicion, ahora, costo, ventana_5h, ventana_7d, margen=0.05):
    """("lanzar", None), ("esperar", reinicio de la ventana de 5 horas) o ("parar", reinicio semanal o None)."""
    if medicion is None:
        return "lanzar", None
    (u5, r5), (u7, r7) = medicion["five_hour"], medicion["seven_day"]
    u5, u7 = (u5 if ahora < r5 else 0), (u7 if ahora < r7 else 0)
    if u7 + costo / ventana_7d > 1 - margen:
        return "parar", r7
    if costo / ventana_5h > 1 - margen:
        return "parar", None
    if u5 + costo / ventana_5h > 1 - margen:
        return "esperar", r5
    return "lanzar", None


def cortada(transcript):
    """True si la corrida terminó porque la cuenta llegó a su límite de uso."""
    if not transcript.exists():
        return False
    for linea in transcript.read_text().splitlines():
        if '"usage_limit_reached"' in linea:
            try:
                if json.loads(linea).get("api_error") == "usage_limit_reached":
                    return True
            except ValueError:
                continue
    return False


def limpia(out):
    """Deja la salida como al preparar; False si el repositorio tiene cambios que no se pueden descartar a ciegas."""
    repo = out / "repo"
    sucio = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True).stdout
    commits = subprocess.run(["git", "-C", str(repo), "rev-list", "--count", "HEAD"], capture_output=True, text=True).stdout.strip()
    if sucio or commits != "1":
        return False
    for x in out.iterdir():
        if x.name not in ("repo", "transcript.jsonl"):
            shutil.rmtree(x) if x.is_dir() else x.unlink()
    return True


def iguales(a, b):
    if not (Path(a).is_dir() and Path(b).is_dir()):
        return False
    c = filecmp.dircmp(a, b, ignore=["__pycache__"])
    _, distintos, errores = filecmp.cmpfiles(a, b, c.common_files, shallow=False)
    return not (c.left_only or c.right_only or c.common_funny or distintos or errores) and all(
        iguales(Path(a) / d, Path(b) / d) for d in c.common_dirs)


def instantanea(raiz, destino):
    """Copia el plugin a destino si no está; True si la copia es igual al plugin de raiz."""
    partes = (".claude-plugin", "skills")
    if not destino.exists():
        for p in partes:
            shutil.copytree(raiz / p, destino / p, ignore=shutil.ignore_patterns("__pycache__"))
    return all(iguales(raiz / p, destino / p) for p in partes)


def correr(prueba, config, iteracion, plugin, presupuesto):
    """Corre una prueba y anota la fila en corridas.tsv; devuelve el código de salida."""
    out = iteracion / f"eval-{prueba['id']}-{prueba['name']}" / config / "run-1" / "outputs"
    claude = shutil.which("claude") or "claude"
    cmd = comando(prueba, config, out, iteracion / "insumos", plugin, presupuesto)
    env = entorno(prueba, iteracion, dict(os.environ), claude)
    t0 = time.time()
    with open(out / "transcript.jsonl", "w") as f:
        rc = subprocess.run([claude, *cmd[1:]], cwd=out, stdout=f, stderr=subprocess.STDOUT, env=env,
                            stdin=subprocess.DEVNULL).returncode
    costo, denegados = "", []
    for linea in (out / "transcript.jsonl").read_text().splitlines():
        try:
            m = json.loads(linea)
        except ValueError:
            continue
        if m.get("type") == "result":
            costo = m.get("total_cost_usd", "")
            denegados += m.get("permission_denials", [])
    with open(iteracion / "corridas.tsv", "a") as f:
        f.write(f"{out.parents[2].name}\t{config}\t{rc}\t{costo}\t{time.time() - t0:.0f}\t{json.dumps(denegados, ensure_ascii=False)}\n")
    print(out.parents[2].name, config, rc, costo, f"{time.time() - t0:.0f}s", flush=True)
    return rc


def hora(epoch):
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(epoch))


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("skill")
    a.add_argument("iteracion", type=Path)
    a.add_argument("--evals", help="ids separados por coma; por defecto, todas")
    a.add_argument("--configs", default=",".join(CONFIGURACIONES), help="with_skill, without_skill o las dos")
    a.add_argument("--tope", type=float, help="USD que no pasa lo gastado en todas las iteraciones de la skill")
    a.add_argument("--por-corrida", type=float, default=8, help="--max-budget-usd de cada corrida (por defecto 8)")
    a.add_argument("--ventana-5h", type=float, default=17, help="USD que caben en la ventana de 5 horas (por defecto 17)")
    a.add_argument("--ventana-7d", type=float, default=150, help="USD que caben en la ventana semanal (por defecto 150)")
    a.add_argument("--no-esperar", action="store_true", help="sale con 3 en vez de esperar el reinicio de la ventana")
    o = a.parse_args(argv)
    it = o.iteracion.resolve()
    pruebas = json.loads((PRUEBAS / o.skill / "evals.json").read_text())["evals"]
    configs = o.configs.split(",")
    if not set(configs) <= set(CONFIGURACIONES):
        a.error(f"--configs: {o.configs}; las configuraciones son {', '.join(CONFIGURACIONES)}")
    ids = {int(x) for x in o.evals.split(",")} if o.evals else None
    plugin = it / "plugin"
    if "with_skill" in configs and not instantanea(RAIZ, plugin):
        print(f"PLUGIN {plugin} no es igual a skills/: las corridas de una iteración prueban una sola versión. "
              "Arma otra iteración o borra esa copia.", flush=True)
        return 2
    iteraciones = sorted(it.parent.glob("iteration-*"))
    trabajos = pendientes(pruebas, configs, ids, hechas(filas([it])))
    porid = {f"eval-{p['id']}-{p['name']}": p for p in pruebas}
    print("PENDIENTES", len(trabajos), flush=True)
    cortes = set()
    while trabajos:
        nombre, config = trabajos[0]
        todas = filas(iteraciones)
        costo = estimado(todas, nombre, config, o.por_corrida)
        if o.tope is not None and gastado(todas) + costo > o.tope:
            print("TOPE", nombre, config, f"gastado {gastado(todas):.2f} + {costo:.2f} > {o.tope:.2f}", flush=True)
            return 4
        accion, hasta = decidir(uso(list(it.parent.glob("iteration-*/eval-*/*/run-*/outputs/transcript.jsonl"))),
                                time.time(), costo, o.ventana_5h, o.ventana_7d)
        if accion == "parar":
            print("PARA", nombre, config, f"no entra en la ventana {'semanal, se reinicia ' + hora(hasta) if hasta else 'de 5 horas'}", flush=True)
            return 3
        if accion == "esperar":
            print("ESPERA", nombre, config, f"hasta {hora(hasta)}", flush=True)
            if o.no_esperar:
                return 3
            time.sleep(max(0, hasta - time.time()) + 60)
            continue
        out = it / nombre / config / "run-1" / "outputs"
        if not limpia(out):
            print("SUCIO", nombre, config, flush=True)
            trabajos.pop(0)
            continue
        correr(porid[nombre], config, it, plugin, o.por_corrida)
        if cortada(out / "transcript.jsonl"):
            print("LIMITE", nombre, config, flush=True)
            if o.no_esperar or (nombre, config) in cortes:
                return 3
            cortes.add((nombre, config))
            continue
        trabajos.pop(0)
    print("FIN", f"{gastado(filas(iteraciones)):.2f}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
