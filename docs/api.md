# API

Endpoints del backend (`backend/app/main.py`). Documentación interactiva en
http://localhost:8000/docs mientras corre el backend.

| Método | Ruta | Llama a Gemini | Qué hace |
|--------|------|---|----------|
| GET | `/health` | no | Estado del backend |
| GET | `/api/departamentos` | no | Departamentos con catálogo cargado (para el filtro) |
| GET | `/api/carreras` | no | Catálogo completo para la página pública "Catálogo de carreras" |
| POST | `/api/register` | no | Crea estudiante (rechaza nombres con groserías) |
| POST | `/api/submit-survey` | no | Guarda las respuestas |
| POST | `/api/next-question` | **sí** | Siguiente pregunta adaptativa (filtra por departamento + pre-filtro de 35) |
| POST | `/api/recommend` | **sí** | Recomienda carreras agrupadas con % (filtra por departamento, sin pre-filtro) |
| POST | `/api/simular-dia` | **sí** | "Un día siendo…": 5-7 eventos con hora + cierre, on-demand desde el dashboard |
| POST | `/api/comparar` | **sí** | Compara dos carreras del resultado, on-demand |
| POST | `/api/admin/juicio` | no | Calificación del profesional sobre una evaluación (204, solo `ADMIN_EMAILS`) |
| POST | `/api/tts` | no | Audio de un texto con `edge-tts` (voz `es-MX-DaliaNeural`), en streaming |
| GET | `/api/psicometrico/preguntas` | no | Banco de 100 ítems, sin la clave de respuestas |
| POST | `/api/psicometrico` | **sí** | Califica, guarda y devuelve el resumen con IA |
| GET | `/api/holland/preguntas` | no | Los 60 ítems del Interest Profiler, servidos por O*NET |
| POST | `/api/holland` | no | Puntajes RIASEC + ocupaciones (los calcula O*NET) y guarda el resultado |
| GET | `/api/holland/mio` | no | Último perfil de Holland guardado del alumno logueado (o `null`) |
| GET | `/api/uso-tokens` | no | Consumo de tokens de Gemini por sesión |

## Sesión obligatoria y límites de uso

Todo endpoint donde el alumno **se evalúa** exige `Authorization: Bearer <jwt>`
y responde **401** sin él: `/api/register`, `/api/submit-survey`,
`/api/next-question`, `/api/recommend`, `/api/simular-dia`, `/api/comparar`,
`/api/psicometrico`, `/api/cip`, `/api/personalidad`, `/api/holland`,
`/api/holland/mio`, `/api/historial*`. Los bancos de preguntas, el catálogo y
`/health` siguen abiertos. El JWT lo emite `/api/auth/google` (ver
`backend/app/auth.py`).

**Solo en local**, con `LOGIN_OPCIONAL=1` en `backend/.env`, esos endpoints
dejan de pedir sesión y caen a un alumno de prueba (`dev@local`), para no tener
que loguearse en cada prueba de un detalle del chat. El frontend tiene el botón
equivalente ("Entrar sin sesión") solo en `npm run dev`. En Render la variable
no se define y manda el default: 401. El bypass **no abre `/api/admin/*`**, el
alumno de prueba no está en `ADMIN_EMAILS`.

Encima del login, `backend/app/cuota.py` pone dos límites, ambos **429**:

- **Tope por alumno** (`MAX_CHATS_DIARIOS`, 3 por defecto): chats **terminados**
  (con recomendación entregada) que una misma cuenta puede acumular en una
  ventana deslizante de 24 horas. Deslizante y no día calendario, así nadie
  espera al cambio de fecha ni junta seis a caballo de la medianoche. Los chats
  a medias no gastan cupo: a quien se le cayó la conexión no se le cobra el
  intento. La respuesta trae `Retry-After` y dice cuándo se libera el siguiente.
  **Solo se limita el chat**, que es lo único que gasta Gemini: `/api/holland`
  no tiene tope, ni siquiera depende del presupuesto global, porque lo califica
  O*NET y no cuesta nada.
- **Tope global diario** (`TOPE_TOKENS_DIARIO`): suma de `uso_tokens` del día
  UTC. Es el freno de emergencia del crédito de Gemini; el login por sí solo no
  lo protege, crear una cuenta de Google es gratis.

El **503** queda reservado para "el servidor no está configurado" (falta
`GEMINI_API_KEY`), que es lo que el frontend distingue del 429.

`/api/simular-dia` y `/api/comparar` (`backend/app/extras.py`) reciben del
frontend el contexto ya calculado por `/api/recommend` (descripción, razones), así
que **no cargan el catálogo** ni dependen de nombres exactos en la BD: 1 llamada
a Gemini cada una, solo si el estudiante las pide.

## Sugerencia de diversificado (alumnos de básicos)

Cuando `respuestas.nivel == "Básico"`, `POST /api/recommend` agrega
`diversificados`: hasta 3 carreras de nivel medio que preparan para las carreras
que le salieron, con una frase de por qué. Sale de `data/diversificados.json`
cruzando nombres, sin llamar a Gemini y sin gastar tokens. Para el resto de
niveles llega vacío. `GET /api/historial` lo recalcula para las evaluaciones ya
guardadas, así que no depende de que se haya guardado.

## Registro de administración

`GET /api/admin/respuestas?limite=500` devuelve, de la más reciente a la más
antigua, cada evaluación con lo que el alumno contestó en las preguntas fijas
(nombre, edad, nivel, grado, carrera cursada, si le gustó, motivo, departamento),
la carrera que pidió descartar, su top-3 recomendado, si terminó y la
calificación del profesional.

Cada fila trae además el **resultado de Holland** de ese alumno (`holland` con el
código RIASEC, `holland_puntajes` con los seis puntajes y `holland_previo`): el
del mismo recorrido si lo hizo antes del chat y, si no, el más reciente de su
cuenta, marcado como de otro recorrido. Es dato clínico para quien interpreta la
evaluación, no alimenta la recomendación (ver docs/holland.md). Un alumno puede
repetir el test cuantas veces quiera: `holland_total` dice cuántos lleva y el
detalle, `GET /api/admin/respuestas/{id}`, trae el que corresponde en `holland`
y todos los demás en `holland_historial`, del más reciente al más viejo.

`POST /api/admin/juicio` guarda la calificación del profesional sobre una
evaluación: `juicio` (`acerto` | `parcial` | `no_acerto`, o `null` para
descalificarla) y `nota` (comentario libre, hasta 4000 chars). Se guarda en
`respuestas_cuestionario.juicio` y `.juicio_nota`, y sale en el listado, en el
detalle y en el CSV. Es el **criterio externo** de
[estudio-con-estudiantes.md](estudio-con-estudiantes.md) §4 y es la **única**
calificación que existe: el 👍/👎 del alumno se quitó del dashboard, porque él
no puede saber si la recomendación acertó hasta que la evalúe un profesional.

Pide sesión de Google **y** que el correo esté en `ADMIN_EMAILS`
(`backend/.env`); si no, responde 403. Sin la variable no entra nadie. La página
que lo consume es `/admin` y no tiene enlace en el menú a propósito.

## Notas de validación

- El `session_id` está topado a 64 chars con el tipo compartido `SessionId` en
  `main.py`, usado por los **cinco** schemas que lo reciben. Sin el tope, uno más
  largo reventaba el `INSERT` (las columnas son `VARCHAR(64)`) y salía como un
  **500 sin manejar** — el hueco existía también en `/next-question`,
  `/recommend`, `/simular-dia` y `/comparar`.
- `/api/psicometrico` exige los **40 ítems de personalidad**; un envío parcial
  daba coherencia "0%", indistinguible de haberse contradicho. Los tiempos que
  reporta el navegador se recortan a `[0, 2h]` antes de entrar al prompt de la IA.
- `GET /api/psicometrico/preguntas` devuelve enunciados y opciones **sin** la
  clave correcta: no se puede leer desde las devtools del navegador.
- `/api/submit-survey` y `/api/recommend` ignoran el `estudiante_id` del cuerpo
  y usan el de la **sesión**: con login obligatorio, aceptar el id del cliente
  dejaría escribir en la fila de otra cuenta. El campo sigue en el schema porque
  el frontend lo manda.
- `/api/register` rechaza nombres con groserías con una lista curada
  (`PALABRAS_OFENSIVAS`), **duplicada a propósito** en `frontend/src/Chat.jsx`
  para cortar antes de la llamada; el backend es el que manda. Si cambia una,
  hay que cambiar la otra.
- `/api/next-question` y `/api/recommend` aceptan un campo opcional **`holland`**
  (modo 3: el alumno hizo el test antes del chat). Llega desde `localStorage`, o
  sea que es **dato no confiable que termina dentro del prompt**: se valida forma
  y tamaño con el schema `HollandRef` (código de 3 letras RIASEC, exactamente 6
  áreas con puntaje 0-40, hasta 12 títulos de ≤120 chars) y **el texto lo arma el
  backend** con `holland.bloque()`, nunca el navegador. Sin el campo, los dos
  endpoints se comportan exactamente igual que antes.
- El bloque de Holland **no entra al pre-filtro** del catálogo. Recortar el
  catálogo al sector se midió y borra las carreras correctas:
  [experiments/holland-en-chat.md](../experiments/holland-en-chat.md) §3.
- `POST /api/holland` guarda además el perfil completo (`resultados_holland.perfil`)
  tal como lo consume el chat: código, las 6 áreas con nombre y puntaje, y los
  títulos de las 8 ocupaciones. `areas` solo tiene los números, y las ocupaciones
  **sí entran al prompt**, así que sin esa columna recuperar el perfil desde la
  base degradaría el prompt en silencio. `GET /api/holland/mio` lo devuelve, y el
  frontend lo sincroniza al iniciar sesión: el perfil es de la **cuenta**, no del
  `localStorage` de la máquina (dos alumnos en la misma computadora se estaban
  pasando el perfil entre sí).
- ⚠️ `edge-tts` es una **API no oficial** (reversa el "Read Aloud" de Edge):
  puede romperse sin aviso. El frontend cae a `speechSynthesis` si `/api/tts`
  falla — marcado con `ponytail:` en `main.py`.

Ejemplo real del prompt que recibe Gemini en `/api/next-question`:
[prompt-next-question-ejemplo.md](prompt-next-question-ejemplo.md).
