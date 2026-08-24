# Costo, cuota y Context Caching de Gemini

**Última medición con `count_tokens`:** 2026-08-02, catálogo de 202 filas.
Archivo principal: `backend/app/recomendar.py`.

---

## ✅ Caching explícito ACTIVO — medido con billing (2026-08-11)

Con billing habilitado en el proyecto primario, `caches.create` ya no falla y el
`_get_cache` de `recomendar.py` funciona sin tocar una línea de código. Medido con
**24 conversaciones completas reales** (4 en paralelo, filtro Quetzaltenango,
144 llamadas a Gemini, 6 por sesión: 5 `next-question` + 1 `recommend`):

| | Total 24 sesiones | Por sesión |
|---|---|---|
| Prompt | 1,276,822 tok | 53,201 |
| **Cacheados** | **1,212,466 tok (95.0%)** | 50,519 |
| Salida | 63,271 tok | 2,636 |
| Total | 1,340,093 tok | 55,837 |
| **Costo real** | **$0.1413** | **$0.0059** |
| Costo si nada cacheara | $0.4141 | $0.0173 |
| **Ahorro** | **65.9%** | |

Proyección: **$0.59 / 100 sesiones · $1.18 / 200 sesiones** (contra $1.73 / $3.45
sin caché). Confirma el estimado del 2026-08-02 (64-65%) casi exacto.

**Contrastado con la factura real de Google:** el crédito prepago bajó de $10.00 a
**$9.85 = $0.15 cobrados** por las 25 sesiones (la de humo + las 24), contra los
$0.147 que calculó el script — **~2% de diferencia**. Los ~$0.003 que faltan son el
almacenamiento del caché ($1/1M tok/hora), que `flujo_gasto.py` no contabiliza.
A este ritmo ($0.006/sesión), $10 de crédito cubren **~1,650 conversaciones
completas**.

⚠️ La consola de Pagos tiene **latencia de horas**: media hora después de la corrida
marcaba $0.12 y el número final fue $0.15. No leer el crédito inmediatamente después
de medir.

El 5% que no cachea es el historial del alumno (variable por definición) más la
primera llamada de cada caché nuevo. 1 de las 25 sesiones falló por `ReadTimeout`
con 4 flujos concurrentes — no es error de cuota (con billing el RPM ya no
aprieta), es el timeout del cliente de prueba.

⚠️ **La key con billing debe ir en `GEMINI_API_KEY`** (la primaria), no en
`GEMINI_API_KEY_RESPALDO`: el caché se crea en el proyecto del cliente que
efectivamente se usa (`key_label` en `_clave_cache`), así que si la de pago es la
de respaldo, el caché solo se activaría cuando la gratis agote cuota. Y hay que
**reiniciar el backend** tras cambiar la key: `_caches` memoriza en memoria el
fallo anterior y no lo reintenta.

Reproducir: `backend/flujo_gasto.py` (N conversaciones completas contra el backend
local, lee `/api/uso-tokens` y calcula ambos costos).

## El pre-filtro crea un caché por llamada (2026-08-23)

El caché se indexa por `sha256(system + catálogo)`, y el catálogo de
`next-question` sale de `filtro.preseleccionar`, que se recalcula tras cada
respuesta. Resultado: el hash cambia en cada llamada y se crea **un
CachedContent nuevo cada vez** (9 cachés en 9 llamadas, medido). Como el
almacenamiento se cobra por hora y por caché, eso es una renta por alumno que
nunca se amortiza. Mandar el catálogo completo deja **1 caché para todo el
grupo**. Números, brazos y bloqueantes en
[../experiments/cache-compartido.md](../experiments/cache-compartido.md).

⚠️ **El % cacheado no sirve para detectar esto.** Un caché recién creado ya
reporta sus tokens como cacheados, así que ambos brazos dan >94%. La métrica es
el **número de cachés distintos**.

⚠️ **`uso_tokens` oculta el 38% del gasto real (verificado 2026-08-24).** La
factura de Google, agrupada por SKU, trae
`Generate content cached content storage token hours`: 597,510 tokens-hora por
**$0.60 de un total de $1.59**, la línea individual más cara, por encima de la
salida y del input. El precio implícito es $1.004/1M tokens-hora, exacto contra
el de lista. Como esa tabla solo registra tokens, **toda cifra sacada de ella es
una cota inferior**, incluidas las proyecciones de este archivo. Detalle en
[../experiments/cache-compartido.md](../experiments/cache-compartido.md) §8.

## La key con billing ya es la primaria en local (2026-08-23)

Verificado probando `caches.create` con cada una: `GEMINI_API_KEY` crea cachés,
`GEMINI_API_KEY_RESPALDO` falla con 429. En **Render también** está la de
billing como primaria (corroborado por el autor). **Corrige lo que dice
`experiments/filtro-catalogo-ab.md`**, que quedó viejo.

Las 7 sesiones de Neon dan 28.5% de cacheado global, dentado entre 0% y 92.6%,
pero eso es **historia, no estado actual**: el cambio en Render entró entre las
dos últimas sesiones, la anterior da 0% (key gratis) y la posterior 92.6% (key
con billing). Ese 92.6% coincide con el 94.6% medido en local, o sea el caché
explícito ya corre bien en producción. Al leer promedios de esta tabla, filtrar
por fecha: `backend/gasto_24h.py 48`.

Diagnóstico rápido de cualquier base: `backend/gasto_24h.py`, que imprime el %
cacheado por sesión y el global.

## Los experimentos no quedaban en `uso_tokens` (2026-08-12)

`uso_tokens` solo se llena desde los endpoints (`_registrar_uso` en `main.py`).
Los scripts `experimento_*.py` llaman a `recomendar.generar()` **directo, sin pasar
por FastAPI**, así que su consumo era invisible: se gastaron **$0.86 de crédito**
(de $9.85 a $8.99) sin una sola fila en la tabla.

Agrava el problema tener la key de pago como respaldo: cuando la gratis agota su
RPD, `generar()` salta sola a la de pago y **todo lo que sigue se factura en
silencio**, sin que nadie lo pida explícitamente.

**Solución (`_GASTO` / `resumen_gasto()` en `recomendar.py`):** contador en memoria
del proceso, por proyecto (primaria/respaldo), que acumula en `generar()` — el único
punto por donde pasan todas las llamadas. Los experimentos lo imprimen al terminar:

```
Gasto en Gemini de este proceso:
  key primaria [gratis: $0 real]: 55 llamadas | 2,750,000 prompt (0 cacheados) | ...  ->  $0.7000
  key respaldo [billing: SE FACTURA]: 12 llamadas | ...  ->  $0.1500
  TOTAL si todo fuera de pago: $0.8500
```

La marca `[billing]` no se configura: sale de `_caches`, porque `caches.create` solo
funciona con plan de pago. La fila de la key gratis es "lo que habría costado".

No reemplaza a `uso_tokens` (que persiste y es por sesión de alumno): es para los
scripts, que mueren al terminar.

---

## Prueba de carga con la key GRATIS de primaria (2026-08-12)

Configuración recomendada para desarrollo (gratis primaria, de pago en
`GEMINI_API_KEY_RESPALDO`), **10 sesiones completas lanzadas en paralelo en el
mismo segundo** (peor caso), 60 llamadas a Gemini:

| | Resultado |
|---|---|
| Llamadas exitosas | **60/60** |
| Saltos a `GEMINI_API_KEY_RESPALDO` | **0** (ningún 429 agotó los reintentos) |
| Prompt cacheado | 33.4% (caching **implícito**, la key gratis no crea `CachedContent`) |
| Costo real | **$0.00** |
| Latencia por sesión | 135s la más rápida · **267s la más lenta** |

**El techo del tier gratis se paga en tiempo, no en dinero.** Ninguna sesión bajó
de 135s; con la key de pago de primaria la más rápida fue de 19s. Los 15 RPM se
saturan, `_con_reintento` espera lo que Google pide y todos hacen fila — pero
nadie falla. Por eso: gratis para desarrollo, de pago para la demo.

El **caching implícito volvió a aparecer** (33.4%) después de las dos pruebas del
2026-07-21 que dieron 0%. Confirma que el mecanismo existe en tier gratis y que se
activa con llamadas simultáneas de prefijo idéntico, pero sigue siendo oportunista:
no presupuestar con él.

⚠️ `flujo_gasto.py` imprime el costo asumiendo que **todas** las llamadas fueron
con key de pago (`uso_tokens` no guarda qué key atendió cada una). Con la gratis de
primaria ese número es una cota superior, no el gasto real.

---

## Medición vigente (2026-08-02)

Medido con `client.models.count_tokens` contra la BD ya sembrada
(`seed_carreras.py`, 202 filas: 185 Quetzaltenango + 17 Totonicapán), sumando
`system_instruction` + `contents` de cada llamada. **No incluye** el
`response_schema` (unos cientos de tokens más por llamada) ni los tokens de
salida.

System prompts: **1,435 tok** (`next-question`) · **830 tok** (`recommend`).

| Filtro | Catálogo `next-question` (con pre-filtro top-35) | Catálogo `next-question` sin pre-filtro | Catálogo `recommend` (completo) |
|---|---|---|---|
| Solo Totonicapán (17 filas → 14 bloques) | 4,772 | 4,772 | 4,761 |
| Solo Quetzaltenango (185 → 85 bloques) | **4,376** | 23,321 | 23,310 |
| Ambos (202 → 90 bloques) | **4,559** | 25,119 | 25,108 |

El pre-filtro deja el catálogo de `next-question` **casi constante (~4.4-4.8k
tok)** sin importar el departamento: las 35 filas que sobreviven se deduplican a
**16 bloques** por `perfil_grupo`. En Totonicapán no recorta nada (17 filas < 35).

**Prompt total de una sesión mínima** (4 adaptativas + 1 recomendación):

| Filtro | Con pre-filtro (hoy) | Sin pre-filtro | Ahorro del filtro |
|---|---|---|---|
| Solo Totonicapán | 31,869 tok | 31,869 tok | 0% (no recorta) |
| Solo Quetzaltenango | **48,834 tok** | 124,614 tok | **61%** |
| Ambos | **51,349 tok** | 133,589 tok | **62%** |

Del prompt de una sesión, **el 97% es cacheable** (system + catálogo, idénticos
entre llamadas): 47,384 de 48,834 en Quetzaltenango; 49,914 de 51,349 en "Ambos".
Lo único fresco son ~1,450 tok de historial del estudiante.

Los **tokens de salida** siguen en la última medición real disponible:
**~2,900 por sesión** (`count_tokens` no puede medir salida).

**Otras llamadas que gastan cuota** (agregadas después de la medición vieja, y
que **no cargan el catálogo**): `/api/simular-dia` y `/api/comparar` (1 llamada
c/u, solo si el estudiante las pide desde el dashboard) y `/api/psicometrico`
(1 llamada, ~1,460 tok).

Reproducir: `count_tokens` es gratis y no genera nada; ver
`backend/dump_prompt.py` para volcar el prompt exacto sin llamar a la API.

⚠️ Lo que sigue debajo es la medición **anterior (2026-07-19/21)**, hecha con un
catálogo de 111 filas. Se conserva porque explica *cómo* funciona el caching y de
dónde salieron las decisiones, pero **sus cifras están superadas por la tabla de
arriba**.

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

⚠️ **Actualizado 2026-07-19, tras cargar Rafael Landívar y Universidad de
Occidente en Quetzaltenango** (94 carreras en ese departamento, 111 en total
— antes eran ~69 en todo el catálogo): un flujo completo real (4 adaptativas,
el mínimo de `MIN_ADAPTATIVAS`, entonces en `App.jsx` y hoy en `Chat.jsx`,
+ 1 recomendación), medido con
`count_tokens` contra el backend local filtrando por Quetzaltenango, gasta
**~89,150 tokens** (86,247 prompt + 2,900 output), de los cuales 35,834
fueron cacheados por *implicit caching* (ver abajo). Esto es un salto de
~31% frente a los ~68,100 tokens/sesión documentados antes de esta carga —
casi todo el aumento es el catálogo de carreras (97% del prompt), que ahora
es dept-dependiente:

| Filtro | catálogo `next-question` | catálogo `recommend` |
|---|---|---|
| Solo Totonicapán (17 carreras) | 4,752 tok | 5,645 tok |
| Solo Quetzaltenango (94 carreras) | 15,218 tok | 19,005 tok |
| Ambos / región que las una (111 carreras) | 17,016 tok | 21,615 tok |

Con "Ambos" o una región que incluya Quetzaltenango (ej. Suroccidente), un
flujo completo rondaría los **~96,000-100,000 tokens** — más que el doble de
lo que costaba antes de tener universidades cargadas en Quetzaltenango. Cada
universidad nueva que se agregue ahí (Mesoamericana, Panamericana, Galileo,
Rural, DaVinci pendientes) va a seguir subiendo esto proporcionalmente; vale
la pena volver a medir cuando estén cargadas y evaluar si conviene activar
billing (ver "Estimado de ahorro con caching activo" más abajo).

**Optimización: la IA nunca recibe (ni reescribe) datos de institución.**
`_catalogo_texto` en `recomendar.py` manda solo nombre + banco de palabras de
cada carrera; universidad/centro/departamento/sello los adjunta Python desde
la BD DESPUÉS de la respuesta (`_agrupar`/`_buscar_grupo`), en vez de pedirle
a Gemini que los repita o redacte un 'enfoque' (que era el `sello` ya
guardado, reescrito con tokens). Medido: -23% input y -44% output en
`/recommend`. Se probó blindar el nombre de carrera con un `Literal`/enum en
el schema, pero con ~94 nombres el enum costaba casi lo mismo que se
ahorraba: quedó texto libre + fallback de matching insensible a mayúsculas.

**Optimización: pre-filtro heurístico del catálogo** (`app/filtro.py`,
`TOP_DEFAULT = 35`, ahorro ~53%): documentada aparte en
[filtro-catalogo.md](filtro-catalogo.md).

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

**Por qué el caching EXPLÍCITO no se veía antes del 2026-08-11** (hoy ya está
activo, ver arriba)**:** el tier gratis de Google
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

Medido real (sesión completa, sin billing, filtro Quetzaltenango, 2026-07-19):
de las 5 llamadas (4 `next-question` + 1 `recommend`), 35,834 tokens en total
cachearon (las llamadas `next-question` repetidas comparten prefijo con la
primera); la #1 de cada tipo (nada previo, o system prompt distinto para
`recommend`) no cachea. Con billing y el caching EXPLÍCITO completo se
cubrirían las 5 llamadas (no solo las repetidas) con una ventana garantizada
de 1h en vez de depender de que el tráfico sea seguido.

⚠️ **Actualizado 2026-07-21 — el caching implícito NO se reprodujo en dos
pruebas nuevas, tras cargar UPANA/Galileo/URURAL/Da Vinci** (catálogo
"Ambos" ya con el ciclo Quetzaltenango+Totonicapán cerrado):
- **Flujo secuencial** (3 llamadas reales del chat, `next-question` ×2 +
  `recommend`, mismo prefijo de catálogo): 37,870 tokens, **0 cacheados
  (0%)**.
- **5 llamadas verdaderamente simultáneas** a `/next-question` (lanzadas en
  paralelo con `curl ... & / wait`, mismas respuestas → mismo prefijo
  exacto): 25,680 tokens de prompt (5,136 c/u), **0 cacheados (0%)**, ni
  siquiera entre sí.

Con el filtro de `app/filtro.py` (`TOP_DEFAULT=35`) ya recortando el
catálogo antes de estas llamadas, el prompt quedó en ~5,100 tokens —sigue
por encima del umbral mínimo (~1,024) pero bastante más chico que los
~15,800-18,100 documentados arriba, lo que puede reducir la probabilidad de
que Google decida cachear. **Conclusión: no asumir el ahorro de caching
implícito al presupuestar costos** — es oportunista y, en estas pruebas,
no se activó ni con llamadas simultáneas de prefijo idéntico. Las mediciones
anteriores con `cached_tokens > 0` (sim15-*, 2026-07-19) siguen siendo
válidas como evidencia de que el mecanismo SÍ existe y funciona en tier
gratis, pero no como garantía repetible.

**Estimado de ahorro con caching activo — RECALCULADO 2026-08-02** con las
mediciones vigentes (48,834 tok de prompt + ~2,900 de salida por sesión en
Quetzaltenango; 97% cacheable; caché = 10% del precio de input; $0.25/$1.50 por
1M input/output con `gemini-3.1-flash-lite`):

| Sesiones | Filtro | Sin caché | Con caché | Ahorro |
|---|---|---|---|---|
| 150 | Quetzaltenango | $2.48 | $0.88 | 64% |
| 200 | Quetzaltenango | $3.31 | $1.18 | 64% |
| 150 | Ambos | $2.58 | $0.89 | 65% |
| 200 | Ambos | $3.44 | $1.19 | 65% |

Más ~$1.00/1M tokens/hora de almacenamiento (con ~25k tokens de catálogo ×
2 cachés ≈ $0.05/hora — insignificante).

Sale **más barato** que el estimado viejo ($3.89/$5.18 sin caché) pese a que el
catálogo casi se duplicó: el pre-filtro de `app/filtro.py` recorta las 4 llamadas
de `next-question`, que son la mayoría. El **% de ahorro bajó** (73% → 64%) por la
misma razón: con menos input cacheable, los ~2,900 tokens de salida —que nunca
cachean y se cobran 6× más caros— pesan más en el total.

⚠️ Recalcular al agregar departamentos: solo sube el catálogo de `/recommend`
(que no se pre-filtra), no el de `next-question`.

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
