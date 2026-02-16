import { useState } from 'react'
import { api } from '../../api/client'

interface CreateProjectProps {
  onNavigate: (path: string) => void
}

export default function CreateProject({ onNavigate }: CreateProjectProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [githubUrl, setGithubUrl] = useState('')
  const [githubPat, setGithubPat] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const body: Record<string, string> = { name }
      if (description) body.description = description
      if (githubUrl) body.github_repo_url = githubUrl
      if (githubPat) body.github_pat = githubPat

      const project = await api.post<{ id: string }>('/api/projects/', body)
      onNavigate(`/projects/${project.id}`)
    } catch {
      setError('Failed to create project')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-lg mx-auto">
      <h1 className="text-2xl font-bold mb-6">New Project</h1>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div>
          <label className="block text-sm mb-1" style={{ color: 'var(--text-secondary)' }}>
            Project Name *
          </label>
          <input
            type="text"
            value={name}
            onChange={e => setName(e.target.value)}
            className="w-full px-3 py-2 rounded border bg-transparent"
            style={{ borderColor: 'var(--border-color)' }}
            required
          />
        </div>
        <div>
          <label className="block text-sm mb-1" style={{ color: 'var(--text-secondary)' }}>
            Description
          </label>
          <textarea
            value={description}
            onChange={e => setDescription(e.target.value)}
            className="w-full px-3 py-2 rounded border bg-transparent resize-none"
            style={{ borderColor: 'var(--border-color)' }}
            rows={3}
          />
        </div>
        <div className="border-t pt-4" style={{ borderColor: 'var(--border-color)' }}>
          <p className="text-sm mb-3" style={{ color: 'var(--text-secondary)' }}>
            GitHub Integration (optional)
          </p>
          <div className="flex flex-col gap-3">
            <input
              type="url"
              placeholder="Repository URL"
              value={githubUrl}
              onChange={e => setGithubUrl(e.target.value)}
              className="w-full px-3 py-2 rounded border bg-transparent"
              style={{ borderColor: 'var(--border-color)' }}
            />
            <input
              type="password"
              placeholder="Personal Access Token"
              value={githubPat}
              onChange={e => setGithubPat(e.target.value)}
              className="w-full px-3 py-2 rounded border bg-transparent"
              style={{ borderColor: 'var(--border-color)' }}
            />
          </div>
        </div>
        {error && <p className="text-sm" style={{ color: 'var(--danger)' }}>{error}</p>}
        <div className="flex gap-3">
          <button
            type="button"
            onClick={() => onNavigate('/projects')}
            className="px-4 py-2 rounded"
            style={{ color: 'var(--text-secondary)' }}
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="flex-1 py-2 rounded font-medium text-white"
            style={{ backgroundColor: 'var(--accent)' }}
          >
            {loading ? 'Creating...' : 'Create Project'}
          </button>
        </div>
      </form>
    </div>
  )
}
