import { useEffect, useState } from 'react'
import { GoogleLogin } from '@react-oauth/google'
import Nav from './Nav'
import Dashboard from './Dashboard'
import { Resultados as ResultadosHolland } from './Holland'
import { authHeader, iniciarSesionGoogle, sesionActual } from './auth'
import Recorrido from './Recorrido'
import './App.css'
import { API } from './api'

function Barra({ valor }) {
  return (
    <div className="psi-barra">
      <span style={{ width: `${valor}%` }} />
    </div>
  )
}

function fecha(iso) {
  return new Date(iso).toLocaleDateString('es-GT', { day: 'numeric', month: 'short', year: 'numeric' })
}

function CardChat({ fila, onAbrir }) {
  // El podio, no solo el primero: la segunda y la tercera suelen ser las
  // que el alumno estaba dudando, y sin ellas la tarjeta no dice casi nada.
  const podio = (fila.recomendacion || []).slice(0, 3)
  return (
    <li className="psi-item hist-card" onClick={() => onAbrir(fila)}>
      <p className="psi-enunciado">Chat con Orienta · {fecha(fila.fecha)}</p>
      {podio.length ? (
        <ol className="hist-podio">
          {podio.map((c, i) => (
            <li key={`${c.carrera}-${i}`}>
              <span className="hist-puesto">{i + 1}</span>
              <span className="hist-carrera">{c.carrera}</span>
              <span className="hist-afinidad">{c.afinidad}%</span>
            </li>
          ))}
        </ol>
      ) : (
        <p className="psi-texto">Sin recomendación guardada.</p>
      )}
    </li>
  )
}

function CardHolland({ fila, onAbrir }) {
  const orden = Object.entries(fila.areas).sort((a, b) => b[1] - a[1])
  return (
    <li className="psi-item hist-card" onClick={() => onAbrir(fila)}>
      <p className="psi-enunciado">Test de Holland · {fecha(fila.fecha)}</p>
      <p className="psi-texto">Código {fila.codigo}</p>
      {orden.slice(0, 3).map(([letra, score]) => (
        <div key={letra} className="psi-rasgo">
          <span className="psi-rasgo-nombre">{letra}</span>
          <Barra valor={Math.round((score / 40) * 100)} />
          <span className="psi-rasgo-valor">{score}</span>
        </div>
      ))}
    </li>
  )
}

function CardPersonalidad({ fila }) {
  const p = fila.puntajes
  return (
    <li className="psi-item">
      <p className="psi-enunciado">Perfil de personalidad · {fecha(fila.fecha)}</p>
      <p className="psi-texto">Estilo cognitivo dominante: {p.estilo_dominante.replaceAll('_', ' ')}</p>
    </li>
  )
}

function CardPsicometrico({ fila }) {
  const per = fila.puntajes.personalidad
  return (
    <li className="psi-item">
      <p className="psi-enunciado">Examen psicométrico · {fecha(fila.fecha)}</p>
      <p className="psi-texto">
        Lógico p{fila.puntajes.logico.percentil} · Verbal p{fila.puntajes.verbal.percentil} ·
        Numérico p{fila.puntajes.numerico.percentil} · Coherencia {per.consistencia.pct}%
      </p>
    </li>
  )
}

export default function Historial() {
  const [sesion, setSesion] = useState(sesionActual)
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState('')
  const [chatAbierto, setChatAbierto] = useState(null)
  const [verDashboard, setVerDashboard] = useState(false) // el recorrido es lo primero que se ve
  const [holland, setHolland] = useState(null) // el resultado completo, recalculado al abrirlo

  async function abrirHolland(fila) {
    setError('')
    setHolland('cargando')
    try {
      const r = await fetch(`${API}/api/holland/${fila.id}`, { headers: authHeader() })
      if (!r.ok) throw new Error((await r.json()).detail || 'No se pudo abrir el resultado.')
      setHolland(await r.json())
      window.scrollTo({ top: 0 })
    } catch (e) {
      setHolland(null)
      setError(String(e.message || e))
    }
  }

  useEffect(() => {
    if (!sesion) return
    fetch(`${API}/api/historial`, { headers: authHeader() })
      .then(async (r) => (r.ok ? r.json() : Promise.reject(new Error((await r.json()).detail))))
      .then(setDatos)
      .catch((e) => setError(String(e.message || e)))
  }, [sesion])

  async function alIniciarSesion(credentialResponse) {
    setError('')
    try {
      setSesion(await iniciarSesionGoogle(credentialResponse.credential))
    } catch (e) {
      setError(String(e.message || e))
    }
  }

  if (holland && holland !== 'cargando') {
    return <ResultadosHolland datos={holland} onVolver={() => setHolland(null)} />
  }

  if (chatAbierto && !verDashboard) {
    return (
      <Recorrido
        fila={chatAbierto}
        onVolver={() => setChatAbierto(null)}
        onDashboard={() => setVerDashboard(true)}
      />
    )
  }

  if (chatAbierto) {
    return (
      <Dashboard
        nombre={chatAbierto.respuestas?.nombre}
        carreras={chatAbierto.recomendacion || []}
        respuestas={chatAbierto.respuestas}
        diversificados={chatAbierto.diversificados}
        confianza={null}
        onReiniciar={() => setVerDashboard(false)}
        textoReiniciar="← Volver al recorrido"
      />
    )
  }

  return (
    <div className="pagina">
      <Nav />
      <main className="contenido contenido-angosto">
        <span className="pasos-kicker">Tu cuenta</span>
        <h1>Mi historial</h1>

        {!sesion && (
          <>
            <p className="intro">Inicia sesión con Google para ver tus resultados guardados.</p>
            <GoogleLogin onSuccess={alIniciarSesion} onError={() => setError('No se pudo iniciar sesión.')} />
          </>
        )}

        {error && <p className="psi-error">{error}</p>}

        {holland === 'cargando' && <p className="intro">Abriendo el resultado…</p>}

        {sesion && !datos && !error && <p className="intro">Cargando…</p>}

        {sesion && datos && (
          <>
            {datos.chat.length === 0 && datos.holland.length === 0 &&
              datos.personalidad.length === 0 && datos.psicometrico.length === 0 && (
              <p className="intro">
                Todavía no tienes resultados guardados. Haz un test y, al terminar,
                elige "guardar resultados" si no iniciaste sesión desde el inicio.
              </p>
            )}

            {datos.chat.length > 0 && (
              <section className="psi-bloque">
                <h2>Chat con Orienta</h2>
                <ul className="psi-lista">
                  {datos.chat.map((f) => <CardChat key={f.id} fila={f} onAbrir={setChatAbierto} />)}
                </ul>
              </section>
            )}
            {datos.holland.length > 0 && (
              <section className="psi-bloque">
                <h2>Test de Holland</h2>
                <ul className="psi-lista">
                  {datos.holland.map((f) => <CardHolland key={f.id} fila={f} onAbrir={abrirHolland} />)}
                </ul>
              </section>
            )}
            {datos.personalidad.length > 0 && (
              <section className="psi-bloque">
                <h2>Perfil de personalidad</h2>
                <ul className="psi-lista">
                  {datos.personalidad.map((f) => <CardPersonalidad key={f.id} fila={f} />)}
                </ul>
              </section>
            )}
            {datos.psicometrico.length > 0 && (
              <section className="psi-bloque">
                <h2>Examen psicométrico</h2>
                <ul className="psi-lista">
                  {datos.psicometrico.map((f) => <CardPsicometrico key={f.id} fila={f} />)}
                </ul>
              </section>
            )}
          </>
        )}
      </main>
    </div>
  )
}
