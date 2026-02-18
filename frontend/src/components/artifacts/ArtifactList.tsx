import { useState, useEffect } from 'react'
import { api } from '../../api/client'
import type { Artifact } from '../../types'
import ArtifactViewer from './ArtifactViewer'

interface ArtifactListProps {
  projectId: string
}

const TYPE_LABELS: Record<string, string> = {
  problem_statement: 'Problem Statement',
  requirements_doc: 'Requirements Document',
  user_stories: 'User Stories',
  architecture_doc: 'Architecture Document',
  diagram: 'Diagram',
  spec: 'Specification',
  upload: 'Uploaded File',
}

export default function ArtifactList({ projectId }: ArtifactListProps) {
  const [artifacts, setArtifacts] = useState<Artifact[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  useEffect(() => {
    api.get<Artifact[]>(`/api/projects/${projectId}/artifacts`)
      .then(setArtifacts)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [projectId])

  const selected = artifacts.find(a => a.id === selectedId)

  if (loading) {
    return <p style={{ color: 'var(--text-secondary)' }}>Loading artifacts...</p>
  }

  if (selected) {
    return (
      <div>
        <button
          onClick={() => setSelectedId(null)}
          className="text-sm mb-4"
          style={{ color: 'var(--accent)' }}
        >
          &larr; Back to artifacts
        </button>
        <ArtifactViewer artifact={selected} />
      </div>
    )
  }

  return (
    <div>
      {artifacts.length === 0 ? (
        <div className="text-center py-8" style={{ color: 'var(--text-secondary)' }}>
          <p className="text-lg mb-2">No artifacts yet</p>
          <p className="text-sm">Artifacts will be created as you progress through conversations with the AI.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {artifacts.map(artifact => (
            <button
              key={artifact.id}
              onClick={() => setSelectedId(artifact.id)}
              className="w-full text-left p-4 rounded-lg border transition-colors"
              style={{
                backgroundColor: 'var(--bg-surface)',
                borderColor: 'var(--border-color)',
              }}
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-medium">{artifact.title}</h3>
                  <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>
                    {TYPE_LABELS[artifact.artifact_type] || artifact.artifact_type}
                    {' '}&middot;{' '}
                    v{artifact.version}
                    {' '}&middot;{' '}
                    {artifact.phase}
                  </p>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
