import { useState } from 'react'
import { ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { color } from './colors'
import { SESSION_ID } from './session'
import './Dashboard.css'

const API = 'http://localhost:8000'

const postJSON = (ruta, body) =>
  fetch(`${API}${ruta}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then((r) => {
    if (!r.ok) throw new Error('No se pudo generar. Inténtalo de nuevo.')
    return r.json()
  })

function ConfianzaBadge({ confianza }) {
  if (!confianza) return null
  const { valor, nota } = confianza
  const nivel = valor >= 80 ? 'alta' : valor >= 50 ? 'media' : 'baja'
  return (
    <div className={`confianza-badge ${nivel}`} title={nota}>
      <span className="confianza-valor">{valor}%</span>
      <span className="confianza-txt">confianza · {nota}</span>
    </div>
  )
}

// Modal genérico simple (overlay + panel).
function Modal({ titulo, onClose, children }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-panel" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2>{titulo}</h2>
          <button className="modal-cerrar" onClick={onClose}>×</button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  )
}

// Botón "Un día siendo..." — genera y muestra una narrativa de la carrera.
function SimuladorDia({ carrera, respuestas }) {
  const [abierto, setAbierto] = useState(false)
  const [cargando, setCargando] = useState(false)
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState(null)

  async function abrir() {
    setAbierto(true)
    if (datos) return
    setCargando(true)
    setError(null)
    try {
      const d = await postJSON('/api/simular-dia', {
        carrera: carrera.carrera,
        descripcion: carrera.descripcion,
        respuestas,
        session_id: SESSION_ID,
      })
      setDatos(d)
    } catch (e) {
      setError(e.message)
    } finally {
      setCargando(false)
    }
  }

  return (
    <>
      <button className="wow-btn" onClick={abrir}>Un día siendo {carrera.carrera.split(' ').slice(0, 3).join(' ')}…</button>
      {abierto && (
        <Modal titulo={`Un día como ${carrera.carrera}`} onClose={() => setAbierto(false)}>
          {cargando && <p className="loading-text">Imaginando tu día…</p>}
          {error && <p className="loading-text">{error}</p>}
          {datos && (
            <>
              <div className="timeline">
                {datos.eventos.map((ev, i) => (
                  <div key={i} className="timeline-item">
                    <div className="timeline-hora">{ev.hora}</div>
                    <div className="timeline-punto" />
                    <div className="timeline-actividad">{ev.actividad}</div>
                  </div>
                ))}
              </div>
              <p className="timeline-cierre">{datos.cierre}</p>
            </>
          )}
        </Modal>
      )}
    </>
  )
}

// Botón "Ver catálogo" — lista todas las carreras del catálogo, agrupadas por
// nombre con sus sedes. Útil para ver qué existe más allá de lo recomendado.
function CatalogoCarreras() {
  const [abierto, setAbierto] = useState(false)
  const [grupos, setGrupos] = useState(null)
  const [error, setError] = useState(null)

  async function abrir() {
    setAbierto(true)
    if (grupos) return
    try {
      const r = await fetch(`${API}/api/carreras`)
      if (!r.ok) throw new Error('No pude cargar el catálogo.')
      const { carreras } = await r.json()
      const mapa = new Map()
      for (const c of carreras) {
        if (!mapa.has(c.nombre)) mapa.set(c.nombre, [])
        mapa.get(c.nombre).push(c)
      }
      setGrupos([...mapa.entries()].map(([nombre, sedes]) => ({ nombre, sedes })))
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <>
      <button className="dash-catalogo" onClick={abrir}>📚 Ver catálogo</button>
      {abierto && (
        <Modal titulo="Catálogo de carreras" onClose={() => setAbierto(false)}>
          {error && <p className="loading-text">{error}</p>}
          {!grupos && !error && <p className="loading-text">Cargando…</p>}
          {grupos && (
            <>
              <p className="catalogo-intro">
                {grupos.length} carreras disponibles. Una misma carrera puede ofrecerse en varias sedes.
              </p>
              <ul className="catalogo-lista">
                {grupos.map((g) => (
                  <li key={g.nombre} className="catalogo-item">
                    <span className="catalogo-nombre">{g.nombre}</span>
                    <span className="catalogo-sedes">
                      {g.sedes.map((s) => `${s.universidad} · ${s.centro} (${s.departamento})`).join('  ·  ')}
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </Modal>
      )}
    </>
  )
}

export default function Dashboard({ nombre, carreras, respuestaId, confianza, respuestas, onReiniciar }) {
  const [sel, setSel] = useState(0) // carrera seleccionada en el detalle
  const [inst, setInst] = useState(0) // institución seleccionada
  const [hover, setHover] = useState(null) // sector del pastel sobre el que está el mouse
  const [feedback, setFeedback] = useState(null) // null | true | false
  const [otraIdx, setOtraIdx] = useState(null) // carrera B elegida para comparar
  const [cmpAbierto, setCmpAbierto] = useState(false)
  const [cmpCargando, setCmpCargando] = useState(false)
  const [cmpDatos, setCmpDatos] = useState(null)
  const [cmpError, setCmpError] = useState(null)

  const enviarFeedback = (acertada) => {
    if (!respuestaId) return
    setFeedback(acertada)
    fetch('http://localhost:8000/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ respuesta_id: respuestaId, acertada }),
    }).catch(() => {})
  }

  const elegirCarrera = (i) => {
    setSel(i)
    setInst(0)
    setOtraIdx(null)
    setCmpDatos(null)
  }

  async function comparar() {
    if (otraIdx === null) return
    setCmpAbierto(true)
    setCmpCargando(true)
    setCmpError(null)
    setCmpDatos(null)
    try {
      const a = carreras[sel]
      const b = carreras[otraIdx]
      const d = await postJSON('/api/comparar', {
        carrera_a: a.carrera, descripcion_a: a.descripcion,
        carrera_b: b.carrera, descripcion_b: b.descripcion,
        respuestas: respuestas || {},
        session_id: SESSION_ID,
      })
      setCmpDatos(d)
    } catch (e) {
      setCmpError(e.message)
    } finally {
      setCmpCargando(false)
    }
  }

  const data = carreras.map((c, i) => ({ name: c.carrera, value: c.afinidad, i }))
  const maxAfinidad = Math.max(...carreras.map((c) => c.afinidad))
  const activa = carreras[hover ?? sel] // lo que muestra el centro del pastel
  const seleccionada = carreras[sel]
  const otrasCarreras = carreras.map((_, i) => i).filter((i) => i !== sel)

  return (
    <div className="dash">
      <header className="dash-head">
        <div>
          <h1>Tu orientación vocacional</h1>
          <p>{nombre ? `${nombre}, estas` : 'Estas'} son las carreras más afines a tu perfil.</p>
          <ConfianzaBadge confianza={confianza} />
        </div>
        <div className="dash-acciones">
          <CatalogoCarreras />
          <button
            className="dash-pdf"
            onClick={() => import('./reporte').then((m) => m.generarPDF(nombre, carreras))}
          >
            ↓ Descargar PDF
          </button>
          {onReiniciar && (
            <button className="dash-reiniciar" onClick={onReiniciar}>↺ Hacer otro test</button>
          )}
        </div>
      </header>

      <section className="dash-charts">
        <div className="chart-card">
          <h2>Afinidad por carrera</h2>
          <div className="barras">
            {carreras.map((c, i) => (
              <div key={i} className="barra-row">
                <div className="barra-top">
                  <span className="barra-nombre">
                    <span className="punto" style={{ background: color(i) }} />
                    {c.carrera}
                  </span>
                  <span className="barra-pct">{c.afinidad}%</span>
                </div>
                <div className="barra-track">
                  <div
                    className="barra-fill"
                    style={{ width: `${(c.afinidad / maxAfinidad) * 100}%`, background: color(i) }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="chart-card">
          <h2>Distribución</h2>
          <div className="pie-wrap">
            <ResponsiveContainer width="100%" height={340}>
              <PieChart>
                <Pie
                  data={data}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={98}
                  outerRadius={150}
                  paddingAngle={2}
                  stroke="none"
                  onMouseEnter={(_, i) => setHover(i)}
                  onMouseLeave={() => setHover(null)}
                >
                  {data.map((d) => <Cell key={d.i} fill={color(d.i)} />)}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div className="pie-center">
              <div className="pie-pct" style={{ color: color(hover ?? sel) }}>{activa.afinidad}%</div>
              <div className="pie-name">{activa.carrera}</div>
            </div>
          </div>
        </div>
      </section>

      <section className="dash-detail">
        <div className="carrera-lista">
          {carreras.map((c, i) => (
            <button
              key={i}
              className={`carrera-item ${i === sel ? 'activa' : ''}`}
              onClick={() => elegirCarrera(i)}
              style={i === sel ? { borderColor: color(i) } : undefined}
            >
              <span className="punto" style={{ background: color(i) }} />
              <span className="carrera-nombre">{c.carrera}</span>
              <span className="carrera-pct">{c.afinidad}%</span>
            </button>
          ))}
        </div>

        <div className="carrera-panel">
          <div className="panel-pct" style={{ color: color(sel) }}>{seleccionada.afinidad}% de afinidad</div>
          <h2>{seleccionada.carrera}</h2>
          <p className="panel-desc">{seleccionada.descripcion}</p>

          {seleccionada.razones?.length > 0 && (
            <>
              <h3>Por qué encaja contigo</h3>
              <ul className="razones">
                {seleccionada.razones.map((r, i) => <li key={i}>{r}</li>)}
              </ul>
            </>
          )}

          {seleccionada.factores?.length > 0 && (
            <>
              <h3>Lo que más influyó</h3>
              <div className="factores">
                {seleccionada.factores.map((f, i) => (
                  <div key={i} className="factor-row">
                    <div className="factor-top">
                      <span>{f.nombre}</span>
                      <span>{f.peso}%</span>
                    </div>
                    <div className="factor-track">
                      <div className="factor-fill" style={{ width: `${f.peso}%`, background: color(sel) }} />
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          <h3>¿Dónde estudiarla?</h3>
          <div className="inst-chips">
            {seleccionada.instituciones.map((x, j) => (
              <button
                key={j}
                className={`inst-chip ${j === inst ? 'activa' : ''}`}
                onClick={() => setInst(j)}
              >
                {x.centro}
              </button>
            ))}
          </div>
          <div className="inst-detalle" style={{ borderLeftColor: color(sel) }}>
            <div className="inst-uni" style={{ color: color(sel) }}>{seleccionada.instituciones[inst].universidad}</div>
            <div className="inst-lugar">
              {seleccionada.instituciones[inst].centro} · {seleccionada.instituciones[inst].departamento}
            </div>
            <p>{seleccionada.instituciones[inst].enfoque}</p>
          </div>

          <div className="wow-acciones">
            <SimuladorDia carrera={seleccionada} respuestas={respuestas || {}} />

            {otrasCarreras.length > 0 && (
              <div className="comparador">
                <select
                  className="comparador-select"
                  value={otraIdx ?? ''}
                  onChange={(e) => setOtraIdx(e.target.value === '' ? null : Number(e.target.value))}
                >
                  <option value="">Comparar con…</option>
                  {otrasCarreras.map((i) => (
                    <option key={i} value={i}>{carreras[i].carrera}</option>
                  ))}
                </select>
                <button className="wow-btn" onClick={comparar} disabled={otraIdx === null}>
                  ¿Por qué esta y no esa?
                </button>
              </div>
            )}
          </div>
        </div>
      </section>

      {cmpAbierto && (
        <Modal
          titulo={`${seleccionada.carrera} vs. ${otraIdx !== null ? carreras[otraIdx].carrera : ''}`}
          onClose={() => setCmpAbierto(false)}
        >
          {cmpCargando && <p className="loading-text">Comparando…</p>}
          {cmpError && <p className="loading-text">{cmpError}</p>}
          {cmpDatos && (
            <div className="comparacion">
              <div className="comparacion-comun">
                <h3>En común</h3>
                <ul className="razones">
                  {cmpDatos.en_comun.map((p, i) => <li key={i}>{p}</li>)}
                </ul>
              </div>
              <div className="comparacion-cols">
                <div>
                  <h3 style={{ color: color(sel) }}>{seleccionada.carrera}</h3>
                  <ul className="razones">
                    {cmpDatos.puntos_a.map((p, i) => <li key={i}>{p}</li>)}
                  </ul>
                </div>
                <div>
                  <h3 style={{ color: color(otraIdx) }}>{otraIdx !== null ? carreras[otraIdx].carrera : ''}</h3>
                  <ul className="razones">
                    {cmpDatos.puntos_b.map((p, i) => <li key={i}>{p}</li>)}
                  </ul>
                </div>
              </div>
              <p className="comparacion-final">{cmpDatos.recomendacion}</p>
            </div>
          )}
        </Modal>
      )}

      {respuestaId && (
        <section className="dash-feedback">
          {feedback === null ? (
            <p>¿Esta recomendación te pareció acertada?
              <button className="opt si" onClick={() => enviarFeedback(true)}>Sí</button>
              <button className="opt no" onClick={() => enviarFeedback(false)}>No</button>
            </p>
          ) : (
            <p>¡Gracias por tu respuesta!</p>
          )}
        </section>
      )}
    </div>
  )
}
