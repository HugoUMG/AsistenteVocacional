import { useState } from 'react'
import { GoogleLogin } from '@react-oauth/google'
import Nav from './Nav'
import { iniciarSesionGoogle, sesionActual } from './auth'
import './App.css'

// Envuelve las rutas donde el alumno se evalúa. El login es obligatorio para
// evaluarse: sostiene el enfriamiento entre evaluaciones y el tope de uso
// diario (ver backend/app/cuota.py). El backend lo exige por su lado con
// 401; esto solo evita que el alumno llene un test para descubrirlo al final.
//
// En desarrollo (npm run dev) se puede pasar sin sesión, para no tener que
// loguearse cada vez que se prueba un detalle del chat. El backend tiene que
// estar de acuerdo: LOGIN_OPCIONAL=1 en backend/.env, si no responde 401. El
// build de producción nunca entra por acá (import.meta.env.DEV es false).
// Qué es cada evaluación, para quien todavía no entró. Antes esta pantalla
// decía solo "iniciá sesión" y el alumno tenía que loguearse para enterarse de
// qué se trataba: la descripción va ANTES del botón, y el botón invita a
// evaluarse, no a iniciar sesión.
const PRESENTACION = {
  holland: {
    kicker: 'Test de intereses',
    titulo: 'Descubrí tu perfil de intereses (RIASEC)',
    intro: 'Son 60 afirmaciones cortas sobre actividades ("reparar un motor", "enseñar a un niño"). Contestás qué tanto te gustaría hacer cada una, y toma entre 10 y 15 minutos.',
    puntos: [
      'Mide tus seis áreas de interés: Realista, Investigador, Artístico, Social, Emprendedor y Convencional.',
      'Te devuelve tu código de tres letras, tus puntajes por área y las ocupaciones que mejor le calzan.',
      'Lo califica la API oficial de O*NET (Departamento de Trabajo de Estados Unidos), no una versión casera.',
      'Guardamos tu resultado en tu historial: podés volver a verlo y usarlo como punto de partida del chat.',
    ],
    cta: 'Evaluate ahora con tu cuenta de Google',
  },
  chat: {
    kicker: 'Orientación vocacional',
    titulo: 'Conversá con Orienta y descubrí qué estudiar',
    intro: 'Es una conversación guiada, no un formulario. Orienta te pregunta por tu nivel académico, lo que te apasiona y cómo te imaginás trabajando, y va afinando según lo que respondés. Toma entre 5 y 10 minutos.',
    puntos: [
      'Al final te entrega un dashboard con las carreras más afines a tu perfil y su porcentaje de afinidad.',
      'Son carreras reales del catálogo de universidades de tu departamento, con el detalle de dónde se imparten.',
      'Podés descargar tu resultado en PDF y compararlo con otras carreras.',
      'Guardamos tu recorrido en tu historial: podés volver a verlo cuando quieras.',
    ],
    cta: 'Evaluate ahora con tu cuenta de Google',
  },
}

const GENERICA = {
  kicker: 'Acceso',
  titulo: 'Iniciá sesión para empezar',
  intro: 'Necesitás entrar con tu cuenta de Google para hacer las evaluaciones. Así guardamos tus resultados en tu historial y podés volver a verlos cuando quieras.',
  puntos: [],
  cta: 'Entrá con tu cuenta de Google',
}

export default function Protegida({ children, test }) {
  const [sesion, setSesion] = useState(sesionActual)
  const [error, setError] = useState('')
  // sessionStorage y no useState: si no, cada recarga vuelve a pedir el clic.
  // Muere al cerrar la pestaña, que para una llave de desarrollo alcanza.
  const [sinLogin, setSinLogin] = useState(
    () => import.meta.env.DEV && sessionStorage.getItem('dev-sin-login') === '1'
  )

  if (sesion || sinLogin) return children

  async function entrar(respuesta) {
    setError('')
    try {
      setSesion(await iniciarSesionGoogle(respuesta.credential))
    } catch (e) {
      setError(String(e.message || e))
    }
  }

  const p = PRESENTACION[test] || GENERICA

  return (
    <div className="pagina">
      <Nav />
      <main className="contenido contenido-angosto">
        <span className="pasos-kicker">{p.kicker}</span>
        <h1>{p.titulo}</h1>
        <p className="intro">{p.intro}</p>
        {!!p.puntos.length && (
          <ul className="acceso-puntos">
            {p.puntos.map((t) => <li key={t}>{t}</li>)}
          </ul>
        )}
        <p className="acceso-cta">{p.cta}</p>
        <div className="nav-login">
          <GoogleLogin onSuccess={entrar} onError={() => setError('No se pudo iniciar sesión.')} />
        </div>
        {error && <p className="nav-login-error">{error}</p>}
        {import.meta.env.DEV && (
          <p className="intro">
            <button className="psi-btn-sec" onClick={() => { sessionStorage.setItem('dev-sin-login', '1'); setSinLogin(true) }}>
              Entrar sin sesión (solo local)
            </button>
          </p>
        )}
      </main>
    </div>
  )
}
