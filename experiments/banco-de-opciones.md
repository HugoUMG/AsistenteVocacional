# Revisión del banco de opciones contra el catálogo completo

**Estado:** APLICADO, MEDIDO y con sus dos pendientes cerrados, 2026-08-23. El banco pasó de 15 a 25 chips en
`gustos` y se reescribieron 5 etiquetas más. La medición está abajo: no prueba
una mejora general, sí prueba que el banco nuevo representa personas que el
viejo no podía representar.

Herramienta: `backend/cobertura_banco.py` (no gasta cuota).

---

## La pregunta

¿Qué temas del catálogo NO tiene forma de nombrar el alumno con las opciones que
le damos?

La depuración anterior (ver [filtro-catalogo-ab.md](filtro-catalogo-ab.md)) fue
carrera por carrera y sobrecontaba: cinco Ingenierías en Sistemas con el mismo
`perfil` son UN tema, no cinco. Acá el clúster es el perfil, que el catálogo ya
agrupa con `perfil_id`: **147 carreras, 90 temas**.

## Por qué importa, dicho con precisión

**No es por el pre-filtro.** El A/B midió que el filtro no mueve el resultado
final, porque `recomendar()` ve el catálogo completo. Si la justificación fuera
esa, este trabajo no se haría.

Importa por dos cosas distintas:

1. **El alumno tiene que reconocerse.** Si le gusta la música, o los idiomas, o
   los animales, y ninguna opción lo nombra, el chip "Otro / especificar" es la
   única salida y hay que saber usarlo.
2. **El texto de las opciones es la señal que lee Gemini.** No por
   emparejamiento de palabras, por significado.

Corolario que conviene no olvidar al editar esto: **las etiquetas se redactan
para el alumno, no para el filtro.** Hubo un intento de reescribirlas para que
empataran con el vocabulario de los perfiles y salía español forzado
("Comunicar, crear, diseñar o investigación"); se descartó.

## Lo que había

**18 de 90 temas** sin ninguna palabra que los tocara, cubriendo 25 carreras:

| Tema | Carreras | Cómo entraba |
|---|---:|---|
| Enfermería | 4 | nada |
| Imágenes médicas (radiología, bio imágenes) | 4 | `estudio` ("el estudio solicitado") |
| Educación, dirección de centros | 4 | `centro`, `liderar` |
| Ciencias de la Educación / Profesorados | 3 | `psicología` |
| Idiomas (inglés x2, maya) | 3 | nada / `escritura` |
| Telecomunicaciones | 2 | `aire` ("viaja a través del aire") |
| Economía y Economía Empresarial | 2 | `realidad` |
| Educación de Lenguaje / de Física y Matemática | 2 | `medio` ("nivel medio") |
| Electrónica | 1 | `funcionan` |
| Agronomía | 1 | nada (el chip decía "agricultura", el perfil dice "agropecuarias", "agronegocios") |
| Música | 1 | nada |
| Teología | 1 | nada |
| Profesorado en TIC | 1 | nada |

Más los cubiertos por un verbo suelto: Comercio Internacional (`libre`),
Relaciones Internacionales (`conflictos`), Psicología Educativa (`trabajar`),
Producción Audiovisual (`movimiento`), Fisioterapia (`directo`).

## Lo que se cambió

**10 chips nuevos en `gustos`**, cada uno por un tema que no tenía forma de
nombrarse:

`Equipos médicos, laboratorio e imágenes` · `Cuerpo, deporte y rehabilitación` ·
`Animales y su cuidado` · `Economía, pobreza y desarrollo del país` ·
`Comercio, política y otros países` · `Música, danza y artes escénicas` ·
`Idiomas y otras culturas` · `Organizar y dirigir equipos o instituciones` ·
`Redes, señal y electrónica` · `Fe, religión y espiritualidad`

**5 etiquetas reescritas**, donde la palabra natural en español además nombra
mejor el tema:

| Antes | Ahora | Por qué |
|---|---|---|
| Salud y cuidar personas | Salud, cuidados y atención a pacientes | era el único chip de enfermería y no la nombraba |
| Negocios, dinero y emprender | Negocios, dinero y emprendimiento | |
| Enseñar y educar | Enseñanza, docencia y educación | la familia más grande del catálogo (14 carreras) colgaba de aquí |
| Medio ambiente y agricultura | Ambiente, agricultura y agronegocios | agronomía es agroindustria, no solo cultivo |
| En medios, un estudio creativo o diseñando | En medios de comunicación o diseñando | `estudio` era por donde entraban Radiología y Teología |

Y en `impacto`, "investigar la realidad" pasó a "hacer investigación", que es lo
que el alumno reconoce.

## Resultado

**De 18 temas descubiertos a 3.** Los 3 que quedan no son huecos de tema, son el
techo conocido de `filtro.py`, que empareja forma exacta de palabra sin lematizar:

- Idioma Maya: el perfil dice `idioma` y `cultura`, el chip dice `idiomas` y `culturas`.
- Profesorado en TIC: el perfil dice `cómputo` y `computadoras`, el chip dice `computación`.
- Educación de la Comunicación y Lenguaje: falso negativo de la propia
  herramienta, que marca `escritura` como falso amigo porque lo es en el perfil
  del idioma maya, pero acá es legítima ("difusión literaria").

No se siguió persiguiendo formas de palabra: sería contorsionar el español para
un filtro que ya se midió que no decide el resultado.

## Los dos pendientes, cerrados

### El caso Rosa NO era dispersión

Se revisó qué marcó Rosa en cada brazo y **marcó exactamente los mismos chips de
máquinas y construcción en los dos**:

| Chip | Brazo A (viejo) | Brazo B (nuevo) |
|---|---|---|
| Construir, diseñar o hacer que las cosas funcionen | sí | sí |
| Construcción, máquinas y cómo funcionan las cosas | sí | sí |
| Liderar, organizar negocios o usar tecnología y números | sí | sí |
| En un laboratorio o taller técnico | sí | sí |

La única diferencia fue que en el brazo nuevo marcó 5 chips de `gustos` en vez
de 3, y los 2 extra eran de salud. **El ingrediente que produjo Ingeniería
Mecánica Industrial estaba presente en los dos brazos**, así que la diferencia
cae dentro del ruido ya medido (3 de 8 personas cambian de resultado solas entre
corridas).

Lección repetida: "más chips dispersan" era una explicación bonita colgada de un
solo caso, igual que la hipótesis de la ambigüedad. Un caso llamativo no es un
patrón hasta que se revisa de dónde salió.

### El móvil, arreglado y verificado

`.options.choices.chips` caía a 1 columna abajo de 560px. Ahora se queda en 2 y
las demás preguntas siguen cayendo a 1. Medido contra la hoja de estilos de la
app en el navegador:

| Ancho | Chips | Otras preguntas |
|---|---|---|
| 375px | **2** (antes 1) | 1 |
| 768px | 2 | 2 |
| 1014px | 3 | 2 |

25 chips pasan de 25 filas de scroll a 13 en teléfono.

---

## La medición (2026-08-23)

Script: `backend/experimento_banco.py` · 6 personas · dos rondas · $0.20.

### Por qué NO se midió con `claves`

El primer diseño puntuaba con `claves`: se define de antemano qué carrera
debería salir y se cuenta si el top-1 la contiene. Para un banco de opciones eso
está roto, y hay que decirlo porque es tentador reusarlo:

1. El perfil del alumno simulado se escribe para llevar a esa carrera, así que
   las respuestas ya vienen elegidas para que ese resultado gane.
2. Si el brazo nuevo propone una carrera **distinta pero igual de sensata**, la
   métrica la cuenta como fallo.

El banco viejo ganaba por construcción. Se cambió a **personas** descritas sin
ninguna carrera en mente (un self-check verifica que ningún perfil nombre
carreras ni repita etiquetas del banco) y un **juez ciego** que puntúa coherencia
con la persona, con el orden de las listas sorteado.

### El arnés tenía un sesgo, y corregirlo dio vuelta el marcador

**Ronda 1:** el alumno simulado contestaba las fijas con un párrafo y la etiqueta
se recuperaba buscándola como subcadena. Cuando parafraseaba, la respuesta se
guardaba como texto libre: **15 de 48 veces**, y asimétricamente (6 en A, 9 en B),
porque son las etiquetas NUEVAS las que no se reconocían. El sesgo iba contra el
brazo que se estaba probando.

**Ronda 2:** `_marcar()` pide índices de las opciones, que es lo que hace el
alumno real en `Chat.jsx` (toca chips, y solo escribe si usa 'Otro'). Caídas a
texto libre: **0 de 48**.

| | A (banco viejo) | B (banco nuevo) |
|---|---:|---:|
| Ronda 1, arnés sesgado | 3 | 2 (+1 empate) |
| **Ronda 2, arnés corregido** | **2** | **4** |
| Coherencia media R2 (1-5) | 4.17 | 4.33 |
| Top-1 distinto entre brazos, R2 | 4 de 6 | |

**Las dos rondas están dentro del ruido y ninguna prueba una mejora general.**
De 6 personas, 3 cambiaron de veredicto entre rondas. Con el piso de ruido
conocido (3 de 8 perfiles cambian solos), un 2-4 no es un resultado. Lo que sí
quedó demostrado es que **el marcador de la ronda 1 no era confiable**.

### Lo único que se repitió en las dos rondas

**Wendy** toca marimba desde los 12. `Profesorado en Educación Artística (Música
y Danza)` aparece en el top-3 del banco nuevo en **las dos rondas** (top-1 en la
1, top-2 en la 2) y en el del banco viejo en **ninguna de las dos**. Con el banco
viejo su música se pierde: marca "Arte, diseño y creatividad" y sale
psicopedagogía o educación primaria.

Esa carrera existe en el catálogo y antes no había forma de llegar a ella. Es la
afirmación que este experimento sostiene: **el banco nuevo representa gente que
el viejo no podía representar.** No sostiene que recomiende mejor en general.

Los chips nuevos se marcan: las 6 personas usaron al menos uno en la ronda 2.

### Evidencia en contra, sin maquillarla

- **Rosa** (quiere salud pero con aparatos, no trato largo con pacientes). En la
  ronda 2 el banco nuevo le dio Fisioterapia, **Ingeniería Mecánica Industrial**
  y **Cirujano Dentista**, peor que el viejo. Se dijo que "más chips también
  puede dispersar" y **eso resultó falso**: ver abajo.
- **Kevin.** El banco nuevo perdió las dos rondas. En la 1 metió Administración
  de Empresas, que él había rechazado explícitamente.
- **El juez no es un instrumento estable.** Trabajo Social como top-1 le pareció
  un acierto en una ronda y lo castigó en la otra, según el resto de la lista.
  Es una segunda opinión, no un veredicto.

### Veredicto

El banco nuevo **se queda**, por la razón por la que se hizo: cubre 18 temas del
catálogo que no tenían forma de nombrarse, los chips se usan, y el caso Wendy se
repitió. **No se afirma que mejore el ranking**, porque no se midió eso.

Antes de subirlo a MiOrienta conviene mirar el caso Rosa con más n: si dispersar
resulta ser un patrón y no un caso, la palanca es afinar la redacción de los
chips de salud, no volver al banco de 15.

### Lo que este experimento deja para el resto del repo

El diseño "personas + juez ciego + coherencia" sirve para releer experimentos
viejos cuyo veredicto dependía de `claves` fijadas de antemano. En particular
[adaptativas-desempate.md](adaptativas-desempate.md), donde la pregunta no es
"¿acertó?" sino "¿la pregunta extra separó dos carreras hermanas?".

---

## A/B de las 3 etiquetas acortadas (2026-08-23)

Script: `backend/experimento_etiquetas.py` · $0.1318 · 8 casos.

### Qué se cambió y por qué se midió

Para que los 25 chips quepan en una línea (y desaparezca el scroll en
escritorio) habría que bajar todas las etiquetas a 26 caracteres. Se probó:
la lista pasa de 696px a 608px y caben los 25 de una vez. Pero
`verifica_etiquetas.py` marcó **13 de 16 pares como no equivalentes**:
"Ambiente y agronegocios" pierde *agricultura*, "Comunicación y medios" pierde
*escritura*, "Comercio y otros países" pierde *política*. En 26 caracteres no
caben tres conceptos, y cada chip lleva tres porque así cubre tres cosas.

Se conservaron solo las 3 que salieron limpias:

| Antes | Ahora |
|---|---|
| Salud, cuidados y atención a pacientes | Salud y cuidar pacientes |
| Enseñanza, docencia y educación | Enseñanza y docencia |
| Psicología y comportamiento | Psicología y conducta |

Eso baja la lista a 679px y el scroll de 65px a 48px, con 24 de 25 chips
visibles. Igual cambia la señal que entra al prompt, así que se midió.

### El diseño, y por qué no el de siempre

Con 22 de 25 etiquetas idénticas, un A/B donde cada brazo conversa por su
cuenta gastaría el presupuesto midiendo qué chips marcó el alumno por azar.
Acá las 4 fijas se contestan **una sola vez** y los dos brazos salen de ahí,
difiriendo **solo en esas 3 cadenas**. Se agregó a Kevin como **control**: su
perfil no roza salud, educación ni psicología, así que sus dos brazos reciben
entradas idénticas.

### Resultado

| Grupo | n | Juez A-B-empate | Coherencia A-B | Top-1 igual |
|---|---:|---|---:|---|
| Marcaron una etiqueta cambiada | 7 | 1-5-1 | -0.71 | 3/7 |
| **Kevin (control, entrada idéntica)** | 1 | 1-0-0 | **+3.00** | **0/1** |

**El control disparó, y ese es el hallazgo.** Kevin recibió exactamente la
misma entrada en los dos brazos y aun así recibió Economía en uno y Contaduría
en el otro, con 3 puntos de diferencia de coherencia. El motivo: el diseño
iguala las respuestas FIJAS, pero las adaptativas se conversan por separado y
divergen solas (temperatura 0.5 en las preguntas, 0.9 en el alumno).

Con un control que se mueve así, **el 1-5-1 a favor de las cortas no se puede
leer como que las cortas sean mejores**, ni el 4 de 7 top-1 distintos como que
el cambio mueva algo. Lo que sí se puede decir:

**No hay evidencia de que acortar esas 3 etiquetas haya degradado nada.** Es lo
que se necesitaba para dejarlas, y es todo lo que este experimento sostiene.

### Qué queda dicho para el resto del repo

Un solo caso de control con entrada idéntica produjo un top-1 distinto. Eso
respalda, con una demostración directa y no con una estimación, el piso de
ruido que ya se venía advirtiendo (3 de 8 personas cambiaban solas entre
rondas en `adaptativas-desempate.md`). **Cualquier A/B de este sistema que no
lleve un brazo de control con entrada idéntica está sobreinterpretando sus
diferencias.**

---

## Brazo de control agregado (2026-08-23), SIN correr

El A/B de las etiquetas descubrió que este sistema devuelve resultados
distintos con entrada idéntica: un caso de control recibió Economía en una
corrida y Contaduría Pública en la otra, con 3 puntos de diferencia de
coherencia. Las adaptativas se conversan por separado y divergen solas.

Eso vuelve **no interpretables** los números de arriba: no tienen contra qué
compararse. El script ya lo dice al reportar datos viejos ("estos casos se
corrieron SIN brazo de control").

**El brazo ya está implementado**, corre el brazo B (banco nuevo) una segunda vez con el mismo banco y juzga ese par. El reporte lo imprime PRIMERO, antes
de cualquier resultado, porque es la vara con la que hay que leer el resto:

    0) PISO DE RUIDO - control: ... (n=N)
       Top-1 distinto pese a la entrada idéntica: X/N
       El juez prefirió una de las dos: X/N
       >> Ninguna diferencia de abajo que no supere esto se puede interpretar.

### Corrido (2026-08-23): el efecto es más chico que el ruido

Cuatro personas con el brazo de control. $0.1008.

| Medida | Control (B contra B, mismo banco) | Tratamiento (A contra B) |
|---|---:|---:|
| Top-1 distinto | 2/4 | 4/4 |
| Diferencia de coherencia | **1.25** | **0.50** |

La diferencia entre el banco viejo y el nuevo (0.50) es **menos de la mitad del
ruido** (1.25). Confirma, ahora con vara, lo que ya se decía arriba: **el banco
nuevo no está probado como mejor**. Sigue en pie por la otra razón, que no
depende del juez: representa temas que antes no se podían nombrar.
