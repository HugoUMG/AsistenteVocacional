// Login con Google: guarda el JWT propio (emitido por POST /api/auth/google,
// ver backend/app/auth.py) en localStorage para que sobreviva a cerrar la
// pestaña. Iniciar sesión es OBLIGATORIO para evaluarse: sostiene el
// enfriamiento entre evaluaciones y el tope de uso (ver backend/app/cuota.py).
import { olvidarPerfilHolland, sincronizarPerfilHolland } from './holland-perfil'

const API = 'http://localhost:8000'
const CLAVE = 'auth'

export function guardarSesion(token, estudiante) {
  localStorage.setItem(CLAVE, JSON.stringify({ token, estudiante }))
}

export function sesionActual() {
  try {
    const s = JSON.parse(localStorage.getItem(CLAVE) || 'null')
    return s?.token && s?.estudiante?.id ? s : null
  } catch {
    return null
  }
}

export function cerrarSesion() {
  localStorage.removeItem(CLAVE)
  // El perfil de Holland es de la CUENTA, no de la máquina: si no se borra, el
  // siguiente alumno que entre en esta computadora hereda el perfil del anterior.
  olvidarPerfilHolland()
}

// Header listo para spread en fetch: {} si no hay sesión (nunca manda un
// Authorization vacío o viejo).
export function authHeader() {
  const s = sesionActual()
  return s ? { Authorization: `Bearer ${s.token}` } : {}
}

// Cambia el ID token de Google por el JWT propio, deja la sesión guardada y
// trae de la cuenta el perfil de Holland (si ya hizo el test antes). Devuelve
// la sesión nueva. La usan el Nav y la pantalla de bloqueo.
export async function iniciarSesionGoogle(credential) {
  const r = await fetch(`${API}/api/auth/google`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ credential }),
  })
  if (!r.ok) throw new Error('No se pudo iniciar sesión.')
  const { token, estudiante } = await r.json()
  guardarSesion(token, estudiante)
  await sincronizarPerfilHolland(token)
  return { token, estudiante }
}
