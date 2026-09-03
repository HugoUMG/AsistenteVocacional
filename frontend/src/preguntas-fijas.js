// Las preguntas FIJAS del chat: las que se hacen siempre y sin llamar a la IA.
// Viven fuera de Chat.jsx porque también las lee el historial (para separar
// estas de las adaptativas al dibujar el recorrido), y porque un archivo que
// exporta componentes Y constantes rompe el refresco en caliente de Vite.
//
// Son catálogo-agnósticas: no mencionan carreras concretas.

// El nivel académico decide TODO lo que se pregunta después: qué grados se
// ofrecen, cómo se pregunta la carrera y el gusto, y por qué está haciendo el
// test. Se arma como tabla y no como ifs regados: agregar un nivel o un grado
// es agregar una fila.
//
// En cada grado: 'carrera' es cómo se pregunta qué estudia o estudió (null =
// no aplica, en básicos no hay carrera que nombrar); 'gusto' es la pregunta de
// si le gustó, en presente o pasado según el caso ({carrera} se sustituye por
// lo que acaba de escribir); 'descarta' marca la carrera que abandonó, para
// sacarla del catálogo antes de recomendar (ver backend/app/filtro.py).

const MOTIVOS_MEDIO = [
  { label: 'Quiero saber qué estudiar' },
  { label: 'Quiero conocer más opciones' },
  { label: 'Quiero confirmar lo que ya tenía pensado' },
]

const MOTIVOS_UNIVERSIDAD = [
  { label: 'Quiero seguir una segunda carrera' },
  { label: 'Quiero conocer más opciones' },
  { label: 'Quiero cambiar de carrera' },
]

const EJEMPLOS_DIVERSIFICADO = 'Por ejemplo: bachillerato en computación, perito contador o magisterio.'

const NIVELES = [
  {
    label: 'Básico',
    motivos: MOTIVOS_MEDIO,
    grados: [
      { label: 'Primero básico' },
      { label: 'Segundo básico' },
      { label: 'Tercero básico' },
      { label: 'Ya terminé los básicos' },
    ].map((g) => ({ ...g, carrera: null, gusto: '¿Te gusta lo que estás llevando en el colegio?' })),
  },
  {
    label: 'Diversificado',
    motivos: MOTIVOS_MEDIO,
    grados: [
      // Bachillerato son 2 años (4o y 5o); magisterio, perito y las demás
      // carreras de diversificado son 3 (4o, 5o y 6o).
      { label: 'Cuarto bachillerato' },
      { label: 'Quinto bachillerato' },
      { label: 'Cuarto de perito, magisterio u otra carrera de 3 años' },
      { label: 'Quinto de perito, magisterio u otra carrera de 3 años' },
      { label: 'Sexto de perito, magisterio u otra carrera de 3 años' },
      {
        label: 'Ya terminé el diversificado',
        carrera: `¿De qué fue tu carrera de diversificado? ${EJEMPLOS_DIVERSIFICADO}`,
        gusto: '¿Te gustó {carrera}?',
      },
    ].map((g) => ({
      carrera: `¿De qué es tu carrera de diversificado? ${EJEMPLOS_DIVERSIFICADO}`,
      gusto: '¿Te está gustando {carrera}?',
      ...g,
    })),
  },
  {
    label: 'Universidad',
    motivos: MOTIVOS_UNIVERSIDAD,
    grados: [
      {
        label: 'La estoy cursando',
        carrera: '¿Qué carrera estás estudiando?',
        gusto: '¿Te está gustando {carrera}?',
      },
      {
        label: 'Ya la terminé',
        carrera: '¿Qué carrera terminaste?',
        gusto: '¿Te gustó {carrera}?',
      },
      {
        label: 'La abandoné',
        carrera: '¿Qué carrera abandonaste? La voy a descartar de tus resultados.',
        gusto: '¿Te gustó {carrera} mientras la llevaste?',
        descarta: true,
      },
    ],
  },
]

export const nivel = (r) => NIVELES.find((n) => n.label === r.nivel)
export const grado = (r) => nivel(r)?.grados.find((g) => g.label === r.grado)

// 'texto' y 'opciones' pueden ser función de las respuestas dadas hasta ese
// momento; quien las consume las resuelve (ver avanzar() en Chat.jsx).
export const FIJAS = [
  {
    clave: 'nombre',
    tipo: 'texto',
    // Sin "¿cómo te llamas?": preguntado así, el alumno contesta saludando de
    // vuelta ("Hola soy Yesi"). Pedirlo como dato baja esa tentación, y
    // limpiaNombre() se encarga de lo que igual venga con saludo.
    texto: '¡Hola! Soy Orienta, tu guía vocacional. Para empezar, escribe tu nombre.',
    placeholder: 'Escribe tu nombre…',
  },
  {
    clave: 'edad',
    tipo: 'texto',
    texto: 'Mucho gusto, {nombre}. ¿Cuántos años tienes?',
    placeholder: 'Escribe tu edad…',
  },
  {
    clave: 'nivel',
    tipo: 'opcion',
    // Sin 'Otro': de esta respuesta salen las preguntas siguientes (el grado y
    // los motivos), así que un texto libre dejaría al chat sin qué preguntar.
    sinOtro: true,
    texto: '¿En qué nivel vas, o cuál fue el último que cursaste?',
    opciones: NIVELES,
  },
  {
    clave: 'grado',
    tipo: 'opcion',
    sinOtro: true, // de aquí sale cómo se pregunta la carrera y el gusto
    texto: (r) =>
      r.nivel === 'Universidad'
        ? '¿Y cómo vas con esa carrera?'
        : '¿En qué grado vas, o cuál fue el último que cursaste?',
    opciones: (r) => nivel(r)?.grados || [],
  },
  {
    clave: 'carrera_cursada',
    tipo: 'texto',
    si: (r) => !!grado(r)?.carrera, // en básicos no hay carrera que preguntar
    texto: (r) => grado(r)?.carrera || '¿Qué estás estudiando?',
    placeholder: 'Escribe la carrera…',
  },
  {
    clave: 'gusto_grado',
    tipo: 'opcion',
    texto: (r) =>
      (grado(r)?.gusto || '¿Te gustó lo último que estudiaste?')
        .replace('{carrera}', r.carrera_cursada || 'lo que estudias'),
    opciones: [
      { label: 'Sí, mucho' },
      { label: 'Más o menos' },
      { label: 'No mucho' },
      { label: 'No, nada' },
    ],
  },
  {
    // No mueve la recomendación, pero es de las estadísticas que pide quien
    // aplica la evaluación: con qué intención llega cada quien.
    clave: 'motivo',
    tipo: 'opcion',
    texto: '¿Por qué estás haciendo este test?',
    opciones: (r) => nivel(r)?.motivos || MOTIVOS_MEDIO,
  },
  {
    clave: 'impacto',
    tipo: 'opcion',
    multiple: true, // puede elegir varios
    texto: '¿Qué tipo de impacto te gustaría tener en el mundo? (puedes elegir varios)',
    opciones: [
      { label: 'Ayudar, enseñar o dar cuidados a las personas' },
      { label: 'Defender la justicia y resolver conflictos' },
      { label: 'Liderar, organizar negocios o usar tecnología y números' },
      { label: 'Trabajar con la naturaleza, el campo o el ambiente' },
      { label: 'Comunicar, crear, diseñar o hacer investigación' },
      { label: 'Construir, diseñar o hacer que las cosas funcionen' },
    ],
  },
  {
    clave: 'estilo',
    tipo: 'opcion',
    multiple: true, // puede combinar formas de trabajo
    texto: '¿Cómo prefieres trabajar? (puedes elegir varias)',
    opciones: [
      { label: 'Con personas, en trato directo' },
      { label: 'Analizando datos, ideas y lógica' },
      { label: 'De forma práctica, con las manos' },
      { label: 'Al aire libre y en movimiento' },
    ],
  },
  {
    clave: 'entorno',
    tipo: 'opcion',
    multiple: true,
    texto: '¿Dónde te imaginas trabajando? (puedes elegir varios)',
    opciones: [
      { label: 'En una oficina o empresa' },
      { label: 'En un hospital, clínica o consultorio' },
      { label: 'Al aire libre, en el campo o la naturaleza' },
      { label: 'En un laboratorio o taller técnico' },
      { label: 'En un aula o centro educativo' },
      { label: 'En una obra, con máquinas o herramientas' },
      // 'un estudio creativo' se quitó a propósito: 'estudio' es la palabra por
      // la que Radiología, Bio Imágenes y Teología entraban al pre-filtro ("el
      // estudio solicitado", "el estudio y el servicio"). Ver
      // experiments/banco-de-opciones.md.
      { label: 'En medios de comunicación o diseñando' },
      { label: 'Con la comunidad, ayudando a personas' },
    ],
  },
  {
    // Banco de palabras: temas de interés alineados a las áreas del catálogo
    // (sin nombrar carreras). El alumno elige varios y puede agregar el suyo.
    //
    // La lista se revisó tema por tema contra el catálogo el 2026-08-23
    // (backend/cobertura_banco.py agrupa las 147 carreras en 90 temas por
    // `perfil_id` y dice cuáles el alumno no tenía forma de nombrar). Había 18
    // temas sin ninguna palabra que los tocara: enfermería, imágenes médicas,
    // telecomunicaciones, electrónica, idiomas, música, teología, economía,
    // dirección de centros educativos y comercio exterior, entre otros.
    //
    // Criterio al agregarlos: nombran el TEMA, nunca la carrera (regla 2 del
    // CLAUDE.md), y se redactaron para que el alumno se reconozca, no para
    // alimentar al pre-filtro; el A/B midió que el filtro no mueve el resultado
    // final (experiments/filtro-catalogo-ab.md).
    //
    // 'grupo' solo va en el PRIMER chip de cada bloque: Chat.jsx dibuja el
    // título cuando el grupo cambia. Con 25 opciones una lista plana obliga a
    // leerlas todas para no perderse la propia; en 6 grupos se leen 6 títulos y
    // se entra a uno. Los títulos son presentación pura: NO se le mandan al
    // modelo, que solo recibe las etiquetas que el alumno marcó, así que
    // reagruparlos no cambia la señal ni exige volver a medir.
    //
    // Tope de 5: la revisión con la psicóloga (2026-09-03) vio que las
    // evaluaciones con muchos gustos marcados le dejaban al chat una lista tan
    // ancha que no lograba distinguir qué quiere el alumno de verdad, y las
    // preguntas adaptativas salían genéricas. Obligar a elegir YA es parte de
    // la orientación. Sin medir todavía, igual que el banco de 25 chips
    // (experiments/banco-de-opciones.md).
    clave: 'gustos',
    tipo: 'opcion',
    multiple: true,
    max: 5,
    chips: true,
    texto: '¿Qué temas te apasionan? Elige hasta 5 (o agrega el tuyo).',
    opciones: [
      { grupo: 'Salud y cuerpo', label: 'Salud y cuidar pacientes' },
      { label: 'Equipos médicos, laboratorio e imágenes' },
      { label: 'Cuerpo, deporte y rehabilitación' },
      { grupo: 'Ciencia, campo y animales', label: 'Biología y naturaleza' },
      { label: 'Química y laboratorio' },
      { label: 'Animales y su cuidado' },
      { label: 'Ambiente, agricultura y agronegocios' },
      { grupo: 'Tecnología y cómo funcionan las cosas', label: 'Matemáticas y números' },
      { label: 'Tecnología y computación' },
      { label: 'Redes, señal y electrónica' },
      { label: 'Construcción, máquinas y cómo funcionan las cosas' },
      { grupo: 'Personas y sociedad', label: 'Enseñanza y docencia' },
      { label: 'Psicología y conducta' },
      { label: 'Leyes, justicia y debate' },
      { label: 'Historia, sociedad y cultura' },
      { label: 'Fe, religión y espiritualidad' },
      { grupo: 'Crear y comunicar', label: 'Arte, diseño y creatividad' },
      { label: 'Música, danza y artes escénicas' },
      { label: 'Comunicación, escritura y medios' },
      { label: 'Idiomas y otras culturas' },
      { grupo: 'Negocios y el mundo', label: 'Negocios, dinero y emprendimiento' },
      { label: 'Economía, pobreza y desarrollo del país' },
      { label: 'Comercio, política y otros países' },
      { label: 'Organizar y dirigir equipos o instituciones' },
      { label: 'Gastronomía, turismo y hotelería' },
    ],
  },
]

// Para que el historial separe estas de las adaptativas (cuya clave es el texto
// mismo de la pregunta) sin mantener una segunda lista que se desincronice.
export const CLAVES_FIJAS = FIJAS.map((f) => f.clave)

// Las respuestas que describen al alumno y no a sus intereses: es lo que el
// chat ofrece reusar de su última evaluación ("continuar con mi perfil"), para
// que no vuelva a escribir su nombre, su edad y su carrera cada vez. Las de
// intereses (impacto, estilo, entorno, gustos) NO se reusan: son las que se
// están midiendo y pueden haber cambiado.
export const CLAVES_PERFIL = ['nombre', 'edad', 'nivel', 'grado',
  'carrera_cursada', 'gusto_grado', 'motivo']

// El alumno le contesta a Orienta como si fuera una persona, así que al pedirle
// el nombre responde saludando. En la prueba con alumnos reales del 2026-08-24,
// 3 de 18 escribieron "Hola", "Hola soy Yesi" o "me llamo Gabriela", y ese texto
// se usaba tal cual en el chat, el dashboard, el PDF y el prompt: uno leyó
// "Mucho gusto, Hola". Se le quita el saludo de adelante y el "me llamo/soy".
//
// ponytail: lista corta de saludos, no un parser de lenguaje natural. Si
// aparecen formas nuevas en campo, se agregan aquí. Devolver cadena vacía es a
// propósito: quien escribió SOLO "Hola" no dio su nombre, y nombreInvalido() de
// Chat.jsx lo manda a escribirlo otra vez en vez de registrar el saludo.
const SALUDO = /^[\s,.:;!¡¿?]*(hola|holi|buenas|buenos días|buenas tardes|buenas noches|qué tal|que tal|hey)\b[\s,.:;!¡¿?]*/iu
const PRESENTACION = /^[\s,.:;]*(me llamo|mi nombre es|yo soy|soy)\b[\s,.:;]*/iu

export function limpiaNombre(v) {
  return String(v ?? '').replace(SALUDO, '').replace(PRESENTACION, '').trim()
}

// Self-check sin framework: `node src/preguntas-fijas.js` desde frontend/.
if (typeof process !== 'undefined' && process.argv?.[1]?.endsWith('preguntas-fijas.js')) {
  const casos = [
    ['Hola soy Yesi', 'Yesi'],           // los tres casos reales de la prueba
    ['me llamo Gabriela', 'Gabriela'],
    ['Hola', ''],                        // solo saludo: no dio nombre
    ['Ana', 'Ana'],                      // el caso normal no se toca
    ['Holanda', 'Holanda'],              // el \b evita comerse un nombre que empieza igual
    ['Soyla', 'Soyla'],
    ['  José  ', 'José'],
  ]
  for (const [entra, espera] of casos) {
    const sale = limpiaNombre(entra)
    if (sale !== espera) throw new Error(`limpiaNombre("${entra}") dio "${sale}", esperaba "${espera}"`)
  }
  console.log('ok')
}
