import { useEffect, useState } from 'react'
import './App.css'

const API = 'http://localhost:8000'

function App() {
  const [status, setStatus] = useState('comprobando...')

  useEffect(() => {
    fetch(`${API}/health`)
      .then((r) => r.json())
      .then((d) => setStatus(`backend: ${d.status}`))
      .catch(() => setStatus('backend: sin conexión'))
  }, [])

  return (
    <main style={{ fontFamily: 'sans-serif', padding: '2rem' }}>
      <h1>Recomendador Vocacional</h1>
      <p>{status}</p>
    </main>
  )
}

export default App
