# Recomendador Vocacional (TFG)

Sistema que captura el perfil de un estudiante y recomienda carreras mediante un
modelo de Machine Learning.

**Stack:** React (Vite) · FastAPI · PostgreSQL · scikit-learn

## Estructura

```
.
├── backend/     FastAPI + (futuro) modelo scikit-learn   [Python 3.12, uv]
└── frontend/    React + Vite
```

## Requisitos

- Python 3.12+ y [uv](https://docs.astral.sh/uv/)
- Node.js 20+ y npm
- Docker Desktop (para Postgres, a partir del Sprint 2)

## Inicio rápido (un comando)

Con Docker Desktop instalado y `backend/.env` configurado, desde la raíz del proyecto:

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

Tablas: `estudiantes`, `carreras`, `respuestas_cuestionario`.

## Endpoints

| Método | Ruta                 | Qué hace                                  |
|--------|----------------------|-------------------------------------------|
| GET    | `/health`            | Estado del backend                        |
| POST   | `/api/register`      | Crea estudiante (`nombre`, `email`)       |
| POST   | `/api/submit-survey` | Guarda respuestas (`estudiante_id`, `respuestas`) |
| GET    | `/api/departamentos` | Lista los departamentos disponibles (para el filtro) |
| POST   | `/api/next-question` | Devuelve la siguiente pregunta adaptativa (Akinator) según lo respondido |
| POST   | `/api/recommend`     | Recomienda carreras con IA (Gemini) según el perfil |

Pruébalos en http://localhost:8000/docs

## Estado

- [x] Sprint 1 — Esqueleto: backend `/health`, frontend arrancando, flujo verificado.
- [x] Sprint 1 — Esquema BD + endpoints `/api/register` y `/api/submit-survey`.
- [x] Chatbot vocacional adaptativo (tipo Akinator): la IA decide cada pregunta
  según lo respondido, descartando/reforzando carreras. Catálogo-agnóstico.
- [x] Dashboard de resultados: barras + dona por % de afinidad, carreras
  agrupadas con detalle por institución.
- [x] Filtro por departamento: el estudiante elige su departamento y solo esas
  carreras alimentan las preguntas y la recomendación.
- [x] Catálogo: Totonicapán (CUNTOTO, URG, UMG) y Quetzaltenango (CUNOC).
- [x] Sprint 2 — Motor de recomendación con IA (Gemini) + `/api/recommend`.
  Catálogo en `backend/data/*.json`, cargado con `uv run python seed_carreras.py`.
- [x] Frontend conectado a `/api/recommend`: muestra las carreras al final del chat.
- [ ] Configurar `GEMINI_API_KEY` para probar recomendaciones reales.
- [ ] Sprint 3 — Cuestionario y resultados en React.
- [ ] Sprint 4 — Integración, pruebas y despliegue.
