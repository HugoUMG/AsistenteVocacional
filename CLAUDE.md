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
4. **Preguntas adaptativas** (IA, tipo "Akinator"): Gemini genera cada pregunta
   según lo respondido, para descartar unas carreras y reforzar otras. **Mínimo
   4, máximo 8**, dirigidas por el vector de cobertura de dimensiones (ver abajo);
   termina cuando cubrió las 4 dimensiones prioritarias Y el ranking es claro.
5. **Análisis final** (IA): genera la recomendación y muestra el dashboard.

Costo aprox.: **~5 llamadas a Gemini por test** (mínimo 4 adaptativas + 1 final).
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

## Cobertura garantizada de las 7 dimensiones vocacionales (2026-07-22)

Un perfil vocacional se explora sobre 7 dimensiones: **personalidad, intereses,
habilidades, estilo cognitivo, valores, entorno, motivaciones**. Las preguntas
fijas ya cubren intereses/entorno/motivaciones; las 4 restantes
(personalidad, habilidades, valores, estilo cognitivo) dependían antes de que
Gemini decidiera preguntarlas — lo que no siempre pasaba (inconsistencia entre
alumnos y cortes por debajo del mínimo de preguntas).

**Solución** (en `backend/app/preguntas.py`, + `session_id` pasado desde
`main.py`):
- **Vector de cobertura por sesión** (`_COBERTURA_POR_SESION`, `{dimensión: 0|1}`,
  en memoria del proceso por `session_id`): arranca con las 3 dimensiones de las
  fijas en 1; el backend se lo pasa a Gemini como **estado explícito** en cada
  llamada (no lo infiere del historial).
- **Campo `dimension_objetivo`** en el schema: la IA declara a qué dimensión
  apunta cada pregunta (verificable en logs `[dimension] ...`).
- **Guard de código**: fuerza `terminado=false` mientras queden dimensiones
  prioritarias sin cubrir. Mínimo 4 adaptativas, máximo 8.
- Límite conocido: el vector vive en memoria; se pierde si el backend reinicia a
  mitad de un test (OK para un solo proceso; marcado con comentario `ponytail:`).
- Self-check sin API: `uv run python -m app.preguntas`.

**Evidencia A/B** (detalle completo en
`docs/cobertura-dimensiones-experimento.md`): con 15 perfiles "primer botón", el
cumplimiento del mínimo de 4 preguntas pasó de **40% → 100%**. Con 10 perfiles
**coherentes** (Gemini responde en el papel de una personalidad fija), el top-1
cayó en el área vocacional esperada en **10/10 (nuevo) vs 7/10 (viejo)**, con
mejor calibración de confianza (afinidad promedio del top-1 ~59%→~48%).
⚠️ Evidencia **preliminar**: una corrida por config, y el "estudiante" simulado
es el mismo modelo — falta validación con orientadores humanos a ciegas.

---

## Intento DESCARTADO: preguntas por microexperiencias (2026-07-25)

Se probó y se **revirtió**. Vale leerlo antes de volver a intentarlo, porque la
idea suena bien y falla por una razón que no es obvia.

El cambio (solo prompt, en `SYSTEM` de `preguntas.py`) hacía que las preguntas
adaptativas describieran **experiencias de la jornada laboral** ("¿cómo te
sentirías si tu trabajo fuera resolver problemas con números todos los días?")
en vez de materias, con ~1 de cada 3 en forma de rechazo y opciones graduadas;
más un desempate que le devolvía a la IA su ranking anterior para que preguntara
lo que separara al top.

**Midió peor: 6/10 aciertos vs. 10/10 de la versión actual** (mismos 10 perfiles
coherentes del experimento anterior). Causa: el formato "una experiencia + qué
tanto te gustaría" es **unipolar**, así que invita a la respuesta socialmente
deseable ("¿te gustaría enseñar a otros a cuidar su entorno?" — nadie dice que
no), y en este catálogo ese "sí" empático siempre empuja hacia Trabajo Social y
Pedagogía: 3 de los 4 fallos aterrizaron ahí. El desempate agravó el problema
encerrando las preguntas siguientes en el par ya equivocado.

Detalle completo, transcripciones y el diagnóstico que separa la culpa de cada
parte: `docs/microexperiencias-experimento.md`.

Si se retoma: **ítems de elección forzada** entre dos experiencias rivales
("¿prefieres A o B?"), nunca "¿qué tanto te gustaría A?". En las mismas
transcripciones, las preguntas que ya tenían esa forma mantuvieron el perfil
correcto.

⚠️ Aparte, quedó detectado: `preseleccionar()` (`app/filtro.py`) cuenta
solapamiento de palabras **sin entender la negación**, así que una respuesta
como "me desagradaría ver sangre" *sube* el puntaje de las carreras de salud.
Hoy es benigno (el filtro solo recorta a 35 de ~111 y nunca sacó el área
correcta en las pruebas), pero cualquier función de rechazo lo vuelve relevante.

---

## Examen psicométrico (pestaña aparte, 2026-07-30)

Módulo **independiente del chat vocacional**: sus resultados NO alimentan la
recomendación de carreras ni comparten prompt con ella. Vive en
`/psicometrico` (pestaña "Exámenes psicométricos" del menú).

Un solo examen de **100 ítems en 4 secciones**, paginado de 20 en 20 (la de
personalidad ocupa 2 páginas, las demás 1 cada una):

| Sección | Ítems | Cómo califica |
|---|---|---|
| Personalidad y comportamiento | 1-40 | Likert 1-5 → 6 rasgos (0-100), + índice de consistencia y deseabilidad social |
| Razonamiento lógico | 41-60 | 1 punto por acierto, sin penalización |
| Razonamiento verbal | 61-80 | 1 punto por acierto, sin penalización |
| Razonamiento numérico | 81-100 | Acierto − 0.25 por error (criterio SHL), + precisión (correctas/intentadas) |

Detalles del diseño:
- **El banco de preguntas y la clave de respuestas viven en el backend**
  (`backend/app/psicometrico.py`). `GET /api/psicometrico/preguntas` devuelve
  enunciados y opciones SIN cuál es la correcta, así que no se puede leer la
  clave desde las devtools del navegador.
- **Coherencia del perfil**: 6 pares de ítems del mismo rasgo (4↔12, 25↔29,
  9↔11, 2↔20, 22↔26, 5↔24). Los ítems invertidos se orientan antes de comparar;
  una brecha ≥3 puntos cuenta como divergencia. Ver el techo declarado abajo.
- **Deseabilidad social**: 8 ítems donde "totalmente de acuerdo" es la respuesta
  que queda bien; la alerta exige el máximo en **los 8**.
- **Tendencia central**: responder "Neutral" a todo daba coherencia 100% y los 6
  rasgos clavados en 50 — el patrón más evasivo salía como el más sincero. Ahora
  se marca aparte (`tendencia_central`, alerta a partir de 20 de 40 neutrales).
  No se toca la coherencia: son cosas distintas, y lo que falla ahí no es la
  consistencia sino que el protocolo no informa nada.
- **Los ítems no presuponen empleo previo.** El banco original venía escrito para
  candidatos a un puesto ("mi jefe", "mi vida laboral", "mis logros
  profesionales actuales", "la rutina laboral", "plazos de entrega"): 8 de 40
  ítems, y **la mitad del rasgo de estabilidad**, que un alumno de 13-17 años no
  puede contestar. Reescritos a contexto general/escolar; el self-check tiene un
  regex que falla si vuelve a colarse uno.
- **Precisión vs. velocidad**: se guardan intentadas y segundos por sección, así
  que 10/10 se distingue de 12/20 (con la penalización ambos dan puntaje 10; la
  precisión es lo que los separa — verificado en el self-check). Sin intentos,
  la precisión es `None`, no 0% (un 0% se leería como "falló todas").
- ⚠️ El **baremo es ilustrativo** (tabla de anclas % aciertos → percentil,
  interpolada), NO una muestra normativa real. Marcado con `ponytail:` en el
  código y con una nota visible al pie de los resultados. El ancla del 25% vale
  **percentil 2** porque 25% es el **piso de azar** (4 opciones): adivinar las 60
  preguntas daba antes percentil ~12, que se leía como desempeño real.
- El backend le pasa a la IA la **banda ya calculada** del percentil (muy bajo /
  bajo / medio-bajo / promedio / alto / muy alto) y la conclusión de coherencia
  con el MISMO umbral que usa el badge. Sin esto la IA interpretaba por su
  cuenta y se contradecía con la interfaz (llamó "desempeño promedio" a un
  percentil 25, y "coherente" a un protocolo que la UI marcaba en ámbar).
- Los 40 ítems de personalidad son **obligatorios** en el endpoint. Antes se
  aceptaba un envío parcial y la coherencia salía en "0%" — indistinguible de
  haberse contradicho, pintado en rojo sobre cero datos. Los tiempos que reporta
  el navegador se **recortan a [0, 2h]** (entran al prompt de la IA).
- El `session_id` está topado a 64 chars con el tipo compartido `SessionId` en
  `main.py`, usado por los **cinco** schemas que lo reciben. Sin el tope, uno más
  largo reventaba el `INSERT` (las columnas son `VARCHAR(64)`) y salía como un
  **500 sin manejar** — el hueco existía también en `/next-question`,
  `/recommend`, `/simular-dia` y `/comparar`.
- El avance se guarda en `localStorage` (`psicometrico-borrador`) y se limpia al
  terminar: son 100 ítems, una recarga accidental borraba 25 minutos de trabajo.
  El borrador incluye los **tiempos** (si no, la recarga conservaba las
  respuestas pero reiniciaba el reloj y las secciones ya hechas salían en "0 s"),
  y al cargarlo se **recorta el índice de página** al último válido (un borrador
  viejo apuntando más allá del final dejaba la pantalla en blanco, sin ítems ni
  botones ni forma de salir).
- El **cronómetro arranca en el primer clic**, no al cargar la página: antes,
  dejar la pestaña abierta antes de empezar se le cobraba a la primera sección
  (medido: 38 s de inactividad facturados a personalidad).
- El **guardia del doble envío es un `useRef`**, no el estado `enviando`:
  `setEnviando(true)` no surte efecto hasta el siguiente render, así que tres
  clics rápidos disparaban **tres POST y tres llamadas a Gemini** (verificado:
  3 filas en la BD con el mismo `session_id` y el mismo segundo).
- La escala Likert se responde con **caritas de color** (rojo el 1 → verde el 5),
  no con botones de texto: ver "Identidad visual". La etiqueta larga que manda el
  backend (`Totalmente en desacuerdo`…) viaja en `aria-label`/`title`, así que el
  significado no depende solo del color ni del dibujo; debajo de cada carita va
  una etiqueta corta ("Para nada", "Poco", "Más o menos", "Bastante",
  "Totalmente").
- La escala es un **grid de `repeat(5, minmax(0, 1fr))`**, no flex. Con
  `flex-wrap` se partía en 2+2+1 en móvil y la última opción quedaba del doble de
  ancho; con `1fr` a secas, la columna de la etiqueta más larga crecía unos
  píxeles. En una escala ordinal un botón más grande sesga la elección hacia él.
  Las caritas sí caben las 5 en una fila a 375px (58×75 c/u, medido).

⚠️ **Techo conocido de la coherencia** (auditado con simulación, 2026-07-30): es
un índice de coherencia, **no una escala de sinceridad validada**. El banco de 40
ítems no contiene paráfrasis literales, así que cualquier par puede divergir de
forma legítima en los extremos — medido: los 6 marcan divergencia si se responde
5 en uno y 1 en el otro, aunque sea honesto. Por eso **una** divergencia no
significa nada (deja el índice en 83%, sobre el umbral de 70) y la interfaz ya
no muestra el conteo de contradicciones, solo avisa por debajo del umbral. Los
pares anteriores eran peores: mezclaban constructos distintos (15↔27 comparaba
una *preferencia* con una *capacidad*) y marcaban contradicción siempre. Si
alguna vez se quiere una escala de mentira de verdad, hay que **agregar** ítems
paráfrasis al banco, no recombinar estos.

Otros números de esa auditoría: la alerta de deseabilidad social se disparaba en
el **21%** de alumnos honestos y responsables (umbral de 6 de 8); con el umbral
de 8 de 8 bajó a **0.7%** sobre 300 perfiles simulados.

Fuera de alcance a propósito (es una demo): la tabla `resultados_psicometricos`
guarda solo `session_id`, **no** `estudiante_id`, así que el resultado no se
puede cruzar con la recomendación vocacional. Tampoco hay PDF, historial ni
límite de tiempo duro.
- **Resumen con IA**: 1 sola llamada a Gemini al terminar, que recibe los
  PUNTAJES ya calculados (no las respuestas) → ~1,460 tokens por examen, sin
  catálogo de por medio. Si falla, los puntajes ya quedaron guardados y el
  estudiante los ve igual.
- Se guarda todo en la tabla `resultados_psicometricos` (respuestas crudas +
  puntajes + resumen) y el consumo se registra en `uso_tokens` como endpoint
  `psicometrico`.
- Self-check sin API: `uv run python -m app.psicometrico`.

Dos enunciados se reformularon respecto al borrador original porque eran
ambiguos en opción múltiple: el ítem 56 ("2 es a 4 como 3 es a…") ahora dice
explícitamente "siguiendo la regla de elevar al cuadrado" (si no, 6 también era
válido), y el 59 pregunta "¿qué día será pasado mañana?" (el original decía "el
mañana de pasado mañana", que da sábado, no viernes).

---

## Catálogo cargado (ciclo Quetzaltenango + Totonicapán cerrado, 2026-07-21)

Todas las universidades con sede física en estos dos departamentos ya están
en `backend/data/*.json`. No falta ninguna por agregar — confirmado por
búsqueda: Galileo, Panamericana, Da Vinci y Rural de Guatemala no tienen
sede en Totonicapán (se concentran en Ciudad de Guatemala y Quetzaltenango).

**Quetzaltenango** (9 centros, ~185 carreras): USAC (CUNOC), Universidad
Rafael Landívar (URL Xela), Universidad de Occidente (UdeO), Universidad
Mariano Gálvez (UMG), Universidad Mesoamericana, Universidad Panamericana
(UPANA), Universidad Galileo, Universidad Rural de Guatemala (URURAL),
Universidad Da Vinci de Guatemala.

**Totonicapán** (3 centros, 17 carreras): USAC (CUNTOTO), Universidad
Mariano Gálvez (UMG), Universidad Regional de Guatemala (URG).

Siguiente paso natural: extender el catálogo a otro departamento (fuera del
alcance actual del proyecto, que es Quetzaltenango/Totonicapán/Suroccidente).

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

## Identidad visual

Paleta de marca de Orienta: **azul, azul marino, gris y negro** — sin
violetas, rosas ni verdes decorativos. Los únicos verdes/rojos/naranjas que
quedan son **semánticos**, a propósito, y no se deben "corregir" a azul:
- el badge de confianza alta/media/baja en `Dashboard.css` (código de semáforo);
- la **escala de caritas** del examen psicométrico (`CARITAS` en
  `Psicometrico.jsx`): rojo el 1, naranja el 2, amarillo el 3, lima el 4 y
  verde el 5. El color codifica el nivel de acuerdo, no decora. El color no
  rellena el botón —va en el trazo de la carita, el borde y un tinte al 12%—
  porque texto blanco sobre amarillo o lima no contrasta.

- Variables base en `frontend/src/index.css` (`--navy`, `--navy-2`,
  `--accent`, `--accent-2`, `--text`, `--muted`, `--bg`).
- `frontend/src/colors.js` (`COLORS`) es la paleta compartida para las
  gráficas del dashboard (barras, dona, colores de carrera) y para el PDF —
  12 tonos de azul/navy/gris/negro, sin repetir el mismo color en carreras
  consecutivas.
- `frontend/src/reporte.js` (generación del PDF con `jsPDF`) usa los mismos
  tonos: `ACCENT` = azul (`--accent`), `VERDE` (nombre heredado, ya no es
  verde) = azul marino para los bullets de "por qué encaja", `TEXT`/`MUTED`/
  `LIGHT` = casi negro/gris/gris muy claro. Si se agrega una gráfica o
  elemento nuevo, tomar el color de `COLORS` o de las variables CSS — nunca
  un color fuera de esta familia.

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

⚠️ **Actualizado 2026-07-19, tras cargar Rafael Landívar y Universidad de
Occidente en Quetzaltenango** (94 carreras en ese departamento, 111 en total
— antes eran ~69 en todo el catálogo): un flujo completo real (4 adaptativas,
el mínimo de `MIN_ADAPTATIVAS` en `App.jsx`, + 1 recomendación), medido con
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

**Optimización: pre-filtro heurístico del catálogo (`app/filtro.py`),
`TOP_DEFAULT = 35`.** Antes de cada llamada a `next-question`, un filtro SIN
IA (solapamiento de palabras entre las respuestas acumuladas del estudiante y
el perfil de cada carrera; stdlib puro, sin librerías) recorta el catálogo a
las 35 carreras más afines. Se recalcula en CADA llamada con TODAS las
respuestas (fijas + adaptativas), así que si el perfil cambia de rumbo a
mitad de test, el recorte se ajusta solo. `/recommend` NO se filtra: se llama
una sola vez y ahí prima no excluir una carrera válida del análisis final.

Medido real (6 perfiles de prueba × flujo completo, catálogo Quetzaltenango
de 105 carreras, comparando con/sin filtro en 30, 35 y 40):
- top=30: ahorro ~53%, pero el #1 recomendado divergió en 1 de 6 perfiles.
- **top=35: ahorro ~53% (~45k vs ~96k tokens/sesión), #1 coincidió en 6/6** ←
  elegido.
- top=40: ahorro ~48% y PEOR precisión (4/6) — ampliar no compra calidad,
  la variación restante es ruido propio de la conversación adaptativa
  (temperatura 0.5, preguntas distintas por corrida).
En los 18 pares probados el filtro nunca sacó la recomendación de su área
temática correcta.

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

**Estimado de ahorro con caching activo** (recalculado con los ~89k
tokens/sesión medidos hoy para Quetzaltenango, ~97% catálogo cacheable,
precio de caché = 10% del precio normal de input, ambos con
`gemini-3.1-flash-lite`):

| Sesiones | Sin caché | Con caché | Ahorro |
|---|---|---|---|
| 150 | $3.89 | $1.06 | 73% |
| 200 | $5.18 | $1.42 | 73% |

Más ~$1.00/1M tokens/hora de almacenamiento (con ~19k tokens de catálogo ×
2 cachés ≈ $0.038/hora — insignificante). Con "Ambos"/región o al agregar las
5 universidades pendientes, esta tabla solo va a subir — recalcular cuando
esté completo el catálogo de Quetzaltenango.

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
│   │   ├── preguntas.py    preguntas adaptativas con Gemini
│   │   └── psicometrico.py examen de 100 items: banco, clave y calificacion
│   ├── data/*.json         catalogo de carreras por centro
│   ├── seed_carreras.py    carga data/*.json a la BD (idempotente)
│   └── .env                DATABASE_URL, GEMINI_API_KEY, GEMINI_MODEL (no en git)
├── frontend/               React (Vite)
│   └── src/
│       ├── App.jsx         chat (fijas + adaptativas), fases chat/loading/dashboard
│       ├── Dashboard.jsx   graficas + detalle por carrera/institucion
│       ├── Psicometrico.jsx examen psicometrico (pestaña aparte del chat)
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
| GET | `/api/psicometrico/preguntas` | Banco de 100 ítems, sin la clave de respuestas |
| POST | `/api/psicometrico` | Califica, guarda y devuelve el resumen con IA |

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
