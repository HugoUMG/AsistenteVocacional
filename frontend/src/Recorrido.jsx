// El recorrido de una evaluación: quién es el alumno, qué contestó en las
// preguntas fijas, qué le preguntó Orienta y qué le salió. Lo usan el historial
// del propio alumno y el registro de administración, que muestran exactamente lo
// mismo.
import Nav from './Nav'
import { CLAVES_FIJAS } from './preguntas-fijas'
import './App.css'

const fecha = (iso) =>
  new Date(iso).toLocaleDateString('es-GT', { day: 'numeric', month: 'short', year: 'numeric' })

// Nombre legible de cada pregunta fija en el recorrido. Las adaptativas no
// necesitan tabla: su clave ES la pregunta que hizo Orienta.
const ETIQUETAS = {
  nombre: 'Nombre',
  edad: 'Edad',
  nivel: 'Nivel académico',
  grado: 'Grado',
  carrera_cursada: 'Carrera que cursa o cursó',
  gusto_grado: '¿Le gustó?',
  motivo: 'Por qué hizo el test',
  impacto: 'Impacto que quiere tener',
  estilo: 'Cómo prefiere trabajar',
  entorno: 'Dónde se imagina trabajando',
  gustos: 'Temas que le apasionan',
  departamento: 'Departamento',
  carrera_descartada: 'Carrera descartada',
}

function Rama({ titulo, pasos }) {
  if (!pasos.length) return null
  return (
    <div className="rec-rama">
      <p className="rec-rama-titulo">{titulo}</p>
      <ul className="rec-pasos">
        {pasos.map(([clave, valor]) => (
          <li key={clave}>
            <span className="rec-pregunta">{(ETIQUETAS[clave] || clave).replaceAll('**', '')}</span>
            <span className="rec-respuesta">{String(valor)}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

// Qué midió el test de Holland de este alumno, si lo hizo. Va antes de las
// preguntas fijas porque en el modo 3 el chat parte de este perfil.
const LETRAS_RIASEC = { R: 'Realista', I: 'Investigador', A: 'Artístico',
  S: 'Social', E: 'Emprendedor', C: 'Convencional' }

function Holland({ h, historial = [] }) {
  if (!h) return null
  // Un alumno puede repetir el test: los demás intentos van como lista corta
  // debajo, para ver si el perfil se movió entre una evaluación y otra.
  const otros = historial.filter((o) => o.fecha !== h.fecha)
  return (
    <div className="rec-rama">
      <p className="rec-rama-titulo">
        Test de Holland {h.mismo_recorrido ? '' : '(de otro recorrido)'}
      </p>
      <ul className="rec-pasos">
        <li>
          <span className="rec-pregunta">Código RIASEC</span>
          <span className="rec-respuesta">{h.codigo} · {fecha(h.fecha)}</span>
        </li>
        {Object.entries(LETRAS_RIASEC).map(([l, nombre]) => (
          <li key={l}>
            <span className="rec-pregunta">{nombre} ({l})</span>
            <span className="rec-respuesta">{h.areas?.[l] ?? '-'}</span>
          </li>
        ))}
      </ul>
      {!!otros.length && (
        <ul className="rec-pasos">
          <li>
            <span className="rec-pregunta">Otros intentos ({otros.length})</span>
            <span className="rec-respuesta">
              {otros.map((o) => `${o.codigo} (${fecha(o.fecha)})`).join(' · ')}
            </span>
          </li>
        </ul>
      )}
    </div>
  )
}

// El recorrido completo de una evaluación, como diagrama de arriba abajo:
// quién es, qué contestó en las fijas, qué le preguntó Orienta y qué le salió.
// ponytail: el diagrama es HTML y CSS (una línea vertical y nodos), sin
// librería de grafos. Si algún día hay que ramificar de verdad, ahí sí.
export default function Recorrido({ fila, onVolver, onDashboard }) {
  const r0 = fila.respuestas || {}
  const entradas = Object.entries(r0)
  const esFija = ([c]) => CLAVES_FIJAS.includes(c) || c === 'departamento' || c === 'carrera_descartada'
  const identidad = ['nombre', 'edad', 'nivel', 'grado']
  const fijas = entradas
    .filter((e) => esFija(e) && !identidad.includes(e[0]))
    .filter(([c, v]) => c !== 'carrera_descartada' || v !== r0.carrera_cursada)
  const adaptativas = entradas.filter((e) => !esFija(e))
  const r = r0
  const podio = (fila.recomendacion || []).slice(0, 5)

  return (
    <div className="pagina">
      <Nav />
      <main className="contenido">
        <span className="pasos-kicker">Recorrido</span>
        <h1>Cómo llegó a este resultado</h1>
        <div className="rec-acciones">
          <button className="opt ghost" onClick={onVolver}>← Volver al historial</button>
          <button className="opt" onClick={onDashboard}>Ver el dashboard →</button>
        </div>

        <div className="rec-diagrama">
          <div className="rec-nodo rec-perfil">
            <strong>{r.nombre || 'Sin nombre'}</strong>
            <span>
              {[r.edad && `${r.edad} años`, r.nivel, r.grado].filter(Boolean).join(' · ')}
            </span>
            <span className="rec-fecha">{fecha(fila.fecha)}</span>
          </div>

          <Holland h={fila.holland} historial={fila.holland_historial} />
          <Rama titulo="Preguntas fijas" pasos={fijas} />
          <Rama titulo="Preguntas de Orienta" pasos={adaptativas} />

          <div className="rec-rama">
            <p className="rec-rama-titulo">Resultado</p>
            {podio.length ? (
              <ol className="rec-resultado">
                {podio.map((c, i) => (
                  <li key={`${c.carrera}-${i}`}>
                    <span className="hist-puesto">{i + 1}</span>
                    <span className="hist-carrera">{c.carrera}</span>
                    <span className="hist-afinidad">{c.afinidad}%</span>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="psi-texto">No llegó a ver resultados.</p>
            )}
            {!!fila.diversificados?.length && (
              <ul className="rec-diversificados">
                {fila.diversificados.map((d) => <li key={d.nombre}>{d.nombre}</li>)}
              </ul>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
