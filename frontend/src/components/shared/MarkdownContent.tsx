import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import MermaidDiagram from './MermaidDiagram'
import type { Components } from 'react-markdown'

interface MarkdownContentProps {
  content: string
}

const components: Components = {
  pre({ children }) {
    return <>{children}</>
  },

  code({ className, children }) {
    const match = /language-(\w+)/.exec(className || '')
    const lang = match?.[1]
    const text = String(children).replace(/\n$/, '')
    const isBlock = lang || text.includes('\n')

    // Detect mermaid blocks
    if (lang === 'mermaid') {
      return <MermaidDiagram source={text} />
    }

    // Fenced / multi-line code block
    if (isBlock) {
      return (
        <pre
          className="rounded-lg p-4 my-3 overflow-x-auto text-sm"
          style={{ backgroundColor: 'var(--bg-raised)', border: '1px solid var(--border-color)' }}
        >
          <code className={className} style={{ color: 'var(--text-primary)' }}>
            {text}
          </code>
        </pre>
      )
    }

    // Inline code
    return (
      <code
        className="rounded px-1.5 py-0.5 text-sm"
        style={{ backgroundColor: 'var(--bg-raised)', color: 'var(--accent)' }}
      >
        {children}
      </code>
    )
  },

  a({ href, children }) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        style={{ color: 'var(--accent)' }}
        className="underline hover:opacity-80"
      >
        {children}
      </a>
    )
  },

  table({ children }) {
    return (
      <div className="overflow-x-auto my-3">
        <table
          className="w-full text-sm border-collapse"
          style={{ borderColor: 'var(--border-color)' }}
        >
          {children}
        </table>
      </div>
    )
  },

  th({ children }) {
    return (
      <th
        className="text-left px-3 py-2 font-semibold border-b"
        style={{
          borderColor: 'var(--border-color)',
          backgroundColor: 'var(--bg-raised)',
          color: 'var(--text-primary)',
        }}
      >
        {children}
      </th>
    )
  },

  td({ children }) {
    return (
      <td
        className="px-3 py-2 border-b"
        style={{ borderColor: 'var(--border-color)' }}
      >
        {children}
      </td>
    )
  },
}

export default function MarkdownContent({ content }: MarkdownContentProps) {
  return (
    <div className="markdown-content">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  )
}
