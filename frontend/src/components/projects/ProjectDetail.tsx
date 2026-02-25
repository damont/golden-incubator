import { useState, useEffect } from 'react'
import { api } from '../../api/client'
import type { Conversation, Project, ProjectPhase } from '../../types'
import ChatView from '../conversations/ChatView'
import ArtifactList from '../artifacts/ArtifactList'
import ProgressSidebar from '../progress/ProgressSidebar'
import EntityList from '../entities/EntityList'

interface ProjectDetailProps {
  projectId: string
  onNavigate: (path: string) => void
}

const PHASE_LABELS: Record<string, string> = {
  discovery: 'Discovery',
  domain_design: 'Domain Design',
  build: 'Build',
  deploy: 'Deploy',
  handoff: 'Handoff',
  complete: 'Complete',
  // Legacy mappings
  intake: 'Discovery',
  requirements: 'Discovery',
  architecture: 'Domain Design',
}

// Canonical phase order for the chat tabs
const CHAT_PHASES: { value: ProjectPhase; label: string }[] = [
  { value: 'discovery', label: 'Discovery' },
  { value: 'domain_design', label: 'Domain Design' },
  { value: 'build', label: 'Build' },
  { value: 'deploy', label: 'Deploy' },
  { value: 'handoff', label: 'Handoff' },
]

// Map legacy phases to their canonical replacement
function canonicalPhase(phase: ProjectPhase): ProjectPhase {
  if (phase === 'intake' || phase === 'requirements') return 'discovery'
  if (phase === 'architecture') return 'domain_design'
  return phase
}

type Tab = 'chat' | 'artifacts' | 'entities'

export default function ProjectDetail({ projectId, onNavigate }: ProjectDetailProps) {
  const [project, setProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<Tab>('chat')
  const [sidebarRefreshKey, setSidebarRefreshKey] = useState(0)
  const [chatPhase, setChatPhase] = useState<ProjectPhase | null>(null)
  const [phasesWithConversations, setPhasesWithConversations] = useState<Set<ProjectPhase>>(new Set())

  const loadProject = () => {
    api.get<Project>(`/api/projects/${projectId}`)
      .then(p => {
        setProject(p)
        // Default chatPhase to the project's current phase
        setChatPhase(prev => prev || canonicalPhase(p.current_phase))
      })
      .catch(() => onNavigate('/projects'))
      .finally(() => setLoading(false))
  }

  const loadConversationPhases = () => {
    api.get<Conversation[]>(`/api/projects/${projectId}/conversations`)
      .then(conversations => {
        const phases = new Set<ProjectPhase>(
          conversations.map(c => canonicalPhase(c.phase))
        )
        setPhasesWithConversations(phases)
      })
      .catch(() => {})
  }

  useEffect(() => {
    loadProject()
    loadConversationPhases()
  }, [projectId])

  const handleMessageSent = () => {
    setSidebarRefreshKey(k => k + 1)
    loadProject()
    loadConversationPhases()
  }

  if (loading || !project) {
    return <p style={{ color: 'var(--text-secondary)' }}>Loading...</p>
  }

  const currentCanonicalPhase = canonicalPhase(project.current_phase)
  const effectiveChatPhase = chatPhase || currentCanonicalPhase

  // Determine which phase tabs to show: phases up to and including current
  const currentPhaseIndex = CHAT_PHASES.findIndex(p => p.value === currentCanonicalPhase)
  const visiblePhases = CHAT_PHASES.slice(0, currentPhaseIndex + 1)

  return (
    <div className="flex flex-1 min-h-0 h-full overflow-hidden">
      {/* Progress Sidebar */}
      <ProgressSidebar
        projectId={projectId}
        refreshKey={sidebarRefreshKey}
        onPhaseClick={(phase) => {
          const canonical = canonicalPhase(phase as ProjectPhase)
          setChatPhase(canonical)
          setActiveTab('chat')
        }}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0 min-h-0 p-6 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between gap-2 mb-4">
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

        {/* Tabs */}
        <div className="flex gap-1 mb-4">
          {(['chat', 'entities', 'artifacts'] as Tab[]).map(tab => (
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
              {tab === 'entities' ? 'Requirements & Items' : tab}
            </button>
          ))}
        </div>

        {/* Phase Chat Tabs (only visible when chat tab is active) */}
        {activeTab === 'chat' && visiblePhases.length > 1 && (
          <div className="flex gap-1 mb-3">
            {visiblePhases.map(p => {
              const isActive = effectiveChatPhase === p.value
              const hasConversation = phasesWithConversations.has(p.value)
              const isCurrent = p.value === currentCanonicalPhase

              return (
                <button
                  key={p.value}
                  onClick={() => setChatPhase(p.value)}
                  className="px-3 py-1 rounded-full text-xs font-medium"
                  style={{
                    backgroundColor: isActive ? 'var(--accent)' : 'var(--bg-surface)',
                    color: isActive ? 'white' : hasConversation ? 'var(--text-primary)' : 'var(--text-muted)',
                    border: `1px solid ${isActive ? 'var(--accent)' : 'var(--border-color)'}`,
                    opacity: hasConversation || isCurrent ? 1 : 0.6,
                  }}
                >
                  {p.label}
                </button>
              )
            })}
          </div>
        )}

        {/* Tab Content */}
        <div className="flex-1 min-h-0 overflow-y-auto">
          {activeTab === 'chat' && (
            <ChatView
              projectId={projectId}
              phase={effectiveChatPhase}
              isCurrentPhase={effectiveChatPhase === currentCanonicalPhase}
              onMessageSent={handleMessageSent}
            />
          )}
          {activeTab === 'entities' && (
            <EntityList projectId={projectId} />
          )}
          {activeTab === 'artifacts' && (
            <ArtifactList projectId={projectId} />
          )}
        </div>
      </div>
    </div>
  )
}
