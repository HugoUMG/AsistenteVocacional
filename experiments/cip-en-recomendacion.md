# CIP como prioridad del catálogo en la recomendación — experimento revertido

Documento de respaldo para la tesis. Registra la hipótesis, la implementación, el
A/B que la evalúa y **por qué se dejó apagada**, con una limitación metodológica
que resultó ser el hallazgo principal.

Fecha: 2026-08-11. Ámbito: catálogo completo de Quetzaltenango + Totonicapán
(202 registros carrera-sede), modelo `gemini-3.1-flash-lite`.

**Veredicto: revertido.** El flag `CIP_EN_RECOMENDACION` queda en `0`. El código
se conserva porque el experimento **no llegó a probar la hipótesis** — ver §6.

---

## 1. Hipótesis

Hoy el emparejamiento alumno↔carrera vive entero dentro de Gemini: recibe el
perfil en texto del chat y el catálogo, y decide. Funciona (10/10 en el
experimento de cobertura), pero tiene dos debilidades para un TFG:

- **No es auditable.** "¿Por qué salió esta carrera primero?" → "el modelo lo
  decidió". No hay número que mostrar.
- **No es estable.** Temperatura 0.3 y preguntas distintas cada corrida.

La hipótesis: si el recorte de candidatas sale del **percentil de un instrumento
psicométrico** en vez del criterio del modelo, el sistema debería mantener o
mejorar el acierto y volverse defendible ante un tribunal.

## 2. Implementación

Toda detrás de un flag, para que revertir no exija deshacer código:

- **`backend/app/cip_filtro.py`** (nuevo). Ordena el catálogo por congruencia con
  el perfil CIP del alumno y lo corta en `TOP_CIP = 30`. La escala principal de
  cada carrera pesa 1.0 y la secundaria 0.5. Una carrera sin codificar recibe el
  percentil medio (50): un hueco de datos no es culpa del estudiante.
- **`backend/app/recomendar.py`**: `recomendar()` acepta `perfil_cip` opcional.
  Con el flag activo, recorta el catálogo y antepone los percentiles al prompt
  como dato medido, con la instrucción de que tienen prioridad sobre lo dicho de
  pasada en el chat.
- **Se prioriza, no se filtra duro.** `filtro.py` ya documenta que `/recommend` a
  propósito no recorta, para no excluir una carrera válida de la respuesta final.
  Un corte agresivo haría el sistema más "auditable" y más frágil a la vez.

Activación: `CIP_EN_RECOMENDACION=1` en `backend/.env`. Apagado por defecto.

## 3. Metodología

La misma del Experimento B de [cobertura-dimensiones.md](cobertura-dimensiones.md),
para que las cifras sean comparables: **10 perfiles ficticios coherentes**, cada
uno con un `area_esperada` como criterio externo débil. Se mide si el top-1 cae en
esa área.

Añadido: cada persona **responde los 150 ítems del CIP en su papel** (1 llamada a
Gemini por persona, cacheada). Esas hojas se califican con `cip_fogliatto` y el
perfil resultante alimenta el brazo NUEVO.

Ambos brazos reciben **las mismas respuestas de chat**. La única variable que
cambia es el CIP. Banco de pruebas: `backend/experimento_cip.py`.

## 4. Resultados

| Persona | Área esperada | VIEJO | NUEVO |
|---|---|---|---|
| Ana | salud | ✅ Médico y Cirujano 35% | ✅ Médico y Cirujano 35% |
| Luis | informática | ✅ Ing. en Ciencias y Sistemas 45% | ✅ Ing. en Ciencias y Sistemas 35% |
| Mario | administración | ✅ Administración de Empresas 35% | ✅ Administración de Empresas 40% |
| Sofía | educación | ✅ Profesorado en Educación Primaria 45% | ❌ PEM en Comunicación y Lenguaje 25% |
| Diego | forestal | ✅ Ingeniería Forestal 45% | ✅ Ingeniería Forestal 60% |
| Carmen | derecho | ✅ Cs. Jurídicas y Sociales 85% | ✅ Cs. Jurídicas y Sociales 55% |
| Pablo | criminalística | ✅ Criminología y Criminalística 60% | ✅ Criminología y Criminalística 45% |
| Lucía | comunicación | ✅ Cs. de la Comunicación Social 45% | ✅ Cs. de la Comunicación Social 35% |
| Roberto | contaduría | ✅ Contaduría Pública y Auditoría 60% | ✅ Contaduría Pública y Auditoría 40% |
| Elena | trabajo social | ✅ Trabajo Social 45% | ✅ Trabajo Social 60% |

| Métrica | VIEJO | NUEVO |
|---|---|---|
| **Top-1 en el área esperada** | **10/10** | **9/10** |
| Afinidad promedio del top-1 | 50% | 43% |
| El top-1 cambió | — | 1/10 |

## 5. Lectura de los resultados

**Midió peor, así que se revierte.** Es la regla 4 del proyecto y se aplica sin
discusión.

Dos matices que conviene registrar, sin usarlos para rescatar el experimento:

- **El único caso que cambió es discutible.** "PEM en Comunicación y Lenguaje" es
  un profesorado, o sea el área de Sofía. Se contó como fallo porque la lista de
  palabras clave del banco de pruebas no incluía `pem`. El criterio se fijó
  **antes** de correr el experimento y no se reescribe después para que el
  resultado convenga: se reporta el 9/10 medido y se anota el matiz.
- **9/10 top-1 idénticos.** El recorte por CIP apenas movió el resultado. Con la
  señal del chat presente, el prefiltro no aportó poder discriminante.

## 6. El hallazgo principal: el experimento no probó la hipótesis

Al revisar las hojas del CIP simuladas se ve que **no reproducen el perfil de la
persona con fiabilidad**:

| Persona | Área esperada | Posición en su perfil CIP |
|---|---|---|
| Ana, Sofía, Diego, Carmen, Pablo, Elena | — | **#1** |
| Mario | Económica-Administrativa | #2 |
| Luis | Cálculo | #4 (salió Físico-Química) |
| Lucía | Comunicación Social | #4 (salió Artístico-Plástica) |
| Roberto | Económica-Administrativa | #5 (salió Cálculo) |

**El área esperada quedó en el top-1 solo en 6/10 casos, y en el top-3 en 7/10.**

Eso invalida el A/B como prueba de la hipótesis: en 3 o 4 perfiles, el brazo NUEVO
recibió un perfil CIP equivocado. No se estaba midiendo "¿ayuda el CIP?", sino
"¿ayuda un CIP mal respondido?" — y a esa pregunta la respuesta obvia es que no.

Es el mismo error que ya se documentó en el Experimento A de cobertura, con otra
cara: **la política de simulación no representa a la persona**. Allá era "elegir
siempre el primer botón"; aquí es "que el propio Gemini conteste 150 ítems
haciéndose pasar por alguien". Un modelo de lenguaje respondiendo un inventario de
intereses en un papel ficticio no produce un perfil psicométrico válido, y no hay
razón para esperar que lo haga.

Hay además circularidad: el mismo modelo responde el instrumento y luego
recomienda. Media entre ambos la calificación aritmética, que el modelo no
controla, pero no alcanza para limpiar el diseño.

## 7. Decisión

1. **El flag queda apagado.** El sistema se comporta exactamente como antes.
2. **El código se conserva**, no se borra: la hipótesis sigue sin probarse, y el
   costo de mantenerlo es un módulo aislado y un `if`.
3. **La prueba decisiva necesita respuestas reales.** El CIP contestado por
   estudiantes de carne y hueso, con su recomendación evaluada por un orientador.
   Eso depende de la autorización de uso del instrumento y de la supervisión
   profesional, que están en trámite — así que el experimento no se puede cerrar
   antes que ese trámite.
4. Si al repetirlo con datos reales vuelve a medir igual o peor, entonces sí se
   borra el módulo y se documenta como segundo intento descartado.

## 8. Subproducto: dos defectos encontrados en el camino

Ninguno tiene que ver con el CIP; salieron al montar el banco de pruebas.

- **Los scripts cargaban el `.env` después de importar `app.recomendar`.** Ese
  módulo resuelve `MODELO`/`MODELO_FINAL` con `os.getenv` al importarse, así que
  corrían con `gemini-2.5-flash` (el default del código) en lugar de
  `gemini-3.1-flash-lite` (el del proyecto). Se agotó la cuota diaria de un modelo
  que el sistema ni siquiera usa. Corregido en `codificar_cip.py` y
  `experimento_cip.py`.
- **`_con_reintento` no reintentaba fallos de transporte.** Si el servidor cortaba
  la conexión sin responder (`httpx.RemoteProtocolError`), no había `APIError` que
  atrapar y la excepción se propagaba: en producción, eso deja a un alumno sin
  recomendación por una desconexión pasajera. Ocurrió dos veces seguidas al mandar
  el catálogo completo inline. Corregido en `recomendar.py`.

También quedó documentado que el free tier de `gemini-3.1-flash-lite` tiene
**cero** almacenamiento de contexto cacheado (`limit=0`), así que `/recommend`
manda hoy el catálogo completo inline en cada llamada. Ver
[decisions/gemini-costos-y-caching.md](../decisions/gemini-costos-y-caching.md).

## 9. Cómo reproducirlo

```
cd backend
uv run python experimento_cip.py --self-check   # sin red
uv run python experimento_cip.py --responder    # 10 llamadas, cachea las hojas
uv run python experimento_cip.py                # el A/B, 20 llamadas
```

Resultados crudos en `backend/data/tests/experimento_cip_resultados.json` y hojas
del CIP en `backend/data/tests/experimento_cip_respuestas.json`.
