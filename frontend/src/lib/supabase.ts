import { createClient } from '@supabase/supabase-js'

// Get Supabase configuration with runtime validation
function getSupabaseConfig() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim() || 'https://placeholder.supabase.co'
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.trim() || 'placeholder-key'

  // Validate URL format
  if (supabaseUrl === 'https://placeholder.supabase.co') {
    console.warn('⚠️  Using placeholder Supabase URL - check environment variables')
  }

  return { supabaseUrl, supabaseAnonKey }
}

// Create Supabase client with runtime configuration
const config = getSupabaseConfig()
export const supabase = createClient(config.supabaseUrl, config.supabaseAnonKey)

// Database type definitions
export type Database = {
  public: {
    Tables: {
      projects: {
        Row: {
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
        Insert: {
          id?: string
          user_id: string
          title: string
          topic: string
          status?: 'draft' | 'processing' | 'completed' | 'failed'
          created_at?: string
          updated_at?: string
          completed_at?: string | null
          metadata?: Record<string, unknown>
        }
        Update: {
          id?: string
          user_id?: string
          title?: string
          topic?: string
          status?: 'draft' | 'processing' | 'completed' | 'failed'
          created_at?: string
          updated_at?: string
          completed_at?: string | null
          metadata?: Record<string, unknown>
        }
      }
      workflow_states: {
        Row: {
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
        Insert: {
          id?: string
          project_id: string
          agent_name: string
          status?: 'pending' | 'in_progress' | 'completed' | 'failed'
          input_data?: Record<string, unknown> | null
          output_data?: Record<string, unknown> | null
          error_message?: string | null
          started_at?: string | null
          completed_at?: string | null
          execution_time_seconds?: number | null
          created_at?: string
        }
        Update: {
          id?: string
          project_id?: string
          agent_name?: string
          status?: 'pending' | 'in_progress' | 'completed' | 'failed'
          input_data?: Record<string, unknown> | null
          output_data?: Record<string, unknown> | null
          error_message?: string | null
          started_at?: string | null
          completed_at?: string | null
          execution_time_seconds?: number | null
          created_at?: string
        }
      }
      slides: {
        Row: {
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
        Insert: {
          id?: string
          project_id: string
          slide_number: number
          title?: string | null
          content: Record<string, unknown>
          html_content?: string | null
          refined_html?: string | null
          layout_type?: string | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          project_id?: string
          slide_number?: number
          title?: string | null
          content?: Record<string, unknown>
          html_content?: string | null
          refined_html?: string | null
          layout_type?: string | null
          created_at?: string
          updated_at?: string
        }
      }
      conversations: {
        Row: {
          id: string
          project_id: string
          slide_id: string
          messages: Record<string, unknown>[]
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          project_id: string
          slide_id: string
          messages?: Record<string, unknown>[]
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          project_id?: string
          slide_id?: string
          messages?: Record<string, unknown>[]
          created_at?: string
          updated_at?: string
        }
      }
      project_files: {
        Row: {
          id: string
          project_id: string
          file_type: string
          file_path: string
          file_name: string
          file_size: number | null
          created_at: string
        }
        Insert: {
          id?: string
          project_id: string
          file_type: string
          file_path: string
          file_name: string
          file_size?: number | null
          created_at?: string
        }
        Update: {
          id?: string
          project_id?: string
          file_type?: string
          file_path?: string
          file_name?: string
          file_size?: number | null
          created_at?: string
        }
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      [_ in never]: never
    }
  }
}

// Typed Supabase client
export type SupabaseClient = ReturnType<typeof createClient<Database>>