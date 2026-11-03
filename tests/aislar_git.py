"""Saca del entorno las variables con que git ata un proceso a un repositorio.

Dentro de `git rebase --exec` en una copia de trabajo vinculada (`git worktree`), git exporta `GIT_DIR`, y otras órdenes
exportan también `GIT_WORK_TREE`, `GIT_INDEX_FILE` y similares. Un test que las hereda y llama a git sobre un repositorio
temporal escribe en el del rebase. La lista la da `git rev-parse --local-env-vars`, la misma que git limpia al entrar a
un submódulo.

Uso desde un test: cargar este archivo con importlib y `setUpModule = aislar_git.aislar_modulo`, o pasar
`env=aislar_git.sin_repositorio(os.environ)` a cada subprocess.
"""
import os
import subprocess
import unittest
from unittest import mock


def variables_del_repositorio():
    return subprocess.run(["git", "rev-parse", "--local-env-vars"], check=True, capture_output=True,
                          text=True).stdout.split()


def sin_repositorio(entorno):
    quitar = set(variables_del_repositorio())
    return {clave: valor for clave, valor in entorno.items() if clave not in quitar}


def aislar_modulo():
    """Para `setUpModule`: quita las variables de os.environ mientras corre el módulo y las devuelve al terminar.

    Cubre los subprocess que heredan el entorno y las funciones que el test llama en el mismo proceso.
    """
    parche = mock.patch.dict(os.environ, sin_repositorio(os.environ), clear=True)
    parche.start()
    unittest.addModuleCleanup(parche.stop)
