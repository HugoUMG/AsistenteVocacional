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

## Base de datos (Sprint 2)

Docker no está instalado todavía. Una vez instalado Docker Desktop, levanta Postgres:
```bash
docker run --name tfg-db -e POSTGRES_PASSWORD=dev -p 5432:5432 -d postgres:16
```
Luego copia `backend/.env.example` a `backend/.env` y ajusta `DATABASE_URL`.

## Estado

- [x] Sprint 1 — Esqueleto: backend con `/health`, frontend arrancando.
- [ ] Sprint 1 — Esquema BD (estudiantes, carreras, respuestas) + endpoints registro/encuesta.
- [ ] Sprint 2 — Pipeline ML (RandomForest) + endpoint `/api/recommend`.
- [ ] Sprint 3 — Cuestionario y resultados en React.
- [ ] Sprint 4 — Integración, pruebas y despliegue.
