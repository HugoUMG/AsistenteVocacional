// Qué se muestra en producción y qué se queda en local.
//
// Producción = los dos instrumentos confirmados: el chat y el test de Holland.
// El psicométrico, el CIP y el perfil corto siguen enteros y accesibles en
// `npm run dev` (se siguen midiendo y se le pueden mostrar a la psicóloga),
// pero no salen en el build que ven los alumnos: el CIP no tiene autorización
// de uso, y el psicométrico y el perfil corto todavía no tienen medido si
// aportan algo al ranking (ver docs/psicometrico.md y docs/personalidad.md).
//
// El backend sirve esos endpoints igual: esto es qué se ofrece, no qué existe.
export const MODO_COMPLETO = import.meta.env.DEV
