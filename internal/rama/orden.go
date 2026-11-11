// Package rama es `flujo rama`: decide en qué rama guarda una skill del flujo y protege el trabajo que la persona tenía
// en la copia. Es el port a Go de `scripts/rama.py` (issue 45, Q151, Q152, Q163): la misma interfaz, las mismas
// salidas y las mismas pruebas de CLI de `tests/rama/`. El contrato está en `uso`, que imprime `flujo rama -h`.
package rama

import (
	"fmt"
	"io"
	"os"
	"os/exec"
	"regexp"
	"slices"
	"strings"
	"unicode/utf8"
)

const uso = `Decide en qué rama guarda una skill del flujo y protege el trabajo que la persona tenía en la copia.

Uso, desde el repositorio de diseño o con --repo:
  flujo rama revisar --tipo <spec|tickets|diseno> --epica <épica>
  flujo rama revisar --tipo diseno --mockup <mockup> --epicas <épica>,<épica>[,...]
  flujo rama apartar <los mismos --tipo y --epica, o --mockup y --epicas> [--rama <rama>]
  flujo rama volver <los mismos --tipo y --epica, o --mockup y --epicas> [--rama-nueva <rama>]
  flujo rama commit (-F <archivo> | -m <mensaje> [-m <párrafo>...]) -- <ruta>...
  flujo rama rechazo --tipo <spec|tickets|diseno> --epica <épica>
  flujo rama rechazo --tipo diseno --mockup <mockup>

--mockup es de html-a-vista cuando las vistas quedan en más de una épica: el nombre del archivo del mockup sin
extensión, en minúsculas y con guiones, reemplaza a la épica en la rama.

Las rutas de la skill son ` + "`design/`, `specs/`, `.gitignore` y `.claude/pm-conventions.md`" + `: lo único que una skill
agrega a su commit. La principal es la que dice el servidor (` + "`git ls-remote --symref`), no `origin/HEAD`" + `.

revisar  antes de la primera escritura. Corre ` + "`git fetch`" + `, no cambia nada más y devuelve:
         guardar  la rama actual es la principal del servidor, o una rama del flujo de la épica con upstream vivo,
                  la rama del mismo nombre en origin: ` + "`spec/`, `tickets/` o `diseno/<épica>`" + `, con o sin sufijo
                  (` + "`-2`, `-3`" + `). Con --mockup, la rama del flujo es ` + "`diseno/<mockup>`" + `, con o sin sufijo.
         ofrecer  solo con --mockup: la rama actual es una rama del flujo viva de una sola de las épicas, aunque el
                  mockup se llame como ella. Lleva ` + "`rama_nueva`, `diseno/<mockup>`" + ` o su primer sufijo libre.
         volver   el upstream de la rama actual ya no está en el servidor y lo suyo entró a la principal: todos sus
                  commits están en alguna rama del servidor, o los archivos que tocan los que no están, desde la
                  base común con la principal, están iguales en ella (squash merge).
         parar    cualquier otro caso, con ` + "`motivo` y `detalle`" + `. Antes que nada, para con ` + "`copia-no-soportada`" + ` y
                  ` + "`rutas`" + ` si la copia tiene un submódulo, un repositorio git anidado en la carpeta, ignorado o no, o
                  un enlace simbólico sin seguimiento en el camino del cambio de rama, apunte adonde apunte: donde la
                  rama a la que va tiene un archivo o una carpeta de sus archivos, o dentro de una carpeta donde tiene
                  un archivo. ` + "`apartar`" + ` no hace nada en esa copia, y se resuelve a mano (Q177).
                  En lugar de ` + "`guardar`, `ofrecer` o `volver`" + `, para con ` + "`cambios-sin-guardar`" + ` si hay trabajo sin
                  guardar que entraría en el commit de la skill: en sus rutas, con los archivos nuevos, o preparado
                  en el índice, en cualquier ruta; con ` + "`ofrecer`" + `, también cualquier cambio de un archivo con
                  seguimiento; con ` + "`volver` y `ofrecer`" + `, también un archivo sin seguimiento en el camino del cambio
                  de rama, ignorado o no y aunque sea igual al de la principal, porque el cambio de rama no pasaría
                  (Q169, Q175).
                  Y para con ` + "`principal-adelantada`" + ` si se va a guardar desde la principal y la de esta copia tiene
                  commits que el servidor no tiene; ahí cuenta también lo que traería igualarla al servidor (Q170).
         Todas llevan ` + "`principal`" + ` cuando el servidor respondió y ` + "`rama`" + ` cuando la copia está en una. Con trabajo
         sin guardar, ` + "`archivos`" + ` trae sus líneas de ` + "`git status --porcelain`" + `, con las rutas sin escapar: lo que
         ` + "`apartar`" + ` guardaría, y ` + "`!! <ruta>`" + ` para un ignorado en el camino del cambio de rama. Con la principal
         adelantada, ` + "`commits`" + ` trae esos commits.

apartar  con el sí de la persona, ante ` + "`otra-rama`, `sin-rama`, `commits-sin-empujar`, `cambios-sin-guardar`" + ` o
         ` + "`principal-adelantada`" + `. Guarda en ` + "`apartado/<rama>`" + ` (cada ` + "`/`" + ` cambiada por ` + "`-`, `sin-rama`" + ` con HEAD separado,
         con el primer sufijo libre, o el de otra corrida que ya tiene lo mismo y que ninguna copia de ` + "`git worktree`" + `
         tiene en uso) lo que había, con un índice temporal, antes de tocar la carpeta (Q171) y sin los hooks de commit
         ni de checkout (` + "`reference-transaction`" + ` y ` + "`post-index-change`" + ` sí pueden correr, y si uno rechaza, para antes de
         tocar HEAD, el índice o la carpeta; Q174): primero lo que estaba preparado, tal cual, después los cambios de
         los archivos con seguimiento, los archivos nuevos de las rutas que no están ignorados y los archivos sin
         seguimiento que el cambio de rama pisaría o no dejaría pasar; los demás archivos sin seguimiento no se tocan.
         Con HEAD separado guarda también los commits que no están en ninguna rama. Si se va a guardar desde la
         principal y tiene commits que el servidor no tiene, los guarda en ` + "`apartado/<principal>`" + ` y la iguala al
         servidor. Vuelve después a la rama del flujo: la actual, si ` + "`revisar`" + ` daba ` + "`guardar`" + `, ` + "`ofrecer`" + ` o ` + "`volver`" + `; si
         no, la rama viva del servidor para este trabajo, ` + "`<tipo>/<nombre>`" + ` con sufijos exactos, o la principal. Si esa
         es la rama actual y no sigue a la del servidor, la iguala al servidor, con sus commits propios antes en
         ` + "`apartado/<rama>`" + `, y la deja siguiéndola. Devuelve lo que devuelve ` + "`revisar`" + ` desde ahí, con ` + "`apartado`" + ` (las
         ramas donde quedó lo apartado) y ` + "`desde`" + ` (la rama donde estaba, o null). Con lo apartado, la copia pasa a
         ` + "`apartado/<rama>`" + ` sin tocar la carpeta y de ahí cambia a la rama del flujo con
         ` + "`git switch --no-overwrite-ignore`" + `, que se niega ante un ignorado que la predicción no vio en lugar de borrarlo
         (Q172, Q175); igualar la principal sin cambiar de rama (` + "`reset --keep`" + `) no tiene esa opción y depende de la
         predicción. El último commit del apartado lleva ` + "`Destino: <rama>`" + `, la rama del flujo a la que va (Q173). Con
         más de una rama viva para este trabajo devuelve ` + "`elegir`" + `, con ` + "`ramas`" + `, y --rama <una de ellas> vuelve a esa.

volver   con ` + "`volver`" + `, o con ` + "`ofrecer`" + ` y el sí de la persona a ` + "`rama_nueva`" + `, que va en --rama-nueva. Corre ` + "`revisar`" + `
         otra vez: si devuelve eso, iguala la principal local al servidor, cambia a ella y, con ` + "`ofrecer`" + `, crea
         ` + "`rama_nueva`" + `. Devuelve ` + "`guardar`" + ` con la rama donde quedó. Con cualquier otra ` + "`accion`" + `, o con ` + "`ofrecer`" + ` y
         otra ` + "`rama_nueva`" + `, no cambia nada y la devuelve. Si el cambio de rama pisaría un cambio sin guardar, no
         cambia nada y para con ` + "`cambios-sin-guardar`" + `.

commit   después de ` + "`git add`" + ` de lo que escribió la skill. Hace el commit solo con las rutas dadas, que tienen que
         estar dentro de las de la skill, con un -m por párrafo o con -F y el mensaje en un archivo UTF-8, con o sin
         BOM, relativo a donde corre la orden: así el mensaje no pasa por la línea de órdenes (Q162). Devuelve
         ` + "`empujar` con `rama` y `archivos`" + ` (estado y ruta de cada uno, separados por un tab), o ` + "`sin-cambios`" + ` si esas
         rutas no cambiaron. Si una ruta no está en la copia y no cambió, no hace el commit y para con
         ` + "`ruta-que-falta` y `rutas`" + `.

rechazo  después de que el servidor rechazó el push a la rama actual por algo que no son credenciales. Devuelve
         ` + "`rama-nueva` con `rama`" + `, la actual, y ` + "`rama_nueva`: `<tipo>/<épica>`" + ` o, si ya existe en local o en el
         servidor, el primer sufijo libre (` + "`-2`, `-3`" + `). Si la rama actual no está en el servidor, es la rama nueva,
         la de ` + "`rama-nueva` o la `rama_nueva` de `ofrecer`" + `, aunque siga a otra rama, y para con
         ` + "`rama-nueva-rechazada`" + `, sin otro sufijo.

Si git falla en ` + "`apartar`" + `, ` + "`volver`" + ` o ` + "`commit`" + `, para con ` + "`error-de-git`" + ` y el mensaje de git en ` + "`detalle`" + `. ` + "`apartar`" + ` no
deshace nada: ` + "`apartado`" + ` lista las ramas donde ya quedó lo apartado y ` + "`rama`" + ` dice dónde quedó la copia. Si falla antes
del ` + "`git switch`" + `, la carpeta está como estaba. Si falla el ` + "`git switch`" + `, la copia queda en ` + "`apartado/<rama>`" + ` sin cambios
sin guardar, y otra corrida de ` + "`apartar`" + `, sin nada nuevo que guardar, va a la rama de su ` + "`Destino:`" + ` sin volver a
calcularla y hace lo que faltaba para llegar, como igualarla al servidor (Q173). Lo hace solo si el último commit es uno
de los dos que escribe ` + "`apartar`" + ` y su ` + "`Destino:`" + ` es una rama a la que ` + "`revisar`" + ` podría mandar esta corrida: la
principal, una rama donde daría ` + "`guardar`" + `, ` + "`ofrecer`" + ` o ` + "`volver`" + `, también una local cuya copia en el servidor ya no está,
o una rama viva del servidor para este trabajo; si no, la calcula otra vez, y ` + "`revisar`" + ` arma ` + "`archivos`" + ` contra esa misma
rama (Q178, Q179). El reintento sabe que la rama del ` + "`Destino:`" + ` es la de la que salió el apartado solo por el nombre del
apartado; un apartado sin commits propios, de HEAD separado solo con commits sueltos, no lleva ` + "`Destino:`" + ` y el reintento
calcula la rama otra vez; y si en una corrida que venía de ` + "`ofrecer`" + ` o ` + "`volver`" + ` falla igualar la principal adelantada,
el reintento no lo rehace y ` + "`revisar`" + ` vuelve a dar ` + "`principal-adelantada`" + `, con otro sí (Q176). Si el índice está en uso
(` + "`index.lock`" + `), para antes de tocarlo, y otra corrida reusa el apartado; si no lo puede escribir, deja HEAD en la rama
de origen y no deja su ` + "`index.lock`" + `.

` + "`fetch` y `ls-remote`" + ` esperan al servidor ` + "`RAMA_TOPE`" + ` segundos (60 si no está); pasado eso, matan a git y a sus
hijos (` + "`taskkill /T`" + ` en Windows) y paran con ` + "`sin-servidor`" + `. git nunca pide credenciales por la terminal.

Escribe en stdout un objeto JSON con ` + "`accion`" + ` y sale con 0. Con uso incorrecto, una épica o un mockup que no sirve
como nombre de rama (con mayúsculas, o que termina en guion y número, como ` + "`fase-2`" + `), o una ruta de commit que no es
de la skill, o un -F que no se puede leer, no es UTF-8 o tiene bytes nulos (Q167), sale con 2 sin escribir en
stdout y dice en stderr por qué. Si no encuentra git, sale con 1.
`

// argumentos son los de una orden de rama, ya validados.
type argumentos struct {
	orden                                   string
	tipo, epica, mockup, repo, rama         string
	ramaNueva                               string
	epicas                                  []string
	mensajes, rutas                         []string
	mensajeDeArchivo                        string
	conArchivo                              bool
	conEpica, conMockup, conEpicas, conTipo bool
}

func (a argumentos) nombre() string {
	if a.conMockup {
		return a.mockup
	}
	return a.epica
}

// errorDeUso es un uso incorrecto: rama sale con 2 y lo dice en stderr.
type errorDeUso string

func fallo(formato string, valores ...any) error {
	return errorDeUso(fmt.Sprintf(formato, valores...))
}

func (e errorDeUso) Error() string { return string(e) }

var ordenes = map[string]func(Git, argumentos) *objeto{
	"revisar": func(g Git, a argumentos) *objeto {
		d, p := revisar(g, a, nil)
		if p != nil {
			return p.salida
		}
		return d.objeto()
	},
	"apartar": apartar,
	"volver":  volver,
	"commit":  commit,
	"rechazo": rechazo,
}

// opciones son las que acepta cada orden, con su nombre sin guiones.
func opciones(orden string) []string {
	switch orden {
	case "commit":
		return []string{"m", "F", "repo"}
	case "rechazo":
		return []string{"tipo", "epica", "mockup", "repo"}
	case "apartar":
		return []string{"tipo", "epica", "mockup", "epicas", "rama", "repo"}
	case "volver":
		return []string{"tipo", "epica", "mockup", "epicas", "rama-nueva", "repo"}
	}
	return []string{"tipo", "epica", "mockup", "epicas", "repo"}
}

// leerArgumentos lee la línea de órdenes como la leía argparse en rama.py: `--opcion valor`, `--opcion=valor`, `-m
// valor` o `-mvalor`, y en `commit` las rutas después de `--`. Devuelve ayuda=true con -h o --help.
func leerArgumentos(argv []string) (a argumentos, ayuda bool, err error) {
	if len(argv) == 0 {
		return a, false, fallo("falta la orden: revisar, apartar, volver, commit o rechazo")
	}
	if argv[0] == "-h" || argv[0] == "--help" {
		return a, true, nil
	}
	a.orden, a.repo = argv[0], "."
	if _, ok := ordenes[a.orden]; !ok {
		return a, false, fallo("orden desconocida %s: van revisar, apartar, volver, commit o rechazo", citar(a.orden))
	}
	if a.orden == "commit" && !slices.Contains(argv, "--") {
		return a, false, fallo("commit lleva las rutas después de --")
	}
	validas := opciones(a.orden)
	for i := 1; i < len(argv); i++ {
		token := argv[i]
		var nombre, valor string
		conValor := false
		switch {
		case token == "-h" || token == "--help":
			return a, true, nil
		case token == "--":
			if a.orden != "commit" && i+1 < len(argv) {
				return a, false, fallo("argumentos de más: %s", strings.Join(argv[i+1:], " "))
			}
			a.rutas = argv[i+1:]
			i = len(argv)
			continue
		case strings.HasPrefix(token, "--"):
			nombre, valor, conValor = strings.Cut(token[2:], "=")
		case (strings.HasPrefix(token, "-m") || strings.HasPrefix(token, "-F")) && a.orden == "commit":
			nombre, valor, conValor = token[1:2], token[2:], len(token) > 2
		default:
			return a, false, fallo("argumento que no se esperaba: %s", citar(token))
		}
		if !slices.Contains(validas, nombre) {
			return a, false, fallo("%s no es una opción de %s", citar(token), a.orden)
		}
		guion := "--" + nombre
		if nombre == "m" || nombre == "F" {
			guion = "-" + nombre
		}
		if !conValor {
			if i+1 >= len(argv) || (strings.HasPrefix(argv[i+1], "-") && argv[i+1] != "-") {
				return a, false, fallo("%s lleva un valor", guion)
			}
			i++
			valor = argv[i]
		}
		switch nombre {
		case "m":
			a.mensajes = append(a.mensajes, valor)
		case "F":
			a.mensajeDeArchivo, a.conArchivo = valor, true
		case "repo":
			a.repo = valor
		case "tipo":
			a.tipo, a.conTipo = valor, true
		case "epica":
			a.epica, a.conEpica = valor, true
		case "mockup":
			a.mockup, a.conMockup = valor, true
		case "epicas":
			a.epicas, a.conEpicas = strings.Split(valor, ","), true
		case "rama":
			a.rama = valor
		case "rama-nueva":
			a.ramaNueva = valor
		}
	}
	return a, false, validar(a)
}

func validar(a argumentos) error {
	if a.orden == "commit" {
		if a.conArchivo == (len(a.mensajes) > 0) {
			return fallo("commit lleva -F con el archivo del mensaje o -m con el mensaje, uno de los dos")
		}
		if len(a.rutas) == 0 {
			return fallo("commit lleva al menos una ruta después de --")
		}
		for _, ruta := range a.rutas {
			if !esRutaDeLaSkill(ruta) {
				return fallo("%s no es una ruta de la skill: van %s o rutas dentro de ellas", citar(ruta),
					strings.Join(rutasDeLaSkill, ", "))
			}
		}
		return nil
	}
	if !a.conTipo {
		return fallo("%s lleva --tipo", a.orden)
	}
	if !slices.Contains(tipos, a.tipo) {
		return fallo("--tipo %s no es uno de %s", citar(a.tipo), strings.Join(tipos, ", "))
	}
	if a.conEpica == a.conMockup {
		return fallo("%s lleva --epica o --mockup, uno de los dos", a.orden)
	}
	for _, valor := range append([]string{a.nombre()}, a.epicas...) {
		if problema := problemaDelNombre(valor); problema != "" {
			return fallo("%s no sirve como nombre de rama: %s", citar(valor), problema)
		}
	}
	if a.conMockup && a.tipo != "diseno" {
		return fallo("--mockup va solo con --tipo diseno")
	}
	if a.orden != "rechazo" && a.conMockup != a.conEpicas {
		return fallo("--mockup y --epicas van juntos")
	}
	if a.conEpicas {
		distintas := slices.Clone(a.epicas)
		slices.Sort(distintas)
		if len(a.epicas) < 2 || len(slices.Compact(distintas)) != len(a.epicas) {
			return fallo("--epicas lleva dos o más épicas distintas; con una sola, usa --epica")
		}
	}
	return nil
}

var (
	nombreDeRama    = regexp.MustCompile(`^[\p{L}\p{N}]+(?:-[\p{L}\p{N}]+)*$`)
	guionYNumero    = regexp.MustCompile(`-[0-9]+$`)
	gitAceptaLaRama = func(valor string) bool {
		return exec.Command("git", "check-ref-format", "refs/heads/spec/"+valor).Run() == nil
	}
)

// problemaDelNombre dice por qué `valor` no sirve como épica o mockup, o "": letras minúsculas, con o sin tilde, y
// números, separados por guiones, sin terminar en guion y número, y que git lo acepte como rama.
func problemaDelNombre(valor string) string {
	if !nombreDeRama.MatchString(valor) || valor != strings.ToLower(valor) {
		return "minúsculas y guiones, sin espacios ni /"
	}
	if guionYNumero.MatchString(valor) {
		return "termina en guion y número, que se confunde con el sufijo de la rama; usa otro, por ejemplo fase-dos"
	}
	if !gitAceptaLaRama(valor) {
		return "git no lo acepta como nombre de rama"
	}
	return ""
}

// esRutaDeLaSkill dice si `ruta` es una de las rutas de la skill o está dentro de una, sin salir con `..` ni usar la
// magia de git.
func esRutaDeLaSkill(ruta string) bool {
	limpia := normalizar(strings.ReplaceAll(ruta, `\`, "/"))
	if strings.HasPrefix(ruta, "-") || strings.HasPrefix(ruta, "/") || strings.HasPrefix(ruta, ":") ||
		strings.HasPrefix(limpia, "..") {
		return false
	}
	for _, r := range rutasDeLaSkill {
		if limpia == strings.TrimSuffix(r, "/") || (strings.HasSuffix(r, "/") && strings.HasPrefix(limpia, r)) {
			return true
		}
	}
	return false
}

// normalizar es `posixpath.normpath`: sin `.`, sin `//` y con cada `..` resuelto contra lo anterior.
func normalizar(ruta string) string {
	var partes []string
	for _, parte := range strings.Split(ruta, "/") {
		switch {
		case parte == "" || parte == ".":
		case parte == ".." && len(partes) > 0 && partes[len(partes)-1] != "..":
			partes = partes[:len(partes)-1]
		case parte == ".." && strings.HasPrefix(ruta, "/"):
		default:
			partes = append(partes, parte)
		}
	}
	limpia := strings.Join(partes, "/")
	if strings.HasPrefix(ruta, "/") {
		limpia = "/" + limpia
	}
	if limpia == "" {
		return "."
	}
	return limpia
}

// citar escribe un valor entre comillas simples, como el repr de Python en los mensajes de rama.py.
func citar(valor string) string {
	return "'" + valor + "'"
}

// Correr corre `flujo rama` con sus argumentos y devuelve el código de salida.
func Correr(argv []string, stdout, stderr io.Writer) int {
	a, ayuda, err := leerArgumentos(argv)
	if ayuda {
		fmt.Fprint(stdout, uso)
		return 0
	}
	if _, errGit := exec.LookPath("git"); errGit != nil {
		fmt.Fprintln(stderr, "flujo rama: no encuentro git en el PATH")
		return 1
	}
	if err == nil && a.conArchivo {
		a.mensajes, err = leerMensaje(a.mensajeDeArchivo)
	}
	if err != nil {
		fmt.Fprintf(stderr, "flujo rama: %s\nUso: flujo rama -h\n", err)
		return 2
	}
	fmt.Fprintln(stdout, ordenes[a.orden](Git{repo: a.repo}, a).json())
	return 0
}

// leerMensaje lee el mensaje de commit de `ruta`, relativa a donde corre flujo: UTF-8, sin el BOM que escribe
// `Set-Content -Encoding UTF8` en PowerShell 5.1 y con los CRLF como LF. Va a git como un solo -m. Otro encoding, como
// el UTF-16 de `>` y `Out-File` o el ANSI de `Set-Content` sin `-Encoding`, es uso incorrecto (Q167).
func leerMensaje(ruta string) ([]string, error) {
	contenido, err := os.ReadFile(ruta)
	if err != nil {
		return nil, fallo("no se puede leer el mensaje de -F %s: %v", citar(ruta), err)
	}
	if !utf8.Valid(contenido) {
		return nil, fallo("el mensaje de -F %s no es UTF-8: escríbelo con la herramienta de archivos de la sesión, "+
			"no con > ni Out-File de PowerShell, que escriben UTF-16, ni con Set-Content sin -Encoding UTF8", citar(ruta))
	}
	// git no acepta un argumento con un byte nulo: UTF-16 sin BOM, o un archivo que no es texto (Q167).
	if strings.ContainsRune(string(contenido), 0) {
		return nil, fallo("el mensaje de -F %s tiene bytes nulos, que git no acepta: escríbelo con la herramienta "+
			"de archivos de la sesión, en UTF-8", citar(ruta))
	}
	texto := strings.TrimPrefix(string(contenido), "\ufeff")
	texto = strings.TrimSpace(strings.ReplaceAll(texto, "\r\n", "\n"))
	if texto == "" {
		return nil, fallo("el mensaje de -F %s está vacío", citar(ruta))
	}
	return []string{texto}, nil
}
