import { useNavigate } from 'react-router-dom'
import './App.css'

export default function Inicio() {
  const navigate = useNavigate()
  return (
    <div className="inicio">
      <div className="inicio-card">
        <h1>Orienta</h1>
        <p>
          Un chat que te ayuda a descubrir qué carrera universitaria va más
          contigo. Respondes unas preguntas fáciles y te mostramos las
          carreras que mejor encajan.
        </p>
        <button className="inicio-btn" onClick={() => navigate('/mapa')}>
          Empezar a chatear →
        </button>
      </div>
    </div>
  )
}
