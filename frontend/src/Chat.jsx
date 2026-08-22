import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import Dashboard from './Dashboard'
import { color } from './colors'
import { nuevaSesion, sessionId } from './session'
import { leerPerfilHolland } from './holland-perfil'
import { leerPerfilPersonalidad } from './personalidad-perfil'
import { authHeader, sesionActual } from './auth'
import './App.css'
import { API } from './api'
import { FIJAS, grado } from './preguntas-fijas'

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

const post = (ruta, body) =>
  fetch(`${API}${ruta}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify(body),
  })

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

// Cuanto dejar una burbuja en pantalla cuando la voz esta apagada: a ~200
// palabras por minuto de lectura (300 ms por palabra) mas un respiro fijo, y
// escalado con el mismo control de velocidad que la voz.
// ponytail: cuenta palabras, no silabas ni signos; alcanza para frases cortas.
function tiempoLectura(texto) {
  const palabras = (texto || '').trim().split(/\s+/).filter(Boolean).length
  const ms = (500 + palabras * 300) / velocidad
  return Math.min(9000, Math.max(900, ms))
}

// Los 429 los redacta el backend (enfriamiento entre evaluaciones o tope de uso
// del día, ver backend/app/cuota.py) y se muestran tal cual: un mensaje genérico
// dejaría al alumno sin saber por qué se detuvo ni cuándo puede volver.
async function errorDelBackend(r, generico) {
  const d = await r.json().catch(() => null)
  return new Error(typeof d?.detail === 'string' ? d.detail : generico)
}

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

// TTS: voz neuronal de Edge (edge-tts) vía el backend (/api/tts), que suena
// natural en vez de la robótica de speechSynthesis. Si el backend/edge-tts
// falla (API no oficial, puede romperse), cae a la voz nativa del navegador.
let vozHabilitada = true
let audioActual = null
let velocidad = 1 // 1, 1.1, 1.2, 1.25, 1.3, 1.4 o 1.5; la normal se siente lenta
const VELOCIDADES = [1, 1.1, 1.2, 1.25, 1.3, 1.4, 1.5]

// Cachea el audio por texto exacto: las preguntas fijas siempre son el mismo
// texto, así que se piden una sola vez (precargadas en cargarFijas()) y de ahí
// en adelante salen del caché sin ida y vuelta al backend.
const cacheAudio = new Map() // texto -> URL del blob

// Quita lo que no debe LEERSE en voz alta pero sí debe VERSE en pantalla:
// negrita markdown y acotaciones entre paréntesis ("(puedes elegir varios)").
function limpiarParaVoz(texto) {
  return (texto || '')
    .replace(/\*\*/g, '')
    .replace(/\([^)]*\)/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

function hablarNativo(texto) {
  if (!('speechSynthesis' in window)) return Promise.resolve()
  return new Promise((resolve) => {
    const u = new SpeechSynthesisUtterance(texto)
    u.lang = 'es-MX'
    u.rate = velocidad
    u.onend = resolve
    u.onerror = resolve
    window.speechSynthesis.speak(u)
  })
}

// Pide (o reutiliza del caché) el audio de un texto, SIN reproducirlo todavía.
// Devuelve null si la voz está apagada/oculta o si falló (así el llamador cae
// a hablarNativo en vez de intentar reproducir un blob vacío).
async function cargarAudio(texto) {
  const limpio = limpiarParaVoz(texto)
  if (!vozHabilitada || document.hidden || !limpio) return null
  if (cacheAudio.has(limpio)) return cacheAudio.get(limpio)
  try {
    const r = await fetch(`${API}/api/tts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ texto: limpio }),
    })
    if (!r.ok) throw new Error('tts backend error')
    const blob = await r.blob()
    const url = URL.createObjectURL(blob)
    cacheAudio.set(limpio, url)
    return url
  } catch {
    return null
  }
}

function reproducirUrl(url) {
  return new Promise((resolve) => {
    audioActual = new Audio(url)
    audioActual.playbackRate = velocidad
    audioActual.onended = resolve
    audioActual.onerror = resolve
    audioActual.onpause = resolve // silenciar a media lectura no debe colgar el turno
    audioActual.play().catch(resolve)
  })
}

// Habla y espera a que termine (evita que dos burbujas se lean encimadas);
// resuelve de una vez si la voz está apagada o el texto viene vacío.
async function hablar(texto) {
  const limpio = limpiarParaVoz(texto)
  if (!vozHabilitada || document.hidden || !limpio) return
  const url = await cargarAudio(limpio)
  if (url) await reproducirUrl(url)
  else await hablarNativo(limpio)
}

// Sonido de "escribiendo" mientras la IA piensa: clics cortos sintetizados con
// WebAudio, así no hay que servir ni cargar un archivo de audio.
// ponytail: intervalo fijo; si se quiere ritmo humano, variar el delay por clic.
let ctxTecleo = null
let tecleoTimer = null
function tecleo(encendido) {
  if (!encendido) {
    clearInterval(tecleoTimer)
    tecleoTimer = null
    return
  }
  if (tecleoTimer) return
  ctxTecleo ||= new (window.AudioContext || window.webkitAudioContext)()
  const clic = () => {
    const t = ctxTecleo.currentTime
    const osc = ctxTecleo.createOscillator()
    const vol = ctxTecleo.createGain()
    osc.type = 'square'
    osc.frequency.value = 1400 + Math.random() * 700
    vol.gain.setValueAtTime(0.025, t)
    vol.gain.exponentialRampToValueAtTime(0.0001, t + 0.03)
    osc.connect(vol).connect(ctxTecleo.destination)
    osc.start(t)
    osc.stop(t + 0.04)
  }
  clic()
  tecleoTimer = setInterval(clic, 130)
}

// Guarda el perfil y pide el análisis de afinidad. Lanza error si falla.
async function obtenerCarreras(respuestas) {
  let estudiante_id = 0
  try {
    const reg = await post('/api/register', { nombre: respuestas.nombre || 'Anónimo' })
    if (reg.ok) {
      estudiante_id = (await reg.json()).id
      // El session_id acompana el recorrido entero (Holland -> chat): sin el,
      // esta fila queda huerfana y el tope diario cuenta dos evaluaciones donde
      // el alumno hizo una sola. Tambien es por donde /historial/reclamar cruza.
      await post('/api/submit-survey', { estudiante_id, respuestas, session_id: sessionId() })
    }
  } catch {
    /* backend caído para guardar: seguimos al análisis igual */
  }

  const r = await post('/api/recommend', {
    estudiante_id,
    respuestas,
    session_id: sessionId(),
    holland: leerPerfilHolland(),
    personalidad: leerPerfilPersonalidad(),
  })
  if (!r.ok) throw await errorDelBackend(r, 'No pude generar las recomendaciones. Inténtalo de nuevo.')
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

function Robot({ thinking, cargando, small }) {
  const s = small ? 34 : 96
  return (
    <div className={`robot ${thinking ? 'thinking' : ''} ${cargando ? 'cargando' : ''} ${small ? 'robot-sm' : ''}`}>
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
  const [saliendo, setSaliendo] = useState(null) // labels elegidos mientras se anima la salida

  // Al responder: las no elegidas se desvanecen y la elegida se despide; recién
  // entonces se avisa al chat (que muestra la elegida bajo la pregunta).
  function responder(valor, elegidos) {
    setSaliendo(elegidos)
    setTimeout(() => onAnswer(valor), 300)
  }

  function clickOpcion(label, i) {
    if (multiple) {
      setSel((s) => (s.includes(i) ? s.filter((x) => x !== i) : [...s, i]))
    } else {
      responder(label, [label])
    }
  }

  function clickOtro() {
    if (multiple) setOtroOn((v) => !v)
    else setOtroOn(true) // única: pasa a modo texto
  }

  function confirmarMulti() {
    const partes = sel.map((i) => pregunta.opciones[i].label)
    if (otroOn && otroText.trim()) partes.push(otroText.trim())
    if (partes.length) responder(partes.join(', '), partes)
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
  // Mientras se anima la salida: la elegida se despide, el resto se desvanece.
  const salida = (label) => (saliendo ? (saliendo.includes(label) ? 'elegido' : 'saliendo') : '')

  return (
    <div className={`options choices ${pregunta.chips ? 'chips' : ''}`}>
      {pregunta.opciones.map((o, i) => (
        <button
          key={i}
          className={`opt-color ${sel.includes(i) ? 'sel' : ''} ${salida(o.label)}`}
          style={{ '--c': color(i) }}
          onClick={() => clickOpcion(o.label, i)}
        >
          {o.label}
        </button>
      ))}

      {multiple && otroOn ? (
        // Ya elegida "Otro": la misma celda se convierte en el cuadro de texto
        // (mismo tamaño/posición que el resto de opciones, no una fila aparte).
        <div className="opt-color otro otro-activo sel" style={{ '--c': '#5c6b80' }}>
          <input
            className="otro-input-inline"
            autoFocus
            value={otroText}
            onChange={(e) => setOtroText(e.target.value)}
            placeholder="Escribe tu respuesta…"
          />
          <button
            type="button"
            className="otro-quitar"
            aria-label="Quitar Otro"
            title="Quitar Otro"
            onClick={() => { setOtroOn(false); setOtroText('') }}
          >
            ×
          </button>
        </div>
      ) : pregunta.sinOtro ? null : (
        <button
          className={`opt-color otro ${otroOn ? 'sel' : ''} ${salida('')}`}
          style={{ '--c': '#5c6b80' }}
          onClick={clickOtro}
        >
          Otro / especificar…
        </button>
      )}

      {multiple && (
        <button
          className={`continuar-btn ${salida('')}`}
          onClick={confirmarMulti}
          disabled={!puedeContinuar}
        >
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
  const [diversificados, setDiversificados] = useState([]) // solo si va en básicos
  const [respuestaId, setRespuestaId] = useState(null)
  const [confianza, setConfianza] = useState(null)
  const [error, setError] = useState(null) // fallo de API (muestra "Reintentar")
  const [avisoInput, setAvisoInput] = useState(null) // validación del input (nombre)
  const [cargando, setCargando] = useState(false)
  const [undoStack, setUndoStack] = useState([]) // para "Regresar"
  const [ranking, setRanking] = useState([]) // radar en tiempo real
  const [confianzaChat, setConfianzaChat] = useState(0) // % de seguridad, monotónico (nunca baja)
  // Modo 3: el alumno hizo el test de Holland antes. Se lee una vez al montar.
  const [perfilHolland] = useState(leerPerfilHolland)
  // Modo "perfil": el alumno hizo el test corto de personalidad antes.
  const [perfilPersonalidad] = useState(leerPerfilPersonalidad)
  const [oferta, setOferta] = useState(null) // { pendiente, puedeSeguir } cuando ya se puede mostrar resultado
  const [voz, setVoz] = useState(vozHabilitada)
  const [vel, setVel] = useState(velocidad)
  const [menuVel, setMenuVel] = useState(false) // menú de velocidades abierto
  const [iniciado, setIniciado] = useState(false) // false = solo la burbuja flotante (pantalla tipo Siri)
  const [hablando, setHablando] = useState(false) // true mientras suena el audio de la pregunta actual
  const [elegida, setElegida] = useState(null) // respuesta recién elegida, visible bajo la pregunta mientras carga la siguiente
  const logRef = useRef(null)

  useEffect(() => {
    logRef.current?.scrollTo(0, logRef.current.scrollHeight)
  }, [history, cargando])

  // Tecleo mientras la IA piensa (avisa que no se congeló). Sigue al botón de
  // silencio: si la voz está apagada, tampoco suena.
  useEffect(() => {
    tecleo(cargando && voz)
    return () => tecleo(false)
  }, [cargando, voz])

  // Envuelve hablar() para poder animar la burbuja mientras suena el audio.
  async function decir(texto) {
    setHablando(true)
    await hablar(texto)
    setHablando(false)
  }

  function iniciar() {
    setIniciado(true)
    decir(FIJAS[0].texto) // el saludo no se leyó al montar (falta el gesto del usuario para el audio)
  }

  // Último mensaje del bot/alerta (lo único que se muestra en pantalla; el
  // historial completo sigue guardándose para que "Regresar" funcione igual).
  const mensajeActual = [...history].reverse().find((m) => m.role !== 'user')

  // Sin departamento en la URL (se llegó sin pasar por /mapa): regresa al mapa.
  useEffect(() => {
    if (!depto) navigate('/mapa', { replace: true })
  }, [depto, navigate])

  // Las 5 preguntas fijas son siempre el mismo texto: se precargan al entrar a
  // la página (antes de tocar la burbuja) para que al mostrarlas ya salgan del
  // caché y suenen sin el retraso de pedirle el audio a edge-tts.
  useEffect(() => {
    // Solo las de texto fijo: las que dependen de respuestas anteriores (el
    // grado, la carrera, el gusto) todavía no tienen texto que precargar.
    FIJAS.forEach((f) => { if (typeof f.texto === 'string') cargarAudio(f.texto) })
  }, [])

  async function analizar(resp) {
    setPaso(null)
    setPhase('loading')
    setError(null)
    try {
      const { carreras, respuesta_id, confianza, confianza_nota, diversificados } = await obtenerCarreras(resp)
      setCarreras(carreras)
      setDiversificados(diversificados || [])
      setRespuestaId(respuesta_id ?? null)
      setConfianza(confianza != null ? { valor: confianza, nota: confianza_nota } : null)
      setPhase('dashboard')
    } catch (e) {
      setError(e.message)
    }
  }

  // Muestra un mensaje del bot en varias burbujas. El texto de una pregunta
  // adaptativa lo genera la IA al vuelo, así que su audio no puede estar en
  // caché de antemano: se piden TODAS las partes en paralelo de una vez y solo
  // se espera la primera. Mientras suena la parte 1, las demás ya están
  // llegando, así que solo la primera burbuja tiene retraso perceptible.
  async function botDice(texto) {
    const partes = enPartes(texto)
    const limpios = partes.map(limpiarParaVoz)
    // Si la voz esta apagada no se pide nada; si el alumno la enciende a media
    // lectura, la parte pendiente pide su audio al vuelo (por eso el ||=).
    const audios = limpios.map((t) => (vozHabilitada ? cargarAudio(t) : null))
    for (let i = 0; i < partes.length; i++) {
      setCargando(true)
      const url = vozHabilitada ? await (audios[i] ||= cargarAudio(limpios[i])) : null
      setCargando(false)
      setElegida(null) // ya llegó la siguiente pregunta: se retira la respuesta anterior
      setHistory((h) => [...h, { role: 'bot', text: partes[i] }])
      if (vozHabilitada) {
        setHablando(true)
        if (url) await reproducirUrl(url)
        else await hablarNativo(limpios[i])
        setHablando(false)
      } else {
        await sleep(tiempoLectura(partes[i])) // sin voz: da tiempo de leer
      }
    }
  }

  // Pide a la IA la siguiente pregunta adaptativa (1 llamada). Esa misma llamada
  // trae el ranking actualizado, con el que calculamos la confianza.
  async function pedirAdaptativa(resp) {
    setError(null)
    setCargando(true)
    try {
      const r = await post('/api/next-question', {
        respuestas: resp,
        session_id: sessionId(),
        holland: leerPerfilHolland(),
        personalidad: leerPerfilPersonalidad(),
      })
      if (!r.ok) throw await errorDelBackend(r, 'No pude cargar la siguiente pregunta. Inténtalo de nuevo.')
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
        setElegida(null)
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
    // Primera fija sin responder que APLIQUE a este alumno: 'si' deja saltar las
    // que no vienen al caso (ver 'carrera_cursada' en básicos).
    const fija = FIJAS.find((f) => resp[f.clave] === undefined && (!f.si || f.si(resp)))
    if (fija) {
      const q = { ...fija }
      q.texto = typeof q.texto === 'function'
        ? q.texto(resp)
        : q.texto.replace('{nombre}', resp.nombre || '')
      // Las opciones también pueden depender de lo ya contestado (los grados
      // salen del nivel que eligió, los motivos también).
      if (typeof q.opciones === 'function') q.opciones = q.opciones(resp)
      setElegida(null) // las fijas no esperan a la IA: no hace falta mostrar la elegida
      setPaso(q)
      setHistory((h) => [...h, { role: 'bot', text: q.texto }])
      decir(q.texto)
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
    // La carrera que abandonó se guarda aparte para que el backend la saque del
    // catálogo (filtro.descartar). Va explícita y no adivinada del texto del
    // grado, que puede cambiar de redacción.
    if (clave === 'carrera_cursada' && grado(next)?.descarta) next.carrera_descartada = respuesta
    setRespuestas(next)
    setHistory((h) => [...h, { role: 'user', text: respuesta }])
    setText('')
    setPaso(null)
    setElegida(respuesta)
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
    setAvisoInput(null)
    setElegida(null)
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

  // La edad entra al prompt y al historial: se acota aquí a un número creíble.
  function edadInvalida(v) {
    if (!/^\d{1,2}$/.test(v) || Number(v) < 10) return 'Escribe tu edad en números (de 10 a 99).'
    return null
  }

  // La carrera cursada se muestra dentro de la pregunta siguiente y entra al
  // prompt, así que se corta aquí lo vacío o lo kilométrico.
  function carreraInvalida(v) {
    if (v.length < 2 || v.length > 60) return 'Escribe el nombre de la carrera (entre 2 y 60 letras).'
    if (!/^[\p{L}\p{N}'’\-.,() ]+$/u.test(v)) return 'Usa solo letras, números y espacios.'
    return null
  }

  function submitText(e) {
    e.preventDefault()
    const val = text.trim().replace(/\s+/g, ' ')
    if (!val) return
    const valida = paso?.clave === 'nombre' ? nombreInvalido
      : paso?.clave === 'edad' ? edadInvalida
      : paso?.clave === 'carrera_cursada' ? carreraInvalida : null
    if (valida) {
      const err = valida(val)
      if (err) { setAvisoInput(err); return }
    }
    setAvisoInput(null)
    answer(val)
  }

  if (phase === 'dashboard') {
    return (
      <Dashboard
        nombre={respuestas.nombre}
        carreras={carreras}
        diversificados={diversificados}
        respuestaId={respuestaId}
        confianza={confianza}
        respuestas={respuestas}
        onReiniciar={() => {
          // Otra prueba = otra sesión. Se pide explícitamente porque navegar a
          // '/' NO recarga la página: sin esto, las dos pruebas quedaban en la
          // base bajo el mismo session_id.
          nuevaSesion()
          navigate('/')
        }}
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

  // Pantalla inicial: solo la burbuja flotante. Se toca para empezar (el click
  // también sirve de gesto del usuario para que el navegador permita el audio).
  if (!iniciado) {
    return (
      <div className="layout">
        <div className="siri-idle" onClick={iniciar} role="button" tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && iniciar()}>
          <Robot thinking />
          <p className="siri-idle-hint">Toca para hablar con Orienta</p>
        </div>
      </div>
    )
  }

  return (
    <div className="layout">
      <div className="chat siri">
      <button
        className="voz-toggle"
        title={voz ? 'Silenciar voz' : 'Activar voz'}
        onClick={() => {
          vozHabilitada = !vozHabilitada
          setVoz(vozHabilitada)
          if (!vozHabilitada) { window.speechSynthesis?.cancel(); audioActual?.pause() }
        }}
      >
        {voz ? '🔊' : '🔇'}
      </button>
      {menuVel && <div className="vel-backdrop" onClick={() => setMenuVel(false)} />}
      <div className="vel-wrap">
        <button
          className={`vel-toggle${menuVel ? ' abierto' : ''}`}
          title="Velocidad de la voz"
          aria-expanded={menuVel}
          aria-haspopup="menu"
          onClick={() => setMenuVel((m) => !m)}
        >
          {vel}×
        </button>
        {menuVel && (
          <div className="vel-menu" role="menu">
            {VELOCIDADES.map((v) => (
              <button
                key={v}
                role="menuitem"
                className={v === velocidad ? 'activo' : ''}
                onClick={() => {
                  velocidad = v
                  setVel(v)
                  if (audioActual) audioActual.playbackRate = v // aplica ya al audio que esté sonando
                  setMenuVel(false)
                }}
              >
                {v}×
              </button>
            ))}
          </div>
        )}
      </div>
      {confianzaChat > 0 && (
        <div className="siri-conf" title="Qué tan definido va quedando tu perfil">
          Perfil <strong>{confianzaChat}%</strong>
        </div>
      )}
      {perfilHolland && (
        <div
          className="siri-conf siri-holland"
          title="Orienta está usando el resultado de tu test de Holland"
        >
          Holland <strong>{perfilHolland.codigo}</strong>
        </div>
      )}
      {perfilPersonalidad && (
        <div
          className="siri-conf siri-personalidad"
          title="Orienta está usando tu perfil de personalidad, valores y estilo cognitivo"
        >
          Perfil <strong>✓</strong>
        </div>
      )}

      <div className="siri-stage" ref={logRef}>
        <Robot thinking={hablando} cargando={cargando} />
        {mensajeActual && (
          <p key={history.indexOf(mensajeActual)} className={`siri-texto ${mensajeActual.role}`}>
            <Formato texto={mensajeActual.text} />
          </p>
        )}
        {elegida && <div className="elegida-chip">{elegida}</div>}
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
        <>
          {avisoInput && <p className="aviso-input">{avisoInput}</p>}
          <form className="input-row" onSubmit={submitText}>
            <input
              autoFocus
              value={text}
              inputMode={paso.clave === 'edad' ? 'numeric' : undefined}
              onChange={(e) => setText(e.target.value)}
              placeholder={paso.placeholder || 'Escribe tu respuesta…'}
            />
            <button type="submit" disabled={!text.trim()} aria-label="Enviar">➤</button>
          </form>
        </>
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
