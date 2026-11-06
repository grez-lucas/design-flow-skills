// Flujo es el ejecutable único de las herramientas de las skills del flujo de diseño, con un subcomando por
// herramienta (Q163). Va en `bin/` del plugin, uno por plataforma (Q152, Q162).
package main

import (
	"fmt"
	"io"
	"os"
	"sort"
	"strings"

	"github.com/grez-lucas/design-flow-skills/internal/rama"
)

// subcomandos son las herramientas de flujo: cada una recibe sus argumentos y devuelve su código de salida.
var subcomandos = map[string]func(argv []string, stdout, stderr io.Writer) int{
	"rama": rama.Correr,
}

func uso() string {
	nombres := make([]string, 0, len(subcomandos))
	for nombre := range subcomandos {
		nombres = append(nombres, nombre)
	}
	sort.Strings(nombres)
	return "Uso: flujo <subcomando> [argumentos]\n\nSubcomandos: " + strings.Join(nombres, ", ") +
		".\n`flujo <subcomando> -h` da el uso de cada uno.\n"
}

func correr(argv []string, stdout, stderr io.Writer) int {
	if len(argv) > 0 && (argv[0] == "-h" || argv[0] == "--help") {
		fmt.Fprint(stdout, uso())
		return 0
	}
	if len(argv) == 0 {
		fmt.Fprint(stderr, "flujo: falta el subcomando\n"+uso())
		return 2
	}
	subcomando, ok := subcomandos[argv[0]]
	if !ok {
		fmt.Fprintf(stderr, "flujo: subcomando desconocido '%s'\n%s", argv[0], uso())
		return 2
	}
	return subcomando(argv[1:], stdout, stderr)
}

func main() {
	os.Exit(correr(os.Args[1:], os.Stdout, os.Stderr))
}
