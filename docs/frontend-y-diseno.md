# Frontend y sistema de diseño

React 19 (Vite) + `react-router`, gráficas con Recharts, PDF con jsPDF.

## Rutas (`frontend/src/main.jsx`)

| Ruta | Componente | Qué es |
|---|---|---|
| `/` | `Inicio.jsx` | Landing |
| `/acerca` | `Acerca.jsx` | Página informativa |
| `/catalogo` | `Catalogo.jsx` | Catálogo público con filtros (texto, departamento, universidad), desde `GET /api/carreras` |
| `/parametros` | `Parametros.jsx` | Explica las 7 dimensiones vocacionales que explora la IA |
| `/mapa` | `Mapa.jsx` | Mapa SVG de Guatemala: elegir departamento o región antes del chat |
| `/chat` | `Chat.jsx` | El chat + el dashboard al terminar |
| `/holland` | `Holland.jsx` | Test de intereses RIASEC (O*NET) |
| `/historial` | `Historial.jsx` | Resultados guardados de la cuenta |
| `/psicometrico` | `Psicometrico.jsx` | Examen de 100 ítems. **Solo en local** |
| `/cip` | `Cip.jsx` | CIP, sin autorización de uso. **Solo en local** |
| `/personalidad` | `Personalidad.jsx` | Perfil corto de 48 ítems. **Solo en local** |

Las rutas donde el alumno **se evalúa** van envueltas en `Protegida.jsx`: sin
sesión iniciada muestran la pantalla de acceso con el botón de Google en vez del
test. El backend lo exige igual con 401 (ver [api.md](api.md)); esto solo evita
que el alumno llene un examen para descubrirlo al final.

### Producción vs. local

`modo.js` exporta `MODO_COMPLETO = import.meta.env.DEV`, y de ahí sale todo lo
que cambia entre las dos:

| | Local (`npm run dev`) | Producción (`npm run build`) |
|---|---|---|
| Instrumentos ofrecidos | los cuatro | chat y Holland |
| Formas de empezar en el inicio | 4 | 3 (el título cuenta solo las visibles) |
| Perfiles predeterminados de Holland | sí | no (`import.meta.env.DEV` en `Holland.jsx`) |

En producción quedan solo los dos instrumentos confirmados: el CIP no tiene
autorización de uso, y del psicométrico y el perfil corto todavía no está medido
si aportan al ranking. Sus rutas ni siquiera se registran, y un enlace viejo cae
en el `<Route path="*">` que manda al inicio, no a una pantalla en blanco.

El backend sirve esos endpoints en los dos casos: la separación es **qué se
ofrece**, no qué existe. Para ver el build tal como lo recibe el alumno:
`npm run preview` en `frontend/` (o la configuración `produccion` de
`.claude/launch.json`, puerto 4173).

`Nav.jsx` es la barra superior de las páginas informativas; **el chat y el
dashboard no la usan**. El mapa marca como "próximamente" todo departamento sin
catálogo (`ACTIVOS` en `Mapa.jsx`, hoy Quetzaltenango y Totonicapán): agregar uno
es editar ese set, no el SVG.

⚠️ **`App.jsx` ya no existe** — el chat es `Chat.jsx`. `App.css` sí sigue siendo
la hoja de estilos compartida.

---

## ¿Qué recibe el usuario al final?

Un **dashboard a pantalla completa** (`Dashboard.jsx`) con:
- **Gráfico de barras** de todas las carreras con afinidad > 1%.
- **Gráfico de dona** que al pasar el mouse muestra la carrera y su % en grande.
- **Lista de carreras** con color distintivo por carrera.
- Panel de detalle por carrera: **descripción general** + selector de
  **instituciones** (centro · departamento) que revela el enfoque de cada una.
- **PDF descargable** (`reporte.js`, `jsPDF`, cargado con `import()` dinámico).
- **"Un día siendo…"** (`POST /api/simular-dia`): narrativa de una jornada real
  en esa carrera, con retos incluidos. On-demand: 1 llamada a Gemini.
- **Comparador** de la carrera principal contra otra del resultado
  (`POST /api/comparar`). On-demand: 1 llamada a Gemini.
- **Feedback** 👍/👎 sobre la recomendación (`POST /api/feedback`).

Ejemplo: si sale "Derecho" con "Ambos", ve las 4 sedes juntas (CUNTOTO, URG, UMG
en Totonicapán y CUNOC en Quetzaltenango), cada una con su sello.

**Desactivado hoy:** `MOSTRAR_RADAR = false` en `Chat.jsx` — el radar de afinidad
en vivo durante el chat existe pero está apagado (marcado con `ponytail:`).

---

## Voz del guía

Los mensajes de Orienta se leen con **voz neuronal** (`POST /api/tts` →
`edge-tts`, voz `es-MX-DaliaNeural`) en vez de la voz robótica de
`speechSynthesis`. Detalles que importan:
- El audio se **cachea por texto exacto** en un `Map` del navegador: las preguntas
  fijas son siempre las mismas, así que se piden una sola vez.
- Antes de mandar el texto se limpia lo que no debe **leerse** pero sí **verse**
  en pantalla.
- Si `/api/tts` o edge-tts fallan (API no oficial), cae a `speechSynthesis`.
- Hay sonido de tecleo sintetizado con **WebAudio** (sin archivo de audio) y se
  silencia junto con la voz.

---

## Identidad visual

Paleta de marca de Orienta: **azul, azul marino, gris y negro** — sin
violetas, rosas ni verdes decorativos. Los únicos verdes/rojos/naranjas que
quedan son **semánticos**, a propósito, y no se deben "corregir" a azul:
- el badge de confianza alta/media/baja en `Dashboard.css` (código de semáforo);
- la **escala de caritas** del examen psicométrico (`CARITAS` en
  `Psicometrico.jsx`): rojo el 1, naranja el 2, amarillo el 3, lima el 4 y
  verde el 5. El color codifica el nivel de acuerdo, no decora. El color no
  rellena el botón —va en el trazo de la carita, el borde y un tinte al 12%—
  porque texto blanco sobre amarillo o lima no contrasta.

- Variables base en `frontend/src/index.css` (`--navy`, `--navy-2`,
  `--accent`, `--accent-2`, `--text`, `--muted`, `--bg`).
- `frontend/src/colors.js` (`COLORS`) es la paleta compartida para las
  gráficas del dashboard (barras, dona, colores de carrera) y para el PDF —
  12 tonos de azul/navy/gris/negro, sin repetir el mismo color en carreras
  consecutivas.
- `frontend/src/reporte.js` (generación del PDF con `jsPDF`) usa los mismos
  tonos: `ACCENT` = azul (`--accent`), `VERDE` (nombre heredado, ya no es
  verde) = azul marino para los bullets de "por qué encaja", `TEXT`/`MUTED`/
  `LIGHT` = casi negro/gris/gris muy claro. Si se agrega una gráfica o
  elemento nuevo, tomar el color de `COLORS` o de las variables CSS — nunca
  un color fuera de esta familia.

---

## Detalles de UI que NO se deben "mejorar" sin leer el motivo

Están documentados en [psicometrico.md](psicometrico.md) porque nacieron ahí, pero
aplican como criterio general del proyecto:

- La escala Likert es un **grid de `repeat(5, minmax(0, 1fr))`**, no flex: con
  `flex-wrap` se partía en 2+2+1 en móvil y la última opción quedaba del doble de
  ancho. En una escala ordinal un botón más grande sesga la elección hacia él.
- El **cronómetro arranca en el primer clic**, no al cargar la página (si no, se
  le factura a la primera sección el tiempo que la pestaña estuvo abierta).
- El **guardia del doble envío es un `useRef`**, no el estado `enviando`
  (`setEnviando(true)` no surte efecto hasta el siguiente render).
- El borrador en `localStorage` guarda también los **tiempos** y **recorta el
  índice de página** al cargar.
