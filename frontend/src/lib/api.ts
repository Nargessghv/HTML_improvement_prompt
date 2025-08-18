import { createClient } from '@/lib/supabase/client'
import { Database } from './supabase'
import { env } from './env'

type Project = Database['public']['Tables']['projects']['Row']
type WorkflowState = Database['public']['Tables']['workflow_states']['Row']
type Slide = Database['public']['Tables']['slides']['Row']

class SlideCreatorAPI {
  private supabase = createClient()

  // Project Operations
  async createProject(title: string, topic: string): Promise<Project | null> {
    const { data: { user } } = await this.supabase.auth.getUser()
    
    if (!user) {
      throw new Error('User not authenticated')
    }

    const { data, error } = await this.supabase
      .from('projects')
      .insert({
        user_id: user.id,
        title,
        topic,
        status: 'draft',
      })
      .select()
      .single()

    if (error) {
      console.error('Error creating project:', error)
      throw error
    }

    return data
  }

  async getUserProjects(limit: number = 50, offset: number = 0): Promise<Project[]> {
    const { data: { user } } = await this.supabase.auth.getUser()
    
    if (!user) {
      throw new Error('User not authenticated')
    }

    const { data, error } = await this.supabase
      .from('projects')
      .select('*')
      .eq('user_id', user.id)
      .order('created_at', { ascending: false })
      .range(offset, offset + limit - 1)

    if (error) {
      console.error('Error fetching projects:', error)
      throw error
    }

    return data || []
  }

  async getProject(projectId: string): Promise<Project | null> {
    const { data: { user } } = await this.supabase.auth.getUser()
    
    if (!user) {
      throw new Error('User not authenticated')
    }

    const { data, error } = await this.supabase
      .from('projects')
      .select('*')
      .eq('id', projectId)
      .eq('user_id', user.id)
      .single()

    if (error) {
      console.error('Error fetching project:', error)
      throw error
    }

    return data
  }

  async deleteProject(projectId: string): Promise<{ message: string; files_deleted?: number; storage_warnings?: string[] }> {
    const { data: { session } } = await this.supabase.auth.getSession()
    
    if (!session?.access_token) {
      throw new Error('User not authenticated')
    }

    const response = await fetch(`/api/projects/${projectId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${session.access_token}`,
      },
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Failed to delete project' }))
      console.error('Error deleting project:', errorData)
      throw new Error(errorData.error || 'Failed to delete project')
    }

    const data = await response.json()
    return data
  }

  // Workflow State Operations
  async getProjectWorkflowStates(projectId: string): Promise<WorkflowState[]> {
    const { data, error } = await this.supabase
      .from('workflow_states')
      .select('*')
      .eq('project_id', projectId)
      .order('created_at', { ascending: true })

    if (error) {
      console.error('Error fetching workflow states:', error)
      throw error
    }

    return data || []
  }

  // Slide Operations
  async getProjectSlides(projectId: string): Promise<Slide[]> {
    const { data, error } = await this.supabase
      .from('slides')
      .select('*')
      .eq('project_id', projectId)
      .order('slide_number', { ascending: true })

    if (error) {
      console.error('Error fetching slides:', error)
      throw error
    }

    return data || []
  }

  // Real-time subscriptions
  subscribeToProject(projectId: string, callback: (payload: unknown) => void) {
    const channel = this.supabase
      .channel(`project-${projectId}`)
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'projects',
          filter: `id=eq.${projectId}`,
        },
        callback
      )
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'workflow_states',
          filter: `project_id=eq.${projectId}`,
        },
        callback
      )
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'slides',
          filter: `project_id=eq.${projectId}`,
        },
        callback
      )
      .subscribe()

    return () => {
      this.supabase.removeChannel(channel)
    }
  }

  // Backend API Integration
  async startSlideGeneration(title: string, topic: string, templatePath?: string): Promise<unknown> {
    // Get the current session to access the JWT token
    const { data: { session } } = await this.supabase.auth.getSession()
    
    if (!session?.access_token) {
      throw new Error('No valid authentication session found')
    }

    const response = await fetch(`${env.NEXT_PUBLIC_API_URL}/projects`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${session.access_token}`,
      },
      body: JSON.stringify({
        title,
        topic,
        template_path: templatePath || 'ekona_slides_template_new.pptx',
      }),
    })

    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`API request failed: ${response.status} ${response.statusText} - ${errorText}`)
    }

    return response.json()
  }
}

export const slideCreatorAPI = new SlideCreatorAPI()