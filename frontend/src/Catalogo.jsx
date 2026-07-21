import { useEffect, useMemo, useState } from 'react'
import Nav from './Nav'
import './App.css'

const API = 'http://localhost:8000'

// Birrete: acento visual de cada tarjeta de carrera.
function IconoBirrete() {
  return (
    <svg viewBox="0 0 24 24" width="26" height="26" aria-hidden="true" fill="none">
      <path d="M12 3 L22 8 L12 13 L2 8 Z" fill="currentColor" />
      <path d="M6 10.5 V15 c0 1.5 2.7 3 6 3 s6-1.5 6-3 v-4.5" stroke="currentColor" strokeWidth="1.6" fill="none" strokeLinecap="round" />
      <line x1="22" y1="8" x2="22" y2="13.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  )
}

export default function Catalogo() {
  const [carreras, setCarreras] = useState(null) // null = cargando
  const [filtro, setFiltro] = useState('')
  const [depto, setDepto] = useState('') // '' = todos
  const [uni, setUni] = useState('') // '' = todas

  useEffect(() => {
    fetch(`${API}/api/carreras`)
      .then((r) => r.json())
      .then((d) => setCarreras(d.carreras || []))
      .catch(() => setCarreras([]))
  }, [])

  const deptos = useMemo(
    () => [...new Set((carreras || []).map((c) => c.departamento))].sort(),
    [carreras]
  )
  const unis = useMemo(
    () => [...new Set((carreras || []).map((c) => c.universidad))].sort(),
    [carreras]
  )

  // Agrupa por nombre de carrera: una tarjeta por carrera, con sus sedes.
  const grupos = useMemo(() => {
    if (!carreras) return []
    const map = new Map()
    for (const c of carreras) {
      if (depto && c.departamento !== depto) continue
      if (uni && c.universidad !== uni) continue
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
  }, [carreras, filtro, depto, uni])

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

        <div className="cat-filtros">
          <input
            className="cat-buscar"
            placeholder="Buscar carrera, universidad o departamento…"
            value={filtro}
            onChange={(e) => setFiltro(e.target.value)}
          />
          <select className="cat-select" value={uni} onChange={(e) => setUni(e.target.value)}>
            <option value="">Todas las universidades</option>
            {unis.map((u) => (
              <option key={u} value={u}>{u}</option>
            ))}
          </select>
        </div>

        {deptos.length > 1 && (
          <div className="cat-deptos">
            <button className={depto === '' ? 'sel' : ''} onClick={() => setDepto('')}>
              Todos
            </button>
            {deptos.map((d) => (
              <button key={d} className={depto === d ? 'sel' : ''} onClick={() => setDepto(d)}>
                {d}
              </button>
            ))}
          </div>
        )}

        {carreras === null && <p className="intro">Cargando catálogo…</p>}
        {carreras !== null && grupos.length === 0 && (
          <p className="intro">No se encontró nada con ese texto (¿está encendido el servidor?).</p>
        )}

        <div className="cat-grid">
          {grupos.map(([nombre, sedes]) => (
            <article key={nombre} className="cat-card">
              <span className="cat-icono"><IconoBirrete /></span>
              <h3>{nombre}</h3>
              {(sedes[0].arquetipo || sedes[0].sello) && (
                <p className="cat-arquetipo">{sedes[0].arquetipo || sedes[0].sello}</p>
              )}
              <details className="cat-sedes">
                <summary>
                  <span className="cat-sedes-pill">
                    {sedes.length === 1 ? '1 sede' : `${sedes.length} sedes`}
                    <span className="cat-sedes-chevron" aria-hidden="true">›</span>
                  </span>
                </summary>
                <ul>
                  {sedes.map((s, i) => (
                    <li key={i}>
                      <strong>{s.universidad}</strong>
                      <span className="cat-sede-meta">{s.centro} · {s.departamento}</span>
                    </li>
                  ))}
                </ul>
              </details>
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
