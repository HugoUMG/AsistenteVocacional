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

## Resultado 1: las adaptativas sí sirven, y sirven DENTRO del área

| | |
|---|---:|
| Juez ciego prefiere A (con adaptativas) | **10** de 19 |
| Prefiere B (sin adaptativas) | 5 |
| Empate | 4 |
| Coherencia media A | **4.63** |
| Coherencia media B | 4.11 |

Y la pregunta concreta del experimento:

| | |
|---|---:|
| Top-1 IGUAL con y sin adaptativas | 7 de 19 |
| Top-1 distinto, **dentro de la misma área** | **8 de 19** |
| Top-1 distinto, cambiando de área | 4 de 19 |

Casos de hermanas de verdad: Mynor (cocina y vende comida) recibe **Chef
Profesional** con adaptativas y **Administración de Hotelería y Turismo** sin
ellas. Rosa oscila entre Fisioterapia y Enfermería. Elmer entre Electrónica y
Ciencias y Sistemas.

**Esto contesta que sí:** las adaptativas eligen dentro del área, no solo el
área. La hipótesis pesimista del documento original queda sin sostén.

Confound a tener presente: el brazo A llega a la recomendación con más
conversación encima, y un juez puede premiar una lista que se explica con más
detalle. El prompt del juez le pide explícitamente no premiar la especificidad
por sí sola, pero no se puede descartar del todo.

## Resultado 2: el guard del desempate cumple la regla sin demostrar que desempata

Sobre el papel salió perfecto: **19 de 19 cierres con la #1 separada de la #2 por
al menos 20 puntos**, contra 12 de 32 (37%) empatados antes del guard. Y 8 de 19
sesiones necesitaron la pregunta extra.

Pero al mirar los números, no aguantan:

- La brecha al cierre es **siempre 23 o 25**. Nunca 40, nunca 60. Catorce veces
  23 y cinco veces 25, justo encima del umbral de 20.
- En el cierre la #1 vale **95 en las 8 sesiones** con pregunta extra, y la #2
  cae a **70-72**. Antes del cierre iban 85-92 contra 78-88.

O sea: cuando se le obliga a no cerrar empatado, el modelo **sube la #1 a 95 y
hunde la #2 a ~71**, aterrizando siempre apenas encima del mínimo. Eso es
satisfacer la restricción, no reportar un juicio que se resolvió.

En 6 de las 8 sesiones la identidad de la #1 sí cambió en el paso final, lo que
podría leerse como que la pregunta extra discriminó. Pero con el #2 aterrizando
siempre en la misma franja, la lectura económica es que el modelo reordena para
cumplir, no que haya aprendido algo.

**Consecuencia práctica:** el guard no hace daño (una pregunta más en el 42% de
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
