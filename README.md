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

## Arrancar en local

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

Pruébalos en http://localhost:8000/docs

## Estado

- [x] Sprint 1 — Esqueleto: backend `/health`, frontend arrancando, flujo verificado.
- [x] Sprint 1 — Esquema BD + endpoints `/api/register` y `/api/submit-survey`.
- [ ] Sprint 2 — Pipeline ML (RandomForest) + endpoint `/api/recommend`.
- [ ] Sprint 3 — Cuestionario y resultados en React.
- [ ] Sprint 4 — Integración, pruebas y despliegue.
