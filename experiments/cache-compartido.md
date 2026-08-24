# El pre-filtro rompe el caching explícito (2026-08-23)

**Estado: MEDIDO, no aplicado.** El cambio depende de un bloqueante de
producción (ver §6). Script: `backend/experimento_cache_compartido.py`.

---

## 1. De dónde salió

Revisando por qué las sesiones de Neon cuestan entre $0.0035 y $0.0185 cuando
la proyección era $0.0059 parejo, apareció esto: el caché de `recomendar.py` se
indexa por `sha256(system + catálogo)` (`_clave_cache`), y el catálogo que ve
`next-question` sale de `filtro.preseleccionar`, que puntúa contra **todas** las
respuestas acumuladas. Cada respuesta nueva reordena el top-35, el texto cambia,
el hash cambia.

Medido **sin gastar API**, Quetzaltenango, 185 carreras:

```
llamada 1: hash 4bdc86e001eb  (19,360 chars)  <- CACHE NUEVO
llamada 2: hash 6edd2bdb51d2  (17,060 chars)  <- CACHE NUEVO
llamada 3: hash b8afc290e35f  (18,207 chars)  <- CACHE NUEVO
llamada 4: hash f58342cc808e  (23,752 chars)  <- CACHE NUEVO
llamada 5: hash e6c586bf03f4  (21,157 chars)  <- CACHE NUEVO

caches distintos en una sola sesion: 5 de 5
```

Esta parte es **determinista**: son hashes de texto, no salidas del modelo. No
necesita brazo de control.

Por departamento:

| Departamento | Carreras | Pre-filtro | Cachés en 5 llamadas | Catálogo de `recommend` |
|---|---|---|---|---|
| Quetzaltenango | 185 | RECORTA | **5** | 110,975 chars |
| Totonicapán | 17 | NO recorta (17 < 35) | **1** | 22,439 chars |
| Ambos | 202 | RECORTA | **5** | 119,347 chars |

Totonicapán ya hace por accidente lo correcto: como no hay nada que recortar, el
catálogo no cambia entre llamadas y la sesión entera reusa un caché.

## 2. Por qué eso cuesta dinero

No hay "primera llamada cara": eso es caching **implícito**. Con el
**explícito** de `caches.create`, el cobro es otro:

- `caches.create` **no** cobra los tokens de entrada.
- Cada request que usa el caché paga sus tokens a **$0.025 / 1M** en vez de $0.25.
- Y encima se paga **alquiler: $1 por 1M tokens almacenados por hora**, con el
  TTL de 1h que fija `_get_cache`.

Entonces un hash que no se repite es **una renta de una hora que no se
amortiza**, y con el pre-filtro hay una renta por alumno y por llamada.

## 3. Los brazos

Los dos corren la fase de chat con los mismos tres perfiles (Ana, Diego, Karla),
Quetzaltenango, 3 llamadas por perfil.

- **A (control)** — producción de hoy: `next-question` ve el top-35 del filtro,
  recalculado tras cada respuesta.
- **B** — `next-question` ve el catálogo completo del departamento, idéntico en
  todas las llamadas y **entre todos los alumnos**.

Respuestas enlatadas (siempre la primera opción que ofrece el modelo). El caché
depende del catálogo, no de qué tan realista conteste el alumno, así que no hace
falta el alumno simulado por Gemini de `experimento_filtro.py`, que duplica el
gasto.

**La calidad no se vuelve a juzgar aquí.** Esa misma comparación ya está medida
en [filtro-catalogo-ab.md](filtro-catalogo-ab.md): 13/16 vs 12/16, empate dentro
de un piso de ruido de 3/8.

## 4. Resultado

| | A (con filtro) | B (completo compartido) |
|---|---|---|
| Llamadas | 9 | 9 |
| Prompt | 53,975 | 226,188 |
| Cacheado | 51,058 (94.6%) | 223,263 (98.7%) |
| Salida | 3,207 | 3,293 |
| **Cachés distintos** | **9** | **1** |
| Costo de tokens | $0.0068 | $0.0113 |
| Alquiler estimado | $0.0511 | $0.0248 |
| **TOTAL** | **$0.0579** | **$0.0361** |

**B cuesta el 62% de A: 38% de ahorro con solo 3 alumnos.** Gasto real de la
corrida completa: $0.0181 en tokens (los 10 cachés se borraron al terminar).

Ojo con la lectura fácil: el "% cacheado" **no distingue los brazos** (94.6% vs
98.7%). Con caching explícito, un caché recién creado ya reporta sus tokens como
cacheados, así que la métrica se ve bien aunque no se reuse nada. **La métrica
que importa es el número de cachés**, no el porcentaje.

## 5. El ahorro crece con el grupo

El alquiler de A escala con los alumnos; el de B es fijo. Por alumno (3
llamadas): A suma ~$0.0193, B suma ~$0.0038 sobre una renta fija de $0.0248.

| Alumnos | A | B | B/A |
|---|---|---|---|
| 1 | $0.019 | $0.029 | 148% (A gana) |
| 3 | $0.058 | $0.036 | 62% |
| 30 | $0.58 | $0.14 | **24%** |

Punto de equilibrio: **~2 alumnos**. Para un estudio con un grupo, B gana
cómodo. Para un alumno suelto y aislado, da igual o pierde un poco.

## 6. Bloqueante: B es una apuesta a que el caché funcione

Si `caches.create` falla, B manda 25k tokens inline por llamada a $0.25/1M en
vez de los 5.7k de A: **B se vuelve ~4x más caro que A**, no más barato.

Y hoy en producción el caché **casi no funciona**. Medido sobre las 7 sesiones
reales de Neon (`backend/gasto_24h.py`):

```
2026-08-24 02:44  5 llamadas  47,791 prompt   92.6% cache  -> $0.0051
2026-08-23 18:51  4 llamadas  42,141 prompt    0.0% cache  -> $0.0134
2026-08-22 23:57  2 llamadas  12,372 prompt   30.6% cache  -> $0.0035
2026-08-22 17:17  7 llamadas  59,522 prompt    6.4% cache  -> $0.0185
2026-08-22 17:10  3 llamadas  38,443 prompt    0.0% cache  -> $0.0120
2026-08-20 07:35  7 llamadas  63,394 prompt   23.9% cache  -> $0.0175
2026-08-20 07:20  6 llamadas  38,683 prompt   49.2% cache  -> $0.0090
Cacheado global: 28.5%
```

La primera lectura fue "producción corre sin billing", porque 28.5% coincide
casi exacto con el **33.4% del caching implícito** medido con la key gratis el
2026-08-12. **Esa lectura era incorrecta.** Verificado el 2026-08-23: la key con
billing es la primaria **en local y en las variables de entorno de Render**
(local comprobado probando `caches.create` con cada key: `GEMINI_API_KEY` crea
cachés, `GEMINI_API_KEY_RESPALDO` falla con 429; Render corroborado por el
autor). Esto corrige lo que dice
[filtro-catalogo-ab.md](filtro-catalogo-ab.md) sobre la key con billing en
respaldo, que quedó viejo.

Lo que explica el número es **la fecha**: la sesión más reciente (08-24 02:44)
da **92.6%**, y las de 0% son todas anteriores. El 28.5% global es un promedio
sobre sesiones de antes del arreglo, no el estado de hoy.

**Confirmado el 2026-08-23 sobre ventana limpia.** El cambio de variable de
entorno en Render entró entre las dos últimas sesiones, y cada una cae del lado
que le toca:

| Sesión | Key | Cacheado |
|---|---|---|
| 08-23 18:51 | gratis (pre-arreglo) | 0.0% |
| 08-24 02:44 | billing (post-arreglo) | **92.6%** |

El 92.6% es casi calcado del **94.6% del brazo A** de §4, que es exactamente lo
que predice el modelo: el caché explícito funciona *y* el pre-filtro sigue
creando uno por llamada. El 25.9% global es un promedio sobre sesiones viejas,
no el estado de hoy.

**El bloqueante del caché queda cerrado.** El que sigue abierto es el alquiler
(§7), y es el que decide si B conviene: n=1 sesión post-arreglo alcanza para
confirmar el mecanismo, no para presupuestar.

## 8. Cada departamento tiene su propio juego de cachés (2026-08-23)

El catálogo viene filtrado por departamento antes de entrar al hash, así que
Quetzaltenango, Totonicapán y "Ambos" nunca comparten caché. Dentro de cada uno
hay dos familias: la de `next-question` (catálogo recortado, cambia por llamada)
y la de `recommend` (catálogo completo, estable y compartido por todos los
alumnos de ese departamento).

Medido con `backend/costo_por_departamento.py`, que no gasta cuota
(`count_tokens` es gratis y los hashes se calculan local):

| Depto | Carreras | Chat por llamada | Recommend | Cachés del 1er alumno | Que agrega el 2do |
|---|---|---|---|---|---|
| Quetzaltenango | 185 | 3,870 tok | 23,330 tok | **5** (4 chat + 1 rec) | **+4** |
| Totonicapán | 17 | 4,752 tok | 4,752 tok | **2** (1 chat + 1 rec) | **+0** |
| Ambos | 202 | 3,793 tok | 25,115 tok | **5** | **+4** |

**Totonicapán es el caso sano y lo es por accidente:** 17 carreras < `TOP_DEFAULT`
= 35, así que `preseleccionar` no recorta nada, el catálogo del chat no cambia
nunca y el segundo alumno entra sin crear un solo caché. Su catálogo por llamada
es incluso MÁS grande que el de Quetzaltenango (4,752 vs 3,870) y aun así gana:
la métrica que manda es el número de cachés, no su tamaño. Es la misma
conclusión de §4 vista desde otro ángulo.

Escenario de 3 alumnos simultáneos, uno por departamento, y luego otros 3
iguales: la primera tanda crea **12 cachés**, la segunda agrega **8**.

### Costo por alumno, y las dos columnas que se contradicen

| Depto | Solo tokens | Con alquiler, 1er alumno | Con alquiler, 2do |
|---|---|---|---|
| Quetzaltenango | $0.0053 | $0.0441 | $0.0208 |
| Totonicapán | $0.0049 | $0.0144 | $0.0049 |
| Ambos | $0.0054 | $0.0456 | $0.0205 |

**En tokens puros el departamento casi no importa** (~$0.005 en los tres): lo que
domina es la salida (~2,900 tok a $1.50/1M), no el catálogo. **Con alquiler,
Totonicapán sale 3x más barato** y la elección pesa muchísimo.

Y aquí está la evidencia que apunta contra el modelo de alquiler: la sesión real
de Neon del 2026-08-24 costó **$0.0051**, que coincide con la columna de solo
tokens ($0.0053), no con la de alquiler ($0.0441). Dos lecturas posibles, y no
se pueden distinguir desde el código:

1. Google **no** cobra el alquiler como el precio de lista, y el costo real es
   ~$0.005 por alumno sin importar el departamento.
2. Sí lo cobra, pero `uso_tokens` no lo ve porque cae en la factura y no en la
   tabla, y el gasto real es ~4x lo que reporta el script.

Para 6 alumnos son $0.032 contra $0.15: da igual. Para 1,000 son **$5 contra
$45**, y ahí decide el presupuesto de la tesis. Resolverlo es un vistazo a
Facturación → Informes agrupando por SKU, y **vale más que cualquier otra
medición pendiente de este experimento**.

## 7. Pendientes

- **(El más importante, ver §8.)** El alquiler es **estimado a precio de lista**,
  asumiendo que Google cobra el TTL completo. Nunca se ha visto un SKU de almacenamiento en la factura, y la
  reconciliación del 2026-08-11 solo encontró ~$0.003 de diferencia, mucho menos
  de lo que este modelo predice. Verificar en Facturación → Informes, agrupando
  por SKU. **Si Google no cobra el alquiler como se modela aquí, el ahorro de B
  se reduce al de tokens, y ahí A gana** ($0.0068 vs $0.0113).
- `_SIN_SENAL` no excluye `nombre` (`filtro.py:35`): el nombre del alumno entra
  al texto que puntúa el filtro. No aporta señal vocacional y ensucia el hash.
  Arreglo de una palabra, sin relación con el A/B.
- Alternativa intermedia sin medir: **congelar** las candidatas tras las 4 fijas
  en vez de quitar el filtro. Baja de 5 cachés a 1 por sesión, pero **no** da
  reuso entre alumnos (los chips son multi-selección sobre 25 opciones, dos
  alumnos casi nunca producen el mismo top-35). Rinde menos que B.
- `backend/flujo_gasto.py` **está roto en la rama
  `produccion-login-obligatorio`**: todos los endpoints exigen login de Google y
  `/api/register` responde 500. Se puede correr con `LOGIN_OPCIONAL=1`.
