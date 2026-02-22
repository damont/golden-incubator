import { useEffect, useRef, useState } from 'react'
import mermaid from 'mermaid'

let mermaidInitialized = false

function ensureMermaidInit() {
  if (mermaidInitialized) return
  mermaid.initialize({
    startOnLoad: false,
    theme: 'dark',
    themeVariables: {
      primaryColor: '#6c8aec',
      primaryTextColor: '#e4e4e8',
      primaryBorderColor: '#2e2e3a',
      lineColor: '#9898a4',
      secondaryColor: '#24242e',
      tertiaryColor: '#1a1a22',
      background: '#1a1a22',
      mainBkg: '#24242e',
      nodeBorder: '#2e2e3a',
      clusterBkg: '#1a1a22',
      titleColor: '#e4e4e8',
      edgeLabelBackground: '#1a1a22',
    },
  })
  mermaidInitialized = true
}

let idCounter = 0

interface MermaidDiagramProps {
  source: string
}

export default function MermaidDiagram({ source }: MermaidDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [error, setError] = useState<string | null>(null)
  const [showSource, setShowSource] = useState(false)

  useEffect(() => {
    let cancelled = false

    async function render() {
      ensureMermaidInit()
      const id = `mermaid-${++idCounter}`
      try {
        const { svg } = await mermaid.render(id, source.trim())
        if (!cancelled && containerRef.current) {
          containerRef.current.innerHTML = svg
          setError(null)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to render diagram')
        }
        // mermaid.render creates a temp element on failure — clean it up
        document.getElementById('d' + id)?.remove()
      }
    }

    render()
    return () => { cancelled = true }
  }, [source])

  if (error) {
    return (
      <div
        className="rounded-lg border p-4 my-3 text-sm"
        style={{ backgroundColor: 'var(--bg-raised)', borderColor: 'var(--border-color)' }}
      >
        <div className="flex items-center gap-2 mb-2" style={{ color: 'var(--danger)' }}>
          <span>Diagram render error</span>
        </div>
        <button
          onClick={() => setShowSource(!showSource)}
          className="text-xs underline mb-2"
          style={{ color: 'var(--accent)' }}
        >
          {showSource ? 'Hide source' : 'Show source'}
        </button>
        {showSource && (
          <pre
            className="rounded p-3 overflow-x-auto text-xs"
            style={{ backgroundColor: 'var(--bg-surface)', color: 'var(--text-secondary)' }}
          >
            <code>{source}</code>
          </pre>
        )}
      </div>
    )
  }

  return (
    <div
      ref={containerRef}
      className="my-3 flex justify-center [&_svg]:max-w-full"
    />
  )
}
