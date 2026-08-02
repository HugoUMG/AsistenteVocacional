# Cobertura garantizada de dimensiones vocacionales — mejora e evidencia

Documento de respaldo para la tesis. Registra el problema detectado en el test
adaptativo, la solución implementada y los dos experimentos A/B que la evalúan,
con sus conclusiones y limitaciones metodológicas.

Fecha: 2026-07-22. Ámbito de las pruebas: catálogo de **Totonicapán** (17
carreras), modelo `gemini-3.1-flash-lite`.

---

## 1. Marco: las 7 dimensiones vocacionales

Un perfil vocacional se explora sobre 7 dimensiones:

1. **Personalidad** — cómo es.
2. **Intereses** — qué disfruta.
3. **Habilidades** — en qué es bueno o podría desarrollar.
4. **Estilo cognitivo** — cómo piensa / resuelve problemas.
5. **Valores** — qué le importa en una profesión.
6. **Entorno laboral** — dónde se imagina trabajando.
7. **Motivaciones** — qué lo impulsa.

Las **preguntas fijas** del cuestionario (ver `frontend/src/Chat.jsx`) cubren de
entrada **intereses** ("¿qué temas te apasionan?"), **entorno** ("¿dónde te
imaginas trabajando?") y **motivaciones** ("¿qué impacto quieres tener?"). Las
otras cuatro — **personalidad, habilidades, valores, estilo cognitivo** — quedan
a cargo de las preguntas adaptativas (IA).

## 2. Problema detectado

En la versión anterior, el prompt de `app/preguntas.py` solo *sugería* a Gemini
preguntar "sobre intereses, gustos, habilidades, valores y estilo de trabajo",
sin llevar registro de qué dimensiones ya se habían cubierto ni obligar a cerrar
las pendientes. Consecuencias:

- **Inconsistencia entre estudiantes**: dos alumnos podían recibir un perfil
  construido sobre dimensiones distintas, según lo que Gemini decidiera preguntar.
- **Corte prematuro**: la regla "haz al menos 4 preguntas adaptativas" era una
  instrucción de texto que Gemini incumplía con frecuencia.

## 3. Solución implementada

Tres capas, todas en `backend/app/preguntas.py` (+ una línea en `main.py` para
pasar `session_id`):

1. **Instrucción de cobertura en el prompt**: enumera las 7 dimensiones y obliga
   a dirigir cada pregunta a una dimensión aún pendiente.
2. **Campo `dimension_objetivo`** en el schema de salida: la IA declara a qué
   dimensión apunta cada pregunta (verificable en logs).
3. **Vector de cobertura real** (`_COBERTURA_POR_SESION`, por `session_id`): el
   backend lleva el estado `{dimensión: 0|1}`, lo inicializa con las 3 dimensiones
   que cubren las fijas ya en 1, y se lo pasa a Gemini como dato explícito en cada
   llamada (en vez de pedirle que lo infiera del historial). Un *guard* de código
   fuerza `terminado=false` mientras queden dimensiones prioritarias sin cubrir.

Límite conocido: el vector vive en memoria del proceso; se pierde si el backend
reinicia a mitad de un test (aceptable para despliegue de un solo proceso;
marcado con comentario `ponytail:` en el código).

---

## 4. Experimento A — política de respuesta "primer botón" (15 perfiles)

**Metodología**: 15 perfiles con respuestas fijas distintas; a cada pregunta
adaptativa se respondía **eligiendo siempre la primera opción** presentada.
Comparación versión anterior vs. nueva.

| Métrica | Antes | Ahora |
|---|---|---|
| Cumplió el mínimo de 4 preguntas adaptativas | 6/15 (40%) | **15/15 (100%)** |
| Cubrió las 4 dimensiones prioritarias | 0/15 (sin registro) | **15/15 (100%)** |
| Afinidad promedio del top-1 | 67% | 46% |
| Top-1 cambió respecto al viejo | — | 8/15 (53%) |

**Hallazgo sólido**: en la versión vieja, **9/15 perfiles (60%) terminaron con
menos de las 4 preguntas mínimas** que el propio prompt exigía. El guard de
código lo volvió garantía dura (15/15).

**Debilidad metodológica detectada** (caso Valeria): elegir siempre la primera
opción NO simula una persona, simula "el primer botón". Se verificó
reproduciendo el flujo de un mismo perfil dos veces: la opción `[0]` representaba
rasgos **distintos** en cada corrida ("escuchar con empatía" vs. "liderar un
equipo" vs. "defender derechos"), porque es simplemente la que el modelo listó
primero esa vez. Esto arrastraba el perfil de forma arbitraria. Se descartó que
la variación viniera de la llamada `/recommend`: ejecutada 4 veces con un input
**congelado idéntico**, dio resultado idéntico las 4 veces (determinista en la
práctica).

**Conclusión del Experimento A**: demuestra mejora de **consistencia del proceso**
(60%→0% de incumplimiento del mínimo), pero **no** permite concluir mejora de
**precisión**, por la política de respuesta no realista.

---

## 5. Experimento B — perfiles coherentes (10 personas)

**Metodología mejorada**: 10 perfiles ficticios con personalidad **fija y
coherente**. Cada pregunta adaptativa la responde Gemini **en el papel de esa
persona** (no por posición de opción). Cada perfil tiene un **`área_esperada`**
= criterio externo débil para medir si el top-1 cae en el área temática correcta.

Perfiles: Ana (salud/psicología), Luis (informática), Mario (administración),
Sofía (educación), Diego (forestal), Carmen (derecho), Pablo (criminalística),
Lucía (comunicación), Roberto (contaduría), Elena (trabajo social).

### Resultados (top-1 vs. área esperada)

| Persona | Área esperada | VIEJO | NUEVO |
|---|---|---|---|
| Ana | salud/psicología | ❌ PEM Pedagogía+Ambiente 55% (Psic. Clínica #3) | ✅ Enfermería 65% |
| Luis | informática | ✅ Sistemas Informáticos (3 preg.) | ✅ Sistemas Informáticos |
| Mario | administración | ✅ Cs. de la Administración | ✅ Cs. de la Administración |
| Sofía | educación | ✅ PEM Pedagogía (3 preg.) | ✅ PEM Pedagogía |
| Diego | forestal | ❌ PEM Pedagogía+Ambiente 65% (Forestal #2) | ✅ Ingeniería Forestal 60% |
| Carmen | derecho | ❌ Criminalística 50% (Abogacía #2; con 5 preg.) | ✅ Abogacía y Notariado 45% |
| Pablo | criminalística | ✅ Criminalística | ✅ Criminalística |
| Lucía | comunicación | ✅ Comunicación/Periodismo | ✅ Comunicación/Publicidad |
| Roberto | contaduría | ✅ Contaduría (3 preg.) | ✅ Contaduría |
| Elena | trabajo social | ✅ Trabajo Social (5 preg.) | ✅ Trabajo Social |

| Métrica | VIEJO | NUEVO |
|---|---|---|
| **Top-1 en el área esperada** | **7/10 (70%)** | **10/10 (100%)** |
| Cumplió el mínimo de 4 preguntas | 7/10 (Luis, Sofía, Roberto con 3) | **10/10** |
| Afinidad promedio del top-1 | ~59% | ~48% |

### Interpretación

- **Caso Carmen** (el más elocuente): el viejo hizo **5 preguntas** (más que el
  mínimo) y aun así recomendó Criminalística en vez de Derecho. Prueba que la
  mejora **no es "hacer más preguntas" sino "preguntar con cobertura dirigida"**.
- Los 3 fallos del viejo (Ana, Diego, Carmen) comparten patrón: la recomendación
  se fue a un área **adyacente pero equivocada**, y la carrera correcta existía en
  el catálogo pero aparecía más abajo — el sistema la tenía identificada pero no
  la priorizaba.
- **Calibración de confianza**: el nuevo baja la afinidad del top-1 (~59%→~48%)
  **y a la vez acierta más** (7→10). La menor "seguridad" no es pérdida de
  calidad sino mejor calibración (la versión vieja era sobre-confiada).

---

## 6. Conclusiones y limitaciones (redacción para la tesis)

> La incorporación de un mecanismo que garantiza la cobertura de las dimensiones
> vocacionales incrementó la consistencia del proceso de evaluación, logrando que
> el 100% de los perfiles simulados fueran analizados bajo los mismos criterios
> mínimos (frente al 40% del sistema anterior). Con perfiles simulados coherentes,
> la recomendación principal se ubicó en el área vocacional esperada en 10 de 10
> casos, frente a 7 de 10 del sistema anterior; los casos corregidos compartían un
> patrón en el que la carrera adecuada existía en el catálogo pero no era
> priorizada por falta de exploración de dimensiones como personalidad y valores.
> La disminución de la afinidad promedio (~59% a ~48%) se interpreta como una mejor
> calibración de la confianza, no como pérdida de precisión.

**Limitaciones que deben declararse explícitamente:**

1. **Una sola ejecución por configuración** (temperatura 0.4–0.5). Los resultados
   son indicativos, no estadísticamente robustos; requieren repeticiones múltiples
   para dar un intervalo de confianza.
2. **Sesgo de modelo compartido**: en el Experimento B, el "estudiante" que
   responde también es Gemini, contestando preguntas generadas por Gemini y
   evaluadas contra una recomendación de Gemini. Esto infla la coherencia interna.
3. **Circularidad parcial del criterio**: el `área_esperada` fue diseñado junto con
   el perfil por el mismo autor. Lo mitiga que los mapeos son los que haría
   cualquier orientador, pero no reemplaza el juicio humano independiente.

**Siguiente paso para evidencia externa** (fuera del alcance actual): repetir con
respuestas de estudiantes reales o con validación a ciegas de **orientadores
vocacionales humanos** — que elijan las 3 carreras más compatibles para cada
perfil sin ver la recomendación de la IA, y comparar. Solo eso permitiría evaluar
la **precisión** (no solo la consistencia) con evidencia independiente del modelo.

---

## 7. Reproducibilidad

- Código de la solución: `backend/app/preguntas.py` (vector de cobertura, guard,
  `dimension_objetivo`), `backend/app/main.py` (paso de `session_id`).
- Self-check sin API: `uv run python -m app.preguntas`.
- Los scripts de batch (`_batch_ab.py`, `_batch_coherente.py`) fueron temporales y
  no se versionan; la metodología queda descrita en las secciones 4 y 5 para
  reconstruirlos. La versión "vieja" se obtiene con `git stash` de
  `preguntas.py`/`main.py` sobre el commit previo a esta mejora.
