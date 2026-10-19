// Iconos de trazo en SVG, dibujados a mano en una cuadricula de 24x24 para no
// sumar una libreria de iconos por veinte dibujos. Heredan el color del texto
// (currentColor), asi que se pintan con la paleta por CSS como cualquier letra.
const ICONOS = {
  manana: <><path d="M17 18a5 5 0 0 0-10 0" /><path d="M12 2v7" /><path d="m4.9 10.9 1.4 1.4" /><path d="M2 18h2" /><path d="M20 18h2" /><path d="m19.1 10.9-1.4 1.4" /><path d="M22 22H2" /><path d="m8 6 4-4 4 4" /></>,
  mediodia: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2" /><path d="M12 20v2" /><path d="m4.9 4.9 1.4 1.4" /><path d="m17.7 17.7 1.4 1.4" /><path d="M2 12h2" /><path d="M20 12h2" /><path d="m6.3 17.7-1.4 1.4" /><path d="m19.1 4.9-1.4 1.4" /></>,
  tarde: <><path d="M17 18a5 5 0 0 0-10 0" /><path d="M12 9V2" /><path d="m4.9 10.9 1.4 1.4" /><path d="M2 18h2" /><path d="M20 18h2" /><path d="m19.1 10.9-1.4 1.4" /><path d="M22 22H2" /><path d="m16 5-4 4-4-4" /></>,
  noche: <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />,
  reloj: <><circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" /></>,
  balanza: <><path d="M12 3v18" /><path d="M7 21h10" /><path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2" /><path d="m2 16 3-8 3 8c-.9.7-1.9 1-3 1s-2.1-.3-3-1Z" /><path d="m16 16 3-8 3 8c-.9.7-1.9 1-3 1s-2.1-.3-3-1Z" /></>,
  comun: <><circle cx="9" cy="12" r="6" /><circle cx="15" cy="12" r="6" /></>,
  brujula: <><circle cx="12" cy="12" r="10" /><path d="m16.2 7.8-1.8 5.4a2 2 0 0 1-1.3 1.3l-5.3 1.7 1.8-5.4a2 2 0 0 1 1.3-1.3Z" /></>,
  foco: <><path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5" /><path d="M9 18h6" /><path d="M10 22h4" /></>,
  descargar: <><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><path d="m7 10 5 5 5-5" /><path d="M12 15V3" /></>,
  libro: <><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2Z" /><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7Z" /></>,
  barras: <><path d="M3 3v18h18" /><path d="M8 17v-5" /><path d="M13 17V7" /><path d="M18 17v-8" /></>,
  dona: <><path d="M21.2 15.9A10 10 0 1 1 8 2.8" /><path d="M22 12A10 10 0 0 0 12 2v10Z" /></>,
  diana: <><circle cx="12" cy="12" r="10" /><circle cx="12" cy="12" r="6" /><circle cx="12" cy="12" r="2" /></>,
  check: <><circle cx="12" cy="12" r="10" /><path d="m8 12 3 3 5-6" /></>,
  ajustes: <><path d="M4 21v-7" /><path d="M4 10V3" /><path d="M12 21v-9" /><path d="M12 8V3" /><path d="M20 21v-5" /><path d="M20 12V3" /><path d="M1 14h6" /><path d="M9 8h6" /><path d="M17 16h6" /></>,
  birrete: <><path d="M22 10 12 5 2 10l10 5 10-5Z" /><path d="M6 12v5c3 3 9 3 12 0v-5" /><path d="M22 10v6" /></>,
  pin: <><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" /><circle cx="12" cy="10" r="3" /></>,
  flecha: <><path d="M5 12h14" /><path d="m12 5 7 7-7 7" /></>,
  atras: <><path d="M19 12H5" /><path d="m12 19-7-7 7-7" /></>,
  reintentar: <><path d="M3 12a9 9 0 1 0 9-9 9.8 9.8 0 0 0-6.7 2.7L3 8" /><path d="M3 3v5h5" /></>,
  alerta: <><circle cx="12" cy="12" r="10" /><path d="M12 8v4" /><path d="M12 16h.01" /></>,
  cerrar: <><path d="M18 6 6 18" /><path d="m6 6 12 12" /></>,
}

export default function Icono({ nombre, tam = 18, grosor = 2 }) {
  return (
    <svg
      className="icono" width={tam} height={tam} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth={grosor} strokeLinecap="round" strokeLinejoin="round"
      aria-hidden="true" focusable="false"
    >
      {ICONOS[nombre]}
    </svg>
  )
}
