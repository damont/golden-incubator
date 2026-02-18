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
  file_name?: string
  file_size?: number
  content_type?: string
}

export type ArtifactType =
  | 'problem_statement'
  | 'requirements_doc'
  | 'user_stories'
  | 'architecture_doc'
  | 'diagram'
  | 'spec'
  | 'upload'

// ============================================================================
// Progress & Entities
// ============================================================================

export interface PhaseInfo {
  phase: ProjectPhase
  name: string
  description: string
  status: 'completed' | 'current' | 'upcoming'
  entered_at: string | null
  completed_at: string | null
  requirements_count: number
  instructions_count: number
  instructions_completed: number
  notes_count: number
  artifacts_count: number
}

export interface ProgressResponse {
  project_id: string
  project_name: string
  current_phase: ProjectPhase
  current_phase_index: number
  total_phases: number
  percent_complete: number
  phases: PhaseInfo[]
  pending_instructions: number
  open_questions: number
  total_requirements: number
  confirmed_requirements: number
}

export type EntityType =
  | 'REQ'
  | 'INSTR'
  | 'DEC'
  | 'Q'
  | 'ASSUME'
  | 'CONST'
  | 'RISK'
  | 'TODO'
  | 'NOTE'

export type EntityStatus =
  | 'draft'
  | 'confirmed'
  | 'rejected'
  | 'completed'
  | 'superseded'

export interface Entity {
  id: string
  project_id: string
  entity_type: EntityType
  reference_id: string
  status: EntityStatus
  phase: ProjectPhase
  title: string
  description: string
  tags: string[]
  priority: number | null
  source_text: string
  created_by: string
  created_at: string
  updated_at: string
}

export type NoteType =
  | 'user_note'
  | 'agent_note'
  | 'system_note'
  | 'phase_change'
  | 'decision'
  | 'clarification'
  | 'feedback'

export interface Note {
  id: string
  project_id: string
  phase: ProjectPhase
  note_type: NoteType
  content: string
  tags: string[]
  pinned: boolean
  created_by: string
  created_at: string
}
