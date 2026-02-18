import { useState, useEffect } from 'react'
import { api } from '../../api/client'
import type { ProgressResponse, PhaseInfo } from '../../types'

interface ProgressSidebarProps {
  projectId: string
  refreshKey?: number
  onPhaseClick?: (phase: string) => void
}

export default function ProgressSidebar({ projectId, refreshKey, onPhaseClick }: ProgressSidebarProps) {
  const [progress, setProgress] = useState<ProgressResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<string | null>(null)

  useEffect(() => {
    loadProgress()
  }, [projectId, refreshKey])

  const loadProgress = async () => {
    try {
      const data = await api.get<ProgressResponse>(`/api/projects/${projectId}/progress`)
      setProgress(data)
      // Auto-expand current phase
      setExpanded(data.current_phase)
    } catch (err) {
      console.error('Failed to load progress', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="w-72 p-4" style={{ backgroundColor: 'var(--bg-surface)' }}>
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-gray-700 rounded w-3/4"></div>
          <div className="h-2 bg-gray-700 rounded w-full"></div>
          <div className="space-y-2 mt-4">
            {[1, 2, 3, 4, 5, 6].map(i => (
              <div key={i} className="h-8 bg-gray-700 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (!progress) {
    return null
  }

  return (
    <div
      className="w-72 shrink-0 flex flex-col border-r overflow-hidden"
      style={{
        backgroundColor: 'var(--bg-surface)',
        borderColor: 'var(--border)',
      }}
    >
      {/* Progress Header */}
      <div className="p-4 border-b" style={{ borderColor: 'var(--border)' }}>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
            Progress
          </span>
          <span className="text-sm font-bold" style={{ color: 'var(--accent)' }}>
            {progress.percent_complete}%
          </span>
        </div>
        
        {/* Progress Bar */}
        <div className="h-2 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--bg-primary)' }}>
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${progress.percent_complete}%`,
              backgroundColor: 'var(--accent)',
            }}
          />
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-2 gap-2 mt-3 text-xs">
          <div className="flex items-center gap-1">
            <span style={{ color: 'var(--text-secondary)' }}>📋</span>
            <span style={{ color: 'var(--text-secondary)' }}>
              {progress.confirmed_requirements}/{progress.total_requirements} REQ
            </span>
          </div>
          <div className="flex items-center gap-1">
            <span style={{ color: 'var(--text-secondary)' }}>⏳</span>
            <span style={{ color: progress.pending_instructions > 0 ? 'var(--warning, #f59e0b)' : 'var(--text-secondary)' }}>
              {progress.pending_instructions} pending
            </span>
          </div>
          {progress.open_questions > 0 && (
            <div className="flex items-center gap-1 col-span-2">
              <span>❓</span>
              <span style={{ color: 'var(--warning, #f59e0b)' }}>
                {progress.open_questions} open questions
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Phase List */}
      <div className="flex-1 overflow-y-auto py-2">
        {progress.phases.map((phase) => (
          <PhaseItem
            key={phase.phase}
            phase={phase}
            isExpanded={expanded === phase.phase}
            onToggle={() => {
              setExpanded(expanded === phase.phase ? null : phase.phase)
              onPhaseClick?.(phase.phase)
            }}
          />
        ))}
      </div>
    </div>
  )
}

interface PhaseItemProps {
  phase: PhaseInfo
  isExpanded: boolean
  onToggle: () => void
}

function PhaseItem({ phase, isExpanded, onToggle }: PhaseItemProps) {
  const statusIcon = {
    completed: '✓',
    current: '●',
    upcoming: '○',
  }[phase.status]

  const statusColor = {
    completed: 'var(--success, #22c55e)',
    current: 'var(--accent)',
    upcoming: 'var(--text-secondary)',
  }[phase.status]

  const pendingInstructions = phase.instructions_count - phase.instructions_completed

  return (
    <div className="px-2">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2 px-2 py-2 rounded text-left transition-colors"
        style={{
          backgroundColor: phase.status === 'current' ? 'var(--selected-bg)' : 'transparent',
        }}
      >
        {/* Status Icon */}
        <span
          className="w-5 h-5 flex items-center justify-center text-sm font-bold"
          style={{ color: statusColor }}
        >
          {statusIcon}
        </span>

        {/* Phase Name */}
        <span
          className="flex-1 text-sm font-medium"
          style={{
            color: phase.status === 'upcoming' ? 'var(--text-secondary)' : 'var(--text-primary)',
          }}
        >
          {phase.name}
        </span>

        {/* Badge for pending items */}
        {phase.status !== 'upcoming' && pendingInstructions > 0 && (
          <span
            className="text-xs px-1.5 py-0.5 rounded-full"
            style={{
              backgroundColor: 'var(--warning, #f59e0b)',
              color: 'black',
            }}
          >
            {pendingInstructions}
          </span>
        )}

        {/* Expand Arrow */}
        <span
          className="text-xs transition-transform"
          style={{
            color: 'var(--text-secondary)',
            transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
          }}
        >
          ▶
        </span>
      </button>

      {/* Expanded Details */}
      {isExpanded && (
        <div
          className="ml-7 mb-2 pl-2 border-l text-xs space-y-1"
          style={{ borderColor: 'var(--border)' }}
        >
          <div className="flex justify-between py-1">
            <span style={{ color: 'var(--text-secondary)' }}>Requirements</span>
            <span style={{ color: 'var(--text-primary)' }}>{phase.requirements_count}</span>
          </div>
          <div className="flex justify-between py-1">
            <span style={{ color: 'var(--text-secondary)' }}>Instructions</span>
            <span style={{ color: 'var(--text-primary)' }}>
              {phase.instructions_completed}/{phase.instructions_count}
            </span>
          </div>
          <div className="flex justify-between py-1">
            <span style={{ color: 'var(--text-secondary)' }}>Notes</span>
            <span style={{ color: 'var(--text-primary)' }}>{phase.notes_count}</span>
          </div>
          <div className="flex justify-between py-1">
            <span style={{ color: 'var(--text-secondary)' }}>Artifacts</span>
            <span style={{ color: 'var(--text-primary)' }}>{phase.artifacts_count}</span>
          </div>
          
          {phase.entered_at && (
            <div className="pt-1 mt-1 border-t" style={{ borderColor: 'var(--border)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>
                Started: {new Date(phase.entered_at).toLocaleDateString()}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
