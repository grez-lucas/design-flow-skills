"""Pruebas de pruebas/lanzar.py: comando de cada corrida, reanudación, tope, límite de uso de la cuenta.

No llaman a Claude: la prueba de punta a punta pone un `claude` falso primero en el PATH.
Uso: python3 -m unittest discover -s tests/pruebas -v
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PRUEBAS = RAIZ / "pruebas"
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("lanzar", PRUEBAS / "lanzar.py")
L = importlib.util.module_from_spec(spec)
spec.loader.exec_module(L)

PRUEBA = {"id": 1, "name": "chico-con-ds", "prompt": "Pásalo al repositorio.",
          "reglas": "Repositorio en <outputs>/repo. Mockup en <insumos>/chico.html."}


def temporal(test):
    d = Path(tempfile.mkdtemp())
    test.addCleanup(shutil.rmtree, d)
    return d


def evento(u5, r5, u7, r7, estado="allowed"):
    return {"type": "rate_limit_event", "rate_limit_info": {"status": estado, "unifiedWindows": {
        "five_hour": {"utilization": u5, "resetsAt": r5, "status": estado},
        "seven_day": {"utilization": u7, "resetsAt": r7, "status": "allowed"}}}}


def escribir_transcript(path, *mensajes):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(m) + "\n" for m in mensajes))


class Comando(unittest.TestCase):
    def test_con_la_skill_carga_el_plugin_y_sin_ella_no(self):
        out, insumos, plugin = Path("/it/eval-1/x/run-1/outputs"), Path("/it/insumos"), Path("/it/plugin")
        con = L.comando(PRUEBA, "with_skill", out, insumos, plugin, 8)
        sin = L.comando(PRUEBA, "without_skill", out, insumos, plugin, 8)
        self.assertEqual(con[con.index("--plugin-dir") + 1], str(plugin))
        self.assertNotIn("--plugin-dir", sin)
        self.assertEqual(con[:2], ["claude", "-p"])
        self.assertEqual(con[2], "Pásalo al repositorio.\n\nRepositorio en /it/eval-1/x/run-1/outputs/repo. Mockup en /it/insumos/chico.html.")
        self.assertEqual(con[con.index("--max-budget-usd") + 1], "8")
        self.assertEqual(con[con.index("--add-dir") + 1], str(insumos))
        self.assertIn("--strict-mcp-config", con)

    def test_bash_solo_con_las_ordenes_permitidas(self):
        cmd = L.comando(PRUEBA, "with_skill", Path("/o"), Path("/i"), Path("/p"), 8)
        permitidas = cmd[cmd.index("--allowedTools") + 1:]
        permitidas = permitidas[:next((n for n, x in enumerate(permitidas) if x.startswith("--")), len(permitidas))]
        self.assertNotIn("Bash", permitidas)
        self.assertTrue(all(not p.startswith("Bash") or p.startswith("Bash(") for p in permitidas), permitidas)
        self.assertIn("Bash(python3:*)", permitidas)
        self.assertIn("Agent", permitidas)

    def test_sin_subagentes_niega_agent_y_task(self):
        cmd = L.comando(dict(PRUEBA, arnes=["sin-subagentes"]), "with_skill", Path("/o"), Path("/i"), Path("/p"), 8)
        negadas = cmd[cmd.index("--disallowedTools") + 1:]
        self.assertIn("Agent", negadas)
        self.assertIn("Task", negadas)
        self.assertNotIn("--disallowedTools", L.comando(PRUEBA, "with_skill", Path("/o"), Path("/i"), Path("/p"), 8))

    def test_sin_navegador_niega_chrome_y_lo_saca_del_path(self):
        it = temporal(self)
        prueba = dict(PRUEBA, arnes=["sin-navegador"])
        cmd = L.comando(prueba, "with_skill", Path("/o"), Path("/i"), Path("/p"), 8)
        negadas = cmd[cmd.index("--disallowedTools") + 1:]
        for orden in ("Bash(google-chrome:*)", "Bash(npx:*)", "Bash(node:*)"):
            self.assertIn(orden, negadas)
        env = L.entorno(prueba, it, {"PATH": "/usr/bin:/bin", "HOME": "/h"}, "/opt/claude/bin/claude")
        dirs = env["PATH"].split(":")
        self.assertEqual(dirs[0], "/opt/claude/bin")
        binarios = {p.name for d in dirs[1:] for p in Path(d).iterdir()}
        self.assertIn("git", binarios)
        self.assertFalse([b for b in binarios if "chrom" in b or "playwright" in b])
        self.assertTrue(env["PLAYWRIGHT_BROWSERS_PATH"].startswith(str(it)))
        self.assertEqual(env["HOME"], "/h")
        self.assertEqual(L.entorno(PRUEBA, it, {"PATH": "/usr/bin"}, "/x/claude"), {"PATH": "/usr/bin"})


class Corridas(unittest.TestCase):
    def tsv(self, carpeta, nombre, filas):
        carpeta.mkdir(parents=True, exist_ok=True)
        (carpeta / nombre).write_text("".join("\t".join(map(str, f)) + "\n" for f in filas))

    def test_reanuda_salteando_las_que_terminaron_bien(self):
        it = temporal(self) / "iteration-2"
        self.tsv(it, "corridas.tsv", [("eval-1-chico-con-ds", "with_skill", 0, 3.2, 400, "[]"),
                                      ("eval-2-chico-sin-ds", "with_skill", 1, 2.7, 300, "[]")])
        self.tsv(it, "corridas-intento-1.tsv", [("eval-3-grande-con-ds", "with_skill", 1, 0.9, 140, "[]")])
        pruebas = [{"id": n, "name": x} for n, x in ((1, "chico-con-ds"), (2, "chico-sin-ds"), (3, "grande-con-ds"))]
        hechas = L.hechas(L.filas([it]))
        self.assertEqual(L.pendientes(pruebas, ["with_skill", "without_skill"], None, hechas), [
            ("eval-1-chico-con-ds", "without_skill"), ("eval-2-chico-sin-ds", "with_skill"),
            ("eval-2-chico-sin-ds", "without_skill"), ("eval-3-grande-con-ds", "with_skill"),
            ("eval-3-grande-con-ds", "without_skill")])
        self.assertEqual(L.pendientes(pruebas, ["with_skill"], {3}, hechas), [("eval-3-grande-con-ds", "with_skill")])

    def test_el_tope_suma_todas_las_iteraciones_y_el_costo_sale_de_corridas_anteriores(self):
        skill = temporal(self)
        self.tsv(skill / "iteration-1", "corridas.tsv", [("eval-3-grande-con-ds", "with_skill", 0, 5.0, 600, "[]"),
                                                         ("eval-3-grande-con-ds", "with_skill", 1, 1.5, 100, "[]")])
        self.tsv(skill / "iteration-2", "corridas.tsv", [("eval-3-grande-con-ds", "with_skill", 0, 7.25, 700, "[]"),
                                                         ("eval-1-chico-con-ds", "with_skill", 1, "", 2, "[]")])
        f = L.filas(sorted(skill.glob("iteration-*")))
        self.assertAlmostEqual(L.gastado(f), 13.75)
        self.assertEqual(L.estimado(f, "eval-3-grande-con-ds", "with_skill", 8), 7.25)
        self.assertEqual(L.estimado(f, "eval-1-chico-con-ds", "with_skill", 8), 8)
        self.assertEqual(L.estimado(f, "eval-3-grande-con-ds", "without_skill", 8), 8)


class LimiteDeUso(unittest.TestCase):
    def test_lee_la_ultima_medicion_del_transcript_mas_reciente(self):
        d = temporal(self)
        viejo, nuevo = d / "a" / "transcript.jsonl", d / "b" / "transcript.jsonl"
        escribir_transcript(viejo, evento(0.9, 100, 0.5, 900))
        escribir_transcript(nuevo, {"type": "system", "subtype": "init"}, evento(0.2, 200, 0.6, 900),
                            {"type": "rate_limit_event", "rate_limit_info": {"status": "allowed"}}, evento(0.35, 200, 0.61, 900))
        os.utime(viejo, (1000, 1000))
        os.utime(nuevo, (2000, 2000))
        self.assertEqual(L.uso([viejo, nuevo]), {"five_hour": (0.35, 200), "seven_day": (0.61, 900)})
        self.assertIsNone(L.uso([]))

    def test_lanza_si_la_corrida_entra_en_lo_que_queda_de_la_ventana(self):
        uso = {"five_hour": (0.40, 5000), "seven_day": (0.50, 90000)}
        self.assertEqual(L.decidir(uso, 1000, 7.0, 17, 150), ("lanzar", None))
        self.assertEqual(L.decidir(None, 1000, 7.0, 17, 150), ("lanzar", None))

    def test_espera_al_reinicio_si_la_corrida_no_entra_en_la_ventana_de_5_horas(self):
        uso = {"five_hour": (0.54, 5000), "seven_day": (0.50, 90000)}
        self.assertEqual(L.decidir(uso, 1000, 7.0, 17, 150), ("esperar", 5000))
        self.assertEqual(L.decidir(uso, 5000, 7.0, 17, 150), ("lanzar", None))

    def test_para_si_no_entra_en_la_semana_o_no_entra_en_ninguna_ventana(self):
        self.assertEqual(L.decidir({"five_hour": (0.0, 5000), "seven_day": (0.92, 90000)}, 1000, 7.0, 17, 150), ("parar", 90000))
        self.assertEqual(L.decidir({"five_hour": (0.92, 5000), "seven_day": (0.92, 90000)}, 1000, 7.0, 17, 150), ("parar", 90000))
        self.assertEqual(L.decidir({"five_hour": (0.0, 5000), "seven_day": (0.1, 90000)}, 1000, 20.0, 17, 150), ("parar", None))

    def test_detecta_la_corrida_cortada_por_el_limite(self):
        d = temporal(self)
        t = d / "transcript.jsonl"
        escribir_transcript(t, {"type": "result", "is_error": True, "api_error": "usage_limit_reached", "total_cost_usd": 3.9})
        self.assertTrue(L.cortada(t))
        escribir_transcript(t, {"type": "result", "total_cost_usd": 3.9})
        self.assertFalse(L.cortada(t))
        self.assertFalse(L.cortada(d / "no-existe.jsonl"))


class Preparacion(unittest.TestCase):
    def git(self, repo, *args):
        env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com", "GIT_COMMITTER_NAME": "t",
               "GIT_COMMITTER_EMAIL": "t@example.com", "PATH": os.environ["PATH"]}
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=env)

    def salida(self):
        out = temporal(self) / "outputs"
        (out / "repo").mkdir(parents=True)
        (out / "repo" / "a.txt").write_text("a\n")
        self.git(out / "repo", "init", "-q", "-b", "main")
        self.git(out / "repo", "add", "-A")
        self.git(out / "repo", "commit", "-q", "-m", "estado inicial")
        return out

    def test_limpia_deja_la_salida_como_al_preparar(self):
        out = self.salida()
        (out / "trabajo").mkdir()
        (out / "trabajo" / "x.md").write_text("x")
        (out / "notas.md").write_text("n")
        (out / "transcript.jsonl").write_text("{}\n")
        self.assertTrue(L.limpia(out))
        self.assertEqual(sorted(p.name for p in out.iterdir()), ["repo", "transcript.jsonl"])

    def test_no_limpia_un_repositorio_con_cambios_o_commits_nuevos(self):
        out = self.salida()
        (out / "repo" / "a.txt").write_text("b\n")
        self.assertFalse(L.limpia(out))
        self.git(out / "repo", "commit", "-qam", "cambio")
        self.assertFalse(L.limpia(out))

    def test_la_copia_del_plugin_queda_fija_para_toda_la_iteracion(self):
        raiz = temporal(self)
        for archivo, texto in ((".claude-plugin/plugin.json", "{}"), ("skills/s/SKILL.md", "uno"), ("README.md", "r")):
            (raiz / archivo).parent.mkdir(parents=True, exist_ok=True)
            (raiz / archivo).write_text(texto)
        (raiz / "skills" / "s" / "__pycache__").mkdir()
        (raiz / "skills" / "s" / "__pycache__" / "x.pyc").write_text("b")
        destino = temporal(self) / "plugin"
        self.assertTrue(L.instantanea(raiz, destino))
        self.assertEqual(sorted(p.relative_to(destino).as_posix() for p in destino.rglob("*") if p.is_file()),
                         [".claude-plugin/plugin.json", "skills/s/SKILL.md"])
        self.assertTrue(L.instantanea(raiz, destino))
        (raiz / "skills" / "s" / "SKILL.md").write_text("dos")
        self.assertFalse(L.instantanea(raiz, destino))
        self.assertEqual((destino / "skills" / "s" / "SKILL.md").read_text(), "uno")


FALSO = """#!{python}
import json, os, sys
from pathlib import Path
with open(os.environ["LLAMADAS"], "a") as f:
    f.write(json.dumps(sys.argv[1:]) + "\\n")
modo = os.environ.get("MODO", "bien")
print(json.dumps({{"type": "system", "subtype": "init"}}))
print(json.dumps({{"type": "rate_limit_event", "rate_limit_info": {{"status": "allowed", "unifiedWindows": {{
    "five_hour": {{"utilization": 0.3, "resetsAt": 4102444800, "status": "allowed"}},
    "seven_day": {{"utilization": 0.4, "resetsAt": 4102444800, "status": "allowed"}}}}}}}}))
if modo == "limite":
    print(json.dumps({{"type": "result", "is_error": True, "api_error": "usage_limit_reached", "total_cost_usd": 1.5,
                      "permission_denials": []}}))
    sys.exit(1)
Path("notas.md").write_text("informe\\n")
print(json.dumps({{"type": "result", "total_cost_usd": 2.5, "permission_denials": [{{"tool_name": "Bash"}}]}}))
"""


class PuntaAPunta(unittest.TestCase):
    """lanzar.py con un claude falso: prepara la iteración, corre, anota, reanuda y para en el límite."""

    def preparar(self):
        base = temporal(self)
        it = base / "html-a-vista" / "iteration-1"
        subprocess.run([sys.executable, str(PRUEBAS / "preparar.py"), "html-a-vista", str(it)], check=True, capture_output=True)
        binario = base / "bin"
        binario.mkdir()
        (binario / "claude").write_text(FALSO.format(python=sys.executable))
        (binario / "claude").chmod(0o755)
        llamadas = base / "llamadas.jsonl"
        env = dict(os.environ, PATH=f"{binario}:{os.environ['PATH']}", LLAMADAS=str(llamadas))
        return it, env, llamadas

    def lanzar(self, it, env, *args):
        return subprocess.run([sys.executable, str(PRUEBAS / "lanzar.py"), "html-a-vista", str(it), *args],
                              capture_output=True, text=True, env=env, timeout=120)

    def test_corre_anota_y_reanuda(self):
        it, env, llamadas = self.preparar()
        r = self.lanzar(it, env, "--evals", "1,11", "--configs", "with_skill", "--no-esperar")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        filas = [l.split("\t") for l in (it / "corridas.tsv").read_text().splitlines()]
        self.assertEqual([f[:4] for f in filas], [["eval-1-chico-con-ds", "with_skill", "0", "2.5"],
                                                  ["eval-11-chico-sin-subagentes", "with_skill", "0", "2.5"]])
        self.assertEqual(json.loads(filas[0][5]), [{"tool_name": "Bash"}])
        self.assertTrue((it / "eval-1-chico-con-ds" / "with_skill" / "run-1" / "outputs" / "notas.md").is_file())
        self.assertTrue((it / "plugin" / "skills" / "html-a-vista" / "SKILL.md").is_file())
        argv = [json.loads(l) for l in llamadas.read_text().splitlines()]
        self.assertEqual(argv[0][argv[0].index("--plugin-dir") + 1], str(it / "plugin"))
        self.assertNotIn("--disallowedTools", argv[0])
        self.assertIn("Agent", argv[1][argv[1].index("--disallowedTools") + 1:])
        r = self.lanzar(it, env, "--evals", "1,11", "--configs", "with_skill", "--no-esperar")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(len(llamadas.read_text().splitlines()), 2)
        self.assertIn("PENDIENTES 0", r.stdout)

    def test_no_lanza_si_pasaria_el_tope(self):
        it, env, llamadas = self.preparar()
        (it / "corridas.tsv").write_text("eval-2-chico-sin-ds\twith_skill\t0\t115.0\t10\t[]\n")
        r = self.lanzar(it, env, "--evals", "1", "--configs", "with_skill", "--tope", "120", "--no-esperar")
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(llamadas.exists())
        self.assertIn("TOPE", r.stdout)

    def test_sin_esperar_sale_si_la_ventana_no_alcanza(self):
        it, env, llamadas = self.preparar()
        escribir_transcript(it / "eval-2-chico-sin-ds" / "with_skill" / "run-1" / "outputs" / "transcript.jsonl",
                            evento(0.9, 4102444800, 0.3, 4102444800))
        r = self.lanzar(it, env, "--evals", "1", "--configs", "with_skill", "--no-esperar")
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertFalse(llamadas.exists())
        self.assertIn("ESPERA", r.stdout)

    def test_para_cuando_una_corrida_choca_con_el_limite(self):
        it, env, llamadas = self.preparar()
        env["MODO"] = "limite"
        r = self.lanzar(it, env, "--evals", "1,2", "--configs", "with_skill", "--no-esperar")
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertEqual(len(llamadas.read_text().splitlines()), 1)
        self.assertIn("LIMITE", r.stdout)
        fila = (it / "corridas.tsv").read_text().split("\t")
        self.assertEqual(fila[:4], ["eval-1-chico-con-ds", "with_skill", "1", "1.5"])

    def test_no_corre_con_un_plugin_distinto_del_de_la_iteracion(self):
        it, env, llamadas = self.preparar()
        (it / "plugin" / "skills" / "html-a-vista").mkdir(parents=True)
        (it / "plugin" / "skills" / "html-a-vista" / "SKILL.md").write_text("otra versión\n")
        r = self.lanzar(it, env, "--evals", "1", "--configs", "with_skill", "--no-esperar")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertFalse(llamadas.exists())


class PruebasConArnes(unittest.TestCase):
    def test_las_restricciones_del_arnes_estan_en_evals_json(self):
        pruebas = {p["name"]: p for p in json.loads((PRUEBAS / "html-a-vista" / "evals.json").read_text())["evals"]}
        self.assertEqual(pruebas["react-sin-navegador"].get("arnes"), ["sin-navegador"])
        self.assertEqual(pruebas["chico-sin-subagentes"].get("arnes"), ["sin-subagentes"])
        conocidas = {"sin-navegador", "sin-subagentes"}
        for skill in ("checklist-diseno", "grilling-es", "html-a-vista", "spec-a-html", "spec-a-tickets"):
            for p in json.loads((PRUEBAS / skill / "evals.json").read_text())["evals"]:
                self.assertLessEqual(set(p.get("arnes", [])), conocidas, f"{skill} {p['name']}")


if __name__ == "__main__":
    unittest.main()
