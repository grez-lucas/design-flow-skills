// proto.js: escenarios y anchos de las vistas de design/. Se copia sin modificar.
// Lee <body data-escenarios>, muestra los elementos [data-state] del escenario activo,
// clona filas en [data-repeat] para "muchos-datos" y arma un panel fuera del frame.
// URL: ?escenario=<nombre>  ?ancho=390|1280|1440  ?proto=0 (sin panel)
(function () {
  var params = new URLSearchParams(location.search);
  var body = document.body;
  var escenarios = (body.dataset.escenarios || "normal")
    .split(",").map(function (s) { return s.trim(); }).filter(Boolean);
  var anchos = [390, 1280, 1440];
  var frame = document.querySelector("[data-frame]") || body;
  var originales = new Map();

  function aplicarEscenario(nombre) {
    document.querySelectorAll("[data-state]").forEach(function (el) {
      var estados = el.dataset.state.split(/\s+/);
      el.hidden = estados.indexOf(nombre) === -1;
    });
    document.querySelectorAll("[data-repeat]").forEach(function (el) {
      if (!originales.has(el)) originales.set(el, Array.from(el.children));
      var base = originales.get(el);
      el.replaceChildren.apply(el, base);
      if (nombre !== "muchos-datos") return;
      var total = parseInt(el.dataset.repeat, 10) || 50;
      for (var i = base.length; i < total; i++) {
        el.appendChild(base[i % base.length].cloneNode(true));
      }
    });
    body.dataset.escenario = nombre;
  }

  function aplicarAncho(ancho) {
    frame.style.maxWidth = ancho ? ancho + "px" : "";
    frame.style.marginInline = ancho ? "auto" : "";
    body.dataset.ancho = ancho || "";
  }

  function actualizarUrl(clave, valor) {
    var p = new URLSearchParams(location.search);
    p.set(clave, valor);
    history.replaceState(null, "", "?" + p.toString());
  }

  var actual = params.get("escenario");
  if (escenarios.indexOf(actual) === -1) actual = escenarios[0];
  aplicarEscenario(actual);
  var ancho = parseInt(params.get("ancho"), 10);
  aplicarAncho(anchos.indexOf(ancho) === -1 ? null : ancho);

  if (params.get("proto") === "0") return;

  var panel = document.createElement("aside");
  panel.setAttribute("data-proto", "");
  panel.setAttribute("aria-label", "Panel de prototipo");
  panel.style.cssText = "position:fixed;right:8px;bottom:8px;z-index:2147483647;" +
    "background:#111;color:#fff;font:12px/1.4 system-ui,sans-serif;padding:8px;" +
    "border-radius:6px;max-width:240px;opacity:.92";

  function grupo(titulo, valores, activo, onClick) {
    var g = document.createElement("div");
    g.style.marginBottom = "6px";
    var t = document.createElement("div");
    t.textContent = titulo;
    t.style.opacity = ".7";
    g.appendChild(t);
    valores.forEach(function (v) {
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = v;
      b.style.cssText = "margin:2px;padding:2px 6px;border:1px solid #555;border-radius:4px;" +
        "background:" + (String(v) === String(activo) ? "#fff;color:#111" : "transparent;color:#fff") +
        ";cursor:pointer;font:inherit";
      b.addEventListener("click", function () { onClick(v); });
      g.appendChild(b);
    });
    return g;
  }

  function render() {
    panel.replaceChildren(
      grupo("Escenario", escenarios, body.dataset.escenario, function (v) {
        aplicarEscenario(v); actualizarUrl("escenario", v); render();
      }),
      grupo("Ancho", ["auto"].concat(anchos), body.dataset.ancho || "auto", function (v) {
        aplicarAncho(v === "auto" ? null : v); actualizarUrl("ancho", v); render();
      })
    );
  }

  render();
  body.appendChild(panel);
})();
