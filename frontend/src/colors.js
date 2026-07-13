// Paleta compartida: opciones del chat y gráficas del dashboard usan estos colores.
export const COLORS = [
  '#6c5ce7', '#00cec9', '#fd79a8', '#fdcb6e', '#0984e3', '#e17055',
  '#00b894', '#a29bfe', '#e84393', '#16a085', '#f39c12', '#9b59b6',
]

export const color = (i) => COLORS[i % COLORS.length]
