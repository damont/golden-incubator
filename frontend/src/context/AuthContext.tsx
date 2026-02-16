import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { api } from '../api/client'
import type { User } from '../types'

interface AuthContextType {
  isAuthenticated: boolean
  isLoading: boolean
  user: User | null
  login: (username: string, password: string) => Promise<void>
  register: (email: string, username: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (api.isAuthenticated()) {
      api.get<User>('/api/auth/me')
        .then(setUser)
        .catch(() => api.clearToken())
        .finally(() => setIsLoading(false))
    } else {
      setIsLoading(false)
    }
  }, [])

  const login = async (username: string, password: string) => {
    const res = await api.post<{ access_token: string }>('/api/auth/login', { username, password })
    api.setToken(res.access_token)
    const u = await api.get<User>('/api/auth/me')
    setUser(u)
  }

  const register = async (email: string, username: string, password: string) => {
    await api.post('/api/auth/register', { email, username, password })
    await login(username, password)
  }

  const logout = () => {
    api.clearToken()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated: !!user, isLoading, user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)!
