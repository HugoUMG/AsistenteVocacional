# Holland antes del chat: ¿siguen haciendo falta las 4 preguntas fijas?

**Fecha:** 2026-08-16 · **Estado:** las preguntas fijas **se quedan** en el modo
"Holland → chat". El hallazgo importante es otro y no era la pregunta original:
**el bloque de Holland en el prompt no pesa en la recomendación.**

Ámbito: catálogo de Quetzaltenango + Totonicapán (202 registros carrera-sede),
`gemini-3.1-flash-lite`. Banco de pruebas: `backend/experimento_holland.py`.

---

## 1. Qué se probó

El modo que se quiere construir es el tercero de la app: el alumno responde el
test de Holland y **luego** conversa, y el chat arranca con sus intereses ya
medidos para gastar sus turnos en averiguar qué carrera concreta del sector
encaja, en vez de descubrir el sector.

La pregunta que decide el diseño: con Holland de entrada, ¿las 4 preguntas fijas
(impacto/estilo/entorno/gustos) siguen aportando o estorban?

| | A — solo adaptativas | B — fijas + adaptativas |
|---|---|---|
| Preguntas fijas | ninguna | las 4 de producción |
| Dimensiones cubiertas al arrancar | intereses (por Holland) | intereses, entorno, motivaciones |
| Lo que persigue el chat | las otras 6 | las 4 prioritarias de producción |

Los dos brazos reciben el **mismo** bloque de Holland en el prompt de
`next-question` y en `recomendar()`. La única variable son las fijas.

## 2. Metodología, y el control que le faltó al experimento del CIP

Perfiles: **Dulce** y **Melany**, los dos casos de
[psicometrico-en-chat.md](psicometrico-en-chat.md) donde quitar las fijas hizo
daño medible. Mismo `contexto` y mismo `guion`, para poder contrastar con
aquellas transcripciones.

**La hoja de Holland NO la responde Gemini.** Es la lección de
[cip-en-recomendacion.md](cip-en-recomendacion.md) §6: allá el modelo contestó
150 ítems haciéndose pasar por alguien, el perfil no representaba a la persona en
4 de 10 casos, y el A/B terminó midiendo "¿ayuda un instrumento mal respondido?".

Acá cada perfil tiene un nivel real de interés 1-5 por área RIASEC y cada ítem se
contesta con el nivel de **su** área (el dato `area` viene en el banco oficial de
O*NET) más ±1 de ruido determinista. La califica la API de O*NET. `--hojas`
verifica que el código devuelto contenga el área dominante que se pretendía; si
no, la hoja no representa a la persona y el A/B no se corre.

| Perfil | Niveles reales | Código que devolvió O*NET | Puntajes |
|---|---|---|---|
| Dulce | A5 S5 C3 R2 I2 E2 | **ASC** ✅ | A=39 S=38 C=19 R=12 I=10 E=10 |
| Melany | C5 E4 I3 R2 S2 A1 | **CEI** ✅ | C=36 E=29 I=16 R=9 S=9 A=3 |

Las dos hojas son **honestas a propósito**: se podría simular a una Dulce que
esconde el arte también en el test, pero eso sería amañar el brazo A para que
falle. A Holland se le da su mejor caso.

## 3. Antes de correr nada: el recorte al sector se cayó solo

El diseño original recortaba el catálogo al sector de Holland (el texto de las 3
áreas altas + las ocupaciones afines entrando a `filtro.py` como una respuesta
más). Medido sobre el catálogo real, **sin gastar una sola llamada de Gemini**:

| Estado del pre-filtro | Dulce: ¿sobrevive lo suyo? | Melany: ¿sobrevive Contaduría? |
|---|---|---|
| Tras las 4 fijas, producción hoy | **3** (Diseño Gráfico, Publicidad c/ Diseño Gráfico, …) | no |
| Tras las 4 fijas + recorte Holland | **1** (una Pedagogía que casa por "Diseño Curricular") | no |
| Turno 1, producción hoy | 1 | **sí** |
| Turno 1 + recorte Holland | 1 | **no** |

El recorte **borra justo las carreras correctas**, y eso que A=39 es el área más
alta de Dulce. La causa es concreta: las ocupaciones que O*NET devuelve para un
perfil A+S son todas de docencia ("Maestros de Escuela Primaria", "Instructores
de Educación Básica…"), y el solapamiento de palabras arrastra el catálogo hacia
pedagogía.

Con el recorte encendido los dos brazos pierden la carrera correcta por igual, y
el A/B mediría el filtro en vez de las preguntas fijas — el mismo error que dejó
al experimento del CIP sin probar su hipótesis. **Se corrió con el recorte
apagado.** El código queda tras `--sector` y `--recorte` reproduce esta tabla.

## 4. Resultados

Dulce se corrió **3 veces** por brazo: la primera corrida dio un resultado
llamativo y a temperatura 0.9 una corrida no es un dato.

| Corrida | A — solo adaptativas | B — fijas + adaptativas |
|---|---|---|
| 1 | **Comunicación y Diseño 45%** ✅ | Enfermería 35% |
| 2 | Enfermería 45% | Psicología 45% |
| 3 | Fisioterapia 35% | Enfermería 45% |

| Métrica (Dulce, 3 corridas) | A | B |
|---|---|---|
| Lo suyo (arte/comunicación) en **top-1** | 1/3 | 0/3 |
| Lo suyo en **top-3** | 1/3 | **3/3** |
| Preguntas adaptativas | 6, 6, 6 | 4, 4, 4 |
| Tokens | 80 790 · 81 747 · 82 198 | 57 745 · 59 776 · 60 701 |
| Alertas de contradicción | 2, 3, 1 | 4, 0, 1 |
| Confianza | 85%, 85%, 85% | 85%, 85%, 85% |

**Melany** (1 corrida por brazo): **empate exacto**. Los dos brazos cerraron en
`Contaduría Pública y Auditoría 45%` con **95% de confianza**. Donde Holland
coincide con lo que el chat ya averiguaría, no aporta nada medible.

## 5. Lectura

### 5.1 Las preguntas fijas no son lo que decide, pero se quedan

1/3 contra 0/3 en top-1 es ruido: **la varianza entre corridas del mismo brazo es
mayor que la varianza entre brazos**. La primera corrida, leída sola, decía que
quitar las fijas rescataba a Dulce; repetida dos veces, no.

Lo que sí es estable en las 3 corridas y decide el asunto:

- **Con fijas, la opción creativa se queda en el top-3 siempre (3/3 contra
  1/3).** No gana, pero el alumno la ve en su dashboard. Sin fijas, en 2 de 3
  corridas el top-3 entero fue de salud.
- **Con fijas es más barato y más corto: 4 preguntas contra 6, y ~38% menos
  tokens.** Al revés de la intuición: quitar las fijas no ahorra, cuesta, porque
  entonces el chat tiene que cubrir entorno y motivaciones por su cuenta y las
  fijas no gastaban IA.

Es el mismo veredicto de [psicometrico-en-chat.md](psicometrico-en-chat.md), por
un camino distinto y con Holland (que mide el **mismo** constructo que los chips)
en vez del psicométrico.

### 5.2 El hallazgo grande: el bloque de Holland no pesa en la recomendación

En 5 de 6 corridas de Dulce el top-1 fue de salud, **con A=39 en el prompt** —
su área más alta, medida por un instrumento oficial, presente en los dos brazos y
en todas las llamadas.

La corrida 1 del brazo B lo muestra sin ambigüedad. Los chips funcionaron
perfecto: en la fija de entorno escribió *"si me dejaran elegir sin que nadie me
viera, me iría de fijo a un estudio creativo"*. El chat detectó la tensión **4
veces** y la nota de confianza dice *"dividir tu corazón entre el servicio en
salud y tu gran talento creativo digital"*. Revelación: perfecta. Detección:
perfecta. Recomendación: Enfermería.

**Un bloque de texto en el prompt es contexto, no peso.** Lo que decide sigue
siendo la conversación; cuando la alumna declara una prioridad ("salud, eso es lo
principal"), el modelo le hace caso por encima de lo medido. Poner el resultado
de Holland "de referencia corta" personaliza la conversación —y eso se nota en
las aperturas— pero **no vuelve a Holland un motor de la recomendación**, que era
la decisión abierta #1 de [docs/holland.md](../docs/holland.md).

### 5.3 Dos cosas que ninguno de los dos brazos hizo

- **Nadie confrontó a Melany con lo de "leyes".** Lo mencionó en los dos brazos
  (brazo A: *"la ley es lo que manda y eso es lo que quiero estudiar"*) y el
  brazo A **ni siquiera levantó alerta**. La mejor pregunta del experimento
  anterior no se repitió.
- **La confianza fue 85% en las 6 corridas de Dulce**, acertara o no. No informa
  nada sobre la calidad del resultado.

## 6. Decisión

1. **El modo 3 (Holland → chat) conserva las 4 preguntas fijas.** Es más barato,
   más corto y mantiene la opción creativa a la vista.
2. **El bloque corto de Holland se queda** (código + 6 puntajes + ocupaciones):
   personaliza la conversación y no cuesta casi nada. Pero **no se le puede
   atribuir peso en la recomendación** — medido, no lo tiene. No decir en la
   tesis que "Holland alimenta la recomendación".
3. **El recorte al sector queda apagado** (`--sector`). Como está construido
   —solapamiento de palabras contra títulos de ocupaciones de EE. UU.— borra las
   carreras correctas.
4. **Si Holland tiene que ser motor, entra como estructura, no como prosa.** El
   camino es codificar el catálogo con los códigos RIASEC que O*NET publica para
   cada ocupación y ordenar por distancia al código del alumno. Es la ventaja que
   el CIP no tenía: la codificación se ancla a una fuente real en vez de que la
   invente el modelo. Eso es otro experimento y hay que medirlo igual.

## 7. Limitaciones

- 2 perfiles ficticios, 3 corridas en uno y 1 en el otro. Sirve para leer
  mecanismos, no para afirmar una mejora. La sección 5.1 existe justamente
  porque una sola corrida decía lo contrario.
- Circularidad parcial: quien responde el chat y quien recomienda son el mismo
  modelo. Entre ambos media la calificación de O*NET, que el modelo no controla —
  eso sí es mejor que en el experimento del CIP, donde el modelo también
  respondía el instrumento.
- La prueba decisiva sigue necesitando alumnos reales.

## 8. Reproducir

```bash
cd backend
uv run python experimento_holland.py --self-check   # sin red
uv run python experimento_holland.py --hojas        # califica las hojas en O*NET, sin Gemini
uv run python experimento_holland.py --recorte      # la tabla de §3, sin Gemini
uv run python experimento_holland.py                # el A/B (56 llamadas)
uv run python experimento_holland.py --perfil Dulce # una corrida de un perfil
```

Crudos: `backend/data/tests/experimento_holland_resultados.json` y las tres
corridas de Dulce en `experimento_holland_corrida{1,2,3}.json`.
