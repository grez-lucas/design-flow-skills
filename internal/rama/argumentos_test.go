package rama

import (
	"bytes"
	"slices"
	"strings"
	"testing"
)

func TestRutasDeLaSkill(t *testing.T) {
	si := []string{"design/", "design", "design/vistas/a.html", "specs/x/spec.md", ".gitignore",
		".claude/pm-conventions.md", "./design/a", "design//a", `design\vistas\a.html`, "specs/../design/a"}
	no := []string{".", "notas.txt", "-A", "../fuera", "design/../notas.txt", "/design/a", ":design", ":(top)design",
		".claude/otro.md", "designs/a", "..design", ".gitignore/a"}
	for _, ruta := range si {
		if !esRutaDeLaSkill(ruta) {
			t.Errorf("esRutaDeLaSkill(%q) = false, quiero true", ruta)
		}
	}
	for _, ruta := range no {
		if esRutaDeLaSkill(ruta) {
			t.Errorf("esRutaDeLaSkill(%q) = true, quiero false", ruta)
		}
	}
}

func TestNormalizarComoPosixpath(t *testing.T) {
	// Los valores de posixpath.normpath de Python.
	casos := map[string]string{"": ".", "a/./b": "a/b", "a//b/": "a/b", "a/../..": "..", "../a/../b": "../b",
		"/../a": "/a", "a/b/../../c": "c"}
	for ruta, quiero := range casos {
		if got := normalizar(ruta); got != quiero {
			t.Errorf("normalizar(%q) = %q, quiero %q", ruta, got, quiero)
		}
	}
}

func TestProblemaDelNombre(t *testing.T) {
	bien := []string{"riego", "fase2", "fase-dos-b", "señales", "acción-1a"}
	for _, valor := range bien {
		if p := problemaDelNombre(valor); p != "" {
			t.Errorf("problemaDelNombre(%q) = %q, quiero que sirva", valor, p)
		}
	}
	mal := map[string]string{"": "minúsculas", "riego nuevo": "minúsculas", "riego/norte": "minúsculas",
		"Riego": "minúsculas", "Señales": "minúsculas", "riego-": "minúsculas", "-riego": "minúsculas",
		"riego_norte": "minúsculas", "fase-2": "fase-dos", "riego-10": "guion y número"}
	for valor, texto := range mal {
		if p := problemaDelNombre(valor); !strings.Contains(p, texto) {
			t.Errorf("problemaDelNombre(%q) = %q, quiero que diga %q", valor, p, texto)
		}
	}
}

func TestLeerArgumentos(t *testing.T) {
	a, _, err := leerArgumentos([]string{"commit", "-m", "uno", "-mdos", "--repo=/r", "--", "design/", "-A"})
	if err == nil {
		t.Fatalf("una ruta -A después de -- tiene que fallar: %+v", a)
	}
	a, _, err = leerArgumentos([]string{"commit", "-m", "uno", "-mdos", "--repo=/r", "--", "design/", "specs/x"})
	if err != nil || !slices.Equal(a.mensajes, []string{"uno", "dos"}) || a.repo != "/r" ||
		!slices.Equal(a.rutas, []string{"design/", "specs/x"}) {
		t.Errorf("commit: %+v, %v", a, err)
	}
	a, _, err = leerArgumentos([]string{"revisar", "--tipo", "diseno", "--mockup=panel", "--epicas", "riego,alertas"})
	if err != nil || a.nombre() != "panel" || !slices.Equal(a.epicas, []string{"riego", "alertas"}) || a.repo != "." {
		t.Errorf("revisar con mockup: %+v, %v", a, err)
	}
	_, ayuda, err := leerArgumentos([]string{"revisar", "-h"})
	if !ayuda || err != nil {
		t.Errorf("-h: ayuda=%v, %v", ayuda, err)
	}
	for _, argv := range [][]string{
		{}, {"otra"}, {"commit", "-m", "x", "design/"}, {"commit", "--", "design/"}, {"commit", "-m", "x", "--"},
		{"revisar", "--tipo", "spec"}, {"revisar", "--tipo", "feat", "--epica", "riego"},
		{"revisar", "--tipo", "spec", "--epica", "riego", "--mockup", "panel"},
		{"revisar", "--tipo", "spec", "--epica"}, {"revisar", "--tipo", "spec", "--epica", "-riego"},
		{"revisar", "--tipo", "spec", "--epica", "riego", "sobra"},
		{"revisar", "--tipo", "spec", "--epica", "riego", "--rama", "x"},
		{"rechazo", "--tipo", "diseno", "--mockup", "panel", "--epicas", "a,b"},
		{"apartar", "--tipo", "diseno", "--mockup", "panel", "--epicas", "riego"},
		{"volver", "--tipo", "diseno", "--mockup", "panel", "--epicas", "riego,riego"},
		{"revisar", "--tipo", "spec", "--mockup", "panel", "--epicas", "riego,alertas"},
	} {
		if _, _, err := leerArgumentos(argv); err == nil {
			t.Errorf("leerArgumentos(%q) no falló", argv)
		}
	}
}

func TestUsoIncorrectoSaleConDosSinStdout(t *testing.T) {
	var stdout, stderr bytes.Buffer
	if codigo := Correr([]string{"revisar", "--tipo", "spec", "--epica", "fase-2"}, &stdout, &stderr); codigo != 2 {
		t.Errorf("código %d, quiero 2", codigo)
	}
	if stdout.Len() != 0 || !strings.Contains(stderr.String(), "guion y número") {
		t.Errorf("stdout %q, stderr %q", stdout.String(), stderr.String())
	}
}

func TestLineasDeEstadoConRenombrados(t *testing.T) {
	partes := []string{"R  nuevo.md", "viejo.md", " M a b.md", "RM x", "y", "?? z", "C  copia", "original"}
	quiero := []string{"R  viejo.md -> nuevo.md", " M a b.md", "RM y -> x", "?? z", "C  original -> copia"}
	if got := lineasDeEstado(partes); !slices.Equal(got, quiero) {
		t.Errorf("lineasDeEstado = %q, quiero %q", got, quiero)
	}
	// B3: el renombrado en la segunda columna.
	if got := lineasDeEstado([]string{" R b", "a"}); !slices.Equal(got, []string{" R a -> b"}) {
		t.Errorf("renombrado en la segunda columna: %q", got)
	}
}
