import { useState, useEffect, useCallback } from 'react'
import { api } from '../../api/client'
import { useWebSocket } from '../../hooks/useWebSocket'
import type { Session, Message, Document } from '../../types'
import ChatPanel from './ChatPanel'
import DocumentPanel from './DocumentPanel'

interface SessionViewProps {
  sessionId: string
  onNavigate: (path: string) => void
}

export default function SessionView({ sessionId, onNavigate }: SessionViewProps) {
  const [session, setSession] = useState<Session | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [document, setDocument] = useState<Document | null>(null)
  const [previousContent, setPreviousContent] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const token = api.getToken()

  // Load session data
  useEffect(() => {
    setLoading(true)
    setError(null)
    Promise.all([
      api.getSession(sessionId),
      api.getMessages(sessionId),
      api.getDocument(sessionId),
    ])
      .then(([s, m, d]) => {
        setSession(s)
        setMessages(m)
        setDocument(d)
      })
      .catch(() => setError('Failed to load session'))
      .finally(() => setLoading(false))
  }, [sessionId])

  const handleMessage = useCallback((msg: Message) => {
    setMessages(prev => [...prev, msg])
  }, [])

  const handleAssistantMessage = useCallback((msg: Message) => {
    setMessages(prev => [...prev, msg])
  }, [])

  const handleDocumentUpdate = useCallback((doc: Document) => {
    setDocument(prev => {
      if (prev) setPreviousContent(prev.content)
      return doc
    })
  }, [])

  const handleError = useCallback((err: string) => {
    setError(err)
  }, [])

  const { isConnected, isThinking, sendMessage } = useWebSocket({
    sessionId: loading ? null : sessionId,
    token,
    onMessage: handleMessage,
    onAssistantMessage: handleAssistantMessage,
    onDocumentUpdate: handleDocumentUpdate,
    onError: handleError,
  })

  const handleExport = () => {
    api.exportDocument(sessionId)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <p style={{ color: 'var(--text-secondary)' }}>Loading session...</p>
      </div>
    )
  }

  if (error && !session) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <p style={{ color: 'var(--danger)' }}>{error}</p>
        <button
          onClick={() => onNavigate('/sessions')}
          className="text-sm px-4 py-2 rounded-lg"
          style={{ backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
        >
          Back to Sessions
        </button>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Session header */}
      <div
        className="flex items-center gap-3 px-4 py-2 border-b"
        style={{ borderColor: 'var(--border-color)', backgroundColor: 'var(--bg-surface)' }}
      >
        <button
          onClick={() => onNavigate('/sessions')}
          className="text-sm"
          style={{ color: 'var(--text-secondary)' }}
        >
          &larr; Back
        </button>
        <h1 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
          {session?.name}
        </h1>
        <span className="text-xs" style={{ color: isConnected ? 'var(--success)' : 'var(--text-muted)' }}>
          {isConnected ? 'Connected' : 'Disconnected'}
        </span>
        {error && (
          <span className="text-xs ml-auto" style={{ color: 'var(--danger)' }}>{error}</span>
        )}
      </div>

      {/* Split screen */}
      <div className="flex flex-1 min-h-0">
        {/* Left: Chat */}
        <div
          className="w-1/2 border-r"
          style={{ borderColor: 'var(--border-color)' }}
        >
          <ChatPanel
            messages={messages}
            isThinking={isThinking}
            onSendMessage={sendMessage}
          />
        </div>

        {/* Right: Document */}
        <div className="w-1/2">
          <DocumentPanel
            content={document?.content || ''}
            previousContent={previousContent}
            onExport={handleExport}
          />
        </div>
      </div>
    </div>
  )
}
