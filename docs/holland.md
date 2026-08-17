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
todos entre 1 y 5. El código Holland (p. ej. `ASE`) se calcula ordenando los seis
puntajes; la letra sale de la **posición** del área, no de su nombre, porque el
endpoint en español las devuelve traducidas.

`job_zone` (2-5) filtra las ocupaciones por nivel de preparación; el frontend
manda 4 ≈ carrera universitaria.

## Límites conocidos

- Las ocupaciones son del mercado laboral de EE. UU. Sirven para ver *tipo* de
  trabajo, no como catálogo de carreras en Guatemala — eso lo da el chat.
- **No alimenta la recomendación** ni se guarda en la base de datos (igual que el
  CIP). Si se va a usar en la investigación, se agrega una tabla como
  `resultados_psicometricos`.
- El banco de preguntas se cachea en memoria (`functools.cache`); un reinicio del
  backend lo vuelve a pedir.

Self-check: `uv run python -m app.holland` (hace llamadas reales si hay credenciales).
