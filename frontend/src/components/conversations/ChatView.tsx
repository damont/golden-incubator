import { useState, useEffect, useRef } from 'react'
import { api } from '../../api/client'
import type { Conversation, Message, ProjectPhase } from '../../types'
import MessageBubble from './MessageBubble'

interface ChatViewProps {
  projectId: string
  phase: ProjectPhase
}

export default function ChatView({ projectId }: ChatViewProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [loadingConv, setLoadingConv] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api.get<Conversation>(`/api/projects/${projectId}/conversations/current`)
      .then(conv => setMessages(conv.messages))
      .catch(() => {})
      .finally(() => setLoadingConv(false))
  }, [projectId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || sending) return
    const userMessage = input.trim()
    setInput('')
    setSending(true)

    const userMsg: Message = {
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString(),
    }
    setMessages(prev => [...prev, userMsg])

    try {
      const response = await api.post<Message>(
        `/api/projects/${projectId}/messages`,
        { content: userMessage }
      )
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: response.content, timestamp: new Date().toISOString() },
      ])
    } catch {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: 'Sorry, something went wrong. Please try again.', timestamp: new Date().toISOString() },
      ])
    } finally {
      setSending(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  if (loadingConv) {
    return <p style={{ color: 'var(--text-secondary)' }}>Loading conversation...</p>
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-2 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-8" style={{ color: 'var(--text-secondary)' }}>
            <p className="text-lg mb-2">Start a conversation</p>
            <p className="text-sm">Tell the AI about your project idea and it will guide you through the process.</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}
        {sending && (
          <div className="flex items-center gap-2 px-4 py-3" style={{ color: 'var(--text-secondary)' }}>
            <span className="animate-pulse">Thinking...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div
        className="border-t p-3 flex gap-2"
        style={{ borderColor: 'var(--border-color)' }}
      >
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message..."
          className="flex-1 px-3 py-2 rounded border bg-transparent resize-none"
          style={{ borderColor: 'var(--border-color)' }}
          rows={1}
          disabled={sending}
        />
        <button
          onClick={handleSend}
          disabled={sending || !input.trim()}
          className="px-4 py-2 rounded font-medium text-white min-h-[44px] sm:min-h-0"
          style={{
            backgroundColor: sending || !input.trim() ? 'var(--text-muted)' : 'var(--accent)',
          }}
        >
          Send
        </button>
      </div>
    </div>
  )
}
