import { useState, useEffect, useRef } from 'react'
import { api } from '../api/client'

export type AgentStatus = 'idle' | 'thinking' | 'generating' | 'tool_call' | 'tool_result' | 'complete' | 'error'

interface AgentStreamState {
  status: AgentStatus
  currentTool: string | null
  toolSummary: string | null
  generatingDetail: string | null
  iteration: number
  assistantText: string | null
  conversationId: string | null
  error: string | null
  isComplete: boolean
}

const initialState: AgentStreamState = {
  status: 'idle',
  currentTool: null,
  toolSummary: null,
  generatingDetail: null,
  iteration: 0,
  assistantText: null,
  conversationId: null,
  error: null,
  isComplete: false,
}

export function useAgentStream(jobId: string | null): AgentStreamState {
  const [state, setState] = useState<AgentStreamState>(initialState)
  const cleanupRef = useRef<(() => void) | null>(null)

  useEffect(() => {
    if (!jobId) {
      setState(initialState)
      return
    }

    setState({ ...initialState, status: 'thinking', iteration: 1 })

    const cleanup = api.streamJob(jobId, {
      onThinking: (iteration) => {
        setState(prev => ({
          ...prev,
          status: 'thinking',
          iteration,
          currentTool: null,
          toolSummary: null,
          generatingDetail: null,
        }))
      },
      onGenerating: (detail) => {
        setState(prev => ({
          ...prev,
          status: 'generating',
          generatingDetail: detail,
        }))
      },
      onToolCall: (tool, inputSummary) => {
        setState(prev => ({
          ...prev,
          status: 'tool_call',
          currentTool: tool,
          toolSummary: inputSummary,
        }))
      },
      onToolResult: (tool, summary) => {
        setState(prev => ({
          ...prev,
          status: 'tool_result',
          currentTool: tool,
          toolSummary: summary,
        }))
      },
      onComplete: (text, conversationId) => {
        setState(prev => ({
          ...prev,
          status: 'complete',
          assistantText: text,
          conversationId,
          isComplete: true,
          currentTool: null,
          toolSummary: null,
        }))
      },
      onError: (message) => {
        setState(prev => ({
          ...prev,
          status: 'error',
          error: message,
          isComplete: true,
        }))
      },
    })

    cleanupRef.current = cleanup

    return () => {
      cleanup()
      cleanupRef.current = null
    }
  }, [jobId])

  return state
}
