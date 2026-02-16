import { useState, useEffect } from 'react'
import { api } from '../../api/client'
import type { Project } from '../../types'
import ChatView from '../conversations/ChatView'
import ArtifactList from '../artifacts/ArtifactList'

interface ProjectDetailProps {
  projectId: string
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

type Tab = 'chat' | 'artifacts'

export default function ProjectDetail({ projectId, onNavigate }: ProjectDetailProps) {
  const [project, setProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<Tab>('chat')

  useEffect(() => {
    api.get<Project>(`/api/projects/${projectId}`)
      .then(setProject)
      .catch(() => onNavigate('/projects'))
      .finally(() => setLoading(false))
  }, [projectId, onNavigate])

  if (loading || !project) {
    return <p style={{ color: 'var(--text-secondary)' }}>Loading...</p>
  }

  return (
    <div className="flex flex-col h-[calc(100vh-73px)]">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => onNavigate('/projects')}
            className="text-sm"
            style={{ color: 'var(--text-secondary)' }}
          >
            &larr; Projects
          </button>
          <h1 className="text-xl font-bold">{project.name}</h1>
          <span
            className="text-xs px-2 py-1 rounded-full"
            style={{ color: 'var(--accent)', backgroundColor: 'var(--selected-bg)' }}
          >
            {PHASE_LABELS[project.current_phase]}
          </span>
        </div>
      </div>

      <div className="flex gap-1 mb-4">
        {(['chat', 'artifacts'] as Tab[]).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className="px-4 py-2 rounded-t text-sm font-medium capitalize"
            style={{
              backgroundColor: activeTab === tab ? 'var(--bg-surface)' : 'transparent',
              color: activeTab === tab ? 'var(--text-primary)' : 'var(--text-secondary)',
              borderBottom: activeTab === tab ? '2px solid var(--accent)' : '2px solid transparent',
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      <div className="flex-1 min-h-0">
        {activeTab === 'chat' && (
          <ChatView projectId={projectId} phase={project.current_phase} />
        )}
        {activeTab === 'artifacts' && (
          <ArtifactList projectId={projectId} />
        )}
      </div>
    </div>
  )
}
