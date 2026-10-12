import { API } from './api'
// El perfil de Holland que el chat arrastra cuando el alumno hizo el test antes
// (modo 3, ver docs/holland.md). Vive en localStorage para que sobreviva a
// recargar la página o a abrir el chat en otra pestaña.
//
// Se guardan los campos que el backend valida y mete al prompt (el código, los
// 6 puntajes con su nombre de área y los títulos de las ocupaciones) más la
// descripción de cada área, que NO entra al prompt (el backend la ignora):
// la usan el dashboard y el PDF del chat para explicar las áreas altas.
const CLAVE = 'holland-perfil'
const OCUPACIONES = 8

export function guardarPerfilHolland(resultado) {
  localStorage.setItem(
    CLAVE,
    JSON.stringify({
      codigo: resultado.codigo,
      areas: resultado.areas.map((a) => ({
        letra: a.letra,
        title: a.title,
        score: a.score,
        description: a.description || '',
      })),
      ocupaciones: resultado.carreras.slice(0, OCUPACIONES).map((c) => c.title),
      fecha: new Date().toISOString(),
    })
  )
}

export function leerPerfilHolland() {
  try {
    const p = JSON.parse(localStorage.getItem(CLAVE) || 'null')
    // Un localStorage viejo o a medias no puede tumbar el chat: si no tiene la
    // forma que el backend espera, se ignora y el chat corre en modo normal.
    return p?.codigo && p.areas?.length === 6 ? p : null
  } catch {
    return null
  }
}

export const MAX_AREA = 40
export const NOMBRE_AREA = { R: 'Realista', I: 'Investigador', A: 'Artístico',
  S: 'Social', E: 'Emprendedor', C: 'Convencional' }

// El dashboard y el PDF reciben el perfil en dos formas: la lista del chat
// ({letra, title, score, description}) o el diccionario {R: 30, ...} del
// registro del admin. Devuelve siempre {codigo, areas: [...]} ordenado de
// mayor a menor, o null si no hay perfil.
export function normalizarHolland(h) {
  if (!h?.codigo || !h.areas) return null
  const areas = Array.isArray(h.areas)
    ? h.areas
    : Object.entries(h.areas).map(([letra, score]) => ({ letra, title: NOMBRE_AREA[letra], score }))
  return { codigo: h.codigo, areas: [...areas].sort((a, b) => b.score - a.score) }
}

export function olvidarPerfilHolland() {
  localStorage.removeItem(CLAVE)
}

// Trae de la CUENTA el último perfil de Holland guardado y lo deja en
// localStorage (o lo borra si esa cuenta no tiene ninguno). Se llama al iniciar
// sesión: sin esto, dos alumnos que usan la misma computadora se pasan el
// perfil entre sí. El token va por parámetro para no importar auth.js desde
// aquí (auth.js ya importa este archivo).
export async function sincronizarPerfilHolland(token) {
  try {
    const r = await fetch(`${API}/api/holland/mio`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!r.ok) return
    const perfil = await r.json()
    if (perfil?.codigo) localStorage.setItem(CLAVE, JSON.stringify(perfil))
    else olvidarPerfilHolland()
  } catch {
    // Sin red se deja lo que haya: el chat corre igual sin perfil de Holland.
  }
}
