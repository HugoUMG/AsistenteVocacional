# Orienta — Asistente Vocacional (TFG)

Chatbot de orientación vocacional para estudiantes de Guatemala. El alumno elige
en un mapa dónde quiere estudiar, conversa con un guía ("Orienta") que le hace
preguntas adaptativas, y recibe un **dashboard** con las carreras más afines de
un catálogo real de universidades. Aparte hay un **examen psicométrico** de 100
ítems, independiente de la recomendación.

**Stack:** React 19 (Vite) · FastAPI (Python 3.12, uv) · PostgreSQL · Gemini
(`google-genai`)

> La recomendación la hace un **LLM (Gemini)**, no un modelo de Machine Learning
> entrenado. Es una decisión deliberada, documentada en
> [decisions/llm-vs-red-neuronal.md](decisions/llm-vs-red-neuronal.md).

## Estructura

```
.
├── backend/      FastAPI + motor de IA (Gemini) + examen psicométrico   [Python 3.12, uv]
├── frontend/     React + Vite (react-router: inicio, mapa, chat, catálogo, psicométrico…)
├── docs/         arquitectura, API, motor de IA, psicométrico, catálogo, diseño
├── decisions/    decisiones técnicas (motivo, alternativas, consecuencias)
└── experiments/  evidencia medida de los cambios de prompt
```

Documentación completa: [CLAUDE.md](CLAUDE.md) es el índice.

## Requisitos

- Python 3.12+ y [uv](https://docs.astral.sh/uv/)
- Node.js 20+ y npm
- Docker Desktop (para Postgres)
- Una `GEMINI_API_KEY` (de aistudio.google.com) en `backend/.env`

## Inicio rápido (un comando)

Con Docker Desktop instalado y `backend/.env` configurado, desde la raíz:

```powershell
.\start.ps1
```

Levanta la base de datos, carga el catálogo y arranca backend y frontend (abre el
navegador solo). Para detener todo: `.\stop.ps1`.

> Si PowerShell bloquea el script: `powershell -ExecutionPolicy Bypass -File .\start.ps1`

## Arrancar en local (manual)

**Backend** (puerto 8000):
```bash
cd backend
uv run uvicorn app.main:app --reload --port 8000
```
Comprueba: http://localhost:8000/health · Docs API: http://localhost:8000/docs

**Frontend** (puerto 5173):
```bash
cd frontend
npm install
npm run dev
```

## Base de datos

Levanta Postgres con Docker:
```bash
docker run --name tfg-db -e POSTGRES_PASSWORD=dev -e POSTGRES_DB=tfg -p 5432:5432 -d postgres:16
```
Las tablas se crean solas al arrancar el backend (`create_all`). El backend usa
`DATABASE_URL` (por defecto apunta al contenedor de arriba); para cambiarla, copia
`backend/.env.example` a `backend/.env`.

Tablas: `estudiantes`, `carreras`, `respuestas_cuestionario`,
`resultados_psicometricos`, `uso_tokens`.

Cargar el catálogo de carreras (idempotente):
```bash
cd backend && uv run python seed_carreras.py
```

## Endpoints

| Método | Ruta | Qué hace |
|--------|------|----------|
| GET | `/health` | Estado del backend |
| POST | `/api/register` | Crea estudiante (`nombre`) |
| POST | `/api/submit-survey` | Guarda respuestas (`estudiante_id`, `respuestas`) |
| GET | `/api/departamentos` | Departamentos con catálogo cargado |
| GET | `/api/carreras` | Catálogo completo (página "Catálogo de carreras") |
| POST | `/api/next-question` | Siguiente pregunta adaptativa (tipo Akinator) |
| POST | `/api/recommend` | Recomienda carreras agrupadas con % de afinidad |
| POST | `/api/simular-dia` | "Un día siendo…" para una carrera del resultado |
| POST | `/api/comparar` | Compara dos carreras del resultado |
| POST | `/api/feedback` | 👍/👎 del estudiante sobre la recomendación |
| POST | `/api/tts` | Voz neuronal (edge-tts) para leer los mensajes del chat |
| GET | `/api/psicometrico/preguntas` | Banco de 100 ítems, sin la clave |
| POST | `/api/psicometrico` | Califica, guarda y devuelve el resumen con IA |
| GET | `/api/uso-tokens` | Consumo de tokens de Gemini por sesión |

Pruébalos en http://localhost:8000/docs

## Self-checks (sin gastar cuota de IA)

```bash
cd backend && uv run python -m app.preguntas
cd backend && uv run python -m app.psicometrico
```

## Estado

- [x] Chatbot vocacional adaptativo (Akinator): la IA decide cada pregunta según
  lo respondido. Catálogo-agnóstico, mínimo 4 y máximo 8 preguntas adaptativas.
- [x] Cobertura garantizada de las 7 dimensiones vocacionales (vector por sesión).
- [x] Selección de departamento/región en un mapa de Guatemala antes del chat.
- [x] Dashboard: barras + dona por % de afinidad, carreras agrupadas con detalle
  por institución, PDF descargable, simulador de "un día siendo…", comparador de
  dos carreras y feedback.
- [x] Voz neuronal en el chat (edge-tts) con caída a la voz del navegador.
- [x] Catálogo cerrado para Quetzaltenango (9 centros) y Totonicapán (3 centros).
- [x] Examen psicométrico de 100 ítems en pestaña aparte, con resumen de IA.
- [x] Medición de consumo de tokens y respaldo con una segunda API key.
- [ ] Extender el catálogo a más departamentos.
- [ ] Validación del test con orientadores humanos (hoy la evidencia es simulada).
