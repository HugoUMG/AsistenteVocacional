import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { GoogleOAuthProvider } from '@react-oauth/google'
import './index.css'
import Inicio from './Inicio.jsx'
import Acerca from './Acerca.jsx'
import Catalogo from './Catalogo.jsx'
import Parametros from './Parametros.jsx'
import Psicometrico from './Psicometrico.jsx'
import Mapa from './Mapa.jsx'
import Chat from './Chat.jsx'
import Cip from './Cip.jsx'
import Holland from './Holland.jsx'
import Personalidad from './Personalidad.jsx'
import Historial from './Historial.jsx'

// Sin VITE_GOOGLE_CLIENT_ID (frontend/.env), el provider igual monta: los
// botones de Google Login solo no aparecen o fallan al usarse, el resto de
// la app sigue funcionando anónima. Ver frontend/.env.example.
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || ''

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Inicio />} />
          <Route path="/acerca" element={<Acerca />} />
          <Route path="/catalogo" element={<Catalogo />} />
          <Route path="/parametros" element={<Parametros />} />
          <Route path="/psicometrico" element={<Psicometrico />} />
          <Route path="/mapa" element={<Mapa />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/cip" element={<Cip />} />
          <Route path="/holland" element={<Holland />} />
          <Route path="/personalidad" element={<Personalidad />} />
          <Route path="/historial" element={<Historial />} />
        </Routes>
      </BrowserRouter>
    </GoogleOAuthProvider>
  </StrictMode>,
)
