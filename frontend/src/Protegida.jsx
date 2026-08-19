import { useState } from 'react'
import { GoogleLogin } from '@react-oauth/google'
import Nav from './Nav'
import { iniciarSesionGoogle, sesionActual } from './auth'
import './App.css'

// Envuelve las rutas donde el alumno se evalúa. El login es obligatorio para
// evaluarse: sostiene el enfriamiento entre evaluaciones y el tope de uso
// diario (ver backend/app/cuota.py). El backend lo exige por su lado con
// 401; esto solo evita que el alumno llene un test para descubrirlo al final.
export default function Protegida({ children }) {
  const [sesion, setSesion] = useState(sesionActual)
  const [error, setError] = useState('')

  if (sesion) return children

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
      </main>
    </div>
  )
}
