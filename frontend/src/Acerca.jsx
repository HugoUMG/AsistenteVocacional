import { useNavigate } from 'react-router-dom'
import Nav from './Nav'
import './App.css'

export default function Acerca() {
  const navigate = useNavigate()
  return (
    <div className="pagina">
      <Nav />
      <main className="contenido contenido-angosto">
        <span className="pasos-kicker">Acerca de</span>
        <h1>¿Qué es Orienta?</h1>
        <p className="intro">
          Orienta es un asistente vocacional con inteligencia artificial, creado
          como proyecto de graduación, para estudiantes de Guatemala que están por
          elegir qué carrera universitaria estudiar.
        </p>
        <div className="acerca-bloques">
          <article>
            <h3>El problema</h3>
            <p>
              Elegir carrera es una de las decisiones más importantes de la vida, y
              muchos estudiantes la toman sin orientación: por moda, por presión o
              sin conocer las opciones reales que existen en su propio departamento.
            </p>
          </article>
          <article>
            <h3>La solución</h3>
            <p>
              Un chat gratuito que conversa contigo como un orientador humano. La IA
              analiza lo que te gusta, cómo piensas y dónde te imaginas trabajando, y
              lo compara con un catálogo real de carreras de universidades de
              Quetzaltenango y Totonicapán — con planes de crecer a más departamentos.
            </p>
          </article>
          <article>
            <h3>El resultado</h3>
            <p>
              Un tablero con tus carreras más afines, el porcentaje de afinidad de
              cada una, las razones de la recomendación y las universidades exactas
              donde puedes estudiarlas, cada una con su sello particular.
            </p>
          </article>
        </div>
        <div className="cierre">
          <button className="hero-btn" onClick={() => navigate('/mapa')}>Probar Orienta →</button>
        </div>
      </main>
    </div>
  )
}
