import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

export default function Login() {
  const { user, login, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from ?? '/'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await login(email, password)
      navigate(from, { replace: true, state: { flash: 'You are logged in.' } })
    } catch (err) {
      setError((err as Error).message)
      setPassword('')
    } finally {
      setBusy(false)
    }
  }

  if (user) {
    return (
      <div className="container page auth">
        <div className="auth-card">
          <h1>You're logged in</h1>
          <p className="muted">Signed in as <strong>{user.email}</strong>.</p>
          <Link to="/products" className="btn btn-primary">Keep shopping</Link>
          <button className="btn btn-ghost" onClick={() => logout()}>Log out to switch accounts</button>
        </div>
      </div>
    )
  }

  return (
    <div className="container page auth">
      <form className="auth-card" onSubmit={onSubmit} noValidate>
        <h1>Log in</h1>
        <p className="muted">Welcome back to Campus Customs.</p>
        {error && <p className="notice notice-error" role="alert">{error}</p>}
        <label>
          Email
          <input type="email" name="email" autoComplete="email" required value={email}
                 onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label>
          Password
          <input type="password" name="password" autoComplete="current-password" required value={password}
                 onChange={(e) => setPassword(e.target.value)} />
        </label>
        <button className="btn btn-primary" type="submit" disabled={busy || !email || !password}>
          {busy ? 'Logging in…' : 'Log in'}
        </button>
        <p className="muted small">
          New here? <Link to="/create-account">Create an account</Link>
        </p>
      </form>
    </div>
  )
}
