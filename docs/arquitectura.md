# Arquitectura y flujo

Detalle de `CLAUDE.md`. Cubre el flujo del test, la estructura de carpetas, qué
datos se guardan y cómo levantar el proyecto.

---

## ¿Cómo funciona el flujo?

El test es **híbrido** (preguntas fijas + adaptativas) para gastar poca cuota de IA:

1. **Departamento o región** — se elige ANTES del chat, en el mapa de Guatemala
   (`/mapa`, `Mapa.jsx`): por departamento (hoy solo Quetzaltenango y Totonicapán
   están activos), por región (manda la lista de departamentos de esa región) o
   el botón "Ver todas las carreras (Ambos)". Llega al chat como query param
   `?depto=` y **filtra** el catálogo: solo esas carreras alimentan el resto.
2. **Nombre** (fijo, sin IA) — para saludar y personalizar. Pasa por un filtro de
   groserías duplicado en frontend y backend (`PALABRAS_OFENSIVAS` en `Chat.jsx`
   y `main.py`), porque el nombre se muestra en el dashboard y en el PDF.
3. **4 preguntas vocacionales fijas** (sin IA), todas de opción múltiple con
   selección múltiple: `impacto` (qué impacto quiere tener), `estilo` (cómo
   prefiere trabajar), `entorno` (dónde se imagina trabajando) y `gustos` (temas
   que le apasionan, en chips, con opción de agregar el suyo).
4. **Preguntas adaptativas** (IA, tipo "Akinator"): Gemini genera cada pregunta
   según lo respondido, para descartar unas carreras y reforzar otras. **Mínimo
   4, máximo 8** (`MIN_ADAPTATIVAS`/`MAX_ADAPTATIVAS`, definidas en los dos lados:
   `frontend/src/Chat.jsx` y `backend/app/preguntas.py`), dirigidas por el vector
   de cobertura de dimensiones (ver [motor-ia.md](motor-ia.md)); termina cuando
   cubrió las 4 dimensiones prioritarias Y el ranking es claro.
5. **Análisis final** (IA): genera la recomendación y muestra el dashboard.

Costo aprox.: **~5 llamadas a Gemini por test** (mínimo 4 adaptativas + 1 final),
más 1 por cada extra que el estudiante pida en el dashboard (simular un día,
comparar dos carreras). Las preguntas de opción múltiple permiten elegir varias,
una opción "Otro" con texto libre, y hay botón "← Regresar" para corregir
respuestas.

**Voz**: los mensajes del guía se leen con voz neuronal (`POST /api/tts` →
`edge-tts`, voz `es-MX-DaliaNeural`), cacheada por texto exacto en el navegador.
Si el backend o edge-tts fallan (es una API no oficial), cae a `speechSynthesis`.
El estudiante puede apagarla.

---

## Estructura de carpetas

```
.
├── backend/                FastAPI + motor de IA
│   ├── app/
│   │   ├── main.py         endpoints, filtro de groserias, TTS
│   │   ├── models.py       tablas (5, ver abajo)
│   │   ├── db.py           conexion SQLAlchemy
│   │   ├── recomendar.py   recomendacion con Gemini + capa comun (reintentos, cache, tokens)
│   │   ├── preguntas.py    preguntas adaptativas con Gemini
│   │   ├── extras.py       simulador "un dia siendo..." y comparador de 2 carreras
│   │   ├── filtro.py       pre-filtro heuristico del catalogo (sin IA)
│   │   └── psicometrico.py examen de 100 items: banco, clave y calificacion
│   ├── data/*.json         catalogo de carreras por centro
│   ├── data/perfiles_compartidos.json  perfiles reusados por varias sedes
│   ├── seed_carreras.py    carga data/*.json a la BD (idempotente)
│   └── .env                DATABASE_URL, GEMINI_API_KEY, GEMINI_MODEL (no en git)
├── frontend/               React 19 (Vite) + react-router
│   └── src/
│       ├── main.jsx        rutas: / /acerca /catalogo /parametros /psicometrico /mapa /chat
│       ├── Inicio.jsx      landing
│       ├── Nav.jsx         barra superior de las paginas informativas (el chat no la usa)
│       ├── Mapa.jsx        mapa: los departamentos con catálogo (Totonicapán y Quetzaltenango)
│       ├── Chat.jsx        chat (fijas + adaptativas), voz, fases chat/loading/dashboard
│       ├── Dashboard.jsx   graficas, detalle por institucion, PDF, simulador, comparador
│       ├── Catalogo.jsx    catalogo publico con filtros (GET /api/carreras)
│       ├── Parametros.jsx  explicacion de las 7 dimensiones vocacionales
│       ├── Acerca.jsx      pagina informativa
│       ├── Psicometrico.jsx examen psicometrico (pestaña aparte del chat)
│       ├── data/           SVG de los departamentos de Guatemala
│       ├── reporte.js      PDF con jsPDF
│       ├── session.js      SESSION_ID (uno por carga de pagina)
│       └── colors.js       paleta compartida
├── docs/ decisions/ experiments/   documentacion (ver indice en CLAUDE.md)
├── start.ps1 / stop.ps1    levantan / detienen todo con un comando
└── README.md
```

⚠️ **Ya no existe `App.jsx`**: el chat vive en `Chat.jsx` desde que la app pasó a
ser multipágina con `react-router`. Documentación vieja que lo mencione está
desactualizada.

---

## ¿Qué información recopila? (base de datos)

Se guarda en PostgreSQL (`backend/app/models.py`), 6 tablas:
- **`estudiantes`**: nombre (el email es opcional, hoy no se pide).
- **`respuestas_cuestionario`**: todas las respuestas del test como JSON, ligadas
  al estudiante, más la `recomendacion` que devolvió la IA y el `juicio` del
  profesional (`acerto` | `parcial` | `no_acerto`) con su `juicio_nota`. El
  alumno NO califica su propia recomendación: el 👍/👎 que había en el
  dashboard se quitó porque no puede saber si acertó hasta que la evalúe un
  profesional.
- **`carreras`**: el catálogo (nombre, departamento, centro, universidad,
  `perfil`, `perfil_grupo` y `sello`). `perfil_grupo` apunta a un perfil
  compartido (`data/perfiles_compartidos.json`): la misma carrera en varias sedes
  usa un solo banco de palabras y **viaja una sola vez** en el prompt.
  `sello` es el enfoque particular de esa sede, que Python adjunta después de la
  respuesta de la IA.
- **`uso_tokens`**: consumo de Gemini por `session_id` y endpoint (ver
  [decisions/gemini-costos-y-caching.md](../decisions/gemini-costos-y-caching.md)).
- **`resultados_psicometricos`**: respuestas crudas + puntajes + resumen del
  examen psicométrico (ver [psicometrico.md](psicometrico.md)).
- **`resultados_holland`**: hoja de 60 dígitos, código RIASEC y puntajes por área
  del test de Holland (ver [holland.md](holland.md)).

El **`session_id`** es lo que une todo: identifica un *recorrido* del alumno
(Holland + chat + dashboard), no una carga de página. Vive en `sessionStorage`
(`frontend/src/session.js`), así que sobrevive a recargar la página — antes se
generaba con `crypto.randomUUID()` en cada carga y una recarga a media prueba
partía los datos en dos sesiones que ya no se podían cruzar en la investigación.
Empezar otra prueba llama a `nuevaSesion()` explícitamente, porque "Hacer otro
test" navega sin recargar y reusaba la sesión anterior.

No se recopilan datos sensibles ni credenciales. La `GEMINI_API_KEY` vive solo en
`backend/.env` (ignorado por git, nunca se sube al repo).

---

## Cómo correrlo

**Rápido (Windows):** desde la raíz, con Docker Desktop instalado y `backend/.env`
configurado:
```powershell
.\start.ps1     # levanta BDD + backend + frontend y abre el navegador
.\stop.ps1      # detiene todo
```

**Manual:**
```bash
docker start tfg-db                                   # Postgres
cd backend && uv run python seed_carreras.py          # cargar catalogo
cd backend && uv run uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev                            # http://localhost:5173
```

Para agregar carreras: crear/editar un `backend/data/*.json` (con `departamento`,
`centro`, `universidad` y las `carreras` con su `perfil`) y correr
`seed_carreras.py`. Ver [catalogo.md](catalogo.md).

**Self-checks sin API** (no gastan cuota de Gemini):
```bash
cd backend && uv run python -m app.preguntas
cd backend && uv run python -m app.psicometrico
```
