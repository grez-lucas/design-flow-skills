"""B2 y N10: con `RAMA_TOPE`, `revisar` para con `sin-servidor` ante un servidor HTTPS que acepta la conexión y no
responde nunca, y no deja vivo a ningún hijo de git.

Es la prueba de la VM de Windows del issue 45, en cualquier sistema: `git fetch` por HTTPS lanza `git-remote-https`,
que en Windows no muere cuando muere git; el ejecutable tiene que matar el árbol entero. La prueba lo ve desde el
servidor falso: la conexión de `git-remote-https` tiene que cerrarse poco después de que `rama` termina. Corre contra
el ejecutable de `RAMA`, como las demás pruebas de CLI.
Uso: python3 -m unittest discover -s tests/rama -p 'test_tope.py' -v
"""
import socket
import threading
import time
import unittest

from repos import Repositorio, git

TOPE = 3
CIERRE = 10  # lo que se espera a que el sistema cierre la conexión del hijo muerto


class ServidorMudo:
    """Acepta conexiones en 127.0.0.1 y no responde nunca. Anota cuándo llegó cada una y cuándo la cerró el otro."""

    def __init__(self):
        self.escucha = socket.create_server(("127.0.0.1", 0))
        self.puerto = self.escucha.getsockname()[1]
        self.conexiones = []
        self.cerradas = []
        threading.Thread(target=self.aceptar, daemon=True).start()

    def aceptar(self):
        while True:
            try:
                conexion, _ = self.escucha.accept()
            except OSError:
                return
            self.conexiones.append(time.monotonic())
            threading.Thread(target=self.esperar_cierre, args=(conexion,), daemon=True).start()

    def esperar_cierre(self, conexion):
        with conexion:
            try:
                while conexion.recv(4096):
                    pass
            except OSError:
                pass
        self.cerradas.append(time.monotonic())

    def cerrar(self):
        self.escucha.close()


class Tope(Repositorio):
    def test_un_servidor_https_que_no_responde_para_y_no_deja_hijos_vivos(self):
        servidor = ServidorMudo()
        self.addCleanup(servidor.cerrar)
        git("remote", "set-url", "origin", f"https://127.0.0.1:{servidor.puerto}/repo.git", cwd=self.copia)
        antes = self.status(), self.rama_actual()
        entorno = {"RAMA_TOPE": str(TOPE), "NO_PROXY": "127.0.0.1", "no_proxy": "127.0.0.1",
                   "HTTPS_PROXY": "", "https_proxy": "", "ALL_PROXY": "", "all_proxy": ""}

        inicio = time.monotonic()
        salida = self.correr("revisar", "--tipo", "spec", "--epica", "alertas", entorno=entorno, tope=TOPE + 30)
        termino = time.monotonic()

        self.assertEqual((salida["accion"], salida["motivo"]), ("parar", "sin-servidor"), salida)
        self.assertIn(f"{TOPE} segundos", salida["detalle"])
        self.assertLess(termino - inicio, TOPE + 8, "el tope esperó a git o a sus hijos")
        self.assertEqual(len(servidor.conexiones), 1, "git no llegó a conectarse: la prueba no probó el tope")
        limite = time.monotonic() + CIERRE
        while not servidor.cerradas and time.monotonic() < limite:
            time.sleep(0.1)
        self.assertTrue(servidor.cerradas, f"la conexión de git seguía abierta {CIERRE} s después: quedó vivo un hijo")
        self.assertEqual((self.status(), self.rama_actual()), antes)


if __name__ == "__main__":
    unittest.main()
