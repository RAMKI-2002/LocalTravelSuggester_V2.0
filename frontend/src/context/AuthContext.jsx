/**
 * AuthContext — global authentication state.
 *
 * Why useContext (not Redux): three pages share one value (the JWT token).
 * Context is the right tool for this scope. Redux would add 4 files and
 * unnecessary boilerplate for a 3-page application.
 *
 * Token is stored in localStorage so it survives page refreshes.
 */

import { createContext, useContext, useState, useCallback } from 'react'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('access_token'))
  const [user, setUser] = useState(null)

  const login = useCallback((accessToken, userData = null) => {
    localStorage.setItem('access_token', accessToken)
    setToken(accessToken)
    setUser(userData)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('access_token')
    setToken(null)
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ token, user, login, logout, isLoggedIn: !!token }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
