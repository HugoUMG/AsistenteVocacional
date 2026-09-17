import { useState } from 'react'
import Nav from './Nav'
import { actualizarEstudiante, authHeader } from './auth'
import { API } from './api'
import './App.css'

// Pantalla de bienvenida, una sola vez por cuenta, justo después del primer
// login: (1) confirma o corrige el nombre que trajo Google y (2) acepta los
// términos de uso. Se muestra desde Protegida, o sea antes de cualquier
// evaluación; el backend guarda la fecha en estudiantes.terminos_aceptados y
// no vuelve a pedirla.
const TERMINOS = [
  ['Sin costo',
    'La plataforma es gratuita. Es un proyecto de graduación y no se cobra por ninguna evaluación ni por el informe final.'],
  ['Uso de tus respuestas',
    'Tus respuestas y tus resultados quedan guardados en tu cuenta y se usarán para investigación académica: para evaluar y mejorar el recomendador. Se tratan con reserva y no se publican con tu nombre.'],
  ['Responde con honestidad',
    'La recomendación se construye solo con lo que tú respondes. Si contestas con sinceridad, el resultado se parece más a ti. Si contestas al azar o por salir del paso, la evaluación no será precisa.'],
  ['Es orientación, no un diagnóstico',
    'El informe te da carreras afines a tu perfil para que las pienses y las conversas con tu familia o un orientador. No sustituye a un profesional ni decide por ti.'],
  ['Responsabilidad',
    'La plataforma no se hace responsable del uso indebido que se le dé al informe final ni de decisiones tomadas únicamente a partir de él.'],
  ['Servicios externos',
    'Tus respuestas se procesan con la API de Gemini (Google) para generar las preguntas y la recomendación. El test de Holland lo califica la API de O*NET (Departamento de Trabajo de EE. UU.).'],
  ['Quién ve tus datos',
    'Solo el equipo del proyecto y la psicóloga que valida el estudio pueden revisar tu evaluación con tu nombre. En la tesis y en cualquier publicación los resultados se presentan sin identificarte.'],
  ['Si eres menor de edad',
    'Tu participación es voluntaria y fue autorizada por tu establecimiento educativo. Puedes dejar la evaluación en cualquier momento sin ninguna consecuencia.'],
  ['Cuánto tiempo se guardan',
    'Tus datos se conservan mientras dure la investigación y hasta que se cierre el proyecto de graduación.'],
  ['Puedes pedir que se borren',
    'Si quieres que eliminemos tu cuenta y tus resultados, escribe a hriverag5@miumg.edu.gt desde el correo con el que iniciaste sesión.'],
]

export default function Bienvenida({ sesion, onListo }) {
  const [paso, setPaso] = useState(1)
  const [nombre, setNombre] = useState(sesion.estudiante.nombre || '')
  const [acepto, setAcepto] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')

  async function confirmar() {
    setEnviando(true)
    setError('')
    try {
      const r = await fetch(`${API}/api/aceptar-terminos`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeader() },
        body: JSON.stringify({ nombre }),
      })
      if (!r.ok) {
        const d = await r.json().catch(() => null)
        // El 422 de Pydantic trae el motivo del nombre inválido en detail[0].msg.
        const msg = Array.isArray(d?.detail) ? d.detail[0]?.msg?.replace(/^Value error, /, '') : d?.detail
        throw new Error(msg || 'No se pudo guardar. Inténtalo de nuevo.')
      }
      onListo(actualizarEstudiante(await r.json()))
    } catch (e) {
      setError(String(e.message || e))
      setPaso(1) // el único dato editable es el nombre: ahí se corrige
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="pagina">
      <Nav />
      <main className="contenido contenido-angosto">
        <span className="pasos-kicker">Paso {paso} de 2</span>
        {paso === 1 ? (
          <>
            <h1>Verifica tu información</h1>
            <p className="intro">
              Así aparecerás en tus resultados y en tu historial. Puedes cambiar el nombre si quieres.
            </p>
            <div className="bienvenida-form">
              <label>
                Nombre
                <input
                  value={nombre}
                  onChange={(e) => setNombre(e.target.value)}
                  maxLength={40}
                  autoFocus
                />
              </label>
              <label>
                Correo
                <input value={sesion.estudiante.email || ''} readOnly />
              </label>
              {error && <p className="psi-error">{error}</p>}
              <button className="hero-btn" disabled={nombre.trim().length < 2} onClick={() => setPaso(2)}>
                Siguiente
              </button>
            </div>
          </>
        ) : (
          <>
            <h1>Términos y condiciones</h1>
            <p className="intro">Antes de empezar, lee esto. Es corto y te explica cómo usamos lo que respondes.</p>
            <ol className="bienvenida-terminos">
              {TERMINOS.map(([titulo, texto]) => (
                <li key={titulo}><strong>{titulo}.</strong> {texto}</li>
              ))}
            </ol>
            <div className="bienvenida-form">
              <label className="bienvenida-check">
                <input type="checkbox" checked={acepto} onChange={(e) => setAcepto(e.target.checked)} />
                Leí y acepto los términos y condiciones
              </label>
              <div className="bienvenida-botones">
                <button className="psi-btn-sec" onClick={() => setPaso(1)} disabled={enviando}>Atrás</button>
                <button className="hero-btn" disabled={!acepto || enviando} onClick={confirmar}>
                  {enviando ? 'Guardando…' : 'Aceptar y continuar'}
                </button>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  )
}
