import { useEffect, useRef, useState } from 'react'
import Dashboard from './Dashboard'
import './App.css'

const API = 'http://localhost:8000'
const MAX_ADAPTATIVAS = 3 // preguntas que genera la IA (cada una = 1 llamada)

// Preguntas FIJAS (sin llamar a la IA): nombre + 3 vocacionales genéricas.
// Son catálogo-agnósticas (no mencionan carreras).
const FIJAS = [
  {
    clave: 'nombre',
    tipo: 'texto',
    texto: '¡Hola! 👋 Soy Orienta, tu guía vocacional. Para empezar, ¿cómo te llamas?',
    placeholder: 'Escribe tu nombre…',
  },
  {
    clave: 'departamento',
    tipo: 'opcion',
    texto: '{nombre}, ¿en qué departamento quieres estudiar?',
    opciones: [], // se llenan dinámicamente desde el backend
  },
  {
    clave: 'impacto',
    tipo: 'opcion',
    texto: '¿Qué tipo de impacto te gustaría tener en el mundo?',
    opciones: [
      { label: '🤝 Ayudar, enseñar o cuidar a las personas' },
      { label: '⚖️ Defender la justicia y resolver conflictos' },
      { label: '💼 Liderar, organizar negocios o usar tecnología y números' },
      { label: '🌳 Trabajar con la naturaleza, el campo o el ambiente' },
      { label: '🎨 Comunicar, crear, diseñar o investigar la realidad' },
    ],
  },
  {
    clave: 'estilo',
    tipo: 'opcion',
    texto: '¿Cómo prefieres trabajar?',
    opciones: [
      { label: '👥 Con personas, en trato directo' },
      { label: '📊 Analizando datos, ideas y lógica' },
      { label: '🛠️ De forma práctica, con las manos' },
      { label: '🏃 Al aire libre y en movimiento' },
    ],
  },
  {
    clave: 'gustos',
    tipo: 'texto',
    texto: 'Cuéntame en tus palabras: ¿qué materias o temas te apasionan?',
    placeholder: 'Ej: matemáticas, biología, historia, arte…',
  },
]

const post = (ruta, body) =>
  fetch(`${API}${ruta}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

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
  const [history, setHistory] = useState([{ role: 'bot', text: FIJAS[0].texto }])
  const [paso, setPaso] = useState(FIJAS[0]) // pregunta actual (fija tiene .clave; adaptativa no)
  const [text, setText] = useState('')
  const [phase, setPhase] = useState('chat') // chat | loading | dashboard
  const [carreras, setCarreras] = useState([])
  const [error, setError] = useState(null)
  const [cargando, setCargando] = useState(false)
  const [departamentos, setDepartamentos] = useState([])
  const logRef = useRef(null)

  useEffect(() => {
    logRef.current?.scrollTo(0, logRef.current.scrollHeight)
  }, [history, cargando])

  // Trae los departamentos disponibles para la pregunta de filtro.
  useEffect(() => {
    fetch(`${API}/api/departamentos`)
      .then((r) => r.json())
      .then((d) => setDepartamentos(d.departamentos || []))
      .catch(() => {})
  }, [])

  async function analizar(resp) {
    setPaso(null)
    setPhase('loading')
    setError(null)
    try {
      setCarreras(await obtenerCarreras(resp))
      setPhase('dashboard')
    } catch (e) {
      setError(e.message)
    }
  }

  // Pide a la IA la siguiente pregunta adaptativa (1 llamada).
  async function pedirAdaptativa(resp) {
    setError(null)
    setCargando(true)
    try {
      const r = await post('/api/next-question', { respuestas: resp })
      if (r.status === 503) throw new Error('El motor de IA aún no está configurado en el servidor.')
      if (!r.ok) throw new Error('No pude cargar la siguiente pregunta. Inténtalo de nuevo.')
      const q = await r.json()
      if (q.terminado) {
        await analizar(resp)
      } else {
        setPaso({ texto: q.pregunta_texto, tipo: q.pregunta_tipo, opciones: q.opciones || [] })
        setHistory((h) => [...h, { role: 'bot', text: q.pregunta_texto }])
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setCargando(false)
    }
  }

  // Decide qué sigue: fija (sin IA), adaptativa (IA), o análisis final.
  function avanzar(resp) {
    const fijasAns = FIJAS.filter((f) => resp[f.clave] !== undefined).length
    if (fijasAns < FIJAS.length) {
      const q = { ...FIJAS[fijasAns] }
      q.texto = q.texto.replace('{nombre}', resp.nombre || '')
      if (q.clave === 'departamento') {
        q.opciones = departamentos.map((d) => ({ label: d }))
      }
      setPaso(q)
      setHistory((h) => [...h, { role: 'bot', text: q.texto }])
      return
    }
    const nAdapt = Object.keys(resp).length - FIJAS.length
    if (nAdapt >= MAX_ADAPTATIVAS) {
      analizar(resp)
    } else {
      pedirAdaptativa(resp)
    }
  }

  function answer(respuesta) {
    const clave = paso.clave ?? paso.texto
    const next = { ...respuestas, [clave]: respuesta }
    setRespuestas(next)
    setHistory((h) => [...h, { role: 'user', text: respuesta }])
    setText('')
    setPaso(null)
    avanzar(next)
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

  const esAdaptativa = paso && !paso.clave

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
          <button className="opt" onClick={() => pedirAdaptativa(respuestas)}>Reintentar</button>
        </div>
      )}

      {!cargando && paso?.tipo === 'texto' && (
        <form className="input-row" onSubmit={submitText}>
          <input
            autoFocus
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={paso.placeholder || 'Escribe tu respuesta…'}
          />
          <button type="submit" disabled={!text.trim()}>➤</button>
        </form>
      )}

      {!cargando && paso?.tipo === 'sino' && (
        <div className="options">
          <button className="opt si" onClick={() => answer('Sí')}>Sí</button>
          <button className="opt no" onClick={() => answer('No')}>No</button>
        </div>
      )}

      {!cargando && paso?.tipo === 'opcion' && (
        <div className="options choices">
          {paso.opciones.map((o, j) => (
            <button key={j} className="opt" onClick={() => answer(o.label)}>
              {o.label}
            </button>
          ))}
        </div>
      )}

      {!cargando && esAdaptativa && (
        <button className="terminar-btn" onClick={() => analizar(respuestas)}>
          Ya, muéstrame mis resultados →
        </button>
      )}
    </div>
  )
}

export default App
