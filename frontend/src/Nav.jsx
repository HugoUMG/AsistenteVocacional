import { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { GoogleLogin } from '@react-oauth/google'
import { cerrarSesion, iniciarSesionGoogle, sesionActual } from './auth'

// Barra superior compartida por las páginas informativas (inicio, acerca,
// catálogo, parámetros). El chat y el dashboard no la usan.
export default function Nav() {
  const navigate = useNavigate()
  const [sesion, setSesion] = useState(sesionActual)
  const [error, setError] = useState('')

  async function alIniciarSesion(credentialResponse) {
    setError('')
    try {
      setSesion(await iniciarSesionGoogle(credentialResponse.credential))
    } catch (e) {
      setError(String(e.message || e))
    }
  }

  function salir() {
    cerrarSesion()
    setSesion(null)
  }

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
        <NavLink to="/psicometrico">Exámenes psicométricos</NavLink>
        {/* /cip sale del menú: mide lo mismo que Holland (intereses) pero sin
            autorización de uso y con baremos españoles de otra época. La ruta
            sigue viva para poder mostrárselo a quien lo pida. Ver docs/holland.md. */}
        <NavLink to="/holland">Test de Holland</NavLink>
        <NavLink to="/parametros">Parámetros</NavLink>
        {sesion && <NavLink to="/historial">Mi historial</NavLink>}
      </nav>
      <div className="nav-cuenta">
        {sesion ? (
          <>
            <span className="nav-nombre">{sesion.estudiante.nombre}</span>
            <button className="nav-salir" onClick={salir}>Cerrar sesión</button>
          </>
        ) : (
          <div className="nav-login">
            <GoogleLogin onSuccess={alIniciarSesion} onError={() => setError('No se pudo iniciar sesión.')} />
          </div>
        )}
        {error && <span className="nav-login-error">{error}</span>}
      </div>
      <button className="nav-cta" onClick={() => navigate('/mapa')}>Empezar el chat</button>
    </header>
  )
}
