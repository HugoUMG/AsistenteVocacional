# ¿Quitar el pre-filtro del catálogo mejora algo?

**Estado:** MEDIDO, 2026-08-23. Dos rondas, 8 perfiles, 32 sesiones completas,
448 llamadas a Gemini, $0.2948 de crédito real (presupuesto autorizado: $0.45).

> ⚠️ **La conclusión "no se quita" quedó SUPERADA el 2026-08-24.** Se basaba en
> que el filtro parecía ahorrar en costo. La factura de Google mostró que
> `uso_tokens` oculta el alquiler del caché (38% del gasto), y el filtro crea un
> caché por llamada mientras que el catálogo completo comparte uno. Un rerun **con
> brazo de control** confirmó las dos mitades: en calidad no hay señal (efecto
> 4/8 < ruido 5/8) y en costo el catálogo completo cuesta el **23%** del filtrado.
> **El veredicto se invirtió: conviene quitarlo.** Ver
> [cache-compartido.md](cache-compartido.md) §4 y §9.

**Resultado corto (histórico):** la calidad quedó empatada (13/16 contra 12/16)
dentro de un piso de ruido de 3/8, así que la medida no distingue nada. El filtro
**no decide el resultado final**. La parte de latencia del pico de producción es
real y viene de la key gratis, no del filtro.

Script: `backend/experimento_filtro.py` · Análisis: `backend/analiza_filtro.py`
Datos: `backend/data/tests/experimento_filtro_ronda1.json` y
`experimento_filtro_resultados.json`

---

## De dónde sale

De la depuración del banco de opciones contra el catálogo (mismo día). El
filtro empareja **palabra literal** entre las respuestas del alumno y el
`perfil` de cada carrera, y ese emparejamiento resultó ser en buena parte
accidental:

- 9 palabras del banco no existen en ningún perfil: `cuidar`, `emprender`,
  `educar`, `investigar`, `analizando`, `diseñando`, `ayudando`, `cosas`,
  `funcionen`.
- 2 son ruido puro: `hacer` aparece en 147 de 147 perfiles, `diseño` en 66.
- 85 de 147 carreras (57%) no tienen ninguna palabra específica en común con el
  banco o cuelgan de una sola, y en 30 casos esa palabra es un falso amigo.

Falsos amigos verificados en el texto del perfil:

| Carrera | Entra por | Pero el perfil dice |
|---|---|---|
| Las 5 Ingenierías en Sistemas | `campo`, `crear` | "un **campo** que cambia a diario", "**crear** soluciones digitales" |
| Ing. en Telecomunicaciones | `aire` | "viaja a través del **aire**" |
| Contaduría Pública y Auditoría | `salud`, `historia` | "la **salud** de una organización", "la **historia** económica" |
| Radiología, Bio Imágenes, Teología Sistemática | `estudio` | "el **estudio** solicitado", "el **estudio** y el servicio" |
| Lic. en Educación de la Física y Matemática | `medio` | "nivel **medio** y universitario" |
| Prof. en Inglés como Idioma Extranjero | `práctica` | "la **práctica** constante del idioma" |
| Optometría, Laboratorio Clínico | `trato` | "**trato** cercano al paciente" |

## Comprobación previa, sin gastar cuota

`experimento_filtro.py --seco` barre, para la carrera objetivo de cada perfil,
cada opción del banco sola y cada par de opciones (561 combinaciones) y reporta
el mejor puesto alcanzable dentro del recorte de 35.

| Perfil | Carrera objetivo | Mejor puesto | Con qué opciones |
|---|---|---:|---|
| Byron | Economía Empresarial | 21 | Comunicar, crear, diseñar + Analizando datos |
| Kimberly | Ing. en Telecomunicaciones | 4 | **Al aire libre y en movimiento** + Comunicación, escritura y medios |
| Dilan | Criminología y Política Criminal | 16 | **Trabajar con la naturaleza, el campo** + Analizando datos |
| Yesenia | Téc. en Radiología e Imágenes | 4 | **En medios, un estudio creativo** + Tecnología y computación |
| Alfredo | Prof. en Inglés como Idioma Extranjero | 12 | **De forma práctica, con las manos** + aula |
| Josué | Ing. en Ciencias y Sistemas | 1 | Analizando datos, ideas y lógica |
| Marisol | Enfermería | 22 | Salud y cuidar personas + Comunicación, escritura y medios |
| Andrea | Lic. en Ciencias Jurídicas y Sociales | 1 | Defender la justicia y resolver conflictos |

Lo que hay que leer en negrita: para meter Telecomunicaciones hay que marcar
"al aire libre y en movimiento", y para meter Radiología hay que marcar "un
estudio creativo". La opción semánticamente correcta no las levanta; la
equivocada sí. Solo los dos controles (Josué, Andrea) llegan al puesto 1 por la
razón correcta.

Marcar TODAS las opciones a la vez no es el máximo de señal: el puntaje es una
suma y el ranking es relativo, así que agregar opciones que favorecen a otras
carreras empuja la propia hacia abajo. Con todas marcadas, 7 de los 8 objetivos
quedan fuera de las 35.

## Diseño

Dos brazos, el mismo perfil de alumno, el flujo de producción completo
(4 fijas + 4 adaptativas + recomendación). Lo único que cambia:

- **A (control):** `next-question` ve el top-35 del filtro.
- **B:** `next-question` ve las 185 filas de Quetzaltenango.

`recomendar()` no usa el filtro en ninguno de los dos, nunca lo ha usado.

Dos conversaciones por perfil, no una: el filtro cambia lo que el modelo ve al
ELEGIR cada pregunta, así que cada brazo necesita la suya. A y B se corren
intercalados para que una racha lenta de Google no le caiga entera a un brazo.

Ocho perfiles: cinco apuntan a carreras que la depuración marcó como rotas y
tres son control, para detectar regresión.

### Dos fallas de diseño corregidas antes de gastar

1. **La corrida seca decía "FUERA" para todo** porque marcaba todas las
   opciones a la vez y eso diluye. Se cambió por el barrido de pares.
2. **El alumno simulado contestaba las fijas en prosa.** Producción guarda la
   ETIQUETA del chip que el alumno marca, no un párrafo. Guardar la prosa le
   regalaba al filtro vocabulario ("investigación", "estadística",
   "estructuras") que un alumno real no produce, e inflaba al brazo A. Se
   agregó `_solo_etiquetas()`, que recorta a lo que Chat.jsx guardaría, y se
   descartó la corrida hecha antes de eso.

## Resultado 1: la calidad no se distingue

| Perfil | R1:A | R1:B | R2:A | R2:B | |
|---|---|---|---|---|---|
| Byron | sí | sí | sí | sí | |
| Kimberly | sí | sí | sí | sí | |
| Dilan | sí | sí | **NO** | sí | A cambia solo |
| Yesenia | sí | NO | sí | NO | |
| Alfredo | sí | sí | sí | sí | |
| Josué | sí | sí | sí | sí | |
| Marisol | sí | sí | **NO** | NO | A cambia solo |
| Andrea | sí | NO | **NO** | sí | A cambia solo |
| **Total** | **8/8** | 6/8 | **5/8** | 6/8 | |

Acumulado: **A 13/16, B 12/16.**

El número que manda no es ese, es este otro: **en 3 de 8 perfiles el MISMO
brazo A cambia de resultado entre las dos rondas.** El brazo A solo pasó de 8/8
a 5/8 sin que nada cambiara más que la semilla de la conversación. El piso de
ruido de este arnés es 3/8 y la diferencia entre brazos es 1/16.

**Conclusión: esta medida no distingue nada.** No dice que quitar el filtro sea
igual de bueno, dice que con 8 perfiles y el alumno a temperatura 0.9 no se
puede saber. Para resolverlo haría falta un n mucho mayor, y no vale la pena
gastarlo: las medidas de abajo sí concluyen y apuntan a otro lado.

## Resultado 2: el filtro sí borra la carrera correcta, y da igual

De cuántas de las 5 llamadas de `next-question` la carrera objetivo sobrevivió
el recorte, en el brazo A:

| Perfil | R1 | R2 | Top-1 que salió igual |
|---|---|---|---|
| Marisol | **0/5** | **0/5** | Licenciatura en Enfermería (R1) |
| Dilan | 1/5 | **0/5** | Criminología y Política Criminal (R1) |
| Alfredo | 2/5 | **0/5** | Profesorado de Enseñanza Media (las dos) |
| Yesenia | 4/5 | 5/5 | Téc. en Radiología (las dos) |
| Byron, Kimberly, Josué, Andrea | 4-5/5 | 5/5 | |

Marisol nunca tuvo Enfermería entre las 35 candidatas, en ninguna de las 10
llamadas, y aun así su top-1 fue Licenciatura en Enfermería. Es la confirmación
directa de lo que ya decía el docstring de `filtro.py`: **el recorte no gatea el
resultado final**, porque `recomendar()` recibe el catálogo completo. El daño
del filtro se queda en la elección de preguntas.

## Resultado 3: quitar el filtro es MÁS RÁPIDO en la mediana

Esta sí tiene muestra: 96 llamadas por brazo.

| | A: con filtro | B: sin filtro |
|---|---:|---:|
| next-question, mediana | 2.44 s | **1.86 s** |
| next-question, p90 | 2.76 s | 2.17 s |
| next-question, p95 | 2.92 s | 2.50 s |
| next-question, máximo | 4.28 s | **19.42 s** |
| recommend, mediana | 3.25 s | 3.35 s |
| **Sesión completa, mediana** | **15.6 s** | **12.4 s** |
| Peor sesión | 17.2 s | 30.0 s |
| Prompt cacheado | 94.3% | **97.9%** |
| Costo por sesión | $0.0058 | $0.0081 |

Es al revés de lo que uno esperaría con un prompt 2.8 veces más grande, y el
motivo está en la columna de caché. **Con filtro, el top-35 se recalcula en cada
llamada con las respuestas acumuladas, así que el texto del catálogo cambia,
la clave del `CachedContent` cambia y el caché se recrea.** Sin filtro el
catálogo es constante: la misma entrada de caché sirve todas las llamadas de
todas las sesiones del departamento.

El precio de quitarlo está en la cola, no en la mediana: ese máximo de 19.4 s
es crear el caché de 25k tokens la primera vez. Ocurre una vez por hora (el TTL
es de 3600 s) y le cae a un alumno.

Dinero: **+$0.0023 por sesión, o sea +$0.23 por cada 100 sesiones.**

## Resultado 4 (no buscado): los picos de 10 s no son del filtro

La primera corrida de calibración salió con la configuración actual de
`backend/.env`, que tiene la key con billing en `GEMINI_API_KEY_RESPALDO` y la
gratis en `GEMINI_API_KEY`. Con esa configuración:

| | Key gratis (config actual) | Key con billing |
|---|---:|---:|
| `caches.create` | falla (el tier gratis tiene el almacenamiento en 0) | funciona |
| Prompt cacheado, brazo A | **0.0%** | 94.3% |
| Primera llamada de la sesión | **46.2 s** | 1.2-3.9 s |
| Costo del par de sesiones | $0.045 (habría costado) | $0.018 real |

`decisions/gemini-costos-y-caching.md` ya lo advertía: la key con billing debe
ir en la primaria, porque el caché se crea en el proyecto del cliente que
efectivamente atiende la llamada. Mientras esté al revés, producción corre sin
caché explícito y paga el prompt entero cada vez.

**La queja de 3-4 s con picos de 10 s se explica ahí, no en el filtro.** Con la
key de pago como primaria la mediana medida es de 2.4 s y el p95 de 2.9 s, y
ninguna de las 96 llamadas del brazo A pasó de 4.3 s.

## Qué se hace

1. **El filtro se queda.** No hay evidencia de que quitarlo mejore la
   recomendación, y la evidencia de que no la empeora tampoco existe: la medida
   no alcanza. Sin evidencia a favor, no se toca lo que está en producción.
2. **Mover la key con billing a `GEMINI_API_KEY`** y reiniciar el backend. Es
   el arreglo de latencia, y es de configuración, no de código.
3. **Las 9 palabras muertas y las 2 de ruido del banco sí se pueden arreglar
   solas**, sin tocar el filtro: son redacción de las opciones. Pendiente de
   medir aparte.
4. **No invertir más en este A/B.** Si alguna vez se retoma, el arnés necesita
   n grande o perfiles con top-1 estable; los tres perfiles inestables
   (Dilan, Marisol, Andrea) hay que sacarlos o repetirlos hasta tener tasa.

## Lo que este experimento NO probó

- Que el filtro sea bueno. Solo que quitarlo no se nota con n=8.
- Que las carreras "rotas" salgan mal recomendadas. Salen bien, porque
  `recomendar()` no usa el filtro.
- Nada sobre el desempate entre carreras hermanas: eso sigue siendo
  `experiments/adaptativas-desempate.md`, sin ejecutar.
