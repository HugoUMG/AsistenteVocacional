# Preguntas por microexperiencias — intento, medición y descarte

Documento de respaldo para la tesis. Registra una mejora **propuesta,
implementada, medida y revertida**: el resultado negativo y su causa son el
aporte, no un fracaso a esconder.

Fecha: 2026-07-25. Ámbito: catálogo de **Totonicapán** (17 carreras), modelo
`gemini-3.1-flash-lite`, mismos 10 perfiles coherentes del Experimento B de
`cobertura-dimensiones-experimento.md` (para que los resultados sean
comparables).

---

## 1. La hipótesis

Los inventarios vocacionales modernos no preguntan "¿te gusta Medicina?" sino
"¿qué tan agradable te parece atender pacientes?". La premisa: un adolescente
sabe mejor si disfrutaría una **actividad concreta** que si le gusta una
**materia**, y la actividad tiene menos sesgo. Sobre esa base se implementaron
dos cambios, ambos **solo de prompt** (`SYSTEM` en `backend/app/preguntas.py`),
sin tocar el schema, la base de datos ni el frontend:

**Paso 1 — microexperiencias.**
- Prohibido preguntar por materias o gustos abstractos; obligatorio describir la
  jornada real (qué haría, con quién, dónde, cuánto tiempo), incluyendo la parte
  incómoda (turnos de noche, lluvia, papeleo).
- ~1 de cada 3 preguntas en forma de **rechazo** ("¿qué tanto te molestaría…?"),
  bajo la premisa de que el rechazo descarta más rápido que el gusto.
- **Opciones graduadas** en vez de Sí/No ("Me encantaría / Lo haría sin problema
  / Lo aguantaría un rato / No me veo ahí").
- ~22 microexperiencias incluidas como *few-shot de estilo*. Se descartó de
  entrada la variante "banco de 150–250 ítems con pesos por carrera": elegir el
  ítem que más reduce la incertidumbre exige pesos ítem×carrera, es decir un
  modelo psicométrico (IRT o árbol de decisión) que no hay cómo calibrar sin
  datos etiquetados — el mismo motivo por el que el proyecto no entrena una red.

**Paso 2 — desempate por ranking previo.** El ranking que la IA devuelve se le
regresa en la llamada siguiente (`_RANKING_POR_SESION`, mismo patrón en memoria
que el vector de cobertura). Si dos o más carreras están a menos de 10 puntos de
la #1, se le pide una pregunta que las **separe**; si hay líder clara, una que la
**confirme o descarte**.

Costo medido: +385 tokens por llamada a `next-question` (5,136 → 5,521) por el
paso 1, y ~+70 más por el paso 2.

## 2. Metodología

Réplica del Experimento B: 10 perfiles con personalidad fija y coherente (Ana
salud/psicología, Luis informática, Mario administración, Sofía educación, Diego
forestal, Carmen derecho, Pablo criminalística, Lucía comunicación, Roberto
contaduría, Elena trabajo social). Cada pregunta adaptativa la responde Gemini
**en el papel de esa persona**. Criterio de acierto: que el top-1 caiga en el
área vocacional esperada.

Las dos configuraciones se ejecutaron **el mismo día, contra el mismo backend y
el mismo catálogo**, intercambiando únicamente `preguntas.py` (versión nueva vs.
versión en `HEAD`).

**Control de validez del arnés**: la corrida "vieja" reprodujo el **10/10 ya
documentado** para esa versión en `cobertura-dimensiones-experimento.md`. La
diferencia medida no es ruido del montaje experimental.

## 3. Resultados

| Configuración | Top-1 en el área esperada | Preguntas prom. | Afinidad top-1 |
|---|---|---|---|
| **Versión actual** (sin los cambios) | **10/10** | 4.0 | 47% |
| **Con pasos 1+2** | **6/10** | 5.6 | 54% |
| Con pasos 1+2, cortada a 4 preguntas | 8/10 | 4.0 | — |

| Persona | Área esperada | Versión actual | Con pasos 1+2 |
|---|---|---|---|
| Ana | salud/psicología | ✅ Enfermería | ❌ Trabajo Social (Psic. Clínica #2) |
| Luis | informática | ✅ Sistemas Informáticos | ✅ Sistemas Informáticos |
| Mario | administración | ✅ Cs. de la Administración | ✅ Cs. de la Administración |
| Sofía | educación | ✅ PEM Pedagogía | ✅ PEM Pedagogía |
| Diego | forestal | ✅ Ingeniería Forestal | ❌ PEM Pedagogía (Forestal fuera del top-3) |
| Carmen | derecho | ✅ Abogacía y Notariado | ✅ Abogacía y Notariado |
| Pablo | criminalística | ✅ Criminalística | ✅ Criminalística |
| Lucía | comunicación | ✅ Comunicación (Publicidad) | ❌ Trabajo Social (Periodismo #2) |
| Roberto | contaduría | ✅ Contaduría | ❌ Sistemas Informáticos (Contaduría #2) |
| Elena | trabajo social | ✅ Trabajo Social | ✅ Trabajo Social |

La versión nueva quedó además **más segura y menos precisa** (54% vs. 47% de
afinidad promedio del top-1): lo contrario de la mejora de calibración que sí
había traído el mecanismo de cobertura de dimensiones.

## 4. Diagnóstico

### 4.1 La prueba que separa las culpas

Se repitió la llamada `/recommend` de la corrida nueva usando **solo las 4
primeras respuestas adaptativas** de cada transcripción (sin generar preguntas
nuevas: 10 llamadas). Resultado: **8/10**. Recupera a Ana y a Roberto, pero
Diego y Lucía siguen fallando.

Conclusión: **2 de los 4 fallos vienen de alargar la conversación (paso 2) y 2
del estilo de ítem (paso 1)**.

### 4.2 El sesgo de deseabilidad social

**Diego** (forestal) iba con Ingeniería Forestal 95% tras dos preguntas. La
tercera fue: *"¿qué tan cómodo te sentirías explicando y enseñando a otros a
cuidar su entorno?"*. Nadie contesta que no a eso. PEM Pedagogía saltó a 90% y
desplazó a Forestal, que ya no volvió al top.

**Lucía** (comunicación) iba con Periodismo 92%. La cuarta pregunta, de la
dimensión "valores", fue: *"¿qué tan importante sería para ti que tu trabajo
tuviera impacto social directo en personas olvidadas?"*. Ese ítem no discrimina
absolutamente nada: todos responden que sí. Entró Trabajo Social y la quinta
pregunta lo remató.

La causa raíz es el **formato**, no el tema: "una experiencia + qué tanto te
gustaría" es un ítem **unipolar**, y los ítems unipolares sobre conductas
prosociales miden deseabilidad social, no preferencia vocacional. En un catálogo
donde existen carreras genéricas de "ayudar a personas" (Trabajo Social,
Pedagogía), ese sesgo tiene siempre a dónde ir: **3 de los 4 fallos aterrizaron
en esas dos carreras**.

### 4.3 El arrastre del desempate

El paso 2 agrava lo anterior en vez de corregirlo. Una vez que el ranking se
voltea por una respuesta socialmente deseable, el desempate se **encierra en el
par nuevo**: a Diego, de la quinta pregunta en adelante, se le ofreció pedagogía
contra pedagogía. La carrera desplazada no tiene forma de volver.

A esto se suma un **efecto de recencia**: las últimas respuestas pesan
desproporcionadamente en el `/recommend` final, así que alargar la conversación
amplifica cualquier deriva tardía.

## 5. Decisión

Se **revirtió** `preguntas.py` a la versión anterior. Se prioriza la consistencia
y el uso correcto de los perfiles por encima de la riqueza conversacional.

## 6. Qué habría que cambiar si se retoma

1. **Ítems de elección forzada**, no unipolares: "¿preferirías A o B?" entre dos
   experiencias rivales, nunca "¿qué tanto te gustaría A?". Es la corrección
   estándar contra la deseabilidad social, porque ambas opciones son socialmente
   aceptables. En estas mismas transcripciones, las preguntas que ya tenían esa
   forma (p. ej. a Luis: *"seguir reglas estrictas… comparado con inventar
   soluciones nuevas"*) mantuvieron el perfil correcto.
2. **Prohibir explícitamente** los ítems cuya respuesta "buena" es obvia
   ("¿es importante para ti ayudar a los demás?").
3. **No dejar que el desempate alargue** la conversación: el efecto de recencia
   convierte cada pregunta extra en un riesgo.
4. **Volver a medir antes de aceptar**: la intuición de diseño falló aquí en la
   dirección contraria a la esperada.

## 7. Limitaciones

1. **Una sola ejecución por configuración** (temperatura 0.5). La brecha
   (6/10 vs. 10/10) es amplia, pero no tiene intervalo de confianza.
2. **Sesgo de modelo compartido**: el "estudiante" también es Gemini. La
   deseabilidad social del simulado puede ser mayor que la de un adolescente
   real — aunque el sesgo de aquiescencia está bien documentado en humanos, así
   que el fenómeno no es un artefacto puro de la simulación.
3. **Catálogo pequeño** (17 carreras). La existencia de dos carreras "atractoras"
   genéricas de ayuda social amplifica el efecto; en el catálogo de
   Quetzaltenango (94 carreras) podría distribuirse distinto — no se midió.

## 8. Reproducibilidad

- Perfiles y criterio de acierto: sección 2 y tabla de la sección 3.
- Los scripts de batch (`exp_micro.py`, `diag_truncado.py`) fueron temporales y
  no se versionan, igual que en el experimento anterior; la metodología queda
  descrita para reconstruirlos.
- La versión medida como "con pasos 1+2" no está en el repo: fue revertida. Su
  contenido se describe en la sección 1 y en `CLAUDE.md`.
