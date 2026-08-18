# Holland como estructura: el catálogo codificado con los RIASEC de O*NET

**Fecha:** 2026-08-16 · rev. 2026-08-18 (§8 revisión a mano de 90/90, §9 A/B
repetido) · **Estado:** construido y medido **dos veces**. **El flag
`HOLLAND_EN_RECOMENDACION` queda apagado**: con la conversación presente, el
orden por afinidad RIASEC **no movió el top-1** en ninguno de los dos perfiles,
ni con el catálogo sin revisar (§4) ni con el catálogo revisado (§9).
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
- Toda entrada nacía con `"revisado": false`. **La revisión humana es parte del
  trabajo, no un adorno**: `--revisar` imprime carrera → código → ocupaciones
  usadas, en una sola pantalla, para poder corregirla a mano. Los tres límites
  de esta lista se atacaron en **§8**, que también corrige el flag: había
  quedado en `true` en las 90 entradas sin que nadie las mirara.

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
   como prosa (medido antes), ni como estructura (medido acá), ni como
   estructura bien codificada (medido en §9, después de revisar el catálogo a
   mano y cambiar 18 códigos).
5. Lo que **sí** se puede afirmar, y con evidencia: el catálogo está codificado
   con una fuente oficial, la afinidad RIASEC alumno↔carrera es un número
   auditable, y ese número **no cambia el resultado** cuando ya hay una
   conversación de por medio. §9 lo deja más firme: la carrera de Melany subió
   del puesto 12 al 1 del catálogo ordenado y la recomendación no se movió.

## 7. Limitaciones

- **2 perfiles ficticios, 1 corrida cada uno.** Sirve para leer el mecanismo, no
  para afirmar una mejora ni descartarla con fuerza estadística. Compartir la
  conversación quita la varianza entre corridas pero no agrega potencia.
- **La codificación está revisada a mano, 90/90** (2026-08-18, ver §8), pero
  revisada no es lo mismo que correcta: 41 se dieron por buenas sin probarles
  alternativa, y varias arrastran techos del buscador que quedaron anotados
  (telecomunicaciones, lenguas mayas, los nombres híbridos).
- **El corte nunca se probó con Gemini.** Se descartó en la puerta previa por lo
  que le hace al perfil artístico. Probarlo solo con Melany sería elegir el
  perfil al que le conviene.
- **El A/B se corrió dos veces, con el mismo n.** §9 repite §4 con el catálogo
  revisado y vuelve a dar 0/2. Son 2 perfiles ficticios y 1 corrida por brazo
  las dos veces: dos negativos coincidentes leen mejor que uno, pero no
  sustituyen la potencia estadística que ninguno de los dos tiene.
- La prueba decisiva sigue necesitando alumnos reales respondiendo el test.

## 8. La revisión a mano (2026-08-17 y 2026-08-18)

§7 decía que la codificación no estaba revisada (0/90) mientras el JSON traía
`"revisado": true` en las 90 entradas. El flag estaba mal: nadie las había
mirado. Se revisaron en tres pasadas (20, luego 70, luego las 41 que quedaban
sin probar) y el flag pasó a significar una sola cosa: que alguien tomó una
decisión explícita sobre esa carrera y la dejó escrita. Los tres grupos viven en
`codificar_holland.py` con el motivo por entrada, y `--recodificar` los reaplica:
los arreglos son reproducibles, no ediciones sueltas del JSON.

### Las dos causas raíz

1. **Sesgo de "profesor de la materia".** El buscador manda el nombre académico
   a "Profesores de X de Nivel Postsecundario", o sea el vector de *enseñar* la
   carrera y no el de *ejercerla*. Ya estaba visto en §2 con los 19 `SIC`.
2. **"Pedagogía" devuelve una sola ocupación y equivocada:** "Profesores de
   Arte, Teatro, y Música". Es determinista, no azar, y contaminaba 6 entradas.
   En una de ellas ("Pedagogía (PEM en Comunicación y Lenguaje y Lic. en Diseño
   Curricular)") el vector entero salía de esa única ocupación, con A=79 y
   S=100 inventados. En los profesorados la docencia sí es la ocupación
   correcta, lo que estaba mal era la materia.

   Variante del mismo problema: "Física" se lee como *educación física*.
   "Licenciatura en Educación de la Física y Matemática" traía "Especialistas
   en Educación Física Adaptada" de primera.

Una tercera, vista en la 2.ª pasada: **en los nombres híbridos el buscador se
come la segunda mitad**. "Ingeniería Agrícola con Énfasis en Gerencia" devuelve
operadores de maquinaria y jornaleros, cero gerencia; "Administración de
Empresas Turísticas y Hoteleras" devolvía recepcionistas y guías, o sea el
personal de mostrador y no quien administra.

### Resultado

**Las 90 quedaron con una decisión explícita tomada**, en tres grupos que viven
en `codificar_holland.py`:

| Grupo | Cuántas | Qué significa |
|---|---|---|
| `TERMINOS_REVISADOS` | **25** | se le corrigió el término de búsqueda, con el motivo |
| `SIN_MEJOR_TERMINO` | **24** | se le probó una alternativa y **no mejoró**, con el número que la descartó |
| `YA_CORRECTAS` | **41** | se miró y no había hipótesis que probar (Médico y Cirujano → cirujanos, Enfermería → enfermeros, Contaduría → contadores) |

Contra el catálogo original: **18 códigos de 3 letras cambiados** y 7 más con el
mismo código y el vector más limpio.

Los peores casos que encontró la 2.ª pasada no eran de sesgo docente sino de
carreras a las que les faltaba **su rasgo definitorio**:

- **Profesorado en Educación Artística (Música y Danza)** era el único perfil
  de arte sin arte (A=34.3), indistinguible de cualquier otra pedagogía. Y la
  ocupación que le faltaba, "Profesores de Arte, Teatro y Música", es
  exactamente la que "Pedagogía" metía de más en las seis que no la
  necesitaban.
- **Ingeniería en Ciencias y Sistemas**, una carrera de computación, tenía
  tecnólogos eléctricos, mecánicos y directores de ciencias naturales. Cero
  computación.
- **Ingeniería en Administración de Tierras** traía las mismas tres ocupaciones
  que Ingeniería Mecánica, ninguna relacionada con la tierra.
- Las tres psicologías (general, clínica y educativa) compartían **un vector
  idéntico**: el catálogo no las distinguía. Educativa ya se separó; clínica y
  general siguen iguales y con este método no hay cómo separarlas.

### Lo que la revisión enseñó, y conviene no exagerar

- **Títulos limpios no son vector correcto.** "Administración de Empresas"
  emparejaba con "Coordinadores de Reciclaje", pero su código `ECS` ya era el
  correcto: los otros dos resultados eran gerentes y cargaban la E. Un intento
  intermedio con "Analistas de Gestión Empresarial" produjo una lista de
  títulos impecable y un vector peor (E de 75 a 51, S de 54 a 22, C a 86.7: el
  perfil de un analista de datos, no de un administrador). Hubo que mirar el
  vector, no la lista, para verlo. Mismo caso en Física y Matemática.
- **En la 2.ª pasada esto pasó de anécdota a regla: 10 de 23 alternativas
  probadas midieron peor y se rechazaron**, todas con una lista de ocupaciones
  que se leía mejor que la original. El patrón: pedir la ocupación profesional
  por su nombre ("Ingenieros Químicos", "Ingenieros Mecánicos") arrastra oficios
  de planta ("Operadores de Caldera") que suben la R y **bajan la I**, que es
  justo lo que distingue a un ingeniero. Los "Tecnólogos y Técnicos" que
  parecían el error daban un vector más equilibrado.
- Y al revés: ruido que parecía obvio resultó ser señal. El "Profesores de
  Inglés y Literatura" del técnico en música es lo que sostiene su A=82.3;
  quitarlo la baja a 64.7.
- Por eso el criterio de aceptación de un término corregido es **el vector**,
  y los intentos descartados quedaron escritos en los dicts junto al bueno,
  con el número que los descartó. Sirven para no volver a probarlos.
- **Esto no reabre la decisión de §6**, y ya no es una suposición: con los 16
  códigos cambiados se repitió el A/B entero y dio **0/2 otra vez** (§9). Lo
  que mejora es la afinidad RIASEC como **dato auditable**, que es lo que §5
  dice que este trabajo produjo.

El filtro automático por solapamiento léxico entre el nombre de la carrera y
los títulos de las ocupaciones **no sirve** y se descartó: "Comunicación y
Diseño" → "Diseñadores Gráficos" da cero palabras en común y es correcto. La
revisión fue leer el informe de `--revisar` entero, con el vector al lado.

### Los techos que quedan anotados, para no reintentarlos

- **Telecomunicaciones.** `Especialistas en Ingeniería de Telecomunicaciones`,
  `Ingenieros de Telecomunicaciones` y `Gerentes de Telecomunicaciones e
  Ingeniería` devuelven **las mismas 3 ocupaciones**, dos de ellas instaladores
  de líneas. O*NET en español no tiene gestión de telecomunicaciones. Su R=80.3
  está mal para una licenciatura y aun así se deja: la alternativa la dejaría
  con el vector *exacto* de otra carrera y sin nada de telecom.
- **Los híbridos pierden su segunda mitad y no hay cómo evitarlo.** "Ingeniería
  Agrícola con Énfasis en Gerencia" ya no es un jornalero (I de 22.7 a 79.7),
  pero la gerencia se sigue perdiendo.
- Lenguas mayas, hemodiálisis, emprendimiento, arquitectura y teología, ya
  documentados arriba.
- **Psicología Clínica y Psicología (PEM y Licenciatura) comparten vector** y
  con este método no hay forma de separarlas.

Que las 90 estén revisadas **no las vuelve correctas**: quiere decir que alguien
las miró y dejó dicho qué decidió. Los techos de esta lista siguen ahí.

## 9. El A/B repetido con el catálogo revisado (2026-08-18)

§8 cambió 16 códigos RIASEC (18 al terminar la 3.ª pasada), así que el A/B de §4
se volvió a correr entero. El A/B se corrió con los 16 primeros; las 2 entradas
que faltaban se corrigieron después y no se volvió a pagar la corrida.

### La puerta previa sí mejoró

Antes de gastar cuota, `--ranking`. La recodificación movió el orden de verdad:

| | §3 (catálogo sin revisar) | ahora |
|---|---|---|
| Melany · Contaduría Pública y Auditoría | puesto **12** | puesto **1** |
| Dulce · Publicidad c/ Diseño Gráfico | puesto 59 | puesto 59 |
| Dulce · top-1 del catálogo ordenado | pedagogías de S alta | **Profesorado en Educación Artística** |

Para el perfil artístico el catálogo ordenado ahora encabeza con la carrera de
arte, que es exactamente la entrada que §8 arregló (A=34.3 → 61). Diseño
Gráfico sigue en el puesto 59 por la razón de §3, que no era de codificación:
Dulce es A+S y el diseñador de O*NET es A+E+C.

### El resultado: idéntico

| Perfil | VIEJO | NUEVO |
|---|---|---|
| **Dulce** (ASC) | Enfermería 35% · Comunicación y Diseño 30% · Producción Audiovisual 20% | Enfermería 35% · Producción Audiovisual 30% · Educación Primaria 20% |
| **Melany** (CEI) | Contaduría 35% · Adm. de Empresas 25% · Adm. de Sistemas 20% | Contaduría 35% · Adm. de Empresas 25% · Informática e Inteligencia de Negocios 20% |

| Métrica | §4 (sin revisar) | ahora (revisado) |
|---|---|---|
| **El top-1 cambió** | **0/2** | **0/2** |
| Afinidad del top-1 | 35%, 35% | 35%, 35% |
| Lo creativo en el top-3 de Dulce | sí | sí |

Costo: 15 llamadas, 173k tokens, ~$0.03 equivalentes. La primera corrida se
cortó con un **503 de Google** después de Dulce (el mismo que dejó sin medir a
`gemini-3.7-flash` en [comparacion-modelos.md](comparacion-modelos.md)); el
script es resumible y el reintento solo corrió a Melany.

### Lectura: la evidencia se hizo más fuerte, no más débil

**Melany es el caso que lo prueba.** Su carrera pasó del puesto 12 al **puesto
1** del catálogo ordenado: Gemini ahora la lee de primera en la lista, con la
mejor afinidad RIASEC posible. La recomendación **no se movió ni un punto** (35%,
confianza 90%, mismo top-1 en los dos brazos). Antes se podía objetar que el
orden no cambiaba nada porque el orden estaba mal calculado. Ya no: el orden
mejoró mucho y el resultado es el mismo.

Y Dulce sigue en Enfermería aunque el catálogo ordenado le ponga el profesorado
de arte en el primer lugar. Es lo que §5 ya decía: la alumna **declara** salud y
el modelo le hace caso por encima de lo medido, con prosa, con estructura y
ahora también con estructura bien codificada.

Lo que queda igual que en §6: **`HOLLAND_EN_RECOMENDACION` sigue en `0`** y en
la tesis no se puede decir que Holland alimenta la recomendación. Lo que sí se
gana con §8 es que la afinidad RIASEC alumno↔carrera es ahora un número
auditable **y además correcto** en 41 de 90 perfiles, no solo auditable.

Sigue siendo **2 perfiles ficticios y 1 corrida por brazo**: sirve para leer el
mecanismo, no para cerrar la pregunta con fuerza estadística.

Crudos: `backend/data/tests/experimento_holland_estructura.json` (esta corrida)
y `..._precodificacion.json` (la de §4, con el catálogo sin revisar).

## 10. Reproducir

```bash
cd backend
uv run python codificar_holland.py --self-check                  # sin red
uv run python codificar_holland.py                               # codifica (solo O*NET, gratis)
uv run python codificar_holland.py --revisar                     # informe para revisión humana
uv run python codificar_holland.py --recodificar                 # reaplica los arreglos a mano (§8)
uv run python -m app.holland_filtro                              # self-check del filtro
uv run python experimento_holland_estructura.py --self-check     # sin red
uv run python experimento_holland_estructura.py --ranking        # la tabla de §3, sin Gemini
uv run python experimento_holland_estructura.py                  # el A/B
```

Crudos: `backend/data/tests/experimento_holland_estructura.json` (incluye las
transcripciones y el puesto de cada carrera en el catálogo ordenado).
