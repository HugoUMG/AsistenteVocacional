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

**Antes de aplicar B hay que confirmarlo sobre una ventana limpia**, o sea solo
sesiones posteriores al arreglo:

```bash
cd backend && DATABASE_URL="...neon..." uv run python gasto_24h.py 48
```

Si da ~95% parejo, B es seguro. Si sigue dentado, hay otra causa y B
cuadruplica el costo en vez de bajarlo.

## 7. Pendientes

- El alquiler es **estimado a precio de lista**, asumiendo que Google cobra el
  TTL completo. Nunca se ha visto un SKU de almacenamiento en la factura, y la
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
