// Paleta compartida: opciones del chat y gráficas del dashboard usan estos colores.
// Sin violetas: la identidad de la app es azul marino/azul (ver index.css).
export const COLORS = [
  '#1d4ed8', '#0ea5e9', '#fd79a8', '#fdcb6e', '#0984e3', '#e17055',
  '#00b894', '#60a5fa', '#e84393', '#16a085', '#f39c12', '#334155',
]

export const color = (i) => COLORS[i % COLORS.length]
