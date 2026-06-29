// Guion del chatbot vocacional.
// Tipos: "text" (abierta), "yesno" (Sí/No), "choice" (opción múltiple).
// `bot` puede ser texto o una función(answers) para personalizar.
// `next` (opcional) ramifica: función(answer, answers) => id de la siguiente, o null para terminar.
// Sin `next`, avanza a la siguiente del array.

export const questions = [
  {
    id: 'nombre',
    type: 'text',
    bot: '¡Hola! 👋 Soy Orienta, tu guía vocacional. Para empezar, ¿cómo te llamas?',
    placeholder: 'Escribe tu nombre...',
  },
  {
    id: 'gustos',
    type: 'text',
    bot: (a) => `¡Mucho gusto, ${a.nombre}! Cuéntame con tus palabras: ¿qué materias o temas te gustan más?`,
    placeholder: 'Ej: matemáticas, comunicación, deportes...',
  },
  {
    id: 'disfruta_resolver',
    type: 'yesno',
    bot: '¿Disfrutas resolviendo problemas o acertijos? 🧩',
    // Ramificación: si dice que sí, profundizamos; si no, saltamos.
    next: (answer) => (answer === 'si' ? 'tipo_problemas' : 'estilo'),
  },
  {
    id: 'tipo_problemas',
    type: 'text',
    bot: '¡Genial! ¿Qué tipo de problemas te gusta resolver?',
    placeholder: 'Ej: cálculos, conflictos entre personas, armar cosas...',
    next: () => 'estilo',
  },
  {
    id: 'estilo',
    type: 'choice',
    bot: 'Cuando trabajas en algo, ¿cómo prefieres hacerlo?',
    options: [
      { value: 'investigacion', label: '🔬 Investigando a fondo' },
      { value: 'practica', label: '🛠️ De forma práctica, con las manos' },
      { value: 'fisica', label: '🏃 Activo/a y en movimiento' },
      { value: 'analitica', label: '📊 Analizando datos y lógica' },
    ],
  },
  {
    id: 'trabajo_equipo',
    type: 'yesno',
    bot: '¿Te gusta trabajar en equipo? 🤝',
  },
  {
    id: 'meta',
    type: 'text',
    bot: 'Última pregunta: ¿qué te gustaría lograr o resolver en el mundo?',
    placeholder: 'Escribe libremente...',
  },
]

export const firstId = questions[0].id
