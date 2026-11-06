//go:build !windows

package main

import (
	"os/exec"
	"syscall"
)

// matarElArbolAlCancelar lanza git en una sesión propia, sin terminal donde pedir credenciales, y al vencer el tope
// mata la sesión entera: git y los hijos que lanzó para hablar con el servidor.
func matarElArbolAlCancelar(orden *exec.Cmd) {
	orden.SysProcAttr = &syscall.SysProcAttr{Setsid: true}
	orden.Cancel = func() error {
		if err := syscall.Kill(-orden.Process.Pid, syscall.SIGKILL); err != nil {
			return orden.Process.Kill()
		}
		return nil
	}
}
