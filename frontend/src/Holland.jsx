import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Nav from './Nav'
import { nuevaSesion, sessionId } from './session'
import { guardarPerfilHolland, olvidarPerfilHolland } from './holland-perfil'
import { authHeader } from './auth'
import GuardarResultados from './GuardarResultados'
import { color } from './colors'
import './App.css'
import './Dashboard.css'
import { API } from './api'

const POR_PAGINA = 12 // el mismo tamaño de página que usa O*NET
const BORRADOR = 'holland-borrador'
// Puntaje máximo por área: 10 ítems, hasta 4 puntos cada uno (escala 1-5, base 0).
const MAX_AREA = 40

// Misma escala de caritas que Psicometrico.jsx, de rojo (1) a verde (5). Acá
// las 5 etiquetas las trae O*NET (banco.opciones), no un array propio: solo
// se reusa el color y el dibujo por posición.
const CARITAS = [
  { color: '#e5484d', boca: 'M12 29 Q20 21 28 29' },
  { color: '#f76b15', boca: 'M12 28 Q20 23 28 28' },
  { color: '#eab308', boca: 'M12.5 26.5 L27.5 26.5' },
  { color: '#84cc16', boca: 'M12 24 Q20 29 28 24' },
  { color: '#16a34a', boca: 'M12 23 Q20 31 28 23' },
]

function Carita({ boca }) {
  return (
    <svg viewBox="0 0 40 40" width="34" height="34" aria-hidden="true">
      <circle cx="20" cy="20" r="16.5" fill="none" stroke="currentColor" strokeWidth="2.2" />
      <circle cx="14.5" cy="16" r="2.1" fill="currentColor" />
      <circle cx="25.5" cy="16" r="2.1" fill="currentColor" />
      <path d={boca} fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  )
}

// ponytail: SOLO PRUEBAS. Cada ítem de O*NET trae su área en `p.area`
// ("realistic", ...); no hay que adivinar el orden. El preset marca "me gusta
// mucho" (5) en los ítems de esas áreas y "no me gusta" (1) en el resto, para
// simular un perfil sin pasar por las 60 preguntas.
const LETRA_DE_AREA = {
  realistic: 'R', investigative: 'I', artistic: 'A',
  social: 'S', enterprising: 'E', conventional: 'C',
}
function cadenaPreset(preguntas, letrasAltas) {
  return preguntas
    .map((p) => (letrasAltas.includes(LETRA_DE_AREA[p.area]) ? '5' : '1'))
    .join('')
}
const PERFILES_PRUEBA = [
  { nombre: 'Realista (R)', letras: 'R' },
  { nombre: 'Investigador (I)', letras: 'I' },
  { nombre: 'Artístico (A)', letras: 'A' },
  { nombre: 'Social (S)', letras: 'S' },
  { nombre: 'Emprendedor (E)', letras: 'E' },
  { nombre: 'Convencional (C)', letras: 'C' },
  { nombre: 'Social+Investigador+Convencional (SIC)', letras: 'SIC' },
  { nombre: 'Artístico+Social (AS)', letras: 'AS' },
]

// Best/Great/Good de O*NET, con el mismo semáforo verde-azul-gris que ya usa
// el resto de la app para "nivel de ajuste" (semántico a propósito, no paleta).
const FIT_COLOR = { Best: '#16a34a', Great: '#2563eb', Good: '#64748b' }
function FitBadge({ fit }) {
  return (
    <span className="carrera-pct" style={{ color: FIT_COLOR[fit] || 'var(--muted)' }}>
      {fit}
    </span>
  )
}

function leerBorrador() {
  try {
    return JSON.parse(localStorage.getItem(BORRADOR) || 'null')
  } catch {
    return null
  }
}

function Barra({ valor }) {
  return (
    <div className="psi-barra">
      <span style={{ width: `${valor}%` }} />
    </div>
  )
}

export default function Holland() {
  const [banco, setBanco] = useState(null)
  const [error, setError] = useState('')
  const [pagina, setPagina] = useState(() => Number(leerBorrador()?.pagina) || 0)
  const [respuestas, setRespuestas] = useState(() => leerBorrador()?.respuestas || {})
  const [enviando, setEnviando] = useState(false)
  const [resultado, setResultado] = useState(null)
  const [letrasCustom, setLetrasCustom] = useState('')

  useEffect(() => {
    fetch(`${API}/api/holland/preguntas`)
      .then(async (r) => (r.ok ? r.json() : Promise.reject(new Error((await r.json()).detail))))
      .then(setBanco)
      // Si el backend está apagado, fetch tira "Failed to fetch": inútil para el alumno.
      .catch((e) =>
        setError(
          e instanceof TypeError
            ? 'No se pudo cargar el cuestionario. ¿Está encendido el servidor?'
            : String(e.message)
        )
      )
  }, [])

  useEffect(() => {
    localStorage.setItem(BORRADOR, JSON.stringify({ respuestas, pagina }))
  }, [respuestas, pagina])

  const paginas = useMemo(() => {
    if (!banco) return []
    const out = []
    for (let i = 0; i < banco.preguntas.length; i += POR_PAGINA) {
      out.push(banco.preguntas.slice(i, i + POR_PAGINA))
    }
    return out
  }, [banco])

  const actual = paginas[pagina]
  const total = banco?.total || 60
  const contestadas = Object.keys(respuestas).length
  const faltanEnPagina = actual
    ? actual.filter((p) => respuestas[p.index] === undefined).length
    : 0

  function reiniciar() {
    localStorage.removeItem(BORRADOR)
    olvidarPerfilHolland() // si lo va a responder de nuevo, el chat no debe usar el viejo
    nuevaSesion() // otra prueba, otra sesión: no mezclar los dos resultados en la base
    setRespuestas({})
    setPagina(0)
    setResultado(null)
    setError('')
  }

  async function terminar(cadenaForzada) {
    if (enviando) return
    setEnviando(true)
    setError('')
    try {
      // La API oficial espera una cadena continua: un dígito por pregunta, en
      // el orden de su índice. Sin ese orden el puntaje sale de otra persona.
      const cadena = cadenaForzada || banco.preguntas.map((p) => respuestas[p.index]).join('')
      const r = await fetch(`${API}/api/holland`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeader() },
        body: JSON.stringify({ respuestas: cadena, zona: 4, session_id: sessionId() }),
      })
      if (!r.ok) {
        const d = await r.json()
        throw new Error(d.detail?.[0]?.msg || d.detail || 'Error al calificar')
      }
      const datos = await r.json()
      setResultado(datos)
      guardarPerfilHolland(datos) // para que el chat lo pueda usar (modo 3)
      localStorage.removeItem(BORRADOR)
      window.scrollTo({ top: 0 })
    } catch (e) {
      setError(String(e.message || e))
    } finally {
      setEnviando(false)
    }
  }

  if (resultado) return <Resultados datos={resultado} onReiniciar={reiniciar} />

  return (
    <div className="pagina">
      <Nav />
      <main className="contenido contenido-angosto">
        <span className="pasos-kicker">Intereses vocacionales</span>
        <h1>Test de Holland (RIASEC)</h1>
        <p className="intro">
          Son <strong>{total} actividades</strong>. Para cada una indicá cuánto te
          gustaría hacerla, sin pensar en cuánto se gana, si hace falta estudiar
          mucho o si creés que serías capaz. No hay respuestas correctas.
        </p>
        {/* La licencia de O*NET exige acreditar y enlazar el servicio. No quitar. */}
        <p className="psi-instruccion">
          Cuestionario <strong>O*NET Interest Profiler</strong> del Departamento de
          Trabajo de EE. UU., en su versión en español. Las preguntas y el puntaje
          vienen de{' '}
          <a href="https://services.onetcenter.org/" target="_blank" rel="noreferrer">
            O*NET Web Services
          </a>
          ; esta plataforma no los modifica.
        </p>

        {import.meta.env.DEV && banco && (
          <section className="psi-bloque" style={{ border: '2px dashed #e5484d' }}>
            <h2>Solo pruebas: perfiles predeterminados</h2>
            <p className="psi-texto">
              Salta las 60 preguntas y califica un perfil simulado, para revisar
              rápido resultados, carreras y recomendaciones. No aparece fuera de
              modo desarrollo.
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {PERFILES_PRUEBA.map((p) => (
                <button
                  key={p.letras}
                  type="button"
                  className="psi-btn-sec"
                  disabled={enviando}
                  onClick={() => terminar(cadenaPreset(banco.preguntas, p.letras))}
                >
                  {p.nombre}
                </button>
              ))}
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 10, alignItems: 'center' }}>
              <input
                type="text"
                placeholder="Combinación libre, ej. RSC"
                value={letrasCustom}
                onChange={(e) => setLetrasCustom(e.target.value.toUpperCase())}
                style={{ maxWidth: 220 }}
              />
              <button
                type="button"
                className="hero-btn"
                disabled={enviando || !/^[RIASEC]+$/.test(letrasCustom)}
                onClick={() => terminar(cadenaPreset(banco.preguntas, letrasCustom))}
              >
                Probar combinación
              </button>
            </div>
          </section>
        )}

        {error && <p className="psi-error">{error}</p>}
        {!banco && !error && <p className="intro">Cargando cuestionario…</p>}

        {banco && actual && (
          <>
            <div className="psi-progreso">
              <Barra valor={Math.round((contestadas / total) * 100)} />
              <span className="psi-progreso-txt">
                {contestadas} de {total} · página {pagina + 1} de {paginas.length}
              </span>
            </div>

            <ul className="psi-lista">
              {actual.map((p) => (
                <li key={p.index} className="psi-item">
                  <p className="psi-enunciado" id={`holland-p${p.index}`}>
                    <span className="psi-num">{p.index}</span>
                    {p.text}
                  </p>
                  {/* role=radiogroup: igual razón que en Psicometrico.jsx, un
                      lector de pantalla no debe anunciar 5 botones sueltos. */}
                  <div
                    className="psi-escala"
                    role="radiogroup"
                    aria-labelledby={`holland-p${p.index}`}
                  >
                    {banco.opciones.map((o, i) => {
                      const c = CARITAS[i]
                      const elegida = respuestas[p.index] === o.value
                      return (
                        <button
                          key={o.value}
                          type="button"
                          role="radio"
                          aria-checked={elegida}
                          aria-label={o.name}
                          title={o.name}
                          className={elegida ? 'sel' : ''}
                          style={{ '--carita': c.color }}
                          onClick={() =>
                            setRespuestas((r) => ({ ...r, [p.index]: o.value }))
                          }
                        >
                          <Carita boca={c.boca} />
                          <span>{o.name}</span>
                        </button>
                      )
                    })}
                  </div>
                </li>
              ))}
            </ul>

            <div className="psi-nav">
              <button
                className="psi-btn-sec"
                disabled={pagina === 0}
                onClick={() => {
                  setPagina((p) => p - 1)
                  window.scrollTo({ top: 0, behavior: 'smooth' })
                }}
              >
                Anterior
              </button>
              {faltanEnPagina > 0 && (
                <span className="psi-faltan">Faltan {faltanEnPagina} en esta página</span>
              )}
              {pagina < paginas.length - 1 ? (
                <button
                  className="hero-btn"
                  disabled={faltanEnPagina > 0}
                  onClick={() => {
                    setPagina((p) => p + 1)
                    window.scrollTo({ top: 0, behavior: 'smooth' })
                  }}
                >
                  Siguiente
                </button>
              ) : (
                <button
                  className="hero-btn"
                  disabled={faltanEnPagina > 0 || contestadas < total || enviando}
                  onClick={terminar}
                >
                  {enviando ? 'Calificando…' : 'Ver mi perfil'}
                </button>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  )
}

function Resultados({ datos, onReiniciar }) {
  const { areas, codigo, carreras, carreras_total, carreras_catalogo } = datos
  const orden = [...areas].sort((a, b) => b.score - a.score)
  const navigate = useNavigate()

  return (
    <div className="pagina">
      <Nav />
      <main className="contenido contenido-angosto">
        <span className="pasos-kicker">Resultados</span>
        <h1>Tu código Holland: {codigo}</h1>
        <p className="intro">
          El código son tus <strong>tres áreas de mayor interés</strong>, de la más
          alta a la más baja. Lo que orienta no es un área sola, sino el contraste
          entre las seis.
        </p>

        <GuardarResultados />

        <section className="psi-bloque">
          <h2>Perfil por área</h2>
          {orden.map((a) => (
            <div key={a.letra} className="psi-rasgo">
              <span className="psi-rasgo-nombre">
                {a.letra}. {a.title}
              </span>
              <Barra valor={Math.round((a.score / MAX_AREA) * 100)} />
              <span className="psi-rasgo-valor">{a.score}</span>
            </div>
          ))}
        </section>

        <section className="psi-bloque">
          <h2>Qué significan tus áreas altas</h2>
          {orden.slice(0, 3).map((a) => (
            <div key={a.letra} style={{ marginBottom: 14 }}>
              <h3>{a.title}</h3>
              <p className="psi-texto">{a.description}</p>
            </div>
          ))}
        </section>

        <section className="psi-bloque">
          <h2>Carreras recomendadas por el Departamento de Trabajo de EE. UU.</h2>
          <p className="psi-texto">
            {carreras.length < carreras_total ? (
              <>
                Las <strong>{carreras.length}</strong> de mejor ajuste, de{' '}
                {carreras_total} que encontró O*NET
              </>
            ) : (
              <>
                Las <strong>{carreras.length}</strong> que encontró O*NET
              </>
            )}{' '}
            para ocupaciones que piden preparación universitaria (job zone 4). Son
            ocupaciones del mercado de EE. UU.: sirven para ver el tipo de trabajo,
            no como catálogo de carreras en Guatemala; para eso está el chat.
          </p>
          <div className="carrera-lista holland-grid">
            {carreras.map((c, i) => (
              <div key={c.code} className="carrera-item" style={{ cursor: 'default' }}>
                <span className="punto" style={{ background: color(i) }} />
                <span className="carrera-nombre">{c.title}</span>
                <FitBadge fit={c.fit} />
              </div>
            ))}
          </div>
        </section>

        {carreras_catalogo?.length > 0 && (
          <section className="psi-bloque">
            <h2>Basado en la escala Holland, estas son afines a tu perfil</h2>
            <p className="psi-texto">
              Carreras de nuestro catálogo con código Holland parecido al tuyo, un
              acercamiento por parámetros del test, no el resultado final del
              chat: la recomendación real usa la conversación completa, no solo
              este perfil.
            </p>
            <div className="carrera-lista holland-grid">
              {carreras_catalogo.map((c, i) => (
                <div key={c.nombre} className="carrera-item" style={{ cursor: 'default' }}>
                  <span className="punto" style={{ background: color(i) }} />
                  <span className="carrera-nombre">{c.nombre}</span>
                  <span className="carrera-pct">{c.codigo}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        <p className="intro">
          Este resultado describe intereses, no capacidades ni rendimiento. No
          sustituye la evaluación de un profesional de la psicología. Puntajes y
          ocupaciones calculados por{' '}
          <a href="https://services.onetcenter.org/" target="_blank" rel="noreferrer">
            O*NET Web Services
          </a>
          , del Departamento de Trabajo de EE. UU.
        </p>

        {/* Modo 3: seguir al chat con este perfil. El chat lo lee de
            localStorage; las 4 preguntas fijas se quedan igual (medido en
            experiments/holland-en-chat.md). */}
        <section className="psi-bloque">
          <h2>¿Y qué estudio en Guatemala?</h2>
          <p className="psi-texto">
            Las ocupaciones de arriba son de EE. UU. Si seguís al chat, Orienta
            usa este perfil como punto de partida y busca la carrera concreta que
            te encaja en las universidades de tu departamento.
          </p>
          <button className="hero-btn" onClick={() => navigate('/mapa')}>
            Continuar al chat con este perfil →
          </button>
        </section>

        <div className="psi-nav">
          <button className="psi-btn-sec" onClick={onReiniciar}>
            Responderlo de nuevo
          </button>
        </div>
      </main>
    </div>
  )
}
