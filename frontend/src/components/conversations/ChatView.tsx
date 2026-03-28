import { useState, useEffect, useRef } from 'react'
import { api } from '../../api/client'
import { useAgentStream } from '../../hooks/useAgentStream'
import type { Artifact, Conversation, Message, ProjectPhase } from '../../types'
import AgentStatus from './AgentStatus'
import MessageBubble from './MessageBubble'

interface ChatViewProps {
  projectId: string
  phase: ProjectPhase
  isCurrentPhase: boolean
  onMessageSent?: () => void
}

export default function ChatView({ projectId, phase, isCurrentPhase, onMessageSent }: ChatViewProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [loadingConv, setLoadingConv] = useState(true)
  const [activeJobId, setActiveJobId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const introRequestedRef = useRef<string | null>(null)

  const agentStream = useAgentStream(activeJobId)

  useEffect(() => {
    setLoadingConv(true)
    // Reset intro guard when phase changes
    introRequestedRef.current = null
    api.get<Conversation[]>(`/api/projects/${projectId}/conversations?phase=${phase}`)
      .then(conversations => {
        const phaseConv = conversations.find(c => c.phase === phase)
        setMessages(phaseConv?.messages || [])
      })
      .catch(() => setMessages([]))
      .finally(() => setLoadingConv(false))
  }, [projectId, phase])

  // Auto-request phase intro when conversation is empty and it's the current phase
  useEffect(() => {
    if (loadingConv || messages.length > 0 || !isCurrentPhase || sending) return
    // Prevent double-triggering for the same phase
    const introKey = `${projectId}:${phase}`
    if (introRequestedRef.current === introKey) return
    introRequestedRef.current = introKey

    api.requestPhaseIntro(projectId)
      .then(result => {
        if (result.job_id) {
          setSending(true)
          setActiveJobId(result.job_id)
        }
      })
      .catch(() => {
        // Silently fail — user can still type manually
      })
  }, [loadingConv, messages.length, isCurrentPhase, sending, projectId, phase])

  // When agent stream completes, add the assistant message
  useEffect(() => {
    if (agentStream.isComplete && agentStream.status === 'complete' && agentStream.assistantText) {
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: agentStream.assistantText!,
          timestamp: new Date().toISOString(),
        },
      ])
      setActiveJobId(null)
      setSending(false)
      onMessageSent?.()
    } else if (agentStream.isComplete && agentStream.status === 'error') {
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, something went wrong. Please try again.',
          timestamp: new Date().toISOString(),
        },
      ])
      setActiveJobId(null)
      setSending(false)
    }
  }, [agentStream.isComplete, agentStream.status, agentStream.assistantText])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, agentStream.status])

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
      const { job_id } = await api.sendMessage(projectId, userMessage)
      setActiveJobId(job_id)
    } catch {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: 'Sorry, something went wrong. Please try again.', timestamp: new Date().toISOString() },
      ])
      setSending(false)
    }
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    try {
      const artifact = await api.upload<Artifact>(
        `/api/projects/${projectId}/artifacts/upload`,
        file
      )
      setMessages(prev => [
        ...prev,
        {
          role: 'user',
          content: `Uploaded file: ${artifact.file_name || file.name}`,
          timestamp: new Date().toISOString(),
        },
      ])
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Upload failed'
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: `Upload failed: ${message}`,
          timestamp: new Date().toISOString(),
        },
      ])
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
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
        {messages.length === 0 && !sending && (
          <div className="text-center py-8" style={{ color: 'var(--text-secondary)' }}>
            {isCurrentPhase ? (
              <p className="text-sm">Preparing phase introduction...</p>
            ) : (
              <p className="text-sm">No conversation for this phase.</p>
            )}
          </div>
        )}
        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}
        {sending && (
          <AgentStatus
            status={agentStream.status}
            currentTool={agentStream.currentTool}
            toolSummary={agentStream.toolSummary}
            generatingDetail={agentStream.generatingDetail}
            iteration={agentStream.iteration}
          />
        )}
        {uploading && (
          <div className="flex items-center gap-2 px-4 py-3" style={{ color: 'var(--text-secondary)' }}>
            <span className="animate-pulse">Uploading...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {isCurrentPhase && (
        <div
          className="border-t p-3 flex gap-2"
          style={{ borderColor: 'var(--border-color)' }}
        >
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            onChange={handleUpload}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading || sending}
            className="px-3 py-2 rounded border font-medium"
            style={{
              borderColor: 'var(--border-color)',
              color: uploading || sending ? 'var(--text-muted)' : 'var(--text-primary)',
            }}
            title="Upload file"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
            </svg>
          </button>
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
            className="px-4 py-2 rounded font-medium text-white"
            style={{
              backgroundColor: sending || !input.trim() ? 'var(--text-muted)' : 'var(--accent)',
            }}
          >
            Send
          </button>
        </div>
      )}
    </div>
  )
}
