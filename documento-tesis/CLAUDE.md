# Documento de Tesis (Word) — CLAUDE.md

Esta carpeta **no contiene el .docx** (vive fuera del repo, en `C:\Users\hgo32\Downloads\`).
Es solo memoria escrita del estado del documento de tesis y de la guía UMG, para que
cualquier sesión futura (yo u otra instancia de Claude) retome el trabajo sobre el Word
sin perder contexto ni repetir análisis ya hechos. Complementa al `CLAUDE.md` de la raíz
del repo (que es sobre la app/código, no sobre el documento escrito).

**Archivos relevantes (en Downloads, no en el repo):**
- `tesis_corregida_v3.docx` — versión original, sin las correcciones de esta sesión.
- `tesis_corregida_v3_tablas_sin_lineas.docx` — **versión vigente**, con todas las
  correcciones descritas abajo. Es la que se debe seguir editando.
- `22-08-2025 GUIA, PG GENERAL (1) (3).pdf` — guía oficial UMG de formato y redacción
  (Ingeniería en Sistemas). Resumida íntegra más abajo.

---

## De qué trata el proyecto (leído del documento completo, no solo del índice)

**Orienta** es el nombre de la plataforma que desarrolla esta tesis: un sistema web
conversacional de orientación vocacional, sustentado en inteligencia artificial, para
estudiantes de nivel diversificado y de primer ingreso universitario de los
departamentos de **Quetzaltenango y Totonicapán**, Guatemala. El hilo argumentativo del
documento, de principio a fin, es el siguiente.

**El problema.** Elegir carrera es una de las decisiones más determinantes en la vida
de un joven guatemalteco, pero miles de estudiantes la enfrentan sin acceso a
orientación vocacional de calidad, sin herramientas adaptadas al contexto nacional y
sin información suficiente sobre la oferta académica real de su región. El documento
respalda esto con evidencia: la elección vocacional inadecuada es un factor
documentado de deserción universitaria (Erazo Guerra y Rosero Morales, 2021), y en
Guatemala no existe, a la fecha de la investigación, una herramienta de este tipo
adaptada a la oferta académica nacional — vacío que el proyecto se propone cerrar. La
pregunta de investigación central es si es posible diseñar e implementar un sistema de
orientación vocacional con IA que oriente a esos estudiantes de forma personalizada,
accesible y confiable.

**Por qué ahora (justificación).** El argumento no es solo "hace falta", sino "ya es
posible": la madurez de los modelos de lenguaje, la nube y la conectividad móvil hacen
viable, técnica y económicamente, una solución que antes no lo era. El documento es
explícito en que esto no busca sustituir al orientador vocacional humano, sino extender
su alcance a poblaciones y contextos donde hoy no llega — y en que el rigor técnico
(validación, pruebas con usuarios reales, métricas objetivas) no es negociable, porque
una recomendación vocacional equivocada puede ser tan dañina como no dar ninguna.

**Objetivos y cómo se miden.** El objetivo general es evaluar el impacto de la
plataforma sobre la precisión y pertinencia de las recomendaciones y sobre el nivel de
aceptación de los usuarios. Se desglosa en cuatro objetivos específicos medibles:
caracterizar el perfil vocacional de los estudiantes a partir del cuestionario; medir
la precisión del motor de recomendación contra un conjunto de validación, con una
**meta explícita de precisión superior al 70%**; determinar la relación entre la
calidad/cobertura del catálogo de carreras y la pertinencia de las recomendaciones; y
evaluar la satisfacción y aceptación de los usuarios mediante pruebas de usabilidad.

**Diseño de la investigación y muestra.** Es un estudio de enfoque exploratorio y
aplicado (con un componente descriptivo en la fase de validación), planteado como
**estudio piloto de caso único**: una sola institución educativa de nivel
diversificado en Quetzaltenango o Totonicapán, con muestreo no probabilístico por
conveniencia. La muestra prevista es de **~300 estudiantes** de tercero básico y del
último año de diversificado (14–18 años), más orientadores y personal académico que
validan los instrumentos y las recomendaciones. No busca representatividad estadística
departamental ni nacional — es una validación inicial, no un estudio poblacional.

**Alcance y límites, con honestidad metodológica.** El documento delimita con
precisión lo que el sistema SÍ cubre (catálogo real de Quetzaltenango y Totonicapán,
sistema funcional desplegado, con manual de usuario) y lo que deliberadamente NO
cubre (carreras fuera de esos dos departamentos, opciones en el extranjero). También
declara sus límites de forma explícita en vez de ignorarlos: depende de una API externa
de pago/cuota (Gemini) cuya disponibilidad no controla, lo que puede afectar el volumen
de solicitudes procesables; el costo por token puede crecer con el tráfico; y el
calendario académico limita cuántas iteraciones de desarrollo y prueba son posibles
antes de la entrega. Frente a esto, el documento no promete lo que no puede sostener:
prioriza funcionalidades esenciales y documenta el resto como trabajo futuro.

**La solución técnica.** Orienta se describe (Capítulo IV) como una arquitectura en
tres capas más un servicio externo: presentación (React/Vite: chat, mapa de
Guatemala, tablero de resultados, catálogo consultable, reporte PDF), aplicación
(FastAPI/Python 3.12: coordina el cuestionario, aplica el prefiltro del catálogo,
construye las instrucciones para el modelo) y datos (PostgreSQL: estudiantes,
respuestas, catálogo, consumo de recursos). El motor de recomendación es un modelo de
lenguaje (Gemini, de Google) consumido con salida estructurada validada con Pydantic —
nunca texto libre sin esquema. Esta arquitectura es también el argumento de
sostenibilidad del proyecto: la interfaz se puede rediseñar sin tocar la lógica de
recomendación, el proveedor del modelo se puede cambiar sin rediseñar el sistema
completo (el contrato es un esquema de datos, no el modelo en sí), y agregar un
departamento nuevo es cuestión de cargar un catálogo, no de reescribir código.

**Catálogo real, no simulado.** Al momento de esta documentación, el catálogo carga
202 registros de carrera por sede (147 nombres de carrera distintos), en 12 centros de
10 universidades: 185 registros en Quetzaltenango y 17 en Totonicapán. Cada registro
lleva nombre de carrera, universidad, centro, departamento y un perfil vocacional en
texto (afinidades, habilidades, entorno, intereses, estilo cognitivo) — ese perfil es
lo que el motor de IA usa para recomendar, y solo puede recomendar carreras que de
verdad existen en ese catálogo (no inventa oferta académica).

**Las 8 características que el documento destaca del sistema ya construido**:
formato conversacional con opción de retroceder y de escuchar los mensajes en voz;
delimitación territorial por mapa interactivo (el departamento elegido filtra todo lo
demás); preguntas adaptativas cuya cantidad varía (4 a 8) según qué tan definido esté
el perfil del estudiante; recomendaciones agrupadas por carrera (no repetidas por cada
sede que la ofrece); un tablero con gráfica de barras, gráfica de dona y reporte PDF
descargable; dos funciones opcionales de exploración (simular una jornada laboral de
la carrera, comparar dos carreras); y validación/seguridad del nombre del estudiante
más medición del consumo de recursos por sesión (para que el costo sea un dato medible,
no una estimación).

**Coherencia con el proyecto de código (raíz del repo):** esta descripción del
sistema coincide con lo ya implementado y documentado en el `CLAUDE.md` de la raíz del
repo (mismo stack, mismo flujo híbrido de preguntas fijas + adaptativas, mismo motor
Gemini con salida estructurada, mismas 7 dimensiones vocacionales, mismo dashboard con
barras/dona/PDF). Es decir: **el documento de tesis describe con fidelidad el sistema
que ya existe en `backend/` y `frontend/`** — no es una propuesta aspiracional
desconectada del código. Cualquier cambio futuro al código que afecte estos puntos
(arquitectura, endpoints, catálogo, dimensiones, características del chat/tablero)
debería reflejarse también en el Capítulo IV del Word para no romper esa coherencia.

---

## 1. Historial de modificaciones hechas al Word (esta sesión)

1. **Quitar líneas de columna (verticales) de las 16 tablas.** Antes, la Tabla 1 tenía
   cuadrícula completa (estilo Word "Table Grid") y las Tablas 5–16 tenían líneas
   verticales delgadas; las Tablas 2–4 ya no las tenían. Se dejaron solo líneas
   horizontales (arriba, abajo, entre filas).
2. **Unificar el estilo de las Tablas 1–4 al de las Tablas 5–16** (que ya eran
   consistentes entre sí y visualmente más cuidadas): encabezado azul marino
   `#12294D` con texto blanco negrita centrado, filas de datos alternadas
   sin relleno / `#EEF2F9`, letra de cuerpo 10 pt. Antes, las Tablas 1–4 no tenían
   color, letra 12 pt y encabezado sin resaltar.
   - Decisión del usuario: se aceptó explícitamente que este cambio de tamaño de
     letra iba a re-paginar el documento (12 pt → 10 pt reduce el espacio que ocupan
     esas 4 tablas).
3. **Verificación de las 5 figuras** contra el índice de figuras: conteo, numeración
   correlativa, título exacto y páginas cacheadas — todo correcto, no requirió cambios.
4. **Corrección de 3 tablas con título "huérfano"** (defecto preexistente, no
   introducido en esta sesión): el título "Tabla N." y su descripción quedaban solos al
   final de una página, con la tabla real recién en la página siguiente. Afectaba a las
   Tablas 7, 10 y 16. Se corrigió agregando `keepNext` al párrafo del título y al de la
   descripción, para que Word ya no los separe de la tabla en un salto de página.
5. **Actualización de los tres índices** (general, de tablas, de figuras): los números
   de página son campos de Word con un valor cacheado que **no se recalcula solo** al
   editar el XML por script. Tras los cambios de los puntos 2 y 4 (que sí mueven
   contenido), se refrescaron los tres índices vía automatización de Word
   (`Fields.Update()` + repaginar + guardar) y se verificó cada entrada contra su
   página real en el PDF exportado.

## 2. Estilo de tablas vigente (no revertir sin querer)

- Las 16 tablas comparten: sin líneas verticales; encabezado con relleno `#12294D`,
  texto blanco, negrita, centrado, 10 pt; filas de datos alternadas sin relleno /
  `#EEF2F9`; letra de cuerpo 10 pt (`sz=20` en el XML).
- Estructura de cada tabla en el documento: párrafo "**Tabla N.** Título" (con
  `bookmarkStart`/campo `SEQ Tabla`, es lo que alimenta el índice de tablas) → párrafo
  descriptivo de una oración (10 pt) → la tabla → párrafo "Tabla N. Título. Fuente:
  Elaboración propia." (9 pt) inmediatamente después.
- Las Tablas 7, 10 y 16 llevan `keepNext` explícito en el título y en la descripción
  — no quitarlo, es lo que evita que el título quede huérfano en la página anterior.
- **Pendiente cosmético, no resuelto a propósito:** las Tablas 3 y 4 declaran un ancho
  de tabla (`tblW`) ligeramente distinto (9342 y 9493 respectivamente) al resto (9360).
  Diferencia menor a 0.1 pulgada, invisible al ojo; no se corrigió porque implicaría
  recalcular a mano el ancho de cada columna de esas dos tablas, con riesgo de romper
  el layout, para un beneficio prácticamente nulo.

## 3. Los tres índices — por qué se desactualizan y cómo verificarlos

El documento tiene tres campos TOC (tabla de contenido) distintos:
- **Índice general**: `TOC \o "1-3" \h \z \u` (hoja vi), 123 entradas (niveles 1–3).
- **Índice de tablas**: `TOC \h \z \c "Tabla"` (hoja vii).
- **Índice de figuras**: `TOC \h \z \c "Figura"` (hoja viii).

Cada entrada guarda un **número de página cacheado como texto plano** dentro del XML,
no un valor recalculado en vivo. Cualquier edición que cambie cuánto espacio ocupa el
contenido ANTES de un título/tabla/figura (tamaño de letra, márgenes, una tabla que
crece o encoge, un párrafo que se agrega o se quita) puede desfasar ese número sin que
nada "se rompa" visualmente ni el validador de esquema lo detecte — hay que revisarlo
a propósito.

**Regla para cualquier edición futura de contenido o formato:**
1. Editar el XML.
2. Validar contra el esquema (ver sección 4).
3. Abrir con Word (o vía COM) y refrescar TODOS los campos: seleccionar todo → F9,
   o por automatización: `doc.Fields.Update()` + `doc.Repaginate()` + guardar.
4. Exportar a PDF y comparar **cada entrada de cada índice, una por una, por su
   título**, contra la página real donde aparece ese contenido en el PDF. No basta con
   ver que el conteo total de páginas no cambió — un documento puede mantener el mismo
   número de páginas totales y aun así tener 3-5 títulos internos desplazados (le pasó
   a este documento: el conteo total se mantuvo en 104 páginas de PDF después del
   cambio de fuente de las Tablas 1-4, pero 5 títulos del índice general y 1 tabla del
   índice de tablas quedaron con el número cacheado equivocado).

## 4. Cómo editar y verificar el .docx (flujo probado en esta sesión)

Esta máquina **no tiene LibreOffice ni poppler (pdftoppm) instalados** — el flujo
estándar del skill `docx` para convertir a PDF/renderizar falla ahí. Alternativa usada:

1. Descomprimir el .docx (`unzip` o `zipfile` de Python) y usar el flujo del skill
   `docx` del repo (unzip → editar `word/document.xml` → rezip).
2. Para ediciones de estructura (no solo texto), usar `lxml.etree` en vez de
   reemplazos de texto por regex — Word es muy estricto con el **orden de los hijos**
   dentro de `<w:pPr>` (`CT_PPrBase` es una `xsd:sequence`, no un `xsd:choice`: un
   `<w:jc>` insertado después de un `<w:cnfStyle>` invalida el documento). El `<w:rPr>`
   de una corrida (`<w:r>`) en cambio es un `xsd:choice` sin límite de repeticiones, así
   que ahí el orden de los hijos no importa.
3. Validar con el `validate.py` del skill `docx`, comparando contra el original:
   `PYTHONUTF8=1 python validate.py <nuevo>.docx --original <original>.docx`.
   **Importante:** en esta máquina Windows, correr `validate.py` SIN `PYTHONUTF8=1`
   produce falsos "nuevos errores" porque el script abre XML con `open(archivo, "r")`
   sin especificar `encoding="utf-8"`, y Python cae al cp1252 del sistema. Es un bug
   del propio script, no del documento — siempre usar `PYTHONUTF8=1`.
4. Para convertir a PDF (ya que no hay LibreOffice), usar Word por COM desde
   PowerShell:
   ```powershell
   $word = New-Object -ComObject Word.Application
   $word.Visible = $false
   $doc = $word.Documents.Open("<ruta>.docx")
   foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
   $doc.Fields.Update()
   $doc.Repaginate()
   $doc.Save()
   $doc.SaveAs([ref]"<ruta>.pdf", [ref]17)
   $doc.Close(); $word.Quit()
   ```
5. Para inspeccionar el PDF (tampoco hay poppler), usar PyMuPDF
   (`pip install pymupdf`, es rápido y no tiene dependencias del sistema):
   extraer texto por página, comparar contra los números cacheados del índice.

## 5. Estructura y flujo actual del documento (resumen del índice general)

El índice general tiene 123 entradas (niveles 1–3). Mapa de capítulos actual:

| Sección | Página (actual) |
|---|---|
| Portada, hojas preliminares (i–xii, romanos) | — |
| INTRODUCCIÓN | 1 |
| CAPÍTULO I – ANTEPROYECTO (1.1 Antecedentes … 1.18 Recursos) | 2–23 |
| CAPÍTULO II – MARCO TEÓRICO (2.1 Orientación vocacional … 2.5 Educación en Guatemala) | 25–47 |
| CAPÍTULO III – SEGUNDO TEÓRICO - COMPLEMENTARIO (3.1 Metodologías … 3.11 Pruebas de software) | 48–67 |
| CAPÍTULO IV – PRIMER PRÁCTICO: ANÁLISIS Y DESCRIPCIÓN DEL ENTORNO (4.1 … 4.7 Cronogramas) | 68–86 |
| BIBLIOGRAFÍA | 89–92 (última sección) |

El documento arábigo termina en la página 92, dentro de la bibliografía.

### ⚠️ Vacío estructural crítico — confirmar antes de la entrega final

Se buscó en **todo** el XML del documento (no solo en el índice) y **no existe ninguna
ocurrencia** de: `CAPÍTULO V`, `CAPÍTULO VI`, `CONCLUSIONES`, `RECOMENDACIONES`,
`GLOSARIO`, ni `ANEXOS`. El documento termina en la Bibliografía.

Según la guía UMG (sección 6 de este archivo), la estructura esperada tiene 5–6
capítulos: los Capítulos I–III son de "Proyecto de Graduación I" y los Capítulos
IV–VI de "Proyecto de Graduación II" (diseño e implementación), seguidos de
Conclusiones, Recomendaciones, Glosario, Bibliografía y Anexos. Este documento ya
incluye el Capítulo IV (que es material de PG2: requerimientos, RUP, cronogramas) pero
se detiene ahí — faltarían, si se sigue el patrón de la guía:
- Capítulo V (diseño: modelado de negocio, UML/casos de uso, diagrama ER, prototipos).
- Capítulo VI (implementación: pruebas, puesta en producción, segmentos de código).
- Conclusiones, Recomendaciones, Glosario, Anexos.

**No asumir que es un error** — puede ser intencional si esta entrega corresponde a
una fase intermedia (p. ej. "PG1 + Capítulo IV" como corte parcial). Pero si el
objetivo es la tesis completa, esto es lo primero que falta. Confirmar con el
estudiante o el asesor antes de dar por "terminado" el documento.

## 6. Guía UMG — reglas a recordar siempre (de "22-08-2025 GUIA, PG GENERAL")

Fuente: guía oficial de Ingeniería en Sistemas de Información, UMG, para la revisión
del proyecto de graduación (formato UMG + Normas APA parciales).

### Formato físico del documento
- Papel bond 60 g, tamaño carta.
- Fuente Times New Roman o Arial, **12 pt, en todo el documento** (ver ⚠️ en la
  sección de tablas/figuras más abajo — hay una tensión con el 10 pt ya usado dentro
  de las tablas).
- Títulos en negrita, sin subrayado.
- Interlineado 1.5 (la guía es explícita: usar 1.5 y no el 2.0 de APA, "pierde forma y
  vista el documento"). Espacio entre párrafos de 2.0 puntos.
- Márgenes: superior, inferior, izquierdo y derecho, 2.54 cm.
- Sangría de 5 espacios o un TAB al inicio de cada párrafo.
- Párrafos de 6 a 10 líneas; no dividir en subtemas/subtítulos dentro de un mismo
  párrafo.
- No cortar un párrafo justo al cambiar de hoja. Los títulos no deben quedar solos
  ("huérfanos") al pasar a una hoja nueva — exactamente el defecto que se corrigió en
  las Tablas 7, 10 y 16 (sección 1, punto 4).
- Numeración de página: preliminares en números romanos minúscula, centrado abajo;
  cuerpo en arábigos, centrado abajo, sin guiones ni palabras, empezando en 1 en la
  Introducción.
- Diagramas muy anchos: usar hoja en orientación horizontal (par o impar según el
  ejemplo de la guía), indicando bien la ubicación de la numeración de página en esa
  hoja.

### Redacción
- Redacción **impersonal**, en **voz activa** (no "ha sido observado, se ha contado,
  fue llevado" → sí "se observó, se contó, se llevó").
- Evitar gerundios y adverbios de modo en exceso.
- Evitar coloquialismos: "ya que", "puesto que", "hoy por hoy", "hoy en día", "aquí",
  "ahí", "acá", entre otros.
- No repetir la misma palabra dentro de un mismo párrafo — sustituir por sinónimos.
- Evitar palabras rebuscadas o de difícil comprensión.
- No usar "etc." — sustituir siempre por "entre otros".
- Las décadas se escriben completas: "década de los noventa", no "los 90s".
- No usar extranjerismos, salvo dentro de una cita textual (ejemplo dado: Voucher,
  Inbox, Sticker). Las palabras en inglés que aparezcan van en cursiva (ej.
  *Software*).
- No usar viñetas para subdividir párrafos. Las viñetas solo se permiten en
  subdivisiones de **nivel 4** (el índice llega hasta nivel 3; nivel 4 no aparece en
  el índice).
- Ningún título ni subtítulo del índice lleva ":" al final ni paréntesis con
  aclaraciones tipo "(ABC)".
- Cada título o subtítulo debe caber en **una sola línea** del índice (si se pasa de
  línea, se ve desordenado).
- Citas y referencias bibliográficas según el Reglamento de Tesis UMG + Normas APA
  parciales (versión vigente).
- Máximo 20% de citas de fuentes exploratorias (internet); el resto debe ser de
  fuentes primarias. Las fuentes de internet usadas deben ser de sitios verificables.
- No copiar texto de forma literal sin la cita correspondiente — usar herramientas
  antiplagio antes de entregar.

### Estructura de capítulos (los títulos del ejemplo de la guía son solo ilustrativos,
no obligatorios usarlos tal cual — "Los títulos utilizados son para ejemplo, no es
para que sean utilizados en su documento")
- 5 o 6 capítulos en total. Cada capítulo: mínimo 15, máximo 20 páginas.
- **Capítulo I** (fase PG1) — Anteproyecto/Propuesta del negocio, máx. 20 páginas:
  antecedentes (6–8 páginas), justificación, planteamiento del problema, objetivos
  (uno general + mínimo 3 específicos, medibles), viabilidad/factibilidad, alcances,
  límites, hipótesis (solo si el alcance no es exploratorio), variables, indicadores,
  supuestos, herramientas/técnicas de investigación, población y muestra,
  planificación (Gantt).
- **Capítulo II** (fase PG1) — Marco teórico, primer tema principal: conceptos y
  subtemas del marco teórico, **mínimo 25 páginas**, con cita o referencia en
  **cada página** (una página sin cita normalmente delata opinión propia, contenido
  plagiado o relleno). No incluir opiniones del autor ni citas textuales en el marco
  conceptual/planteamiento del problema — es descripción propia del autor sobre el
  problema detectado.
- **Capítulo III** (fase PG1) — Segundo teórico, complementario: teoría de la
  metodología a implementar y de las herramientas a utilizar.
- **Capítulo IV** (fase PG2) — Primer práctico, análisis y descripción del entorno:
  análisis y diseño del sistema, levantamiento de requerimientos, funcionamiento
  actual (con diagrama), características principales, identificación de usuarios,
  RUP/ciclo de vida/fases/artefactos, cronogramas de planificación.
- **Capítulo V** (fase PG2) — Segundo práctico, diseño: herramienta de diagramación
  (opcional, breve), modelado de negocio, UML (casos de uso con tabla y diagramas
  pertinentes), diagrama ER, presentación de prototipos (pantallas).
- **Capítulo VI** (fase PG2) — Tercer práctico, implementación: presentación del
  proyecto, pruebas internas y externas, configuraciones/capacitaciones/puesta en
  producción, resúmenes de código (solo segmentos relevantes, no todo).
- **Conclusiones**: ligadas a los objetivos, la comprobación de la hipótesis, el
  problema planteado y los indicadores. Entre 3 y 5 líneas cada una.
- **Recomendaciones**: derivadas de las conclusiones, dirigidas a distintos actores
  (empresa, otras empresas, usuarios, programadores, directores, docentes,
  universidades, etc.). Entre 3 y 5 líneas cada una. La frase "se recomienda" **no**
  debe ir dentro del texto de la recomendación misma.
- **Glosario**: orden alfabético, cada definición justificada y con contenido real
  (no una sola línea sin sentido).
- **Bibliografía**: orden alfabético, con margen francés (sangría francesa) por cada
  ítem — **esto ya está correctamente implementado** en el documento actual
  (`ind left=720 hanging=720` en cada referencia).
- **Anexos**: no deben ser muy extensos. Incluir encuestas, entrevistas,
  cuestionarios, cartas de autorización y de entrega del proyecto, mapa mental del
  tema, y segmentos de código fuente relevantes (acceso a base de datos,
  mantenimientos/procesos del sistema, manejo de usuarios/accesos) — el código puede
  ir con interlineado menor para no ocupar tanto espacio, y solo los segmentos más
  importantes, no todo el código.
- Ningún trabajo puede entrar a la defensa si no está terminado.

### Portada y páginas preliminares
- Carátula 1, llamada "Guarda".
- Carátula 2: título de la tesis (sin comillas, sin caracteres especiales, evitar
  palabras en inglés), "TRABAJO DE GRADUACIÓN PRESENTADO POR: [nombre]", grados a
  optar, lugar y fecha (formato "GUATEMALA, MES DEL 20##").
- Escudo de la universidad: 11 × 11 cm, en ambas carátulas.
- Hoja "iii": autoridades de la facultad y asesor.
- Hoja "iv": autorización para la impresión, en negrita, centrada en la hoja.
- Hoja "v": Reglamento del Trabajo de Graduación, Artículo 8 (Responsabilidad),
  centrado en la página.
- Hoja "vi": índice general.
- Hoja "vii": índice de tablas (si aplica).
- Hoja "viii": índice de figuras (si aplica).
- El número de hoja de estos últimos tres puede variar según el contenido.

### Tablas y figuras (formato de ejemplo de la guía)
- Solo existen dos tipos de elemento visual: **Tabla** y **Figura**. Cualquier
  gráfica o imagen que no sea una tabla se llama "Figura" (no "gráfica", no
  "imagen", no "diagrama" como categoría separada en el índice).
- Cada tipo tiene su propio índice (de Tablas en hoja vii, de Figuras en viii),
  siguiendo el mismo formato de interlineado y orden que el índice general.
- Encima del elemento: "**Tabla N.** Título" o "**Figura N.** Título", seguido de un
  texto de definición de 2 a 4 líneas (mínimo 2, máximo 3–4) antes del contenido.
- Debajo del elemento: "Tabla N. Título. Fuente: Elaboración propia." (o la cita de
  la página de origen si no es propia, ej. Wikipedia.org). Esta línea puede ir en
  **tamaño 9**.
- ⚠️ **Conflicto a verificar con el asesor**: la guía pide 12 pt "en todo el
  documento" para la fuente general, y solo exime explícitamente el tamaño 9 para la
  línea "Fuente: ...". El **contenido interior** de las tablas de este documento usa
  10 pt (heredado del estilo que ya traían las Tablas 5–16 antes de esta sesión, y
  que se replicó a las Tablas 1–4 para unificar el diseño — ver sección 2). La guía
  no exime explícitamente ese tamaño para el interior de una tabla. Es una práctica
  común en tesis reducir la letra dentro de tablas anchas para que quepan las
  columnas, pero no está escrito como excepción en esta guía — **confirmar con el
  asesor/revisor si 10 pt en el cuerpo de las tablas es aceptable**, o si hay que
  subirlo a 12 pt (lo cual probablemente rompa el ajuste de columnas de varias
  tablas y requeriría rediseñarlas).
