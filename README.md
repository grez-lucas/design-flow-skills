# design-flow-skills

Skills en español para pasar de una idea de producto a un diseño listo para construir: grilling del requerimiento, spec con historias de usuario, tickets y HTML de cada vista sobre un design system liviano. Funcionan con Claude Code y con cualquier agente compatible con `npx skills`.

---

## Flujo

1. `grilling-es`: entrevista al requerimiento antes de dibujar. Usa Lavish cuando la sesión tiene terminal y el chat cuando no. Cierra con el spec sobre una plantilla fija.
2. `spec-a-tickets`: escribe los tickets desde el spec, antes del HTML, con historia, criterios de aceptación "Dado, cuando, entonces", pruebas, casos borde y preguntas abiertas. Los publica en el tracker del proyecto o, si no hay, como un archivo markdown por ticket.
3. `spec-a-html`: en una sesión nueva, toma el spec y genera el HTML de la vista o del flujo. Busca un design system existente y, si no hay, lo crea, siempre preguntando antes.
4. `checklist-diseno`: revisa el HTML contra la definición de listo antes de la planificación del sprint.

---

## Artefactos

Todo vive en un repositorio de diseño por producto, separado del repositorio de código:

```
design/
  tokens.css        design system: variables CSS (color, tipografía, espaciado, radios, sombras, temas)
  components.css    componentes compartidos, construidos sobre tokens.css
  vistas/           un HTML semántico por vista o flujo
specs/
  <épica>/
    spec.md
    tickets/NN-titulo.md   solo si el proyecto no tiene tracker
```

El formato es liviano a propósito: los agentes leen estos archivos en cada tarea. Un HTML enlaza `tokens.css` y `components.css`, no usa frameworks por CDN, y muestra sus estados con `?escenario=` o un panel `data-proto`, nunca con controles dentro de la pantalla.

---

## Instalación

Con `npx skills` (Node.js 22.20 o superior):

```
npx skills add grez-lucas/design-flow-skills
```

Como plugin de Claude Code, desde una sesión:

```
/plugin marketplace add grez-lucas/design-flow-skills
/plugin install flujo-diseno@design-flow-skills
```

---

## Estado

| Skill | Estado |
| :--- | :--- |
| `spec-a-html` | borrador, probado con specs ficticios |
| `grilling-es` | pendiente |
| `spec-a-tickets` | pendiente |
| `checklist-diseno` | pendiente |

---

## Licencia

MIT. Ver `LICENSE`.
