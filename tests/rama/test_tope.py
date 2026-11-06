"""B2: el tope de `fetch` y `ls-remote` corta aunque un hijo de git siga vivo con su stderr, como pasa en Windows,
donde matar a git no mata al hijo que habla con el servidor. En Linux se simula la rama de Windows: `rama.py`
decide por `os.name`, y sin `taskkill` mata solo a git, como haría `kill()` sin el árbol.

No es una prueba de CLI: mira la rama de Windows del código. La de verdad corre en la VM de Windows (issue 45).
Uso: python3 -m unittest discover -s tests/rama -v
"""
import importlib.util
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from repos import ENTORNO, SCRIPT, git


def cargar_rama():
    spec = importlib.util.spec_from_file_location("rama_bajo_prueba", SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class TopeEnWindows(unittest.TestCase):
    def test_b2_corta_aunque_el_hijo_de_git_siga_vivo(self):
        rama = cargar_rama()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            git("init", "-q", "--bare", str(tmp / "servidor.git"), cwd=tmp)
            git("init", "-q", str(tmp / "copia"), cwd=tmp)
            git("remote", "add", "origin", str(tmp / "servidor.git"), cwd=tmp / "copia")
            lento = tmp / "lento.sh"
            lento.write_text("#!/bin/sh\nsleep 20\n", encoding="utf-8")
            lento.chmod(0o755)
            git("config", "remote.origin.uploadpack", str(lento), cwd=tmp / "copia")
            with mock.patch.dict(os.environ, ENTORNO, clear=True), mock.patch.object(rama.os, "name", "nt"):
                inicio = time.monotonic()
                resultado = rama.Git(str(tmp / "copia")).correr("fetch", "origin", tope=2)
                tardo = time.monotonic() - inicio
        self.assertEqual(resultado.returncode, 124)
        self.assertLess(tardo, 12, "el tope esperó al hijo de git")


if __name__ == "__main__":
    unittest.main()
