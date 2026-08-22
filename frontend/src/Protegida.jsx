import { useState } from 'react'
import { GoogleLogin } from '@react-oauth/google'
import Nav from './Nav'
import { iniciarSesionGoogle, sesionActual } from './auth'
import './App.css'

// Envuelve las rutas donde el alumno se evalúa. El login es obligatorio para
// evaluarse: sostiene el enfriamiento entre evaluaciones y el tope de uso
// diario (ver backend/app/cuota.py). El backend lo exige por su lado con
// 401; esto solo evita que el alumno llene un test para descubrirlo al final.
//
// En desarrollo (npm run dev) se puede pasar sin sesión, para no tener que
// loguearse cada vez que se prueba un detalle del chat. El backend tiene que
// estar de acuerdo: LOGIN_OPCIONAL=1 en backend/.env, si no responde 401. El
// build de producción nunca entra por acá (import.meta.env.DEV es false).
export default function Protegida({ children }) {
  const [sesion, setSesion] = useState(sesionActual)
  const [error, setError] = useState('')
  // sessionStorage y no useState: si no, cada recarga vuelve a pedir el clic.
  // Muere al cerrar la pestaña, que para una llave de desarrollo alcanza.
  const [sinLogin, setSinLogin] = useState(
    () => import.meta.env.DEV && sessionStorage.getItem('dev-sin-login') === '1'
  )

  if (sesion || sinLogin) return children

  async function entrar(respuesta) {
    setError('')
    try {
      setSesion(await iniciarSesionGoogle(respuesta.credential))
    } catch (e) {
      setError(String(e.message || e))
    }
  }

  return (
    <div className="pagina">
      <Nav />
      <main className="contenido contenido-angosto">
        <span className="pasos-kicker">Acceso</span>
        <h1>Iniciá sesión para empezar</h1>
        <p className="intro">
          Necesitás entrar con tu cuenta de Google para hacer las evaluaciones.
          Así guardamos tus resultados en tu historial y podés volver a verlos
          cuando quieras.
        </p>
        <div className="nav-login">
          <GoogleLogin onSuccess={entrar} onError={() => setError('No se pudo iniciar sesión.')} />
        </div>
        {error && <p className="nav-login-error">{error}</p>}
        {import.meta.env.DEV && (
          <p className="intro">
            <button className="psi-btn-sec" onClick={() => { sessionStorage.setItem('dev-sin-login', '1'); setSinLogin(true) }}>
              Entrar sin sesión (solo local)
            </button>
          </p>
        )}
      </main>
    </div>
  )
}
