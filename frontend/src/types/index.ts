export interface User {
  id: string
  email: string
  username: string
  role: string
  created_at: string
}

export interface Project {
  id: string
  name: string
  description: string | null
  current_phase: ProjectPhase
  phase_history: PhaseHistoryEntry[]
  github_repo_url: string | null
  created_at: string
  updated_at: string
}

export type ProjectPhase =
  | 'intake'
  | 'requirements'
  | 'architecture'
  | 'build'
  | 'deploy'
  | 'handoff'
  | 'complete'

export interface PhaseHistoryEntry {
  phase: ProjectPhase
  entered_at: string
  completed_at: string | null
}

export interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

export interface Conversation {
  id: string
  project_id: string
  phase: ProjectPhase
  messages: Message[]
  summary: string | null
  created_at: string
  updated_at: string
}

export interface Artifact {
  id: string
  project_id: string
  phase: ProjectPhase
  artifact_type: ArtifactType
  title: string
  content: string
  version: number
  created_by: string
  created_at: string
  updated_at: string
}

export type ArtifactType =
  | 'problem_statement'
  | 'requirements_doc'
  | 'user_stories'
  | 'architecture_doc'
  | 'diagram'
  | 'spec'
