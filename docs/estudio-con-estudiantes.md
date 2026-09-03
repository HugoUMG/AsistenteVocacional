# Plan del estudio con estudiantes reales

**Fecha:** 2026-08-18 · **Estado:** plan, sin ejecutar.

Todo lo que este proyecto midió hasta hoy se hizo con **perfiles ficticios
simulados por el propio Gemini** y calificados contra **listas de palabras clave
escritas por el desarrollador**. Eso mide consistencia interna, no validez. Este
documento es el plan para conseguir la evidencia que falta.

---

## 1. Qué problema resuelve, en concreto

Los experimentos de `experiments/` tienen tres debilidades apiladas:

| Debilidad | ¿La resuelven estudiantes reales? |
|---|---|
| Gemini hace de alumno (circularidad: el mismo modelo pregunta y responde) | **Sí, del todo.** Es el arreglo principal. |
| La respuesta "correcta" la define una lista de palabras clave del desarrollador | **No por sí solos.** Hace falta un criterio independiente, ver §4. |
| n minúsculo (2-3 perfiles, 1-6 corridas) | **Parcialmente.** 20-30 alumnos es más, pero sigue siendo chico. |

Sin criterio independiente, un estudio con alumnos reales da **datos auténticos
sin vara para medirlos**, y la subjetividad simplemente se muda de los perfiles
ficticios a los datos reales.

## 2. La decisión de diseño que abarata todo

**Grabar la conversación una vez y reusarla offline.**

Es el diseño de [experiments/holland-estructura.md](../experiments/holland-estructura.md)
§4, que comparte una conversación entre brazos, pero con una conversación
**auténtica** en lugar de simulada. Se recolecta la sesión del alumno una sola
vez y después se corre la recomendación cuantas veces haga falta: con y sin el
bloque de Holland, con y sin el catálogo ordenado por afinidad RIASEC.

Eso **asciende los tres experimentos de Holland de "perfil ficticio" a
"conversación real"** sin volver a molestar a nadie y por centavos de Gemini.

**Pero no sirve para todo.** Hay que separar dos familias de hallazgo:

| Familia | Ejemplos | Diseño que necesita |
|---|---|---|
| **Paso de recomendar** | Holland como prosa, como estructura, catálogo ordenado | Reejecución offline sobre la misma conversación. **Intra-sujeto, barato, limpio.** |
| **Paso de preguntar** | Apertura explícita, turno de sondeo | Cambian la conversación misma, no se pueden reejecutar. **Entre-sujetos, n grande.** |

Consecuencia práctica: la medición de la apertura
([holland-apertura.md](../experiments/holland-apertura.md) §8, p = 0.545)
**no se salva con 25 alumnos.** Con un fenómeno cercano al 50/50 haría falta
mucho más, o se acepta que queda exploratoria.

## 3. Preguntas del estudio

Ordenadas por lo que rinden contra lo que cuestan:

1. **¿El ranking se mueve con Holland, en conversaciones reales?** Reejecución
   offline, intra-sujeto. Es la réplica directa de tres experimentos y la más
   barata. Si con datos reales sigue sin moverse, esa afirmación pasa a ser
   defendible, que hoy no lo es.
2. **¿Coinciden Holland y el chat?** Concordancia entre el área RIASEC medida y
   el sector de la carrera recomendada. Ojo: pueden coincidir y estar los dos
   equivocados. Es descriptivo, no validante.
3. **¿La recomendación le parece acertada a un experto?** El criterio de §4.
4. **¿El alumno la percibe como útil y personalizada?** Aceptabilidad. Es lo
   único que mide directamente la apertura explícita, que es lo que esa función
   sí controla al 100%.

## 4. El criterio, y hay que fijarlo ANTES de recolectar

Elegir la vara después de ver los datos invalida el ejercicio. Opciones de menor
a mayor valor probatorio:

| Criterio | Qué prueba | Viabilidad |
|---|---|---|
| Satisfacción del alumno | Aceptabilidad, no acierto | Alta |
| Concordancia Holland ↔ chat | Que dos instrumentos coinciden | Alta |
| **Juicio de la psicóloga a ciegas** | **Acuerdo con un experto humano** | **Media, y es el recomendado** |
| Seguimiento a 1 año (inscripción, permanencia) | Validez predictiva, patrón oro | Fuera del alcance de un TFG |

**Recomendado: la psicóloga califica a ciegas.** Recibe, para cada alumno, las
salidas sin saber cuál vino de qué instrumento, y las puntúa. Eso da una vara
independiente del desarrollador y del modelo, que es exactamente lo que falta.

Detalle de diseño: presentar las salidas **en orden aleatorizado y sin
etiquetas** de origen. Si sabe cuál es cuál, el sesgo de expectativa se cuela.

**Dónde se registra ese juicio:** ya está en la app. Dentro de `/admin`, al
abrir una evaluación, al final del recorrido hay tres opciones (Acertó, Acertó
en parte, No acertó) y un campo de comentarios. Se guarda en
`respuestas_cuestionario.juicio` y `.juicio_nota` (`POST /api/admin/juicio`) y
sale en el CSV del registro, así que entra al análisis junto con el resto de la
fila. Ojo con §4: para que sea a ciegas, quien califica **no debería ver el
recorrido completo** de un solo golpe; hoy la pantalla lo muestra todo, y eso
hay que resolverlo con el protocolo de la sesión, no con la UI.

La guía de [entrevista-validacion-psicologa.md](entrevista-validacion-psicologa.md)
ya toca esto en su ítem 6. **Falta pedirle explícitamente que acepte hacer de
criterio externo**, que es un compromiso de tiempo distinto a dar una opinión.

## 5. Tamaño de muestra

- **Para las preguntas intra-sujeto (§3.1):** cada alumno aporta un par
  comparable, así que rinden mucho más por persona. 20-30 alumnos dan una base
  razonable para describir el fenómeno.
- **Para lo entre-sujetos (§3.4 y la apertura):** un efecto de 50% → 83% pide
  ~15 por brazo con 80% de potencia. Con dos brazos son 30 alumnos **solo para
  esa pregunta**.

Con 25-30 alumnos alcanza para §3.1, §3.2 y §3.3, que es el grueso del valor.
No alcanza para cerrar la apertura, y eso hay que declararlo, no estirarlo.

## 6. Requisitos previos, bloqueantes

1. **Consentimiento informado de padres o tutores.** Son menores de 13 a 17
   años. No es un trámite: es un cuello de botella de calendario y hay que
   arrancarlo con semanas de anticipación.
2. **Asentimiento del propio alumno**, aparte del consentimiento de los padres.
3. ~~**Quitar el panel de perfiles de prueba de Holland.**~~ **RESUELTO**
   (verificado 2026-08-23): el panel está detrás de `import.meta.env.DEV` en
   `frontend/src/Holland.jsx`, así que no existe en el build de producción, y
   en el repo público no está el bloque. No hay nada que hacer acá.
4. **Definir qué se guarda y cómo se anonimiza.** Hoy existen cuatro tablas de
   resultados (`respuestas_cuestionario`, `resultados_holland`,
   `resultados_psicometricos`, `resultados_personalidad`) más `uso_tokens`. Hay
   que decidir el identificador de estudio y no guardar nombre real junto a las
   respuestas.
5. **Fijar el criterio (§4) por escrito** antes del primer alumno.
6. **Aviso de que interviene una IA** y de que el resultado no es un
   diagnóstico. Es una exigencia ética, y varias preguntas de la guía de
   entrevista apuntan ahí.

## 7. Logística de la sesión

El modo 3 completo es Holland (60 ítems) más el chat (4 fijas + 4 a 8
adaptativas). En un colegio eso es aproximadamente **un período de clase por
alumno**. El psicométrico de 100 ítems **no cabe en la misma sesión**: si entra
en el estudio, va en una sesión aparte.

Conviene una prueba piloto con 2 o 3 alumnos antes de la tanda completa, para
medir el tiempo real y detectar preguntas que no se entienden.

## 8. Qué se va a poder afirmar, y qué no

**Sí:**
- Si el resultado de Holland mueve o no la recomendación **en conversaciones
  reales**, que es la réplica que hoy falta.
- Cuánto concuerda el sistema con el juicio de una profesional.
- Si los estudiantes lo perciben como útil y personalizado.

**No, ni con este estudio:**
- Que el sistema **supere** a Holland. Eso pide validez predictiva, o sea
  seguimiento longitudinal. Ver la discusión en
  [holland.md](holland.md): lo defendible es **complementariedad y alcance
  distinto**, no superioridad.
- Nada con potencia estadística sobre las intervenciones del paso de preguntar,
  salvo que el estudio crezca bastante.

## 9. Orden sugerido

1. Entrevista con la psicóloga, usando la guía existente, y pedirle que acepte
   ser criterio externo.
2. Fijar el criterio por escrito y redactar los consentimientos.
3. Quitar los presets de prueba (§6.3) y definir la anonimización (§6.4).
4. Piloto con 2-3 alumnos.
5. Tanda de 25-30.
6. Reejecución offline de los brazos sobre las conversaciones reales (§2).
7. Calificación a ciegas de la psicóloga.
8. Informe, con el mismo formato que `experiments/`: qué se midió, qué salió,
   qué NO se puede afirmar.
