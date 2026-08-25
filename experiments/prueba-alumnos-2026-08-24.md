# Primera prueba de campo con alumnos reales (2026-08-24)

**No es un A/B.** Es una corrida observacional en producción (MiOrienta, Render)
con una clase de quinto bachillerato. No hay brazo de control, así que aquí no
se afirma que ningún cambio mejore o empeore nada: lo que se reporta es lo que
pasó, y dos defectos que la corrida dejó al descubierto.

**Fuente:** export de `/api/admin/respuestas` (lista + detalle de cada
evaluación) y `/api/uso-tokens` de producción. El archivo con nombres y correos
NO entra al repo: son menores de edad (ver `docs/estudio-con-estudiantes.md`).
Aquí solo se citan ids de evaluación.

---

## 1. Qué pasó

| | |
|---|---|
| Ventana | 19:25:52 a 19:38:31 UTC (12 min 39 s) |
| Evaluaciones de alumnos | 18 (17 cuentas, una repitió) |
| Evaluaciones previas tuyas ese día | 8, descartadas del análisis |
| Abandonos (sin recomendación) | **0** |
| Preguntas adaptativas por alumno | 0 (1 caso), 3 (11), 4 (5), 5 (1) |
| Perfil del grupo | 15 de 18 cursan bachillerato en medicina o computación con diplomado en medicina |

La clase entera entró en 13 minutos y **nadie se quedó sin resultado**. Las 18
evaluaciones tienen recomendación guardada. El pool de keys gratis por sesión
aguantó la concurrencia sin cortar a nadie a media conversación, que era el
riesgo principal de la corrida.

Detalle menor pero visible: 3 de 18 escribieron un saludo en el campo del
nombre ("Hola", "Hola soy Yesi", "me llamo Gabriela"), y ese texto se usa tal
cual en el chat y en el dashboard. Un alumno leyó "Hola, Hola". El campo pide un
nombre pero la primera burbuja se siente como un saludo. Se arregla en el texto
de la pregunta, no en el código.

Otro detalle: una alumna contestó "Medicina y enfermeria" a una pregunta de
opción entre analítico y creativo (id 21). El chat no se atoró, siguió con un
enlace genérico. Aguantó bien la respuesta fuera de menú.

---

## 2. Defecto 1: el chat cierra a las 3 adaptativas, no a las 4

`MIN_ADAPTATIVAS = 4` en los dos lados, pero 11 de 18 alumnos contestaron
**3**. La causa es una cuenta mal hecha en `frontend/src/Chat.jsx:634`:

```js
const nAdapt = Object.keys(resp).length - FIJAS.length
```

`resp` arranca en `{ departamento }` (`Chat.jsx:475`) y `departamento` no está
en `FIJAS`, así que `nAdapt` nace en 1 y siempre va uno arriba de la cuenta
real. Con 3 adaptativas contestadas el frontend cree que van 4, corta y ofrece
el resultado. Peor con los grados que descartan carrera: ahí también se agrega
`carrera_descartada` (`Chat.jsx:542` y `:710`), la cuenta va **dos** arriba y el
chat cerraría a las 2. En esta clase no se dio porque nadie contestó que no le
gustaba su carrera, así que el caso de 2 sigue sin verse en campo.

Consecuencia de fondo: las cuatro dimensiones prioritarias
(`personalidad, habilidades, valores, estilo_cognitivo`) necesitan cuatro
preguntas para cubrirse, una cada una. Con tres, **una dimensión prioritaria se
queda sin cubrir siempre**. Eso es justo lo que
[cobertura-dimensiones.md](cobertura-dimensiones.md) midió como 40% a 100% de
cumplimiento: el backend sigue haciendo su parte (devuelve `terminado: false` y
genera la cuarta pregunta), pero el frontend ya no la muestra.

Efecto secundario en costo: esa cuarta pregunta **se genera y se paga**, y se
tira si el alumno elige ver el resultado. Es una llamada a `next-question` por
sesión, alrededor del 20% del gasto de ese endpoint.

Arreglo, una línea:

```js
const EXTRAS = new Set([...CLAVES_FIJAS, 'departamento', 'carrera_descartada'])
const nAdapt = Object.keys(resp).filter((k) => !EXTRAS.has(k)).length
```

---

## 3. Defecto 2: repetir la prueba sin "Empezar de nuevo" deja el chat en cero

La evaluación **id 20** tiene recomendación (Médico y Cirujano, 45% de
afinidad) y **cero preguntas adaptativas**. Solo las fijas.

Es la misma alumna de la **id 16**, dos minutos antes. Las dos evaluaciones
traen `holland.mismo_recorrido: true` contra el mismo test de las 19:23:18, o
sea que **corrieron bajo el mismo `session_id`**. Cambió de departamento
(Quetzaltenango la primera, "Ambos" la segunda), así que volvió al mapa y entró
otra vez al chat.

`_COBERTURA_POR_SESION` en `backend/app/preguntas.py:151` es un diccionario en
memoria del proceso, indexado por `session_id`, y nadie lo limpia al empezar
otra prueba. En la segunda corrida ya estaba lleno de la primera: `pendientes`
salió vacío, el modelo cerró con `terminado: true` en la primera llamada y el
frontend saltó directo al resultado.

`nuevaSesion()` existe y arregla justo esto, pero solo se llama desde el botón
del dashboard (`Chat.jsx:784`). Cualquier otro camino de vuelta al chat (el
menú, el botón atrás, volver a elegir departamento en el mapa) reusa la sesión.

Dos arreglos posibles, de menor a mayor:

1. Llamar `nuevaSesion()` al montar el chat cuando no hay respuestas todavía.
2. En el backend, borrar la cobertura de la sesión cuando llega un
   `next-question` sin ninguna respuesta adaptativa. Cierra el hueco aunque el
   frontend se equivoque, y también cubre el reinicio del proceso en Render.

El (2) es el que aguanta solo. El comentario `ponytail:` de esa línea ya avisaba
del techo, pero por el lado de "se pierde al reiniciar el backend"; el que
mordió fue el contrario, que **no se pierde cuando debería**.

---

## 4. Calidad: el instrumento no separa dentro de un grupo homogéneo

Top-1 de los 18:

| Carrera | Top-1 | En el top-3 |
|---|---|---|
| Licenciatura en Enfermería | 8 | 13 |
| Médico y Cirujano | 3 | 4 |
| Fisioterapia | 2 | 5 |
| Psicología (PEM y Licenciatura) | 2 | 4 |
| Nutrición | 1 | 5 |
| Química Biológica | 1 | 1 |
| Arquitectura | 1 | 1 |

16 de 18 top-1 caen en salud. Con una clase donde 15 de 18 ya cursan
bachillerato en medicina eso no sorprende por sí solo, pero hay dos cosas que sí
piden atención:

**Enfermería aparece en 13 de 18 top-3.** Coincide con lo que ya había anotado
[filtro-catalogo-ab.md](filtro-catalogo-ab.md): Enfermería sale top-1 incluso
con 0 de 5 de presencia en las candidatas del pre-filtro. Con 18 alumnos reales
el patrón se sostiene. Vale medir si el prompt de `recomendar.py` la trata como
respuesta por defecto del área de salud.

**Y el bachillerato pesa más de lo que debería.** El caso limpio es la **id 13**:
impacto "trabajar con la naturaleza", entorno "al aire libre, en el campo",
gustos solo "animales y su cuidado", Holland AIR, y las tres adaptativas
apuntando a lo mismo. El top-1 fue Enfermería, con esta razón textual:

> "Tu bachillerato en medicina te dio una base ideal"

Enfermería Veterinaria quedó de segunda. Todas las señales declaradas apuntaban
a animales y el modelo las pasó por encima con la carrera cursada.
[edad-y-grado.md](edad-y-grado.md) decidió NO meter `carrera_cursada` al prompt
(flag `EDAD_Y_GRADO_EN_RECOMENDACION` apagado), pero el dato viaja igual dentro
de `_historial(respuestas)`, así que el modelo lo lee de todos modos. La
decisión de no usarlo nunca llegó a aplicarse de verdad.

Contrapeso honesto, y por eso esto es una hipótesis y no una conclusión: el
sistema **sí** se sale del molde cuando la señal es fuerte. La **id 25** cursa
medicina, contestó que le gustó "más o menos", y salió con Arquitectura,
Ingeniería Mecánica y Chef. La **id 17** salió con Química Biológica. Con 4 o 5
adaptativas los resultados se ven más finos que con 3, aunque con n=6 eso no se
puede afirmar.

Esto es exactamente la pregunta de
[adaptativas-desempate.md](adaptativas-desempate.md), que sigue sin ejecutar:
¿las adaptativas sirven para elegir DENTRO del área? La corrida sugiere que con
tres preguntas no alcanza, pero **el defecto 1 contamina la evidencia**: nadie
recibió el instrumento completo. Hay que arreglarlo y volver a medir.

**Ninguna de las 18 tiene juicio de la psicóloga todavía.** Sin ese criterio
externo esto describe el comportamiento del sistema, no su acierto.

---

## 5. Costo

De `/api/uso-tokens` (acumulado de producción, 27 sesiones, incluye tus 8
pruebas previas):

| | |
|---|---|
| Tokens totales | 1,718,569 (63,651 por sesión) |
| Llamadas | 122 `next-question`, 27 `recommend`, 1 `simular-dia` |
| Costo si todo se facturara | $0.4097 ($0.0152 por sesión) |
| Prompt cacheado | 28.7% |

El 28.7% está muy abajo del 92.6% documentado. 8 de las 27 sesiones traen
`cached_tokens = 0` y son las que atendió el pool de keys gratis:
`caches.create` solo corre en el proyecto con billing. No es una falla, es el
precio del pool, pero el costo por alumno de la tesis se calculó con el caché
prendido y conviene decirlo así.

Las dos cotas de siempre: `uso_tokens` no registra el alquiler del caché, así
que $0.4097 se queda corto por ese lado; y lo que corrió en keys gratis no se
factura, así que por el otro lado sobra. La cifra defendible sigue siendo la de
[cache-compartido.md](cache-compartido.md).

---

## 6. Pendientes

1. Arreglar el conteo de adaptativas y la cobertura por sesión (secciones 2 y 3).
2. Que la psicóloga califique las 18 desde `/admin`. Sin eso no hay acierto medido.
3. Con el instrumento completo, repetir la corrida y ahí sí atacar
   [adaptativas-desempate.md](adaptativas-desempate.md).
4. Decidir si `carrera_cursada` debe seguir entrando al historial que ve el modelo.
