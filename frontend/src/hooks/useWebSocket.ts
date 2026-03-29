import { useEffect, useRef, useState, useCallback } from 'react'
import type { Message, Document, WebSocketMessage } from '../types'

interface UseWebSocketOptions {
  sessionId: string | null
  token: string | null
  onMessage?: (msg: Message) => void
  onAssistantMessage?: (msg: Message) => void
  onDocumentUpdate?: (doc: Document) => void
  onError?: (error: string) => void
}

export function useWebSocket({
  sessionId,
  token,
  onMessage,
  onAssistantMessage,
  onDocumentUpdate,
  onError,
}: UseWebSocketOptions) {
  const [isConnected, setIsConnected] = useState(false)
  const [isThinking, setIsThinking] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const callbacksRef = useRef({ onMessage, onAssistantMessage, onDocumentUpdate, onError })

  // Keep callbacks fresh without reconnecting
  callbacksRef.current = { onMessage, onAssistantMessage, onDocumentUpdate, onError }

  useEffect(() => {
    if (!sessionId || !token) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const url = `${protocol}//${host}/api/sessions/${sessionId}/ws?token=${encodeURIComponent(token)}`

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => setIsConnected(true)

    ws.onclose = () => {
      setIsConnected(false)
      setIsThinking(false)
    }

    ws.onerror = () => {
      callbacksRef.current.onError?.('WebSocket connection error')
    }

    ws.onmessage = (event) => {
      const data: WebSocketMessage = JSON.parse(event.data)

      switch (data.type) {
        case 'message_saved':
          callbacksRef.current.onMessage?.(data.message)
          break
        case 'thinking':
          setIsThinking(true)
          break
        case 'assistant_message':
          setIsThinking(false)
          callbacksRef.current.onAssistantMessage?.(data.message)
          break
        case 'document_update':
          callbacksRef.current.onDocumentUpdate?.(data.document)
          break
        case 'error':
          setIsThinking(false)
          callbacksRef.current.onError?.(data.message)
          break
      }
    }

    return () => {
      ws.close()
      wsRef.current = null
    }
  }, [sessionId, token])

  const sendMessage = useCallback((content: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'message', content }))
    }
  }, [])

  return { isConnected, isThinking, sendMessage }
}
