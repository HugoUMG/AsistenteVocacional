// Un id de sesión por carga de página (un test = una sesión). Se envía en cada
// llamada de IA para que el backend atribuya el consumo de tokens y se pueda
// estimar costo/presupuesto. "Hacer otro test" recarga la página → nueva sesión.
export const SESSION_ID = crypto.randomUUID()
