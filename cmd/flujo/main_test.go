package main

import (
	"bytes"
	"strings"
	"testing"
)

func TestSubcomandos(t *testing.T) {
	casos := []struct {
		argv           []string
		codigo         int
		stdout, stderr string
	}{
		{nil, 2, "", "falta el subcomando"},
		{[]string{"otra"}, 2, "", "subcomando desconocido 'otra'"},
		{[]string{"-h"}, 0, "Subcomandos: rama.", ""},
		{[]string{"rama", "-h"}, 0, "flujo rama revisar", ""},
		{[]string{"rama", "revisar", "--tipo", "spec", "--epica", "fase-2"}, 2, "", "guion y número"},
	}
	for _, c := range casos {
		var stdout, stderr bytes.Buffer
		codigo := correr(c.argv, &stdout, &stderr)
		if codigo != c.codigo || !strings.Contains(stdout.String(), c.stdout) || !strings.Contains(stderr.String(), c.stderr) {
			t.Errorf("flujo %q: código %d, stdout %q, stderr %q", c.argv, codigo, stdout.String(), stderr.String())
		}
		if c.stdout == "" && stdout.Len() != 0 {
			t.Errorf("flujo %q escribió en stdout: %q", c.argv, stdout.String())
		}
	}
}
