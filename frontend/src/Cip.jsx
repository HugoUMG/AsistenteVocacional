import { useEffect, useMemo, useState } from 'react'
import Nav from './Nav'
import './App.css'

const API = 'http://localhost:8000'
// 150 ítems en páginas de 15 → 10 páginas. Paginar NO altera el instrumento
// siempre que se respete el orden impreso del cuadernillo: los ítems vienen
// entrelazados entre escalas a propósito, y agruparlos por escala induciría
// series de respuesta ("todo esto es de medicina, pongo Agrado a todo").
const POR_PAGINA = 15
// El test toma 25-30 min: sin esto una recarga accidental borra todo el avance.
const BORRADOR = 'cip-borrador'

const OPCIONES = [
  { valor: 'D', texto: 'Desagrado' },
  { valor: 'I', texto: 'Indiferencia' },
  { valor: 'A', texto: 'Agrado' },
]

function leerBorrador() {
  try {
    return JSON.parse(localStorage.getItem(BORRADOR) || 'null')
  } catch {
    return null
  }
}

function Barra({ valor }) {
  return (
    <div className="psi-barra">
      <span style={{ width: `${valor}%` }} />
    </div>
  )
}

function Aviso() {
  return (
    <p className="psi-instruccion">
      <strong>Prototipo en revisión.</strong> Este cuestionario está montado para
      que el asesor y la profesional de psicología puedan revisarlo. La
      autorización de uso del instrumento sigue en trámite, así que{' '}
      <strong>las respuestas no se guardan</strong> y todavía no debe aplicarse a
      estudiantes.
    </p>
  )
}

export default function Cip() {
  const [banco, setBanco] = useState(null) // null = cargando
  const [error, setError] = useState('')
  const [sexo, setSexo] = useState(() => leerBorrador()?.sexo || '')
  const [empezado, setEmpezado] = useState(() => Boolean(leerBorrador()?.empezado))
  const [pagina, setPagina] = useState(() => Number(leerBorrador()?.pagina) || 0)
  const [respuestas, setRespuestas] = useState(() => leerBorrador()?.respuestas || {})
  const [enviando, setEnviando] = useState(false)
  const [resultado, setResultado] = useState(null)

  useEffect(() => {
    fetch(`${API}/api/cip/preguntas`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(setBanco)
      .catch(() =>
        setError('No se pudo cargar el cuestionario. ¿Está encendido el servidor?')
      )
  }, [])

  useEffect(() => {
    localStorage.setItem(
      BORRADOR,
      JSON.stringify({ respuestas, pagina, sexo, empezado })
    )
  }, [respuestas, pagina, sexo, empezado])

  // Páginas correlativas: se conserva el orden del cuadernillo tal cual.
  const paginas = useMemo(() => {
    if (!banco) return []
    const out = []
    for (let i = 0; i < banco.items.length; i += POR_PAGINA) {
      out.push(banco.items.slice(i, i + POR_PAGINA))
    }
    return out
  }, [banco])

  // Un borrador viejo puede apuntar más allá del final si cambia POR_PAGINA o el
  // banco: sin esto la página quedaba en blanco y sin forma de salir.
  useEffect(() => {
    if (paginas.length && pagina > paginas.length - 1) setPagina(paginas.length - 1)
  }, [paginas, pagina])

  const actual = paginas[pagina]
  const total = banco?.items.length || 0
  const contestadas = Object.keys(respuestas).length
  const faltanEnPagina = actual
    ? actual.filter((it) => respuestas[it.n] === undefined).length
    : 0

  function reiniciar() {
    localStorage.removeItem(BORRADOR)
    setRespuestas({})
    setPagina(0)
    setEmpezado(false)
    setResultado(null)
    setError('')
  }

  function avanzar(delta) {
    setPagina((p) => p + delta)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  async function terminar() {
    if (enviando) return
    setEnviando(true)
    setError('')
    try {
      const r = await fetch(`${API}/api/cip`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ respuestas, sexo }),
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
      setEnviando(false)
    }
  }

  if (resultado) {
    return <Resultados datos={resultado} sexo={sexo} onReiniciar={reiniciar} />
  }

  // --- Portada: instrucciones y el dato que el baremo necesita ---
  if (!empezado) {
    return (
      <div className="pagina">
        <Nav />
        <main className="contenido contenido-angosto">
          <span className="pasos-kicker">Intereses profesionales</span>
          <h1>Cuestionario de Intereses Profesionales (CIP)</h1>
          <Aviso />
          {error && <p className="psi-error">{error}</p>}

          <p className="intro">
            Son <strong>{total || 150} actividades</strong> propias de distintas
            profesiones. En cada una indicas si te produce <strong>Agrado</strong>,{' '}
            <strong>Indiferencia</strong> o <strong>Desagrado</strong>. No es un
            examen: no hay respuestas correctas ni incorrectas, y no lleva nota.
          </p>
          <p className="intro">
            No hay límite de tiempo, aunque normalmente se completa en 25 a 30
            minutos. Conviene quedarse con la primera impresión y no detenerse
            demasiado en cada actividad. Piensa solo en si la tarea te gusta,
            dejando de lado si es bien pagada, si es prestigiosa o si crees que
            serías capaz de hacerla.
          </p>

          <section className="psi-bloque">
            <h2>Antes de empezar</h2>
            <p className="psi-texto">
              El baremo original del CIP solo existe separado por sexo, así que el
              dato hace falta para convertir tus puntuaciones a percentiles. Es una
              limitación del instrumento, no una decisión de esta plataforma.
            </p>
            <div className="psi-opciones" style={{ maxWidth: 420, marginTop: 12 }}>
              {[
                { v: 'femenino', t: 'Femenino' },
                { v: 'masculino', t: 'Masculino' },
              ].map((o) => (
                <button
                  key={o.v}
                  className={sexo === o.v ? 'sel' : ''}
                  onClick={() => setSexo(o.v)}
                >
                  {o.t}
                </button>
              ))}
            </div>
          </section>

          <div className="psi-nav">
            {contestadas > 0 && (
              <button className="psi-btn-sec" onClick={reiniciar}>
                Borrar avance ({contestadas})
              </button>
            )}
            <button
              className="hero-btn"
              disabled={!banco || !sexo}
              onClick={() => setEmpezado(true)}
            >
              {contestadas > 0 ? 'Continuar' : 'Empezar'}
            </button>
          </div>
          {!sexo && banco && (
            <p className="psi-faltan">Elige una opción para continuar.</p>
          )}
        </main>
      </div>
    )
  }

  // --- Cuestionario ---
  return (
    <div className="pagina">
      <Nav />
      <main className="contenido contenido-angosto">
        <span className="pasos-kicker">Intereses profesionales</span>
        <h1>Cuestionario de Intereses Profesionales</h1>
        <Aviso />

        {error && <p className="psi-error">{error}</p>}
        {!banco && !error && <p className="intro">Cargando cuestionario…</p>}

        {banco && actual && (
          <>
            <div className="psi-progreso">
              <Barra valor={Math.round((contestadas / total) * 100)} />
              <span className="psi-progreso-txt">
                {contestadas} de {total} · página {pagina + 1} de {paginas.length}
              </span>
            </div>

            <p className="psi-instruccion">
              ¿Qué tanto te atrae realizar cada una de estas actividades?
            </p>

            <ul className="psi-lista">
              {actual.map((it) => (
                <li key={it.n} className="psi-item">
                  <p className="psi-enunciado">
                    <span className="psi-num">{it.n}</span>
                    {it.texto}
                  </p>
                  <div className="psi-opciones">
                    {OPCIONES.map((o) => (
                      <button
                        key={o.valor}
                        className={respuestas[it.n] === o.valor ? 'sel' : ''}
                        onClick={() =>
                          setRespuestas((r) => ({ ...r, [it.n]: o.valor }))
                        }
                      >
                        {o.texto}
                      </button>
                    ))}
                  </div>
                </li>
              ))}
            </ul>

            <div className="psi-nav">
              <button
                className="psi-btn-sec"
                disabled={pagina === 0}
                onClick={() => avanzar(-1)}
              >
                Anterior
              </button>
              {/* El manual es explícito: no puede quedar ningún ítem sin
                  responder, así que la página no deja avanzar con huecos. */}
              {faltanEnPagina > 0 && (
                <span className="psi-faltan">
                  Faltan {faltanEnPagina} en esta página
                </span>
              )}
              {pagina < paginas.length - 1 ? (
                <button
                  className="hero-btn"
                  disabled={faltanEnPagina > 0}
                  onClick={() => avanzar(1)}
                >
                  Siguiente
                </button>
              ) : (
                <button
                  className="hero-btn"
                  disabled={faltanEnPagina > 0 || contestadas < total || enviando}
                  onClick={terminar}
                >
                  {enviando ? 'Calificando…' : 'Ver mi perfil'}
                </button>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  )
}

function Resultados({ datos, sexo, onReiniciar }) {
  const { resultado, sinceridad } = datos
  const { perfil, patron, baremo } = resultado
  const orden = [...perfil].sort((a, b) => b.percentil - a.percentil)
  // No se usa `dominantes` del backend tal cual: es el top 3 por orden, y en un
  // perfil plano eso destacaba áreas en percentil 25 — que no es interés bajo
  // sino rechazo. Solo se resalta lo que de verdad está alto; si nada lo está,
  // el manual dice que el consejo orientador no se sostiene, y eso es lo que se
  // muestra en lugar de inventar tres favoritas.
  const destacadas = orden.filter((e) => e.percentil >= 60).slice(0, 3)

  return (
    <div className="pagina">
      <Nav />
      <main className="contenido contenido-angosto">
        <span className="pasos-kicker">Resultados</span>
        <h1>Tu perfil de intereses profesionales</h1>
        <Aviso />

        <p className="intro">
          El percentil compara tu puntuación con la de otros estudiantes de la
          muestra de referencia. Un percentil de 80 en un área significa que tu
          interés por ella es mayor que el del 80% de esa muestra.{' '}
          <strong>Lo que orienta no es un área aislada, sino el contraste entre
          todas.</strong>
        </p>

        {sinceridad.alerta && (
          <div className="psi-flags">
            <span className="alerta">{sinceridad.nota}</span>
          </div>
        )}

        <section className="psi-bloque">
          <h2>Perfil por área</h2>
          {orden.map((e) => (
            <div key={e.romano} className="psi-rasgo">
              <span className="psi-rasgo-nombre">
                {destacadas.some((d) => d.romano === e.romano) ? '★ ' : ''}
                {e.nombre}
              </span>
              <Barra valor={e.percentil} />
              <span className="psi-rasgo-valor">{e.percentil}</span>
            </div>
          ))}
          <p className="psi-texto">{patron.nota}</p>
        </section>

        <section className="psi-bloque">
          <h2>
            {destacadas.length ? 'Tus áreas de mayor interés' : 'Sin áreas destacadas'}
          </h2>
          {destacadas.length === 0 ? (
            <p className="psi-texto">
              Ninguna área alcanzó un interés claramente por encima del resto. Eso
              no es un resultado inválido: puede significar que todavía estás
              explorando, o que el cuestionario no alcanzó a captar lo que te
              mueve. Conviene conversarlo con la persona que te acompaña en el
              proceso antes de sacar conclusiones.
            </p>
          ) : (
            destacadas.map((e) => (
              <div key={e.romano} style={{ marginBottom: 14 }}>
                <h3>
                  {e.nombre} · percentil {e.percentil}
                </h3>
                <p className="psi-texto">{e.definicion}</p>
              </div>
            ))
          )}
        </section>

        <section className="psi-bloque">
          <h2>Detalle de la calificación</h2>
          <p className="psi-texto">
            Baremo aplicado: muestra {baremo.muestra.replace(/-/g, ' ')}, sexo{' '}
            {sexo}, N = {baremo.n}. Las puntuaciones directas son la suma de los
            ítems de cada área (Desagrado 1, Indiferencia 2, Agrado 3).
          </p>
          <ul className="psi-metricas">
            {perfil.map((e) => (
              <li key={e.romano}>
                {e.romano}. {e.nombre}{' '}
                <strong>
                  {e.directa}/{e.n_items * 3}
                </strong>{' '}
                · Pc {e.percentil} · {e.conteo.A}A {e.conteo.I}I {e.conteo.D}D
              </li>
            ))}
          </ul>
        </section>

        <p className="intro">
          Este resultado es orientativo y describe intereses, no capacidades ni
          rendimiento. No sustituye la evaluación de un profesional de la
          psicología.
        </p>

        <div className="psi-nav">
          <button className="psi-btn-sec" onClick={onReiniciar}>
            Responderlo de nuevo
          </button>
        </div>
      </main>
    </div>
  )
}
