import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Nav from './Nav'
import { nuevaSesion, sessionId } from './session'
import { guardarPerfilHolland, olvidarPerfilHolland } from './holland-perfil'
import './App.css'

const API = 'http://localhost:8000'
const POR_PAGINA = 12 // el mismo tamaño de página que usa O*NET
const BORRADOR = 'holland-borrador'
// Puntaje máximo por área: 10 ítems, hasta 4 puntos cada uno (escala 1-5, base 0).
const MAX_AREA = 40

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

  async function terminar() {
    if (enviando) return
    setEnviando(true)
    setError('')
    try {
      // La API oficial espera una cadena continua: un dígito por pregunta, en
      // el orden de su índice. Sin ese orden el puntaje sale de otra persona.
      const cadena = banco.preguntas.map((p) => respuestas[p.index]).join('')
      const r = await fetch(`${API}/api/holland`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
                  <p className="psi-enunciado">
                    <span className="psi-num">{p.index}</span>
                    {p.text}
                  </p>
                  <div className="psi-opciones">
                    {banco.opciones.map((o) => (
                      <button
                        key={o.value}
                        className={respuestas[p.index] === o.value ? 'sel' : ''}
                        onClick={() =>
                          setRespuestas((r) => ({ ...r, [p.index]: o.value }))
                        }
                      >
                        {o.name}
                      </button>
                    ))}
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
  const { areas, codigo, carreras, carreras_total } = datos
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
          <h2>Ocupaciones afines</h2>
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
            no como catálogo de carreras en Guatemala — para eso está el chat.
          </p>
          <ul className="psi-metricas">
            {carreras.map((c) => (
              <li key={c.code}>
                {c.title} <strong>{c.fit}</strong> · {c.code}
              </li>
            ))}
          </ul>
        </section>

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
