import { useEffect, useMemo, useRef, useState } from 'react'
import Nav from './Nav'
import { sessionId } from './session'
import './App.css'

const API = 'http://localhost:8000'
const POR_PAGINA = 20
// El examen son 100 ítems (20-30 min): sin esto, una recarga accidental borra
// todo el avance. Se limpia al terminar.
const BORRADOR = 'psicometrico-borrador'

// Formatea segundos como "4 min 12 s".
function tiempo(seg) {
  if (!seg && seg !== 0) return '—'
  const m = Math.floor(seg / 60)
  return m ? `${m} min ${seg % 60} s` : `${seg} s`
}

// Escala de caritas para la sección de personalidad, de rojo (1) a verde (5).
// El color aquí es SEMÁNTICO (escala de acuerdo), no decorativo: es la misma
// excepción a la paleta azul de marca que el badge de confianza del dashboard.
// La etiqueta larga que manda el backend viaja en aria-label/title, así que el
// significado no depende solo del color ni de la carita.
const CARITAS = [
  { color: '#e5484d', corto: 'Para nada', boca: 'M12 29 Q20 21 28 29' },
  { color: '#f76b15', corto: 'Poco', boca: 'M12 28 Q20 23 28 28' },
  { color: '#eab308', corto: 'Más o menos', boca: 'M12.5 26.5 L27.5 26.5' },
  { color: '#84cc16', corto: 'Bastante', boca: 'M12 24 Q20 29 28 24' },
  { color: '#16a34a', corto: 'Totalmente', boca: 'M12 23 Q20 31 28 23' },
]

function Carita({ boca }) {
  return (
    <svg viewBox="0 0 40 40" width="34" height="34" aria-hidden="true">
      <circle cx="20" cy="20" r="16.5" fill="none" stroke="currentColor" strokeWidth="2.2" />
      <circle cx="14.5" cy="16" r="2.1" fill="currentColor" />
      <circle cx="25.5" cy="16" r="2.1" fill="currentColor" />
      <path d={boca} fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  )
}

function leerBorrador() {
  try {
    return JSON.parse(localStorage.getItem(BORRADOR) || 'null')
  } catch {
    return null
  }
}

// Barra horizontal simple (0-100). No usa Recharts: es una sola métrica por fila.
function Barra({ valor }) {
  return (
    <div className="psi-barra">
      <span style={{ width: `${valor}%` }} />
    </div>
  )
}

export default function Psicometrico() {
  const [banco, setBanco] = useState(null) // null = cargando
  const [error, setError] = useState('')
  const [pagina, setPagina] = useState(() => Number(leerBorrador()?.pagina) || 0)
  const [respuestas, setRespuestas] = useState(() => leerBorrador()?.respuestas || {})
  const [enviando, setEnviando] = useState(false)
  const [resultado, setResultado] = useState(null)

  // Tiempo por categoría: se acumula al salir de cada una (el baremo y la
  // lectura de velocidad vs. precisión lo necesitan). Va en el borrador porque
  // si no, una recarga conservaba las respuestas pero reiniciaba el reloj y las
  // secciones ya trabajadas salían en "0 s".
  const tiempos = useRef(leerBorrador()?.tiempos || {})
  // null hasta el PRIMER clic: si arrancara al cargar la página, dejar la
  // pestaña abierta antes de empezar se le cobraba a la primera sección.
  const inicio = useRef(null)
  // El guardia del doble envío tiene que ser un ref, no el estado `enviando`:
  // setEnviando(true) no surte efecto hasta el siguiente render, así que tres
  // clics rápidos disparaban tres POST (y tres llamadas a Gemini).
  const enviandoRef = useRef(false)

  useEffect(() => {
    fetch(`${API}/api/psicometrico/preguntas`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(setBanco)
      .catch(() => setError('No se pudo cargar el examen. ¿Está encendido el servidor?'))
  }, [])

  useEffect(() => {
    localStorage.setItem(
      BORRADOR,
      JSON.stringify({ respuestas, pagina, tiempos: tiempos.current })
    )
  }, [respuestas, pagina])

  // Páginas de 20 ítems SIN mezclar categorías: personalidad ocupa 2, cada
  // sección de razonamiento ocupa 1.
  const paginas = useMemo(() => {
    if (!banco) return []
    const out = []
    for (const cat of Object.keys(banco.categorias)) {
      const items = banco.preguntas.filter((p) => p.categoria === cat)
      for (let i = 0; i < items.length; i += POR_PAGINA) {
        out.push({ categoria: cat, items: items.slice(i, i + POR_PAGINA) })
      }
    }
    return out
  }, [banco])

  // Un borrador viejo puede apuntar más allá del final (si cambia el tamaño del
  // banco o POR_PAGINA): sin esto la página quedaba en blanco, sin ítems ni
  // botones, y sin forma de salir salvo borrar el localStorage a mano.
  useEffect(() => {
    if (paginas.length && pagina > paginas.length - 1) setPagina(paginas.length - 1)
  }, [paginas, pagina])

  const actual = paginas[pagina]
  const total = banco?.preguntas.length || 0
  const contestadas = Object.keys(respuestas).length
  const esPersonalidad = actual?.categoria === 'personalidad'
  const faltanEnPagina = actual
    ? actual.items.filter((p) => respuestas[p.id] === undefined).length
    : 0

  function responder(id, valor) {
    if (inicio.current === null) inicio.current = Date.now() // el reloj arranca aquí
    setRespuestas((r) => ({ ...r, [id]: valor }))
  }

  // Cierra el cronómetro de la categoría que se abandona.
  function cerrarTiempo(cat) {
    if (inicio.current === null) return // ni empezó a contestar: no hay nada que cobrar
    const seg = Math.round((Date.now() - inicio.current) / 1000)
    tiempos.current[cat] = (tiempos.current[cat] || 0) + seg
    inicio.current = Date.now()
  }

  function avanzar(delta) {
    const destino = paginas[pagina + delta]
    if (destino && destino.categoria !== actual.categoria) cerrarTiempo(actual.categoria)
    setPagina((p) => p + delta)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  async function terminar() {
    if (enviandoRef.current) return
    enviandoRef.current = true
    cerrarTiempo(actual.categoria)
    setEnviando(true)
    setError('')
    try {
      const r = await fetch(`${API}/api/psicometrico`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          respuestas,
          tiempos: tiempos.current,
          session_id: sessionId(),
        }),
      })
      if (!r.ok) {
        const d = await r.json()
        throw new Error(d.detail?.[0]?.msg || d.detail || 'Error al calificar')
      }
      setResultado(await r.json())
      localStorage.removeItem(BORRADOR)
      window.scrollTo({ top: 0 })
    } catch (e) {
      setError(String(e.message || e))
    } finally {
      enviandoRef.current = false // que pueda reintentar si falló
      setEnviando(false)
    }
  }

  if (resultado) return <Resultados datos={resultado} banco={banco} />

  return (
    <div className="pagina">
      <Nav />
      <main className="contenido contenido-angosto">
        <span className="pasos-kicker">Exámenes psicométricos</span>
        <h1>Evaluación de perfil y aptitudes</h1>

        {error && <p className="psi-error">{error}</p>}
        {!banco && !error && <p className="intro">Cargando examen…</p>}

        {banco && actual && (
          <>
            <p className="intro">
              Un solo examen de {total} ítems dividido en cuatro secciones. Es
              independiente del chat vocacional: sus resultados no cambian las
              carreras que Orienta te recomienda.
            </p>

            <div className="psi-tabs">
              {Object.entries(banco.categorias).map(([clave, nombre]) => (
                <span
                  key={clave}
                  className={`psi-tab ${clave === actual.categoria ? 'sel' : ''}`}
                >
                  {nombre}
                </span>
              ))}
            </div>

            <div className="psi-progreso">
              <div className="psi-barra">
                <span style={{ width: `${(contestadas / total) * 100}%` }} />
              </div>
              <span className="psi-progreso-txt">
                {contestadas} de {total} · sección {pagina + 1} de {paginas.length}
              </span>
            </div>

            <p className="psi-instruccion">
              {esPersonalidad
                ? 'No hay respuestas correctas ni incorrectas: elige la carita que muestre qué tan de acuerdo estás con cada frase.'
                : actual.categoria === 'numerico'
                  ? 'Elige una opción por pregunta. Cada error resta ¼ de punto, así que es mejor dejar en blanco lo que no sepas que adivinar.'
                  : 'Elige una opción por pregunta. Puedes dejar en blanco lo que no sepas; los errores no restan.'}
            </p>

            <ol className="psi-lista">
              {actual.items.map((p) => (
                <li key={p.id} className="psi-item">
                  <p className="psi-enunciado" id={`psi-p${p.id}`}>
                    <span className="psi-num">{p.id}</span>
                    {p.texto}
                  </p>
                  {/* role=radiogroup: sin esto un lector de pantalla anuncia 5
                      botones sueltos por ítem, 100 veces, sin decir cuál está
                      elegida ni que son excluyentes. */}
                  <div
                    className={esPersonalidad ? 'psi-escala' : 'psi-opciones'}
                    role="radiogroup"
                    aria-labelledby={`psi-p${p.id}`}
                  >
                    {esPersonalidad
                      ? banco.escala.map((etiqueta, i) => {
                          const c = CARITAS[i]
                          const elegida = respuestas[p.id] === i + 1
                          return (
                            <button
                              key={etiqueta}
                              type="button"
                              role="radio"
                              aria-checked={elegida}
                              aria-label={etiqueta}
                              title={etiqueta}
                              className={elegida ? 'sel' : ''}
                              style={{ '--carita': c.color }}
                              onClick={() => responder(p.id, i + 1)}
                            >
                              <Carita boca={c.boca} />
                              <span>{c.corto}</span>
                            </button>
                          )
                        })
                      : p.opciones.map((op, i) => (
                          <button
                            key={op}
                            type="button"
                            role="radio"
                            aria-checked={respuestas[p.id] === i}
                            className={respuestas[p.id] === i ? 'sel' : ''}
                            onClick={() => responder(p.id, i)}
                          >
                            {op}
                          </button>
                        ))}
                  </div>
                </li>
              ))}
            </ol>

            <div className="psi-nav">
              <button
                type="button"
                className="psi-btn-sec"
                disabled={pagina === 0}
                onClick={() => avanzar(-1)}
              >
                ← Regresar
              </button>
              {/* En personalidad se exigen todas: sin respuesta no hay perfil de
                  rasgos. En las de razonamiento, dejar en blanco es una decisión
                  válida que el puntaje mide (intentadas vs. correctas). */}
              {esPersonalidad && faltanEnPagina > 0 && (
                <span className="psi-faltan">Faltan {faltanEnPagina} por responder</span>
              )}
              {pagina < paginas.length - 1 ? (
                <button
                  type="button"
                  className="hero-btn"
                  disabled={esPersonalidad && faltanEnPagina > 0}
                  onClick={() => avanzar(1)}
                >
                  Siguiente →
                </button>
              ) : (
                <button
                  type="button"
                  className="hero-btn"
                  disabled={enviando}
                  onClick={terminar}
                >
                  {enviando ? 'Calificando…' : 'Ver mis resultados'}
                </button>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  )
}

const NOMBRE_RASGO = {
  organizacion: 'Orden y atención al detalle',
  liderazgo: 'Iniciativa y exposición social',
  estabilidad: 'Manejo de la presión',
  apertura: 'Apertura al cambio y creatividad',
  interpersonal: 'Empatía y trabajo en equipo',
  logro: 'Orientación al logro',
}

function Resultados({ datos, banco }) {
  const { puntajes, resumen } = datos
  const per = puntajes.personalidad
  const secciones = ['logico', 'verbal', 'numerico']

  return (
    <div className="pagina">
      <Nav />
      <main className="contenido contenido-angosto">
        <span className="pasos-kicker">Resultados</span>
        <h1>Tu perfil psicométrico</h1>
        <p className="intro">
          Este examen mide estilo de trabajo y aptitudes; no mide inteligencia ni
          valor personal, y no diagnostica nada.
        </p>

        <section className="psi-bloque">
          <h2>Perfil de personalidad</h2>
          {Object.entries(per.rasgos).map(([clave, r]) => (
            <div key={clave} className="psi-rasgo">
              <span className="psi-rasgo-nombre">{NOMBRE_RASGO[clave] || clave}</span>
              <Barra valor={r.puntaje} />
              <span className="psi-rasgo-valor">{r.puntaje}</span>
            </div>
          ))}
          {/* No se muestra el conteo de contradicciones: con este banco de ítems,
              una divergencia aislada es normal en gente honesta, y verla en
              pantalla se lee como acusación. Solo se avisa bajo el umbral. */}
          <div className="psi-flags">
            <span className={per.consistencia.pct >= 70 ? 'ok' : 'alerta'}>
              Coherencia del perfil {per.consistencia.pct}%
              {per.consistencia.pct < 70 && ' · conviene revisarlo con calma'}
            </span>
            {per.deseabilidad_social.alerta && (
              <span className="alerta">
                Marcaste el máximo en todas las virtudes · el perfil pierde matiz
              </span>
            )}
            {per.tendencia_central.alerta && (
              <span className="alerta">
                Respondiste “Neutral” en el {per.tendencia_central.pct}% · con tanto
                punto medio el perfil casi no dice nada de ti
              </span>
            )}
          </div>
          {resumen && <p className="psi-texto">{resumen.personalidad}</p>}
        </section>

        <div className="psi-grid">
          {secciones.map((cat) => {
            const c = puntajes[cat]
            return (
              <section key={cat} className="psi-bloque">
                <h2>{banco?.categorias[cat] || cat}</h2>
                <p className="psi-dato-grande">
                  {c.correctas}<span>/{c.total}</span>
                </p>
                <ul className="psi-metricas">
                  <li>Percentil <strong>{c.percentil}</strong></li>
                  <li>
                    {/* precision viene null si no intentó ninguna: un "0%" ahí
                        se leería como "falló todas". */}
                    Precisión <strong>{c.precision === null ? '—' : `${c.precision}%`}</strong>
                    {' '}({c.intentadas} intentadas)
                  </li>
                  <li>Puntaje <strong>{c.puntaje}</strong>
                    {c.penalizacion_por_error > 0 && ' (con penalización por error)'}
                  </li>
                  <li>Tiempo <strong>{tiempo(c.segundos)}</strong></li>
                </ul>
                {resumen && <p className="psi-texto">{resumen[cat]}</p>}
              </section>
            )
          })}
        </div>

        {resumen ? (
          <section className="psi-bloque">
            <h2>Lectura general</h2>
            <div className="psi-listas">
              <div>
                <h3>Fortalezas</h3>
                <ul>{resumen.fortalezas.map((f, i) => <li key={i}>{f}</li>)}</ul>
              </div>
              <div>
                <h3>Por desarrollar</h3>
                <ul>{resumen.a_desarrollar.map((f, i) => <li key={i}>{f}</li>)}</ul>
              </div>
            </div>
            <p className="psi-texto">{resumen.cierre}</p>
          </section>
        ) : (
          <p className="psi-error">
            Tus respuestas quedaron guardadas, pero no se pudo generar el resumen
            con IA (revisa la GEMINI_API_KEY del backend).
          </p>
        )}

        <div className="psi-nav">
          <button
            type="button"
            className="psi-btn-sec"
            onClick={() => {
              localStorage.removeItem(BORRADOR)
              window.location.reload()
            }}
          >
            Hacer el examen de nuevo
          </button>
        </div>

        <p className="psi-nota">
          El percentil se calcula con un baremo ilustrativo, no con una muestra
          normativa real de estudiantes guatemaltecos. Un percentil por debajo de
          10 cae en el rango del azar: no distingue si se supo o se adivinó.
        </p>
      </main>
    </div>
  )
}
