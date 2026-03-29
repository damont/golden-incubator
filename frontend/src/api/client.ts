import type { Session, Message, Document } from '../types'

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
  post<T>(path: string, body?: unknown) { return this.request<T>('POST', path, body) }
  delete<T>(path: string) { return this.request<T>('DELETE', path) }

  // Session endpoints
  createSession(name: string) {
    return this.post<Session>('/api/sessions/', { name })
  }

  listSessions() {
    return this.get<Session[]>('/api/sessions/')
  }

  getSession(id: string) {
    return this.get<Session>(`/api/sessions/${id}`)
  }

  deleteSession(id: string) {
    return this.delete(`/api/sessions/${id}`)
  }

  getMessages(sessionId: string) {
    return this.get<Message[]>(`/api/sessions/${sessionId}/messages`)
  }

  getDocument(sessionId: string) {
    return this.get<Document>(`/api/sessions/${sessionId}/document`)
  }

  async exportDocument(sessionId: string) {
    const headers: Record<string, string> = {}
    const token = this.getToken()
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const res = await fetch(`${this.baseUrl}/api/sessions/${sessionId}/export`, { headers })
    if (!res.ok) throw new Error(`API error: ${res.status}`)

    const blob = await res.blob()
    const disposition = res.headers.get('Content-Disposition')
    const filename = disposition?.match(/filename="(.+)"/)?.[1] || 'requirements.md'

    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }
}

export const api = new ApiClient()
