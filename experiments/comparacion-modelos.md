# Comparación de modelo Gemini — medición y descarte

Documento de respaldo para la tesis. Registra una mejora **propuesta** (cambiar
el modelo del orientador por uno más caro), **medida y descartada**: el modelo
en producción se queda igual.

Fecha: 2026-08-17. Ámbito: catálogo completo (202 registros carrera-sede), los
5 perfiles simulados de `experimento_psicometrico.py` (Kevin, Dulce, Brandon,
Melany, Josué), flujo de producción completo (4 fijas + adaptativas +
recomendación).

---

## 1. La pregunta

Con billing activo en el proyecto de Google, ¿vale la pena mover el modelo del
orientador (`GEMINI_MODEL`/`GEMINI_MODEL_FINAL`, hoy `gemini-3.1-flash-lite`) a
uno más caro? Se evaluaron los candidatos disponibles en la API a esa fecha:
`gemini-3.5-flash-lite`, `gemini-3.5-flash`, `gemini-3.6-flash`,
`gemini-3.7-flash` y `gemini-3.1-pro`.

Se descartaron de entrada `3.5/3.6 Flash` completo y `3.1 Pro` sin medirlos:
cuestan 6-10x más que flash-lite ($1.50-$2.00 input / $7.50-$12.00 output por
1M tokens, contra $0.25/$1.50) y la tarea es clasificación estructurada contra
un catálogo acotado, no razonamiento largo — el mismo tipo de gasto que ya se
descartó por rendimientos decrecientes en `cobertura-dimensiones.md` (ahí la
mejora vino del *prompt*, no de más cómputo). Se corrieron solo los dos
candidatos con precio comparable al actual:

| Modelo | Input /1M tok | Output /1M tok | vs. actual |
|---|---|---|---|
| `gemini-3.1-flash-lite` (actual) | $0.25 | $1.50 | 1x |
| `gemini-3.5-flash-lite` | $0.30 | $2.50 | ~1.3-1.7x |
| `gemini-3.7-flash` | $0.75 (precio de lanzamiento, hasta 2026-12-31) | $3.75 | ~3x |

## 2. Metodología

Script: `backend/experimento_modelos.py`. Corre el flujo real de producción
(`preguntas.siguiente_pregunta` + `recomendar.recomendar`, sin reimplementar
nada) para cada perfil, una vez por modelo comparado. El modelo que actúa de
alumno simulado (`_responder`) se deja **fijo en `gemini-3.1-flash-lite` en
todos los brazos**, para que la comparación mida al orientador y no a dos
actores con estilos de respuesta distintos.

Se registró top-1, afinidad, confianza, alertas de contradicción y costo real
(tokens medidos × precio oficial del modelo) por perfil y por modelo.

## 3. `gemini-3.7-flash`: descartado sin datos, por infraestructura

Antes de llegar a resultados, se intentó correr `3.7-flash` (el candidato más
prometedor por su precio de lanzamiento). **4 corridas consecutivas contra el
perfil Kevin fallaron con 503 "model is currently experiencing..."** antes de
completar una sola conversación, la última agotando cuota tanto de la key
primaria como de la de respaldo sin producir una respuesta:

```
[gemini] key primaria agoto cuota (429), reintentando con GEMINI_API_KEY_RESPALDO — model=gemini-3.7-flash
[gemini] RemoteProtocolError al enviar, reintentando (1/4)
[gemini] ConnectTimeout al enviar, reintentando (2/4)
[gemini] RemoteProtocolError al enviar, reintentando (3/4)
ABORTADO (ServerError: 503 UNAVAILABLE...)
```

Se confirmó que el nombre del modelo es correcto (aparece en
`client.models.list()`), así que no es un error de configuración: es
sobrecarga real del lado de Google en un modelo recién lanzado (14-ago-2026,
3 días antes de esta medición). Se decidió sacarlo de la comparación en vez de
seguir quemando cuota de los dos proyectos en reintentos sin garantía. Queda
pendiente si se quiere reintentar más adelante (ver sección 6).

## 4. Resultados: `3.5-flash-lite` vs. actual

5 perfiles completos, 2 modelos, 10 conversaciones reales. Costo total medido:
**$0.2222** (Kevin $0.0465 en la corrida de prueba inicial + $0.1757 en los 4
restantes).

| Perfil | actual (3.1 Flash-Lite) | 3.5 Flash-Lite | ¿Cambió el top-1? |
|---|---|---|---|
| Kevin | Ing. en Ciencias y Sistemas, 25% afin., 90% conf. | mismo, 32% afin., 90% conf. | No |
| Brandon | Téc. Univ. en Desarrollo de Software, 40% afin., 65% conf. | mismo, 35% afin., 55% conf. | No |
| Melany | Contaduría Pública y Auditoría, 45% afin., 90% conf. | mismo, 38% afin., 88% conf. | No |
| Dulce | Trabajo Social, 45% afin., 85% conf. | **Licenciatura en Enfermería**, 32% afin., 82% conf. | **Sí** |
| Josué | Ingeniería en Agronomía, 45% afin., 90% conf. | **Ingeniería Mecánica**, 32% afin., 88% conf. | **Sí** |

**2 de 5 top-1 cambiaron.** Costo por sesión completa (4 fijas + 4 adaptativas
+ recomendación): $0.018-0.021 con el modelo actual, $0.023-0.028 con
3.5-flash-lite (+25% a +40%).

## 5. Diagnóstico: en los dos casos que cambiaron, el modelo más caro leyó peor

Dulce y Josué son, en `experimento_psicometrico.py`, los dos perfiles
diseñados con un **guion familiar que tapa a propósito lo que la persona
realmente quiere** (Dulce: la casa espera enfermería, ella se delata hablando
de arte y diseño; Josué: le da pena el campo y se presenta como "ingeniería",
pero se suelta hablando de la milpa y los suelos).

Con el modelo actual, el top-1 en ambos casos fue una lectura razonable de la
señal indirecta (Trabajo Social para Dulce, Agronomía para Josué: ambas
cercanas a lo que el perfil realmente revela). Con `3.5-flash-lite`, el top-1
se fue a la lectura **literal del guion de la casa** (Enfermería, Mecánica):
justo lo que estos dos perfiles están construidos para que un buen orientador
NO tome al pie de la letra.

No hay evidencia de que el modelo más caro leyó mejor en ningún caso: en los 3
perfiles donde no cambió nada, tampoco hubo mejora de afinidad o confianza
(de hecho bajó ligeramente en Brandon y Melany). El patrón, con 5 perfiles, es
"igual o peor a más precio", no "mejor a más precio".

## 6. Decisión

Se **mantiene** `gemini-3.1-flash-lite` como modelo de producción. Ningún
candidato probado justificó el costo adicional:

- `3.5-flash-lite`: medido, no mejora el ranking, cuesta 25-40% más, y en los
  2 casos que sí cambió algo, leyó peor la señal indirecta que el proyecto
  viene optimizando desde `cobertura-dimensiones.md`.
- `3.7-flash`: no se pudo medir, infraestructura de Google no lo sirvió de
  forma confiable el 17-ago-2026.
- `3.5/3.6 Flash` completo y `3.1 Pro`: descartados sin medir por precio (6-10x)
  sin razón para esperar mejora en una tarea de clasificación estructurada.

## 7. Qué haría falta para reabrir esto

1. **Reintentar `3.7-flash`** más adelante (su ventana de precio de lanzamiento
   dura hasta 2026-12-31): si la sobrecarga de agosto era temporal, vale la
   pena una corrida limpia con los mismos 5 perfiles antes de esa fecha.
2. Si se repite el experimento, **medir latencia**, no solo ranking y costo:
   este experimento no la midió y es un factor real para la experiencia del
   alumno en el chat.
3. Como con el resto de intentos en `experiments/`: si algún modelo nuevo
   mejora el ranking, medirlo con más de 5 perfiles antes de aceptarlo — 5 no
   dan potencia estadística, solo permiten leer el patrón.

## 8. Limitaciones

1. **5 perfiles ficticios, una corrida por modelo** (temperatura 0.5 en el
   orientador): no hay potencia estadística, solo lectura de patrón, igual que
   en el resto de `experiments/`.
2. **El "alumno" simulado es el mismo modelo en los tres brazos** (fijo en
   3.1 Flash-Lite) a propósito, para no confundir "el orientador razona
   distinto" con "el actor responde distinto" — pero sigue siendo circular:
   quien responde y quien recomienda comparten arquitectura de modelo.
3. `3.7-flash` no se pudo evaluar por un problema de infraestructura ajeno al
   diseño del experimento, no por descarte metodológico.
4. Precios de `3.5-flash-lite` y `3.7-flash` tomados de fuentes de terceros
   (búsqueda web, 2026-08-17), no de una factura real como el de flash-lite en
   `decisions/gemini-costos-y-caching.md`.

## 9. Reproducibilidad

- Script versionado: `backend/experimento_modelos.py` (`--self-check` sin red,
  `--perfil <nombre>` para un caso, sin argumentos para los 5).
- Resultados completos (transcripciones, tokens, costo por llamada):
  `backend/data/tests/experimento_modelos_resultados.json` (no versionado,
  igual que los demás `experimento_*_resultados.json`).
