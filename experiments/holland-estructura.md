# Holland como estructura: el catálogo codificado con los RIASEC de O*NET

**Fecha:** 2026-08-16 · **Estado:** construido y medido. **El flag
`HOLLAND_EN_RECOMENDACION` queda apagado**: con la conversación presente, el
orden por afinidad RIASEC **no movió el top-1** en ninguno de los dos perfiles.
La codificación del catálogo sí queda hecha y es reutilizable.

Ámbito: catálogo de Quetzaltenango + Totonicapán (202 registros carrera-sede, 90
perfiles distintos), `gemini-3.1-flash-lite`. Banco de pruebas:
`backend/experimento_holland_estructura.py`.

---

## 1. Qué se probó y por qué

[holland-en-chat.md](holland-en-chat.md) §5.2 midió que el bloque de texto con el
resultado de Holland en el prompt **no mueve la recomendación**: con A=39 —el
área más alta de la alumna, medida por un instrumento oficial— en el prompt, en 5
de 6 corridas el top-1 fue de otra área. La conclusión de aquel informe, y la
decisión abierta #1 de [docs/holland.md](../docs/holland.md), era:

> Si Holland tiene que ser motor, entra como estructura, no como prosa: codificar
> el catálogo con los códigos RIASEC que O*NET publica por ocupación y ordenar
> por distancia al código del alumno.

Esto es ese experimento.

## 2. La codificación del catálogo (`codificar_holland.py`)

Para cada uno de los 90 perfiles del catálogo:

1. se busca el nombre de la carrera en el buscador **en español** de O*NET
   (`/mpp/search`, el mismo "Mi Próximo Paso" que sirve el test),
2. se toman las 3 primeras ocupaciones,
3. se les pide su perfil de intereses oficial
   (`/online/occupations/{code}/details/interests`, 0-100 por área),
4. se promedian los tres vectores.

Resultado: `backend/data/holland_catalogo.json`, 90/90 perfiles con vector
RIASEC, código de 3 letras y **las ocupaciones con las que se armó cada uno**.
Cero llamadas a Gemini: **los códigos no los inventa el modelo**, salen de la
misma fuente que califica el test del alumno. Esa es exactamente la ventaja que
el CIP no tenía ([cip-en-recomendacion.md](cip-en-recomendacion.md) §6).

Ejemplos, para ver que discrimina:

| Carrera | Código | Ocupaciones de O*NET usadas |
|---|---|---|
| Publicidad con Especialidad en Diseño Gráfico | **ACE** (A=86) | Diseñadores Gráficos; Directores de Arte; Diseñadores Web |
| Contaduría Pública y Auditoría | **CES** (C=85, E=82) | Contadores y Auditores; Supervisores de Oficina; Gerentes Financieros |
| Médico y Cirujano | **ISR** (I=94) | Cirujanos Pediátricos; Cirujanos Ortopédicos; Medicina Interna |

Y los límites, que son grandes y se ven a simple vista:

- **19 de 90 perfiles salieron `SIC`.** El buscador manda muchas carreras a
  "Profesores de … de Nivel Postsecundario" (Ingeniería Química → profesores de
  ingeniería, Teología → profesores de religión). El vector queda siendo el de
  *enseñar esa materia*, no el de *ejercerla*.
- Casos francamente mal emparejados: "Licenciatura en Comunicación y Diseño" →
  instaladores de torres de telefonía (`RCI`); "Administración de Empresas" →
  coordinadores de reciclaje entre las tres.
- Toda entrada lleva `"revisado": false`. **La revisión humana es parte del
  trabajo, no un adorno**: `--revisar` imprime carrera → código → ocupaciones
  usadas, en una sola pantalla, para poder corregirla a mano.

## 3. La puerta previa: el corte se cayó solo (otra vez)

Antes de gastar una sola llamada de Gemini, `--ranking` responde dónde queda la
carrera correcta con el catálogo ordenado por afinidad. Con un corte en 30
registros, como el que usaba `cip_filtro`:

| Perfil (código) | Su carrera | Puesto | ¿Sobrevive un corte en 30? |
|---|---|---|---|
| Dulce (**ASC**) | Publicidad c/ Diseño Gráfico | **59** | ❌ |
| Dulce (ASC) | Producción Audiovisual | 47 | ❌ |
| Melany (**CEI**) | Contaduría Pública y Auditoría | **12** | ✅ |

La causa es concreta y vale la pena anotarla: el vector de Diseño Gráfico es
**A+E+C** (el diseñador vende, cotiza y organiza), y Dulce es **A+S**. La
correlación baja a 0.31 y por delante se le cuelan todas las pedagogías, que son
S altas. Con la codificación anclada a ocupaciones de EE. UU., "arte" y "arte
para ayudar a gente" no son el mismo vector.

Es el mismo accidente que ya había dejado apagado el recorte al sector
([holland-en-chat.md](holland-en-chat.md) §3). La decisión de diseño que sale de
acá: **`TOP_HOLLAND = 0`, ordenar sin cortar**. Prioriza de verdad (Gemini lee el
catálogo en ese orden) y no puede excluir a nadie, que es lo que `filtro.py` ya
documenta para `/recommend`.

Notar de paso que para Melany el top del catálogo ordenado son las cinco
Ciencias Jurídicas (corr. 0.95) — su plan declarado, no lo que el chat descubre.
El vector RIASEC del derecho y el de la contaduría casi no se distinguen.

## 4. El A/B

Los dos brazos comparten **la misma conversación** (4 fijas + adaptativas, con el
bloque de Holland en el prompt), corrida una sola vez por perfil. La única
variable es el catálogo que ve Gemini al recomendar:

- **VIEJO** — producción de hoy: catálogo en su orden, Holland solo como prosa.
- **NUEVO** — `HOLLAND_EN_RECOMENDACION=1`: catálogo ordenado por correlación
  entre los seis puntajes del alumno y el vector RIASEC de cada carrera.

Compartir la conversación es lo que aísla la variable: en el experimento anterior
la varianza entre corridas fue **mayor** que la varianza entre brazos.

| Perfil | VIEJO | NUEVO |
|---|---|---|
| **Dulce** (ASC) | Enfermería 35% · Comunicación y Diseño 30% · Educación Inicial 20% | Enfermería 35% · Producción Audiovisual 30% · Fisioterapia 20% |
| **Melany** (CEI) | Contaduría 35% · Adm. de Sistemas Informáticos 25% · Ing. Industrial 20% | Contaduría 35% · Informática e Inteligencia de Negocios 30% · Adm. de Empresas 20% |

| Métrica | VIEJO | NUEVO |
|---|---|---|
| **El top-1 cambió** | — | **0/2** |
| Afinidad del top-1 | 35%, 35% | 35%, 35% |
| Confianza | 85%, 90% | 85%, 85% |
| Lo creativo en el top-3 de Dulce | sí | sí |

Costo de la corrida: 30 llamadas, 175k tokens de prompt, ~$0.05 equivalentes.

## 5. Lectura

**El orden del catálogo no es peso tampoco.** El top-1 no se movió en ninguno de
los dos perfiles, y lo que cambió fueron los puestos 2 y 3 — carreras del mismo
sector intercambiándose. Es el mismo resultado que dio el CIP priorizando el
catálogo (9/10 top-1 idénticos): **con la señal de la conversación presente, el
prefiltro estructural no aporta poder discriminante.**

Dulce sigue terminando en Enfermería. No es que el sistema no la "oiga": su nota
de confianza nombra los dos mundos y lo creativo se queda en el top-3 en los dos
brazos. Es que la alumna **declara** salud, y el modelo le hace caso por encima
de lo medido — con prosa y con estructura.

Dicho sin adorno: **codificar el catálogo con O*NET no convirtió a Holland en
motor de la recomendación.** Lo que sí produjo es un dato reutilizable y
defendible (el vector de cada carrera, anclado a una fuente oficial), y una
explicación de por qué el emparejamiento por vector falla donde falla (§3).

## 6. Decisión

1. **`HOLLAND_EN_RECOMENDACION` queda en `0`.** El sistema se comporta como
   antes. Revertir es no encender el flag.
2. **`TOP_HOLLAND = 0` (sin corte)** si alguien lo enciende: el corte, medido,
   borra la carrera correcta del perfil artístico.
3. **La codificación se conserva** (`data/holland_catalogo.json`): es barata de
   mantener, no cuesta nada en tiempo de ejecución y es el insumo de cualquier
   intento futuro.
4. **En la tesis no se puede decir que Holland alimenta la recomendación.** Ni
   como prosa (medido antes) ni como estructura (medido acá).
5. Lo que **sí** se puede afirmar, y con evidencia: el catálogo está codificado
   con una fuente oficial, la afinidad RIASEC alumno↔carrera es un número
   auditable, y ese número **no cambia el resultado** cuando ya hay una
   conversación de por medio.

## 7. Limitaciones

- **2 perfiles ficticios, 1 corrida cada uno.** Sirve para leer el mecanismo, no
  para afirmar una mejora ni descartarla con fuerza estadística. Compartir la
  conversación quita la varianza entre corridas pero no agrega potencia.
- **Revisión a mano: 6/90 corregidos** (2026-08-17). `administracion_empresas`
  emparejaba con "Coordinadores de Reciclaje", `periodismo` (Ciencias de la
  Comunicación Social) con puros profesores, y otras 4 (Administración
  Educativa x2, Economía Empresarial, Relaciones Internacionales) con sesgo de
  "profesor de la materia" en vez de "quien ejerce la carrera"; se corrigieron
  con una búsqueda más específica por el nombre de la ocupación real
  ("Superintendentes de Educación", "Analistas Económicos y Financieros",
  etc). El resto del catálogo llevaba `"revisado": true` desde antes sin que
  el contenido estuviera realmente corregido, ese flag no es confiable como
  métrica de avance. Un caso revisado y dejado tal cual: "Profesorado en
  Emprendimiento para la Productividad" busca mal ("Atletas y Competidores
  Deportivos") y no hay mejor término en español que probar, techo real del
  buscador de O*NET, no de la revisión.
- **El corte nunca se probó con Gemini.** Se descartó en la puerta previa por lo
  que le hace al perfil artístico. Probarlo solo con Melany sería elegir el
  perfil al que le conviene.
- La prueba decisiva sigue necesitando alumnos reales respondiendo el test.

## 8. Reproducir

```bash
cd backend
uv run python codificar_holland.py --self-check                  # sin red
uv run python codificar_holland.py                               # codifica (solo O*NET, gratis)
uv run python codificar_holland.py --revisar                     # informe para revisión humana
uv run python -m app.holland_filtro                              # self-check del filtro
uv run python experimento_holland_estructura.py --self-check     # sin red
uv run python experimento_holland_estructura.py --ranking        # la tabla de §3, sin Gemini
uv run python experimento_holland_estructura.py                  # el A/B
```

Crudos: `backend/data/tests/experimento_holland_estructura.json` (incluye las
transcripciones y el puesto de cada carrera en el catálogo ordenado).
