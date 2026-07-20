import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { VIEWBOX, DEPARTAMENTOS_SVG } from './data/guatemalaDeptos'
import { REGIONES } from './data/regiones'
import { color } from './colors'
import './App.css'

// Únicos departamentos con carreras cargadas hoy (ver backend/data/*.json).
// Agregar un depto aquí en cuanto tenga catálogo — no requiere tocar el SVG.
const ACTIVOS = new Set(['Totonicapán', 'Quetzaltenango'])

// Departamento -> región a la que pertenece.
const REGION_DE = new Map(REGIONES.flatMap((r) => r.deptos.map((d) => [d, r])))

export default function Mapa() {
  const navigate = useNavigate()
  const [modo, setModo] = useState('depto') // 'depto' | 'region'

  function irADepto(nombre) {
    navigate(`/chat?depto=${encodeURIComponent(nombre)}`)
  }

  function irARegion(region) {
    navigate(`/chat?depto=${encodeURIComponent(region.deptos.join(','))}`)
  }

  return (
    <div className="mapa-page">
      <h1>¿Dónde te gustaría estudiar?</h1>
      <p>{modo === 'depto' ? 'Toca un departamento para ver sus carreras.' : 'Toca una región para ver sus carreras.'}</p>

      <div className="mapa-modos">
        <button className={modo === 'depto' ? 'sel' : ''} onClick={() => setModo('depto')}>Por departamento</button>
        <button className={modo === 'region' ? 'sel' : ''} onClick={() => setModo('region')}>Por región</button>
      </div>

      <svg className="mapa-svg" viewBox={VIEWBOX}>
        {DEPARTAMENTOS_SVG.map(({ nombre, d }) => {
          if (modo === 'depto') {
            const activo = ACTIVOS.has(nombre)
            return (
              <path
                key={nombre}
                d={d}
                className={`depto ${activo ? 'activo' : 'inactivo'}`}
                onClick={activo ? () => irADepto(nombre) : undefined}
              >
                <title>{activo ? nombre : `${nombre} (próximamente)`}</title>
              </path>
            )
          }

          const region = REGION_DE.get(nombre)
          const activa = region.deptos.some((dep) => ACTIVOS.has(dep))
          const idx = REGIONES.findIndex((r) => r.id === region.id)
          return (
            <path
              key={nombre}
              d={d}
              className={`depto ${activa ? '' : 'inactivo'}`}
              style={activa ? { fill: color(idx) } : undefined}
              onClick={activa ? () => irARegion(region) : undefined}
            >
              <title>
                {`Región ${region.id} - ${region.nombre}`}
                {activa ? '' : ' (próximamente)'}
              </title>
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
