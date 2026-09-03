# Edad y grado académico en la recomendación

**Fecha:** 2026-08-20
**Estado:** medido dos veces, NO se integra. Flag
`EDAD_Y_GRADO_EN_RECOMENDACION`, apagado. Las preguntas fijas SÍ se quedan.
**Script:** `backend/experimento_edad_grado.py`
**Datos crudos:** ronda 1 en
`backend/data/tests/experimento_edad_grado_resultados.json`, ronda 2 en
`backend/data/tests/experimento_edad_grado_ronda2.json`

## De dónde salió

De la validación con la psicóloga. Su observación: un joven de 15 y un adulto de
28 que ya cursó algo no están en el mismo punto (el joven tiene menos
conocimiento de las carreras y menos autoconocimiento; el adulto ya tiene una
idea y se orienta más fácil), así que pidió tres datos nuevos y de alta
importancia en el chat: **edad**, **grado académico actual o el último cursado**
y, según eso, **"¿te gustó?" o "¿te está gustando?"**.

Las tres preguntas fijas ya están en producción (`frontend/src/Chat.jsx`) y sus
respuestas ya llegan al prompt: `recomendar()` vuelca el dict completo de
respuestas en el PERFIL DEL ESTUDIANTE. Lo que este experimento mide es lo otro:
si además hay que **decirle al modelo qué hacer con esos datos**.

## Los dos brazos

Bloque `recomendar.CONTEXTO_ACADEMICO`: trato de adulto joven de 18 en adelante,
opciones más amplias en básicos, no reproponer la carrera que dejó si dijo que no
le gustó, contar lo ya cursado como ventaja, y respetar la línea actual si sí le
está gustando.

- **A (control):** producción de hoy. Los datos están en el perfil, sin
  instrucción sobre ellos.
- **B:** lo mismo más el bloque.

Una sola conversación por perfil y dos llamadas a `recomendar()` alternando el
flag. El cambio vive en el último paso, así que correr dos chats aparte solo
habría metido ruido de temperatura 0.9 en la comparación.

## Perfiles

| Perfil | Edad | Grado | ¿Le gustó? | Esperado |
|---|---|---|---|---|
| Kevin | 17 | Diversificado (en curso) | Sí, mucho | informática |
| Melany | 17 | Diversificado (en curso) | Más o menos | administración/contaduría |
| Ana | 23 | Dejó una carrera (Sistemas) | No, nada | educación/humanidades |
| Sergio | 26 | Dejó una carrera (Derecho) | No, nada | gastronomía/turismo |
| Marvin | 31 | Terminó diversificado hace 12 años | Más o menos | administración/contaduría |

## Resultado

| Perfil | A (control) | B (con bloque) |
|---|---|---|
| Kevin | Ingeniería en Electrónica | Ingeniería en Electrónica |
| Melany | Contaduría Pública y Auditoría | Contaduría Pública y Auditoría |
| Ana | Profesorado en Pedagogía con Especialización | Profesorado en Educación Primaria |
| Sergio | Artes Culinarias y Negocios Gastronómicos | Artes Culinarias y Negocios Gastronómicos |
| Marvin | Contaduría Pública y Auditoría | Contaduría Pública y Auditoría |

**Sobre el ranking, no hay efecto.** 4 de 5 top-1 idénticos. El único que se
movió, Ana, se movió DENTRO de su área (Pedagogía → Educación Primaria): los dos
aciertan. Es el mismo resultado que Holland y que el CIP: el ranking no se mueve
por prosa añadida al prompt.

**La medida que importaba no discriminó.** La petición concreta era que no le
vuelvan a proponer la carrera que dejó. El control YA la evita: 0 de 2 en los dos
brazos. En estos perfiles el dato no hacía falta, porque la conversación misma lo
dice ("no quiero nada de programar", "no quiero nada de leyes").

**Y el bloque costó tono.** En los 3 perfiles adultos, B despersonaliza la
descripción del top-1:

- Ana, A: "es perfecta para ti porque combina **tu** amor por la enseñanza".
  B: "es perfecta para **quienes** tienen vocación de servicio".
- Marvin, A: "Te permitirá asegurar que los números de **los negocios de tu
  familia** cuadren". B: "Te permite convertirte en el garante de la salud
  financiera de **una empresa**".
- Sergio, A: "Aprenderás técnicas culinarias avanzadas y cómo administrar un
  negocio". B: "Es el camino ideal para **quienes** desean transformar su
  pasión".

3 de 3. Los dos perfiles de 17 años, que el bloque no toca, conservan el "tú" en
ambos brazos. O sea que el efecto no es ruido de temperatura: es el "háblale como
a un adulto joven, sin sonar a colegio" empujando al modelo a la tercera persona
genérica, justo lo contrario de lo que se quería.

**La otra instrucción ni siquiera se cumplió.** "Lo que ya estudió cuenta como
ventaja, dilo en las razones": ninguna de las razones de Ana ni de Sergio en el
brazo B menciona sus estudios previos.

## Por qué falla, y qué falta de verdad

El bloque no tiene con qué trabajar. Las tres preguntas nuevas capturan *que*
dejó una carrera, no **cuál**. Sin el nombre, el modelo no puede evitarla ni
puede contarla como ventaja, y lo único que le queda del bloque es la parte del
tono, que es justo la que hace daño.

Lo que falta es la pregunta condicional que la psicóloga también pidió y que
todavía no está: **"¿qué carrera estás estudiando / qué estudiaste?"** cuando el
grado es universitario. Con ese dato el experimento se vuelve contestable, porque
la medida "no repitas lo que dejó" pasa a tener contenido incluso cuando el
alumno no lo menciona en el chat. Sin ese dato, esto ya está medido y da que no.

## Qué queda en el código

- Las tres preguntas fijas (edad, grado, condicional) **se quedan**: son datos que
  la psicóloga pidió para el historial y para el registro de la práctica, y no
  hacen daño. Este experimento no las evalúa a ellas.
- `recomendar.CONTEXTO_ACADEMICO` queda escrito y **apagado**
  (`EDAD_Y_GRADO_EN_RECOMENDACION=0`). Volver a encenderlo solo tiene sentido
  después de agregar la pregunta de qué carrera cursó, y midiendo de nuevo.
- `filtro.py` excluye `edad` y `grado` del solapamiento de palabras del
  pre-filtro. Eso no depende del flag: el texto del grado ("universidad",
  "carrera") solapa con casi cualquier perfil y ensuciaba el recorte a 35.

## Limitaciones, dichas de frente

- 5 perfiles ficticios. La medida de evitación son 2. Esto muestra que el
  mecanismo NO se dispara, no prueba que nunca pueda servir.
- Circularidad parcial: la persona simulada y el orientador son el mismo modelo.
- El "acierta=False" de Kevin es artefacto del criterio, no del experimento: sus
  claves de acierto no incluían "electrónica" y el top-1 fue Ingeniería en
  Electrónica en los DOS brazos. No afecta la comparación A/B, pero el número
  suelto no debe leerse como un fallo del sistema.
- Gasto de la corrida: 75 llamadas, 447k tokens de prompt, ~$0.14 a precio de
  pago (corrió en la key gratis).


---

# Ronda 2: ahora con la carrera cursada

**Fecha:** 2026-08-20, el mismo día.

La ronda 1 tenía dos fallas de diseño y las dos se arreglaron:

1. **El dato no existía.** El chat ahora pregunta qué carrera cursa o cursó
   (`carrera_cursada`), con el texto adaptado al grado ("¿Qué carrera
   empezaste?" para quien la dejó, "¿De qué fue tu diversificado?" para quien lo
   terminó) y la pregunta del gusto nombrando esa carrera.
2. **El control se enteraba por el chat.** Ahora los perfiles que dejaron o
   terminaron una carrera **NO la nombran en la conversación** (su guion se lo
   prohíbe). El campo fijo es la única fuente, que es el caso que importa.

Al bloque se le quitó la cláusula de tono de adulto que causó la
despersonalización y se le puso lo contrario explícito ("háblale SIEMPRE de tú,
no escribas para 'quienes' en general"). Se agregó Wendy (28, terminó
Administración de Empresas y no le gustó) para tener 3 casos de evitación, y una
medida automática de segunda persona.

## Resultado

| Perfil | A (control) | B (con bloque) |
|---|---|---|
| Kevin, 17, bachillerato en computación, sí le gusta | Ingeniería en Ciencias y Sistemas ✔ | **Ingeniería Mecánica Industrial ✘** |
| Melany, 17, perito contador | Ciencias Jurídicas y Sociales | Ciencias Jurídicas y Sociales |
| Ana, 23, dejó Ingeniería en Sistemas | Profesorado en Psicopedagogía ✔ | Psicología (PEM y Licenciatura) ✔ |
| Sergio, 26, dejó Ciencias Jurídicas | Artes Culinarias ✔ | Chef Profesional ✔ |
| Marvin, 31, perito contador | Administración de Empresas ✔ | Administración de Empresas ✔ |
| Wendy, 28, terminó Administración | Comunicación y Diseño ✔ | Comunicación y Diseño ✔ |

**La evitación sale 0 de 3 en LOS DOS brazos.** Ninguno le repite a Ana la
Ingeniería en Sistemas, a Sergio el Derecho ni a Wendy la Administración, y esta
vez ellos no lo dijeron en el chat. O sea: **el campo fijo solo ya alcanza**. El
modelo lee "carrera_cursada: Ingeniería en Sistemas" junto a "gusto_grado: No,
nada" y se aparta sin que nadie se lo ordene. Eso es lo que la psicóloga pidió, y
ya funciona sin el bloque.

**El bloque, en cambio, rompió un caso.** Kevin dice que le gusta mucho su
bachillerato en computación. El control lo manda a Ingeniería en Ciencias y
Sistemas; el brazo con bloque lo manda a Ingeniería Mecánica Industrial, fuera de
su área, justo lo que la cláusula "si dijo que SÍ le gusta, lo que propongas debe
ir en esa línea" existía para evitar. La cláusula no solo no sirvió: el resultado
fue peor con ella.

**La despersonalización bajó pero no desapareció.** De 3 de 3 adultos en la ronda
1 a 1 de 6 (Sergio: "Es el camino directo para dominar el arte culinario", contra
el "Esta carrera es perfecta para ti" del control). Marvin B también se va a "Es
ideal para quien busca hacer crecer un negocio" en la segunda mitad de la
descripción. Con la cláusula explícita en contra, sigue pasando.

**La cláusula de aprovechar lo ya cursado tampoco es del bloque.** El control ya
lo hace por su cuenta: a Marvin le dice "Tienes experiencia manejando cuentas en
tiendas". En el brazo B, Ana y Sergio siguen sin una sola razón que mencione lo
que estudiaron antes.

## Nota sobre Melany

En la ronda 1 los dos brazos la mandaron a Contaduría; en la ronda 2 los dos la
mandaron a Derecho. La conversación es nueva en cada ronda y su perfil tiene el
conflicto declarado ("quiero leyes") contra el medido (números y orden), así que
se mueve entera de una ronda a otra. Igual que Dulce en
[holland-sondeo-intereses.md](holland-sondeo-intereses.md), **no sirve para
medir con n chico**: el cambio es entre rondas, no entre brazos.

## Conclusión

Dos rondas, 11 comparaciones A/B, cero mejoras atribuibles al bloque y una
regresión. **El bloque queda apagado, esta vez sin pendientes**: la hipótesis
tenía un hueco (faltaba la carrera cursada), se tapó, y volvió a medir que no.

Lo que SÍ quedó demostrado es lo otro, y es lo que importa para la tesis: **las
cuatro preguntas nuevas (edad, grado, carrera cursada y si le gustó) cambian la
recomendación por sí solas**, sin tocar el prompt. Ana no vuelve a Sistemas,
Wendy no vuelve a Administración y Sergio no vuelve a Derecho, en el brazo de
producción. El catálogo y los datos hacen el trabajo; la prosa en el prompt no
agrega nada.

## Aviso: las preguntas cambiaron DESPUÉS de esta medición

Tras la ronda 2, y por pedido de la psicóloga, las fijas se reorganizaron: el
nivel (básico, diversificado, universidad) se pregunta aparte del grado, el grado
sale de ese nivel (primero a tercero básico; cuarto y quinto de bachillerato;
cuarto a sexto de las carreras de 3 años; cursando, terminada o abandonada en la
universidad) y se agregó el motivo del test. Los textos de `grado` en
`experimento_edad_grado.py` son los de ANTES de ese cambio.

Eso no invalida lo medido, porque lo que se comparó fue el bloque del prompt
contra su ausencia con el MISMO perfil en los dos brazos. Pero si se vuelve a
correr el script, hay que actualizar los perfiles a las etiquetas nuevas.

Lo otro que cambió es que la carrera abandonada ahora se descarta del catálogo
en el backend (`filtro.descartar`), sin pasar por el modelo. Eso también es
posterior a la medición.

Gasto de la ronda 2: 90 llamadas, 543k tokens de prompt (128k cacheados), ~$0.14
a precio de pago.
