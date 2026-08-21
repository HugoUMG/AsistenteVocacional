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
    texto: '¡Hola! Soy Orienta, tu guía vocacional. Para empezar, ¿cómo te llamas?',
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
      { label: 'Ayudar, enseñar o cuidar a las personas' },
      { label: 'Defender la justicia y resolver conflictos' },
      { label: 'Liderar, organizar negocios o usar tecnología y números' },
      { label: 'Trabajar con la naturaleza, el campo o el ambiente' },
      { label: 'Comunicar, crear, diseñar o investigar la realidad' },
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
      { label: 'En medios, un estudio creativo o diseñando' },
      { label: 'Con la comunidad, ayudando a personas' },
    ],
  },
  {
    // Banco de palabras: temas de interés alineados a las áreas del catálogo
    // (sin nombrar carreras). El alumno elige varios y puede agregar el suyo.
    clave: 'gustos',
    tipo: 'opcion',
    multiple: true,
    chips: true,
    texto: '¿Qué temas te apasionan? Elige los que quieras (o agrega el tuyo).',
    opciones: [
      { label: 'Matemáticas y números' },
      { label: 'Tecnología y computación' },
      { label: 'Salud y cuidar personas' },
      { label: 'Biología y naturaleza' },
      { label: 'Química y laboratorio' },
      { label: 'Leyes, justicia y debate' },
      { label: 'Negocios, dinero y emprender' },
      { label: 'Arte, diseño y creatividad' },
      { label: 'Comunicación, escritura y medios' },
      { label: 'Enseñar y educar' },
      { label: 'Psicología y comportamiento' },
      { label: 'Medio ambiente y agricultura' },
      { label: 'Construcción, máquinas y cómo funcionan las cosas' },
      { label: 'Gastronomía, turismo y hotelería' },
      { label: 'Historia, sociedad y cultura' },
    ],
  },
]

// Para que el historial separe estas de las adaptativas (cuya clave es el texto
// mismo de la pregunta) sin mantener una segunda lista que se desincronice.
export const CLAVES_FIJAS = FIJAS.map((f) => f.clave)
