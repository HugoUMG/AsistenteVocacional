// El perfil del test corto de personalidad/valores/estilo cognitivo que el
// chat arrastra cuando el alumno lo hizo antes (modo opcional, igual que
// Holland: ver frontend/src/holland-perfil.js).
const CLAVE = 'personalidad-perfil'

export function guardarPerfilPersonalidad(puntajes) {
  const aLista = (obj) =>
    Object.entries(obj).map(([clave, puntaje]) => ({ clave, puntaje }))
  localStorage.setItem(
    CLAVE,
    JSON.stringify({
      personalidad: aLista(puntajes.personalidad),
      valores: aLista(puntajes.valores),
      estilo_cognitivo: aLista(puntajes.estilo_cognitivo),
      estilo_dominante: puntajes.estilo_dominante,
      fecha: new Date().toISOString(),
    })
  )
}

export function leerPerfilPersonalidad() {
  try {
    const p = JSON.parse(localStorage.getItem(CLAVE) || 'null')
    // Un localStorage viejo o a medias no puede tumbar el chat: si no tiene la
    // forma que el backend espera, se ignora y el chat corre en modo normal.
    return p?.personalidad?.length === 6 &&
      p?.valores?.length === 4 &&
      p?.estilo_cognitivo?.length === 4
      ? p
      : null
  } catch {
    return null
  }
}

export function olvidarPerfilPersonalidad() {
  localStorage.removeItem(CLAVE)
}
