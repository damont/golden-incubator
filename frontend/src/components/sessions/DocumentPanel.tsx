import { useState, useEffect, useRef } from 'react'
import MarkdownContent from '../shared/MarkdownContent'
import DiffView from './DiffView'

interface DocumentPanelProps {
  content: string
  previousContent: string | null
  onExport: () => void
}

export default function DocumentPanel({ content, previousContent, onExport }: DocumentPanelProps) {
  const [showDiff, setShowDiff] = useState(false)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // When content changes and there's a previous version, show diff temporarily
  useEffect(() => {
    if (previousContent !== null && previousContent !== content) {
      setShowDiff(true)

      // Clear any existing timer
      if (timerRef.current) clearTimeout(timerRef.current)

      // Auto-fade back to clean view after 8 seconds
      timerRef.current = setTimeout(() => setShowDiff(false), 8000)
    }

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [content, previousContent])

  const hasDiff = previousContent !== null && previousContent !== content

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b"
        style={{ borderColor: 'var(--border-color)' }}
      >
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold" style={{ color: 'var(--text-secondary)' }}>
            Requirements Document
          </h2>
          {hasDiff && (
            <button
              onClick={() => setShowDiff(!showDiff)}
              className="text-xs px-2 py-0.5 rounded"
              style={{
                backgroundColor: showDiff ? 'rgba(108, 138, 236, 0.2)' : 'var(--bg-raised)',
                border: '1px solid var(--border-color)',
                color: showDiff ? 'var(--accent)' : 'var(--text-secondary)',
              }}
            >
              {showDiff ? 'Changes' : 'Show changes'}
            </button>
          )}
        </div>
        <button
          onClick={onExport}
          className="text-xs px-3 py-1 rounded"
          style={{
            backgroundColor: 'var(--bg-raised)',
            border: '1px solid var(--border-color)',
            color: 'var(--text-primary)',
          }}
        >
          Export .md
        </button>
      </div>

      {/* Document content */}
      <div className="flex-1 overflow-y-auto p-6">
        {showDiff && previousContent !== null ? (
          <DiffView oldContent={previousContent} newContent={content} />
        ) : (
          <MarkdownContent content={content} />
        )}
      </div>
    </div>
  )
}
