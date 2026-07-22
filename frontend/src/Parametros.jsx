import { useNavigate } from 'react-router-dom'
import Nav from './Nav'
import './App.css'

// Las 7 dimensiones vocacionales que la IA explora del estudiante y cruza
// contra el perfil de cada carrera. El test adaptativo garantiza cubrirlas
// todas (ver backend/app/preguntas.py, vector de cobertura).
const DIMENSIONES = [
  {
    nombre: 'Personalidad',
    corto: 'Cómo eres tú',
    texto:
      'Tu forma de ser: qué te mueve, qué te indigna, qué disfrutas. La IA busca carreras cuya vocación coincida con tu personalidad, no solo con tus notas.',
  },
  {
    nombre: 'Intereses',
    corto: 'Los temas que te apasionan',
    texto:
      'Los temas de los que no te aburres: números, leyes, naturaleza, arte, tecnología. La IA cruza tus intereses con los temas centrales de cada carrera.',
  },
  {
    nombre: 'Habilidades',
    corto: 'Lo que sabes y aprenderías a hacer',
    texto:
      'Las destrezas concretas que esa carrera te enseña y exige: argumentar, calcular, programar, cuidar, diseñar. Se comparan con lo que dices que te sale bien o te gustaría dominar.',
  },
  {
    nombre: 'Estilo cognitivo',
    corto: 'Cómo piensas',
    texto:
      'Tu manera de razonar: lógico y estructurado, creativo e intuitivo, práctico y manual, o analítico y crítico. Cada carrera favorece ciertos estilos de pensamiento.',
  },
  {
    nombre: 'Valores',
    corto: 'Qué te importa en una profesión',
    texto:
      'Lo que para ti hace que un trabajo valga la pena: ayudar a otros, la justicia, la estabilidad, la libertad para crear. Cada carrera responde a valores distintos, y la IA busca los que coinciden con los tuyos.',
  },
  {
    nombre: 'Entorno',
    corto: 'Dónde trabajarías',
    texto:
      'El escenario real del día a día: oficina, hospital, campo, laboratorio, tribunal o aula. Si te imaginas al aire libre, una carrera de escritorio pierde puntos contigo.',
  },
  {
    nombre: 'Motivaciones',
    corto: 'Qué te impulsa',
    texto:
      'El motor detrás de tus decisiones: el impacto que quieres dejar en el mundo, ya sea cuidar personas, construir cosas, defender causas o crear e innovar. La IA parte de ahí para entender hacia dónde apuntas.',
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
          Para recomendarte bien, la IA construye tu <strong>perfil vocacional</strong> a
          partir de siete dimensiones. Mientras chateas, cruza lo que descubre de ti con el
          perfil de <em>todas</em> las carreras de tu departamento —cada una resumida por un
          "arquetipo" o personaje (el jurista que defiende el orden, el sanador científico, el
          constructor de infraestructura)— y al final asigna un porcentaje de afinidad a cada
          una. No hay respuestas buenas ni malas: solo qué tanto se parece cada carrera a ti.
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
