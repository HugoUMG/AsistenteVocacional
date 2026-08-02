# Decisión: pre-filtro heurístico del catálogo antes de cada pregunta adaptativa

**Fecha:** 2026-07 (vigente). **Archivo:** `backend/app/filtro.py`, `TOP_DEFAULT = 35`.

## Motivo

El catálogo es el 97% del prompt de cada llamada a Gemini. Recortarlo antes de
`next-question` es el ahorro más grande disponible sin tocar el modelo.

**Cómo funciona:** antes de cada llamada a `next-question`, un filtro SIN
IA (solapamiento de palabras entre las respuestas acumuladas del estudiante y
el perfil de cada carrera; stdlib puro, sin librerías) recorta el catálogo a
las 35 carreras más afines. Se recalcula en CADA llamada con TODAS las
respuestas (fijas + adaptativas), así que si el perfil cambia de rumbo a
mitad de test, el recorte se ajusta solo. `/recommend` NO se filtra: se llama
una sola vez y ahí prima no excluir una carrera válida del análisis final.

## Alternativas descartadas (medidas)

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

También se descartó **filtrar `/recommend`**: se llama una sola vez por test, así
que el ahorro es marginal frente al riesgo de excluir la carrera correcta del
análisis final.

## Consecuencias técnicas

- **Medido con `count_tokens` el 2026-08-02** (catálogo actual de 202 filas): el
  catálogo de `next-question` queda en **4,376 tok** (Quetzaltenango) / **4,559
  tok** ("Ambos") frente a 23,321 / 25,119 sin filtro. En una sesión mínima
  (4 adaptativas + 1 recomendación) eso es **48,834 vs 124,614 tokens de prompt:
  61% de ahorro** (62% con "Ambos"). El ahorro subió respecto al ~53% medido en
  su momento, porque el catálogo creció y el recorte no.
- ⚠️ **El recorte es de 35 filas, no de 35 carreras distintas**: tras deduplicar
  por `perfil_grupo`, la IA ve **16 bloques** en Quetzaltenango y en "Ambos". Es
  decir, el abanico real de carreras que puede considerar en cada pregunta
  adaptativa es la mitad de lo que sugiere el nombre `TOP_DEFAULT = 35`. Con esto
  el #1 coincidió 6/6 en las pruebas, así que hoy no es un problema — pero si se
  vuelve a tocar el filtro, el número que importa es el de **bloques**, no el de
  filas. En Totonicapán (17 filas) el filtro no recorta nada.
- Efecto secundario: el prompt quedó bastante por debajo de los ~15,800-18,100
  tokens previos, lo que puede reducir la probabilidad de que Google active el
  *implicit caching* (ver
  [gemini-costos-y-caching.md](gemini-costos-y-caching.md)).
- ⚠️ **Límite conocido:** `preseleccionar()` cuenta solapamiento de palabras **sin
  entender la negación**, así que una respuesta como "me desagradaría ver sangre"
  *sube* el puntaje de las carreras de salud. Hoy es benigno (el filtro solo
  recorta a 35 de ~111 y nunca sacó el área correcta en las pruebas), pero
  cualquier función de rechazo lo vuelve relevante — fue una de las causas del
  fracaso del intento de microexperiencias
  ([experiments/microexperiencias.md](../experiments/microexperiencias.md)).
