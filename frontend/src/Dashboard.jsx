import { useEffect, useId, useState } from 'react'
import { ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { color } from './colors'
import Icono from './Iconos'
import { sessionId } from './session'
import GuardarResultados from './GuardarResultados'
import { authHeader } from './auth'
import { MAX_AREA, normalizarHolland } from './holland-perfil'
import './Dashboard.css'
import { API } from './api'

const postJSON = (ruta, body) =>
  fetch(`${API}${ruta}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify(body),
  }).then(async (r) => {
    if (!r.ok) {
      // El 429 (tope de uso) trae su propio mensaje: se muestra tal cual.
      const d = await r.json().catch(() => null)
      throw new Error(typeof d?.detail === 'string' ? d.detail : 'No se pudo generar. Inténtalo de nuevo.')
    }
    return r.json()
  })

// Para quien va en básicos: el siguiente paso no es la universidad, es el
// diversificado. Lo calcula el backend sin IA (app/diversificado.py) y llega
// vacío para todos los demás niveles, así que aquí no se pinta nada.
function Diversificados({ opciones }) {
  if (!opciones?.length) return null
  return (
    <div className="dash-diversificados">
      <p className="dash-div-titulo">Antes de la universidad: qué diversificado te conviene llevar</p>
      <ul>
        {opciones.map((o) => (
          <li key={o.nombre}>
            <strong>{o.nombre}</strong> <span>{o.porque}</span>
            {/* El departamento, no el colegio: la app orienta, no recomienda
                establecimientos. */}
            {!!o.departamentos?.length && (
              <span className="dash-div-donde">Se ofrece en: {o.departamentos.join(' y ')}</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}

// Los puntajes del test de Holland, si el alumno lo hizo antes del chat. Va en
// el dashboard y en el PDF porque el informe también es la toma de datos que
// revisa la psicóloga: sin esto, el perfil medido quedaba solo en /holland.
// No mueve la recomendación (medido, ver experiments/holland-estructura.md): se muestra, nada más.
function PerfilHolland({ holland }) {
  if (!holland) return null
  const altas = holland.areas.slice(0, 3).filter((a) => a.description)
  return (
    <section className="chart-card dash-holland">
      <h2><Icono nombre="diana" tam={16} /> Tu perfil de intereses (Holland) · código {holland.codigo}</h2>
      <div className="barras">
        {holland.areas.map((a, i) => (
          <div key={a.letra} className="barra-row">
            <div className="barra-top">
              <span className="barra-nombre">
                <span className="punto" style={{ background: color(i) }} />
                {a.letra}. {a.title}
              </span>
              <span className="barra-pct">{a.score} / {MAX_AREA}</span>
            </div>
            <div className="barra-track">
              <div className="barra-fill" style={{ width: `${(a.score / MAX_AREA) * 100}%`, background: color(i) }} />
            </div>
          </div>
        ))}
      </div>
      {altas.length > 0 && (
        <div className="dash-holland-altas">
          <h3>Qué significan tus áreas altas</h3>
          {altas.map((a) => (
            <p key={a.letra}><strong>{a.title}.</strong> {a.description}</p>
          ))}
        </div>
      )}
    </section>
  )
}

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

// Modal genérico: overlay + panel. Cierra con la X, con Escape o tocando fuera.
function Modal({ icono, kicker, titulo, ancho, onClose, children }) {
  const idTitulo = useId()
  useEffect(() => {
    const alPulsar = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', alPulsar)
    return () => window.removeEventListener('keydown', alPulsar)
  }, [onClose])

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className={`modal-panel ${ancho ? 'modal-ancho' : ''}`}
        role="dialog" aria-modal="true" aria-labelledby={idTitulo}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-head">
          {icono && <span className="modal-icono"><Icono nombre={icono} tam={22} /></span>}
          <div className="modal-titulos">
            {kicker && <span className="modal-kicker">{kicker}</span>}
            <h2 id={idTitulo}>{titulo}</h2>
          </div>
          <button className="modal-cerrar" onClick={onClose} aria-label="Cerrar">
            <Icono nombre="cerrar" tam={16} />
          </button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  )
}

// Mientras responde Gemini se adelanta la forma del resultado, no un texto
// suelto: así se nota que algo viene en camino.
function Esqueleto({ texto, filas = 5 }) {
  return (
    <div className="esqueleto" aria-busy="true">
      <p className="esqueleto-txt">{texto}</p>
      {Array.from({ length: filas }, (_, i) => (
        <div key={i} className="esqueleto-fila">
          <span className="esq esq-icono" />
          <span className="esq esq-linea" style={{ width: `${88 - (i % 3) * 14}%` }} />
        </div>
      ))}
    </div>
  )
}

function ErrorExtra({ mensaje, onReintentar }) {
  return (
    <div className="extra-error" role="alert">
      <Icono nombre="alerta" tam={30} grosor={1.8} />
      <p>{mensaje}</p>
      <button className="extra-reintentar" onClick={onReintentar}>
        <Icono nombre="reintentar" tam={15} /> Reintentar
      </button>
    </div>
  )
}

// Icono del momento del día según la hora del evento ("07:30").
function iconoHora(hora) {
  const h = parseInt(hora, 10)
  if (Number.isNaN(h)) return 'reloj'
  if (h >= 5 && h < 11) return 'manana'
  if (h >= 11 && h < 15) return 'mediodia'
  if (h >= 15 && h < 19) return 'tarde'
  return 'noche'
}

// Tarjeta "Un día en esta carrera": genera y muestra una jornada típica.
function SimuladorDia({ carrera, respuestas }) {
  const [abierto, setAbierto] = useState(false)
  const [cargando, setCargando] = useState(false)
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState(null)

  function abrir() {
    setAbierto(true)
    if (!datos && !cargando) cargar()
  }

  async function cargar() {
    setCargando(true)
    setError(null)
    try {
      const d = await postJSON('/api/simular-dia', {
        carrera: carrera.carrera,
        descripcion: carrera.descripcion,
        respuestas,
        session_id: sessionId(),
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
      <button className="explora-card" onClick={abrir}>
        <span className="explora-icono"><Icono nombre="reloj" tam={22} /></span>
        <span className="explora-txt">
          <strong>Un día en esta carrera</strong>
          <span>Una jornada típica, con lo que entusiasma y lo que exige.</span>
        </span>
        <span className="explora-ir"><Icono nombre="flecha" tam={18} /></span>
      </button>
      {abierto && (
        <Modal icono="reloj" kicker="Un día como" titulo={carrera.carrera} onClose={() => setAbierto(false)}>
          {cargando && <Esqueleto texto="Imaginando tu día…" />}
          {error && <ErrorExtra mensaje={error} onReintentar={cargar} />}
          {datos && (
            <>
              <ol className="timeline">
                {datos.eventos.map((ev, i) => (
                  <li key={i} className="timeline-item" style={{ '--i': i }}>
                    <span className="timeline-icono"><Icono nombre={iconoHora(ev.hora)} tam={18} /></span>
                    <div className="timeline-cuerpo">
                      <span className="timeline-hora">{ev.hora}</span>
                      <p className="timeline-actividad">{ev.actividad}</p>
                    </div>
                  </li>
                ))}
              </ol>
              <div className="extra-cierre">
                <Icono nombre="foco" tam={20} />
                <p>{datos.cierre}</p>
              </div>
            </>
          )}
        </Modal>
      )}
    </>
  )
}

// Botón "Ver catálogo": lista todas las carreras del catálogo, agrupadas por
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
      <button className="dash-catalogo" onClick={abrir}><Icono nombre="libro" tam={16} /> Ver catálogo</button>
      {abierto && (
        <Modal icono="libro" kicker="Todo lo disponible" titulo="Catálogo de carreras" onClose={() => setAbierto(false)}>
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
                    <span className="catalogo-sede-count">
                      {g.sedes.length} {g.sedes.length === 1 ? 'sede' : 'sedes'}
                    </span>
                    <ul className="catalogo-sedes">
                      {g.sedes.map((s, i) => (
                        <li key={i} className="catalogo-sede">
                          <span className="catalogo-sede-uni">{s.universidad}</span>
                          <span className="catalogo-sede-detalle">{s.centro} · {s.departamento}</span>
                        </li>
                      ))}
                    </ul>
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

export default function Dashboard({
  nombre, carreras, confianza, respuestas, diversificados, holland, onReiniciar,
  textoReiniciar = 'Hacer otro test', iconoReiniciar = 'reintentar',
}) {
  const perfilHolland = normalizarHolland(holland)
  const [sel, setSel] = useState(0) // carrera seleccionada en el detalle
  const [inst, setInst] = useState(0) // institución seleccionada
  const [hover, setHover] = useState(null) // sector del pastel sobre el que está el mouse
  const [otraIdx, setOtraIdx] = useState(null) // carrera B elegida para comparar
  const [cmpAbierto, setCmpAbierto] = useState(false)
  const [cmpCargando, setCmpCargando] = useState(false)
  const [cmpDatos, setCmpDatos] = useState(null)
  const [cmpError, setCmpError] = useState(null)

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
        session_id: sessionId(),
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
  const sede = seleccionada.instituciones[inst]
  // Una sede puede dar dos programas de la misma carrera (licenciatura y
  // tecnico). Ahi el chip nombra el programa: si no, se ven dos botones iguales.
  // Las recomendaciones guardadas antes de este cambio no traen 'programa' y se
  // ven como antes.
  const centros = seleccionada.instituciones.map((x) => x.centro)
  const repetida = (c) => centros.indexOf(c) !== centros.lastIndexOf(c)
  const programaDistinto = sede.programa && sede.programa !== seleccionada.carrera
  const otrasCarreras = carreras.map((_, i) => i).filter((i) => i !== sel)
  const otra = otraIdx !== null ? carreras[otraIdx] : null

  return (
    <div className="dash">
      <header className="dash-head">
        <div>
          <span className="dash-kicker">Tu resultado</span>
          <h1>Tu orientación vocacional</h1>
          <p>{nombre ? `${nombre}, estas` : 'Estas'} son las carreras más afines a tu perfil.</p>
          <ConfianzaBadge confianza={confianza} />
        </div>
        <div className="dash-acciones">
          <CatalogoCarreras />
          <button
            className="dash-pdf"
            onClick={() => import('./reporte').then((m) => m.generarPDF(nombre, carreras, perfilHolland))}
          >
            <Icono nombre="descargar" tam={16} /> Descargar PDF
          </button>
          {onReiniciar && (
            <button className="dash-reiniciar" onClick={onReiniciar}>
              <Icono nombre={iconoReiniciar} tam={16} /> {textoReiniciar}
            </button>
          )}
        </div>
      </header>

      <Diversificados opciones={diversificados} />

      <GuardarResultados />

      <section className="dash-charts">
        <div className="chart-card">
          <h2><Icono nombre="barras" tam={16} /> Afinidad por carrera</h2>
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
          <h2><Icono nombre="dona" tam={16} /> Distribución</h2>
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

      <PerfilHolland holland={perfilHolland} />

      <section className="dash-detail">
        <div className="carrera-lista">
          {carreras.map((c, i) => {
            const enUMG = c.instituciones?.some((x) => x.universidad === 'Universidad Mariano Gálvez')
            return (
              <button
                key={i}
                className={`carrera-item ${i === sel ? 'activa' : ''} ${enUMG ? 'carrera-item-umg' : ''}`}
                onClick={() => elegirCarrera(i)}
                style={i === sel ? { borderColor: color(i) } : undefined}
              >
                <span className="punto" style={{ background: color(i) }} />
                <span className="carrera-nombre">{c.carrera}</span>
                {enUMG && <span className="sello-umg">UMG</span>}
                <span className="carrera-pct">{c.afinidad}%</span>
              </button>
            )
          })}
        </div>

        <div className="carrera-panel">
          <div className="panel-pct" style={{ color: color(sel) }}>{seleccionada.afinidad}% de afinidad</div>
          <h2>{seleccionada.carrera}</h2>
          <p className="panel-desc">{seleccionada.descripcion}</p>

          {seleccionada.razones?.length > 0 && (
            <>
              <h3><Icono nombre="check" tam={15} /> Por qué encaja contigo</h3>
              <ul className="razones">
                {seleccionada.razones.map((r, i) => <li key={i}>{r}</li>)}
              </ul>
            </>
          )}

          {seleccionada.factores?.length > 0 && (
            <>
              <h3><Icono nombre="ajustes" tam={15} /> Lo que más influyó</h3>
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

          <h3><Icono nombre="birrete" tam={15} /> ¿Dónde estudiarla?</h3>
          <div className="inst-chips">
            {seleccionada.instituciones.map((x, j) => (
              <button
                key={j}
                className={`inst-chip ${j === inst ? 'activa' : ''}`}
                onClick={() => setInst(j)}
              >
                {x.centro}{repetida(x.centro) && x.programa ? ` · ${x.programa}` : ''}
              </button>
            ))}
          </div>
          <div className="inst-detalle" style={{ borderLeftColor: color(sel) }}>
            <div className="inst-uni" style={{ color: color(sel) }}>{sede.universidad}</div>
            <div className="inst-lugar">
              <Icono nombre="pin" tam={13} />
              {programaDistinto && `${sede.programa} · `}{sede.centro} · {sede.departamento}
            </div>
            <p>{sede.enfoque}</p>
          </div>

          <div className="explora">
            <h3><Icono nombre="brujula" tam={15} /> Explora esta carrera</h3>
            <div className="explora-grid">
              {/* key: al cambiar de carrera el simulador arranca de cero; sin
                  ella mostraba el día de la carrera que se abrió primero. */}
              <SimuladorDia key={sel} carrera={seleccionada} respuestas={respuestas || {}} />

              {otrasCarreras.length > 0 && (
                <div className="explora-card explora-comparar">
                  <span className="explora-icono"><Icono nombre="balanza" tam={22} /></span>
                  <div className="explora-txt">
                    <strong>¿Por qué esta y no otra?</strong>
                    <span>Compárala con otra carrera de tu resultado.</span>
                    <div className="comparador">
                      <select
                        className="comparador-select"
                        aria-label="Carrera para comparar"
                        value={otraIdx ?? ''}
                        onChange={(e) => setOtraIdx(e.target.value === '' ? null : Number(e.target.value))}
                      >
                        <option value="">Elige una carrera…</option>
                        {otrasCarreras.map((i) => (
                          <option key={i} value={i}>{carreras[i].carrera}</option>
                        ))}
                      </select>
                      <button className="comparador-btn" onClick={comparar} disabled={otraIdx === null}>
                        Comparar <Icono nombre="flecha" tam={15} />
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {cmpAbierto && (
        <Modal
          icono="balanza"
          kicker="Comparación"
          titulo={<>{seleccionada.carrera} <span className="vs">vs</span> {otra?.carrera}</>}
          ancho
          onClose={() => setCmpAbierto(false)}
        >
          {cmpCargando && <Esqueleto texto="Comparando las dos carreras…" filas={4} />}
          {cmpError && <ErrorExtra mensaje={cmpError} onReintentar={comparar} />}
          {cmpDatos && (
            <div className="comparacion">
              <div className="cmp-comun">
                <h3><Icono nombre="comun" tam={16} /> En común</h3>
                <ul>
                  {cmpDatos.en_comun.map((p, i) => <li key={i}>{p}</li>)}
                </ul>
              </div>
              <div className="cmp-cols">
                {[[seleccionada, sel, cmpDatos.puntos_a], [otra, otraIdx, cmpDatos.puntos_b]].map(([c, idx, puntos]) => (
                  <div key={idx} className="cmp-col" style={{ '--c': color(idx) }}>
                    <h3><span className="punto" /> {c?.carrera}</h3>
                    <ul>
                      {puntos.map((p, i) => <li key={i}>{p}</li>)}
                    </ul>
                  </div>
                ))}
              </div>
              <div className="extra-cierre">
                <Icono nombre="brujula" tam={20} />
                <div>
                  <strong>Para decidir</strong>
                  <p>{cmpDatos.recomendacion}</p>
                </div>
              </div>
            </div>
          )}
        </Modal>
      )}

    </div>
  )
}
