import type { Artifact } from '../../types'

interface ArtifactViewerProps {
  artifact: Artifact
}

const TYPE_LABELS: Record<string, string> = {
  problem_statement: 'Problem Statement',
  requirements_doc: 'Requirements Document',
  user_stories: 'User Stories',
  architecture_doc: 'Architecture Document',
  diagram: 'Diagram',
  spec: 'Specification',
}

export default function ArtifactViewer({ artifact }: ArtifactViewerProps) {
  return (
    <div>
      <div className="mb-4">
        <h2 className="text-xl font-bold">{artifact.title}</h2>
        <div className="flex gap-3 mt-1 text-xs" style={{ color: 'var(--text-secondary)' }}>
          <span>{TYPE_LABELS[artifact.artifact_type] || artifact.artifact_type}</span>
          <span>v{artifact.version}</span>
          <span>Phase: {artifact.phase}</span>
          <span>By: {artifact.created_by}</span>
        </div>
      </div>
      <div
        className="p-4 rounded-lg border prose prose-invert max-w-none"
        style={{
          backgroundColor: 'var(--bg-surface)',
          borderColor: 'var(--border-color)',
          whiteSpace: 'pre-wrap',
          fontFamily: 'inherit',
          lineHeight: '1.7',
        }}
      >
        {artifact.content}
      </div>
    </div>
  )
}
