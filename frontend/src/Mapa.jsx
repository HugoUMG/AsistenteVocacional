import { useNavigate } from 'react-router-dom'
import Nav from './Nav'
import { DEPARTAMENTOS_SVG } from './data/guatemalaDeptos'
import './App.css'

// Únicos departamentos con carreras cargadas hoy (ver backend/data/*.json).
// Agregar un depto aquí en cuanto tenga catálogo (no requiere tocar el SVG).
// El mapa dibuja SOLO estos: es el alcance real del proyecto hoy, y mostrar el
// país entero en gris invitaba a tocar departamentos que no llevan a ningún
// lado. La vista "por región" se quitó por lo mismo (los dos caen en la misma).
const ACTIVOS = new Set(['Totonicapán', 'Quetzaltenango'])

const EN_MAPA = DEPARTAMENTOS_SVG.filter((d) => ACTIVOS.has(d.nombre))

// Los paths del SVG son solo pares "x,y" absolutos (M y L), así que el recuadro
// y el centro salen de leer los números; no hace falta medir en el DOM.
// ponytail: si algún día los paths traen curvas (C, Q), los puntos de control
// entran al cálculo y el recuadro queda algo más grande. No rompe nada.
const puntos = (d) =>
  [...d.matchAll(/(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)/g)].map(([, x, y]) => [+x, +y])

const promedio = (ns) => ns.reduce((a, b) => a + b, 0) / ns.length

/** Recuadro (viewBox) que encierra los paths dados, con un margen. */
function recuadro(paths, margen = 12) {
  const ps = paths.flatMap(puntos)
  const xs = ps.map((p) => p[0])
  const ys = ps.map((p) => p[1])
  const x0 = Math.min(...xs) - margen
  const y0 = Math.min(...ys) - margen
  return `${x0} ${y0} ${Math.max(...xs) + margen - x0} ${Math.max(...ys) + margen - y0}`
}

/** Centro aproximado de un path, para poner la etiqueta encima. */
const centro = (d) => {
  const ps = puntos(d)
  return [promedio(ps.map((p) => p[0])), promedio(ps.map((p) => p[1]))]
}

const VISTA = recuadro(EN_MAPA.map((d) => d.d))

export default function Mapa() {
  const navigate = useNavigate()

  return (
    <div className="pagina">
      <Nav />
      <div className="mapa-page">
      <span className="pasos-kicker">Explora el mapa</span>
      <h1>¿Dónde te gustaría estudiar?</h1>
      <p>Toca un departamento para ver sus carreras.</p>

      <div className="mapa-panel">
      <svg className="mapa-svg" viewBox={VISTA}>
        {EN_MAPA.map(({ nombre, d }) => (
          <g key={nombre} className="depto-grupo" onClick={() => navigate(`/chat?depto=${encodeURIComponent(nombre)}`)}>
            <path d={d} className="depto activo">
              <title>{nombre}</title>
            </path>
            <text className="depto-nombre" x={centro(d)[0]} y={centro(d)[1]}>{nombre}</text>
          </g>
        ))}
      </svg>
      </div>

      <button className="mapa-ambos-btn" onClick={() => navigate('/chat?depto=Ambos')}>
        Ver todas las carreras (Ambos) →
      </button>
      </div>
    </div>
  )
}
