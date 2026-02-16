import { useState } from 'react'
import { useAuth } from '../../context/AuthContext'

interface RegisterProps {
  onNavigate: (path: string) => void
}

export default function Register({ onNavigate }: RegisterProps) {
  const { register } = useAuth()
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await register(email, username, password)
    } catch {
      setError('Registration failed. Email or username may already be taken.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm p-6 rounded-lg" style={{ backgroundColor: 'var(--bg-surface)' }}>
        <h1 className="text-2xl font-bold mb-6 text-center">Create Account</h1>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            className="w-full px-3 py-2 rounded border bg-transparent"
            style={{ borderColor: 'var(--border-color)' }}
            required
          />
          <input
            type="text"
            placeholder="Username"
            value={username}
            onChange={e => setUsername(e.target.value)}
            className="w-full px-3 py-2 rounded border bg-transparent"
            style={{ borderColor: 'var(--border-color)' }}
            required
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            className="w-full px-3 py-2 rounded border bg-transparent"
            style={{ borderColor: 'var(--border-color)' }}
            required
          />
          {error && <p className="text-sm" style={{ color: 'var(--danger)' }}>{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 rounded font-medium text-white"
            style={{ backgroundColor: 'var(--accent)' }}
          >
            {loading ? 'Creating account...' : 'Create Account'}
          </button>
        </form>
        <p className="mt-4 text-center text-sm" style={{ color: 'var(--text-secondary)' }}>
          Already have an account?{' '}
          <a
            href="/login"
            onClick={e => { e.preventDefault(); onNavigate('/login') }}
            style={{ color: 'var(--accent)' }}
          >
            Sign in
          </a>
        </p>
      </div>
    </div>
  )
}
