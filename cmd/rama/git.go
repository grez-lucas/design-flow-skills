package main

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

// codigoTope es el código de salida de una orden de git que no terminó antes del tope, como `timeout`.
const codigoTope = 124

// esperaDeTuberias es lo que se espera a que se cierren las tuberías de git después de que git terminó o se lo mató:
// un hijo que sigue vivo con la salida de git abierta no deja terminar a rama (B2).
const esperaDeTuberias = 5 * time.Second

// Git corre git en un repositorio, sin pedir credenciales por la terminal y con las rutas sin escapar.
type Git struct {
	repo string
}

type resultado struct {
	codigo int
	stdout string
	stderr string
}

// correr corre git y devuelve su código y su salida. Si git no arranca, el código es -1 y stderr dice por qué.
func (g Git) correr(args ...string) resultado {
	return g.correrConTope(0, args...)
}

// correrConTope mata a git y a lo que haya lanzado si no termina en `tope`, y devuelve el código 124. Sin tope, espera.
func (g Git) correrConTope(tope time.Duration, args ...string) resultado {
	ctx := context.Background()
	if tope > 0 {
		var cancelar context.CancelFunc
		ctx, cancelar = context.WithTimeout(ctx, tope)
		defer cancelar()
	}
	orden := exec.CommandContext(ctx, "git", append([]string{"-c", "core.quotePath=false", "-C", g.repo}, args...)...)
	orden.Env = append(os.Environ(), "GIT_TERMINAL_PROMPT=0")
	var salida, errores bytes.Buffer
	orden.Stdout, orden.Stderr = &salida, &errores
	matarElArbolAlCancelar(orden)
	orden.WaitDelay = esperaDeTuberias
	err := orden.Run()
	if tope > 0 && errors.Is(ctx.Err(), context.DeadlineExceeded) {
		return resultado{codigoTope, "", fmt.Sprintf("el servidor no respondió en %d segundos", int(tope/time.Second))}
	}
	r := resultado{0, salida.String(), errores.String()}
	var salidaDeGit *exec.ExitError
	switch {
	case err == nil:
	case errors.As(err, &salidaDeGit):
		r.codigo = salidaDeGit.ExitCode()
	case errors.Is(err, exec.ErrWaitDelay) && orden.ProcessState != nil:
		// git terminó pero un hijo dejó abiertas sus tuberías: vale el código de git.
		r.codigo = orden.ProcessState.ExitCode()
	default:
		r.codigo, r.stderr = -1, err.Error()
	}
	return r
}

// salida es la salida de git sin los espacios de los extremos, y false si git falló.
func (g Git) salida(args ...string) (string, bool) {
	r := g.correr(args...)
	if r.codigo != 0 {
		return "", false
	}
	return strings.TrimSpace(r.stdout), true
}

// lineas son las líneas de la salida, sin quitar los espacios del comienzo, que en `git status` son datos.
func (g Git) lineas(args ...string) []string {
	r := g.correr(args...)
	if r.codigo != 0 {
		return nil
	}
	return noVacias(strings.Split(sinRetornos(r.stdout), "\n"))
}

// rutas son las rutas de una orden con `-z`.
func (g Git) rutas(args ...string) []string {
	r := g.correr(args...)
	if r.codigo != 0 {
		return nil
	}
	return noVacias(strings.Split(r.stdout, "\x00"))
}

// hacer corre una orden que cambia la copia: si git falla, para con su mensaje.
func (g Git) hacer(args ...string) *parada {
	r := g.correr(args...)
	if r.codigo != 0 {
		return nuevaParada("error-de-git", fmt.Sprintf("`git %s` falló: %s", strings.Join(args, " "),
			strings.TrimSpace(r.stderr)), g.rama())
	}
	return nil
}

func (g Git) existe(ref string) bool {
	return g.correr("rev-parse", "--verify", "--quiet", ref).codigo == 0
}

// rama es la rama actual, o "" con HEAD separado.
func (g Git) rama() string {
	rama, _ := g.salida("symbolic-ref", "--quiet", "--short", "HEAD")
	return rama
}

// enLaCopia es una ruta que da git relativa a la carpeta del repositorio, o la ruta tal cual si es absoluta.
func (g Git) enLaCopia(ruta string) string {
	if filepath.IsAbs(ruta) {
		return ruta
	}
	return filepath.Join(g.repo, ruta)
}

// tope es lo que se espera al servidor: `RAMA_TOPE` segundos, o 60 si no está o no es un número.
func tope() time.Duration {
	segundos, err := strconv.Atoi(strings.TrimSpace(os.Getenv("RAMA_TOPE")))
	if err != nil {
		segundos = 60
	}
	return time.Duration(max(1, segundos)) * time.Second
}

// sinRetornos lee la salida de git como texto: `\r\n` y `\r` son fin de línea, como en Python con text=True.
func sinRetornos(texto string) string {
	return strings.ReplaceAll(strings.ReplaceAll(texto, "\r\n", "\n"), "\r", "\n")
}

func noVacias(partes []string) []string {
	var llenas []string
	for _, p := range partes {
		if p != "" {
			llenas = append(llenas, p)
		}
	}
	return llenas
}
