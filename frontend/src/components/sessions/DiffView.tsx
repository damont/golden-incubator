import { useMemo } from 'react'
import { diffWords } from 'diff'

interface DiffViewProps {
  oldContent: string
  newContent: string
}

export default function DiffView({ oldContent, newContent }: DiffViewProps) {
  const parts = useMemo(() => diffWords(oldContent, newContent), [oldContent, newContent])

  return (
    <pre className="whitespace-pre-wrap text-sm leading-relaxed font-sans" style={{ color: 'var(--text-primary)' }}>
      {parts.map((part, i) => {
        if (part.added) {
          return (
            <span key={i} className="diff-added">
              {part.value}
            </span>
          )
        }
        if (part.removed) {
          return (
            <span key={i} className="diff-removed">
              {part.value}
            </span>
          )
        }
        return <span key={i}>{part.value}</span>
      })}
    </pre>
  )
}
