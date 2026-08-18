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

El alumno elige uno de **tres modos** en el inicio: solo chat, solo el test de
Holland, o **Holland y luego el chat** (modo 3: el chat parte del perfil RIASEC
medido). El diagrama de abajo es el chat; en el modo 3 llega con el perfil de
Holland encima, y **las 4 preguntas fijas se quedan igual** — quitarlas se midió
y salió peor ([experiments/holland-en-chat.md](experiments/holland-en-chat.md)).

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
10. **Holland NO alimenta la recomendación.** Se midió **tres veces** y el
    ranking no se movió: como texto en el prompt, con el catálogo codificado en
    RIASEC, y con ese catálogo **revisado a mano** (90/90, 18 códigos
    cambiados). No afirmarlo en la tesis. La revisión del catálogo ya está
    hecha: **no es el paso pendiente y no vale la pena reintentarla**. Lo único
    sin probar es el prompt de arbitraje entre lo declarado y lo medido, ver la
    decisión abierta #5 de [docs/holland.md](docs/holland.md).
11. **NUNCA uses la raya o guion largo (—) ni dobles guiones (--) en tus
    respuestas, descripciones de documentos, textos web, comentarios de código
    o código fuente.** En su lugar, utiliza comas para aclaraciones breves,
    puntos para separar ideas en frases cortas, o guiones cortos estándar (-)
    únicamente si la sintaxis del código o lenguaje lo requiere. Los "—" que ya
    existen en este repo son históricos: no es necesario purgarlos, solo no
    agregar más.

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
- [docs/personalidad.md](docs/personalidad.md) — test corto (48 ítems, sin IA)
  de personalidad/valores/estilo cognitivo, pre-chat, mismo patrón que
  Holland. Pendiente de medir si mueve el ranking.
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
- [experiments/holland-en-chat.md](experiments/holland-en-chat.md) — modo
  "Holland → chat": las 4 fijas se quedan (más baratas y más cortas), y el bloque
  de Holland en el prompt **no pesa** en la recomendación (5/6 corridas).
- [experiments/holland-apertura.md](experiments/holland-apertura.md) — obligar
  al chat a nombrar el resultado de Holland en su primera pregunta se cumple
  siempre (6/6) y no cambia el ranking (4/5 corridas iguales): cambia la
  experiencia de apertura, no el motor. Se adopta.
- [experiments/holland-estructura.md](experiments/holland-estructura.md) —
  catálogo codificado con los RIASEC de O*NET y ordenado por afinidad: el top-1
  no cambió (0/2). Flag `HOLLAND_EN_RECOMENDACION`, apagado. §8 revisó el
  catálogo a mano (90/90, 18 códigos cambiados) y §9 repitió el A/B con el
  catálogo revisado: **0/2 otra vez**. Los términos de búsqueda corregidos y los
  que midieron peor viven en `codificar_holland.py`, con el motivo.
- [experiments/holland-sondeo-intereses.md](experiments/holland-sondeo-intereses.md) —
  obligar al chat a gastar un turno sondeando el interés MEDIDO (cobertura de
  `intereses` pendiente y prioritaria). El mecanismo cumple 6/6 pero no mejora:
  5/6 contra 6/6, +1 pregunta y +12% de tokens. **No se integra.** Ojo, el
  control salió en el techo (6/6), así que no descarta la hipótesis. Deja dos
  cosas: forzar la elección entre lo declarado y lo medido se resuelve a favor
  de lo declarado, y la sospecha de que la apertura explícita pesa más de lo que
  midió `holland-apertura.md`.
- [experiments/cip-en-recomendacion.md](experiments/cip-en-recomendacion.md) —
  CIP priorizando el catálogo: revertido (9/10 vs 10/10), y el diseño no llegó a
  probar la hipótesis. Flag `CIP_EN_RECOMENDACION`, apagado.
- [experiments/comparacion-modelos.md](experiments/comparacion-modelos.md) —
  `gemini-3.5-flash-lite` contra el actual: 2/5 top-1 cambiaron y leyeron peor
  la señal indirecta, cuesta 25-40% más. Se mantiene `gemini-3.1-flash-lite`.
  `gemini-3.7-flash` no se pudo medir (503 persistente de Google, 2026-08-17).
- [docs/prompt-next-question-ejemplo.md](docs/prompt-next-question-ejemplo.md) —
  ejemplo real del prompt que recibe Gemini.
