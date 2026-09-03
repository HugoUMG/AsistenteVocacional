# Turno obligado de sondeo: que Holland dirija las preguntas, no la recomendación

**Fecha:** 2026-08-18 · **Estado:** medido y **NO se integra**. Cuesta +1
pregunta y +12% de tokens, midió 5/6 contra 6/6 del flujo actual, y el
diagnóstico de la corrida que retrocedió muestra un mecanismo por el que la
intervención puede **empeorar** el resultado.

**Advertencia de lectura, antes que nada: este experimento no tenía margen de
mejora.** El brazo de control salió 6/6, o sea en el techo. Un A/B contra un
control perfecto no puede detectar una mejora, así que este informe **no
descarta la hipótesis**: solo dice que la intervención no aportó nada acá y sí
costó. Ver §5.

Ámbito: catálogo de Quetzaltenango + Totonicapán (202 registros),
`gemini-3.1-flash-lite`, 2 perfiles ficticios × 2 brazos × 3 corridas = 12
conversaciones. Banco: `backend/experimento_holland_sondeo.py`.

---

## 1. La hipótesis y por qué era distinta

Holland no mueve la recomendación. Medido tres veces:
[holland-en-chat.md](holland-en-chat.md) §5.2 (como prosa),
[holland-estructura.md](holland-estructura.md) §4 (como orden del catálogo) y §9
(con el catálogo revisado a mano). Las tres veces, 0 cambios en el top-1.

El mecanismo del fallo está diagnosticado: **el alumno declara una cosa, el test
mide otra, y el modelo le hace caso a lo declarado.** Los tres intentos
atacaron el momento de *recomendar*, o sea le pidieron al modelo que ponderara
mejor. Este atacó el momento de *preguntar*.

La razón para esperar algo distinto: el único experimento de este proyecto que
midió una **mejora** fue de dirección de preguntas
([cobertura-dimensiones.md](cobertura-dimensiones.md), 40%→100% de cumplimiento
y 7/10→10/10 de acierto). La palanca de las preguntas había funcionado; la de la
recomendación nunca.

## 2. Qué estaba roto, en concreto

`app/holland.py::adenda_chat` **ya** le dice al modelo que contraste:

> "Después de esa apertura, contrasta: si lo que dice contradice lo medido,
> pregunta para aclarar esa tensión y anótalo en 'alerta_contradiccion'."

O sea que la instrucción de arbitraje **ya estaba en producción**. Lo que no
existía era la **obligación**: en `app/preguntas.py`, `intereses` arranca
cubierta (`COBERTURA_INICIAL`, por las 4 preguntas fijas) y no está en
`PRIORITARIAS`. El modelo podía saltarse el contraste sin costo alguno.

**La intervención:** cuando hay perfil de Holland, `intereses` deja de arrancar
cubierta y pasa a ser la primera prioritaria. Los intereses *declarados* en las
4 fijas ya no dan por saldada la dimensión que el test mide de otra forma.

## 3. Diseño

Los dos brazos usan la adenda de producción (`holland.adenda_chat`), las 4
preguntas fijas y el catálogo sin recortar. La única variable es la semilla de
cobertura:

- **VIEJO** — producción de hoy: `intereses` cubierta, prioritarias = las 4
  normales.
- **NUEVO** — `intereses` PENDIENTE y primera de la lista.

**Acá no se puede compartir la conversación entre brazos**, como sí hace
[holland-estructura.md](holland-estructura.md) §4, porque la intervención cambia
la conversación misma. Eso reintroduce la varianza entre corridas que aquel
informe documenta como mayor que la varianza entre brazos, y por eso son 3
corridas por brazo y se lee por tasa.

## 4. Resultados

| Perfil | Brazo | top-1 correcto | sondeó intereses | adaptativas | tokens |
|---|---|---|---|---|---|
| **Dulce** | VIEJO | **3/3** | 0/3 | 4.0 | 57,711 |
| **Dulce** | NUEVO | **2/3** | 3/3 | 5.0 | 65,081 |
| **Melany** | VIEJO | **3/3** | 0/3 | 4.0 | 53,757 |
| **Melany** | NUEVO | **3/3** | 3/3 | 5.0 | 60,189 |

| Métrica | VIEJO | NUEVO |
|---|---|---|
| top-1 correcto | **6/6** | **5/6** |
| Se gastó un turno en sondear lo medido | 0/6 | **6/6** |
| Preguntas adaptativas | 4.0 | 5.0 |
| Tokens por conversación | 55,734 | 62,635 (**+12%**) |

Costo de la corrida: ~$0.13 equivalentes, 12 conversaciones.

**El mecanismo funciona técnicamente.** 6/6 de cumplimiento en el brazo NUEVO y
0/6 en el VIEJO: la semilla de cobertura obliga al turno de sondeo de forma
perfectamente fiable. Lo que no produce es un mejor resultado.

## 5. El defecto del diseño: no había margen

**El control salió 6/6.** No se puede mejorar sobre un control perfecto, así que
este A/B no podía detectar una mejora aunque la intervención sirviera. Eso es un
defecto del experimento, no un resultado sobre la hipótesis.

Y hay algo más que llama la atención: en
[holland-estructura.md](holland-estructura.md) §4 y §9, **Dulce terminaba en
Enfermería**, no en lo artístico. Acá el brazo de control la manda a Comunicación
y Diseño 3/3.

> **Corrección (2026-08-18).** La primera versión de este informe atribuyó esa
> diferencia a la adenda de producción y la propuso como "la pista más
> interesante". **Era falso y se comprobó:** el brazo C de
> [holland-apertura.md](holland-apertura.md) usaba la MISMA apertura explícita
> que producción y con él Dulce salió Enfermería 2/2. Los dos bancos tenían la
> apertura; la adenda no explica nada.
>
> Lo que sí explica la diferencia, contando todas las corridas de Dulce del
> corpus, es que **su resultado es una moneda al aire**: 6 Enfermería contra 6
> Comunicación y Diseño. Y tiene causa estructural, no de banco: su perfil es
> **A=39 vs S=38, un empate técnico de 1 punto** entre dos áreas que apuntan a
> sectores opuestos, arte y salud. El propio informe de apertura ya lo había
> anotado en sus limitaciones. El 3/3 del control de este experimento fueron
> tres caras seguidas, no una mejora.

De ahí la lección de método, que vale para todo el proyecto: **comparar tasas
entre experimentos con n distinto, sobre un perfil inestable, produce hallazgos
fantasma.** Dulce necesita n grande para cualquier afirmación, o un perfil de
reemplazo sin empate técnico.

## 6. Por qué el sondeo puede empeorar

La única corrida que retrocedió (Dulce NUEVO #2, top-1 Enfermería) tiene un
diagnóstico claro. La pregunta de sondeo salió así:

> "Vi que tu test de Holland salió súper fuerte en Artístico y Social... "
> Opciones: **"Diseñar algo visual que impacte a muchos"** /
> **"Atender a alguien de forma directa y cercana"**

Y la respuesta:

> "Uy, qué difícil, profe. La verdad es que diseñar una campaña me emociona un
> montón, me imagino haciendo los videos y que la mara reaccione, **pero fijo voy
> a elegir atender a alguien de forma directa**."

**Forzar el contraste la obligó a declarar salud de forma explícita.** Sin el
sondeo, la tensión quedaba sin resolver y el modelo conservaba lo artístico; con
el sondeo, la alumna resolvió la tensión a favor de lo declarado y quedó por
escrito como una elección deliberada, no como una ambigüedad.

Es un resultado con moraleja: **pedirle a un alumno que elija entre lo que dice
y lo que midió el test tiende a resolverse a favor de lo que dice.** El formato
de opción binaria empeora eso: obliga a elegir donde antes había matiz.

## 7. Decisión

1. **No se integra.** Producción queda igual: `intereses` sigue arrancando
   cubierta y fuera de `PRIORITARIAS`. Nada que revertir, la intervención vivió
   solo en el banco de pruebas (regla 4).
2. **La hipótesis no queda descartada**, queda sin probar por falta de margen
   (§5). Si alguien la retoma, necesita un perfil donde el flujo actual **falle**,
   que es lo que este experimento no tuvo.
3. **Si se retoma, no usar opción binaria** para el sondeo (§6). Una pregunta
   abierta, o una que pida ordenar en vez de elegir, no fuerza a descartar.
4. **Dulce ya no sirve como perfil suelto para este tipo de A/B.** Su empate
   técnico (A=39/S=38, sectores opuestos) la vuelve una moneda al aire: 6 y 6 en
   todo el corpus (§5). Cualquier medición que la use necesita n grande, o un
   perfil nuevo con área dominante clara que igual contradiga el guion de la
   casa. Su inestabilidad no es un defecto del banco, **es el hallazgo**: cuando
   el instrumento mismo es ambiguo, la recomendación es inestable.

## 8. Limitaciones

- **2 perfiles ficticios, 3 corridas por brazo.** La diferencia 5/6 vs 6/6 es
  **una sola conversación**: está dentro del ruido y no se puede leer como que
  la intervención empeora. Lo que sí se puede afirmar es que no mejoró y que
  cuesta más.
- El "acierto" se mide por coincidencia de subcadena contra una lista de
  palabras clave escrita por el desarrollador, sobre perfiles inventados y
  simulados por el propio Gemini. Mide **consistencia interna, no validez**.
- El control en el techo (§5) es el límite principal de todo el informe.

## 9. Reproducir

```bash
cd backend
uv run python experimento_holland_sondeo.py --self-check   # sin red
uv run python experimento_holland_sondeo.py --resumen      # tasas, sin red
uv run python experimento_holland_sondeo.py                # el A/B (~$0.13)
```

Crudos: `backend/data/tests/experimento_holland_sondeo.json` (incluye las
transcripciones completas y la dimensión de cada pregunta).
