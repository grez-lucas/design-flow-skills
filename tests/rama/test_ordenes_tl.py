"""Pruebas de conducta de las órdenes que `spec-a-tickets` entrega al TL para subir los tickets (B1, B10): se leen de
`references/trackers.md`, se corren con `bash` y un `gh` y un `glab` de prueba que guardan lo que reciben, y el cuerpo
tiene que ser el archivo sin su título, con los tildes intactos.
Uso: python3 -m unittest discover -s tests/rama -v
"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
TRACKERS = RAIZ / "skills" / "spec-a-tickets" / "references" / "trackers.md"
TICKET = "# [US-REC-001] Ver facturas vencidas\n\n**Depende de:** ninguno\n\nCOMO contadora, QUIERO ver las facturas vencidas, PARA cobrarlas a tiempo: ñandú, acción, pingüino.\n"
FALSO = """#!/bin/sh
printf '%s\\n' "$@" > "$SALIDA/argumentos"
cat > "$SALIDA/entrada"
"""


@unittest.skipUnless(shutil.which("bash"), "sin bash")
class OrdenesParaElTL(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        (self.tmp / "bin").mkdir()
        for nombre in ("gh", "glab"):
            falso = self.tmp / "bin" / nombre
            falso.write_text(FALSO, encoding="utf-8")
            falso.chmod(0o755)
        tickets = self.tmp / "specs" / "recordatorios" / "tickets"
        tickets.mkdir(parents=True)
        (tickets / "01-ver-facturas.md").write_bytes(TICKET.encode("utf-8"))
        self.subir = re.search(r"^### Para que el TL los suba\n(.*?)(?=^#|\Z)", TRACKERS.read_text(encoding="utf-8"),
                               flags=re.S | re.M).group(1)

    def orden(self, comienzo):
        ordenes = [o for o in re.findall(r"`([^`]+)`", self.subir) if re.search(rf"\b{comienzo} issue create\b", o)]
        self.assertEqual(len(ordenes), 1, f"no hay una sola orden con {comienzo}: {ordenes}")
        return (ordenes[0].replace("<épica>", "recordatorios").replace("<archivo>", "01-ver-facturas.md")
                .replace("<título>", "[US-REC-001] Ver facturas vencidas").replace("<label>", "story"))

    def correr(self, orden):
        entorno = {**os.environ, "PATH": f"{self.tmp / 'bin'}{os.pathsep}{os.environ['PATH']}", "SALIDA": str(self.tmp)}
        (self.tmp / "entrada").write_bytes(b"")
        subprocess.run(["bash", "-c", orden], cwd=self.tmp, env=entorno, check=True, stdin=subprocess.DEVNULL, timeout=30)
        return ((self.tmp / "argumentos").read_text(encoding="utf-8").splitlines(),
                (self.tmp / "entrada").read_bytes())

    def cuerpo_esperado(self):
        return TICKET.split("\n", 1)[1].encode("utf-8")

    def test_gh_recibe_el_cuerpo_sin_el_titulo_y_con_los_tildes(self):
        argumentos, entrada = self.correr(self.orden("gh"))
        self.assertEqual(entrada, self.cuerpo_esperado())
        self.assertIn("[US-REC-001] Ver facturas vencidas", argumentos)

    def test_glab_recibe_el_cuerpo_sin_el_titulo_y_con_los_tildes(self):
        argumentos, _ = self.correr(self.orden("glab"))
        descripcion = argumentos[argumentos.index("--description") + 1:argumentos.index("--label")]
        self.assertEqual("\n".join(descripcion).encode("utf-8"), self.cuerpo_esperado().rstrip(b"\n"))

    def test_no_entrega_una_orden_para_cmd_que_cambie_los_tildes(self):
        self.assertNotIn("more +1", self.subir)
        self.assertRegex(self.subir, r"En Windows, las órdenes van desde Git Bash, que viene con Git")


if __name__ == "__main__":
    unittest.main()
