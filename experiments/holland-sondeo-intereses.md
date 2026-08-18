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
y Diseño 3/3. La diferencia entre bancos: este usa la adenda de producción
(`adenda_chat`, con la regla de apertura integrada el 2026-08-17) y aquel usaba
la `adenda_system` vieja del banco de `experimento_holland.py`.

Eso **sugiere** que la apertura explícita pesa más de lo que concluyó
[holland-apertura.md](holland-apertura.md) ("no cambia qué carrera gana", 4/5
corridas iguales). No lo prueba: son bancos distintos, n chico y varianza alta.
Queda como la pista más interesante que salió de acá, ver §7.

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
4. **La pista que vale la pena seguir es otra:** medir si la apertura explícita
   (`adenda_chat`) mueve el ranking, con el mismo banco y n≥3 por brazo.
   [holland-apertura.md](holland-apertura.md) concluyó que no, pero acá el
   control con la adenda de producción se comportó distinto que los informes
   anteriores sin ella (§5).

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
