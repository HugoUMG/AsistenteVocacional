// El perfil de Holland que el chat arrastra cuando el alumno hizo el test antes
// (modo 3, ver docs/holland.md). Vive en localStorage para que sobreviva a
// recargar la página o a abrir el chat en otra pestaña.
//
// Se guardan SOLO los campos que el backend valida y mete al prompt: el código,
// los 6 puntajes con su nombre de área y los títulos de las ocupaciones. Las
// descripciones largas y la hoja cruda no viajan.
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
    const r = await fetch('http://localhost:8000/api/holland/mio', {
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
