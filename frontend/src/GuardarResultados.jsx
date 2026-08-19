import { useState } from 'react'
import { GoogleLogin } from '@react-oauth/google'
import { sessionId } from './session'
import { iniciarSesionGoogle, sesionActual } from './auth'

const API = 'http://localhost:8000'

// Banner "¿quieres guardar tus resultados?" para la pantalla final de cada
// instrumento (Dashboard, Holland/Personalidad/Psicometrico Resultados). Si
// el alumno ya iba logueado, el resultado se guardó solo (estudiante_id en
// la fila) y este banner no tiene nada que hacer. Si no, loguearse AHORA
// reclama justo el resultado que se acaba de generar (por session_id) — ver
// docs/historial.md.
export default function GuardarResultados() {
  const [estado, setEstado] = useState(sesionActual() ? 'ya-logueado' : 'inicial')
  const [error, setError] = useState('')

  if (estado === 'ya-logueado') return null

  async function alIniciarSesion(credentialResponse) {
    setError('')
    try {
      const { token } = await iniciarSesionGoogle(credentialResponse.credential)

      const r2 = await fetch(`${API}/api/historial/reclamar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ session_id: sessionId() }),
      })
      if (!r2.ok) throw new Error('Se guardó tu cuenta, pero no se pudo vincular este resultado.')
      setEstado('guardado')
    } catch (e) {
      setError(String(e.message || e))
    }
  }

  if (estado === 'guardado') {
    return <p className="psi-guardado">Resultados guardados en tu cuenta ✓</p>
  }

  return (
    <div className="psi-guardar-bloque">
      <p className="psi-texto">
        ¿Quieres guardar tus resultados? Inicia sesión con Google para
        verlos después en tu historial.
      </p>
      <GoogleLogin onSuccess={alIniciarSesion} onError={() => setError('No se pudo iniciar sesión.')} />
      {error && <p className="psi-error">{error}</p>}
    </div>
  )
}
