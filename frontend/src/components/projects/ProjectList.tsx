import { useState, useEffect } from 'react'
import { api } from '../../api/client'
import type { Project } from '../../types'

interface ProjectListProps {
  onNavigate: (path: string) => void
}

const PHASE_LABELS: Record<string, string> = {
  intake: 'Intake',
  requirements: 'Requirements',
  architecture: 'Architecture',
  build: 'Build',
  deploy: 'Deploy',
  handoff: 'Handoff',
  complete: 'Complete',
}

const PHASE_COLORS: Record<string, string> = {
  intake: 'var(--success)',
  requirements: 'var(--accent)',
  architecture: 'var(--warning)',
  build: '#c084fc',
  deploy: '#f472b6',
  handoff: '#22d3ee',
  complete: 'var(--text-muted)',
}

export default function ProjectList({ onNavigate }: ProjectListProps) {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get<Project[]>('/api/projects/')
      .then(setProjects)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <p style={{ color: 'var(--text-secondary)' }}>Loading projects...</p>
  }

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <h1 className="text-2xl font-bold">Projects</h1>
        <button
          onClick={() => onNavigate('/projects/new')}
          className="w-full sm:w-auto px-4 py-2 rounded font-medium text-white min-h-[44px] sm:min-h-0"
          style={{ backgroundColor: 'var(--accent)' }}
        >
          New Project
        </button>
      </div>

      {projects.length === 0 ? (
        <div className="text-center py-12" style={{ color: 'var(--text-secondary)' }}>
          <p className="text-lg mb-2">No projects yet</p>
          <p className="text-sm">Create your first project to get started.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {projects.map(project => (
            <a
              key={project.id}
              href={`/projects/${project.id}`}
              onClick={e => { e.preventDefault(); onNavigate(`/projects/${project.id}`) }}
              className="block p-4 rounded-lg border transition-colors"
              style={{
                backgroundColor: 'var(--bg-surface)',
                borderColor: 'var(--border-color)',
              }}
            >
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-semibold text-lg">{project.name}</h3>
                <span
                  className="text-xs px-2 py-1 rounded-full font-medium"
                  style={{
                    color: PHASE_COLORS[project.current_phase] || 'var(--text-secondary)',
                    backgroundColor: `color-mix(in srgb, ${PHASE_COLORS[project.current_phase] || 'var(--text-secondary)'} 15%, transparent)`,
                  }}
                >
                  {PHASE_LABELS[project.current_phase] || project.current_phase}
                </span>
              </div>
              {project.description && (
                <p className="text-sm line-clamp-2" style={{ color: 'var(--text-secondary)' }}>
                  {project.description}
                </p>
              )}
            </a>
          ))}
        </div>
      )}
    </div>
  )
}
