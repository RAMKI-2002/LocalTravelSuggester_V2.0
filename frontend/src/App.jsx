import { BrowserRouter, Routes, Route, Navigate, Link, useNavigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import HistoryPage from './pages/HistoryPage'
import FavoritesPage from './pages/FavoritesPage'

function Nav() {
  const { isLoggedIn, logout, user } = useAuth()
  const navigate = useNavigate()

  if (!isLoggedIn) return null

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <nav className="bg-indigo-700 text-white px-6 py-3 flex items-center gap-6 shadow">
      <span className="text-lg font-bold mr-4">🗺️ Local Travel Suggester</span>
      <Link to="/dashboard" className="hover:text-indigo-200 transition-colors">Dashboard</Link>
      <Link to="/history" className="hover:text-indigo-200 transition-colors">History</Link>
      <Link to="/favorites" className="hover:text-indigo-200 transition-colors">Favorites</Link>
      <div className="ml-auto flex items-center gap-4">
        {user && <span className="text-indigo-200 text-sm">👤 {user.username}</span>}
        <button
          onClick={handleLogout}
          className="bg-indigo-600 hover:bg-indigo-500 px-3 py-1 rounded text-sm transition-colors"
        >
          Logout
        </button>
      </div>
    </nav>
  )
}

function ProtectedRoute({ children }) {
  const { isLoggedIn } = useAuth()
  return isLoggedIn ? children : <Navigate to="/login" replace />
}

function AppRoutes() {
  return (
    <>
      <Nav />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
        <Route path="/history" element={<ProtectedRoute><HistoryPage /></ProtectedRoute>} />
        <Route path="/favorites" element={<ProtectedRoute><FavoritesPage /></ProtectedRoute>} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="min-h-screen bg-gray-50">
          <AppRoutes />
        </div>
      </BrowserRouter>
    </AuthProvider>
  )
}
