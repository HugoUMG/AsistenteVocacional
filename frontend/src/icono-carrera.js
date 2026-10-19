// Qué icono lleva cada carrera en el catálogo, deducido de su nombre. El
// catálogo no trae un área por carrera y no hace falta agregarla solo para esto:
// una carrera nueva que no encaje en ninguna regla sale con el birrete, así que
// sumar carreras no exige tocar este archivo: el catálogo sigue mandando.
//
// ponytail: reglas por palabras del nombre, en orden; gana la primera que
// coincide. El orden importa: "Telecomunicaciones" contiene "comunicacion",
// "Enfermería Veterinaria" contiene "enfermer" y "Chef Profesional e
// Internacional" contiene "internacional". Si un día el catálogo trae el área
// de cada carrera, esto se cambia por esa columna.

const REGLAS = [
  [/dent|odontolog/, 'diente'],
  [/optometr/, 'ojo'],
  [/radiolog|imagenes/, 'monitor'],
  [/laboratorio|quimica/, 'matraz'],
  [/fisioterapia|terapia fisica/, 'pesa'],
  [/nutricion/, 'manzana'],
  [/veterinari/, 'huella'],
  [/enfermer|medic|cirujano|cirugia|hemodialisis|salud/, 'estetoscopio'],
  [/psicolog|psicopedagog/, 'conversacion'],
  [/criminal|forense/, 'lupa'],
  [/juridic|abogad|notari/, 'mazo'],
  [/chef|culinari|gastronom|hotel|turis|restaurant/, 'cubiertos'],
  [/internacional/, 'mundo'],
  [/teologia/, 'vela'],
  [/pedagog|profesorado|pem |educacion|educativ|ensenanza/, 'pizarra'],
  [/musica/, 'musica'],
  [/audiovisual|cinematograf/, 'camara'],
  [/diseno|publicidad/, 'paleta'],
  [/telecomunicaciones|electronica/, 'senal'],
  [/comunicacion|periodismo/, 'megafono'],
  [/sistemas|informatic|software|computacion/, 'laptop'],
  [/civil/, 'casco'],
  [/arquitectura/, 'edificio'],
  [/forestal/, 'arboles'],
  [/agro|agricol|tierras/, 'brote'],
  [/mecanica|industrial/, 'llave'],
  [/ambiental/, 'hoja'],
  [/contadur|auditor/, 'calculadora'],
  [/economia/, 'tendencia'],
  [/marketing|mercadotecnia|mercadeo|ventas/, 'megafono'],
  [/recursos humanos|trabajo social/, 'personas'],
  [/administracion|empresa|negocios|gerencia|emprendimiento/, 'maletin'],
]

const plano = (s) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()

export function iconoCarrera(nombre) {
  const n = plano(nombre || '')
  return REGLAS.find(([re]) => re.test(n))?.[1] || 'birrete'
}

// Self-check sin framework: `node src/icono-carrera.js` desde frontend/.
if (typeof process !== 'undefined' && process.argv?.[1]?.endsWith('icono-carrera.js')) {
  const casos = [
    ['Ingeniería en Telecomunicaciones', 'senal'], // no 'comunicacion'
    ['Técnico Universitario en Enfermería Veterinaria', 'huella'], // no 'enfermer'
    ['Chef Profesional e Internacional (Técnico Universitario)', 'cubiertos'], // no 'internacional'
    ['Ingeniería Agroindustrial', 'brote'], // no 'industrial'
    ['Licenciatura en Psicología Industrial', 'conversacion'],
    ['Técnico en Laboratorio Dental', 'diente'],
    ['Teología Sistemática', 'vela'], // no 'sistemas'
    ['Economía Empresarial', 'tendencia'], // no 'empresa'
    ['Licenciatura en Administración Educativa', 'pizarra'], // no 'administracion'
    ['Una carrera que todavía no existe', 'birrete'],
  ]
  for (const [nombre, espera] of casos) {
    const sale = iconoCarrera(nombre)
    if (sale !== espera) throw new Error(`iconoCarrera("${nombre}") dio "${sale}", esperaba "${espera}"`)
  }
  console.log('ok')
}
