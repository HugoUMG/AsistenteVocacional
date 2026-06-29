import { useState } from 'react'
import {
  ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Cell, Tooltip,
  PieChart, Pie,
} from 'recharts'
import './Dashboard.css'

const COLORS = ['#6c5ce7', '#00cec9', '#fd79a8', '#fdcb6e', '#0984e3', '#e17055', '#00b894', '#a29bfe']
const color = (i) => COLORS[i % COLORS.length]

export default function Dashboard({ nombre, carreras, onReiniciar }) {
  const [sel, setSel] = useState(0) // carrera seleccionada en el detalle
  const [inst, setInst] = useState(0) // institución seleccionada
  const [hover, setHover] = useState(null) // sector del pastel sobre el que está el mouse

  const elegirCarrera = (i) => {
    setSel(i)
    setInst(0)
  }

  const data = carreras.map((c, i) => ({ name: c.carrera, value: c.afinidad, i }))
  const activa = carreras[hover ?? sel] // lo que muestra el centro del pastel
  const seleccionada = carreras[sel]

  return (
    <div className="dash">
      <header className="dash-head">
        <div>
          <h1>Tu orientación vocacional</h1>
          <p>{nombre ? `${nombre}, estas` : 'Estas'} son las carreras más afines a tu perfil.</p>
        </div>
        {onReiniciar && (
          <button className="dash-reiniciar" onClick={onReiniciar}>↺ Hacer otro test</button>
        )}
      </header>

      <section className="dash-charts">
        <div className="chart-card">
          <h2>Afinidad por carrera</h2>
          <ResponsiveContainer width="100%" height={Math.max(180, carreras.length * 46)}>
            <BarChart data={data} layout="vertical" margin={{ left: 8, right: 30, top: 4, bottom: 4 }}>
              <XAxis type="number" domain={[0, 'dataMax']} hide />
              <YAxis
                type="category"
                dataKey="name"
                width={175}
                tick={{ fontSize: 11, fill: '#2b2740' }}
                tickFormatter={(t) => (t.length > 28 ? t.slice(0, 26) + '…' : t)}
              />
              <Tooltip formatter={(v) => [`${v}%`, 'Afinidad']} cursor={{ fill: 'rgba(108,92,231,0.06)' }} />
              <Bar dataKey="value" radius={[0, 6, 6, 0]} label={{ position: 'right', formatter: (v) => `${v}%`, fontSize: 11 }}>
                {data.map((d) => <Cell key={d.i} fill={color(d.i)} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h2>Distribución</h2>
          <div className="pie-wrap">
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={data}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={74}
                  outerRadius={108}
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
          <div className="inst-detalle">
            <div className="inst-uni">{seleccionada.instituciones[inst].universidad}</div>
            <p>{seleccionada.instituciones[inst].enfoque}</p>
          </div>
        </div>
      </section>
    </div>
  )
}
