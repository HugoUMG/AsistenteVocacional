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

  // Fichas de las preguntas de intereses del chat (campo 'icono' en preguntas-fijas.js).
  corazon: <path d="M19 14c1.5-1.5 3-3.2 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.8 0-3 .5-4.5 2-1.5-1.5-2.7-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.1 3 5.5l7 7Z" />,
  maletin: <><rect x="2" y="7" width="20" height="14" rx="2" /><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" /></>,
  hoja: <><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.5 19 2c1 2 2 4.2 2 8 0 5.5-4.8 10-10 10Z" /><path d="M2 21c0-3 1.9-5.4 5.2-6.1 2.4-.5 4.9-2 5.8-4.9" /></>,
  llave: <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.8-3.8a6 6 0 0 1-7.9 7.9l-6.9 6.9a2.1 2.1 0 0 1-3-3l6.9-6.9a6 6 0 0 1 7.9-7.9l-3.8 3.8Z" />,
  personas: <><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M22 21v-2a4 4 0 0 0-3-3.9" /><path d="M16 3.1a4 4 0 0 1 0 7.8" /></>,
  martillo: <><path d="m15 12-8.5 8.5a2.1 2.1 0 0 1-3-3L12 9" /><path d="M17.6 15 22 10.6" /><path d="m20.9 11.7-1.2-1.3a3.2 3.2 0 0 1-.9-2.2v-.9L16 4.6A5.6 5.6 0 0 0 12.1 3H9l.9.8A6.2 6.2 0 0 1 12 8.4V10l2 2h2.5l2.3 1.9" /></>,
  montana: <path d="m8 3 4 8 5-5 5 15H2L8 3Z" />,
  edificio: <><rect x="4" y="2" width="16" height="20" rx="2" /><path d="M9 22v-4h6v4" /><path d="M8 6h.01" /><path d="M12 6h.01" /><path d="M16 6h.01" /><path d="M8 10h.01" /><path d="M12 10h.01" /><path d="M16 10h.01" /><path d="M8 14h.01" /><path d="M12 14h.01" /><path d="M16 14h.01" /></>,
  hospital: <><rect x="3" y="3" width="18" height="18" rx="3" /><path d="M12 8v8" /><path d="M8 12h8" /></>,
  arboles: <><path d="M10 10v.2A3 3 0 0 1 8.9 16H5a3 3 0 0 1-1-5.8V10a3 3 0 0 1 6 0Z" /><path d="M7 16v6" /><path d="M13 19v3" /><path d="M12 19h8.3a1 1 0 0 0 .7-1.7L18 14h.3a1 1 0 0 0 .7-1.7L16 9h.2a1 1 0 0 0 .8-1.7L13 3l-1.4 1.5" /></>,
  matraz: <><path d="M10 2v7.5L4.5 19A2 2 0 0 0 6.2 22h11.6a2 2 0 0 0 1.7-3L14 9.5V2" /><path d="M8.5 2h7" /><path d="M7 16h10" /></>,
  pizarra: <><path d="M2 3h20" /><path d="M21 3v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V3" /><path d="m7 21 5-5 5 5" /></>,
  casco: <><path d="M2 18a1 1 0 0 0 1 1h18a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1H3a1 1 0 0 0-1 1v2Z" /><path d="M10 10V5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v5" /><path d="M4 15v-3a6 6 0 0 1 6-6" /><path d="M14 6a6 6 0 0 1 6 6v3" /></>,
  camara: <><path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3Z" /><circle cx="12" cy="13" r="3" /></>,
  estetoscopio: <><path d="M11 2v2" /><path d="M5 2v2" /><path d="M5 3H4a2 2 0 0 0-2 2v4a6 6 0 0 0 12 0V5a2 2 0 0 0-2-2h-1" /><path d="M8 15a6 6 0 0 0 12 0v-3" /><circle cx="20" cy="10" r="2" /></>,
  monitor: <><rect x="2" y="3" width="20" height="14" rx="2" /><path d="M8 21h8" /><path d="M12 17v4" /><path d="M6 10h3l1.5-3 3 6 1.5-3h3" /></>,
  pesa: <><path d="M7 12h10" /><rect x="4" y="7" width="3" height="10" rx="1" /><rect x="17" y="7" width="3" height="10" rx="1" /><path d="M2 10v4" /><path d="M22 10v4" /></>,
  huella: <><circle cx="11" cy="4" r="2" /><circle cx="18" cy="8" r="2" /><circle cx="20" cy="16" r="2" /><path d="M9 10a5 5 0 0 1 5 5v3.5a3.5 3.5 0 0 1-6.8 1C6.5 17.5 4.5 16.8 4.5 16.8A3.5 3.5 0 0 1 5.5 10Z" /></>,
  brote: <><path d="M7 20h10" /><path d="M10 20c5.5-2.5.8-6.4 3-10" /><path d="M9.5 9.4c1.1.8 1.8 2.2 2.3 3.7-2 .4-3.5.4-4.8-.3-1.2-.6-2.3-1.9-3-4.2 2.8-.5 4.4 0 5.5.8Z" /><path d="M14.1 6a7 7 0 0 0-1.1 4c1.9-.1 3.3-.6 4.3-1.4 1-1 1.6-2.3 1.7-4.6-2.7.1-4 1-4.9 2Z" /></>,
  calculadora: <><rect x="4" y="2" width="16" height="20" rx="2" /><path d="M8 6h8" /><path d="M16 14v4" /><path d="M8 10h.01" /><path d="M12 10h.01" /><path d="M16 10h.01" /><path d="M8 14h.01" /><path d="M12 14h.01" /><path d="M8 18h.01" /><path d="M12 18h.01" /></>,
  laptop: <><rect x="3" y="4" width="18" height="12" rx="2" /><path d="M2 20h20" /></>,
  senal: <><path d="M12 20h.01" /><path d="M2 8.8a15 15 0 0 1 20 0" /><path d="M5 12.9a10 10 0 0 1 14 0" /><path d="M8.5 16.4a5 5 0 0 1 7 0" /></>,
  conversacion: <><path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z" /><path d="M15.8 9.2a2.5 2.5 0 0 0-3.5 0l-.3.4-.4-.4a2.5 2.5 0 1 0-3.5 3.5l3.9 3.8 3.8-3.8a2.5 2.5 0 0 0 0-3.5Z" /></>,
  mazo: <><path d="m14 13-7.5 7.5a2.1 2.1 0 0 1-3-3L11 10" /><path d="m16 16 6-6" /><path d="m8 8 6-6" /><path d="m9 7 8 8" /><path d="m21 11-8-8" /></>,
  columnas: <><path d="M3 22h18" /><path d="M6 18v-7" /><path d="M10 18v-7" /><path d="M14 18v-7" /><path d="M18 18v-7" /><path d="M12 2 20 7H4Z" /></>,
  vela: <><path d="M9 22V12h6v10" /><path d="M7 22h10" /><path d="M12 9.5V12" /><path d="M12 2c1.5 2 2.5 3.2 2.5 4.6a2.5 2.5 0 0 1-5 0C9.5 5.2 10.5 4 12 2Z" /></>,
  paleta: <><path d="M12 22a10 10 0 1 1 10-10c0 2.2-1.8 3-3.5 3H16a2 2 0 0 0-1.5 3.3A2 2 0 0 1 12 22Z" /><circle cx="13.5" cy="6.5" r="1" /><circle cx="17.5" cy="10.5" r="1" /><circle cx="8.5" cy="7.5" r="1" /><circle cx="6.5" cy="12.5" r="1" /></>,
  musica: <><path d="M9 18V5l12-2v13" /><circle cx="6" cy="18" r="3" /><circle cx="18" cy="16" r="3" /></>,
  megafono: <><path d="m3 11 18-5v12L3 14v-3Z" /><path d="M11.6 16.8a3 3 0 1 1-5.8-1.6" /></>,
  idiomas: <><path d="m5 8 6 6" /><path d="m4 14 6-6 2-3" /><path d="M2 5h12" /><path d="M7 2h1" /><path d="m22 22-5-10-5 10" /><path d="M14 18h6" /></>,
  monedas: <><circle cx="8" cy="8" r="6" /><path d="M18.1 10.4A6 6 0 1 1 10.3 18" /><path d="M7 6h1v4" /><path d="m16.7 13.9.7.7-2.8 2.8" /></>,
  tendencia: <><path d="M22 7 13.5 15.5 8.5 10.5 2 17" /><path d="M16 7h6v6" /></>,
  mundo: <><circle cx="12" cy="12" r="10" /><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" /><path d="M2 12h20" /></>,
  organigrama: <><rect x="9" y="2" width="6" height="5" rx="1" /><rect x="2" y="17" width="6" height="5" rx="1" /><rect x="16" y="17" width="6" height="5" rx="1" /><path d="M5 17v-3h14v3" /><path d="M12 7v7" /></>,
  cubiertos: <><path d="M3 2v7c0 1.1.9 2 2 2h4a2 2 0 0 0 2-2V2" /><path d="M7 2v20" /><path d="M21 15V2a5 5 0 0 0-5 5v6c0 1.1.9 2 2 2h3Zm0 0v7" /></>,
  lapiz: <><path d="M12 20h9" /><path d="M16.4 3.6a2.1 2.1 0 1 1 3 3L7.4 18.6 3 20l1.4-4.4Z" /></>,

  // Tarjetas del catálogo (ver icono-carrera.js).
  diente: <path d="M12 5.5C10.5 3.5 5.5 3 4.5 6.5c-.6 2.2.4 4.3 1 6.5.6 2.4.6 7 2.5 7 1.6 0 1.4-4.5 4-4.5s2.4 4.5 4 4.5c1.9 0 1.9-4.6 2.5-7 .6-2.2 1.6-4.3 1-6.5C18.5 3 13.5 3.5 12 5.5Z" />,
  ojo: <><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z" /><circle cx="12" cy="12" r="3" /></>,
  manzana: <><path d="M12 7c-1.5-1-3.2-1.3-4.7-.7C4.8 7.2 3.8 10 4.3 13c.6 3.6 3.1 8 5.6 8 1 0 1.4-.5 2.1-.5s1.1.5 2.1.5c2.5 0 5-4.4 5.6-8 .5-3-.5-5.8-3-6.7-1.5-.6-3.2-.3-4.7.7Z" /><path d="M12 7c0-2 1-3.5 3-4.5" /></>,
  lupa: <><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></>,
}

export default function Icono({ nombre, tam = 18, grosor = 2 }) {
  // Un nombre mal escrito no rompe nada, solo deja el hueco vacío: que avise.
  if (import.meta.env.DEV && !ICONOS[nombre]) console.warn(`Icono desconocido: "${nombre}"`)
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
