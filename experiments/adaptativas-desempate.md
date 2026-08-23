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
