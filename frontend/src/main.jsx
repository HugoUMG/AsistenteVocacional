import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
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
import Protegida from './Protegida.jsx'
import { MODO_COMPLETO } from './modo'

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
          <Route path="/mapa" element={<Mapa />} />
          <Route path="/chat" element={<Protegida><Chat /></Protegida>} />
          <Route path="/holland" element={<Protegida><Holland /></Protegida>} />
          <Route path="/historial" element={<Historial />} />
          {/* Solo en local: en producción se ofrecen los dos instrumentos
              confirmados. Ver modo.js. */}
          {MODO_COMPLETO && <Route path="/psicometrico" element={<Protegida><Psicometrico /></Protegida>} />}
          {MODO_COMPLETO && <Route path="/cip" element={<Protegida><Cip /></Protegida>} />}
          {MODO_COMPLETO && <Route path="/personalidad" element={<Protegida><Personalidad /></Protegida>} />}
          {/* Un enlace viejo a una ruta que ya no se ofrece manda al inicio, no
              a una pantalla en blanco. */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </GoogleOAuthProvider>
  </StrictMode>,
)
