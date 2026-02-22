import type { JobResponse } from '../types'

class ApiClient {
  private baseUrl = ''

  getToken(): string | null {
    return localStorage.getItem('token')
  }

  setToken(token: string) {
    localStorage.setItem('token', token)
  }

  clearToken() {
    localStorage.removeItem('token')
  }

  isAuthenticated(): boolean {
    return this.getToken() !== null
  }

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    const token = this.getToken()
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const res = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    })

    if (res.status === 401) {
      this.clearToken()
      throw new Error('Unauthorized')
    }

    if (!res.ok) {
      throw new Error(`API error: ${res.status}`)
    }

    if (res.status === 204) return undefined as T
    return res.json()
  }

  get<T>(path: string) { return this.request<T>('GET', path) }
  post<T>(path: string, body: unknown) { return this.request<T>('POST', path, body) }
  put<T>(path: string, body: unknown) { return this.request<T>('PUT', path, body) }
  patch<T>(path: string, body: unknown) { return this.request<T>('PATCH', path, body) }
  delete<T>(path: string) { return this.request<T>('DELETE', path) }

  /** Dispatch a message to the agent worker. Returns immediately with a job_id. */
  sendMessage(projectId: string, content: string): Promise<JobResponse> {
    return this.post<JobResponse>(`/api/projects/${projectId}/messages`, { content })
  }

  /** Connect to the SSE stream for a job. Returns a cleanup function. */
  streamJob(
    jobId: string,
    callbacks: {
      onThinking?: (iteration: number) => void
      onToolCall?: (tool: string, inputSummary: string) => void
      onToolResult?: (tool: string, summary: string) => void
      onComplete?: (text: string, conversationId: string) => void
      onError?: (message: string) => void
    }
  ): () => void {
    const token = this.getToken()
    if (!token) {
      callbacks.onError?.('Not authenticated')
      return () => {}
    }

    const url = `${this.baseUrl}/api/jobs/${jobId}/stream?token=${encodeURIComponent(token)}`
    const eventSource = new EventSource(url)

    eventSource.addEventListener('thinking', (e) => {
      const data = JSON.parse(e.data)
      callbacks.onThinking?.(data.iteration)
    })

    eventSource.addEventListener('tool_call', (e) => {
      const data = JSON.parse(e.data)
      callbacks.onToolCall?.(data.tool, data.input_summary)
    })

    eventSource.addEventListener('tool_result', (e) => {
      const data = JSON.parse(e.data)
      callbacks.onToolResult?.(data.tool, data.summary)
    })

    eventSource.addEventListener('complete', (e) => {
      const data = JSON.parse(e.data)
      callbacks.onComplete?.(data.text, data.conversation_id)
      eventSource.close()
    })

    eventSource.addEventListener('error', (e) => {
      // SSE error event can be a MessageEvent (server-sent) or a generic Event (connection error)
      if (e instanceof MessageEvent && e.data) {
        const data = JSON.parse(e.data)
        callbacks.onError?.(data.message)
      } else {
        callbacks.onError?.('Connection lost')
      }
      eventSource.close()
    })

    return () => eventSource.close()
  }

  async upload<T>(path: string, file: File): Promise<T> {
    const formData = new FormData()
    formData.append('file', file)

    const headers: Record<string, string> = {}
    const token = this.getToken()
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const res = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers,
      body: formData,
    })

    if (res.status === 401) {
      this.clearToken()
      throw new Error('Unauthorized')
    }

    if (!res.ok) {
      if (res.status === 413) throw new Error('File too large (10 MB limit)')
      throw new Error(`API error: ${res.status}`)
    }

    return res.json()
  }

  async downloadBlob(path: string): Promise<Blob> {
    const headers: Record<string, string> = {}
    const token = this.getToken()
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const res = await fetch(`${this.baseUrl}${path}`, { headers })

    if (res.status === 401) {
      this.clearToken()
      throw new Error('Unauthorized')
    }

    if (!res.ok) throw new Error(`API error: ${res.status}`)
    return res.blob()
  }
}

export const api = new ApiClient()
