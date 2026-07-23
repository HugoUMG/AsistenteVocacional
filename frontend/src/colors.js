// Paleta compartida: opciones del chat, gráficas del dashboard y el PDF usan
// estos colores. Identidad de marca Orienta: azul, azul marino, gris, negro
// (ver "Identidad visual" en CLAUDE.md) — sin violetas, rosas ni verdes.
export const COLORS = [
  '#1d4ed8', '#0ea5e9', '#12294d', '#334155', '#2563eb', '#64748b',
  '#0b1a33', '#3b82f6', '#94a3b8', '#0f1b2d', '#1e3a5f', '#475569',
]

export const color = (i) => COLORS[i % COLORS.length]
