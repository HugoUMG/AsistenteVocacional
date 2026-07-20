import { useNavigate } from 'react-router-dom'
import Nav from './Nav'
import './App.css'

// Las 6 dimensiones del "banco de palabras" con las que la IA compara al
// estudiante contra cada carrera (mismas secciones que en la BD de carreras).
const DIMENSIONES = [
  {
    nombre: 'Arquetipo',
    corto: 'Quién llegarías a ser',
    texto:
      'Cada carrera tiene un "personaje" que la resume: el jurista que defiende el orden, el sanador científico, el constructor de infraestructura. Es la foto rápida de en quién te convierte esa profesión.',
  },
  {
    nombre: 'Afinidad (ser)',
    corto: 'Cómo eres tú',
    texto:
      'Tu forma de ser: qué te mueve, qué te indigna, qué disfrutas. La IA busca carreras cuya vocación coincida con tu personalidad, no solo con tus notas.',
  },
  {
    nombre: 'Habilidades (saber hacer)',
    corto: 'Lo que aprenderías a hacer',
    texto:
      'Las destrezas concretas que esa carrera te enseña y exige: argumentar, calcular, programar, cuidar, diseñar. Se comparan con lo que dices que te sale bien o te gustaría dominar.',
  },
  {
    nombre: 'Entorno',
    corto: 'Dónde trabajarías',
    texto:
      'El escenario real del día a día: oficina, hospital, campo, laboratorio, tribunal o aula. Si te imaginas al aire libre, una carrera de escritorio pierde puntos contigo.',
  },
  {
    nombre: 'Gustos temáticos',
    corto: 'Los temas que te apasionan',
    texto:
      'Los temas de los que no te aburres: números, leyes, naturaleza, arte, tecnología. La IA cruza tus intereses con los temas centrales de cada carrera.',
  },
  {
    nombre: 'Estilo cognitivo',
    corto: 'Cómo piensas',
    texto:
      'Tu manera de razonar: lógico y estructurado, creativo e intuitivo, práctico y manual, o analítico y crítico. Cada carrera favorece ciertos estilos de pensamiento.',
  },
]

export default function Parametros() {
  const navigate = useNavigate()
  return (
    <div className="pagina">
      <Nav />
      <main className="contenido">
        <span className="pasos-kicker">Parámetros de evaluación</span>
        <h1>¿Cómo te evalúa la inteligencia artificial?</h1>
        <p className="intro">
          Cada carrera del catálogo tiene un <strong>perfil vocacional</strong> dividido
          en seis dimensiones. Mientras chateas, la IA compara tus respuestas contra
          esas seis dimensiones de <em>todas</em> las carreras de tu departamento, y al
          final asigna un porcentaje de afinidad a cada una. No hay respuestas buenas
          ni malas: solo qué tanto se parece cada carrera a ti.
        </p>
        <div className="dim-grid">
          {DIMENSIONES.map((d, i) => (
            <article key={d.nombre} className="dim-card">
              <span className="dim-num">{String(i + 1).padStart(2, '0')}</span>
              <h3>{d.nombre}</h3>
              <span className="dim-corto">{d.corto}</span>
              <p>{d.texto}</p>
            </article>
          ))}
        </div>
        <div className="cierre">
          <p>¿Listo para ver qué carreras se parecen a ti?</p>
          <button className="hero-btn" onClick={() => navigate('/mapa')}>Empezar el chat →</button>
        </div>
      </main>
    </div>
  )
}
