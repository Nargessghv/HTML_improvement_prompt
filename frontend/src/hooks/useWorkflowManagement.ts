'use client'

import { useState, useCallback } from 'react'
import { useSupabaseAuth } from './useSupabaseAuthSimple'
import { toast } from 'sonner'

interface WorkflowState {
  id: string
  project_id: string
  agent_name: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  input_data: any
  output_data: any
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  execution_time_seconds: number | null
  created_at: string
}

interface Project {
  id: string
  title: string
  topic: string
  status: 'draft' | 'processing' | 'completed' | 'failed'
}

export function useWorkflowManagement() {
  const { supabase, user } = useSupabaseAuth()
  const [isRetrying, setIsRetrying] = useState(false)
  const [isCancelling, setIsCancelling] = useState(false)

  const retryFailedStages = useCallback(async (projectId: string, failedStates: WorkflowState[]) => {
    if (!user) {
      toast.error('User not authenticated')
      return false
    }

    setIsRetrying(true)
    try {
      // Reset failed workflow states to pending
      const { error: resetError } = await supabase
        .from('workflow_states')
        .update({ 
          status: 'pending',
          error_message: null,
          started_at: null,
          completed_at: null,
          execution_time_seconds: null
        })
        .in('id', failedStates.map(state => state.id))

      if (resetError) {
        console.error('Error resetting workflow states:', resetError)
        toast.error('Failed to reset workflow states')
        return false
      }

      // Update project status back to processing if it was failed
      const { error: projectError } = await supabase
        .from('projects')
        .update({ status: 'processing' })
        .eq('id', projectId)

      if (projectError) {
        console.error('Error updating project status:', projectError)
        toast.error('Failed to update project status')
        return false
      }

      toast.success('Failed stages reset. Workflow will resume automatically.')
      
      // TODO: Call backend API to trigger workflow retry
      // This will be implemented when backend integration is added
      console.log('TODO: Trigger backend workflow retry for project:', projectId)

      return true
    } catch (error) {
      console.error('Unexpected error during retry:', error)
      toast.error('An unexpected error occurred during retry')
      return false
    } finally {
      setIsRetrying(false)
    }
  }, [supabase, user])

  const cancelWorkflow = useCallback(async (projectId: string) => {
    if (!user) {
      toast.error('User not authenticated')
      return false
    }

    setIsCancelling(true)
    try {
      // Update all non-completed workflow states to failed with cancellation message
      const { data: activeStates, error: fetchError } = await supabase
        .from('workflow_states')
        .select('*')
        .eq('project_id', projectId)
        .in('status', ['pending', 'in_progress'])

      if (fetchError) {
        console.error('Error fetching active workflow states:', fetchError)
        toast.error('Failed to fetch workflow states')
        return false
      }

      if (activeStates && activeStates.length > 0) {
        const { error: cancelError } = await supabase
          .from('workflow_states')
          .update({
            status: 'failed',
            error_message: 'Workflow cancelled by user',
            completed_at: new Date().toISOString()
          })
          .in('id', activeStates.map(state => state.id))

        if (cancelError) {
          console.error('Error cancelling workflow states:', cancelError)
          toast.error('Failed to cancel workflow states')
          return false
        }
      }

      // Update project status to failed
      const { error: projectError } = await supabase
        .from('projects')
        .update({ 
          status: 'failed',
          completed_at: new Date().toISOString()
        })
        .eq('id', projectId)

      if (projectError) {
        console.error('Error updating project status:', projectError)
        toast.error('Failed to update project status')
        return false
      }

      toast.success('Workflow cancelled successfully')

      // TODO: Call backend API to cancel running workflow
      // This will be implemented when backend integration is added
      console.log('TODO: Cancel backend workflow for project:', projectId)

      return true
    } catch (error) {
      console.error('Unexpected error during cancellation:', error)
      toast.error('An unexpected error occurred during cancellation')
      return false
    } finally {
      setIsCancelling(false)
    }
  }, [supabase, user])

  const restartWorkflow = useCallback(async (project: Project) => {
    if (!user) {
      toast.error('User not authenticated')
      return false
    }

    try {
      // Delete all existing workflow states
      const { error: deleteError } = await supabase
        .from('workflow_states')
        .delete()
        .eq('project_id', project.id)

      if (deleteError) {
        console.error('Error deleting workflow states:', deleteError)
        toast.error('Failed to clear existing workflow states')
        return false
      }

      // Update project status to processing
      const { error: projectError } = await supabase
        .from('projects')
        .update({ 
          status: 'processing',
          completed_at: null
        })
        .eq('id', project.id)

      if (projectError) {
        console.error('Error updating project status:', projectError)
        toast.error('Failed to restart workflow')
        return false
      }

      toast.success('Workflow restarted successfully')

      // TODO: Call backend API to start fresh workflow
      // This will be implemented when backend integration is added
      console.log('TODO: Start fresh backend workflow for project:', project.id)

      return true
    } catch (error) {
      console.error('Unexpected error during workflow restart:', error)
      toast.error('An unexpected error occurred during restart')
      return false
    }
  }, [supabase, user])

  const getWorkflowHealth = useCallback((states: WorkflowState[]) => {
    const totalStates = states.length
    const completedStates = states.filter(s => s.status === 'completed').length
    const failedStates = states.filter(s => s.status === 'failed').length
    const inProgressStates = states.filter(s => s.status === 'in_progress').length

    return {
      total: totalStates,
      completed: completedStates,
      failed: failedStates,
      inProgress: inProgressStates,
      pending: totalStates - completedStates - failedStates - inProgressStates,
      healthScore: totalStates > 0 ? (completedStates / totalStates) * 100 : 0,
      hasErrors: failedStates > 0,
      isActive: inProgressStates > 0
    }
  }, [])

  return {
    retryFailedStages,
    cancelWorkflow,
    restartWorkflow,
    getWorkflowHealth,
    isRetrying,
    isCancelling
  }
}