// Un id de sesión por RECORRIDO del alumno (test de Holland + chat + dashboard),
// no por carga de página. Se envía en cada llamada de IA para atribuir el
// consumo de tokens, y es lo que permite cruzar en la base el resultado de
// Holland (`resultados_holland`) con la conversación y la recomendación de esa
// misma persona.
//
// Vive en sessionStorage: sobrevive a recargar la página y muere al cerrar la
// pestaña. Antes era `crypto.randomUUID()` por carga de página, y eso tenía dos
// fallas opuestas: recargar a media prueba partía los datos en dos sesiones que
// ya no se podían cruzar, y en cambio "Hacer otro test" —que navega sin
// recargar— reusaba la misma sesión para dos pruebas distintas. Empezar otra
// prueba ya no depende de que el navegador recargue: se llama `nuevaSesion()`.
const CLAVE = 'session-id'

// ponytail: si sessionStorage no está disponible (modo privado de algunos
// navegadores), el id vive solo en memoria: se pierde al recargar, que es
// exactamente el comportamiento que había antes.
function guardar(id) {
  try {
    sessionStorage.setItem(CLAVE, id)
  } catch {
    /* sin almacenamiento: seguimos con el id en memoria */
  }
  return id
}

function inicial() {
  try {
    return sessionStorage.getItem(CLAVE) || guardar(crypto.randomUUID())
  } catch {
    return crypto.randomUUID()
  }
}

let actual = inicial()

export const sessionId = () => actual

/** Arranca otra prueba: nuevo id, para que no se mezcle con la anterior. */
export function nuevaSesion() {
  actual = guardar(crypto.randomUUID())
  return actual
}
