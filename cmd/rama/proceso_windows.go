//go:build windows

package main

import (
	"context"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"time"
)

// matarElArbolAlCancelar mata, al vencer el tope, a git y a los hijos que lanzó con `taskkill /T /F`: en Windows
// matar a git no mata a `git-remote-https`, que sigue esperando al servidor. Probado en Windows 11 con el `git.exe`
// de `cmd\`, que lanza otro `git.exe`, el del `fetch` y `git-remote-https.exe` (issue 45).
func matarElArbolAlCancelar(orden *exec.Cmd) {
	orden.Cancel = func() error {
		ctx, cancelar := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancelar()
		taskkill := "taskkill"
		if raiz := os.Getenv("SystemRoot"); raiz != "" {
			taskkill = filepath.Join(raiz, "System32", "taskkill.exe")
		}
		_ = exec.CommandContext(ctx, taskkill, "/T", "/F", "/PID", strconv.Itoa(orden.Process.Pid)).Run()
		return orden.Process.Kill()
	}
}
