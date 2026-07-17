# Asistente Vocacional — CLAUDE.md

Chatbot de orientación vocacional para estudiantes de Guatemala. El alumno
conversa con un guía ("Orienta"), responde un cuestionario adaptativo y recibe
un **dashboard** con las carreras más afines a su perfil, tomadas de un catálogo
real de universidades por departamento.

Proyecto de graduación (TFG). Repo: https://github.com/HugoUMG/AsistenteVocacional

---

## ¿Qué tecnología usa?

| Capa | Tecnología |
|------|-----------|
| Frontend | **React** (Vite), gráficas con **Recharts** |
| Backend | **FastAPI** (Python 3.12, gestionado con **uv**), ORM **SQLAlchemy** + **psycopg** |
| Base de datos | **PostgreSQL** (en Docker) |
| Motor de IA | **API de Gemini** de Google (SDK `google-genai`), con **salida estructurada JSON** validada con Pydantic |

> **Decisión clave:** la recomendación la hace un **LLM (Gemini)**, NO una red
> neuronal entrenada. Motivo: el requisito del TFG es "aprovechar la IA para
> simplificar el proceso" (no exige un modelo entrenado con métricas) y no hay
> datos de entrenamiento etiquetados. Entrenar una red con datos simulados sería
> circular. El LLM además entiende el texto libre del cuestionario.

Modelo por defecto: `gemini-3.1-flash-lite` (configurable con `GEMINI_MODEL` en
`backend/.env`). Se eligió por su cuota gratuita amplia (~500 req/día).

---

## ¿Cómo funciona el flujo?

El test es **híbrido** (preguntas fijas + adaptativas) para gastar poca cuota de IA:

1. **Nombre** (fijo, sin IA) — para saludar y personalizar.
2. **Departamento** (fijo) — el alumno elige: Quetzaltenango, Totonicapán o
   **Ambos**. Esto **filtra** el catálogo: solo esas carreras alimentan el resto.
3. **3 preguntas vocacionales fijas** (sin IA): impacto que quiere tener (multi),
   cómo prefiere trabajar (multi) y qué temas le apasionan (texto libre).
4. **Hasta 3 preguntas adaptativas** (IA, tipo "Akinator"): Gemini genera cada
   pregunta según lo respondido, para descartar unas carreras y reforzar otras.
   Puede terminar antes si el perfil ya es claro.
5. **Análisis final** (IA): genera la recomendación y muestra el dashboard.

Costo aprox.: **~4 llamadas a Gemini por test** (hasta 3 adaptativas + 1 final).
Las preguntas de opción múltiple permiten elegir varias, una opción "Otro" con
texto libre, y hay botón "← Regresar" para corregir respuestas.

---

## ¿Cómo llega a una recomendación?

1. Cada carrera del catálogo tiene un **"banco de palabras" / perfil** (afinidades,
   habilidades, entorno, gustos, estilo cognitivo). Vive en la tabla `carreras`.
2. En `/api/recommend`, el backend toma el catálogo **filtrado por el departamento
   elegido** ("Ambos" = sin filtro) y lo pasa, junto con las respuestas del
   estudiante, a Gemini (`backend/app/recomendar.py`).
3. Gemini devuelve un JSON estructurado donde:
   - **Agrupa por carrera**: una misma carrera ofrecida por varios centros o
     departamentos es **un solo grupo** con varias instituciones.
   - Asigna a cada carrera un **% de afinidad** (los porcentajes suman 100).
   - Da una **descripción general** por carrera y, por cada institución, su
     universidad, centro, departamento y **enfoque/sello particular**.

Las preguntas adaptativas usan la misma idea en `backend/app/preguntas.py`.

---

## ¿Qué recibe el usuario al final?

Un **dashboard a pantalla completa** con:
- **Gráfico de barras** de todas las carreras con afinidad > 1%.
- **Gráfico de dona** que al pasar el mouse muestra la carrera y su % en grande.
- **Lista de carreras** con color distintivo por carrera.
- Panel de detalle por carrera: **descripción general** + selector de
  **instituciones** (centro · departamento) que revela el enfoque de cada una.

Ejemplo: si sale "Derecho" con "Ambos", ve las 4 sedes juntas (CUNTOTO, URG, UMG
en Totonicapán y CUNOC en Quetzaltenango), cada una con su sello.

---

## ¿Qué información recopila?

Se guarda en PostgreSQL (`backend/app/models.py`):
- **`estudiantes`**: nombre (el email es opcional, hoy no se pide).
- **`respuestas_cuestionario`**: todas las respuestas del test como JSON, ligadas
  al estudiante.
- **`carreras`**: el catálogo (nombre, departamento, centro, universidad, perfil).

No se recopilan datos sensibles ni credenciales. La `GEMINI_API_KEY` vive solo en
`backend/.env` (ignorado por git, nunca se sube al repo).

---

## Estructura

```
.
├── backend/                FastAPI + motor de IA
│   ├── app/
│   │   ├── main.py         endpoints
│   │   ├── models.py       tablas (estudiantes, carreras, respuestas)
│   │   ├── db.py           conexion SQLAlchemy
│   │   ├── recomendar.py   recomendacion con Gemini (agrupada por carrera)
│   │   └── preguntas.py    preguntas adaptativas con Gemini
│   ├── data/*.json         catalogo de carreras por centro
│   ├── seed_carreras.py    carga data/*.json a la BD (idempotente)
│   └── .env                DATABASE_URL, GEMINI_API_KEY, GEMINI_MODEL (no en git)
├── frontend/               React (Vite)
│   └── src/
│       ├── App.jsx         chat (fijas + adaptativas), fases chat/loading/dashboard
│       ├── Dashboard.jsx   graficas + detalle por carrera/institucion
│       └── colors.js       paleta compartida
├── start.ps1 / stop.ps1    levantan / detienen todo con un comando
└── README.md
```

### Endpoints
| Método | Ruta | Qué hace |
|--------|------|----------|
| GET | `/api/departamentos` | Lista departamentos (para el filtro) |
| POST | `/api/register` | Crea estudiante |
| POST | `/api/submit-survey` | Guarda las respuestas |
| POST | `/api/next-question` | Siguiente pregunta adaptativa (filtra por departamento) |
| POST | `/api/recommend` | Recomienda carreras agrupadas con % (filtra por departamento) |

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
`centro`, `universidad` y las `carreras` con su `perfil`) y correr `seed_carreras.py`.

---

## Convenciones

- Español en UI, comentarios y mensajes.
- El catálogo es la fuente de verdad: los prompts de IA son **catálogo-agnósticos**
  (no mencionan carreras concretas), así que agregar carreras/centros no requiere
  tocar código.
- No subir `backend/.env` (contiene la API key). El default seguro está en
  `.env.example`.
