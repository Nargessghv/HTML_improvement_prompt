// Database types re-export
export type { Database } from '@/lib/supabase'

// Common project types
export interface Project {
  id: string
  user_id: string
  title: string
  topic: string
  status: 'draft' | 'processing' | 'completed' | 'failed'
  created_at: string
  updated_at: string
  completed_at: string | null
  metadata: Record<string, unknown>
}

export interface WorkflowState {
  id: string
  project_id: string
  agent_name: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  input_data: Record<string, unknown> | null
  output_data: Record<string, unknown> | null
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  execution_time_seconds: number | null
  created_at: string
}

export interface Slide {
  id: string
  project_id: string
  slide_number: number
  title: string | null
  content: Record<string, unknown>
  html_content: string | null
  refined_html: string | null
  layout_type: string | null
  created_at: string
  updated_at: string
}

export interface ProjectFile {
  id: string
  project_id: string
  file_type: string
  file_path: string
  file_name: string
  file_size: number | null
  created_at: string
}

export interface Conversation {
  id: string
  project_id: string
  slide_id: string
  messages: ChatMessage[]
  created_at: string
  updated_at: string
}

// Chat and AI types
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  metadata?: Record<string, unknown>
}

// UI State types
export interface UserPreferences {
  theme: 'light' | 'dark' | 'system'
  sidebarCollapsed: boolean
  itemsPerPage: number
  enableNotifications: boolean
  enableAutoSave: boolean
}

// API Response types
export interface ApiResponse<T = unknown> {
  data?: T
  error?: string
  message?: string
  success: boolean
}

export interface PaginatedResponse<T> {
  data: T[]
  pagination: {
    page: number
    limit: number
    total: number
    totalPages: number
  }
}

export interface CreateProjectRequest {
  title: string
  topic: string
}

export interface StartGenerationRequest {
  project_id: string
  topic: string
  template_path?: string
}

export interface WorkflowProgress {
  project_id: string
  current_agent: string
  progress_percentage: number
  estimated_completion: string | null
  workflow_states: WorkflowState[]
}

// UI State types
export interface ProjectFilters {
  status?: 'draft' | 'processing' | 'completed' | 'failed'
  search?: string
  sortBy?: 'created_at' | 'updated_at' | 'title'
  sortOrder?: 'asc' | 'desc'
}

export interface PaginationState {
  page: number
  limit: number
  total: number
}

// Error types
export interface APIError {
  message: string
  code?: string
  details?: Record<string, unknown>
}

// Agent types
export type AgentName = 
  | 'layout_analysis'
  | 'presentation_planning'
  | 'content_generation'
  | 'html_content_generation'
  | 'html_refinement'
  | 'quality_review'
  | 'slide_assembly'

export interface AgentProgress {
  name: AgentName
  display_name: string
  description: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  progress_percentage?: number
  started_at?: string | null
  completed_at?: string | null
  execution_time_seconds?: number | null
  error_message?: string | null
}

// Webhook types
export interface WebhookEvent {
  event_type: 'workflow_update' | 'project_created' | 'project_completed' | 'project_failed' | 'slide_generated' | 'error_occurred'
  project_id: string
  agent_name?: string
  status?: string
  timestamp: string
  data?: Record<string, unknown>
}