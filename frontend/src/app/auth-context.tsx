import React, { createContext, useContext, useEffect, useState } from 'react'
import { apiClient, setCsrfToken } from '../lib/api'
import type { AuthStatus } from '../types/auth'

interface AuthContextType {
  auth: AuthStatus | null
  isLoading: boolean
  error: string | null
  login: (password: string) => Promise<void>
  logout: () => Promise<void>
  refreshAuth: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [auth, setAuth] = useState<AuthStatus | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refreshAuth = async () => {
    try {
      const data = await apiClient<AuthStatus>('/api/auth/me')
      setAuth(data)
      if (data.csrf_token) {
        setCsrfToken(data.csrf_token)
      } else {
        setCsrfToken(null)
      }
      setError(null)
    } catch (err: any) {
      setAuth(null)
      setCsrfToken(null)
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    refreshAuth()
  }, [])

  const login = async (password: string) => {
    setError(null)
    try {
      const data = await apiClient<AuthStatus>('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ password }),
      })
      setAuth(data)
      if (data.csrf_token) {
        setCsrfToken(data.csrf_token)
      }
    } catch (err: any) {
      setError(err.message)
      throw err
    }
  }

  const logout = async () => {
    try {
      await apiClient('/api/auth/logout', { method: 'POST' })
    } finally {
      setAuth(null)
      setCsrfToken(null)
      // Hard reload or state reset
      window.location.href = '/login'
    }
  }

  return (
    <AuthContext.Provider
      value={{
        auth,
        isLoading,
        error,
        login,
        logout,
        refreshAuth,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
