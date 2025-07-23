'use client'

import { useEffect, useRef } from 'react'
import { useSupabaseAuth } from './useSupabaseAuthSimple'
import { toast } from 'sonner'

interface WorkflowState {
  id: string
  project_id: string
  agent_name: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  error_message: string | null
}

interface Project {
  id: string
  title: string
  status: 'draft' | 'processing' | 'completed' | 'failed'
}

interface WorkflowNotificationOptions {
  enableBrowserNotifications?: boolean
  enableSoundNotifications?: boolean
  enableToastNotifications?: boolean
  enableEmailNotifications?: boolean
}

const defaultOptions: WorkflowNotificationOptions = {
  enableBrowserNotifications: true,
  enableSoundNotifications: false,
  enableToastNotifications: true,
  enableEmailNotifications: false
}

export function useWorkflowNotifications(
  projectId: string,
  options: WorkflowNotificationOptions = defaultOptions
) {
  const { supabase, user } = useSupabaseAuth()
  const previousProjectStatus = useRef<string | null>(null)
  const previousWorkflowStates = useRef<WorkflowState[]>([])
  const hasRequestedPermission = useRef(false)

  // Request browser notification permission
  useEffect(() => {
    if (options.enableBrowserNotifications && !hasRequestedPermission.current) {
      hasRequestedPermission.current = true
      if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission().then(permission => {
          if (permission === 'granted') {
            toast.success('Browser notifications enabled for workflow updates')
          }
        })
      }
    }
  }, [options.enableBrowserNotifications])

  // Set up real-time subscriptions for notifications
  useEffect(() => {
    if (!projectId || !user) return

    let projectSubscription: any = null
    let workflowSubscription: any = null

    const setupProjectSubscription = () => {
      // Subscribe to project status changes
      projectSubscription = supabase
        .channel(`project-notifications-${projectId}`)
        .on(
          'postgres_changes',
          {
            event: 'UPDATE',
            schema: 'public',
            table: 'projects',
            filter: `id=eq.${projectId}`
          },
          (payload) => {
            const newProject = payload.new as Project
            const oldProject = payload.old as Project

            // Only notify on status changes
            if (oldProject.status !== newProject.status) {
              handleProjectStatusChange(oldProject, newProject)
            }
          }
        )
        .subscribe()
    }

    const setupWorkflowSubscription = () => {
      // Subscribe to workflow state changes
      workflowSubscription = supabase
        .channel(`workflow-notifications-${projectId}`)
        .on(
          'postgres_changes',
          {
            event: '*',
            schema: 'public',
            table: 'workflow_states',
            filter: `project_id=eq.${projectId}`
          },
          (payload) => {
            if (payload.eventType === 'UPDATE') {
              const newState = payload.new as WorkflowState
              const oldState = payload.old as WorkflowState

              // Only notify on status changes
              if (oldState.status !== newState.status) {
                handleWorkflowStateChange(oldState, newState)
              }
            } else if (payload.eventType === 'INSERT') {
              const newState = payload.new as WorkflowState
              handleWorkflowStateStart(newState)
            }
          }
        )
        .subscribe()
    }

    setupProjectSubscription()
    setupWorkflowSubscription()

    return () => {
      if (projectSubscription) {
        projectSubscription.unsubscribe()
      }
      if (workflowSubscription) {
        workflowSubscription.unsubscribe()
      }
    }
  }, [projectId, user, supabase, options])

  const handleProjectStatusChange = (oldProject: Project, newProject: Project) => {
    const agentNames: Record<string, string> = {
      'layout_analysis': 'Layout Analysis',
      'planning': 'Content Planning',
      'content_generation': 'Content Generation',
      'html_generation': 'HTML Generation',
      'refinement': 'Content Refinement',
      'quality_review': 'Quality Review',
      'assembly': 'Final Assembly'
    }

    const statusMessages = {
      processing: {
        title: '🚀 Workflow Started',
        message: `AI agents have started working on "${newProject.title}"`,
        type: 'info' as const
      },
      completed: {
        title: '✅ Presentation Complete!',
        message: `"${newProject.title}" has been successfully generated and is ready for download`,
        type: 'success' as const
      },
      failed: {
        title: '❌ Workflow Failed',
        message: `An error occurred while processing "${newProject.title}"`,
        type: 'error' as const
      }
    }

    const statusConfig = statusMessages[newProject.status as keyof typeof statusMessages]
    if (!statusConfig) return

    // Toast notification
    if (options.enableToastNotifications) {
      if (statusConfig.type === 'success') {
        toast.success(statusConfig.message, {
          duration: 5000,
          action: {
            label: 'View Project',
            onClick: () => {
              window.location.href = `/projects/${newProject.id}`
            }
          }
        })
      } else if (statusConfig.type === 'error') {
        toast.error(statusConfig.message, {
          duration: 7000,
          action: {
            label: 'View Details',
            onClick: () => {
              window.location.href = `/projects/${newProject.id}`
            }
          }
        })
      } else {
        toast.info(statusConfig.message, {
          duration: 4000
        })
      }
    }

    // Browser notification
    if (options.enableBrowserNotifications && 'Notification' in window && Notification.permission === 'granted') {
      new Notification(statusConfig.title, {
        body: statusConfig.message,
        icon: '/favicon.ico',
        badge: '/favicon.ico',
        tag: `project-${projectId}`,
        requireInteraction: newProject.status === 'completed' || newProject.status === 'failed'
      })
    }

    // Sound notification (simple beep for now)
    if (options.enableSoundNotifications && newProject.status === 'completed') {
      playNotificationSound()
    }
  }

  const handleWorkflowStateChange = (oldState: WorkflowState, newState: WorkflowState) => {
    const agentDisplayName = newState.agent_name
      .replace(/_/g, ' ')
      .replace(/\b\w/g, l => l.toUpperCase())

    if (newState.status === 'completed') {
      if (options.enableToastNotifications) {
        toast.success(`${agentDisplayName} completed`, {
          description: 'Moving to next stage...',
          duration: 2000
        })
      }
    } else if (newState.status === 'failed') {
      if (options.enableToastNotifications) {
        toast.error(`${agentDisplayName} failed`, {
          description: newState.error_message || 'An error occurred during processing',
          duration: 5000,
          action: {
            label: 'View Error',
            onClick: () => {
              // This would open the log viewer - can be implemented later
              console.log('TODO: Open log viewer for failed state:', newState.id)
            }
          }
        })
      }

      // Browser notification for failures
      if (options.enableBrowserNotifications && 'Notification' in window && Notification.permission === 'granted') {
        new Notification(`⚠️ ${agentDisplayName} Failed`, {
          body: newState.error_message || 'An error occurred during processing',
          icon: '/favicon.ico',
          tag: `workflow-error-${newState.id}`,
          requireInteraction: true
        })
      }
    }
  }

  const handleWorkflowStateStart = (newState: WorkflowState) => {
    if (newState.status === 'in_progress') {
      const agentDisplayName = newState.agent_name
        .replace(/_/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase())

      if (options.enableToastNotifications) {
        toast.info(`${agentDisplayName} started`, {
          description: 'AI agent is now processing...',
          duration: 2000
        })
      }
    }
  }

  const playNotificationSound = () => {
    try {
      // Create a simple beep sound using Web Audio API
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
      const oscillator = audioContext.createOscillator()
      const gainNode = audioContext.createGain()
      
      oscillator.connect(gainNode)
      gainNode.connect(audioContext.destination)
      
      oscillator.frequency.value = 800 // Frequency in Hz
      oscillator.type = 'sine'
      
      gainNode.gain.setValueAtTime(0, audioContext.currentTime)
      gainNode.gain.linearRampToValueAtTime(0.3, audioContext.currentTime + 0.01)
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5)
      
      oscillator.start(audioContext.currentTime)
      oscillator.stop(audioContext.currentTime + 0.5)
    } catch (error) {
      console.warn('Could not play notification sound:', error)
    }
  }

  const sendTestNotification = () => {
    if (options.enableToastNotifications) {
      toast.success('Test notification', {
        description: 'Workflow notifications are working correctly!',
        duration: 3000
      })
    }

    if (options.enableBrowserNotifications && 'Notification' in window && Notification.permission === 'granted') {
      new Notification('🧪 Test Notification', {
        body: 'Workflow notifications are working correctly!',
        icon: '/favicon.ico',
        tag: 'test-notification'
      })
    }

    if (options.enableSoundNotifications) {
      playNotificationSound()
    }
  }

  return {
    sendTestNotification,
    notificationPermission: typeof window !== 'undefined' && 'Notification' in window 
      ? Notification.permission 
      : 'denied'
  }
}