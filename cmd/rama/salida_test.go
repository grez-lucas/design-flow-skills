package main

import "testing"

// Las salidas esperadas son las de `json.dumps` de Python para los mismos valores, como las escribía rama.py.
func TestJSONComoElDeRamaPy(t *testing.T) {
	casos := []struct {
		objeto *objeto
		python string
	}{
		{nuevoObjeto(par{"accion", "guardar"}, par{"rama", "main"}, par{"principal", "main"}),
			`{"accion": "guardar", "rama": "main", "principal": "main"}`},
		{nuevoObjeto(par{"a", "señal ñ é 😀"}, par{"b", []string{"x\ty", `q"\\/<>&`}}, par{"c", nil},
			par{"d", []string{}}),
			`{"a": "se\u00f1al \u00f1 \u00e9 \ud83d\ude00", "b": ["x\ty", "q\"\\\\/<>&"], "c": null, "d": []}`},
		{nuevoObjeto(par{"x", "\x00\x01\x1f\x7f\n\r\b\f"}), `{"x": "\u0000\u0001\u001f\u007f\n\r\b\f"}`},
		{nuevoObjeto(par{"roto", "a\xffb"}), `{"roto": "a\ufffdb"}`},
		{nuevoObjeto(par{"lista", []string(nil)}), `{"lista": []}`},
	}
	for _, c := range casos {
		if got := c.objeto.json(); got != c.python {
			t.Errorf("json() = %s\n          quiero %s", got, c.python)
		}
	}
}

func TestPonerCambiaElValorSinMoverLaClave(t *testing.T) {
	o := nuevoObjeto(par{"accion", "parar"}, par{"rama", "main"}, par{"motivo", "x"})
	o.poner("rama", nil)
	o.poner("apartado", []string{})
	if got, quiero := o.json(), `{"accion": "parar", "rama": null, "motivo": "x", "apartado": []}`; got != quiero {
		t.Errorf("json() = %s, quiero %s", got, quiero)
	}
}

func TestNuevaParadaLlevaSoloLosExtrasConValor(t *testing.T) {
	p := nuevaParada("cambios-sin-guardar", "detalle", "", par{"principal", "main"}, par{"archivos", []string(nil)},
		par{"commits", []string{"abc uno"}})
	quiero := `{"accion": "parar", "motivo": "cambios-sin-guardar", "detalle": "detalle", "principal": "main", ` +
		`"commits": ["abc uno"]}`
	if got := p.salida.json(); got != quiero {
		t.Errorf("json() = %s, quiero %s", got, quiero)
	}
}
