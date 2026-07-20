import { useEffect, useMemo, useState } from 'react'
import Nav from './Nav'
import './App.css'

const API = 'http://localhost:8000'

export default function Catalogo() {
  const [carreras, setCarreras] = useState(null) // null = cargando
  const [filtro, setFiltro] = useState('')

  useEffect(() => {
    fetch(`${API}/api/carreras`)
      .then((r) => r.json())
      .then((d) => setCarreras(d.carreras || []))
      .catch(() => setCarreras([]))
  }, [])

  // Agrupa por nombre de carrera: una tarjeta por carrera, con sus sedes.
  const grupos = useMemo(() => {
    if (!carreras) return []
    const map = new Map()
    for (const c of carreras) {
      if (!map.has(c.nombre)) map.set(c.nombre, [])
      map.get(c.nombre).push(c)
    }
    const q = filtro.trim().toLowerCase()
    return [...map.entries()]
      .filter(([nombre, sedes]) =>
        !q ||
        nombre.toLowerCase().includes(q) ||
        sedes.some((s) => `${s.universidad} ${s.centro} ${s.departamento}`.toLowerCase().includes(q))
      )
      .sort((a, b) => a[0].localeCompare(b[0]))
  }, [carreras, filtro])

  return (
    <div className="pagina">
      <Nav />
      <main className="contenido">
        <span className="pasos-kicker">Catálogo de carreras</span>
        <h1>Todas las carreras que Orienta conoce</h1>
        <p className="intro">
          Este es el catálogo real con el que trabaja la IA: carreras de
          universidades de Quetzaltenango y Totonicapán, cada una con las sedes
          donde puedes estudiarla.
        </p>

        <input
          className="cat-buscar"
          placeholder="Buscar carrera, universidad o departamento…"
          value={filtro}
          onChange={(e) => setFiltro(e.target.value)}
        />

        {carreras === null && <p className="intro">Cargando catálogo…</p>}
        {carreras !== null && grupos.length === 0 && (
          <p className="intro">No se encontró nada con ese texto (¿está encendido el servidor?).</p>
        )}

        <div className="cat-grid">
          {grupos.map(([nombre, sedes]) => (
            <article key={nombre} className="cat-card">
              <h3>{nombre}</h3>
              <ul>
                {sedes.map((s, i) => (
                  <li key={i}>
                    <strong>{s.universidad}</strong> · {s.centro} · {s.departamento}
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>

        {carreras !== null && carreras.length > 0 && (
          <p className="cat-total">
            {grupos.length} carreras{filtro ? ' encontradas' : ''} · {carreras.length} programas por sede
          </p>
        )}
      </main>
    </div>
  )
}
