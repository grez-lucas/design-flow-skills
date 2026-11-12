package rama

import (
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"regexp"
	"slices"
	"strings"
)

var (
	tipos = []string{"spec", "tickets", "diseno"}
	// rutasDeLaSkill es lo único que una skill agrega a su commit.
	rutasDeLaSkill = []string{"design/", "specs/", ".gitignore", ".claude/pm-conventions.md"}
	apartables     = []string{"otra-rama", "sin-rama", "commits-sin-empujar", "cambios-sin-guardar",
		"principal-adelantada"}
)

// parada es una salida con `accion: parar`: un motivo, su detalle y lo que haga falta para arreglarlo.
type parada struct {
	motivo string
	salida *objeto
}

// nuevaParada lleva `rama` si la copia está en una, y de los extras solo los que tienen valor.
func nuevaParada(motivo, detalle, rama string, extras ...par) *parada {
	p := &parada{motivo, nuevoObjeto(par{"accion", "parar"}, par{"motivo", motivo}, par{"detalle", detalle})}
	if rama != "" {
		p.salida.poner("rama", rama)
	}
	for _, e := range extras {
		if tieneValor(e.valor) {
			p.salida.poner(e.clave, e.valor)
		}
	}
	return p
}

func tieneValor(valor any) bool {
	switch v := valor.(type) {
	case nil:
		return false
	case string:
		return v != ""
	case []string:
		return len(v) > 0
	}
	return true
}

// decision es lo que dice la rama actual cuando la skill puede seguir: `guardar`, `ofrecer` o `volver`.
type decision struct {
	accion, rama, principal, ramaNueva string
}

func (d decision) objeto() *objeto {
	o := nuevoObjeto(par{"accion", d.accion}, par{"rama", d.rama}, par{"principal", d.principal})
	if d.accion == "ofrecer" {
		o.poner("rama_nueva", d.ramaNueva)
	}
	return o
}

// delServidor es lo que el servidor dice tener: su rama principal y el conjunto de sus ramas.
type delServidor struct {
	principal string
	ramas     map[string]bool
}

// servidor corre `git fetch --prune` y pregunta al servidor su principal y sus ramas.
func servidor(g Git) (delServidor, *parada) {
	if _, ok := g.salida("remote", "get-url", "origin"); !ok {
		return delServidor{}, nuevaParada("sin-servidor", "El repositorio no tiene un servidor `origin` configurado.", "")
	}
	var r resultado
	for _, args := range [][]string{{"fetch", "--quiet", "--prune", "origin"},
		{"ls-remote", "--symref", "origin", "HEAD", "refs/heads/*"}} {
		r = g.correrConTope(tope(), args...)
		if r.codigo != 0 {
			return delServidor{}, nuevaParada("sin-servidor",
				"git no pudo hablar con el servidor: "+strings.TrimSpace(r.stderr), "")
		}
	}
	s := delServidor{ramas: map[string]bool{}}
	for _, linea := range strings.Split(sinRetornos(r.stdout), "\n") {
		izquierda, ref, _ := strings.Cut(linea, "\t")
		if principal, ok := strings.CutPrefix(izquierda, "ref: refs/heads/"); ok && ref == "HEAD" {
			s.principal = principal
		} else if rama, ok := strings.CutPrefix(ref, "refs/heads/"); ok {
			s.ramas[rama] = true
		}
	}
	if !s.ramas[s.principal] {
		return delServidor{}, nuevaParada("sin-principal", "El servidor no dice cuál es su rama principal.", "")
	}
	return s, nil
}

// upstream es el nombre de la rama de origin que sigue `rama`, y false si no sigue una de origin.
func upstream(g Git, rama string) (string, bool) {
	if remoto, _ := g.salida("config", "--get", "branch."+rama+".remote"); remoto != "origin" {
		return "", false
	}
	merge, _ := g.salida("config", "--get", "branch."+rama+".merge")
	return strings.CutPrefix(merge, "refs/heads/")
}

const sufijo = `(?:-(?:[2-9]|[1-9][0-9]+))?`

// esDelFlujo dice si `rama` es `<tipo>/<nombre>`, con o sin sufijo (`-2`, `-3`), para alguno de `tiposValidos`.
func esDelFlujo(rama, nombre string, tiposValidos ...string) bool {
	patron := `^(?:` + strings.Join(tiposValidos, "|") + `)/` + regexp.QuoteMeta(nombre) + sufijo + `$`
	return regexp.MustCompile(patron).MatchString(rama)
}

// ramaDelFlujo es lo que dice la rama actual, sin mirar el trabajo sin guardar: `guardar`, `ofrecer`, `volver` o
// una parada.
func ramaDelFlujo(g Git, a argumentos, s delServidor) (decision, *parada) {
	return ramaDelFlujoDe(g, a, s, g.rama())
}

// ramaDelFlujoDe es lo que diría `ramaDelFlujo` con la copia en `actual`.
func ramaDelFlujoDe(g Git, a argumentos, s delServidor, actual string) (decision, *parada) {
	if actual == "" {
		return decision{}, nuevaParada("sin-rama", "La copia no está en ninguna rama.", "", par{"principal", s.principal})
	}
	if actual == s.principal {
		return decision{"guardar", actual, s.principal, ""}, nil
	}
	sigue, conUpstream := upstream(g, actual)
	// Viva: sigue a la rama del mismo nombre en el servidor, la que recibe `git push`.
	vivo := conUpstream && sigue == actual && s.ramas[sigue]
	if vivo && len(a.epicas) > 0 && slices.ContainsFunc(a.epicas, func(e string) bool { return esDelFlujo(actual, e, tipos...) }) {
		return decision{"ofrecer", actual, s.principal, primeraLibre(g, s.ramas, "diseno/"+a.mockup)}, nil
	}
	tiposDeLaRama := tipos
	if len(a.epicas) > 0 {
		tiposDeLaRama = []string{"diseno"}
	}
	if vivo && esDelFlujo(actual, a.nombre(), tiposDeLaRama...) {
		return decision{"guardar", actual, s.principal, ""}, nil
	}
	if conUpstream && !s.ramas[sigue] {
		if trabajoEnLaPrincipal(g, s.principal, actual) {
			return decision{"volver", actual, s.principal, ""}, nil
		}
		return decision{}, nuevaParada("commits-sin-empujar", fmt.Sprintf("La rama %s ya no está en el servidor y "+
			"tiene commits que el servidor no tiene.", actual), actual, par{"principal", s.principal})
	}
	if s.ramas[actual] && esDelFlujo(actual, a.nombre(), a.tipo) {
		return decision{}, nuevaParada("otra-rama", fmt.Sprintf("La rama %s es de este trabajo y está en el servidor, "+
			"pero no sigue a la del servidor: `git push` no iría a ella.", actual), actual, par{"principal", s.principal})
	}
	return decision{}, nuevaParada("otra-rama", fmt.Sprintf("La rama %s no es la principal ni una rama de este trabajo "+
		"en el servidor.", actual), actual, par{"principal", s.principal})
}

// llegaALaPrincipal dice si la skill va a guardar desde la principal: ahí, en la rama nueva que sale de ella, o al volver.
func llegaALaPrincipal(d decision) bool {
	return d.accion == "ofrecer" || d.accion == "volver" || d.rama == d.principal
}

// destinoDelFlujo es adónde vuelve `apartar` desde una rama que no es de este trabajo: la rama viva del servidor para
// este trabajo, con sufijos exactos, o la principal; "" si hay que elegir entre las candidatas.
func destinoDelFlujo(a argumentos, s delServidor, elegida string) (string, []string) {
	var candidatas []string
	for rama := range s.ramas {
		if esDelFlujo(rama, a.nombre(), a.tipo) {
			candidatas = append(candidatas, rama)
		}
	}
	slices.Sort(candidatas)
	switch {
	case len(candidatas) == 1:
		return candidatas[0], candidatas
	case len(candidatas) > 1 && slices.Contains(candidatas, elegida):
		return elegida, candidatas
	case len(candidatas) > 1:
		return "", candidatas
	}
	return s.principal, candidatas
}

// refDeLlegada es la ref a la que va de verdad el `git switch` a `rama`: la del servidor si la rama se iguala a él
// (la principal, o con `alServidor`) o si la local no existe o avanza hasta él; si no, la local, con sus commits
// propios (M1).
func refDeLlegada(g Git, rama, principal string, alServidor bool) string {
	local, remota := "refs/heads/"+rama, "refs/remotes/origin/"+rama
	if rama == principal || alServidor || !g.existe(local) {
		return remota
	}
	if g.correr("merge-base", "--is-ancestor", local, remota).codigo == 0 {
		return remota
	}
	return local
}

// llegada es la rama a la que la copia va a cambiar, o "" si se queda en la actual.
func llegada(d *decision, destino, principal string) string {
	if d == nil {
		return destino
	}
	if d.accion == "ofrecer" || d.accion == "volver" {
		return principal
	}
	return ""
}

func revisar(g Git, a argumentos, ya *delServidor) (decision, *parada) {
	var s delServidor
	if ya != nil {
		s = *ya
	} else {
		var p *parada
		if s, p = servidor(g); p != nil {
			return decision{}, p
		}
	}
	desde := g.rama()
	d, p := ramaDelFlujo(g, a, s)
	if p != nil {
		if slices.Contains(apartables, p.motivo) {
			destino, candidatas, seguir := destinoDeApartar(g, a, s, desde)
			// Antes del sí, contra cada rama a la que puede ir `apartar`, con lo que guardaría (Q180).
			_, guardados := sinGuardar(g, "")
			if p := noSoportada(g, finales(g, nil, destino, candidatas, desde, s.principal, seguir), s.principal,
				guardados); p != nil {
				return decision{}, p
			}
			if _, amplio := sinGuardar(g, refFinal(g, nil, destino, desde, s.principal, seguir)); len(amplio) > 0 {
				p.salida.poner("archivos", amplio)
			}
		}
		return decision{}, p
	}
	ref := ""
	if destino := llegada(&d, "", s.principal); destino != "" {
		ref = "refs/remotes/origin/" + destino
	}
	estrecho, amplio := sinGuardar(g, ref)
	// `ofrecer` cambia de rama con lo que haya: cuenta cualquier cambio de un archivo con seguimiento.
	aparta := len(estrecho) > 0 || (d.accion == "ofrecer" && len(amplio) > 0)
	var commits []string
	if llegaALaPrincipal(d) {
		commits = adelantada(g, s.principal)
	}
	// Sin nada que apartar, la skill guarda sin `apartar`, y lo que hay sin guardar no está en el camino (Q180).
	var guardados []string
	if aparta || len(commits) > 0 {
		guardados = amplio
	}
	if p := noSoportada(g, finales(g, &d, desde, nil, desde, s.principal, false), s.principal, guardados); p != nil {
		return decision{}, p
	}
	if aparta {
		return decision{}, nuevaParada("cambios-sin-guardar", fmt.Sprintf("La copia tiene trabajo sin guardar en la rama "+
			"%s que entraría en el commit de la skill o que el cambio de rama pisaría.", d.rama), d.rama,
			par{"principal", s.principal}, par{"archivos", amplio})
	}
	if len(commits) > 0 {
		// `apartar` iguala la principal al servidor, que trae sus archivos aunque la copia no cambie de rama (Q170).
		_, amplio := sinGuardar(g, "refs/remotes/origin/"+s.principal)
		return decision{}, nuevaParada("principal-adelantada", fmt.Sprintf("La rama principal %s de esta copia "+
			"tiene commits que el servidor no tiene, y el push los subiría.", s.principal), d.rama,
			par{"principal", s.principal}, par{"archivos", amplio}, par{"commits", commits})
	}
	return d, nil
}

// sinGuardar es el trabajo sin guardar, en líneas de `git status --porcelain`: lo que entraría en el commit de la skill
// o el cambio a `destino` pisaría, y lo que se aparta. Lo primero son las rutas de la skill, con sus archivos nuevos,
// lo preparado en el índice, en cualquier ruta, y los archivos sin seguimiento que `destino` tiene, en `choques`; lo
// segundo suma los cambios de cualquier archivo con seguimiento. Un submódulo con cambios adentro no cuenta: `apartar`
// no los guarda. Uno en el camino no llega acá: `revisar` y `apartar` paran antes con `copia-no-soportada` (Q180).
func sinGuardar(g Git, destino string) (estrecho, amplio []string) {
	enRutas := estado(g, append([]string{"--untracked-files=all", "--"}, rutasDeLaSkill...)...)
	seguidos := estado(g, "--untracked-files=no")
	var preparados []string
	for _, l := range seguidos {
		if l[0] != ' ' && l[0] != '?' {
			preparados = append(preparados, l)
		}
	}
	var chocan []string
	if destino != "" {
		chocan = choques(g, destino)
	}
	return unicas(enRutas, preparados, chocan), unicas(enRutas, seguidos, chocan)
}

// estado son las líneas de `git status --porcelain`, `XY <ruta>` o `XY <antes> -> <después>`, con las rutas tal cual,
// sin comillas ni escapes aunque lleven espacios o tildes (N9).
func estado(g Git, args ...string) []string {
	return lineasDeEstado(g.rutas(append([]string{"status", "--porcelain", "-z", "--ignore-submodules=dirty"}, args...)...))
}

// lineasDeEstado arma las líneas de `git status --porcelain -z`: un renombrado o una copia, con `R` o `C` en cualquiera
// de las dos columnas (B3), trae después la ruta de antes.
func lineasDeEstado(partes []string) []string {
	var lineas []string
	for i := 0; i < len(partes); i++ {
		linea := partes[i]
		if len(linea) >= 3 && strings.ContainsAny(linea[:2], "RC") && i+1 < len(partes) {
			i++
			linea = linea[:3] + partes[i] + " -> " + linea[3:]
		}
		lineas = append(lineas, linea)
	}
	return lineas
}

// choques son las líneas de los archivos sin seguimiento de `camino`.
func choques(g Git, destino string) []string {
	lineas, _ := camino(g, destino)
	return lineas
}

// camino es lo que hay sin seguimiento en el camino de `git switch` a `destino`, lo que el `switch` reemplaza o borra:
// lo que `destino` tiene en la misma ruta, lo que no es una carpeta donde `destino` tiene una carpeta, y lo que hay
// dentro de una carpeta donde `destino` tiene un archivo (H1 de la revisión 4). Devuelve las líneas de los archivos y
// los enlaces simbólicos. Un archivo va como `?? <ruta>` si no está ignorado y `!! <ruta>` si lo está, aunque el
// contenido sea el mismo: git se niega igual ante uno sin seguimiento (Q168), y ante un ignorado con
// `--no-overwrite-ignore` (Q175). Un enlace va aparte, apunte adonde apunte, porque hace parar con
// `copia-no-soportada` (Q177).
func camino(g Git, destino string) (lineas, enlaces []string) {
	raiz, ok := g.salida("rev-parse", "--show-toplevel")
	if !ok || raiz == "" || !g.existe(destino) {
		return nil, nil
	}
	enRaiz := Git{repo: raiz}
	seguidos := map[string]bool{}
	for _, r := range g.rutas("ls-files", "-z") {
		seguidos[r] = true
	}
	enDestino, perdidos, deEnlaces, vistas := map[string]bool{}, map[string]bool{}, map[string]bool{}, map[string]bool{}
	var carpetas []string
	for _, entrada := range g.rutas("ls-tree", "-r", "-z", "--full-tree", destino) {
		datos, ruta, _ := strings.Cut(entrada, "\t")
		campos := strings.Split(datos, " ")
		if len(campos) != 3 || campos[1] != "blob" {
			continue
		}
		// Una carpeta de `destino` que en la copia es un archivo o un enlace sin seguimiento: el `switch` lo reemplaza.
		partes := strings.Split(ruta, "/")
		for i := 1; i < len(partes); i++ {
			carpeta := strings.Join(partes[:i], "/")
			if vistas[carpeta] {
				continue
			}
			vistas[carpeta] = true
			if seguidos[carpeta] {
				continue
			}
			info, err := os.Lstat(enRaiz.enLaCopia(carpeta))
			switch {
			case err != nil:
			case info.Mode()&os.ModeSymlink != 0:
				deEnlaces[carpeta] = true
			case !info.IsDir():
				perdidos[carpeta] = true
			}
		}
		if seguidos[ruta] {
			continue
		}
		info, err := os.Lstat(enRaiz.enLaCopia(ruta))
		switch {
		case err != nil:
		case info.Mode()&os.ModeSymlink != 0:
			deEnlaces[ruta] = true
		case info.IsDir():
			carpetas = append(carpetas, ruta)
		case info.Mode().IsRegular():
			enDestino[ruta] = true
		}
	}
	// Un archivo de `destino` que en la copia es una carpeta: el `switch` borra lo que tiene sin seguimiento.
	if len(carpetas) > 0 {
		for _, r := range g.rutas(append([]string{"-C", raiz, "ls-files", "-z", "--others", "--"}, carpetas...)...) {
			if info, err := os.Lstat(enRaiz.enLaCopia(r)); err == nil && info.Mode()&os.ModeSymlink != 0 {
				deEnlaces[r] = true
			} else {
				perdidos[r] = true
			}
		}
	}
	enlaces = ordenadas(deEnlaces)
	for r := range perdidos {
		enDestino[r] = true
	}
	rutas := ordenadas(enDestino)
	if len(rutas) == 0 {
		return nil, enlaces
	}
	ignorados := map[string]bool{}
	for _, r := range g.rutas(append([]string{"-C", raiz, "ls-files", "-z", "--others", "--ignored",
		"--exclude-standard", "--"}, rutas...)...) {
		ignorados[r] = true
	}
	for _, r := range rutas {
		if ignorados[r] {
			lineas = append(lineas, "!! "+r)
		} else {
			lineas = append(lineas, "?? "+r)
		}
	}
	return lineas, enlaces
}

// ordenadas son las claves de `conjunto`, ordenadas.
func ordenadas(conjunto map[string]bool) []string {
	var claves []string
	for clave := range conjunto {
		claves = append(claves, clave)
	}
	slices.Sort(claves)
	return claves
}

// forma es lo que `apartar` no sabe guardar sin riesgo de perder trabajo y está en el camino del cambio a alguna de las
// refs de `finales` (Q177, Q180), como ruta y qué es. El camino son las rutas que cambian entre la copia, HEAD y el
// índice, y cada ref; las de `guardados`, líneas de `git status --porcelain` de lo que `apartar` guardaría; y lo que
// `camino` encuentra sin seguimiento. Un submódulo de la copia o de una ref, o un repositorio git anidado, ignorado o
// no, está en el camino si una de esas rutas es la suya, está dentro de él o lo contiene; un enlace simbólico sin
// seguimiento, si `camino` lo encuentra (H5 de la revisión 5). Sin cambio de rama ni nada que guardar no hay camino.
func forma(g Git, finales, guardados []string) map[string]string {
	raiz, ok := g.salida("rev-parse", "--show-toplevel")
	if !ok || raiz == "" {
		return nil
	}
	rutas, enlaces := rutasDeEstado(guardados), map[string]bool{}
	conHead := g.existe("HEAD")
	submodulos := submodulosDe(g, raiz, "")
	if conHead {
		for r := range submodulosDe(g, raiz, "HEAD") {
			submodulos[r] = true
		}
	}
	for _, final := range finales {
		lineas, deEnlaces := camino(g, final)
		for _, l := range lineas {
			rutas[strings.TrimSuffix(l[3:], "/")] = true
		}
		for _, r := range deEnlaces {
			enlaces[r] = true
		}
		for _, r := range g.rutas("diff-index", "--cached", "-z", "--name-only", "--no-renames",
			"--ignore-submodules=none", final) {
			rutas[r] = true
		}
		if conHead {
			for _, r := range g.rutas("diff-tree", "-r", "-z", "--name-only", "--no-renames", "--ignore-submodules=none",
				"HEAD", final) {
				rutas[r] = true
			}
		}
		for r := range submodulosDe(g, raiz, final) {
			submodulos[r] = true
		}
	}
	// Las rutas del camino y las carpetas que las contienen.
	cerca := map[string]bool{}
	for r := range rutas {
		partes := strings.Split(r, "/")
		for i := 1; i <= len(partes); i++ {
			cerca[strings.Join(partes[:i], "/")] = true
		}
	}
	enElCamino := func(ruta string) bool {
		if cerca[ruta] {
			return true
		}
		partes := strings.Split(ruta, "/")
		for i := 1; i < len(partes); i++ {
			if rutas[strings.Join(partes[:i], "/")] {
				return true
			}
		}
		return false
	}
	encontradas := map[string]string{}
	poner := func(ruta, que string) {
		if _, esta := encontradas[ruta]; !esta {
			encontradas[ruta] = que
		}
	}
	for _, r := range ordenadas(submodulos) {
		if enElCamino(r) {
			poner(r, "submódulo")
		}
	}
	vinculadas := copiasVinculadas(g, raiz)
	for _, r := range ordenadas(anidados(raiz, cerca, rutas)) {
		if vinculadas[r] {
			poner(r, "copia de `git worktree` de este repositorio")
		} else {
			poner(r, "repositorio git anidado")
		}
	}
	for _, r := range ordenadas(enlaces) {
		poner(r, "enlace simbólico en el camino del cambio de rama")
	}
	return encontradas
}

// rutasDeEstado son las rutas de líneas de `git status --porcelain`, las dos de un renombrado, sin la `/` de una
// carpeta.
func rutasDeEstado(lineas []string) map[string]bool {
	rutas := map[string]bool{}
	for _, l := range lineas {
		cuerpo := l[3:]
		partes := []string{cuerpo}
		if strings.ContainsAny(l[:2], "RC") {
			partes = strings.SplitN(cuerpo, " -> ", 2)
		}
		for _, r := range partes {
			rutas[strings.TrimSuffix(r, "/")] = true
		}
	}
	return rutas
}

// submodulosDe son las rutas de los submódulos de `ref`, o del índice con "".
func submodulosDe(g Git, raiz, ref string) map[string]bool {
	var entradas []string
	if ref != "" {
		entradas = g.rutas("ls-tree", "-r", "-z", "--full-tree", ref)
	} else {
		entradas = g.rutas("-C", raiz, "ls-files", "-z", "--stage")
	}
	submodulos := map[string]bool{}
	for _, entrada := range entradas {
		if datos, ruta, _ := strings.Cut(entrada, "\t"); strings.HasPrefix(datos, "160000 ") {
			submodulos[ruta] = true
		}
	}
	return submodulos
}

// anidados son los repositorios git anidados en el camino, con `.git` como archivo o como carpeta: una carpeta de
// `cerca`, o una carpeta dentro de una ruta del camino que en la copia es una carpeta. Así se ven también los que git
// no lista como `<ruta>/` porque su carpeta tiene archivos con seguimiento (H1 de la revisión 6).
func anidados(raiz string, cerca, rutas map[string]bool) map[string]bool {
	enRaiz := Git{repo: raiz}
	encontrados := map[string]bool{}
	for c := range cerca {
		if _, err := os.Lstat(filepath.Join(enRaiz.enLaCopia(c), ".git")); err == nil {
			encontrados[c] = true
		}
	}
	for r := range rutas {
		lugar := enRaiz.enLaCopia(r)
		if info, err := os.Lstat(lugar); err != nil || !info.IsDir() {
			continue
		}
		filepath.WalkDir(lugar, func(ruta string, entrada fs.DirEntry, err error) error {
			if err != nil || !entrada.IsDir() {
				return nil
			}
			if _, err := os.Lstat(filepath.Join(ruta, ".git")); err == nil {
				if relativa, err := filepath.Rel(raiz, ruta); err == nil {
					encontrados[filepath.ToSlash(relativa)] = true
				}
				return filepath.SkipDir
			}
			return nil
		})
	}
	return encontrados
}

// copiasVinculadas son las rutas, dentro de la carpeta, de las copias de `git worktree` de este repositorio (Q182).
func copiasVinculadas(g Git, raiz string) map[string]bool {
	base, err := filepath.EvalSymlinks(raiz)
	if err != nil {
		base = raiz
	}
	rutas := map[string]bool{}
	for _, l := range g.lineas("worktree", "list", "--porcelain") {
		ruta, ok := strings.CutPrefix(l, "worktree ")
		if !ok {
			continue
		}
		if real, err := filepath.EvalSymlinks(ruta); err == nil {
			ruta = real
		}
		relativa, err := filepath.Rel(base, ruta)
		if err != nil {
			continue
		}
		relativa = filepath.ToSlash(relativa)
		if relativa != "." && relativa != ".." && !strings.HasPrefix(relativa, "../") {
			rutas[relativa] = true
		}
	}
	return rutas
}

// finales son las refs a las que puede llevar la carpeta `apartar`, o la skill sin él: la de `refFinal` o, si hay que
// elegir, la de cada candidata, como si viniera con --rama, y la de la principal si la iguala sin cambiar de rama
// (Q180).
func finales(g Git, d *decision, destino string, candidatas []string, desde, principal string, seguir bool) []string {
	if d != nil || destino != "" {
		if final := refFinal(g, d, destino, desde, principal, seguir); final != "" {
			return []string{final}
		}
		return nil
	}
	var refs []string
	for _, c := range candidatas {
		if r := refFinal(g, nil, c, desde, principal, c == desde); r != "" {
			refs = append(refs, r)
		}
	}
	if r := refFinal(g, nil, "", desde, principal, false); r != "" {
		refs = append(refs, r)
	}
	return unicas(refs)
}

// noSoportada para con `copia-no-soportada` si en el camino hay algo que `apartar` no sabe guardar (Q177, Q180).
func noSoportada(g Git, finales []string, principal string, guardados []string) *parada {
	encontradas := forma(g, finales, guardados)
	if len(encontradas) == 0 {
		return nil
	}
	rutas := make([]string, 0, len(encontradas))
	for ruta := range encontradas {
		rutas = append(rutas, ruta)
	}
	slices.Sort(rutas)
	partes := make([]string, len(rutas))
	for i, ruta := range rutas {
		partes[i] = ruta + " (" + encontradas[ruta] + ")"
	}
	return nuevaParada("copia-no-soportada", "La copia tiene en el camino del cambio de rama algo que `apartar` no "+
		"sabe guardar sin riesgo de perder trabajo, y se resuelve a mano (Q177, Q180): "+strings.Join(partes, ", ")+".",
		g.rama(), par{"principal", principal}, par{"rutas", rutas})
}

// unicas junta las listas sin repetir líneas, en el orden en que aparecen.
func unicas(listas ...[]string) []string {
	vistas := map[string]bool{}
	var juntas []string
	for _, lista := range listas {
		for _, l := range lista {
			if !vistas[l] {
				vistas[l] = true
				juntas = append(juntas, l)
			}
		}
	}
	return juntas
}

// adelantada son los commits de la principal local que no están en la del servidor, como `<hash> <asunto>`.
func adelantada(g Git, principal string) []string {
	if !g.existe("refs/heads/" + principal) {
		return nil
	}
	return g.lineas("log", "--format=%h %s", "refs/remotes/origin/"+principal+"..refs/heads/"+principal)
}

// trabajoEnLaPrincipal dice si lo que `rama` tiene y no está en ninguna rama del servidor ya entró a la
// principal: no hay commits así, o los archivos que tocan desde la base común con la principal están iguales en ella
// (un squash merge).
func trabajoEnLaPrincipal(g Git, principal, rama string) bool {
	local := "refs/heads/" + rama
	pendientes, ok := g.salida("rev-list", "--count", local, "--not", "--remotes=origin")
	if ok && pendientes == "0" {
		return true
	}
	remota := "refs/remotes/origin/" + principal
	base, okBase := g.salida("merge-base", local, remota)
	if !ok || pendientes == "" || !okBase || base == "" {
		return false
	}
	tocados, okTocados := archivos(g, base, local)
	distintos, okDistintos := archivos(g, local, remota)
	if !okTocados || len(tocados) == 0 || !okDistintos {
		return false
	}
	for ruta := range tocados {
		if distintos[ruta] {
			return false
		}
	}
	return true
}

// archivos son las rutas que cambian entre dos commits, y false si git falla.
func archivos(g Git, desde, hasta string) (map[string]bool, bool) {
	r := g.correr("diff", "--name-only", "--no-renames", "-z", desde, hasta)
	if r.codigo != 0 {
		return nil, false
	}
	rutas := map[string]bool{}
	for _, ruta := range noVacias(strings.Split(r.stdout, "\x00")) {
		rutas[ruta] = true
	}
	return rutas, true
}

// primeraLibre es `base`, o `base-2`, `base-3`... la primera que no existe en local ni en el servidor.
func primeraLibre(g Git, ramasDelServidor map[string]bool, base string) string {
	locales, _ := g.salida("for-each-ref", "--format=%(refname:short)", "refs/heads")
	ocupada := func(rama string) bool {
		return ramasDelServidor[rama] || slices.Contains(strings.Split(sinRetornos(locales), "\n"), rama)
	}
	if !ocupada(base) {
		return base
	}
	n := 2
	for ocupada(fmt.Sprintf("%s-%d", base, n)) {
		n++
	}
	return fmt.Sprintf("%s-%d", base, n)
}

func apartar(g Git, a argumentos) *objeto {
	s, p := servidor(g)
	if p != nil {
		return p.salida
	}
	desde := g.rama()
	creadas := []string{}
	salida, p := apartarYVolver(g, a, s, desde, &creadas)
	if p == nil {
		return salida
	}
	if p.motivo == "error-de-git" {
		p.salida.poner("apartado", creadas)
		p.salida.poner("desde", nulable(desde))
		p.salida.poner("rama", nulable(g.rama()))
	}
	return p.salida
}

func rutaDelIndice(g Git) string {
	ruta, _ := g.salida("rev-parse", "--git-path", "index")
	if ruta == "" {
		return ""
	}
	absoluta, err := filepath.Abs(g.enLaCopia(ruta))
	if err != nil {
		return g.enLaCopia(ruta)
	}
	return absoluta
}

// guardarAparte arma el apartado de lo que hay en la copia sin tocar la carpeta, el índice ni HEAD y sin los hooks de
// commit ni de checkout (Q171, Q174): un índice temporal, copia del de la copia con sus marcas, `write-tree` y
// `commit-tree`. Primero lo preparado, tal cual, porque `git add -u` pisaría lo que está solo en el índice (H3);
// después los cambios de los archivos con seguimiento, los archivos nuevos de las rutas que no están ignorados (N1) y
// los sin seguimiento que el cambio de rama pisaría o no dejaría pasar (N2, N3). El último commit lleva `Destino:
// <destino>`, si lo hay (Q173). Crea `apartado/<rama>`, o reusa uno que ya tiene esos mismos commits, y devuelve la
// rama y la ruta del índice temporal, que queda con el árbol del apartado; quien la recibe la borra.
func guardarAparte(g Git, s delServidor, donde string, chocan []string, destino string) (string, string, *parada) {
	inicio, _ := g.salida("rev-parse", "HEAD")
	real := rutaDelIndice(g)
	archivo, err := os.CreateTemp(filepath.Dir(real), "index.apartar-")
	if err != nil {
		return "", "", nuevaParada("error-de-git", "no se pudo crear el índice temporal: "+err.Error(), g.rama())
	}
	ruta := archivo.Name()
	archivo.Close()
	listo := false
	defer func() {
		if !listo {
			os.Remove(ruta)
		}
	}()
	if contenido, err := os.ReadFile(real); err == nil {
		if err := os.WriteFile(ruta, contenido, 0o644); err != nil {
			return "", "", nuevaParada("error-de-git", "no se pudo copiar el índice: "+err.Error(), g.rama())
		}
	} else if errors.Is(err, fs.ErrNotExist) {
		os.Remove(ruta)
	} else {
		return "", "", nuevaParada("error-de-git", "no se pudo copiar el índice: "+err.Error(), g.rama())
	}
	temporal := Git{repo: g.repo, indice: ruta}
	preparado, p := escribirArbol(temporal)
	if p != nil {
		return "", "", p
	}
	if p := agregar(temporal, chocan); p != nil {
		return "", "", p
	}
	todo, p := escribirArbol(temporal)
	if p != nil {
		return "", "", p
	}
	var arboles, mensajes []string
	if arbolDeHEAD, _ := g.salida("rev-parse", "HEAD^{tree}"); preparado != arbolDeHEAD {
		arboles, mensajes = append(arboles, preparado), append(mensajes, "Apartado: lo que estaba preparado en "+donde)
	}
	if todo != preparado {
		arboles, mensajes = append(arboles, todo), append(mensajes, "Apartado: lo que había en "+donde+" antes de guardar")
	}
	padre := inicio
	for i, arbol := range arboles {
		parrafos := []string{mensajes[i]}
		// El último commit lleva el destino, que lee el reintento desde el apartado (Q173).
		if destino != "" && i == len(arboles)-1 {
			parrafos = append(parrafos, "Destino: "+destino)
		}
		if padre, p = commitTree(g, arbol, padre, parrafos...); p != nil {
			return "", "", p
		}
	}
	base := "apartado/" + strings.ReplaceAll(donde, "/", "-")
	apartado := reusable(g, base, inicio, arboles, destino)
	if apartado == "" {
		apartado = primeraLibre(g, s.ramas, base)
		// Con el valor anterior vacío, update-ref falla si la rama ya existe.
		if p := g.hacer("update-ref", "refs/heads/"+apartado, padre, ""); p != nil {
			return "", "", p
		}
	}
	listo = true
	return apartado, ruta, nil
}

func escribirArbol(temporal Git) (string, *parada) {
	r := temporal.correr("write-tree")
	if r.codigo != 0 {
		return "", nuevaParada("error-de-git", "`git write-tree` falló: "+strings.TrimSpace(r.stderr), temporal.rama())
	}
	return strings.TrimSpace(r.stdout), nil
}

func agregar(temporal Git, chocan []string) *parada {
	if p := temporal.hacer("add", "-u"); p != nil {
		return p
	}
	if nuevos := temporal.rutas(append([]string{"ls-files", "-z", "--others", "--exclude-standard", "--"},
		rutasDeLaSkill...)...); len(nuevos) > 0 {
		if p := temporal.hacer(append([]string{"add", "--"}, nuevos...)...); p != nil {
			return p
		}
	}
	if len(chocan) > 0 {
		raiz, _ := temporal.salida("rev-parse", "--show-toplevel")
		return temporal.hacer(append([]string{"-C", raiz, "add", "-f", "--"}, chocan...)...)
	}
	return nil
}

func commitTree(g Git, arbol, padre string, parrafos ...string) (string, *parada) {
	args := []string{"commit-tree", arbol, "-p", padre}
	for _, parrafo := range parrafos {
		args = append(args, "-m", parrafo)
	}
	r := g.correr(args...)
	if r.codigo != 0 {
		return "", nuevaParada("error-de-git", "`git "+strings.Join(args, " ")+"` falló: "+strings.TrimSpace(r.stderr),
			g.rama())
	}
	return strings.TrimSpace(r.stdout), nil
}

// destinoDe es el `Destino: <rama>` del último commit de `ref`, que escribió `apartar` al guardar (Q173), o "".
func destinoDe(g Git, ref string) string {
	lineas := g.lineas("log", "-1", "--format=%B", ref)
	for i := len(lineas) - 1; i >= 0; i-- {
		if destino, ok := strings.CutPrefix(lineas[i], "Destino: "); ok {
			return strings.TrimSpace(destino)
		}
	}
	return ""
}

// reusable es un `apartado/<base>` o `apartado/<base>-<n>` que ya tiene, sobre `inicio`, commits con estos mismos
// árboles y el mismo destino: lo dejó otra corrida que guardó y no alcanzó a pasar la copia al apartado (Q171). No uno
// que tiene en uso alguna copia de `git worktree` (H7 de la revisión 4).
func reusable(g Git, base, inicio string, arboles []string, destino string) string {
	enUso := map[string]bool{}
	for _, l := range g.lineas("worktree", "list", "--porcelain") {
		if rama, ok := strings.CutPrefix(l, "branch refs/heads/"); ok {
			enUso[rama] = true
		}
	}
	for _, rama := range apartados(g, base) {
		if !enUso[rama] && g.correr("merge-base", "--is-ancestor", inicio, rama).codigo == 0 &&
			slices.Equal(g.lineas("log", "--reverse", "--format=%T", inicio+".."+rama), arboles) &&
			(len(arboles) == 0 || destinoDe(g, rama) == destino) {
			return rama
		}
	}
	return ""
}

// apartados son las ramas locales `apartado/<base>` y `apartado/<base>-<n>`.
func apartados(g Git, base string) []string {
	patron := regexp.MustCompile("^" + regexp.QuoteMeta(base) + "(-[0-9]+)?$")
	var ramas []string
	for _, r := range g.lineas("for-each-ref", "--format=%(refname:short)", "refs/heads/apartado/") {
		if patron.MatchString(r) {
			ramas = append(ramas, r)
		}
	}
	return ramas
}

// pasarAlApartado pone HEAD en `apartado/<rama>` y el árbol del apartado en el índice, sin tocar la carpeta (Q172):
// la copia queda como si hubiera hecho los commits ahí, y el `git switch` que sigue es el mismo de siempre. El índice
// se escribe con `index.lock`, como lo escribe git, así que otro git que lo esté usando lo frena. Si no se puede
// reemplazar el índice, HEAD vuelve adonde estaba y el candado se borra: la copia queda como estaba (H4 de la revisión
// 4).
func pasarAlApartado(g Git, apartado, indice string) *parada {
	origen := g.rama()
	inicio, _ := g.salida("rev-parse", "HEAD")
	real := rutaDelIndice(g)
	candado := real + ".lock"
	contenido, err := os.ReadFile(indice)
	if err != nil {
		return nuevaParada("error-de-git", "no se pudo leer el índice temporal: "+err.Error(), g.rama())
	}
	archivo, err := os.OpenFile(candado, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o644)
	if errors.Is(err, fs.ErrExist) {
		return nuevaParada("error-de-git", "`"+candado+"` existe: otro proceso de git está usando el índice.", g.rama())
	}
	if err != nil {
		return nuevaParada("error-de-git", "no se pudo escribir `"+candado+"`: "+err.Error(), g.rama())
	}
	_, err = archivo.Write(contenido)
	if errCierre := archivo.Close(); err == nil {
		err = errCierre
	}
	if err != nil {
		os.Remove(candado)
		return nuevaParada("error-de-git", "no se pudo escribir `"+candado+"`: "+err.Error(), g.rama())
	}
	if r := g.correr("symbolic-ref", "HEAD", "refs/heads/"+apartado); r.codigo != 0 {
		os.Remove(candado)
		return nuevaParada("error-de-git", fmt.Sprintf("`git symbolic-ref HEAD refs/heads/%s` falló: %s", apartado,
			strings.TrimSpace(r.stderr)), g.rama())
	}
	if err := os.Rename(candado, real); err != nil {
		if origen != "" {
			g.correr("symbolic-ref", "HEAD", "refs/heads/"+origen)
		} else {
			g.correr("update-ref", "--no-deref", "HEAD", inicio)
		}
		os.Remove(candado)
		return nuevaParada("error-de-git", "no se pudo escribir `"+real+"`: "+err.Error(), g.rama())
	}
	return nil
}

// apartarCommits deja en `apartado/<rama>` los commits de `rama` que el servidor no tiene: en el apartado recién
// creado si ya los tiene, en uno de otra corrida que los tiene (Q171), o en uno nuevo.
func apartarCommits(g Git, s delServidor, rama string, creadas *[]string) *parada {
	local := "refs/heads/" + rama
	if yaApartada(g, local, *creadas) {
		return nil
	}
	base := "apartado/" + strings.ReplaceAll(rama, "/", "-")
	apartado := ""
	for _, r := range apartados(g, base) {
		if g.correr("merge-base", "--is-ancestor", local, r).codigo == 0 {
			apartado = r
			break
		}
	}
	if apartado == "" {
		apartado = primeraLibre(g, s.ramas, base)
		if p := g.hacer("branch", apartado, local); p != nil {
			return p
		}
	}
	*creadas = append(*creadas, apartado)
	return nil
}

// refFinal es la ref cuyo árbol trae `apartar` a la carpeta, o "" si la carpeta no cambia: la rama a la que cambia
// (con N4, `seguir`, se iguala al servidor; las demás van a la local si tiene commits propios, M1), o la principal del
// servidor si la copia se queda en la principal y la iguala a él (Q170).
func refFinal(g Git, d *decision, destino, desde, principal string, seguir bool) string {
	if vaA := llegada(d, destino, principal); vaA != "" {
		return refDeLlegada(g, vaA, principal, seguir)
	}
	if desde == principal && len(adelantada(g, principal)) > 0 {
		return "refs/remotes/origin/" + principal
	}
	return ""
}

// formaDelApartado es el mensaje del último commit de un apartado, como lo escribe `guardarAparte`: el asunto de uno
// de sus dos commits, con la rama de la que salió, y el destino.
var formaDelApartado = regexp.MustCompile(`^Apartado: lo que (?:estaba preparado en (?P<preparado>.+)|había en ` +
	`(?P<habia>.+) antes de guardar)\n\nDestino: (?P<destino>.+)$`)

// destinoGuardado es, en el reintento desde un `apartado/<rama>` sin nada nuevo que guardar, la rama del `Destino:`
// de su último commit, adonde iba la corrida que lo armó (Q173). Solo si ese commit tiene la forma de los de `apartar`,
// con la rama del nombre del apartado en el asunto (Q178), y si `revisar` podría mandar esta corrida a ese destino
// (Q179): es una rama donde `ramaDelFlujo` da `guardar`, `ofrecer` o `volver`, como la principal, o una de las que
// daría `destinoDelFlujo`; si no, "".
func destinoGuardado(g Git, a argumentos, desde string, s delServidor) string {
	if !strings.HasPrefix(desde, "apartado/") {
		return ""
	}
	if _, amplio := sinGuardar(g, ""); len(amplio) > 0 {
		return ""
	}
	mensaje, _ := g.salida("log", "-1", "--format=%B", "HEAD")
	forma := formaDelApartado.FindStringSubmatch(mensaje)
	if forma == nil {
		return ""
	}
	donde := forma[formaDelApartado.SubexpIndex("preparado")] + forma[formaDelApartado.SubexpIndex("habia")]
	if !regexp.MustCompile("^apartado/" + regexp.QuoteMeta(strings.ReplaceAll(donde, "/", "-")) + "(-[0-9]+)?$").
		MatchString(desde) {
		return ""
	}
	destino := forma[formaDelApartado.SubexpIndex("destino")]
	if _, candidatas := destinoDelFlujo(a, s, a.rama); slices.Contains(candidatas, destino) {
		return destino
	}
	if destino == s.principal || g.existe("refs/heads/"+destino) {
		if _, p := ramaDelFlujoDe(g, a, s, destino); p == nil {
			return destino
		}
	}
	return ""
}

// destinoDeApartar es adónde va `apartar` desde una rama que no es de este trabajo: la rama, o "" si hay que elegir; las
// candidatas; y si la iguala al servidor y le pone el upstream (N4). En el reintento desde un apartado, la de su
// `Destino:` (Q173, Q178); si no, la rama viva del servidor para este trabajo, o la principal.
func destinoDeApartar(g Git, a argumentos, s delServidor, desde string) (string, []string, bool) {
	destino := destinoGuardado(g, a, desde, s)
	if destino == "" {
		destino, candidatas := destinoDelFlujo(a, s, a.rama)
		// N4: la rama de este trabajo de la que salió `apartar` está en el servidor pero no lo sigue.
		return destino, candidatas, destino != "" && destino == desde
	}
	// En el reintento desde `apartado/<rama>`, la rama de la que salió es la del nombre del apartado.
	sigue, _ := upstream(g, destino)
	nombre := regexp.MustCompile("^apartado/" + regexp.QuoteMeta(strings.ReplaceAll(destino, "/", "-")) + "(-[0-9]+)?$")
	return destino, nil, destino != s.principal && s.ramas[destino] && sigue != destino && nombre.MatchString(desde)
}

func apartarYVolver(g Git, a argumentos, s delServidor, desde string, creadas *[]string) (*objeto, *parada) {
	var d *decision
	var destino string
	var candidatas []string
	seguir := false
	encontrada, p := ramaDelFlujo(g, a, s)
	switch {
	case p == nil:
		d, destino = &encontrada, desde
	case !slices.Contains(apartables, p.motivo):
		return nil, p
	default:
		destino, candidatas, seguir = destinoDeApartar(g, a, s, desde)
	}
	var chocan []string
	final := refFinal(g, d, destino, desde, s.principal, seguir)
	// Antes de escribir nada: con un submódulo, un repositorio anidado o un enlace en el camino, no hace nada (Q177,
	// Q180).
	_, guardados := sinGuardar(g, "")
	if p := noSoportada(g, finales(g, d, destino, candidatas, desde, s.principal, seguir), s.principal,
		guardados); p != nil {
		return nil, p
	}
	if final != "" {
		for _, l := range choques(g, final) {
			chocan = append(chocan, l[3:])
		}
	}
	sueltos := false
	if desde == "" {
		n, ok := g.salida("rev-list", "--count", "HEAD", "--not", "--branches", "--remotes")
		sueltos = !ok || n != "0"
	}
	if _, amplio := sinGuardar(g, ""); len(amplio) > 0 || len(chocan) > 0 || sueltos {
		donde := desde
		if donde == "" {
			donde = "sin-rama"
		}
		apartado, indice, p := guardarAparte(g, s, donde, chocan, destino)
		if p != nil {
			return nil, p
		}
		*creadas = append(*creadas, apartado)
		p = pasarAlApartado(g, apartado, indice)
		os.Remove(indice)
		if p != nil {
			return nil, p
		}
	}

	if (destino == s.principal || (d != nil && llegaALaPrincipal(*d))) && len(adelantada(g, s.principal)) > 0 {
		if p := apartarCommits(g, s, s.principal, creadas); p != nil {
			return nil, p
		}
		if p := igualar(g, s.principal); p != nil {
			return nil, p
		}
	}

	if destino == "" {
		return nuevoObjeto(par{"accion", "elegir"}, par{"ramas", candidatas}, par{"principal", s.principal},
			par{"apartado", *creadas}, par{"desde", nulable(desde)}), nil
	}
	if seguir {
		if p := seguirAlServidor(g, s, destino, creadas); p != nil {
			return nil, p
		}
	}
	if g.rama() != destino {
		if destino != desde {
			if p := alDia(g, destino); p != nil {
				return nil, p
			}
		}
		// Con `--no-overwrite-ignore`, git se niega ante un ignorado que la predicción de choques no vio (Q175).
		if p := g.hacer("switch", "--quiet", "--no-overwrite-ignore", destino); p != nil {
			return nil, p
		}
	}
	var salida *objeto
	if dd, p := revisar(g, a, &s); p != nil {
		salida = p.salida
	} else {
		salida = dd.objeto()
	}
	salida.poner("apartado", *creadas)
	salida.poner("desde", nulable(desde))
	return salida, nil
}

// yaApartada dice si el último apartado ya contiene a `ref`, para no crear otro con los mismos commits.
func yaApartada(g Git, ref string, creadas []string) bool {
	return len(creadas) > 0 && g.correr("merge-base", "--is-ancestor", ref, creadas[len(creadas)-1]).codigo == 0
}

// igualar deja la rama local igual a la del servidor, esté o no la copia en ella.
func igualar(g Git, rama string) *parada {
	remota := "refs/remotes/origin/" + rama
	if g.rama() == rama {
		return g.hacer("reset", "--quiet", "--keep", remota)
	}
	return g.hacer("branch", "--quiet", "-f", rama, remota)
}

// seguirAlServidor hace que una rama de este trabajo que está en el servidor pero no lo sigue pase a seguirlo (N4). Si
// tiene commits que el servidor no tiene, quedan antes en `apartado/<rama>`, y la rama se iguala al servidor.
func seguirAlServidor(g Git, s delServidor, rama string, creadas *[]string) *parada {
	local, remota := "refs/heads/"+rama, "refs/remotes/origin/"+rama
	if g.correr("merge-base", "--is-ancestor", local, remota).codigo != 0 {
		if p := apartarCommits(g, s, rama, creadas); p != nil {
			return p
		}
	}
	// El upstream después de igualar: con upstream vivo, otra corrida tomaría esos commits como del flujo y los subiría.
	if p := igualar(g, rama); p != nil {
		return p
	}
	return g.hacer("branch", "--quiet", "--set-upstream-to=origin/"+rama, rama)
}

// alDia deja la rama local `rama` igual a la del servidor, sin cambiar de rama: se crea siguiéndola, o avanza si está
// atrás. Una que tiene commits propios queda como está, y `revisar` dice qué pasa con ella.
func alDia(g Git, rama string) *parada {
	remota := "refs/remotes/origin/" + rama
	if !g.existe("refs/heads/" + rama) {
		return g.hacer("branch", "--quiet", "--track", rama, remota)
	}
	if g.correr("merge-base", "--is-ancestor", "refs/heads/"+rama, remota).codigo == 0 {
		return g.hacer("branch", "--quiet", "-f", rama, remota)
	}
	return nil
}

func volver(g Git, a argumentos) *objeto {
	s, p := servidor(g)
	if p != nil {
		return p.salida
	}
	d, p := revisar(g, a, &s)
	if p != nil {
		return p.salida
	}
	if !(d.accion == "volver" || (d.accion == "ofrecer" && a.ramaNueva == d.ramaNueva)) {
		return d.objeto()
	}
	if p := alDia(g, s.principal); p != nil {
		return p.salida
	}
	// Un solo `git switch`: si pisaría un cambio sin guardar, git no cambia nada.
	if r := g.correr("switch", "--quiet", s.principal); r.codigo != 0 {
		_, amplio := sinGuardar(g, "refs/remotes/origin/"+s.principal)
		return nuevaParada("cambios-sin-guardar", "Volver a la principal pisaría trabajo sin guardar: "+
			strings.TrimSpace(r.stderr), d.rama, par{"principal", s.principal}, par{"archivos", amplio}).salida
	}
	if d.accion == "ofrecer" {
		if p := g.hacer("switch", "--quiet", "-c", d.ramaNueva); p != nil {
			return p.salida
		}
		return decision{"guardar", d.ramaNueva, s.principal, ""}.objeto()
	}
	return decision{"guardar", s.principal, s.principal, ""}.objeto()
}

func commit(g Git, a argumentos) *objeto {
	actual := g.rama()
	// Una ruta que no está y no cambió: la escribió la skill y otra sesión la apartó o la guardó (N5, Q160).
	var faltan []string
	for _, r := range a.rutas {
		if _, err := os.Lstat(g.enLaCopia(r)); err != nil && g.correr("diff", "--quiet", "HEAD", "--", r).codigo == 0 {
			faltan = append(faltan, r)
		}
	}
	if len(faltan) > 0 {
		return nuevaParada("ruta-que-falta", "Estos archivos de la skill no están en la copia ni cambiaron: "+
			strings.Join(faltan, ", "), actual, par{"rutas", faltan}).salida
	}
	if g.correr(append([]string{"diff", "--quiet", "HEAD", "--"}, a.rutas...)...).codigo == 0 {
		return nuevoObjeto(par{"accion", "sin-cambios"}, par{"rama", nulable(actual)})
	}
	orden := []string{"commit", "--quiet"}
	for _, m := range a.mensajes {
		orden = append(orden, "-m", m)
	}
	if p := g.hacer(append(append(orden, "--"), a.rutas...)...); p != nil {
		return p.salida
	}
	return nuevoObjeto(par{"accion", "empujar"}, par{"rama", nulable(actual)},
		par{"archivos", g.lineas("show", "--name-status", "--format=", "--no-renames", "HEAD")})
}

func rechazo(g Git, a argumentos) *objeto {
	s, p := servidor(g)
	if p != nil {
		return p.salida
	}
	actual := g.rama()
	if actual == "" {
		return nuevaParada("sin-rama", "La copia no está en ninguna rama.", "").salida
	}
	if !s.ramas[actual] {
		// Las ramas a las que se guarda ya están en el servidor; la que no está es la rama nueva, aunque siga a otra.
		return nuevaParada("rama-nueva-rechazada", fmt.Sprintf("El servidor rechazó también la rama nueva %s.", actual),
			actual).salida
	}
	return nuevoObjeto(par{"accion", "rama-nueva"}, par{"rama", actual},
		par{"rama_nueva", primeraLibre(g, s.ramas, a.tipo+"/"+a.nombre())})
}
