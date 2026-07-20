import { useNavigate } from 'react-router-dom'
import Nav from './Nav'
import './App.css'

export default function Acerca() {
  const navigate = useNavigate()
  return (
    <div className="pagina">
      <Nav />
      <main className="contenido">
        <span className="pasos-kicker">Acerca de</span>
        <h1>¿Qué es Orienta?</h1>
        <p className="intro">
          Orienta es un asistente vocacional con inteligencia artificial, creado
          como proyecto de graduación, para estudiantes de Guatemala que están por
          elegir qué carrera universitaria estudiar.
        </p>
        <div className="acerca-bloques">
          <article>
            <svg viewBox="0 0 48 48" width="40" height="40" aria-hidden="true">
              <circle cx="24" cy="24" r="16" fill="none" stroke="var(--accent)" strokeWidth="5" />
              <line x1="24" y1="16" x2="24" y2="26" stroke="var(--accent)" strokeWidth="5" strokeLinecap="round" />
              <circle cx="24" cy="33" r="3" fill="var(--accent)" />
            </svg>
            <h3>El problema</h3>
            <p>
              Elegir carrera es una de las decisiones más importantes de la vida, y
              muchos estudiantes la toman sin orientación: por moda, por presión o
              sin conocer las opciones reales que existen en su propio departamento.
            </p>
          </article>
          <article>
            <svg viewBox="0 0 48 48" width="40" height="40" aria-hidden="true">
              <path d="M24 6 a13 13 0 0 1 7 24 l0 5 h-14 l0 -5 a13 13 0 0 1 7 -24 Z" fill="var(--accent-2)" />
              <rect x="19" y="37" width="10" height="4" rx="2" fill="var(--accent)" />
            </svg>
            <h3>La solución</h3>
            <p>
              Un chat gratuito que conversa contigo como un orientador humano. La IA
              analiza lo que te gusta, cómo piensas y dónde te imaginas trabajando, y
              lo compara con un catálogo real de carreras de universidades de
              Quetzaltenango y Totonicapán — con planes de crecer a más departamentos.
            </p>
          </article>
          <article>
            <svg viewBox="0 0 48 48" width="40" height="40" aria-hidden="true">
              <rect x="8" y="26" width="8" height="14" rx="2" fill="#60a5fa" />
              <rect x="20" y="16" width="8" height="24" rx="2" fill="var(--accent)" />
              <rect x="32" y="8" width="8" height="32" rx="2" fill="var(--accent-2)" />
            </svg>
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
