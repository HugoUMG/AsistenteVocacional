# Examen psicométrico (pestaña aparte, 2026-07-30)

Módulo **independiente del chat vocacional**: sus resultados NO alimentan la
recomendación de carreras ni comparten prompt con ella. Vive en
`/psicometrico` (pestaña "Exámenes psicométricos" del menú).
Backend: `backend/app/psicometrico.py`. Frontend: `frontend/src/Psicometrico.jsx`.

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
  no con botones de texto: ver [frontend-y-diseno.md](frontend-y-diseno.md). La
  etiqueta larga que manda el
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
