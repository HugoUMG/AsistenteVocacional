# Pruebas de campo con alumnos reales (24 al 27 de agosto de 2026)

**No es un A/B.** Son cuatro sesiones observacionales en producción, una por
grupo, sin brazo de control. Aquí se reporta qué pasó y qué calificó la
psicóloga; no se afirma que ningún cambio mejore o empeore nada.

La primera sesión ya tiene su análisis detallado (defectos, calidad y costo) en
[prueba-alumnos-2026-08-24.md](prueba-alumnos-2026-08-24.md). Este documento
junta las cuatro.

**Fuente:** CSV del registro de `/admin` (Historial de alumnos), descargado el
2026-11-05. El archivo trae nombres y correos de menores de edad y **no entra al
repo** (ver [docs/estudio-con-estudiantes.md](../docs/estudio-con-estudiantes.md)).
Aquí solo van conteos y los comentarios de la psicóloga, sin datos del alumno.

**Segunda fuente:** la constancia firmada por la psicóloga que acompañó la
aplicación y revisó los resultados: Lcda. Dunia Fabiola Ixpertay Cajas,
psicóloga clínica, colegiado 7949, Centro Psicológico Integral Trascender.
Totonicapán, 8 de septiembre de 2026. El original lo tiene el autor; no entra al
repo porque trae datos de contacto personales.

---

## 1. Las cuatro sesiones

**Dónde:** Colegio Evangélico Guatemala, jornada vespertina, departamento de
Totonicapán, en cuatro secciones de diversificado (según la constancia).

| Fecha | Grupo (mayoría) | Evaluaciones | Cuentas | Ventana (hora local) | Hicieron Holland |
|---|---|---|---|---|---|
| 24/8 | Quinto bachillerato, medicina o computación con diplomado en medicina | 18 | 17 | 13:25 a 13:38 (12 min 39 s) | 18 |
| 25/8 | Quinto bachillerato, computación, ciencias jurídicas, ciencias y letras | 19 | 18 | 13:22 a 13:39 (16 min 23 s) | 17 |
| 26/8 | Sexto perito contador, varios con orientación en computación | 11 | 11 | 13:26 a 13:53 (27 min) | 11 |
| 27/8 | Quinto bachillerato, medicina | 17 | 17 | 13:29 a 13:41 (11 min 34 s) | 17 |
| **Total** | | **65** | **63** | | **63** |

- Edades de 16 a 24 años; 38 de 65 tienen 17.
- Departamento elegido en el mapa: "Ambos" 38, Quetzaltenango 17, Totonicapán 10.
- Motivo del test: "saber qué estudiar" 37, "conocer más opciones" 16,
  "confirmar lo que ya tenía pensado" 12.
- La constancia llama al grupo del 25/8 "bachillerato con orientación en
  ciencias jurídicas"; en el registro, varios declaran computación o computación
  con diplomado en derecho.
- **Los 65 completaron el proceso y recibieron su resultado, sin abandonos.** Lo
  dice la constancia, de quien estuvo presente. El registro solo no alcanza para
  afirmarlo: la fila se guarda cuando el alumno pide su resultado
  (`obtenerCarreras()` en `frontend/src/Chat.jsx`), así que no ve a quien cierra
  el chat antes.
- Las sesiones del 25 al 27 son posteriores al arreglo del conteo de adaptativas
  y de la cobertura por sesión (commit `4ba9dd3`, 24/8 a las 22:30). El CSV no
  trae cuántas adaptativas contestó cada alumno, así que con esta fuente no se
  puede verificar que ya lleguen a 4.

La constancia habla de 65 estudiantes; el registro tiene 65 evaluaciones de 63
cuentas. Con estas dos fuentes no se puede saber si dos alumnos compartieron
cuenta o si son dos alumnos que repitieron.

Dos cuentas repitieron. La del 24/8 ya está explicada en
[prueba-alumnos-2026-08-24.md](prueba-alumnos-2026-08-24.md) §3. La del 25/8
cambió de departamento entre una corrida y otra (Totonicapán y luego
Quetzaltenango) y el top-3 cambió con él, de Abogacía, Contaduría y Psicología
Industrial a Ciencias Jurídicas, Criminología y Relaciones Internacionales. El
filtro por departamento se comportó como debía.

Una de las 19 del 25/8 corrió en la cuenta del desarrollador, con tres tests de
Holland. No está marcada como descartada, así que entra al conteo. Si fue una
prueba propia, hay que marcarla en `/admin` y el total baja a 64.

---

## 2. Juicio de la psicóloga

La psicóloga calificó desde `/admin` (Acertó, Acertó en parte, No acertó, más un
comentario). Ver [docs/api.md](../docs/api.md), `POST /api/admin/juicio`.

**Su criterio, según la constancia:** si la **carrera principal** recomendada (el
top-1) es pertinente al perfil del estudiante. No califica el top-3 completo.

| Juicio | Evaluaciones |
|---|---|
| Acertó | **9** |
| Acertó en parte | 0 |
| No acertó | **1** |
| Sin calificar | 55 |

**9 de 10 calificadas acertaron (90%; IC 95% de Wilson: 60% a 98%).**

Por sesión:

| Fecha | Calificadas | Acertó | No acertó |
|---|---|---|---|
| 24/8 | 4 de 18 | 4 | 0 |
| 25/8 | 0 de 19 | | |
| 26/8 | 0 de 11 | | |
| 27/8 | 6 de 17 | 5 | 1 |

Sus comentarios, tal cual los dejó (los que tienen texto):

- "si"
- "si, es correcto"
- "correcto, ayuda en la comprensión"
- "Si, y es claro, ayuda en la elaboración del informe"
- "Si, y si puede apoyar en la realización de informe"
- "si, con las respuestas precisas, y cortas da muy buen resultado"
- "las ideas de la evaluada son claras y precisas, ayuda obtener resultados certeros"
- "excelente, si acertó"
- En el único **No acertó**: "evaluar con mayor precisión las respuestas de la
  estudiante y verificar o contrastar con el test de Holland"

**El caso que no acertó** (constancia): la estudiante marcó muchísimos temas de
interés, y eso impidió que el sistema distinguiera una preferencia real; la
recomendación salió genérica. La psicóloga recomendó limitar cuántos temas se
pueden marcar, y se aplicó en el commit `0a02dc6` (2026-09-03): tope de 5 temas
en los chips de gustos. Las 65 evaluaciones de agosto son anteriores al cambio,
así que su efecto todavía no se midió con alumnos.

**Un caso que destaca** (constancia): a un estudiante de bachillerato con
orientación en medicina el sistema le recomendó un profesorado en educación
artística, apartándose de lo que estudia, y ella considera acertada esa
recomendación. Es la evaluación del 27/8 con Holland EAS.

**La utilidad, en palabras de la constancia:** le encuentra valor en dos usos.

1. Como recomendador vocacional por sí solo, "sin necesidad de aplicar varias
   pruebas psicométricas al estudiante para llegar a una sugerencia de carrera".
2. Como insumo para el informe de orientación del estudiante, "trabajo que hoy
   consume una parte considerable del tiempo profesional". Tres de sus
   comentarios en el registro dicen lo mismo.

Dos de sus comentarios también atan el acierto a cómo contesta el alumno:
respuestas claras, precisas y cortas dan mejor resultado. Es la otra cara del
caso que no acertó.

---

## 3. Qué se puede afirmar y qué no

**Sí:**
- En 10 evaluaciones de alumnos reales, una psicóloga clínica colegiada
  consideró pertinente la carrera principal recomendada en 9, y lo dejó por
  escrito en una constancia firmada.
- Para ella, la plataforma sirve como recomendador por sí sola y como insumo
  para el informe de orientación.
- En cuatro sesiones con grupos completos (11 a 19 alumnos a la vez), los 65
  estudiantes terminaron y recibieron su resultado.
- Su observación del caso fallido ya produjo un cambio en el producto (tope de 5
  temas).

**No, todavía:**
- **Lo dice la propia constancia:** es su criterio profesional sobre los casos
  revisados, se refiere a las tres orientaciones que participaron y "no
  constituye una validación estadística del sistema ni una certificación de su
  exactitud". Extenderlo a otras orientaciones pide más aplicaciones.
- **n = 10, el 15% de las 65.** El intervalo va de 60% a 98%: alcanza para decir
  que el acuerdo es alto, no para dar una cifra fina.
- **Las 10 calificadas en el registro son de los dos grupos de medicina.** La
  constancia habla de las tres orientaciones, pero no hay ningún juicio
  registrado para computación, ciencias jurídicas ni perito contador, que son
  justo los grupos donde el top-3 se aleja del área de salud (§4).
- **Ni el registro ni la constancia dicen cómo se eligieron esas 10 ni si fue a
  ciegas.** La
  pantalla de `/admin` muestra el recorrido completo junto con la
  recomendación, y [estudio-con-estudiantes.md](../docs/estudio-con-estudiantes.md)
  §4 advierte que así el juicio no es ciego salvo que el protocolo lo resuelva.
- **No hay medida de satisfacción del alumno.** La columna "¿Le gustó?" del CSV
  es `gusto_grado`: pregunta si le gusta la carrera de diversificado que ya
  estudia, no si le gustó Orienta. El 👍/👎 del alumno se reemplazó por el juicio
  del profesional (commit `42fda51`).

---

## 4. Lo que deja ver el top-3 (descriptivo)

**La recomendación sigue al bachillerato.** Enfermería entra al top-3 en 13 de
18 (24/8) y 10 de 17 (27/8) en los grupos de medicina, y solo en 2 de 19 (25/8)
y 1 de 11 (26/8) en los otros. En el grupo de computación y jurídicas dominan
Abogacía e Informática; en el de perito contador, Administración, Informática y
Contaduría. Eso sostiene la hipótesis de
[prueba-alumnos-2026-08-24.md](prueba-alumnos-2026-08-24.md) §4 (el
bachillerato pesa), pero en grupos tan homogéneos no se puede separar del
interés real del alumno.

**Contrapeso:** los 5 alumnos que dijeron que su carrera actual les gusta "no
mucho" (4) o "nada" (1) recibieron un top-3 fuera de esa línea. Ninguno de los
tres de perito contador recibió Contaduría, el de ciencias jurídicas no recibió
Derecho y el de computación no recibió Informática. Con n = 5 es descriptivo,
pero apunta a que el sistema no repite el bachillerato cuando el alumno dice que
no le gusta. El caso que la psicóloga destaca en su constancia (profesorado en
educación artística para un estudiante de medicina, §2) va en la misma línea, y
ese sí tiene juicio externo.

---

## 5. Pendientes

1. Que la psicóloga califique las 55 restantes, empezando por las del 25/8 y el
   26/8, que no tienen ninguna.
2. Anotar cómo se eligieron las 10 calificadas y si fueron a ciegas.
3. Confirmar si la evaluación del 25/8 en la cuenta del desarrollador fue una
   prueba propia y, si es así, marcarla como descartada.
4. Si se quiere medir la satisfacción del alumno, agregar una pregunta al final
   del recorrido. Hoy no existe.
5. En la próxima aplicación, ver si el tope de 5 temas (`0a02dc6`) corrige los
   casos de recomendación genérica. Todas las evaluaciones de agosto son
   anteriores al cambio.
