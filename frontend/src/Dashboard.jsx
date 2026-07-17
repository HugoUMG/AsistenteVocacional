import { useState } from 'react'
import { ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { color } from './colors'
import './Dashboard.css'

export default function Dashboard({ nombre, carreras, respuestaId, onReiniciar }) {
  const [sel, setSel] = useState(0) // carrera seleccionada en el detalle
  const [inst, setInst] = useState(0) // institución seleccionada
  const [hover, setHover] = useState(null) // sector del pastel sobre el que está el mouse
  const [feedback, setFeedback] = useState(null) // null | true | false

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
  }

  const data = carreras.map((c, i) => ({ name: c.carrera, value: c.afinidad, i }))
  const maxAfinidad = Math.max(...carreras.map((c) => c.afinidad))
  const activa = carreras[hover ?? sel] // lo que muestra el centro del pastel
  const seleccionada = carreras[sel]

  return (
    <div className="dash">
      <header className="dash-head">
        <div>
          <h1>Tu orientación vocacional</h1>
          <p>{nombre ? `${nombre}, estas` : 'Estas'} son las carreras más afines a tu perfil.</p>
        </div>
        <div className="dash-acciones">
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
        </div>
      </section>

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
