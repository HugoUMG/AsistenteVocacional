# Motor de IA (preguntas adaptativas + recomendación)

Archivos: `backend/app/preguntas.py` (adaptativas), `backend/app/recomendar.py`
(recomendación final y capa común de Gemini), `backend/app/filtro.py` (pre-filtro
sin IA).

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

La IA nunca recibe ni reescribe datos de institución (optimización de tokens):
ver [decisions/gemini-costos-y-caching.md](../decisions/gemini-costos-y-caching.md).
Antes de cada `next-question` el catálogo se recorta con un pre-filtro heurístico:
ver [decisions/filtro-catalogo.md](../decisions/filtro-catalogo.md).

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

**Test corto de personalidad (2026-08-17):** el modo opcional `/personalidad`
mete su resultado como CONTEXTO del prompt (igual que Holland). Se probó
además sembrar la cobertura de personalidad/valores/estilo_cognitivo para
saltarse esas preguntas, y midió peor (el chat terminaba en 1 sola adaptativa
en vez de 4, top-1 distinto en 3/5 perfiles): revertido. Ver
[docs/personalidad.md](personalidad.md) y
[experiments/personalidad-en-chat.md](../experiments/personalidad-en-chat.md).

**Evidencia A/B** (detalle completo en
[experiments/cobertura-dimensiones.md](../experiments/cobertura-dimensiones.md)):
con 15 perfiles "primer botón", el
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
parte: [experiments/microexperiencias.md](../experiments/microexperiencias.md).

Si se retoma: **ítems de elección forzada** entre dos experiencias rivales
("¿prefieres A o B?"), nunca "¿qué tanto te gustaría A?". En las mismas
transcripciones, las preguntas que ya tenían esa forma mantuvieron el perfil
correcto.

⚠️ Aparte, quedó detectado: `preseleccionar()` (`app/filtro.py`) cuenta
solapamiento de palabras **sin entender la negación**, así que una respuesta
como "me desagradaría ver sangre" *sube* el puntaje de las carreras de salud.
Hoy es benigno (el filtro solo recorta a 35 de ~111 y nunca sacó el área
correcta en las pruebas), pero cualquier función de rechazo lo vuelve relevante.
