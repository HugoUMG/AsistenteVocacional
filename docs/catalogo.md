# Catálogo de carreras

Fuente de verdad del sistema. Vive en `backend/data/*.json` y se carga a la tabla
`carreras` con `uv run python seed_carreras.py` (idempotente).

Cada carrera lleva un **perfil / "banco de palabras"** (afinidades, habilidades,
entorno, gustos, estilo cognitivo) — es lo único que la IA recibe de cada carrera;
universidad, centro, departamento y sello los adjunta Python después de la
respuesta del modelo.

Para agregar carreras: crear/editar un `backend/data/*.json` (con `departamento`,
`centro`, `universidad` y las `carreras` con su `perfil`) y correr
`seed_carreras.py`. **No hay que tocar código**: los prompts son
catálogo-agnósticos.

---

## Estado: ciclo Quetzaltenango + Totonicapán cerrado (2026-07-21)

Todas las universidades con sede física en estos dos departamentos ya están
en `backend/data/*.json`. No falta ninguna por agregar — confirmado por
búsqueda: Galileo, Panamericana, Da Vinci y Rural de Guatemala no tienen
sede en Totonicapán (se concentran en Ciudad de Guatemala y Quetzaltenango).

**Quetzaltenango** (9 centros, ~185 carreras): USAC (CUNOC), Universidad
Rafael Landívar (URL Xela), Universidad de Occidente (UdeO), Universidad
Mariano Gálvez (UMG), Universidad Mesoamericana, Universidad Panamericana
(UPANA), Universidad Galileo, Universidad Rural de Guatemala (URURAL),
Universidad Da Vinci de Guatemala.

**Totonicapán** (3 centros, 17 carreras): USAC (CUNTOTO), Universidad
Mariano Gálvez (UMG), Universidad Regional de Guatemala (URG).

## Tamaño real (medido con `count_tokens`, 2026-08-02)

| Filtro | Filas (carrera × sede) | Bloques que ve la IA | Catálogo en `/recommend` |
|---|---|---|---|
| Solo Totonicapán | 17 | 14 | 4,761 tok |
| Solo Quetzaltenango | 185 | 85 | 23,310 tok |
| Ambos | 202 | 90 | 25,108 tok |

Los "bloques" son menos que las filas porque `perfil_grupo` **deduplica**: una
carrera ofrecida por 5 sedes comparte un perfil de `perfiles_compartidos.json` y
viaja **una sola vez** en el prompt (`_catalogo_texto` en `recomendar.py`).

En `/next-question` el catálogo pasa antes por el pre-filtro top-35, así que
queda en ~4.4-4.8k tokens **sin importar el departamento** (35 filas → 16
bloques). Desglose completo y costos en
[decisions/gemini-costos-y-caching.md](../decisions/gemini-costos-y-caching.md).

Desglose por centro: 34 UMG Xela · 33 Mesoamericana · 32 URL Xela · 21 UdeO ·
18 CUNOC · 17 Galileo · 12 URURAL · 11 Da Vinci · 7 UPANA (Quetzaltenango);
10 URG · 4 CUNTOTO · 3 UMG Totonicapán (Totonicapán).

Siguiente paso natural: extender el catálogo a otro departamento (fuera del
alcance actual del proyecto, que es Quetzaltenango/Totonicapán/Suroccidente).

⚠️ El tamaño del catálogo domina el costo de cada llamada a Gemini (97% del
prompt): cada centro nuevo sube el gasto proporcionalmente. Ver
[decisions/gemini-costos-y-caching.md](../decisions/gemini-costos-y-caching.md).

---

## Codificación CIP del catálogo

Cada carrera tiene, además de su perfil en texto, **la escala del CIP a la que
pertenece**. Vive en `backend/data/cip_catalogo.json`, aparte de los archivos del
catálogo.

**Para qué.** El perfil en texto lo interpreta Gemini y el emparejamiento sale de
su criterio: funciona, pero no es auditable ni estable entre corridas. Con la
escala, la parte central del emparejamiento pasa a ser una consulta —un alumno con
percentil 92 en Biosanitaria (VII) tiene como candidatas las carreras VII del
catálogo, por aritmética— y Gemini queda redactando el porqué y desempatando. Eso
es lo que permite responder "¿por qué salió esta carrera?" con un número en lugar
de "el modelo lo decidió".

**Formato.** Una entrada por perfil distinto, no por registro carrera-sede:

```json
"medico_cirujano": {
  "nombre": "Médico y Cirujano",
  "principal": "VII",
  "secundaria": "II",
  "revisado": false
}
```

La clave es el `perfil_id` cuando la carrera comparte perfil entre sedes, y
`"centro::nombre"` cuando lo trae inline. Codificar por perfil (90) y no por
registro (202) garantiza por construcción que la misma carrera tenga el mismo
código en todas sus sedes.

**Cómo se genera.** `backend/codificar_cip.py`, una sola vez y offline:

```
uv run python codificar_cip.py --self-check   # sin red, valida el armado
uv run python codificar_cip.py --limite 5     # prueba de humo, 1 llamada
uv run python codificar_cip.py                # el resto
uv run python codificar_cip.py --revisar      # informe, sin llamar a Gemini
```

Es idempotente y resumible: solo pide lo que falta y guarda tras cada lote, así que
una corrida interrumpida no vuelve a gastar cuota. En tiempo de ejecución el
sistema solo lee el JSON: **cero llamadas y cero costo por alumno**.

**Estado de la corrida (2026-08-11):** 90/90 perfiles, 202/202 registros, en 4
llamadas.

| Escala | Registros | | Escala | Registros |
|---|---|---|---|---|
| VIII. Asistencial-Educacional | 57 | | XIII. Artístico-Plástica | 8 |
| X. Económica-Administrativa | 44 | | II. Físico-Química | 7 |
| VII. Biosanitaria | 28 | | IV. Tecnológica | 7 |
| IX. Jurídico-Política | 13 | | VI. Bioagropecuaria | 6 |
| III. Construcción | 12 | | XI. Comunicación Social | 5 |
| I. Cálculo | 9 | | XII, XV, V, XIV | 2, 2, 1, 1 |

El sesgo hacia Asistencial-Educacional y Económica-Administrativa no es un error de
la codificación: refleja la oferta real de Quetzaltenango y Totonicapán, donde las
pedagogías y las administrativas dominan el catálogo.

⚠️ **La codificación automática NO es el producto final.** Todas las entradas
salen con `"revisado": false`. La revisión de un profesional de orientación es
parte del trabajo, y es lo que permite escribir en el documento "codificación
asistida por IA, validada por profesional colegiada". Al revisar una entrada, se
le pone `"revisado": true`.

**Control de calidad ya hecho.** Se contrastó contra 28 asignaciones que un
orientador daría sin discusión (Médico→VII, Contaduría→X, Arquitectura→III,
Periodismo→XI…): **26 coincidieron**. Las 2 diferencias no son errores sino
ordenamientos discutibles, y en ambas la escala esperada quedó como secundaria:

- *Criminología* → principal II (Físico-Química), secundaria IX. Defendible: el
  trabajo forense de laboratorio es químico-analítico.
- *Producción Audiovisual* → principal XIII (Artístico-Plástica), secundaria XI.
  Defendible: es producción creativa antes que periodística.

Son justo el tipo de caso que la revisión humana debe resolver.

**Escalas con poca o ninguna oferta.** Geoastronómica y Artístico-Musical tienen
una sola carrera cada una. No es un defecto del catálogo: es información real y
útil. Un alumno con percentil alto ahí necesita que el sistema se lo diga en vez de
empujarlo a la carrera menos mala disponible.
