import { useState } from 'react'
import { api } from '../../api/client'
import type { Artifact } from '../../types'
import MarkdownContent from '../shared/MarkdownContent'

interface ArtifactViewerProps {
  artifact: Artifact
}

const TYPE_LABELS: Record<string, string> = {
  problem_statement: 'Problem Statement',
  requirements_doc: 'Requirements Document',
  build_plan: 'Build Plan',
  architecture_doc: 'Architecture Document',
  diagram: 'Diagram',
  spec: 'Specification',
  upload: 'Uploaded File',
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function ArtifactViewer({ artifact }: ArtifactViewerProps) {
  const [downloading, setDownloading] = useState(false)
  const [downloadingMd, setDownloadingMd] = useState(false)

  const handleDownload = async () => {
    setDownloading(true)
    try {
      const blob = await api.downloadBlob(
        `/api/projects/${artifact.project_id}/artifacts/${artifact.id}/download`
      )
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = artifact.file_name || 'download'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch {
      // silently fail
    } finally {
      setDownloading(false)
    }
  }

  const handleDownloadMarkdown = async () => {
    setDownloadingMd(true)
    try {
      const blob = await api.downloadBlob(
        `/api/projects/${artifact.project_id}/artifacts/${artifact.id}/download/markdown`
      )
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${artifact.title.toLowerCase().replace(/\s+/g, '-')}.md`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch {
      // silently fail
    } finally {
      setDownloadingMd(false)
    }
  }

  const showMarkdownDownload = artifact.artifact_type !== 'upload' && artifact.content

  return (
    <div>
      <div className="mb-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold">{artifact.title}</h2>
            <div className="flex gap-3 mt-1 text-xs" style={{ color: 'var(--text-secondary)' }}>
              <span>{TYPE_LABELS[artifact.artifact_type] || artifact.artifact_type}</span>
              <span>v{artifact.version}</span>
              <span>Phase: {artifact.phase}</span>
              <span>By: {artifact.created_by}</span>
            </div>
          </div>
          {showMarkdownDownload && (
            <button
              onClick={handleDownloadMarkdown}
              disabled={downloadingMd}
              className="flex items-center gap-2 px-3 py-1.5 rounded text-sm font-medium border shrink-0"
              style={{
                borderColor: 'var(--border-color)',
                color: downloadingMd ? 'var(--text-muted)' : 'var(--text-primary)',
              }}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              {downloadingMd ? 'Downloading...' : 'Download .md'}
            </button>
          )}
        </div>
      </div>

      {artifact.artifact_type === 'upload' ? (
        <div
          className="p-6 rounded-lg border"
          style={{
            backgroundColor: 'var(--bg-surface)',
            borderColor: 'var(--border-color)',
          }}
        >
          <div className="flex items-center gap-4">
            <div
              className="w-12 h-12 rounded-lg flex items-center justify-center text-lg"
              style={{ backgroundColor: 'var(--bg-tertiary)' }}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
                <polyline points="13 2 13 9 20 9" />
              </svg>
            </div>
            <div className="flex-1">
              <p className="font-medium">{artifact.file_name}</p>
              <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>
                {artifact.content_type}
                {artifact.file_size != null && ` \u00b7 ${formatFileSize(artifact.file_size)}`}
              </p>
            </div>
            <button
              onClick={handleDownload}
              disabled={downloading}
              className="px-4 py-2 rounded font-medium text-white"
              style={{ backgroundColor: downloading ? 'var(--text-muted)' : 'var(--accent)' }}
            >
              {downloading ? 'Downloading...' : 'Download'}
            </button>
          </div>
        </div>
      ) : (
        <div
          className="p-4 rounded-lg border"
          style={{
            backgroundColor: 'var(--bg-surface)',
            borderColor: 'var(--border-color)',
          }}
        >
          <MarkdownContent content={artifact.content} />
        </div>
      )}
    </div>
  )
}
