import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Nav from './Nav'
import { nuevaSesion, sessionId } from './session'
import { guardarPerfilPersonalidad, olvidarPerfilPersonalidad } from './personalidad-perfil'
import { authHeader } from './auth'
import GuardarResultados from './GuardarResultados'
import './App.css'
import { API } from './api'

const POR_PAGINA = 16 // 48 ítems / 16 = 3 páginas
const BORRADOR = 'personalidad-borrador'

// Misma escala de caritas que Psicometrico.jsx y Holland.jsx.
const CARITAS = [
  { color: '#e5484d', corto: 'Para nada', boca: 'M12 29 Q20 21 28 29' },
  { color: '#f76b15', corto: 'Poco', boca: 'M12 28 Q20 23 28 28' },
  { color: '#eab308', corto: 'Más o menos', boca: 'M12.5 26.5 L27.5 26.5' },
  { color: '#84cc16', corto: 'Bastante', boca: 'M12 24 Q20 29 28 24' },
  { color: '#16a34a', corto: 'Totalmente', boca: 'M12 23 Q20 31 28 23' },
]

const NOMBRES_DIMENSION = {
  personalidad: 'Personalidad',
  valores: 'Valores',
  estilo_cognitivo: 'Estilo cognitivo',
}

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

export default function Personalidad() {
  const [banco, setBanco] = useState(null)
  const [error, setError] = useState('')
  const [pagina, setPagina] = useState(() => Number(leerBorrador()?.pagina) || 0)
  const [respuestas, setRespuestas] = useState(() => leerBorrador()?.respuestas || {})
  const [enviando, setEnviando] = useState(false)
  const [resultado, setResultado] = useState(null)

  useEffect(() => {
    fetch(`${API}/api/personalidad/preguntas`)
      .then(async (r) => (r.ok ? r.json() : Promise.reject(new Error((await r.json()).detail))))
      .then(setBanco)
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
  const total = banco?.preguntas.length || 48
  const contestadas = Object.keys(respuestas).length
  const faltanEnPagina = actual
    ? actual.filter((p) => respuestas[p.id] === undefined).length
    : 0

  function reiniciar() {
    localStorage.removeItem(BORRADOR)
    olvidarPerfilPersonalidad()
    nuevaSesion()
    setRespuestas({})
    setPagina(0)
    setResultado(null)
    setError('')
  }

  async function terminar() {
    if (enviando) return
    setEnviando(true)
    setError('')
    try {
      const r = await fetch(`${API}/api/personalidad`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeader() },
        body: JSON.stringify({ respuestas, session_id: sessionId() }),
      })
      if (!r.ok) {
        const d = await r.json()
        throw new Error(d.detail?.[0]?.msg || d.detail || 'Error al calificar')
      }
      const puntajes = await r.json()
      setResultado(puntajes)
      guardarPerfilPersonalidad(puntajes)
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
        <span className="pasos-kicker">Perfil antes del chat</span>
        <h1>Personalidad, valores y estilo cognitivo</h1>
        <p className="intro">
          Son <strong>{total} frases cortas</strong>. Marcá qué tan de acuerdo
          estás con cada una. No hay respuestas correctas: contestá lo que sea
          más cierto para vos.
        </p>

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
                <li key={p.id} className="psi-item">
                  <p className="psi-enunciado" id={`per-p${p.id}`}>
                    {p.texto}
                  </p>
                  <div
                    className="psi-escala"
                    role="radiogroup"
                    aria-labelledby={`per-p${p.id}`}
                  >
                    {banco.escala.map((etiqueta, i) => {
                      const c = CARITAS[i]
                      const valor = i + 1
                      const elegida = respuestas[p.id] === valor
                      return (
                        <button
                          key={valor}
                          type="button"
                          role="radio"
                          aria-checked={elegida}
                          aria-label={etiqueta}
                          title={etiqueta}
                          className={elegida ? 'sel' : ''}
                          style={{ '--carita': c.color }}
                          onClick={() =>
                            setRespuestas((r) => ({ ...r, [p.id]: valor }))
                          }
                        >
                          <Carita boca={c.boca} />
                          <span>{c.corto}</span>
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

// `puntajes` llega como {rasgo: 0-100} directo de /api/personalidad.
function BloqueDimension({ titulo, puntajes }) {
  const orden = Object.entries(puntajes).sort((a, b) => b[1] - a[1])
  return (
    <section className="psi-bloque">
      <h2>{titulo}</h2>
      {orden.map(([clave, puntaje]) => (
        <div key={clave} className="psi-rasgo">
          <span className="psi-rasgo-nombre">{clave.replaceAll('_', ' ')}</span>
          <Barra valor={puntaje} />
          <span className="psi-rasgo-valor">{puntaje}</span>
        </div>
      ))}
    </section>
  )
}

function Resultados({ datos, onReiniciar }) {
  const navigate = useNavigate()

  return (
    <div className="pagina">
      <Nav />
      <main className="contenido contenido-angosto">
        <span className="pasos-kicker">Resultados</span>
        <h1>Tu perfil</h1>
        <p className="intro">
          Ningún puntaje es bueno o malo: describen tu estilo, no tu
          capacidad. Lo que orienta es el contraste entre rasgos, no un
          número solo.
        </p>

        <GuardarResultados />

        <BloqueDimension titulo="Personalidad" puntajes={datos.personalidad} />
        <BloqueDimension titulo="Valores" puntajes={datos.valores} />
        <BloqueDimension titulo="Estilo cognitivo" puntajes={datos.estilo_cognitivo} />

        <section className="psi-bloque">
          <h2>¿Y ahora qué?</h2>
          <p className="psi-texto">
            Si seguís al chat, Orienta ya parte de este perfil y no te va a
            volver a preguntar por {NOMBRES_DIMENSION.personalidad.toLowerCase()},{' '}
            {NOMBRES_DIMENSION.valores.toLowerCase()} ni{' '}
            {NOMBRES_DIMENSION.estilo_cognitivo.toLowerCase()}: se enfoca
            directo en encontrar la carrera concreta.
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
