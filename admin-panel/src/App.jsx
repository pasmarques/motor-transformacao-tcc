import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useState } from 'react'
import Login from './pages/Login'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Plugins from './pages/Plugins'
import Regras from './pages/Regras'
import { getAccessToken } from './api/client'

function RequireAuth({ children }) {
  const token = getAccessToken()
  if (!token) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  const [autenticado, setAutenticado] = useState(!!getAccessToken())

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login onLogin={() => setAutenticado(true)} />} />
        <Route
          path="/"
          element={
            autenticado
              ? <Layout onLogout={() => setAutenticado(false)} />
              : <Navigate to="/login" replace />
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="plugins" element={<Plugins />} />
          <Route path="regras" element={<Regras />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
