import { useNavigate } from 'react-router-dom'
import Nav from './Nav'
import './App.css'

// Ondas decorativas del hero (azules sobre azul marino), inspiradas en el
// diseño de referencia. Puramente decorativas: aria-hidden.
function Ondas() {
  return (
    <svg className="hero-ondas" viewBox="0 0 900 340" preserveAspectRatio="none" aria-hidden="true">
      <path
        d="M0,290 C150,240 260,320 420,270 C580,220 640,120 760,140 C830,152 880,200 900,230 L900,340 L0,340 Z"
        fill="#1d4ed8" opacity="0.55"
      />
      <path
        d="M0,320 C180,280 320,340 480,300 C640,260 720,170 900,210 L900,340 L0,340 Z"
        fill="#0ea5e9" opacity="0.45"
      />
      <path
        d="M120,340 C240,230 330,190 430,220 C530,250 560,320 640,340 Z"
        fill="#3b82f6" opacity="0.5"
      />
      <circle cx="750" cy="90" r="34" fill="#0ea5e9" opacity="0.35" />
      <circle cx="640" cy="60" r="12" fill="#60a5fa" opacity="0.5" />
    </svg>
  )
}

const PASOS = [
  {
    titulo: 'Conversa con Orienta',
    texto: 'Respondes preguntas sencillas en un chat: qué te gusta, cómo prefieres trabajar y dónde te imaginas.',
    icono: (
      <svg viewBox="0 0 48 48" width="40" height="40" aria-hidden="true">
        <rect x="6" y="8" width="36" height="26" rx="8" fill="var(--accent)" />
        <path d="M16 34 L16 42 L26 34 Z" fill="var(--accent)" />
        <circle cx="18" cy="21" r="3" fill="#fff" />
        <circle cx="30" cy="21" r="3" fill="#fff" />
      </svg>
    ),
  },
  {
    titulo: 'La IA analiza tu perfil',
    texto: 'Compara tus respuestas con un catálogo real de carreras de universidades de tu departamento.',
    icono: (
      <svg viewBox="0 0 48 48" width="40" height="40" aria-hidden="true">
        <circle cx="21" cy="21" r="12" fill="none" stroke="var(--accent-2)" strokeWidth="5" />
        <line x1="30" y1="30" x2="41" y2="41" stroke="var(--accent-2)" strokeWidth="6" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    titulo: 'Recibe tu recomendación',
    texto: 'Ves las carreras más afines a ti con porcentajes, razones y las universidades donde estudiarlas.',
    icono: (
      <svg viewBox="0 0 48 48" width="40" height="40" aria-hidden="true">
        <rect x="8" y="26" width="8" height="14" rx="2" fill="#60a5fa" />
        <rect x="20" y="16" width="8" height="24" rx="2" fill="var(--accent)" />
        <rect x="32" y="8" width="8" height="32" rx="2" fill="var(--accent-2)" />
      </svg>
    ),
  },
]

export default function Inicio() {
  const navigate = useNavigate()
  return (
    <div className="pagina">
      <Nav />

      <section className="hero">
        <div className="hero-texto">
          <h1>Descubre la carrera que va contigo</h1>
          <p>
            Orienta es un chat con inteligencia artificial que te ayuda a elegir
            qué estudiar. Respondes unas preguntas fáciles y te muestra las
            carreras que mejor encajan contigo, con universidades reales de
            Guatemala.
          </p>
          <button className="hero-btn" onClick={() => navigate('/mapa')}>
            Empezar el chat →
          </button>
        </div>
        <Ondas />
      </section>

      <section className="pasos">
        <span className="pasos-kicker">¿Cómo funciona?</span>
        <h2>Tu orientación vocacional, paso a paso</h2>
        <div className="pasos-grid">
          {PASOS.map((p, i) => (
            <article key={p.titulo} className="paso-card">
              <span className="card-icono">{p.icono}</span>
              <span className="card-paso-num">Paso {i + 1}</span>
              <h3>{p.titulo}</h3>
              <p>{p.texto}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="cierre">
        <p>
          Este proyecto nació para apoyar a estudiantes de Quetzaltenango y
          Totonicapán que están por decidir su futuro. No necesitas registrarte
          ni pagar nada: solo unos minutos y ganas de conocerte mejor.
        </p>
        <button className="hero-btn" onClick={() => navigate('/mapa')}>
          Hacer mi test vocacional →
        </button>
      </section>
    </div>
  )
}
