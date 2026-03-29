import { useState, useEffect } from 'react'
import { api } from '../../api/client'
import type { Session } from '../../types'

interface SessionListProps {
  onNavigate: (path: string) => void
}

export default function SessionList({ onNavigate }: SessionListProps) {
  const [sessions, setSessions] = useState<Session[]>([])
  const [loading, setLoading] = useState(true)
  const [newName, setNewName] = useState('')
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    api.listSessions()
      .then(setSessions)
      .finally(() => setLoading(false))
  }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newName.trim()) return
    setCreating(true)
    try {
      const session = await api.createSession(newName.trim())
      onNavigate(`/sessions/${session.id}`)
    } finally {
      setCreating(false)
    }
  }

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm('Delete this session and all its data?')) return
    await api.deleteSession(id)
    setSessions(sessions.filter(s => s.id !== id))
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <p style={{ color: 'var(--text-secondary)' }}>Loading sessions...</p>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6" style={{ color: 'var(--text-primary)' }}>
        Requirements Sessions
      </h1>

      {/* Create new session */}
      <form onSubmit={handleCreate} className="flex gap-3 mb-8">
        <input
          type="text"
          value={newName}
          onChange={e => setNewName(e.target.value)}
          placeholder="New session name (e.g., My App Idea)"
          className="flex-1 px-4 py-2 rounded-lg text-sm"
          style={{
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border-color)',
            color: 'var(--text-primary)',
          }}
        />
        <button
          type="submit"
          disabled={creating || !newName.trim()}
          className="px-5 py-2 rounded-lg text-sm font-medium"
          style={{
            backgroundColor: 'var(--accent)',
            color: 'white',
            opacity: creating || !newName.trim() ? 0.5 : 1,
          }}
        >
          {creating ? 'Creating...' : 'Create'}
        </button>
      </form>

      {/* Session list */}
      {sessions.length === 0 ? (
        <p style={{ color: 'var(--text-secondary)' }}>
          No sessions yet. Create one to start gathering requirements.
        </p>
      ) : (
        <div className="space-y-2">
          {sessions.map(session => (
            <div
              key={session.id}
              onClick={() => onNavigate(`/sessions/${session.id}`)}
              className="flex items-center justify-between px-4 py-3 rounded-lg cursor-pointer transition-colors"
              style={{
                backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border-color)',
              }}
              onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--bg-raised)')}
              onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'var(--bg-surface)')}
            >
              <div>
                <p className="font-medium" style={{ color: 'var(--text-primary)' }}>
                  {session.name}
                </p>
                <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                  Updated {new Date(session.updated_at).toLocaleDateString()}
                </p>
              </div>
              <button
                onClick={e => handleDelete(session.id, e)}
                className="text-xs px-2 py-1 rounded"
                style={{ color: 'var(--danger)' }}
              >
                Delete
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
