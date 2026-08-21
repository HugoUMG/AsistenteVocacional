// Registro para quien aplica la evaluación: qué contestó cada alumno en las
// preguntas fijas y qué carreras le salieron. El acceso lo decide el BACKEND
// (ADMIN_EMAILS en backend/.env, ver app/auth.py): esta página solo muestra lo
// que el endpoint le entregue, y pinta el 403 tal cual si no está autorizado.
// Por eso no hay enlace en el menú: se entra escribiendo /admin.
import { useEffect, useState } from 'react'
import Nav from './Nav'
import Protegida from './Protegida'
import Recorrido from './Recorrido'
import Dashboard from './Dashboard'
import { authHeader } from './auth'
import { API } from './api'
import './App.css'

const COLUMNAS = [
  ['fecha', 'Fecha'],
  ['nombre', 'Nombre'],
  ['edad', 'Edad'],
  ['nivel', 'Nivel'],
  ['grado', 'Grado'],
  ['carrera_cursada', 'Carrera cursada'],
  ['gusto_grado', '¿Le gustó?'],
  ['motivo', 'Motivo del test'],
  ['carrera_descartada', 'Descartada'],
  ['departamento', 'Departamento'],
  ['top3', 'Top 3 recomendado'],
  ['feedback', '¿Acertó?'],
  ['cuenta', 'Cuenta'],
]

const fecha = (f) => (f ? new Date(f).toLocaleString('es-GT') : '')

function celda(fila, clave) {
  const v = fila[clave]
  if (clave === 'fecha') return fecha(v)
  if (clave === 'top3') return (v || []).join(' · ') || (fila.termino ? '' : 'No terminó')
  if (clave === 'feedback') return v === true ? 'Sí' : v === false ? 'No' : ''
  return v ?? ''
}

// ponytail: el CSV se arma aquí y no en el backend; son unos cientos de filas
// que la página ya tiene en memoria. Si algún día son miles, que lo genere el
// endpoint y se descargue en streaming.
function descargarCsv(filas) {
  const escapa = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`
  const lineas = [
    COLUMNAS.map(([, t]) => escapa(t)).join(','),
    ...filas.map((f) => COLUMNAS.map(([c]) => escapa(celda(f, c))).join(',')),
  ]
  // El BOM es para que Excel en Windows abra los acentos bien.
  const url = URL.createObjectURL(new Blob(['﻿' + lineas.join('\n')], { type: 'text/csv' }))
  const a = document.createElement('a')
  a.href = url
  a.download = `registro-${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

function Registro() {
  const [filas, setFilas] = useState(null)
  const [error, setError] = useState('')
  // La evaluación abierta, con TODO lo que contestó el alumno. La lista solo
  // trae el resumen, así que el detalle se pide al abrirla.
  const [abierta, setAbierta] = useState(null)
  const [verDashboard, setVerDashboard] = useState(false)

  async function abrir(id) {
    setError('')
    try {
      const r = await fetch(`${API}/api/admin/respuestas/${id}`, { headers: authHeader() })
      if (!r.ok) throw new Error((await r.json().catch(() => null))?.detail || 'No se pudo abrir la evaluación.')
      setAbierta(await r.json())
      setVerDashboard(false)
    } catch (e) {
      setError(String(e.message || e))
    }
  }

  useEffect(() => {
    fetch(`${API}/api/admin/respuestas`, { headers: authHeader() })
      .then(async (r) => {
        if (!r.ok) throw new Error((await r.json().catch(() => null))?.detail || 'No se pudo cargar el registro.')
        return r.json()
      })
      .then(setFilas)
      .catch((e) => setError(String(e.message || e)))
  }, [])

  if (abierta && !verDashboard) {
    return (
      <Recorrido
        fila={abierta}
        onVolver={() => setAbierta(null)}
        onDashboard={() => setVerDashboard(true)}
      />
    )
  }

  if (abierta) {
    return (
      <Dashboard
        nombre={abierta.respuestas?.nombre}
        carreras={abierta.recomendacion || []}
        respuestas={abierta.respuestas}
        diversificados={abierta.diversificados}
        confianza={null}
        onReiniciar={() => setVerDashboard(false)}
        textoReiniciar="← Volver al recorrido"
      />
    )
  }

  return (
    <div className="pagina">
      <Nav />
      <main className="contenido">
        <span className="pasos-kicker">Administración</span>
        <h1>Registro de evaluaciones</h1>
        {error && <p className="nav-login-error">{error}</p>}
        {!error && !filas && <p className="intro">Cargando…</p>}
        {filas && (
          <>
            <p className="intro">
              {filas.length} {filas.length === 1 ? 'evaluación' : 'evaluaciones'}, de la
              más reciente a la más antigua. Tocá una fila para ver su recorrido y
              su dashboard. Son datos de estudiantes: no los compartas fuera de
              quienes aplican el estudio.
            </p>
            <button className="opt" onClick={() => descargarCsv(filas)}>Descargar CSV</button>
            <div className="tabla-scroll">
              <table className="tabla-registro">
                <thead>
                  <tr>{COLUMNAS.map(([c, t]) => <th key={c}>{t}</th>)}</tr>
                </thead>
                <tbody>
                  {filas.map((f) => (
                    <tr key={f.id} className="fila-abrible" onClick={() => abrir(f.id)}>
                      {COLUMNAS.map(([c]) => <td key={c}>{celda(f, c)}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </main>
    </div>
  )
}

// Protegida pide el login de Google; el backend decide si ese correo es admin.
export default function Admin() {
  return (
    <Protegida>
      <Registro />
    </Protegida>
  )
}
