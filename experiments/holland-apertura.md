# ¿Ayuda que el chat NOMBRE el resultado de Holland al abrir la conversación?

**Fecha:** 2026-08-17 · **Estado:** confirmado y con resultado nítido —
**se adopta la apertura explícita**, con la lectura correcta de qué prueba.

Ámbito: catálogo de Quetzaltenango + Totonicapán (202 registros carrera-sede),
`gemini-3.1-flash-lite`. Banco de pruebas: `backend/experimento_holland_apertura.py`.

---

## 1. Por qué este experimento

[holland-en-chat.md](holland-en-chat.md) ya midió que el bloque de Holland en
el prompt **no pesa en el ranking** (5/6 corridas ignoraron el área más alta).
La lectura de esa medición fue que Holland no debe competir con el LLM por
decidir qué carrera gana — su valor está en la conversación: que el alumno
sienta que el chat ya lo conoce antes de preguntar. Hoy eso depende de que el
LLM decida, por su cuenta, usar el bloque con tacto; el system prompt no lo
obliga a nada concreto.

Esto pone a prueba una versión **obligatoria** de esa idea: la primera
pregunta adaptativa DEBE nombrar el código o el área más alta de Holland de
forma explícita, y si el perfil tiene dos áreas empatadas (≤5 puntos de
diferencia), la pregunta debe apuntar a desempatarlas en vez de ir a una
dimensión genérica.

## 2. Brazos

Los dos son el modo 3 de producción (Holland → chat, con las 4 fijas — ya
decidido en `holland-en-chat.md`) y reciben el **mismo** bloque de Holland en
el prompt. Solo cambia la instrucción sobre qué hacer con él:

- **B — producción.** La adenda de hoy: "personaliza la apertura, con tacto,
  sin cifras". Sugerencia, no obligación.
- **C — apertura explícita + desempate.** Obligación: la primera frase de la
  primera pregunta adaptativa nombra el código o el área más alta tal cual
  salió en el test; si hay empate técnico, la pregunta apunta a resolverlo.

## 3. Perfiles

Se reusan **Dulce** (A=39/S=38, área artística vs. lo que espera la casa) y
**Melany** (C=36 claro, sin empate) de `experimento_holland.py`, para leer
este experimento junto al anterior. Se agrega **Byron**, diseñado con un
empate técnico real (R=32 vs I=30 en el diseño; salió R=26/I=29 al calificar,
sigue siendo empate) porque ni Dulce ni Melany tienen uno en la dimensión
motriz — Dulce sí resultó tener empate propio (A/S), lo que terminó dando dos
casos de empate en vez de uno.

La hoja de 60 ítems se arma aritméticamente desde el nivel real 1-5 por área
(±1 de ruido determinista) y la califica la API de O*NET — no Gemini. `--hojas`
confirmó que el área dominante de los tres quedó en el código antes de gastar
cuota:

| Perfil | Código | Puntajes | Empate detectado |
|---|---|---|---|
| Dulce | ASC | A=39 S=38 C=19 R=12 I=10 E=10 | Artístico/Social (Δ=1) |
| Melany | CEI | C=36 E=29 I=16 R=9 S=9 A=3 | ninguno |
| Byron | IRE | I=29 R=26 E=11 C=8 A=3 S=3 | Investigador/Realista (Δ=3) |

## 4. Resultados

Dulce y Byron se corrieron **2 veces** cada uno; Melany 1 vez (perfil estable,
sin empate que probar).

### 4.1 Lo que la instrucción controla al 100%: si el chat nombra el resultado

| | B (producción) | C (apertura explícita) |
|---|---|---|
| Nombra Holland en la 1.ª pregunta adaptativa | **0/6** | **6/6** |

Sin excepción, en las 6 corridas. Esto es lo contrario del hallazgo de
`holland-en-chat.md` §5.2 ("un bloque de texto es contexto, no peso"): **una
instrucción obligatoria sobre la FORMA de la primera pregunta sí se cumple
siempre**, aunque el resultado final del ranking no se le pueda ordenar de la
misma manera. La diferencia importa para el diseño: lo que el LLM obedece de
forma confiable es la instrucción sobre CÓMO hablar, no una instrucción sobre
QUÉ recomendar.

Ejemplo real, primera línea de la apertura en C:

> *"Vi que tu test de Holland salió fuerte en Artístico y Social, y me encanta
> que..."* (Dulce)
> *"Vi que tu test de Holland salió fuerte en Convencional, lo que explica..."*
> (Melany)
> *"Vi que tu test de Holland salió fuerte en Investigación y Realistas, y..."*
> (Byron)

### 4.2 Lo que la instrucción NO controla: el ranking final

| Perfil | Corrida | B top-1 | C top-1 |
|---|---|---|---|
| Dulce | 1 | Enfermería 35% (❌ casa) | Enfermería 35% (❌ casa) |
| Dulce | 2 | Comunicación y Diseño 45% (✅ suya) | Enfermería 35% (❌ casa) |
| Melany | 1 | Contaduría 35% | Contaduría 45% |
| Byron | 1 | Ing. Mecánica 35% | Ing. Mecánica 35% |
| Byron | 2 | Ing. Mecánica Industrial 35% | Ing. Mecánica Industrial 45% |

En 4 de 5 corridas comparables, **B y C coinciden en qué carrera gana** — la
apertura explícita no la cambió. La única corrida donde difieren (Dulce #2) es
la que le da la razón a Enfermería con B *sin* la apertura explícita y se la
quita con C *con* ella: **si algo, va al revés de lo esperado**, y confirma que
no hay una relación causal fiable entre "nombrar el resultado" y "que gane esa
área". Con `n=1` no se puede afirmar ni eso — es ruido, igual que la corrida 1
de `holland-en-chat.md` §5.1 lo fue para las preguntas fijas.

El caso de empate de Byron (R/I) tampoco discrimina: las dos áreas apuntan al
mismo sector del catálogo (ingeniería), así que "desempatar" no tenía a dónde
llevar la conversación que fuera visible en el resultado. Es una limitación
del diseño del perfil, no del hallazgo: el desempate real (Dulce, A vs. S, que
sí apuntan a sectores distintos —diseño vs. salud—) es justo el que salió
inestable entre corridas.

### 4.3 Confianza y tokens: sin patrón

| Perfil | Corrida | Tokens B | Tokens C | Confianza B | Confianza C |
|---|---|---|---|---|---|
| Dulce | 1 | 58 247 | 57 421 | 85% | 75% |
| Dulce | 2 | 58 495 | 60 539 | 85% | 85% |
| Melany | 1 | 52 029 | 51 313 | 90% | 90% |
| Byron | 1 | 63 381 | 63 969 | 90% | 90% |
| Byron | 2 | 66 823 | 62 841 | 85% | 85% |

A diferencia del hallazgo de las preguntas fijas (~38% menos tokens, estable
en las 3 corridas), acá **no hay diferencia de costo entre B y C**: a veces C
es más barato, a veces más caro, sin patrón. Tiene sentido — la apertura
explícita cambia una frase, no la cantidad de turnos.

## 5. Lectura

**El resultado que sí se puede afirmar con las 6 corridas, sin matices:** la
instrucción de apertura explícita se cumple siempre y hace que la conversación
se *sienta* leída — el alumno ve, en su propia primera pregunta, que el chat
nombra su resultado de Holland con las palabras del instrumento oficial, no
una alusión genérica. Eso es exactamente la sensación de "ayuda personalizada
que ya entendió mis respuestas" que motivó este experimento.

**Lo que no cambia, y no hay que prometer que cambia:** el ranking final. Con
5 corridas comparables, B y C empatan en 4; en la única que difiere, va al
revés de lo esperado. Esto es consistente, no contradictorio, con
`holland-en-chat.md`: la apertura explícita es una intervención en la FORMA de
la conversación (garantizada), no en el PESO del dato dentro del ranking (que
sigue sin tenerlo). Son dos preguntas distintas y este experimento contesta la
primera, no reabre la segunda.

## 6. Decisión

1. **Se adopta la apertura explícita** en el modo 3 (Holland → chat):
   `adenda_apertura_explicita()` reemplaza a la adenda pasiva de
   `experimento_holland.py`, sujeta a que se traslade a `app/preguntas.py`
   como cambio de producción (regla 3/4 — este documento es la medición que
   lo habilita, falta el paso de integrarlo).
2. **No se afirma en la tesis que esto mejora la recomendación.** Se afirma lo
   que se midió: que hace la apertura de la conversación medible y consistente
   como personalización, sin tocar el motor de ranking — que sigue siendo,
   por diseño y por medición repetida, la conversación completa y el criterio
   del LLM, no un instrumento psicométrico particular.
3. **La regla de desempate queda escrita pero sin evidencia de que aporte.**
   El único caso con empate real entre sectores distintos (Dulce) fue
   justamente el más inestable. No se descarta, pero tampoco se vende como
   validada — es la misma disciplina que dejó "el recorte al sector" apagado
   en `holland-en-chat.md`: construido, medido, sin prueba de que ayude.

## 7. Limitaciones

- 3 perfiles ficticios, 5-6 corridas en total: alcanza para leer el mecanismo
  (¿se cumple la instrucción de forma?, ¿mueve el ranking?), no para afirmar
  una mejora con potencia estadística — igual que los experimentos anteriores
  de este proyecto.
- Byron no fue un buen caso de prueba para el desempate: sus dos áreas
  empatadas (R/I) apuntan al mismo sector del catálogo. Un perfil con empate
  entre dos áreas de sectores distintos (como terminó siendo Dulce, sin
  buscarlo) es el diseño correcto si se repite este experimento.
- Detectar "¿nombró el resultado?" es un regex sobre el texto, no una lectura
  humana — puede tener falsos negativos si el chat parafrasea sin usar el
  código ni el nombre del área (no ocurrió en las 6 corridas, pero es posible).
- Mismas de siempre: quien responde el chat y quien recomienda es el mismo
  modelo; la prueba decisiva sigue necesitando alumnos reales.

## 8. Reproducir

```bash
cd backend
uv run python experimento_holland_apertura.py --self-check   # sin red
uv run python experimento_holland_apertura.py --hojas        # califica en O*NET, sin Gemini
uv run python experimento_holland_apertura.py                # el A/B (gasta cuota)
uv run python experimento_holland_apertura.py --perfil Byron # una corrida de un perfil
```

Crudos: `backend/data/tests/experimento_holland_apertura_resultados.json`
(última corrida de cada perfil) y `experimento_holland_apertura_corrida1.json`
(la primera corrida de las 3, antes de repetir Dulce y Byron).
