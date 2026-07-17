import { jsPDF } from 'jspdf'
import { COLORS } from './colors'

const ACCENT = [108, 92, 231] // morado
const VERDE = [0, 184, 148]
const TEXT = [43, 39, 64]
const MUTED = [122, 117, 150]
const LIGHT = [240, 238, 254]

const hexToRgb = (hex) => {
  const n = parseInt(hex.slice(1), 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}

// Genera y descarga un PDF profesional con el resultado vocacional.
export function generarPDF(nombre, carreras) {
  const doc = new jsPDF({ unit: 'pt', format: 'a4' })
  const W = doc.internal.pageSize.getWidth()
  const H = doc.internal.pageSize.getHeight()
  const M = 48
  const cw = W - 2 * M

  const espacio = (y, need) => (y + need > H - 60 ? (doc.addPage(), 64) : y)

  const seccion = (txt, y) => {
    y = espacio(y, 34)
    doc.setFillColor(...ACCENT)
    doc.roundedRect(M, y - 9, 4, 14, 2, 2, 'F')
    doc.setTextColor(...TEXT)
    doc.setFont('helvetica', 'bold')
    doc.setFontSize(14)
    doc.text(txt, M + 12, y + 2)
    return y + 26
  }

  const subtitulo = (txt, y) => {
    y = espacio(y, 24)
    doc.setTextColor(...MUTED)
    doc.setFont('helvetica', 'bold')
    doc.setFontSize(10)
    doc.text(txt.toUpperCase(), M, y)
    return y + 16
  }

  // ---------- Cabecera ----------
  doc.setFillColor(...ACCENT)
  doc.rect(0, 0, W, 96, 'F')
  doc.setTextColor(255, 255, 255)
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(22)
  doc.text('Orientación Vocacional', M, 48)
  doc.setFont('helvetica', 'normal')
  doc.setFontSize(12)
  const fecha = new Date().toLocaleDateString('es-GT', { year: 'numeric', month: 'long', day: 'numeric' })
  doc.text(`Reporte de ${nombre || 'estudiante'}   ·   ${fecha}`, M, 72)

  let y = 132

  // ---------- Barras de afinidad ----------
  y = seccion('Tus carreras más afines', y)
  const maxAf = Math.max(...carreras.map((c) => c.afinidad), 1)
  carreras.forEach((c, i) => {
    y = espacio(y, 30)
    const col = hexToRgb(COLORS[i % COLORS.length])
    doc.setTextColor(...TEXT)
    doc.setFont('helvetica', 'normal')
    doc.setFontSize(10)
    const nom = c.carrera.length > 62 ? c.carrera.slice(0, 60) + '…' : c.carrera
    doc.text(nom, M, y)
    doc.setFont('helvetica', 'bold')
    doc.setTextColor(...MUTED)
    doc.text(`${c.afinidad}%`, W - M, y, { align: 'right' })
    const by = y + 5
    doc.setFillColor(...LIGHT)
    doc.roundedRect(M, by, cw, 9, 4, 4, 'F')
    doc.setFillColor(...col)
    doc.roundedRect(M, by, Math.max(6, cw * (c.afinidad / maxAf)), 9, 4, 4, 'F')
    y = by + 24
  })

  // ---------- Carrera destacada ----------
  const top = carreras[0]
  y = seccion('Tu carrera destacada', y + 6)
  doc.setTextColor(...ACCENT)
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(15)
  doc.text(doc.splitTextToSize(top.carrera, cw), M, y)
  y += 20
  doc.setTextColor(...TEXT)
  doc.setFont('helvetica', 'normal')
  doc.setFontSize(10.5)
  const desc = doc.splitTextToSize(top.descripcion, cw)
  doc.text(desc, M, y)
  y += desc.length * 14 + 10

  // Por qué encaja
  if (top.razones?.length) {
    y = subtitulo('Por qué encaja contigo', y)
    top.razones.forEach((r) => {
      y = espacio(y, 16)
      doc.setFillColor(...VERDE)
      doc.circle(M + 3, y - 3, 2.4, 'F')
      doc.setTextColor(...TEXT)
      doc.setFont('helvetica', 'normal')
      doc.setFontSize(10)
      const rl = doc.splitTextToSize(r, cw - 16)
      doc.text(rl, M + 14, y)
      y += rl.length * 14 + 2
    })
    y += 8
  }

  // Lo que más influyó
  if (top.factores?.length) {
    y = subtitulo('Lo que más influyó', y)
    const col = hexToRgb(COLORS[0])
    top.factores.forEach((f) => {
      y = espacio(y, 26)
      doc.setTextColor(...TEXT)
      doc.setFont('helvetica', 'normal')
      doc.setFontSize(10)
      doc.text(f.nombre, M, y)
      doc.setTextColor(...MUTED)
      doc.text(`${f.peso}%`, W - M, y, { align: 'right' })
      const by = y + 4
      doc.setFillColor(...LIGHT)
      doc.roundedRect(M, by, cw, 8, 4, 4, 'F')
      doc.setFillColor(...col)
      doc.roundedRect(M, by, Math.max(6, cw * (f.peso / 100)), 8, 4, 4, 'F')
      y = by + 22
    })
    y += 8
  }

  // Dónde estudiarla
  if (top.instituciones?.length) {
    y = subtitulo('Dónde estudiarla', y)
    top.instituciones.forEach((inst) => {
      y = espacio(y, 48)
      doc.setTextColor(...ACCENT)
      doc.setFont('helvetica', 'bold')
      doc.setFontSize(10.5)
      doc.text(inst.universidad, M, y)
      y += 13
      doc.setTextColor(...MUTED)
      doc.setFont('helvetica', 'normal')
      doc.setFontSize(9)
      doc.text(`${inst.centro} · ${inst.departamento}`, M, y)
      y += 13
      doc.setTextColor(...TEXT)
      doc.setFontSize(9.5)
      const el = doc.splitTextToSize(inst.enfoque, cw)
      doc.text(el, M, y)
      y += el.length * 12 + 12
    })
  }

  // ---------- Pie en cada página ----------
  const total = doc.getNumberOfPages()
  for (let p = 1; p <= total; p++) {
    doc.setPage(p)
    doc.setDrawColor(...LIGHT)
    doc.line(M, H - 40, W - M, H - 40)
    doc.setTextColor(...MUTED)
    doc.setFont('helvetica', 'normal')
    doc.setFontSize(8)
    doc.text('Generado por el Asistente Vocacional', M, H - 26)
    doc.text(`Página ${p} de ${total}`, W - M, H - 26, { align: 'right' })
  }

  const slug = (nombre || 'estudiante').toLowerCase().replace(/[^a-z0-9]+/g, '-')
  doc.save(`orientacion-${slug}.pdf`)
}
