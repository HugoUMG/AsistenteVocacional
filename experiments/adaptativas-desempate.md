# ¿Las preguntas adaptativas desempatan entre carreras hermanas?

**Estado:** EJECUTADO el 2026-08-23 con el diseño de personas + juez ciego.
Resultado abajo, en "La ejecución". Resumen: **las adaptativas sí eligen dentro
del área y sí producen listas más coherentes**, pero **el guard del desempate
produce números que cumplen la regla, no un desempate demostrado**.

## De dónde sale

De una observación de uso: las adaptativas siempre giran sobre los mismos dos
ejes, "seguir reglas o improvisar" y "liderar o colaborar", cambiando solo la
redacción.

No es capricho del modelo, es el diseño. Las 4 preguntas fijas ya cubren
intereses, entorno y motivaciones (`preguntas.COBERTURA_INICIAL`), el prompt
obliga a dirigir cada adaptativa a una dimensión PENDIENTE, y quedan exactamente
cuatro: personalidad, habilidades, valores y estilo_cognitivo. Con
`MIN_ADAPTATIVAS = 4`, siempre son esas cuatro y casi en el mismo orden. Además
el prompt prefiere sí/no u opción de 2 a 4, o sea dicotomías.

## La pregunta

Todo lo medido hasta hoy dice que el sistema **acierta el área**. Lo que nadie ha
medido es si las adaptativas sirven para **elegir dentro del área**, entre
carreras de pensum parecido.

Hay una señal en contra, de una sola corrida (2026-08-21, verificación en el
navegador): un perfil de 26 años que dijo "liderar y tomar las decisiones" y cuya
meta declarada era su propio restaurante recibió como top-1 **Chef Profesional e
Internacional**, por encima de **Artes Culinarias y Negocios Gastronómicos**, que
es la que en su perfil dice literalmente "espíritu emprendedor para montar un
negocio propio". n=1 y discutible (también dijo "con las manos" y "en una
cocina", que empujan a Chef), pero es justo el caso que interesa.

## Diseño propuesto

Dos brazos con el MISMO perfil y las mismas 4 preguntas fijas:

- **A:** las 4 adaptativas (producción).
- **B:** cero adaptativas, se va directo a la recomendación.

Medida principal: **cuántas veces cambia el top-1 dentro de la misma área**.
Cambiar de área es otra cosa (eso ya se sabe que lo mueven) y hay que contarlo
aparte.

Perfiles: los que tengan carreras hermanas de verdad en el catálogo (gastronomía
tiene tres, sistemas tiene cinco, jurídicas tiene varias). Ahí es donde la
pregunta tiene sentido.

Costo estimado: unas 60 llamadas, reusando el arnés de
`experimento_edad_grado.py`.

## Qué se hace con el resultado

- Si las adaptativas SÍ desempatan: no tocar nada, y el hallazgo justifica el
  largo del chat.
- Si NO desempatan: la palanca no es el prompt, es el catálogo. Ninguna pregunta
  puede separar dos carreras cuyos perfiles digan lo mismo. La conclusión
  práctica sería acortar el chat o invertir el trabajo en que el `perfil` y el
  `sello` de cada carrera hermana nombren su diferencia real.

## Lo que NO se hace en este experimento

Variar el estilo de las preguntas (más escenarios, prohibir ejes repetidos, 3 o
4 opciones en vez de 2). Es tentador, pero es otro experimento: la regla de
cobertura que produce esta repetición es la misma que subió el acierto de 7/10 a
10/10 ([cobertura-dimensiones.md](cobertura-dimensiones.md)), y ya hubo un
intento que sonaba mejor y midió peor
([microexperiencias.md](microexperiencias.md)). Primero hay que saber si las
adaptativas aportan al desempate; recién después tiene sentido rediseñarlas.

---

## Actualización 2026-08-23: el guard del desempate ya existe (el experimento sigue pendiente)

Revisando el flujo salió que el prompt **ya pedía** no cerrar con el top parejo
(`SYSTEM` de `preguntas.py`: terminado=true solo si la #1 supera a la #2 por al
menos 20 puntos), pero **el código nunca lo verificaba**. El único guard era:

```python
corta_antes_de_tiempo = paso.terminado and pendientes and hechas < MAX_ADAPTATIVAS
```

Solo miraba dimensiones pendientes. Un `terminado=true` con 78 contra 78 pasaba
tal cual. O sea: la cobertura tenía guard más reintento, y el desempate no tenía
nada, aunque las dos reglas viven en el mismo prompt.

### Cuánto pasaba

Medido sobre los 32 cierres reales de `filtro-catalogo-ab.md`, sin gastar cuota
(los rankings ya estaban guardados):

**12 de 32 cierres (37%) tenían el top empatado** por debajo del margen de 20.
Y las parejas son justo las carreras hermanas de las que trata este experimento:

| Diferencia | Empate en el cierre |
|---:|---|
| 3 | Téc. Univ. en Laboratorio Clínico vs Téc. Univ. en Radiología |
| 3 | Ing. en Electrónica vs Lic. en Administración de Telecomunicaciones |
| 6 | Ing. en Ciencias y Sistemas vs Téc. Univ. en Desarrollo de Software |
| 7 | Lic. en Economía vs Economía Empresarial |
| 7 | Ing. en Ciencias y Sistemas vs Ingeniería Industrial |
| 7 | PEM en Comunicación y Lenguaje vs PEM en Pedagogía y Psicología |

Más de un tercio de los chats se cerraban con el top-1 decidido a cara o cruz.

### Qué se cambió

`MARGEN_DESEMPATE = 20` (una sola constante, que ahora alimenta el prompt Y el
guard, para que no se desincronicen), `empatado(ranking)` y el guard extendido:

```python
corta_antes_de_tiempo = (
    paso.terminado and (pendientes or empatado(paso.ranking))
    and hechas < MAX_ADAPTATIVAS
)
```

En el reintento por empate el recordatorio le nombra al modelo **las dos
carreras empatadas** y le pide una pregunta que las separe, sin nombrárselas al
estudiante. Self-check en `python -m app.preguntas`: verifica que el reintento
dispare con el top parejo, que no dispare con el top resuelto, y que no dispare
cuando el modelo no está intentando cerrar.

### Lo que este cambio NO resuelve

Fuerza una pregunta más, no garantiza que esa pregunta desempate. Cuando entra,
ya no quedan dimensiones prioritarias pendientes, así que la pregunta extra
puede volver a subir a las dos por igual: es exactamente la hipótesis que este
experimento sigue sin medir. El guard cierra el hueco entre lo que el prompt
pide y lo que el código exige; **el experimento de abajo sigue sin ejecutar** y
ahora tiene una medida más que mirar: de esos 37% de cierres empatados, ¿cuántos
desempata la pregunta extra?

Costo: la pregunta extra es una llamada de `next-question` más (~$0.0008 con
caché caliente) en el 37% de las sesiones. Despreciable frente al tiempo que
agrega al chat, que es lo que sí habría que vigilar.


---

# La ejecución (2026-08-23)

Script: `backend/experimento_desempate.py` · 8 personas · 19 sesiones · ~$0.20.

## Por qué no se usó el diseño de arriba

El diseño original puntuaba con `claves`. Esa métrica no puede contestar esta
pregunta: si el brazo sin adaptativas propone una carrera hermana igual de
sensata, `claves` decide por subcadena, no por si tiene lógica. Se usó el diseño
de [banco-de-opciones.md](banco-de-opciones.md): **personas** descritas sin
carrera en mente y un **juez ciego** que puntúa coherencia y además clasifica si
los dos top-1 son del mismo campo.

Brazos: **A** = producción (4 fijas + adaptativas + recomendación).
**B** = 4 fijas y directo a la recomendación, cero adaptativas. Las respuestas
fijas se contestan UNA vez y se comparten, así lo único que cambia son las
adaptativas.

## Resultado 1: la dirección se sostiene, la significancia NO

Diseño balanceado, **4 réplicas por cada una de las 8 personas, n=32**.

| | A (con adaptativas) | B (sin adaptativas) |
|---|---:|---:|
| Juez ciego prefiere | **17** | 9 |
| Empate | 6 | |
| Coherencia media (1-5) | **4.56** | 4.06 |

**Sign test sobre las 26 decisivas: p = 0.17.** No es significativo. La primera
lectura con n=19 (10-5-4) parecía más fuerte de lo que es; al balancear y subir
a n=32 la ventaja se mantiene en dirección pero no alcanza. **No se puede
afirmar que las adaptativas mejoren la coherencia en general.**

### Pero el efecto no es parejo, está concentrado

Con 4 réplicas por persona se ve algo que el agregado esconde:

| Persona | Juez A-B-empate | Coherencia A | Coherencia B |
|---|---|---:|---:|
| **Kevin** | **4-0-0** | 4.50 | 2.75 |
| **Ixchel** | **4-0-0** | 5.00 | 3.25 |
| **Mynor** | **4-0-0** | 5.00 | 3.00 |
| Wendy | 2-2-0 | 4.50 | 4.50 |
| Elmer | 1-1-2 | 4.75 | 4.75 |
| Diego | 1-1-2 | 4.75 | 4.75 |
| Rosa | 1-2-1 | 4.00 | 4.50 |
| **Katherine** | **0-3-1** | 4.00 | 5.00 |

En 3 de 8 personas el brazo con adaptativas gana **las 4 réplicas**, con brechas
de coherencia grandes (hasta 2 puntos). En 1 pierde 3 de 4. En las otras 4 no
hay diferencia.

**Hipótesis, no conclusión:** las adaptativas pesan cuando las respuestas fijas
dejan el perfil ambiguo entre áreas (Kevin entre economía y derecho, Ixchel
entre educación y social, Mynor entre cocina y negocio) y no pesan cuando las
fijas ya lo fijaron (Diego no cambió de top-1 en ninguna de las 4; Katherine
salió a sistemas desde el arranque).

**Se probó y FALLÓ.** Ver "La hipótesis de la ambigüedad" al final.

### ¿Eligen DENTRO del área?

| | |
|---|---:|
| Top-1 IGUAL con y sin adaptativas | 12 de 32 |
| Top-1 distinto, **dentro de la misma área** | **11 de 32** |
| Top-1 distinto, cambiando de área | 9 de 32 |

Un tercio de las sesiones cambia de carrera sin cambiar de campo. Wendy cambia
dentro del área en las 4 réplicas. Ese es el mecanismo que el documento quería
ver, y existe; lo que no está demostrado es que el cambio sea para mejor.

Confound a tener presente: el brazo A llega con más conversación encima y un
juez puede premiar una lista que se explica con más detalle. El prompt del juez
pide no premiar la especificidad sola, pero no lo descarta.

## Resultado 2: el guard del desempate cumple la regla sin demostrar que desempata

Sobre el papel salió perfecto: **32 de 32 cierres con la #1 separada de la #2 por
al menos 20 puntos**, contra 12 de 32 (37%) empatados antes del guard. Y 12 de 32
sesiones necesitaron la pregunta extra.

Pero al mirar los números, no aguantan:

- La brecha al cierre, en las 32 sesiones: **20 dos veces, 23 diecisiete veces,
  25 doce veces, 30 una vez**. O sea **31 de 32 aterrizan entre 20 y 25**, justo
  encima del umbral. Nunca 40, nunca 60.
- En el cierre la #1 vale 95 y la #2 cae a 70-72. Antes del cierre iban 85-92
  contra 78-88.

O sea: cuando se le obliga a no cerrar empatado, el modelo **sube la #1 a 95 y
hunde la #2 a ~71**, aterrizando siempre apenas encima del mínimo. Eso es
satisfacer la restricción, no reportar un juicio que se resolvió.

En 6 de las primeras 8 sesiones con pregunta extra la identidad de la #1 sí
cambió en el paso final, lo que
podría leerse como que la pregunta extra discriminó. Pero con el #2 aterrizando
siempre en la misma franja, la lectura económica es que el modelo reordena para
cumplir, no que haya aprendido algo.

**Consecuencia práctica:** el guard no hace daño (una pregunta más en el 38% de
las sesiones, ~$0.0008) y garantiza que la UI no muestre un top empatado. Pero
**no se puede afirmar en la tesis que "el chat desempata"**. Lo que se puede
afirmar es lo del Resultado 1, que no depende del guard: las adaptativas cambian
la elección dentro del área.

## Cómo se sabría de verdad

El número de afinidad lo produce el mismo modelo que decide cerrar, así que
nunca va a ser evidencia independiente de nada. Haría falta un criterio externo:
que la brecha se mida contra algo que el modelo no controle, o que una persona
juzgue si la pregunta extra separó a las dos carreras. Es el mismo bloqueante de
[docs/estudio-con-estudiantes.md](../docs/estudio-con-estudiantes.md).

## Un bug del arnés, anotado

La reanudación comparaba el entero de la ronda contra el string `"R1"` guardado
en el archivo, así que al retomar volvía a correr todo y duplicaba casos. Se
detectó porque aparecieron 19 casos donde debían ir 16. Los duplicados son
corridas independientes válidas y se conservaron como réplicas extra (Wendy,
Elmer, Rosa, Kevin e Ixchel tienen 3; Diego 2; Mynor y Katherine 1). Arreglado
con `_etiquetas()`, que es ahora el único lugar donde se decide el nombre de una
ronda, más un self-check.


---

# La hipótesis de la ambigüedad: probada y descartada (2026-08-23)

Script: `backend/experimento_ambiguedad.py` · $0.14.

## Parte A, exploratoria: clasificar a ciegas los 32 casos ya corridos

Un clasificador que ve **solo las 4 respuestas fijas** (no la persona, no las
adaptativas, no las recomendaciones, no quién ganó) dice si apuntan a un campo o
a varios. Cuesta $0.006 porque reusa datos ya pagados.

| Fijas | n | Juez A-B-emp | Coherencia A-B | Top-1 cambia |
|---|---:|---|---:|---|
| AMBIGUAS | 22 | 13-7-2 | +0.64 | 16/22 (73%) |
| CLARAS | 10 | 4-2-4 | +0.20 | 4/10 (40%) |

Va en la dirección de la hipótesis. **Pero no confirma nada**: la hipótesis salió
de estos mismos datos, así que encontrarla acá era lo esperable. Sirvió para ver
que el clasificador separa algo, y para una pista honesta en contra: marcó a
Katherine como ambigua en las 4 réplicas, y Katherine es justo la persona donde
el brazo SIN adaptativas ganó 3 de 4.

## Parte B, confirmatoria: personas etiquetadas ANTES de correr

Seis personas nuevas, tres diseñadas ambiguas y tres claras, con la etiqueta
puesta en el código antes de ver un solo resultado (un self-check lo verifica).
Dos réplicas cada una, n=12.

**Predicción: la ventaja del brazo con adaptativas debía ser MAYOR en las
ambiguas.**

| Predichas | n | Juez A-B-emp | Coherencia A-B | Top-1 cambia |
|---|---:|---|---:|---|
| AMBIGUAS | 6 | 4-2-0 | **+0.50** | 4/6 |
| CLARAS | 6 | 4-1-1 | **+1.17** | 4/6 |

**La predicción falla, y se invierte.** La ventaja fue más del doble en las
personas cuyo perfil ya estaba claro, y el top-1 cambió en la misma proporción
en los dos grupos (4 de 6). La hipótesis de la ambigüedad **se descarta**.

Con n=6 por grupo tampoco se puede afirmar lo contrario. Lo que queda dicho es
que la explicación bonita que salió del análisis por persona no sobrevivió a una
predicción hecha de antemano, y por eso no debe entrar en la tesis.

Nota de diseño: las "claras" no salieron tan claras como se pretendía. Fredy
osciló entre Mecánica, Civil y Mecánica Industrial, y Julio saltó de Sistemas a
Contaduría. Escribir un perfil que fije el área de verdad es más difícil de lo
que parece, y eso también debilita la prueba.

## Lo que sí queda, sumando todo el corpus

Los 32 casos del A/B más los 12 de la parte B comparten brazos y juez, así que
se pueden sumar:

| | |
|---|---:|
| n | **44** |
| Juez ciego prefiere A (con adaptativas) | **25** |
| Prefiere B (sin adaptativas) | 12 |
| Empate | 7 |
| **Sign test sobre las 37 decisivas** | **p = 0.047** |
| Coherencia media A - B | **+0.59** |

Cruza el umbral convencional, **apenas y sobre datos agrupados**. Las dos
muestras van en la misma dirección por separado (32 casos: 17-9-6; 12 casos:
8-3-1), lo que ayuda, pero agrupar después de mirar no es lo mismo que haberlo
planeado así. Léase como evidencia moderada, no como resultado fuerte.

**Afirmación defendible para la tesis:** las 4 preguntas adaptativas cambian la
carrera recomendada en cerca de dos tercios de los casos, un tercio de las veces
dentro del mismo campo, y las listas que producen son juzgadas algo más
coherentes con el perfil del estudiante (p = 0.047, n = 44, juez ciego).

**Lo que sigue sin poder afirmarse:** que el chat desempata (el guard produce
números que cumplen la regla), y que las adaptativas sirvan especialmente en
perfiles ambiguos (probado y descartado).

---

## Brazo de control agregado (2026-08-23), SIN correr

El A/B de las etiquetas descubrió que este sistema devuelve resultados
distintos con entrada idéntica: un caso de control recibió Economía en una
corrida y Contaduría Pública en la otra, con 3 puntos de diferencia de
coherencia. Las adaptativas se conversan por separado y divergen solas.

Eso vuelve **no interpretables** los números de arriba: no tienen contra qué
compararse. El script ya lo dice al reportar datos viejos ("estos casos se
corrieron SIN brazo de control").

**El brazo ya está implementado**, corre el brazo A una segunda vez con la misma entrada y juzga ese par con el mismo juez ciego. El reporte lo imprime PRIMERO, antes
de cualquier resultado, porque es la vara con la que hay que leer el resto:

    0) PISO DE RUIDO - control: ... (n=N)
       Top-1 distinto pese a la entrada idéntica: X/N
       El juez prefirió una de las dos: X/N
       >> Ninguna diferencia de abajo que no supere esto se puede interpretar.

**Falta correrlo**, y con eso volver a leer las conclusiones de arriba. Costo
estimado: unos $0.15 una ronda de 8 casos, o $0.60 rehacer los 32.
