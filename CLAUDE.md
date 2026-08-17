# Asistente Vocacional — CLAUDE.md

Chatbot de orientación vocacional para estudiantes de Guatemala. El alumno
conversa con un guía ("Orienta"), responde un cuestionario adaptativo y recibe
un **dashboard** con las carreras más afines a su perfil, tomadas de un catálogo
real de universidades por departamento. Aparte, en otra pestaña, hay un **examen
psicométrico** de 100 ítems que NO alimenta la recomendación.

Proyecto de graduación (TFG). Repo: https://github.com/HugoUMG/AsistenteVocacional

Este archivo es el **punto de entrada del agente**: propósito, stack, reglas
críticas e índice. El detalle vive en `docs/`, `decisions/` y `experiments/` —
leer solo lo que la tarea necesite.

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Frontend | **React** (Vite), gráficas con **Recharts**, PDF con **jsPDF** |
| Backend | **FastAPI** (Python 3.12, gestionado con **uv**), ORM **SQLAlchemy** + **psycopg** |
| Base de datos | **PostgreSQL** (en Docker) |
| Motor de IA | **API de Gemini** de Google (SDK `google-genai`), con **salida estructurada JSON** validada con Pydantic |

Modelo por defecto: `gemini-3.1-flash-lite` (configurable con `GEMINI_MODEL` en
`backend/.env`).

---

## Arquitectura resumida

```
Alumno
  ↓  elige departamento o región en el mapa (Mapa.jsx) → /chat?depto=
React (Chat.jsx)
  ↓  nombre + 4 preguntas vocacionales fijas (sin IA), con voz neuronal (/api/tts)
  ↓  4-8 preguntas adaptativas  →  POST /api/next-question
FastAPI (main.py)
  ↓  filtro.py recorta el catálogo a 35 carreras (sin IA)
Gemini (preguntas.py / recomendar.py)
  ↓  JSON estructurado validado con Pydantic
PostgreSQL (respuestas, uso de tokens, resultados)
  ↓  POST /api/recommend
Dashboard.jsx (barras + dona + detalle por institución + PDF)
  ↓  extras on-demand, 1 llamada c/u: /api/simular-dia · /api/comparar
```

Aparte del chat, la app es **multipágina** (`react-router`): inicio, acerca,
catálogo público, parámetros, mapa y examen psicométrico. Ver
[docs/frontend-y-diseno.md](docs/frontend-y-diseno.md).

Flujo completo, estructura de carpetas y cómo correrlo:
[docs/arquitectura.md](docs/arquitectura.md).

---

## Cómo correrlo

**Rápido (Windows):** desde la raíz, con Docker Desktop instalado y `backend/.env`
configurado:
```powershell
.\start.ps1     # levanta BDD + backend + frontend y abre el navegador
.\stop.ps1      # detiene todo
```
Manual y self-checks sin API: [docs/arquitectura.md](docs/arquitectura.md).

---

## Reglas críticas

1. **No reemplazar Gemini por un modelo ML entrenado** sin releer
   [decisions/llm-vs-red-neuronal.md](decisions/llm-vs-red-neuronal.md). Fue una
   decisión consciente, no una etapa pendiente.
2. **El catálogo es la fuente de verdad.** Los prompts son
   **catálogo-agnósticos** (no mencionan carreras concretas): agregar
   carreras/centros no requiere tocar código.
3. **No modificar los prompts vocacionales** (`preguntas.py`, `recomendar.py`)
   sin leer `experiments/` primero. Ya hay un intento que sonaba bien y midió
   peor (microexperiencias, 6/10 vs 10/10) y otro que arregló una brecha real
   (cobertura de dimensiones, 40%→100%).
4. **Todo cambio de prompt o de heurística se mide antes de aceptarse.** Si mide
   peor, se revierte y se documenta en `experiments/`.
5. **Paleta azul/navy/gris/negro.** Los verdes/rojos/naranjas que quedan son
   semánticos a propósito — no "corregirlos". Ver
   [docs/frontend-y-diseno.md](docs/frontend-y-diseno.md).
6. **No subir `backend/.env`** (contiene la API key). El default seguro está en
   `.env.example`. Nunca crear proyectos gratis extra de Google para multiplicar
   cuota (viola los ToS).
7. **Español** en UI, comentarios, mensajes y documentación.
8. Los comentarios `ponytail:` en el código marcan simplificaciones deliberadas
   con techo conocido — leer el comentario antes de "arreglarlas".
9. **Holland es el instrumento de intereses.** No reimplementar sus ítems ni su
   calificación: los sirve la API de O*NET. El **CIP salió del menú** (2026-08-16)
   por falta de autorización de uso — no reponerlo ni invertirle trabajo hasta
   que exista permiso escrito. Ver [docs/holland.md](docs/holland.md).

---

## Índice documental

**Arquitectura y operación**
- [docs/arquitectura.md](docs/arquitectura.md) — flujo del test, estructura de
  carpetas, qué datos se guardan, cómo correrlo.
- [docs/api.md](docs/api.md) — endpoints y notas de validación.
- [docs/frontend-y-diseno.md](docs/frontend-y-diseno.md) — dashboard, paleta,
  detalles de UI que no se deben "mejorar" sin leer el motivo.

**Dominio**
- [docs/motor-ia.md](docs/motor-ia.md) — cómo llega a la recomendación, cobertura
  de las 7 dimensiones vocacionales, intento descartado de microexperiencias.
- [docs/psicometrico.md](docs/psicometrico.md) — examen de 100 ítems: secciones,
  calificación, coherencia, deseabilidad social, baremo y sus límites.
- [docs/holland.md](docs/holland.md) — test RIASEC servido por la API oficial de
  O*NET (proxy con API key, no reimplementación). **Es el instrumento de
  intereses del proyecto**; incluye la tabla de qué mide cada test y las
  decisiones abiertas (¿alimenta la recomendación?, persistencia).
- [docs/catalogo.md](docs/catalogo.md) — universidades cargadas y cómo agregar más.

**Decisiones técnicas** (fecha · motivo · alternativas descartadas · consecuencias)
- [decisions/llm-vs-red-neuronal.md](decisions/llm-vs-red-neuronal.md)
- [decisions/gemini-costos-y-caching.md](decisions/gemini-costos-y-caching.md) —
  modelo, cuotas, backoff, key de respaldo, context caching y costos medidos.
- [decisions/filtro-catalogo.md](decisions/filtro-catalogo.md) — pre-filtro sin IA
  (`TOP_DEFAULT = 35`) y su límite con la negación.

**Experimentos** (evidencia medida)
- [experiments/cobertura-dimensiones.md](experiments/cobertura-dimensiones.md) —
  A/B del vector de cobertura: 40%→100% de cumplimiento, 7/10→10/10 de acierto.
- [experiments/microexperiencias.md](experiments/microexperiencias.md) — intento
  revertido: 6/10, transcripciones y diagnóstico.
- [experiments/psicometrico-en-chat.md](experiments/psicometrico-en-chat.md) —
  psicométrico primero y chat sin preguntas fijas: NO se integra. Las fijas y el
  test miden cosas distintas (intereses declarados vs. aptitud real) y quitarlas
  costó el canal de revelación de los chips y la alerta de contradicción.
- [experiments/cip-en-recomendacion.md](experiments/cip-en-recomendacion.md) —
  CIP priorizando el catálogo: revertido (9/10 vs 10/10), y el diseño no llegó a
  probar la hipótesis. Flag `CIP_EN_RECOMENDACION`, apagado.
- [docs/prompt-next-question-ejemplo.md](docs/prompt-next-question-ejemplo.md) —
  ejemplo real del prompt que recibe Gemini.
