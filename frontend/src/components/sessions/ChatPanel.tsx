import { useState, useRef, useEffect } from 'react'
import type { Message } from '../../types'
import MarkdownContent from '../shared/MarkdownContent'

interface ChatPanelProps {
  messages: Message[]
  isThinking: boolean
  onSendMessage: (content: string) => void
}

export default function ChatPanel({ messages, isThinking, onSendMessage }: ChatPanelProps) {
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isThinking])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const text = input.trim()
    if (!text || isThinking) return
    onSendMessage(text)
    setInput('')
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && !isThinking && (
          <div className="flex items-center justify-center h-full">
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              Start by describing what you want to build.
            </p>
          </div>
        )}

        {messages.map(msg => {
          const isUser = msg.role === 'user'
          return (
            <div key={msg.id} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
              <div
                className="max-w-[85%] px-4 py-3 rounded-lg text-sm"
                style={{
                  backgroundColor: isUser ? 'var(--accent)' : 'var(--bg-surface)',
                  color: isUser ? 'white' : 'var(--text-primary)',
                }}
              >
                {isUser ? (
                  <span className="whitespace-pre-wrap">{msg.content}</span>
                ) : (
                  <MarkdownContent content={msg.content} />
                )}
              </div>
            </div>
          )
        })}

        {isThinking && (
          <div className="flex justify-start">
            <div
              className="px-4 py-3 rounded-lg text-sm"
              style={{ backgroundColor: 'var(--bg-surface)', color: 'var(--text-secondary)' }}
            >
              <span className="animate-pulse">Thinking...</span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="p-4 border-t"
        style={{ borderColor: 'var(--border-color)' }}
      >
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe what you want to build..."
            rows={2}
            className="flex-1 px-3 py-2 rounded-lg text-sm resize-none"
            style={{
              backgroundColor: 'var(--bg-surface)',
              border: '1px solid var(--border-color)',
              color: 'var(--text-primary)',
            }}
          />
          <button
            type="submit"
            disabled={isThinking || !input.trim()}
            className="self-end px-4 py-2 rounded-lg text-sm font-medium"
            style={{
              backgroundColor: 'var(--accent)',
              color: 'white',
              opacity: isThinking || !input.trim() ? 0.5 : 1,
            }}
          >
            Send
          </button>
        </div>
      </form>
    </div>
  )
}
