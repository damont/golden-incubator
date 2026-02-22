import type { AgentStatus as AgentStatusType } from '../../hooks/useAgentStream'

interface AgentStatusProps {
  status: AgentStatusType
  currentTool: string | null
  toolSummary: string | null
  iteration: number
}

const TOOL_LABELS: Record<string, string> = {
  save_artifact: 'Saving artifact',
  save_entity: 'Saving entity',
  update_phase: 'Updating phase',
}

export default function AgentStatus({ status, currentTool, iteration }: AgentStatusProps) {
  if (status === 'idle' || status === 'complete') return null

  if (status === 'error') {
    return (
      <div className="flex items-center gap-2 px-4 py-3" style={{ color: 'var(--text-error, #ef4444)' }}>
        <span>Something went wrong. Please try again.</span>
      </div>
    )
  }

  const toolLabel = currentTool ? (TOOL_LABELS[currentTool] || `Running ${currentTool}`) : null

  return (
    <div className="flex items-center gap-2 px-4 py-3" style={{ color: 'var(--text-secondary)' }}>
      <span className="inline-block w-2 h-2 rounded-full animate-pulse" style={{ backgroundColor: 'var(--accent)' }} />
      {status === 'thinking' && (
        <span>Thinking{iteration > 1 ? ` (step ${iteration})` : ''}...</span>
      )}
      {status === 'tool_call' && toolLabel && (
        <span>{toolLabel}...</span>
      )}
      {status === 'tool_result' && toolLabel && (
        <span>{toolLabel} — done</span>
      )}
    </div>
  )
}
