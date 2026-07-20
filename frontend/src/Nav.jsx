import { NavLink, useNavigate } from 'react-router-dom'

// Barra superior compartida por las páginas informativas (inicio, acerca,
// catálogo, parámetros). El chat y el dashboard no la usan.
export default function Nav() {
  const navigate = useNavigate()
  return (
    <header className="nav">
      <NavLink to="/" className="nav-logo">
        <svg viewBox="0 0 100 100" width="26" height="26" aria-hidden="true">
          <line x1="50" y1="14" x2="50" y2="26" stroke="currentColor" strokeWidth="6" />
          <circle cx="50" cy="11" r="7" fill="currentColor" />
          <rect x="22" y="26" width="56" height="48" rx="14" fill="currentColor" />
          <circle cx="38" cy="48" r="6" fill="#fff" />
          <circle cx="62" cy="48" r="6" fill="#fff" />
          <rect x="40" y="62" width="20" height="4" rx="2" fill="#fff" opacity="0.8" />
        </svg>
        Orienta
      </NavLink>
      <nav className="nav-links">
        <NavLink to="/acerca">Acerca de</NavLink>
        <NavLink to="/catalogo">Catálogo de carreras</NavLink>
        <NavLink to="/parametros">Parámetros</NavLink>
      </nav>
      <button className="nav-cta" onClick={() => navigate('/mapa')}>Empezar el chat</button>
    </header>
  )
}
