import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth, type SignupInput } from '../auth'

const EMPTY: SignupInput = { first_name: '', last_name: '', email: '', password: '', confirm_password: '' }

export default function CreateAccount() {
  const { user, signup, logout } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState<SignupInput>(EMPTY)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const set = (field: keyof SignupInput) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [field]: e.target.value }))

  const mismatch = form.confirm_password !== '' && form.password !== form.confirm_password

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    if (form.password !== form.confirm_password) {
      setError("Passwords don't match.")
      return
    }
    setBusy(true)
    try {
      const u = await signup(form)
      navigate('/', { replace: true, state: { flash: `Welcome, ${u.first_name}! Your account is ready.` } })
    } catch (err) {
      setError((err as Error).message)
      setForm((f) => ({ ...f, password: '', confirm_password: '' }))
    } finally {
      setBusy(false)
    }
  }

  if (user) {
    return (
      <div className="container page auth">
        <div className="auth-card">
          <h1>You're already logged in</h1>
          <p className="muted">Signed in as <strong>{user.email}</strong>. Log out first to create a different account.</p>
          <button className="btn btn-ghost" onClick={() => logout()}>Log out</button>
        </div>
      </div>
    )
  }

  return (
    <div className="container page auth">
      <form className="auth-card" onSubmit={onSubmit} noValidate>
        <h1>Create account</h1>
        <p className="muted">Save your chats with our shopping assistant.</p>
        {error && <p className="notice notice-error" role="alert">{error}</p>}
        <div className="field-row">
          <label>
            First name
            <input type="text" name="first_name" autoComplete="given-name" required maxLength={50}
                   value={form.first_name} onChange={set('first_name')} />
          </label>
          <label>
            Last name
            <input type="text" name="last_name" autoComplete="family-name" required maxLength={50}
                   value={form.last_name} onChange={set('last_name')} />
          </label>
        </div>
        <label>
          Email
          <input type="email" name="email" autoComplete="email" required value={form.email} onChange={set('email')} />
        </label>
        <label>
          Password
          <input type="password" name="password" autoComplete="new-password" required minLength={8} maxLength={128}
                 value={form.password} onChange={set('password')} />
          <span className="hint">At least 8 characters.</span>
        </label>
        <label>
          Confirm password
          <input type="password" name="confirm_password" autoComplete="new-password" required maxLength={128}
                 value={form.confirm_password} onChange={set('confirm_password')}
                 aria-invalid={mismatch} />
          {mismatch && <span className="hint hint-error">Passwords don't match.</span>}
        </label>
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? 'Creating account…' : 'Create account'}
        </button>
        <p className="muted small">
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </form>
    </div>
  )
}
