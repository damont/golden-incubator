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
  delete<T>(path: string) { return this.request<T>('DELETE', path) }
}

export const api = new ApiClient()
