import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import Inicio from './Inicio.jsx'
import Acerca from './Acerca.jsx'
import Catalogo from './Catalogo.jsx'
import Parametros from './Parametros.jsx'
import Mapa from './Mapa.jsx'
import Chat from './Chat.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Inicio />} />
        <Route path="/acerca" element={<Acerca />} />
        <Route path="/catalogo" element={<Catalogo />} />
        <Route path="/parametros" element={<Parametros />} />
        <Route path="/mapa" element={<Mapa />} />
        <Route path="/chat" element={<Chat />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
