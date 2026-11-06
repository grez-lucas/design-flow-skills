"""Pruebas de conducta de la excepción del `.gitignore` de `spec-a-tickets` (Q157): el bloque que da su `SKILL.md` se
agrega al final del `.gitignore` de repositorios reales con distintas reglas, y `git check-ignore` dice si el puntero a
las convenciones deja de estar ignorado.
Uso: python3 -m unittest discover -s tests/rama -v
"""
import re
import tempfile
import unittest
from pathlib import Path

from test_referencia import ENTORNO, SKILLS, Repositorio, bloque_con, git


class ExcepcionDelGitignore(unittest.TestCase):
    """Q157: el bloque que `spec-a-tickets` agrega al final del `.gitignore` deja de ignorar el puntero con cualquier
    regla de la raíz, del excludes global o de `.git/info/exclude`, y `.claude/skills/` sigue ignorada."""

    CASOS = {
        "carpeta": ".claude/\n",
        "sin barra": ".claude\n",
        "desde la raíz": "/.claude/\n",
        "todo lo oculto": ".*\n",
        "en cualquier nivel": "**/.claude/\n",
        "los md de la carpeta": ".claude/*.md\n",
        "un md posterior": ".claude/\n!.claude/pm-conventions.md\n*.md\n",
    }

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        texto = (SKILLS / "spec-a-tickets" / "SKILL.md").read_text(encoding="utf-8")
        guardar = re.search(r"^### 9\. [^\n]*\n(.*?)(?=^### )", texto, flags=re.S | re.M).group(1)
        self.bloque = bloque_con(guardar, "!.claude/")

    def repo(self, nombre):
        repo = self.tmp / nombre
        git("init", "-q", str(repo), cwd=self.tmp)
        for ruta in (".claude/pm-conventions.md", ".claude/skills/x/SKILL.md", ".claude/settings.local.json"):
            Repositorio.escribir(repo, ruta, "x\n")
        return repo

    def ignorado(self, repo, ruta, entorno=None):
        return git("check-ignore", "-q", ruta, cwd=repo, check=False, entorno=entorno).returncode == 0

    def agregar_excepcion(self, repo):
        gitignore = repo / ".gitignore"
        previo = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
        gitignore.write_text(previo + "\n".join(self.bloque) + "\n", encoding="utf-8")

    def test_m3_cada_regla_de_la_raiz_deja_de_ignorar_el_puntero(self):
        for nombre, regla in self.CASOS.items():
            with self.subTest(regla=nombre):
                repo = self.repo(re.sub(r"\W", "-", nombre))
                (repo / ".gitignore").write_text(regla, encoding="utf-8")
                # El `.gitignore` de un repositorio de diseño ya está en un commit, aunque `.*` lo ignore.
                git("add", "-f", ".gitignore", cwd=repo)
                git("commit", "-q", "-m", "gitignore", cwd=repo)
                self.assertTrue(self.ignorado(repo, ".claude/pm-conventions.md"))
                self.agregar_excepcion(repo)
                self.assertFalse(self.ignorado(repo, ".claude/pm-conventions.md"))
                self.assertTrue(self.ignorado(repo, ".claude/skills/x/SKILL.md"))
                git("add", ".claude/pm-conventions.md", ".gitignore", cwd=repo)

    def test_m3_una_regla_del_excludes_global_o_de_info_exclude_tambien(self):
        excludes = self.tmp / "excludes"
        excludes.write_text(".claude/\n", encoding="utf-8")
        con_global = {**ENTORNO, "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.excludesFile",
                      "GIT_CONFIG_VALUE_0": str(excludes)}
        repo = self.repo("global")
        self.assertTrue(self.ignorado(repo, ".claude/pm-conventions.md", con_global))
        self.agregar_excepcion(repo)
        self.assertFalse(self.ignorado(repo, ".claude/pm-conventions.md", con_global))
        repo = self.repo("info")
        (repo / ".git" / "info" / "exclude").write_text(".claude/\n", encoding="utf-8")
        self.agregar_excepcion(repo)
        self.assertFalse(self.ignorado(repo, ".claude/pm-conventions.md"))

    def test_m3_una_regla_mas_adentro_sigue_ignorandolo_y_el_texto_dice_que_hacer(self):
        repo = self.repo("adentro")
        (repo / ".claude" / ".gitignore").write_text("*\n", encoding="utf-8")
        self.agregar_excepcion(repo)
        self.assertTrue(self.ignorado(repo, ".claude/pm-conventions.md"))
        texto = (SKILLS / "spec-a-tickets" / "SKILL.md").read_text(encoding="utf-8")
        self.assertRegex(texto, r"Detente\. Si `git check-ignore \.claude/pm-conventions\.md` sigue respondiendo, la regla está "
                                r"fuera del `\.gitignore` de la raíz: muestra la línea que da `git check-ignore -v "
                                r"\.claude/pm-conventions\.md`")
        self.assertNotIn("git add -f", texto)


if __name__ == "__main__":
    unittest.main()
