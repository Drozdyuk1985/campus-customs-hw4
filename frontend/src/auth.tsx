// Login state for the whole site. The session itself lives in an HttpOnly
// cookie the browser sends automatically; JavaScript never sees the token.
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'

export interface User {
  id: number
  first_name: string
  last_name: string
  email: string
}

export interface SignupInput {
  first_name: string
  last_name: string
  email: string
  password: string
  confirm_password: string
}

interface AuthState {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<User>
  signup: (input: SignupInput) => Promise<User>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

async function postJson<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
    credentials: 'same-origin',
  })
  if (!res.ok) {
    const data = await res.json().catch(() => null)
    throw new Error(data?.detail ?? 'Something went wrong. Please try again.')
  }
  return (res.status === 204 ? undefined : await res.json()) as T
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/auth/me', { credentials: 'same-origin' })
      .then((r) => (r.ok ? r.json() : null))
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const u = await postJson<User>('/api/auth/login', { email, password })
    setUser(u)
    return u
  }, [])

  const signup = useCallback(async (input: SignupInput) => {
    const u = await postJson<User>('/api/auth/signup', input)
    setUser(u)
    return u
  }, [])

  const logout = useCallback(async () => {
    await postJson<void>('/api/auth/logout')
    setUser(null)
  }, [])

  return <AuthContext.Provider value={{ user, loading, login, signup, logout }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
