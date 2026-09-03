// De donde cuelga la API. En local, el backend de siempre; en el sitio
// desplegado, la URL del servicio, que entra por VITE_API_URL al compilar.
//
// Vite congela esto en el build: cambiar la variable exige volver a compilar,
// no basta con reiniciar. Sin barra final, que todas las rutas la ponen.
export const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')
