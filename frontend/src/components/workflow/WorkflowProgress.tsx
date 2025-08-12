'use client'

import { useState, useEffect, useCallback } from 'react'
import { useSupabaseAuth } from '@/hooks/useSupabaseAuthSimple'
import { useWorkflowManagement } from '@/hooks/useWorkflowManagement'
import { useWorkflowNotifications } from '@/hooks/useWorkflowNotifications'
import { WorkflowLogViewer } from './WorkflowLogViewer'
import { RefinementModal } from '@/components/refinement/RefinementModal'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { 
  Play,
  Pause,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  AlertTriangle,
  Eye,
  EyeOff,
  Monitor
} from 'lucide-react'
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

interface WorkflowProgressProps {
  project: Project
  autoRefreshEnabled?: boolean
}

// Define the AI agent workflow stages in order
const WORKFLOW_STAGES = [
  {
    name: 'layout_analysis',
    label: 'Layout Analysis',
    description: 'Analyzing presentation structure and requirements',
    estimatedTimeMinutes: 2,
    isGlobal: true
  },
  {
    name: 'planning',
    label: 'Content Planning', 
    description: 'Planning slide content and structure',
    estimatedTimeMinutes: 3,
    isGlobal: true
  },
  {
    name: 'slide_creation',
    label: 'Creating Slides',
    description: 'Generating individual slides in parallel',
    estimatedTimeMinutes: 8,
    isGlobal: true
  },
  {
    name: 'assembly',
    label: 'Final Assembly',
    description: 'Assembling final presentation',
    estimatedTimeMinutes: 3,
    isGlobal: true
  }
]

const statusConfig = {
  pending: { 
    label: 'Pending', 
    color: 'bg-neutral-100 text-neutral-800 dark:bg-neutral-800 dark:text-neutral-200',
    icon: Clock
  },
  in_progress: { 
    label: 'In Progress', 
    color: 'bg-primary/10 text-primary dark:bg-primary/20 dark:text-primary',
    icon: Loader2
  },
  completed: { 
    label: 'Completed', 
    color: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200',
    icon: CheckCircle2
  },
  failed: { 
    label: 'Failed', 
    color: 'bg-destructive/10 text-destructive dark:bg-destructive/20 dark:text-destructive',
    icon: XCircle
  }
}

export function WorkflowProgress({ project, autoRefreshEnabled = true }: WorkflowProgressProps) {
  const { supabase, user } = useSupabaseAuth()
  const { 
    retryFailedStages, 
    cancelWorkflow, 
    restartWorkflow,
    isRetrying, 
    isCancelling 
  } = useWorkflowManagement()
  const { } = useWorkflowNotifications(project.id)
  const [workflowStates, setWorkflowStates] = useState<WorkflowState[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showDetails, setShowDetails] = useState(false)
  const [estimatedTimeRemaining, setEstimatedTimeRemaining] = useState<number | null>(null)
  const [showRefinementModal, setShowRefinementModal] = useState(false)
  const [hasRefinements, setHasRefinements] = useState(false)
  const [slideProgress, setSlideProgress] = useState<any>(null)

  // Check for available refinements
  useEffect(() => {
    if (!project?.id || !user || project.status === 'draft') return

    const checkRefinements = async () => {
      try {
        const { data, error } = await supabase
          .from('html_refinements')
          .select('id')
          .eq('project_id', project.id)
          .limit(1)

        if (!error && data && data.length > 0) {
          setHasRefinements(true)
        }
      } catch (error) {
        console.error('Error checking refinements:', error)
      }
    }

    checkRefinements()
  }, [project?.id, user, supabase, project.status])

  // Fetch slide progress for parallel processing projects
  useEffect(() => {
    if (!project?.id || !user) return

    const fetchSlideProgress = async () => {
      try {
        const { data, error } = await supabase
          .rpc('get_project_slide_progress', { p_project_id: project.id })

        if (error) {
          console.error('Error fetching slide progress:', error)
          return
        }

        if (data && data.length > 0) {
          setSlideProgress(data[0])
        }
      } catch (error) {
        console.error('Error fetching slide progress:', error)
      }
    }

    if (project.status === 'processing' || project.status === 'completed') {
      fetchSlideProgress()

      // Set up polling for slide progress
      const slideProgressInterval = setInterval(fetchSlideProgress, 15000)
      
      return () => {
        clearInterval(slideProgressInterval)
      }
    }
  }, [project?.id, user, supabase, project.status])

  const calculateEstimatedTime = useCallback((states: WorkflowState[]) => {
    if (project.status !== 'processing') {
      setEstimatedTimeRemaining(null)
      return
    }

    // Calculate remaining stages
    const remainingStages = WORKFLOW_STAGES.filter(stage => {
      const stageState = states.find(s => 
        s.agent_name === stage.name || 
        (s.agent_name === 'presentation_planner' && stage.name === 'planning') ||
        (s.agent_name === 'content_generator' && stage.name === 'content_generation') ||
        (s.agent_name === 'html_content_generator' && stage.name === 'html_generation') ||
        (s.agent_name === 'html_refinement_agent' && stage.name === 'refinement') ||
        (s.agent_name === 'slide_assembler' && stage.name === 'assembly')
      )
      return !stageState || stageState.status !== 'completed'
    })
    
    const totalEstimatedMinutes = remainingStages.reduce(
      (sum, stage) => sum + stage.estimatedTimeMinutes, 
      0
    )
    
    setEstimatedTimeRemaining(totalEstimatedMinutes)
  }, [project.status])

  useEffect(() => {
    if (!project?.id || !user) return

    let pollInterval: NodeJS.Timeout | null = null
    let isSubscribed = true

    const fetchWorkflowStates = async () => {
      if (!isSubscribed) return
      
      try {
        // Get the session to access the JWT token
        const { data: { session } } = await supabase.auth.getSession()
        if (!session?.access_token) {
          console.warn('No valid session found for workflow states')
          return
        }

        const response = await fetch(`/api/projects/${project.id}/workflow-states`, {
          headers: {
            'Authorization': `Bearer ${session.access_token}`
          }
        })

        if (!response.ok) {
          throw new Error(`Failed to fetch workflow states: ${response.status}`)
        }

        const data = await response.json()
        if (isSubscribed) {
          setWorkflowStates(data || [])
          calculateEstimatedTime(data || [])
        }
      } catch (error) {
        console.error('Error fetching workflow states:', error)
        // Don't show toast on every error to avoid spam
      } finally {
        if (isSubscribed) {
          setIsLoading(false)
        }
      }
    }

    // Initial fetch
    fetchWorkflowStates()

    // Set up polling as fallback (every 10 seconds)
    // Only poll if project is still processing and auto-refresh is enabled
    if (project.status === 'processing' && autoRefreshEnabled) {
      pollInterval = setInterval(() => {
        fetchWorkflowStates()
      }, 10000) // Poll every 10 seconds instead of continuous requests
    }

    // Try to set up real-time subscription (but don't rely on it)
    let subscription: any = null
    try {
      subscription = supabase
        .channel(`workflow-states-${project.id}`)
        .on(
          'postgres_changes',
          {
            event: '*',
            schema: 'public',
            table: 'workflow_states',
            filter: `project_id=eq.${project.id}`
          },
          (payload) => {
            if (!isSubscribed) return
            
            // Clear polling interval since real-time is working
            if (pollInterval) {
              clearInterval(pollInterval)
              pollInterval = null
            }

            setWorkflowStates(prev => {
              let newStates = prev
              
              if (payload.eventType === 'INSERT') {
                newStates = [...prev, payload.new as WorkflowState]
              } else if (payload.eventType === 'UPDATE') {
                newStates = prev.map(state => 
                  state.id === payload.new.id ? payload.new as WorkflowState : state
                )
              } else if (payload.eventType === 'DELETE') {
                newStates = prev.filter(state => state.id !== payload.old.id)
              }
              
              // Recalculate estimated time
              calculateEstimatedTime(newStates)
              return newStates
            })
          }
        )
        .subscribe()
    } catch (error) {
      console.warn('Real-time subscription failed, using polling fallback')
    }

    return () => {
      isSubscribed = false
      if (pollInterval) {
        clearInterval(pollInterval)
      }
      if (subscription) {
        subscription.unsubscribe()
      }
    }
  }, [project?.id, user, project.status, supabase, autoRefreshEnabled])

  const getWorkflowStateForStage = (stageName: string): WorkflowState | null => {
    // Helper function to get the most recent state for an agent name
    const getMostRecentState = (agentName: string) => {
      const agentStates = workflowStates.filter(state => state.agent_name === agentName)
      if (agentStates.length === 0) return null
      
      // Sort by created_at descending to get most recent first
      return agentStates.sort((a, b) => 
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      )[0]
    }
    
    // Map UI stage names to actual backend agent names
    const stageToAgentMap: Record<string, string> = {
      'layout_analysis': 'layout_analysis',
      'planning': 'planning', 
      'slide_creation': 'content_generation', // Use content_generation for slide creation stage
      'assembly': 'assembly'
    }
    
    const agentName = stageToAgentMap[stageName]
    if (!agentName) return null
    
    return getMostRecentState(agentName)
  }

  const getOverallProgress = (): number => {
    const totalStages = WORKFLOW_STAGES.length
    const completedStages = WORKFLOW_STAGES.filter(stage => {
      const state = getWorkflowStateForStage(stage.name)
      
      // Special handling for slide_creation stage - check slide progress
      if (stage.name === 'slide_creation') {
        return slideProgress?.completion_percentage === 100
      }
      
      return state?.status === 'completed'
    }).length
    
    return (completedStages / totalStages) * 100
  }

  const getCurrentStageIndex = (): number => {
    const inProgressStage = WORKFLOW_STAGES.findIndex(stage => {
      const state = getWorkflowStateForStage(stage.name)
      return state?.status === 'in_progress'
    })
    
    if (inProgressStage !== -1) return inProgressStage

    const lastCompletedIndex = WORKFLOW_STAGES.map(stage => {
      const state = getWorkflowStateForStage(stage.name)
      return state?.status === 'completed'
    }).lastIndexOf(true)

    return lastCompletedIndex + 1
  }

  const getFailedStages = (): WorkflowState[] => {
    return workflowStates.filter(state => state.status === 'failed')
  }

  const hasFailedStages = (): boolean => {
    return getFailedStages().length > 0
  }

  const handleRetryFailedStages = async () => {
    const failedStates = getFailedStages()
    if (failedStates.length === 0) return

    await retryFailedStages(project.id, failedStates)
  }

  const handleCancelWorkflow = async () => {
    await cancelWorkflow(project.id)
  }

  const handleRestartWorkflow = async () => {
    await restartWorkflow(project)
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Workflow Progress</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center space-x-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Loading workflow progress...</span>
          </div>
        </CardContent>
      </Card>
    )
  }

  const overallProgress = getOverallProgress()
  const currentStageIndex = getCurrentStageIndex()
  const failed = hasFailedStages()

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              Workflow Progress
              {failed && <AlertTriangle className="w-5 h-5 text-red-500" />}
            </CardTitle>
            <CardDescription>
              AI agents working on your presentation
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {hasRefinements && (
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => setShowRefinementModal(true)}
                className="bg-primary/5 border-primary/20 hover:bg-primary/10 text-primary"
              >
                <Monitor className="w-4 h-4 mr-2" />
                View Refinements
              </Button>
            )}
            <WorkflowLogViewer 
              projectId={project.id}
              trigger={
                <Button variant="outline" size="sm">
                  <Eye className="w-4 h-4 mr-2" />
                  View Logs
                </Button>
              }
            />
            <Button
              variant="outline" 
              size="sm"
              onClick={() => setShowDetails(!showDetails)}
            >
              {showDetails ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              {showDetails ? 'Hide' : 'Show'} Details
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {project.status === 'draft' ? (
          <div className="text-center py-8 text-gray-500">
            <Play className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p>Click &quot;Start Processing&quot; to begin the AI workflow</p>
          </div>
        ) : (
          <>
            {/* Overall Progress Bar */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium">
                  Overall Progress ({Math.round(overallProgress)}%)
                </span>
                {estimatedTimeRemaining !== null && estimatedTimeRemaining > 0 && (
                  <span className="text-gray-500">
                    ~{estimatedTimeRemaining} min remaining
                  </span>
                )}
              </div>
              <Progress value={overallProgress} className="h-3" />
            </div>

            {/* Stage Indicators */}
            <div className="space-y-3">
              {WORKFLOW_STAGES.map((stage, index) => {
                const state = getWorkflowStateForStage(stage.name)
                const status = state?.status || 'pending'
                const StatusIcon = statusConfig[status].icon
                const isActive = index === currentStageIndex
                const isCompleted = status === 'completed'
                const isFailed = status === 'failed'

                // Special handling for slide creation stage
                const isSlideCreationStage = stage.name === 'slide_creation'
                const slideCreationStatus = slideProgress ? 
                  (slideProgress.completion_percentage === 100 ? 'completed' : 
                   slideProgress.in_progress_slides > 0 ? 'in_progress' : 'pending') : 'pending'

                const finalStatus = isSlideCreationStage ? slideCreationStatus : status
                const FinalStatusIcon = isSlideCreationStage ? statusConfig[slideCreationStatus].icon : StatusIcon

                return (
                  <div key={stage.name} className={`flex items-center space-x-3 p-3 rounded-lg border ${
                    isActive ? 'border-primary/20 bg-primary/5' : 
                    (isCompleted || finalStatus === 'completed') ? 'border-emerald-200 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950' :
                    (isFailed || finalStatus === 'failed') ? 'border-destructive/20 bg-destructive/5' : 
                    'border-neutral-200 dark:border-neutral-800'
                  }`}>
                    <div className="flex-shrink-0">
                      <FinalStatusIcon className={`w-5 h-5 ${
                        finalStatus === 'in_progress' ? 'animate-spin text-primary' :
                        finalStatus === 'completed' ? 'text-emerald-600' :
                        finalStatus === 'failed' ? 'text-destructive' :
                        'text-neutral-400'
                      }`} />
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2">
                        <span className={`font-medium ${
                          isActive ? 'text-primary dark:text-primary' :
                          (isCompleted || finalStatus === 'completed') ? 'text-emerald-900 dark:text-emerald-300' :
                          (isFailed || finalStatus === 'failed') ? 'text-destructive dark:text-destructive' :
                          'text-neutral-700 dark:text-neutral-300'
                        }`}>
                          {stage.label}
                        </span>
                        <Badge className={statusConfig[finalStatus].color}>
                          {statusConfig[finalStatus].label}
                        </Badge>
                      </div>
                      
                      <p className={`text-sm mt-1 ${
                        isActive ? 'text-primary/70' :
                        (isCompleted || finalStatus === 'completed') ? 'text-emerald-600 dark:text-emerald-400' :
                        (isFailed || finalStatus === 'failed') ? 'text-destructive/70' :
                        'text-neutral-500 dark:text-neutral-400'
                      }`}>
                        {stage.description}
                      </p>

                      {/* Show slide progress for slide creation stage */}
                      {isSlideCreationStage && slideProgress && (
                        <div className="mt-2 space-y-2">
                          <div className="flex items-center justify-between text-xs">
                            <span>Individual Slides</span>
                            <span>{slideProgress.completed_slides} of {slideProgress.total_slides} completed</span>
                          </div>
                          <Progress value={slideProgress.completion_percentage} className="h-2" />
                          <div className="flex flex-wrap gap-1">
                            {slideProgress.completed_slides > 0 && (
                              <Badge variant="secondary" className="text-xs bg-emerald-100 text-emerald-800">
                                <CheckCircle2 className="w-2 h-2 mr-1" />
                                {slideProgress.completed_slides} Done
                              </Badge>
                            )}
                            {slideProgress.in_progress_slides > 0 && (
                              <Badge variant="secondary" className="text-xs bg-primary/10 text-primary">
                                <Loader2 className="w-2 h-2 mr-1 animate-spin" />
                                {slideProgress.in_progress_slides} Processing
                              </Badge>
                            )}
                            {slideProgress.pending_slides > 0 && (
                              <Badge variant="secondary" className="text-xs bg-neutral-100 text-neutral-800">
                                <Clock className="w-2 h-2 mr-1" />
                                {slideProgress.pending_slides} Pending
                              </Badge>
                            )}
                            {slideProgress.failed_slides > 0 && (
                              <Badge variant="secondary" className="text-xs bg-destructive/10 text-destructive">
                                <XCircle className="w-2 h-2 mr-1" />
                                {slideProgress.failed_slides} Failed
                              </Badge>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Show execution time for completed stages */}
                      {state?.execution_time_seconds && finalStatus === 'completed' && !isSlideCreationStage && (
                        <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-1">
                          Completed in {state.execution_time_seconds}s
                        </p>
                      )}

                      {/* Show error message for failed stages */}
                      {state?.error_message && finalStatus === 'failed' && showDetails && (
                        <div className="mt-2 p-2 bg-destructive/5 border border-destructive/20 rounded text-sm text-destructive">
                          <strong>Error:</strong> {state.error_message}
                        </div>
                      )}

                      {/* Show detailed data when details are visible */}
                      {showDetails && state && (finalStatus === 'completed' || finalStatus === 'in_progress') && !isSlideCreationStage && (
                        <div className="mt-2 space-y-1 text-xs text-neutral-500 dark:text-neutral-400">
                          {state.started_at && (
                            <p>Started: {new Date(state.started_at).toLocaleTimeString()}</p>
                          )}
                          {state.completed_at && (
                            <p>Completed: {new Date(state.completed_at).toLocaleTimeString()}</p>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Action Buttons */}
            {(project.status === 'processing' || project.status === 'failed') && (
              <div className="flex justify-center space-x-3 pt-4 border-t">
                {failed && (
                  <Button 
                    onClick={handleRetryFailedStages}
                    variant="outline"
                    size="sm"
                    disabled={isRetrying}
                  >
                    <RefreshCw className={`w-4 h-4 mr-2 ${isRetrying ? 'animate-spin' : ''}`} />
                    {isRetrying ? 'Retrying...' : 'Retry Failed'}
                  </Button>
                )}
                
                {project.status === 'processing' && (
                  <Button 
                    onClick={handleCancelWorkflow}
                    variant="outline"
                    size="sm"
                    disabled={isCancelling}
                  >
                    <Pause className="w-4 h-4 mr-2" />
                    {isCancelling ? 'Cancelling...' : 'Cancel Workflow'}
                  </Button>
                )}

                {project.status === 'failed' && (
                  <Button 
                    onClick={handleRestartWorkflow}
                    variant="outline"
                    size="sm"
                  >
                    <Play className="w-4 h-4 mr-2" />
                    Restart Workflow
                  </Button>
                )}
              </div>
            )}
          </>
        )}
      </CardContent>
      
      {/* Refinement Modal */}
      <RefinementModal
        open={showRefinementModal}
        onOpenChange={setShowRefinementModal}
        projectId={project.id}
      />
    </Card>
  )
}