# Test de Holland (RIASEC) vía O*NET

Pestaña `/holland`. Es el **O*NET Interest Profiler** oficial del Departamento
de Trabajo de EE. UU., en su versión en español ("Mi Próximo Paso"), consumido
con licencia de desarrollador gratuita.

**No se reimplementa el instrumento.** Los 60 ítems, la escala de 5 puntos, el
puntaje RIASEC y el listado de ocupaciones afines los produce la API oficial.
El backend (`backend/app/holland.py`) es un proxy: agrega la API key y traduce
los errores. El navegador no puede llamar a O*NET directo (la key quedaría
expuesta y el servicio no manda CORS).

## Credenciales

Registro gratuito en <https://services.onetcenter.org/developer/signup>: se crea
una organización y un proyecto, y el proyecto genera **una API key** (no hay
usuario ni contraseña; el esquema viejo de Basic Auth ya no aplica). La key va en
el header `X-API-Key` y O*NET no la acepta en la query string. En `backend/.env`:

```
ONET_API_KEY=...
```

Sin ella, `/api/holland/preguntas` responde **503** con ese mismo aviso y el
resto de la app sigue funcionando igual.

La licencia de O*NET exige **acreditar y enlazar** al servicio en cualquier
producto que lo use: por eso la pestaña `/holland` nombra el instrumento y enlaza
a <https://services.onetcenter.org/>.

## Flujo

Se usa la **API v2.0**, cuyo host es `https://api-v2.onetcenter.org/` —
distinto del sitio de documentación (`services.onetcenter.org`), que sigue
sirviendo la v1.9 con usuario/contraseña y responde **401 a la API key**. Ese
detalle costó un rato: el 401 venía de nginx, no de la aplicación. El host real
está en la especificación OpenAPI: <https://services.onetcenter.org/reference/openapi.json>.

| Paso | Endpoint propio | Llamada a O*NET |
|------|-----------------|-----------------|
| Cargar ítems | `GET /api/holland/preguntas` | `/mpp/interestprofiler/questions?start=1&end=60` |
| Calificar | `POST /api/holland` | `/mpp/interestprofiler/results` + `/careers` |

Los dos endpoints de O*NET paginan de 20 en 20 si no se les manda `start`/`end`;
por eso las llamadas piden el rango completo (60 preguntas, hasta 100 ocupaciones).

Dos trampas de la migración v1.9 → v2.0, ya resueltas en el código:

- El filtro por nivel de preparación ahora se llama **`zone`**, no `job_zone`. El
  nombre viejo **no da error**: la API lo ignora y devuelve todas las ocupaciones
  (aparecían baristas y peluqueros en un filtro de carreras universitarias).
- Las áreas ya no traen `area`, sino `code` (en inglés) y `title` (traducido). La
  letra RIASEC se saca del `code`, no de la posición en la lista.

## Qué se le muestra al alumno

O*NET etiqueta cada ocupación como `Best`, `Great` o `Good`. Se muestran los
mejores niveles hasta juntar al menos 10 ocupaciones, con tope de 30: "Best"
sueltas suelen ser dos o tres, y un perfil plano devuelve cientos de "Good" en
orden alfabético que no orientan a nadie. El total sin recortar viaja en
`carreras_total` y la pestaña lo dice.

El frontend arma una cadena de 60 dígitos (1-5, en el orden del índice de cada
pregunta) y la manda como `respuestas`. Se valida en la frontera: 60 caracteres,
todos entre 1 y 5. El código Holland (p. ej. `RSA`) sale de ordenar los seis
puntajes; los empates se rompen con el orden canónico RIASEC, para que el código
no dependa de en qué orden vino la lista.

La pestaña manda `zona: 4` (Job Zone 4 ≈ carrera universitaria). El campo del
endpoint propio se llama `zona` justamente para no confundirlo con el `job_zone`
viejo de la v1.9.

## Límites conocidos

- Las ocupaciones son del mercado laboral de EE. UU. Sirven para ver *tipo* de
  trabajo, no como catálogo de carreras en Guatemala — eso lo da el chat.
- **No alimenta la recomendación.** En el modo 3 su perfil viaja al prompt del
  chat, pero medido no mueve el ranking (ver abajo). Sí se guarda desde el
  2026-08-16 en la tabla `resultados_holland`.
- El banco de preguntas se cachea en memoria (`functools.cache`); un reinicio del
  backend lo vuelve a pedir.

Self-check: `uv run python -m app.holland` (hace llamadas reales si hay credenciales).

## Qué instrumento mide qué (estado al 2026-08-16)

| Instrumento | Mide | Estado |
|---|---|---|
| **Holland / O*NET** (`/holland`) | Intereses (RIASEC) | **En uso.** Oficial, en español, con licencia propia. Es *el* instrumento de intereses del proyecto. |
| **Psicométrico 100 ítems** (`/psicometrico`) | Personalidad + razonamiento lógico/verbal/numérico | En uso, banco propio. Su percentil usa un **baremo ilustrativo**, no una muestra normativa: es la limitación que queda declarada en la tesis. |
| **CIP** (`/cip`) | Intereses | **Retirado del menú** el 2026-08-16. Mide lo mismo que Holland pero sin autorización de uso (lo facilitó una estudiante, no la licenciada) y con baremos españoles de otra época. La ruta y el código siguen vivos para poder mostrarlo; no se le invierte más trabajo. |
| **4 preguntas fijas del chat** | Intereses declarados en conversación | Se quedan. Quitarlas se midió y salió peor: ver [experiments/psicometrico-en-chat.md](../experiments/psicometrico-en-chat.md). |

Holland **no reemplaza** al psicométrico: uno mide intereses y el otro
aptitud/personalidad. Sí reemplaza al CIP, que es el mismo constructo con peor
respaldo legal.

## Los tres modos (implementado el 2026-08-16)

Desde el inicio el alumno elige entre **solo chat**, **solo Holland**, o
**Holland y luego el chat** (modo 3). Cómo viaja el resultado en el modo 3:

```
/holland  → POST /api/holland → O*NET califica
              ├─ se guarda en `resultados_holland` (session_id, hoja, código, áreas)
              └─ frontend/src/holland-perfil.js → localStorage
/chat     → lee localStorage y manda `holland` en /api/next-question y /api/recommend
              └─ el backend valida (HollandRef) y arma el bloque con holland.bloque()
```

- El texto del prompt lo arma **el backend**, no el navegador: lo que llega de
  `localStorage` es dato no confiable. Ver [api.md](api.md).
- Las **4 preguntas fijas se quedan** también en el modo 3.
- El bloque **no entra al pre-filtro** del catálogo.
- "Responderlo de nuevo" borra el perfil guardado, para que el chat no use uno
  viejo mientras el alumno repite el test.
- El chat muestra un chip `Holland ASC` cuando está usando un perfil.

Antes de construirlo se midió el modo 3 en
[experiments/holland-en-chat.md](../experiments/holland-en-chat.md). Lo que quedó
decidido por evidencia:

- **Las 4 preguntas fijas se quedan** también en el modo 3: con ellas el chat usa
  4 preguntas adaptativas en vez de 6, cuesta ~38% menos tokens y mantiene la
  opción "escondida" del alumno en el top-3 (3/3 corridas contra 1/3).
- **El bloque corto de Holland no pesa en la recomendación.** Con el área más
  alta del perfil (39/40) en el prompt, en 5 de 6 corridas el top-1 fue de otra
  área. Un bloque de texto es contexto, no peso: personaliza la conversación,
  pero **no convierte a Holland en motor** — no afirmarlo en la tesis.
- **El recorte del catálogo al sector queda apagado.** Construido con
  solapamiento de palabras contra los títulos de ocupaciones de EE. UU., borra
  las carreras correctas (un perfil A+S devuelve ocupaciones de docencia y
  arrastra el catálogo hacia pedagogía).

## Decisiones abiertas (para retomar)

1. **Si Holland tiene que ser motor, entra como estructura, no como prosa.**
   Codificar el catálogo con los códigos RIASEC que O*NET publica por ocupación y
   ordenar por distancia al código del alumno. Es la ventaja que el CIP no tenía:
   la codificación se ancla a una fuente real en vez de que la invente el modelo.
   Aplica la regla 4 y la lección de
   [cip-en-recomendacion.md](../experiments/cip-en-recomendacion.md): un A/B con
   hojas respondidas por Gemini no prueba la hipótesis (por eso las hojas del
   experimento de Holland se construyen aritméticamente y las califica O*NET).
2. **Persistencia.** Hoy no se guarda nada. Para el modo 3 hace falta que el
   resultado sobreviva al cambio de pestaña (localStorage) y, si entra en la
   investigación, una tabla como `resultados_psicometricos`.
3. **Revisar el psicométrico propio** (pendiente del usuario, 2026-08-16).
