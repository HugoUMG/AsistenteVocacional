import { useNavigate } from 'react-router-dom'
import { VIEWBOX, DEPARTAMENTOS_SVG } from './data/guatemalaDeptos'
import './App.css'

// Únicos departamentos con carreras cargadas hoy (ver backend/data/*.json).
// Agregar un depto aquí en cuanto tenga catálogo — no requiere tocar el SVG.
const ACTIVOS = new Set(['Totonicapán', 'Quetzaltenango'])

export default function Mapa() {
  const navigate = useNavigate()

  return (
    <div className="mapa-page">
      <h1>¿Dónde te gustaría estudiar?</h1>
      <p>Toca un departamento para ver sus carreras.</p>

      <svg className="mapa-svg" viewBox={VIEWBOX}>
        {DEPARTAMENTOS_SVG.map(({ nombre, d }) => {
          const activo = ACTIVOS.has(nombre)
          return (
            <path
              key={nombre}
              d={d}
              className={`depto ${activo ? 'activo' : 'inactivo'}`}
              onClick={activo ? () => navigate(`/chat?depto=${encodeURIComponent(nombre)}`) : undefined}
            >
              <title>{activo ? nombre : `${nombre} (próximamente)`}</title>
            </path>
          )
        })}
      </svg>

      <button className="mapa-ambos-btn" onClick={() => navigate('/chat?depto=Ambos')}>
        Ver todas las carreras (Ambos) →
      </button>
    </div>
  )
}
