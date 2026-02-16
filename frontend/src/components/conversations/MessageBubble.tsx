import type { Message } from '../../types'

interface MessageBubbleProps {
  message: Message
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] sm:max-w-[70%] px-4 py-3 rounded-lg text-sm whitespace-pre-wrap`}
        style={{
          backgroundColor: isUser ? 'var(--accent)' : 'var(--bg-surface)',
          color: isUser ? 'white' : 'var(--text-primary)',
        }}
      >
        {message.content}
      </div>
    </div>
  )
}
