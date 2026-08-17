// Login opcional con Google: guarda el JWT propio (emitido por
// POST /api/auth/google, ver backend/app/auth.py) en localStorage para que
// sobreviva a cerrar la pestaña. Sin sesión, la app funciona igual que
// siempre (anónima) — ver docs/historial.md.
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
}

// Header listo para spread en fetch: {} si no hay sesión (nunca manda un
// Authorization vacío o viejo).
export function authHeader() {
  const s = sesionActual()
  return s ? { Authorization: `Bearer ${s.token}` } : {}
}
