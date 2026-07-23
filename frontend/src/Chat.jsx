import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import Dashboard from './Dashboard'
import { color } from './colors'
import { SESSION_ID } from './session'
import './App.css'

const API = 'http://localhost:8000'
const MIN_ADAPTATIVAS = 4 // mínimo antes de ofrecer el resultado (se siente conversación)
const MAX_ADAPTATIVAS = 8 // tope: perfiles ambiguos afinan más, sin agotar cuota
const MOSTRAR_RADAR = false // ponytail: radar de afinidad en vivo desactivado; poner true para reactivarlo

// Mensajes que rotan bajo la barra de progreso del análisis final.
const MENSAJES_CARGA = [
  'Registrando tus respuestas…',
  'Analizando tu perfil…',
  'Recorriendo el catálogo de carreras…',
  'Alineando las carreras contigo…',
  'Construyendo tu perfil vocacional…',
  'Calculando afinidades…',
  'Puliendo los detalles…',
  'Casi listo…',
]

// Preguntas FIJAS (sin llamar a la IA): nombre + 3 vocacionales genéricas.
// Son catálogo-agnósticas (no mencionan carreras).
const FIJAS = [
  {
    clave: 'nombre',
    tipo: 'texto',
    texto: '¡Hola! Soy Orienta, tu guía vocacional. Para empezar, ¿cómo te llamas?',
    placeholder: 'Escribe tu nombre…',
  },
  {
    clave: 'impacto',
    tipo: 'opcion',
    multiple: true, // puede elegir varios
    texto: '¿Qué tipo de impacto te gustaría tener en el mundo? (puedes elegir varios)',
    opciones: [
      { label: 'Ayudar, enseñar o cuidar a las personas' },
      { label: 'Defender la justicia y resolver conflictos' },
      { label: 'Liderar, organizar negocios o usar tecnología y números' },
      { label: 'Trabajar con la naturaleza, el campo o el ambiente' },
      { label: 'Comunicar, crear, diseñar o investigar la realidad' },
      { label: 'Construir, diseñar o hacer que las cosas funcionen' },
    ],
  },
  {
    clave: 'estilo',
    tipo: 'opcion',
    multiple: true, // puede combinar formas de trabajo
    texto: '¿Cómo prefieres trabajar? (puedes elegir varias)',
    opciones: [
      { label: 'Con personas, en trato directo' },
      { label: 'Analizando datos, ideas y lógica' },
      { label: 'De forma práctica, con las manos' },
      { label: 'Al aire libre y en movimiento' },
    ],
  },
  {
    clave: 'entorno',
    tipo: 'opcion',
    multiple: true,
    texto: '¿Dónde te imaginas trabajando? (puedes elegir varios)',
    opciones: [
      { label: 'En una oficina o empresa' },
      { label: 'En un hospital, clínica o consultorio' },
      { label: 'Al aire libre, en el campo o la naturaleza' },
      { label: 'En un laboratorio o taller técnico' },
      { label: 'En un aula o centro educativo' },
      { label: 'En una obra, con máquinas o herramientas' },
      { label: 'En medios, un estudio creativo o diseñando' },
      { label: 'Con la comunidad, ayudando a personas' },
    ],
  },
  {
    // Banco de palabras: temas de interés alineados a las áreas del catálogo
    // (sin nombrar carreras). El alumno elige varios y puede agregar el suyo.
    clave: 'gustos',
    tipo: 'opcion',
    multiple: true,
    chips: true,
    texto: '¿Qué temas te apasionan? Elige los que quieras (o agrega el tuyo).',
    opciones: [
      { label: 'Matemáticas y números' },
      { label: 'Tecnología y computación' },
      { label: 'Salud y cuidar personas' },
      { label: 'Biología y naturaleza' },
      { label: 'Química y laboratorio' },
      { label: 'Leyes, justicia y debate' },
      { label: 'Negocios, dinero y emprender' },
      { label: 'Arte, diseño y creatividad' },
      { label: 'Comunicación, escritura y medios' },
      { label: 'Enseñar y educar' },
      { label: 'Psicología y comportamiento' },
      { label: 'Medio ambiente y agricultura' },
      { label: 'Construcción, máquinas y cómo funcionan las cosas' },
      { label: 'Gastronomía, turismo y hotelería' },
      { label: 'Historia, sociedad y cultura' },
    ],
  },
]

const post = (ruta, body) =>
  fetch(`${API}${ruta}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

// Filtro básico de groserías para el nombre (misma lista que backend/app/main.py).
// El nombre se muestra en el saludo del dashboard y el PDF, así que se corta aquí
// antes de que avance. ponytail: lista curada, NO exhaustiva; no atrapa evasiones
// ("3stupido"). Se compara por palabra tras normalizar (minúsculas + sin acentos).
const PALABRAS_OFENSIVAS = new Set([
  'estupido', 'estupida', 'idiota', 'imbecil', 'tonto', 'tonta', 'tarado',
  'pendejo', 'pendeja', 'mierda', 'puta', 'puto', 'cabron', 'cabrona', 'verga',
  'culero', 'culo', 'pene', 'pito', 'cono', 'chinga', 'chingar', 'mamon',
  'mamada', 'joder', 'jodete', 'marica', 'maricon', 'zorra', 'perra', 'polla',
  'follar', 'gilipollas', 'cojones', 'baboso', 'babosa', 'estupidos', 'putos',
  'putas', 'wey', 'guey', 'coger', 'verguero',
])

function tieneGroseria(nombre) {
  const norm = [...nombre.normalize('NFKD')]
    .filter((c) => { const n = c.charCodeAt(0); return n < 0x300 || n > 0x36f })
    .join('')
    .toLowerCase()
  return norm.split(/[ \-.']+/).some((t) => PALABRAS_OFENSIVAS.has(t))
}

// Divide un mensaje largo en varias burbujas por oraciones (o ':'), agrupando
// hasta ~150 caracteres. Los mensajes cortos quedan en una sola burbuja.
function enPartes(texto, max = 150) {
  const frases = (texto || '').match(/[^.!?:]+[.!?:]*\s*/g) || [texto]
  const partes = []
  let actual = ''
  for (const f of frases) {
    if (actual && (actual + f).length > max) {
      partes.push(actual.trim())
      actual = f
    } else {
      actual += f
    }
  }
  if (actual.trim()) partes.push(actual.trim())
  return partes
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

  const r = await post('/api/recommend', { estudiante_id, respuestas, session_id: SESSION_ID })
  if (r.status === 503) throw new Error('El motor de IA aún no está configurado en el servidor.')
  if (!r.ok) throw new Error('No pude generar las recomendaciones. Inténtalo de nuevo.')
  return await r.json()
}

// Convierte **negrita** y *cursiva* (Markdown) en elementos React, sin inyectar
// HTML (seguro): solo parte el texto y envuelve. Ignora marcadores sin cerrar.
function Formato({ texto }) {
  const nodos = (texto || '').split(/(\*\*[^*]+\*\*)/g).map((p, i) => {
    if (p.startsWith('**') && p.endsWith('**') && p.length > 4) {
      return <strong key={i}>{p.slice(2, -2)}</strong>
    }
    return p.split(/(\*[^*]+\*)/g).map((s, j) =>
      s.startsWith('*') && s.endsWith('*') && s.length > 2
        ? <em key={`${i}-${j}`}>{s.slice(1, -1)}</em>
        : s
    )
  })
  return <>{nodos}</>
}

function Robot({ thinking, small }) {
  const s = small ? 34 : 96
  return (
    <div className={`robot ${thinking ? 'thinking' : ''} ${small ? 'robot-sm' : ''}`}>
      <svg viewBox="0 0 100 100" width={s} height={s} aria-hidden="true">
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

// Cabecera tipo app de mensajería: avatar + nombre + estado + medidor de perfil.
function ChatHeader({ thinking, confianza }) {
  return (
    <header className="chat-header">
      <div className="chat-avatar">
        <Robot thinking={thinking} small />
        <span className="chat-dot" aria-hidden="true" />
      </div>
      <div className="chat-id">
        <span className="chat-name">Orienta</span>
        <span className={`chat-status ${thinking ? 'esc' : ''}`}>
          {thinking ? 'escribiendo…' : 'En línea · guía vocacional'}
        </span>
      </div>
      {confianza > 0 && (
        <div className="chat-conf" title="Qué tan definido va quedando tu perfil">
          <div className="chat-conf-head">
            <span className="chat-conf-label">Perfil</span>
            <span className="chat-conf-pct">{confianza}%</span>
          </div>
          <div className="chat-conf-track">
            <div className="chat-conf-fill" style={{ width: `${confianza}%` }} />
          </div>
        </div>
      )}
    </header>
  )
}

// Barra de progreso del análisis final. El reporte híbrido tarda (~15-20s), así
// que simula avance: arranca en 10%, sube a saltos y se desacelera cerca del
// final (se queda ~96%) para no completar antes de que llegue la respuesta real.
// Al desmontarse (cuando aparece el dashboard) se entiende como "terminado".
function BarraProgreso() {
  const [pct, setPct] = useState(10)
  const [msg, setMsg] = useState(0)
  useEffect(() => {
    const avance = setInterval(() => {
      setPct((p) => {
        const salto = p < 55 ? 12 : p < 80 ? 7 : p < 92 ? 3 : 1
        return Math.min(96, p + salto)
      })
    }, 2000) // ~20s en llegar a ~92% (el análisis híbrido/2.5-flash tarda)
    const rota = setInterval(() => setMsg((m) => (m + 1) % MENSAJES_CARGA.length), 2800)
    return () => {
      clearInterval(avance)
      clearInterval(rota)
    }
  }, [])
  return (
    <div className="progreso">
      <div className="progreso-pct">{pct}%</div>
      <div className="progreso-track">
        <div className="progreso-fill" style={{ width: `${pct}%` }} />
      </div>
      <p className="loading-text">{MENSAJES_CARGA[msg]}</p>
    </div>
  )
}

// Radar de afinidad en tiempo real: se actualiza con cada pregunta adaptativa.
function Radar({ ranking }) {
  if (!ranking.length) return null
  const max = Math.max(...ranking.map((r) => r.afinidad), 1)
  return (
    <div className="radar">
      <div className="radar-titulo">Tu afinidad en tiempo real</div>
      {ranking.map((r, i) => (
        <div key={r.carrera} className="radar-row">
          <div className="radar-top">
            <span className="radar-nombre">{r.carrera}</span>
            <span className="radar-pct">{r.afinidad}%</span>
          </div>
          <div className="radar-track">
            <div
              className="radar-fill"
              style={{ width: `${(r.afinidad / max) * 100}%`, background: color(i) }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}

// Renderiza las opciones: única o múltiple, con "Otro" y un color por opción.
function Opciones({ pregunta, onAnswer }) {
  const multiple = !!pregunta.multiple
  const [sel, setSel] = useState([])
  const [otroOn, setOtroOn] = useState(false)
  const [otroText, setOtroText] = useState('')

  function clickOpcion(label, i) {
    if (multiple) {
      setSel((s) => (s.includes(i) ? s.filter((x) => x !== i) : [...s, i]))
    } else {
      onAnswer(label)
    }
  }

  function clickOtro() {
    if (multiple) setOtroOn((v) => !v)
    else setOtroOn(true) // única: pasa a modo texto
  }

  function confirmarMulti() {
    const partes = sel.map((i) => pregunta.opciones[i].label)
    if (otroOn && otroText.trim()) partes.push(otroText.trim())
    if (partes.length) onAnswer(partes.join(', '))
  }

  function enviarOtroUnica(e) {
    e.preventDefault()
    if (otroText.trim()) onAnswer(otroText.trim())
  }

  // Selección única en modo "Otro": solo el cuadro de texto.
  if (!multiple && otroOn) {
    return (
      <form className="input-row" onSubmit={enviarOtroUnica}>
        <input
          autoFocus
          value={otroText}
          onChange={(e) => setOtroText(e.target.value)}
          placeholder="Escribe tu respuesta…"
        />
        <button type="submit" disabled={!otroText.trim()}>➤</button>
      </form>
    )
  }

  const puedeContinuar = sel.length > 0 || (otroOn && otroText.trim())

  return (
    <div className={`options choices ${pregunta.chips ? 'chips' : ''}`}>
      {pregunta.opciones.map((o, i) => (
        <button
          key={i}
          className={`opt-color ${sel.includes(i) ? 'sel' : ''}`}
          style={{ '--c': color(i) }}
          onClick={() => clickOpcion(o.label, i)}
        >
          {o.label}
        </button>
      ))}

      <button
        className={`opt-color otro ${otroOn ? 'sel' : ''}`}
        style={{ '--c': '#5c6b80' }}
        onClick={clickOtro}
      >
        Otro / especificar…
      </button>

      {multiple && otroOn && (
        <input
          className="otro-input"
          autoFocus
          value={otroText}
          onChange={(e) => setOtroText(e.target.value)}
          placeholder="Escribe tu respuesta…"
        />
      )}

      {multiple && (
        <button className="continuar-btn" onClick={confirmarMulti} disabled={!puedeContinuar}>
          Continuar →
        </button>
      )}
    </div>
  )
}

function Chat() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const depto = searchParams.get('depto')

  const [respuestas, setRespuestas] = useState({ departamento: depto })
  const [history, setHistory] = useState([{ role: 'bot', text: FIJAS[0].texto }])
  const [paso, setPaso] = useState(FIJAS[0]) // pregunta actual (fija tiene .clave; adaptativa no)
  const [text, setText] = useState('')
  const [phase, setPhase] = useState('chat') // chat | loading | dashboard
  const [carreras, setCarreras] = useState([])
  const [respuestaId, setRespuestaId] = useState(null)
  const [confianza, setConfianza] = useState(null)
  const [error, setError] = useState(null)
  const [cargando, setCargando] = useState(false)
  const [undoStack, setUndoStack] = useState([]) // para "Regresar"
  const [ranking, setRanking] = useState([]) // radar en tiempo real
  const [confianzaChat, setConfianzaChat] = useState(0) // % de seguridad, monotónico (nunca baja)
  const [oferta, setOferta] = useState(null) // { pendiente, puedeSeguir } cuando ya se puede mostrar resultado
  const logRef = useRef(null)

  useEffect(() => {
    logRef.current?.scrollTo(0, logRef.current.scrollHeight)
  }, [history, cargando])

  // Sin departamento en la URL (se llegó sin pasar por /mapa): regresa al mapa.
  useEffect(() => {
    if (!depto) navigate('/mapa', { replace: true })
  }, [depto, navigate])

  async function analizar(resp) {
    setPaso(null)
    setPhase('loading')
    setError(null)
    try {
      const { carreras, respuesta_id, confianza, confianza_nota } = await obtenerCarreras(resp)
      setCarreras(carreras)
      setRespuestaId(respuesta_id ?? null)
      setConfianza(confianza != null ? { valor: confianza, nota: confianza_nota } : null)
      setPhase('dashboard')
    } catch (e) {
      setError(e.message)
    }
  }

  // Muestra un mensaje del bot en varias burbujas, con una pausa de "escribiendo"
  // entre cada una, para que se sienta un orientador y no un muro de texto.
  async function botDice(texto) {
    const partes = enPartes(texto)
    for (let i = 0; i < partes.length; i++) {
      if (i > 0) {
        setCargando(true)
        await sleep(650)
        setCargando(false)
      }
      setHistory((h) => [...h, { role: 'bot', text: partes[i] }])
    }
  }

  // Pide a la IA la siguiente pregunta adaptativa (1 llamada). Esa misma llamada
  // trae el ranking actualizado, con el que calculamos la confianza.
  async function pedirAdaptativa(resp) {
    setError(null)
    setCargando(true)
    try {
      const r = await post('/api/next-question', { respuestas: resp, session_id: SESSION_ID })
      if (r.status === 503) throw new Error('El motor de IA aún no está configurado en el servidor.')
      if (!r.ok) throw new Error('No pude cargar la siguiente pregunta. Inténtalo de nuevo.')
      const q = await r.json()
      if (q.ranking?.length) setRanking(q.ranking)
      // Confianza = afinidad de la carrera líder, pero monotónica: nunca baja.
      const top = q.ranking?.[0]?.afinidad ?? 0
      setConfianzaChat((c) => Math.max(c, top))

      const pregunta = {
        texto: q.pregunta_texto,
        tipo: q.pregunta_tipo,
        multiple: !!q.multiple,
        opciones: q.opciones || [],
      }
      const nAdapt = Object.keys(resp).length - FIJAS.length // adaptativas ya respondidas
      // Ofrecemos el resultado al llegar al mínimo, o antes si la IA ya se dio por
      // segura (terminado): en ese caso no genera más preguntas, forzarla daría una vacía.
      if (nAdapt >= MIN_ADAPTATIVAS || q.terminado) {
        // En vez de decidir por el usuario, le ofrecemos ver el resultado o seguir.
        // Si sigue, mostramos la pregunta ya traída (no la hay si la IA terminó).
        const puedeSeguir = nAdapt < MAX_ADAPTATIVAS && !q.terminado
        if (q.alerta_contradiccion) {
          setHistory((h) => [...h, { role: 'alerta', text: q.alerta_contradiccion }])
        }
        setPaso(null)
        setOferta({ pendiente: puedeSeguir ? pregunta : null, puedeSeguir })
      } else {
        // Debajo del mínimo: seguimos preguntando automáticamente.
        setCargando(false) // apaga los puntos del fetch; botDice maneja los suyos
        if (q.alerta_contradiccion) {
          setHistory((h) => [...h, { role: 'alerta', text: q.alerta_contradiccion }])
        }
        await botDice(q.pregunta_texto)
        setPaso(pregunta)
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setCargando(false)
    }
  }

  // El usuario decide seguir chateando: mostramos la pregunta ya traída.
  async function continuarChat() {
    const q = oferta?.pendiente
    setOferta(null)
    if (!q) return
    await botDice(q.texto)
    setPaso(q)
  }

  // El usuario decide ver su recomendación.
  function verResultados() {
    setOferta(null)
    analizar(respuestas)
  }

  // Decide qué sigue: fija (sin IA), adaptativa (IA), o análisis final.
  function avanzar(resp) {
    const fijasAns = FIJAS.filter((f) => resp[f.clave] !== undefined).length
    if (fijasAns < FIJAS.length) {
      const q = { ...FIJAS[fijasAns] }
      q.texto = q.texto.replace('{nombre}', resp.nombre || '')
      setPaso(q)
      setHistory((h) => [...h, { role: 'bot', text: q.texto }])
      return
    }
    // El análisis final ya no se dispara solo: pedirAdaptativa ofrece la decisión
    // al usuario una vez alcanzado el mínimo de preguntas.
    pedirAdaptativa(resp)
  }

  function answer(respuesta) {
    // Guarda una foto para poder "Regresar" a esta pregunta.
    setUndoStack((s) => [...s, { respuestas, history, paso }])
    const clave = paso.clave ?? paso.texto
    const next = { ...respuestas, [clave]: respuesta }
    setRespuestas(next)
    setHistory((h) => [...h, { role: 'user', text: respuesta }])
    setText('')
    setPaso(null)
    avanzar(next)
  }

  function regresar() {
    if (!undoStack.length) return
    const prev = undoStack[undoStack.length - 1]
    setRespuestas(prev.respuestas)
    setHistory(prev.history)
    setPaso(prev.paso)
    setText('')
    setError(null)
    setOferta(null) // la confianza no baja (monotónica), pero cerramos la oferta
    setUndoStack((s) => s.slice(0, -1))
  }

  // Valida el nombre en la frontera de entrada (misma regla que el backend en
  // main.py): el nombre se muestra en el dashboard/PDF y entra al prompt, así que
  // se corta aquí un nombre vacío/kilométrico/con basura o con groserías comunes.
  function nombreInvalido(v) {
    if (v.length < 2 || v.length > 40) return 'Escribe tu nombre (entre 2 y 40 letras).'
    if (!/^[\p{L}'’\-. ]+$/u.test(v)) return 'Usa solo letras, espacios, guiones y apóstrofos.'
    if (tieneGroseria(v)) return 'Por favor escribe tu nombre real, sin palabras ofensivas.'
    return null
  }

  function submitText(e) {
    e.preventDefault()
    const val = text.trim().replace(/\s+/g, ' ')
    if (!val) return
    if (paso?.clave === 'nombre') {
      const err = nombreInvalido(val)
      if (err) { setError(err); return }
    }
    setError(null)
    answer(val)
  }

  if (phase === 'dashboard') {
    return (
      <Dashboard
        nombre={respuestas.nombre}
        carreras={carreras}
        respuestaId={respuestaId}
        confianza={confianza}
        respuestas={respuestas}
        onReiniciar={() => navigate('/')}
      />
    )
  }

  if (phase === 'loading') {
    return (
      <div className="layout">
      <div className="chat loading-screen">
        {error ? (
          <>
            <div className="spinner-ring err">
              <Robot thinking={false} />
            </div>
            <p className="loading-text">{error}</p>
            <button className="opt" onClick={() => analizar(respuestas)}>Reintentar</button>
          </>
        ) : (
          <BarraProgreso />
        )}
      </div>
      </div>
    )
  }

  const esAdaptativa = paso && !paso.clave
  const hayControles = !cargando && (oferta || undoStack.length > 0 || error ||
    paso?.tipo === 'texto' || paso?.tipo === 'sino' || paso?.tipo === 'opcion' || esAdaptativa)

  return (
    <div className="layout">
      <div className="chat">
      <ChatHeader thinking={cargando} confianza={confianzaChat} />

      <div className="log" ref={logRef}>
        {history.map((m, i) => (
          <div key={i} className={`bubble ${m.role}`}>
            <Formato texto={m.text} />
          </div>
        ))}
        {cargando && (
          <div className="bubble bot escribiendo">
            <span></span><span></span><span></span>
          </div>
        )}
      </div>

      {hayControles && (
      <div className="chat-footer">
      {oferta && (
        <div className="oferta">
          <p className="oferta-msg">
            Ya tengo tu perfil con un <strong>{confianzaChat}%</strong> de seguridad.
            {oferta.puedeSeguir
              ? ' ¿Quieres ver tu recomendación de carreras o seguir afinándolo en el chat?'
              : ' Cuando quieras, mira tu recomendación de carreras.'}
          </p>
          <div className="oferta-btns">
            <button className="opt" onClick={verResultados}>Ver mi recomendación →</button>
            {oferta.puedeSeguir && (
              <button className="opt ghost" onClick={continuarChat}>Seguir chateando</button>
            )}
          </div>
        </div>
      )}

      {undoStack.length > 0 && (
        <button className="regresar-btn" onClick={regresar}>← Regresar</button>
      )}

      {error && (
        <div className="options" style={{ flexDirection: 'column', alignItems: 'center' }}>
          <p className="loading-text">{error}</p>
          <button className="opt" onClick={() => pedirAdaptativa(respuestas)}>Reintentar</button>
        </div>
      )}

      {paso?.tipo === 'texto' && (
        <form className="input-row" onSubmit={submitText}>
          <input
            autoFocus
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={paso.placeholder || 'Escribe tu respuesta…'}
          />
          <button type="submit" disabled={!text.trim()} aria-label="Enviar">➤</button>
        </form>
      )}

      {paso?.tipo === 'sino' && (
        <div className="options">
          <button className="opt si" onClick={() => answer('Sí')}>Sí</button>
          <button className="opt no" onClick={() => answer('No')}>No</button>
        </div>
      )}

      {paso?.tipo === 'opcion' && (
        <Opciones key={paso.texto} pregunta={paso} onAnswer={answer} />
      )}

      {esAdaptativa && (
        <button className="terminar-btn" onClick={() => analizar(respuestas)}>
          Ya, muéstrame mis resultados →
        </button>
      )}
      </div>
      )}
      </div>

      {MOSTRAR_RADAR && ranking.length > 0 && (
        <aside className="radar-aside">
          <Radar ranking={ranking} />
        </aside>
      )}
    </div>
  )
}

export default Chat
