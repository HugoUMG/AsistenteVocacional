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

## Costo, cuota y Context Caching

**Modelo:** `gemini-3.1-flash-lite` para ambas variables (`GEMINI_MODEL` y
`GEMINI_MODEL_FINAL`, ver `.env.example`). Se eligió porque, comparado con
`gemini-2.5-flash` (el original) y `gemini-3.5-flash`, es el más barato
($0.25/$1.50 por 1M tokens input/output) **y** el de mejor cuota gratis
(500 RPD vs 20 RPD de los otros dos). Con un solo modelo para todo, ya no se
comparte el pool de 20 RPD entre `next-question`/`recommend` y el análisis
final — motivo del 500 que se veía antes al agotar cuota.

**RPM = 15 requests/minuto** es un techo duro y real del tier gratis
(confirmado por el propio error de Google: `Quota exceeded... limit: 15`).
Con tráfico concurrente (p. ej. una clase completa arrancando el test a la
vez) se puede superar; `recomendar.py` reintenta con backoff (ver abajo) pero
eso amortigua picos, no sustituye tener billing si el tráfico real lo exige.

**Reintento con backoff** (`_con_reintento` en `recomendar.py`): ante
429/500/503 de Gemini, reintenta hasta 4 veces. Si el 429 trae el
`retryDelay` real que manda Google (RPM agotado), espera exactamente eso
(tope 30s); si no, usa backoff exponencial + jitter (1s, 2s, 4s...). Otros
códigos (400, etc.) se propagan de inmediato, sin reintentar.

**Medición de tokens** (tabla `uso_tokens`, endpoint `GET /api/uso-tokens`):
cada llamada a Gemini registra `prompt_tokens`, `output_tokens`,
`total_tokens` y `cached_tokens` (de `usage_metadata.cached_content_token_count`)
por `session_id` (uno por carga de página, ver `frontend/src/session.js`).
Medido en pruebas reales: un flujo completo (3 adaptativas + 1 recomendación)
gasta **~68,100 tokens** (bajó de ~76,000 tras la optimización de catálogo de
abajo), de los cuales el catálogo de carreras repetido en cada llamada sigue
siendo la parte dominante (el resto es el perfil del estudiante).

**Optimización: `next-question` no recibe datos de institución.**
`_catalogo_texto(carreras, incluir_instituciones=False)` en `recomendar.py`
omite universidad/centro/departamento/sello de cada sede — usado solo por
`preguntas.py`, cuyo propio prompt ya pide "no menciones nombres [de
universidades]" y nunca necesitó esa info (solo el banco de palabras de cada
carrera para decidir la siguiente pregunta). `recomendar.py` (endpoint
`/recommend`) sigue mandando el catálogo completo, porque sí arma el detalle
por institución. Medido real: el prompt de `next-question` bajó de ~18,450 a
**~15,820 tokens/llamada** (-2,630, calca el estimado calculado del catálogo).
Con 3 llamadas `next-question` por sesión, ahorra **~7,900 tokens/sesión**
(~10% del total), sin tocar la calidad de la pregunta generada.

**Context Caching ya está implementado** (`_get_cache`/`generar` en
`recomendar.py`), usando el SDK oficial nuevo (`google-genai`, **no**
`google-generativeai`, que está deprecado): sube el catálogo una vez con
`client.caches.create(...)` y las llamadas siguientes lo referencian con
`cached_content=name` en vez de reenviarlo. La clave del caché es un hash de
`(modelo, system, catálogo)`, así que:
- Si cambia el catálogo (reseed) o el filtro de departamento, se crea un
  caché nuevo automáticamente — no hay que borrar ni apuntar a mano el viejo.
- `next-question` y `recommend` usan *system prompts* distintos → dos cachés
  separados, no comparten uno solo.
- TTL de 1h; si expira (404), el código lo recrea solo, sin intervención.

**Por qué el caching EXPLÍCITO no se ve todavía:** el tier gratis de Google
tiene el almacenamiento de caché en 0
(`TotalCachedContentStorageTokensPerModelFreeTier limit=0`), así que
`caches.create` siempre falla ahí y todo cae a inline (la app no se rompe,
pero no ahorra por esta vía). Se activa solo con **billing habilitado** en el
proyecto de Google Cloud.

**Pero SÍ hay ahorro real hoy, vía *implicit caching*** (confirmado en
`/api/uso-tokens` con `cached_tokens > 0` sin billing activo). Es un mecanismo
DISTINTO al de `_get_cache`, automático en toda la familia Gemini 2.5+
(incluye `3.1-flash-lite`), activo también en tier gratis:
- Se activa cuando dos llamadas comparten el mismo **prefijo exacto** al
  inicio del prompt. Por eso `generar()` ya construye el prompt inline como
  `f"{catalogo}\n\n{variable}"` — catálogo (fijo) primero, respuesta del
  alumno (variable) al final; es la práctica recomendada por Google para
  maximizar cache hits, y no hubo que tocar nada para cumplirla.
- Umbral mínimo ~1,024 tokens de prompt (Gemini 2.5 Flash) — el catálogo
  (~15,800-18,100 tokens según endpoint) lo supera de sobra.
- Es oportunista y de corta duración (infraestructura de servido de Google,
  no un `CachedContent` con TTL propio): si dos llamadas con el mismo
  prefijo se hacen seguidas, la segunda cachea; si pasa mucho tiempo sin
  tráfico repetido, se pierde.
- Mismo descuento que el explícito: 90% menos en los tokens que cachean.

Medido real (sesión completa, sin billing): de las 3 llamadas `next-question`,
la #2 y #3 cachearon **11,930 tokens cada una** (comparten prefijo con la #1);
la #1 (nada previo) y `recommend` (system prompt distinto → prefijo distinto,
primera vez en la corrida) no cachearon. Con billing y el caching EXPLÍCITO
completo se cubrirían las 4 llamadas (no solo 2 de 4) con una ventana
garantizada de 1h en vez de depender de que el tráfico sea seguido.

**Estimado de ahorro con caching activo** (recalculado con los ~68k
tokens/sesión post-optimización, ~97% catálogo cacheable, precio de caché =
10% del precio normal de input, ambos con `gemini-3.1-flash-lite`):

| Sesiones | Sin caché | Con caché | Ahorro |
|---|---|---|---|
| 150 | $2.99 | $0.84 | 72% |
| 200 | $3.98 | $1.12 | 72% |

Más ~$1.00/1M tokens/hora de almacenamiento (con ~18k tokens de catálogo ×
2 cachés ≈ $0.036/hora — insignificante).

**Respaldo con un segundo proyecto (`GEMINI_API_KEY_RESPALDO`, activo hoy con
dos proyectos GRATIS para pruebas/demo):** si el proyecto primario agota su
RPD/RPM (429 tras agotar los reintentos de `_con_reintento`), `generar()`
reintenta UNA vez con la key de `GEMINI_API_KEY_RESPALDO` (backend/.env), si
está configurada. **Debe ser un proyecto de Google Cloud DISTINTO** — la
cuota gratis de Gemini es *por proyecto*, no por API key (confirmado en el
propio error de Google: `GenerateRequestsPerMinutePerProjectPerModel-FreeTier`),
así que una segunda key del MISMO proyecto no ayuda en nada. Cuando se activa
el fallback, se imprime `[gemini] key primaria agoto cuota (429),
reintentando con GEMINI_API_KEY_RESPALDO` en el log del backend — sirve para
confirmarlo en pruebas.

El caché de contexto (`_get_cache`) trata cada proyecto por separado (clave
incluye `"primaria"`/`"respaldo"`): un `CachedContent` creado en un proyecto
no existe en el otro, así que nunca se intenta reusar uno en el proyecto
equivocado. Sin `GEMINI_API_KEY_RESPALDO` configurada (o vacía), el
comportamiento es idéntico a antes: un 429 agotado se propaga tal cual.

**Verificado con pruebas de carga reales** (15 flujos completos en paralelo,
register→3 adaptativas→recommend = 60 llamadas reales a Gemini):
- **Sincronizado** (los 15 arrancan en el mismo segundo, peor caso): 59/60
  llamadas exitosas, el respaldo se activó 12 veces.
- **Escalonado** (arranques repartidos en ~90s, más parecido a un salón
  real): **60/60 llamadas exitosas**, el respaldo se activó solo 2 veces.

Con tráfico realista (estudiantes no hacen clic en el mismo milisegundo), la
combinación backoff+respaldo prácticamente elimina los errores de cuota que
el estudiante podría ver — a costa de que, en los picos, esa sesión puntual
tarde más en responder (Google puede pedir esperar ~24s en vez de fallar).

⚠️ **No crear muchos proyectos gratis "extra"** para multiplicar cuota: los
Términos de Servicio de la API de Gemini prohíben circunvenir límites de
cuota, y Google puede detectar el patrón (varios proyectos gratis nuevos
pegándole a la misma API desde el mismo backend) y suspender la cuenta
completa. Un proyecto gratis + uno de respaldo con billing (que cuesta
centavos, ver tabla arriba) es la combinación razonable — no una carrera de
keys.

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
