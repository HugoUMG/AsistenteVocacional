# Experimento: el psicométrico primero, el chat sin preguntas fijas

**Fecha:** 2026-08-12 · **Estado:** NO se integra al flujo. Queda como experimento
aislado en `backend/experimento_psicometrico.py`. Producción sigue igual.

## Qué se probó

Hipótesis: si el alumno responde el examen psicométrico ANTES de conversar, el
chat puede saltarse las 4 preguntas fijas (impacto / estilo / entorno / gustos)
y gastar sus 4-8 turnos en preguntas especializadas, porque personalidad,
habilidades y estilo cognitivo ya vienen **medidos** en vez de estimados por la
propia IA.

| | VIEJO (flujo de hoy) | NUEVO (propuesta) |
|---|---|---|
| Entrada | 4 preguntas fijas | hoja psicométrica calificada |
| Dimensiones que arrancan cubiertas | intereses, entorno, motivaciones | personalidad, habilidades, estilo_cognitivo |
| Pendientes que persigue el chat | personalidad, habilidades, valores, estilo_cognitivo | intereses, valores, entorno, motivaciones |
| Lo que recibe `recomendar()` | respuestas del chat | respuestas + bloque psicométrico |

Ambos brazos: mismo catálogo (202 registros carrera-sede de Quetzaltenango y
Totonicapán), misma persona respondiendo con el mismo guion, mismo tope de
preguntas adaptativas.

## Cómo se hicieron realistas los 5 perfiles

El punto del experimento no era ver si la IA acierta con alumnos de manual, sino
qué pasa cuando el alumno **miente en unas cosas y es honesto en otras**, que es
lo normal a los 16 años.

- Las secciones objetivas (lógico/verbal/numérico) **no las responde la IA**: se
  simulan con una aptitud por sección y una conducta (cuántos ítems finales deja
  en blanco por tiempo o desgana). Que un alumno "no sepa" es aritmética
  reproducible, no una actuación del modelo.
- La sección de personalidad tampoco: se arma desde los rasgos reales del perfil
  y se le inyectan **distorsiones con nombre** — deseabilidad social,
  aquiescencia, refugio en el centro. Como sé qué sesgo metí, puedo comparar
  contra lo que el instrumento detectó.
- Solo el chat lo responde Gemini en el papel del alumno, con un guion que dice
  explícitamente en qué tema miente y en cuál se delata.

| Perfil | Verdad | Mentira / sesgo | Sesgo inyectado en la hoja | Aptitudes medidas |
|---|---|---|---|---|
| **Kevin**, 17 | Arma PCs, repara celulares, prefiere estar solo | Dice que las matemáticas se le dan bien (las reprueba) y que le gusta liderar | deseabilidad social | log p80 · ver p33 · **num p2** |
| **Dulce**, 16 | Le gusta cuidar gente | Repite el discurso de la casa ("seré enfermera"); esconde que lo suyo es dibujar y editar video | deseabilidad + aquiescencia | log p50 · **ver p75** · num p12 |
| **Brandon**, 15 | Nada le interesa, quiere terminar | No miente: se desentiende | refugio en el centro | log p10 · ver p2 · num p1 |
| **Melany**, 17 | Lleva las cuentas de la tienda, odia improvisar | Cree que quiere "leyes" porque una prima abogada gana bien | ninguno | log p75 · ver p67 · **num p86** |
| **Josué**, 18 | Sabe de suelos y cosecha | Le da pena el campo, en público dice "ingeniería" | aquiescencia | log p50 · **ver p17** · num p42 |

## Lo que el instrumento detectó (y lo que no)

Contrastado contra el sesgo que se inyectó, no contra lo que la IA opinó:

| Sesgo inyectado | ¿Lo detectó `psicometrico.py`? | Cómo |
|---|---|---|
| Deseabilidad social (Kevin, Dulce) | **Sí** | `deseabilidad_social.alerta`, 100% |
| Refugio en el centro (Brandon) | **Sí** | `tendencia_central` 80%, alerta |
| Aquiescencia (Dulce, Josué) | **No** | consistencia 75% y 83%: por encima del umbral |

La aquiescencia — marcar "de acuerdo" sin fijarse en que el ítem estaba
invertido — pasa limpia. Medido con el mismo perfil y la misma semilla, con y
sin el sesgo, la consistencia **sube** (79% → 83%). El motivo es concreto:
ninguno de los 6 pares de `PARES_CONSISTENCIA` enfrenta un ítem directo con su
invertido, así que el sesgo que los ítems invertidos existen para cazar no queda
cazado por ningún par. Es el mismo techo que ya está documentado en el `ponytail:`
de `app/psicometrico.py` (hacen falta ítems paráfrasis, no recombinar los que
hay). El `--self-check` del experimento afirma esta limitación: si algún día se
agregan esos ítems, el assert falla y avisa que hay que reescribir este párrafo.

## Qué cambió en la conversación, caso por caso

### Kevin — el único caso donde el psicométrico cazó una mentira

**VIEJO.** La opción fija de impacto que eligió fue *"Liderar, organizar negocios
o usar tecnología y números"*: una sola casilla que mezcla tres cosas distintas.
Kevin la marcó por "tecnología", y de ahí en adelante la IA lo trató como alguien
de negocios y números. Su primera pregunta adaptativa abrió con *"se nota que te
apasiona meterle mano a las máquinas y que **los números se te dan muy bien**"* —
eso es la mentira del alumno devuelta como halago, sobre un percentil 2 real. Al
preguntarle por trabajo en equipo dijo que le gusta liderar (su segunda mentira),
y la IA la tomó al pie de la letra: la pregunta siguiente ya arrancaba con *"qué
bueno que disfrutes tanto liderar equipos"*. Cerró en **Administración de Sistemas
Informáticos (35%)** con Ingeniería Industrial en el top-3 y **confianza 90%**,
con la nota *"tus respuestas son muy claras y consistentes"*. Es el peor tipo de
error: seguro y equivocado en la misma frase.

**NUEVO.** Con el percentil en el prompt, la IA levantó `alerta_contradiccion` en
3 de las 4 preguntas, y la primera decía textualmente: *"te apasiona la
tecnología, pero en el examen tus resultados en razonamiento numérico fueron
bajos, mientras que en creatividad fuiste muy alto"*. Es exactamente el
comportamiento que se buscaba. **Pero la recomendación se fue a Profesorado en
Tecnología Educativa (45%)**, fuera del área. La causa está en la primera
pregunta: sin las fijas, el chat no tenía ni un dato de intereses, y su primera
pregunta a ciegas fue *"¿mejorar la educación de los jóvenes o proteger la
naturaleza?"*. Kevin eligió educación —con una respuesta coherente con su
carácter, "para que más patojos aprendan a armar sus compus"— y esa elección
arrastró las tres preguntas siguientes y la recomendación final. Confianza 65%.

### Dulce — el flujo actual la destapó; el nuevo la dejó en el guion de la casa

**VIEJO.** En la pregunta fija de temas (chips), marcó *Salud y cuidar personas*
"porque es lo que toca", y en la misma respuesta añadió *Arte, diseño y
creatividad* y *Comunicación, escritura y medios*. Se delató en el turno 1, sin
tener que contradecir a su mamá en voz alta. El chat lo detectó (*"noto que te
apasiona mucho el arte y la edición, pero también quieres enfocarte en la
salud"*) y las 4 preguntas adaptativas exploraron esa tensión. Top-1
**Comunicación y Diseño (45%)**.

**NUEVO.** Sin chips, su primer turno fue una pregunta cerrada: *"¿mejorar la
salud o transformar la educación?"*. Respondió con el guion familiar y ya no
hubo forma de salirse: las tres preguntas siguientes se construyeron sobre "te
motiva cuidar a la gente". Top-1 **Enfermería (35%)**. El dato estaba en el
bloque psicométrico —apertura 86/100, el rasgo más alto de su perfil— y el chat
**no lo usó** para explorar la vena creativa: lo mencionó en un saludo genérico y
nada más.

Este es el hallazgo más incómodo del experimento. La tabla de "área esperada"
marca este caso al revés (VIEJO falla, NUEVO acierta) porque el área esperada era
salud. Contando así, el brazo nuevo gana un punto **por reproducir la presión
familiar en vez de detectarla**. Por eso este informe no se resume en un marcador.

**Por qué pasa:** una pregunta de opción múltiple con 15 chips es un canal de
revelación de bajo costo social. Marcar una casilla entre quince no es
"decirlo"; responderle a un orientador que lo tuyo no es lo que tu familia
espera, sí. Quitar las fijas quitó ese canal.

### Brandon — el nuevo calibra mejor la confianza, pero ninguno se planta

Contestó "me da igual" a todo, en los dos brazos, y **ninguno se negó a
recomendar**. La diferencia está en la honestidad del cierre: VIEJO cerró con
**confianza 65%** y la nota *"tus respuestas son directas y muestran una
preferencia clara por la tecnología"* — inventó una preferencia clara donde solo
hubo desgana. NUEVO cerró con **45%** y *"tus respuestas son muy breves y
neutrales, lo que hace difícil conocerte a fondo"*. Esa mejora viene directo del
bloque de VALIDEZ del prompt: la alerta de 80% de respuestas "Neutral" entró y la
IA la tradujo a menos confianza. Es el efecto más limpio y reproducible que
mostró la integración.

Lo que ninguno hizo: decirle al alumno que su protocolo no informa y ofrecerle
repetirlo. Se recomendó igual, con un 45% que en el dashboard se lee como un
resultado más.

### Melany — el flujo actual desmontó su creencia falsa; el nuevo ni se enteró

**VIEJO.** En los chips marcó *Negocios, dinero y números* **y** *Leyes, justicia
y debate*, "porque es lo que quiero estudiar para que me vaya bien". El chat
detectó la contradicción en 2 preguntas seguidas y la resolvió con la pregunta
más útil de todo el experimento: *"¿se te da mejor organizar información y
números, o leer y entender leyes?"*. Respuesta: *"organizar números, de lejos;
leer textos de leyes me aburre un montón"*. Top-1 **Contaduría Pública y
Auditoría (35%)**, confianza 90%.

**NUEVO.** El tema de las leyes **nunca apareció**. Nadie le preguntó por su meta
y ella no la mencionó sola, así que hubo cero alertas de contradicción y la
conversación fluyó suave sobre lo que ya se sabía. Top-1 **Ingeniería Industrial
(35%)**, con Contaduría desplazada al #3. No es un disparate —encaja con num p86
y organización 83/100, y el psicométrico sí se usó bien en la apertura ("veo que
tienes un perfil muy ordenado y una capacidad increíble para los números")— pero
la alumna terminó la sesión con la misma idea equivocada con la que entró.

**Por qué pasa:** las preguntas fijas no solo recogen datos, obligan al alumno a
**declarar su plan**. El psicométrico mide cómo es y cuánto rinde; no le pregunta
qué quiere ser. Sin ese dato no hay nada contra qué contrastar, y la
`alerta_contradiccion` —que es una de las mejores piezas del sistema— se queda
sin materia prima.

### Josué — empate; los dos llegaron al campo por caminos distintos

**VIEJO.** Eligió la casilla de "construir, diseñar" (su fachada de ingeniería)
pero en el texto libre de la misma pregunta se le salió: *"si le soy sincero, me
gusta más trabajar la tierra"*. La casilla le dio permiso de decir la fachada y
el texto libre le dio permiso de decir la verdad, en el mismo turno. Top-1
**Ingeniería en Agronomía (45%)**.

**NUEVO.** La primera pregunta fue de entorno (oficina vs. campo) y lo llevó al
mismo lugar por la vía rápida. Top-1 **Ingeniería en Administración de Tierras
(45%)**, Agronomía en #2. Área acertada en los dos brazos.

Lo que ninguno de los dos hizo: usar el verbal p17 medido. Recomendar una
ingeniería universitaria a alguien con percentil 17 en comprensión verbal es una
conversación que valía la pena tener, y el dato estaba en el prompt del brazo
nuevo sin que nadie lo tocara.

## Números, para el registro

| Perfil | Brazo | Preguntas | Alertas de contradicción | Confianza | Tokens | Top-1 |
|---|---|---|---|---|---|---|
| Kevin | viejo | 4 | 0 | 90% | 60 553 | Admin. de Sistemas Informáticos |
| Kevin | nuevo | 4 | **3** | 65% | 73 647 | Prof. en Tecnología Educativa |
| Dulce | viejo | 4 | 1 | 85% | 57 103 | Comunicación y Diseño |
| Dulce | nuevo | 4 | 1 | 75% | 61 023 | Enfermería |
| Brandon | viejo | 4 | 0 | 65% | 55 256 | Ingeniería Mecánica |
| Brandon | nuevo | 4 | 0 | **45%** | 61 455 | Téc. en Desarrollo de Software |
| Melany | viejo | 4 | **2** | 90% | 49 251 | Contaduría Pública y Auditoría |
| Melany | nuevo | 4 | 0 | 90% | 64 378 | Ingeniería Industrial |
| Josué | viejo | 4 | 0 | 90% | 62 341 | Ingeniería en Agronomía |
| Josué | nuevo | 4 | 0 | 85% | 70 591 | Ing. en Administración de Tierras |

- **Turnos:** 4 y 4. La hipótesis prometía preguntas mejor gastadas, no menos, y
  en efecto no hubo ahorro: los dos brazos cerraron en el mínimo de 4.
- **Tokens:** 284 504 (viejo) vs **331 094 (nuevo), +16%**. El bloque psicométrico
  viaja en cada llamada de next-question. Quitar 4 preguntas fijas no ahorra nada
  porque las fijas no gastaban IA.
- **Área esperada:** 3/4 vs 2/4 — dato reportado por completitud y **no
  concluyente**: son 4 casos con criterio propio, y en Dulce el marcador premia al
  brazo que reprodujo la presión familiar.

## Conclusión

**No se integra.** No por el marcador, sino porque el experimento identificó qué
aporta cada pieza, y resultan ser piezas distintas que no se sustituyen:

1. **El psicométrico aporta lo que el chat no puede saber: aptitud real.** Es la
   única defensa que apareció contra un alumno que miente sobre lo que se le da
   bien (Kevin), y es lo que hizo que la confianza dejara de inflarse con un
   alumno desentendido (Brandon 65% → 45%).
2. **Las preguntas fijas aportan lo que el psicométrico no mide: intereses
   declarados y el plan que el alumno trae en la cabeza.** Sin ellas se pierden
   dos cosas medidas aquí: el canal de revelación barato de los chips (Dulce,
   Josué) y la materia prima de la `alerta_contradiccion` (Melany).
3. Son **complementarias**, no alternativas. El diseño que probé las puso a
   competir, y esa fue la decisión equivocada del experimento.

### Qué sí vale la pena probar después

- **Sumar, no sustituir:** mantener las 4 fijas e inyectar el bloque psicométrico
  para que la IA contraste lo declarado contra lo medido. Es el diseño que
  hubiera dado las alertas de Kevin sin perder los chips de Dulce. Cuesta ~16%
  más de tokens y hay que medirlo igual.
- **Arreglar la casilla mezclada** *"Liderar, organizar negocios o usar tecnología
  y números"*: junta liderazgo, negocios, tecnología y números en un solo clic, y
  fue el origen del desvío de Kevin en el brazo viejo. Esto no depende del
  experimento; es un defecto que quedó a la vista.
- **Tacto de la alerta:** el brazo nuevo le dijo al alumno *"tus resultados en
  razonamiento numérico fueron bajos"* en medio del chat. El prompt pide no dar
  cifras; hay que reforzarlo antes de que algo así llegue a un alumno real.
- **Ítems paráfrasis** en el banco de personalidad, para que la aquiescencia deje
  de pasar limpia.

## Reproducir

```bash
cd backend
uv run python experimento_psicometrico.py --self-check   # sin red
uv run python experimento_psicometrico.py --hojas        # las 5 hojas calificadas, sin red
uv run python experimento_psicometrico.py                # el A/B (~90 llamadas, reanudable)
```

Transcripciones completas y puntajes crudos:
`backend/data/tests/experimento_psicometrico_resultados.json`.
