package rama

import (
	"fmt"
	"strings"
	"unicode/utf8"
)

// objeto es el JSON que escribe rama: las claves en el orden en que se agregan, como el dict de rama.py.
type objeto struct {
	pares []par
}

type par struct {
	clave string
	valor any
}

func nuevoObjeto(pares ...par) *objeto {
	o := &objeto{}
	for _, p := range pares {
		o.poner(p.clave, p.valor)
	}
	return o
}

// poner cambia el valor de una clave que ya está, sin moverla, o la agrega al final.
func (o *objeto) poner(clave string, valor any) {
	for i := range o.pares {
		if o.pares[i].clave == clave {
			o.pares[i].valor = valor
			return
		}
	}
	o.pares = append(o.pares, par{clave, valor})
}

// nulable es null en el JSON para el texto vacío: una rama que no hay, o HEAD separado.
func nulable(texto string) any {
	if texto == "" {
		return nil
	}
	return texto
}

// json escribe el objeto como `json.dumps` de Python: `, ` y `: ` entre elementos, y todo lo que no es ASCII imprimible
// escapado con \u, para que la salida llegue igual con cualquier página de códigos de la consola de Windows.
func (o *objeto) json() string {
	var b strings.Builder
	escribirValor(&b, o)
	return b.String()
}

func escribirValor(b *strings.Builder, valor any) {
	switch v := valor.(type) {
	case nil:
		b.WriteString("null")
	case string:
		escribirTexto(b, v)
	case []string:
		b.WriteByte('[')
		for i, s := range v {
			if i > 0 {
				b.WriteString(", ")
			}
			escribirTexto(b, s)
		}
		b.WriteByte(']')
	case *objeto:
		b.WriteByte('{')
		for i, p := range v.pares {
			if i > 0 {
				b.WriteString(", ")
			}
			escribirTexto(b, p.clave)
			b.WriteString(": ")
			escribirValor(b, p.valor)
		}
		b.WriteByte('}')
	default:
		// rama solo guarda texto, listas de texto, objetos y null; otro tipo sale como su texto.
		escribirTexto(b, fmt.Sprint(v))
	}
}

func escribirTexto(b *strings.Builder, s string) {
	b.WriteByte('"')
	for len(s) > 0 {
		r, n := utf8.DecodeRuneInString(s)
		s = s[n:]
		switch {
		case r == '"':
			b.WriteString(`\"`)
		case r == '\\':
			b.WriteString(`\\`)
		case r == '\n':
			b.WriteString(`\n`)
		case r == '\r':
			b.WriteString(`\r`)
		case r == '\t':
			b.WriteString(`\t`)
		case r == '\b':
			b.WriteString(`\b`)
		case r == '\f':
			b.WriteString(`\f`)
		case r >= ' ' && r <= '~':
			b.WriteRune(r)
		case r > 0xFFFF:
			r -= 0x10000
			fmt.Fprintf(b, `\u%04x\u%04x`, 0xD800+(r>>10), 0xDC00+(r&0x3FF))
		default:
			// Un byte que no es UTF-8 llega como utf8.RuneError, U+FFFD, como el errors="replace" de rama.py.
			fmt.Fprintf(b, `\u%04x`, r)
		}
	}
	b.WriteByte('"')
}
