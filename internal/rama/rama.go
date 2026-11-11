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
	actual := g.rama()
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
		if trabajoEnLaPrincipal(g, s.principal) {
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
	d, p := ramaDelFlujo(g, a, s)
	if p != nil {
		if slices.Contains(apartables, p.motivo) {
			destino, _ := destinoDelFlujo(a, s, "")
			ref := ""
			if destino != "" {
				ref = refDeLlegada(g, destino, s.principal, destino == g.rama())
			}
			if _, amplio := sinGuardar(g, ref); len(amplio) > 0 {
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
	if len(estrecho) > 0 || (d.accion == "ofrecer" && len(amplio) > 0) {
		return decision{}, nuevaParada("cambios-sin-guardar", fmt.Sprintf("La copia tiene trabajo sin guardar en la rama "+
			"%s que entraría en el commit de la skill o que el cambio de rama pisaría.", d.rama), d.rama,
			par{"principal", s.principal}, par{"archivos", amplio})
	}
	if llegaALaPrincipal(d) {
		if commits := adelantada(g, s.principal); len(commits) > 0 {
			// `apartar` iguala la principal al servidor, que trae sus archivos aunque la copia no cambie de rama (Q170).
			_, amplio := sinGuardar(g, "refs/remotes/origin/"+s.principal)
			return decision{}, nuevaParada("principal-adelantada", fmt.Sprintf("La rama principal %s de esta copia "+
				"tiene commits que el servidor no tiene, y el push los subiría.", s.principal), d.rama,
				par{"principal", s.principal}, par{"archivos", amplio}, par{"commits", commits})
		}
	}
	return d, nil
}

// sinGuardar es el trabajo sin guardar, en líneas de `git status --porcelain`: lo que entraría en el commit de la skill
// o el cambio a `destino` pisaría, y lo que se aparta. Lo primero son las rutas de la skill, con sus archivos nuevos,
// lo preparado en el índice, en cualquier ruta, y los archivos sin seguimiento que `destino` tiene, en `choques`; lo
// segundo suma los cambios de cualquier archivo con seguimiento. Un submódulo con cambios
// adentro no cuenta, porque la skill no lo agrega; uno que apunta a otro commit, sí.
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

// choques son los archivos sin seguimiento que `git switch` a `destino` no dejaría pasar o pisaría: `?? <ruta>` si no
// está ignorado, aunque el contenido sea el mismo, porque git se niega igual (Q168), y `!! <ruta>` si está ignorado y
// se perdería, porque git reemplaza un ignorado sin avisar. Uno ignorado se pierde si `destino` lo tiene con otro
// contenido, si es un archivo donde `destino` tiene una carpeta, o si está dentro de una carpeta donde `destino` tiene
// un archivo (H1 de la revisión 4).
func choques(g Git, destino string) []string {
	raiz, ok := g.salida("rev-parse", "--show-toplevel")
	if !ok || raiz == "" || !g.existe(destino) {
		return nil
	}
	enRaiz := Git{repo: raiz}
	seguidos := map[string]bool{}
	for _, r := range g.rutas("ls-files", "-z") {
		seguidos[r] = true
	}
	enDestino := map[string]string{}
	perdidos := map[string]bool{}
	vistas := map[string]bool{}
	var carpetas []string
	for _, entrada := range g.rutas("ls-tree", "-r", "-z", "--full-tree", destino) {
		datos, ruta, _ := strings.Cut(entrada, "\t")
		campos := strings.Split(datos, " ")
		if len(campos) != 3 || campos[1] != "blob" {
			continue
		}
		// Una carpeta de `destino` que en la copia es un archivo sin seguimiento: el `switch` lo reemplaza.
		partes := strings.Split(ruta, "/")
		for i := 1; i < len(partes); i++ {
			carpeta := strings.Join(partes[:i], "/")
			if vistas[carpeta] {
				continue
			}
			vistas[carpeta] = true
			if info, err := os.Lstat(enRaiz.enLaCopia(carpeta)); err == nil && !seguidos[carpeta] && !info.IsDir() {
				perdidos[carpeta] = true
			}
		}
		if seguidos[ruta] {
			continue
		}
		info, err := os.Lstat(enRaiz.enLaCopia(ruta))
		switch {
		case err != nil:
		case info.IsDir():
			carpetas = append(carpetas, ruta)
		case info.Mode().IsRegular():
			enDestino[ruta] = campos[2]
		case info.Mode()&os.ModeSymlink != 0:
			// Como `os.path.isfile` de rama.py: un enlace a un archivo cuenta como archivo.
			if destinoDelEnlace, err := os.Stat(enRaiz.enLaCopia(ruta)); err == nil && destinoDelEnlace.Mode().IsRegular() {
				enDestino[ruta] = campos[2]
			}
		}
	}
	// Un archivo de `destino` que en la copia es una carpeta: el `switch` borra lo que tiene sin seguimiento.
	if len(carpetas) > 0 {
		for _, r := range g.rutas(append([]string{"-C", raiz, "ls-files", "-z", "--others", "--"}, carpetas...)...) {
			perdidos[r] = true
		}
	}
	var rutas []string
	for r := range enDestino {
		rutas = append(rutas, r)
	}
	for r := range perdidos {
		if _, esta := enDestino[r]; !esta {
			rutas = append(rutas, r)
		}
	}
	if len(rutas) == 0 {
		return nil
	}
	slices.Sort(rutas)
	ignorados := map[string]bool{}
	for _, r := range g.rutas(append([]string{"-C", raiz, "ls-files", "-z", "--others", "--ignored",
		"--exclude-standard", "--"}, rutas...)...) {
		ignorados[r] = true
	}
	var ignoradas []string
	for _, r := range rutas {
		if _, esta := enDestino[r]; esta && ignorados[r] {
			ignoradas = append(ignoradas, r)
		}
	}
	pisadas := map[string]bool{}
	for r := range perdidos {
		pisadas[r] = true
	}
	if len(ignoradas) > 0 {
		locales := g.lineas(append([]string{"-C", raiz, "hash-object", "--"}, ignoradas...)...)
		for i := 0; i < min(len(ignoradas), len(locales)); i++ {
			if locales[i] != enDestino[ignoradas[i]] {
				pisadas[ignoradas[i]] = true
			}
		}
	}
	var lineas []string
	for _, r := range rutas {
		switch {
		case ignorados[r] && pisadas[r]:
			lineas = append(lineas, "!! "+r)
		case !ignorados[r]:
			lineas = append(lineas, "?? "+r)
		}
	}
	return lineas
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

// trabajoEnLaPrincipal dice si lo que la rama actual tiene y no está en ninguna rama del servidor ya entró a la
// principal: no hay commits así, o los archivos que tocan desde la base común con la principal están iguales en ella
// (un squash merge).
func trabajoEnLaPrincipal(g Git, principal string) bool {
	pendientes, ok := g.salida("rev-list", "--count", "HEAD", "--not", "--remotes=origin")
	if ok && pendientes == "0" {
		return true
	}
	remota := "refs/remotes/origin/" + principal
	base, okBase := g.salida("merge-base", "HEAD", remota)
	if !ok || pendientes == "" || !okBase || base == "" {
		return false
	}
	tocados, okTocados := archivos(g, base, "HEAD")
	distintos, okDistintos := archivos(g, "HEAD", remota)
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

// guardarAparte arma el apartado de lo que hay en la copia sin tocar la carpeta, el índice ni HEAD y sin correr hooks
// (Q171): un índice temporal, copia del de la copia con sus marcas, `write-tree` y `commit-tree`. Primero lo
// preparado, tal cual, porque `git add -u` pisaría lo que está solo en el índice (H3); después los cambios de los
// archivos con seguimiento, los archivos nuevos de las rutas que no están ignorados (N1) y los sin seguimiento que el
// cambio de rama pisaría o no dejaría pasar (N2, N3). Crea `apartado/<rama>`, o reusa uno que ya tiene esos mismos
// commits, y devuelve la rama y la ruta del índice temporal, que queda con el árbol del apartado; quien la recibe la
// borra.
func guardarAparte(g Git, s delServidor, donde string, chocan []string) (string, string, *parada) {
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
	var arboles []string
	padre := inicio
	preparado, p := escribirArbol(temporal)
	if p != nil {
		return "", "", p
	}
	if arbolDeHEAD, _ := g.salida("rev-parse", "HEAD^{tree}"); preparado != arbolDeHEAD {
		if padre, p = commitTree(g, preparado, padre, "Apartado: lo que estaba preparado en "+donde); p != nil {
			return "", "", p
		}
		arboles = append(arboles, preparado)
	}
	if p := agregar(temporal, chocan); p != nil {
		return "", "", p
	}
	todo, p := escribirArbol(temporal)
	if p != nil {
		return "", "", p
	}
	if todo != preparado {
		if padre, p = commitTree(g, todo, padre, "Apartado: lo que había en "+donde+" antes de guardar"); p != nil {
			return "", "", p
		}
		arboles = append(arboles, todo)
	}
	base := "apartado/" + strings.ReplaceAll(donde, "/", "-")
	apartado := reusable(g, base, inicio, arboles)
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

func commitTree(g Git, arbol, padre, mensaje string) (string, *parada) {
	r := g.correr("commit-tree", arbol, "-p", padre, "-m", mensaje)
	if r.codigo != 0 {
		return "", nuevaParada("error-de-git", fmt.Sprintf("`git commit-tree %s -p %s -m %s` falló: %s", arbol, padre,
			mensaje, strings.TrimSpace(r.stderr)), g.rama())
	}
	return strings.TrimSpace(r.stdout), nil
}

// reusable es un `apartado/<base>` o `apartado/<base>-<n>` que ya tiene, sobre `inicio`, commits con estos mismos
// árboles: lo dejó otra corrida que guardó y no alcanzó a pasar la copia al apartado (Q171).
func reusable(g Git, base, inicio string, arboles []string) string {
	for _, rama := range apartados(g, base) {
		if g.correr("merge-base", "--is-ancestor", inicio, rama).codigo == 0 &&
			slices.Equal(g.lineas("log", "--reverse", "--format=%T", inicio+".."+rama), arboles) {
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
// (con N4 la actual se iguala al servidor; las demás van a la local si tiene commits propios, M1), o la principal del
// servidor si la copia se queda en la principal y la iguala a él (Q170).
func refFinal(g Git, d *decision, destino, desde, principal string) string {
	if vaA := llegada(d, destino, principal); vaA != "" {
		return refDeLlegada(g, vaA, principal, vaA == desde)
	}
	if desde == principal && len(adelantada(g, principal)) > 0 {
		return "refs/remotes/origin/" + principal
	}
	return ""
}

func apartarYVolver(g Git, a argumentos, s delServidor, desde string, creadas *[]string) (*objeto, *parada) {
	var d *decision
	var destino string
	var candidatas []string
	encontrada, p := ramaDelFlujo(g, a, s)
	switch {
	case p == nil:
		d, destino = &encontrada, desde
	case !slices.Contains(apartables, p.motivo):
		return nil, p
	default:
		destino, candidatas = destinoDelFlujo(a, s, a.rama)
	}
	var chocan []string
	final := refFinal(g, d, destino, desde, s.principal)
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
		if destino != "" {
			llega := final
			if llega == "" {
				llega = "HEAD"
			}
			if sucios := submodulosSucios(g, llega); len(sucios) > 0 {
				return nil, nuevaParada("error-de-git", "Estos submódulos tienen cambios sin guardar adentro, que "+
					"`apartar` no guarda, y el cambio de rama los lleva a otro commit, donde git los pisaría o no "+
					"dejaría pasar: "+strings.Join(sucios, ", ")+". Hay que guardarlos dentro del submódulo antes de "+
					"apartar.", desde)
			}
		}
		donde := desde
		if donde == "" {
			donde = "sin-rama"
		}
		apartado, indice, p := guardarAparte(g, s, donde, chocan)
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
	if d == nil && destino == desde {
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
		cambio := []string{"switch", "--quiet"}
		// Con un submódulo apartado, la copia vuelve también al commit del submódulo que tiene la rama del flujo.
		if len(*creadas) > 0 {
			cambio = append(cambio, "--recurse-submodules")
		}
		if p := g.hacer(append(cambio, destino)...); p != nil {
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

// submodulosSucios son los submódulos con cambios en sus archivos con seguimiento que `git switch
// --recurse-submodules` a `destino` llevaría a otro commit. git 2.43 se niega si el archivo cambia entre los dos
// commits, y si no cambia, descarta el cambio sin avisar (H3 de la revisión 4); los archivos sin seguimiento de adentro
// quedan.
func submodulosSucios(g Git, destino string) []string {
	raiz, _ := g.salida("rev-parse", "--show-toplevel")
	partes := g.rutas("status", "--porcelain=v2", "-z", "--untracked-files=no", "--ignore-submodules=none")
	var sucios []string
	for i := 0; i < len(partes); i++ {
		campos := strings.Split(partes[i], " ")
		desde := 8
		if campos[0] == "2" {
			desde = 9
			i++
		}
		if (campos[0] != "1" && campos[0] != "2") || len(campos) <= desde || !strings.HasPrefix(campos[2], "S") ||
			campos[2][2] != 'M' {
			continue
		}
		ruta := strings.Join(campos[desde:], " ")
		adentro, _ := g.salida("-C", Git{repo: raiz}.enLaCopia(ruta), "rev-parse", "HEAD")
		if enDestino, _ := g.salida("rev-parse", destino+":"+ruta); adentro != enDestino {
			sucios = append(sucios, ruta)
		}
	}
	return sucios
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
