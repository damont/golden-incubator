import { useAuth } from '../../context/AuthContext'

interface HeaderProps {
  onNavigate: (path: string) => void
}

export default function Header({ onNavigate }: HeaderProps) {
  const { user, logout } = useAuth()

  return (
    <header
      className="flex items-center justify-between px-4 py-3 border-b"
      style={{ backgroundColor: 'var(--header-bg)', borderColor: 'var(--border-color)' }}
    >
      <a
        href="/projects"
        onClick={e => { e.preventDefault(); onNavigate('/projects') }}
        className="text-lg font-bold"
        style={{ color: 'var(--accent)' }}
      >
        Golden Incubator
      </a>
      <div className="flex items-center gap-4">
        <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          {user?.username}
        </span>
        <button
          onClick={logout}
          className="text-sm px-3 py-1 rounded"
          style={{ color: 'var(--text-secondary)' }}
        >
          Logout
        </button>
      </div>
    </header>
  )
}
