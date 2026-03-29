export interface User {
  id: string
  email: string
  username: string
  role: string
  created_at: string
}

export interface Session {
  id: string
  name: string
  created_at: string
  updated_at: string
}

export interface Message {
  id: string
  session_id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface Document {
  id: string
  session_id: string
  content: string
  version: number
  created_at: string
}

export type WebSocketMessage =
  | { type: 'message_saved'; message: Message }
  | { type: 'thinking' }
  | { type: 'assistant_message'; message: Message }
  | { type: 'document_update'; document: Document }
  | { type: 'error'; message: string }
