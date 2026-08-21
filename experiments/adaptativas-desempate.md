# ¿Las preguntas adaptativas desempatan entre carreras hermanas?

**Estado:** SIN EJECUTAR. Anotado el 2026-08-21, para después del commit a
producción.

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
