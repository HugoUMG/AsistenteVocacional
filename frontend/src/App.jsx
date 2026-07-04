import { useEffect, useRef, useState } from 'react'
import Dashboard from './Dashboard'
import './App.css'

const API = 'http://localhost:8000'
const MAX_PREGUNTAS = 10 // tope de seguridad

const post = (ruta, body) =>
  fetch(`${API}${ruta}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

// Primera pregunta fija (el nombre, para saludar). Lo vocacional lo decide la IA.
const SALUDO = {
  texto: '¡Hola! 👋 Soy Orienta, tu guía vocacional. Para empezar, ¿cómo te llamas?',
  tipo: 'texto',
  esNombre: true,
}

// Guarda el perfil y pide el análisis de afinidad. Lanza error si falla.
async function obtenerCarreras(respuestas) {
  let estudiante_id = 0
  try {
    const reg = await post('/api/register', { nombre: respuestas.nombre || 'Anónimo' })
    if (reg.ok) {
      estudiante_id = (await reg.json()).id
      await post('/api/submit-survey', { estudiante_id, respuestas })
    }
  } catch {
    /* backend caído para guardar: seguimos al análisis igual */
  }

  const r = await post('/api/recommend', { estudiante_id, respuestas })
  if (r.status === 503) throw new Error('El motor de IA aún no está configurado en el servidor.')
  if (!r.ok) throw new Error('No pude generar las recomendaciones. Inténtalo de nuevo.')
  return (await r.json()).carreras
}

function Robot({ thinking }) {
  return (
    <div className={`robot ${thinking ? 'thinking' : ''}`}>
      <svg viewBox="0 0 100 100" width="96" height="96" aria-hidden="true">
        <line x1="50" y1="14" x2="50" y2="26" stroke="currentColor" strokeWidth="3" />
        <circle cx="50" cy="11" r="5" fill="currentColor" />
        <rect x="22" y="26" width="56" height="48" rx="14" fill="currentColor" />
        <circle className="eye" cx="38" cy="48" r="6" fill="#fff" />
        <circle className="eye" cx="62" cy="48" r="6" fill="#fff" />
        <rect x="40" y="62" width="20" height="4" rx="2" fill="#fff" opacity="0.8" />
      </svg>
    </div>
  )
}

function App() {
  const [respuestas, setRespuestas] = useState({})
  const [history, setHistory] = useState([{ role: 'bot', text: SALUDO.texto }])
  const [current, setCurrent] = useState(SALUDO)
  const [text, setText] = useState('')
  const [phase, setPhase] = useState('chat') // chat | loading | dashboard
  const [carreras, setCarreras] = useState([])
  const [error, setError] = useState(null)
  const [cargando, setCargando] = useState(false) // pidiendo la siguiente pregunta
  const logRef = useRef(null)

  useEffect(() => {
    logRef.current?.scrollTo(0, logRef.current.scrollHeight)
  }, [history, cargando])

  const numVocacionales = Object.keys(respuestas).filter((k) => k !== 'nombre').length

  async function analizar(resp) {
    setPhase('loading')
    setError(null)
    try {
      setCarreras(await obtenerCarreras(resp))
      setPhase('dashboard')
    } catch (e) {
      setError(e.message)
    }
  }

  async function pedirSiguiente(resp) {
    setError(null)
    setCargando(true)
    try {
      const r = await post('/api/next-question', { respuestas: resp })
      if (r.status === 503) throw new Error('El motor de IA aún no está configurado en el servidor.')
      if (!r.ok) throw new Error('No pude cargar la siguiente pregunta. Inténtalo de nuevo.')
      const paso = await r.json()
      const tope = Object.keys(resp).filter((k) => k !== 'nombre').length >= MAX_PREGUNTAS
      if (paso.terminado || tope) {
        setCargando(false)
        await analizar(resp)
      } else {
        const q = { texto: paso.pregunta_texto, tipo: paso.pregunta_tipo, opciones: paso.opciones || [] }
        setCurrent(q)
        setHistory((h) => [...h, { role: 'bot', text: q.texto }])
        setCargando(false)
      }
    } catch (e) {
      setError(e.message)
      setCargando(false)
    }
  }

  function answer(value, label) {
    const next = current.esNombre
      ? { ...respuestas, nombre: value }
      : { ...respuestas, [current.texto]: value }
    setRespuestas(next)
    setHistory((h) => [...h, { role: 'user', text: label ?? value }])
    setText('')
    setCurrent(null)
    pedirSiguiente(next)
  }

  function submitText(e) {
    e.preventDefault()
    if (text.trim()) answer(text.trim())
  }

  if (phase === 'dashboard') {
    return (
      <Dashboard
        nombre={respuestas.nombre}
        carreras={carreras}
        onReiniciar={() => window.location.reload()}
      />
    )
  }

  if (phase === 'loading') {
    return (
      <div className="chat loading-screen">
        <div className={`spinner-ring ${error ? 'err' : ''}`}>
          <Robot thinking={!error} />
        </div>
        {error ? (
          <>
            <p className="loading-text">{error}</p>
            <button className="opt" onClick={() => analizar(respuestas)}>Reintentar</button>
          </>
        ) : (
          <p className="loading-text">Analizando tus respuestas…</p>
        )}
      </div>
    )
  }

  return (
    <div className="chat">
      <Robot thinking={cargando} />

      <div className="log" ref={logRef}>
        {history.map((m, i) => (
          <div key={i} className={`bubble ${m.role}`}>
            {m.text}
          </div>
        ))}
        {cargando && (
          <div className="bubble bot escribiendo">
            <span></span><span></span><span></span>
          </div>
        )}
      </div>

      {!cargando && error && (
        <div className="options" style={{ flexDirection: 'column', alignItems: 'center' }}>
          <p className="loading-text">{error}</p>
          <button className="opt" onClick={() => pedirSiguiente(respuestas)}>Reintentar</button>
        </div>
      )}

      {!cargando && current?.tipo === 'texto' && (
        <form className="input-row" onSubmit={submitText}>
          <input
            autoFocus
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Escribe tu respuesta…"
          />
          <button type="submit" disabled={!text.trim()}>➤</button>
        </form>
      )}

      {!cargando && current?.tipo === 'sino' && (
        <div className="options">
          <button className="opt si" onClick={() => answer('si', 'Sí')}>Sí</button>
          <button className="opt no" onClick={() => answer('no', 'No')}>No</button>
        </div>
      )}

      {!cargando && current?.tipo === 'opcion' && (
        <div className="options choices">
          {current.opciones.map((o) => (
            <button key={o.value} className="opt" onClick={() => answer(o.value, o.label)}>
              {o.label}
            </button>
          ))}
        </div>
      )}

      {!cargando && current && !current.esNombre && numVocacionales >= 3 && (
        <button className="terminar-btn" onClick={() => analizar(respuestas)}>
          Ya, muéstrame mis resultados →
        </button>
      )}
    </div>
  )
}

export default App
