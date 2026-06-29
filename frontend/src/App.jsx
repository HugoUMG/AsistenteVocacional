import { useEffect, useRef, useState } from 'react'
import { questions, firstId } from './questions'
import Dashboard from './Dashboard'
import './App.css'

const API = 'http://localhost:8000'

const byId = (id) => questions.find((q) => q.id === id)

function resolveNext(q, answer, answers) {
  if (typeof q.next === 'function') return q.next(answer, answers)
  const idx = questions.findIndex((x) => x.id === q.id)
  return questions[idx + 1]?.id ?? null
}

const botText = (q, answers) => (typeof q.bot === 'function' ? q.bot(answers) : q.bot)

const post = (ruta, body) =>
  fetch(`${API}${ruta}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

// Guarda el perfil y pide el análisis de afinidad. Lanza error si falla.
async function obtenerCarreras(answers) {
  let estudiante_id = 0
  try {
    const reg = await post('/api/register', { nombre: answers.nombre || 'Anónimo' })
    if (reg.ok) {
      estudiante_id = (await reg.json()).id
      await post('/api/submit-survey', { estudiante_id, respuestas: answers })
    }
  } catch {
    /* backend caído para guardar: seguimos al análisis igual */
  }

  const r = await post('/api/recommend', { estudiante_id, respuestas: answers })
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
  const [answers, setAnswers] = useState({})
  const [currentId, setCurrentId] = useState(firstId)
  const [history, setHistory] = useState([])
  const [text, setText] = useState('')
  const [phase, setPhase] = useState('chat') // chat | loading | dashboard
  const [carreras, setCarreras] = useState([])
  const [error, setError] = useState(null)
  const logRef = useRef(null)
  const announced = useRef(new Set())

  const current = currentId ? byId(currentId) : null

  useEffect(() => {
    if (current && !announced.current.has(current.id)) {
      announced.current.add(current.id)
      setHistory((h) => [...h, { role: 'bot', text: botText(current, answers) }])
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentId])

  useEffect(() => {
    logRef.current?.scrollTo(0, logRef.current.scrollHeight)
  }, [history])

  async function analizar(ans) {
    setError(null)
    setPhase('loading')
    try {
      setCarreras(await obtenerCarreras(ans))
      setPhase('dashboard')
    } catch (e) {
      setError(e.message)
    }
  }

  function answer(value, label) {
    const next = { ...answers, [current.id]: value }
    setAnswers(next)
    setHistory((h) => [...h, { role: 'user', text: label ?? value }])
    setText('')

    const nextId = resolveNext(current, value, next)
    if (nextId) {
      setCurrentId(nextId)
    } else {
      setCurrentId(null)
      analizar(next)
    }
  }

  function submitText(e) {
    e.preventDefault()
    if (text.trim()) answer(text.trim())
  }

  if (phase === 'dashboard') {
    return (
      <Dashboard
        nombre={answers.nombre}
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
            <button className="opt" onClick={() => analizar(answers)}>Reintentar</button>
          </>
        ) : (
          <p className="loading-text">Analizando tus respuestas…</p>
        )}
      </div>
    )
  }

  return (
    <div className="chat">
      <Robot thinking={false} />

      <div className="log" ref={logRef}>
        {history.map((m, i) => (
          <div key={i} className={`bubble ${m.role}`}>
            {m.text}
          </div>
        ))}
      </div>

      {current?.type === 'text' && (
        <form className="input-row" onSubmit={submitText}>
          <input
            autoFocus
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={current.placeholder}
          />
          <button type="submit" disabled={!text.trim()}>➤</button>
        </form>
      )}

      {current?.type === 'yesno' && (
        <div className="options">
          <button className="opt si" onClick={() => answer('si', 'Sí')}>Sí</button>
          <button className="opt no" onClick={() => answer('no', 'No')}>No</button>
        </div>
      )}

      {current?.type === 'choice' && (
        <div className="options choices">
          {current.options.map((o) => (
            <button key={o.value} className="opt" onClick={() => answer(o.value, o.label)}>
              {o.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default App
