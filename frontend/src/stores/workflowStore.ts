// Workflow state management with Zustand
import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'
import { WorkflowState, AgentProgress, AgentName } from '@/types'

interface WorkflowStoreState {
  // Current workflow data
  projectId: string | null
  workflowStates: WorkflowState[]
  
  // Progress tracking
  currentAgent: AgentName | null
  overallProgress: number
  estimatedTimeRemaining: number | null
  
  // Real-time updates
  isActive: boolean
  startedAt: string | null
  completedAt: string | null
  
  // Error handling
  error: string | null
  failedAgent: AgentName | null
  
  // UI state
  isSubscribed: boolean
  lastUpdated: string | null
}

interface WorkflowActions {
  // Workflow lifecycle
  startWorkflow: (projectId: string) => void
  completeWorkflow: () => void
  failWorkflow: (error: string, failedAgent?: AgentName) => void
  resetWorkflow: () => void
  
  // Agent state updates
  updateAgentState: (agentName: AgentName, state: Partial<WorkflowState>) => void
  setWorkflowStates: (states: WorkflowState[]) => void
  
  // Progress tracking
  updateProgress: (progress: number) => void
  setCurrentAgent: (agent: AgentName | null) => void
  setEstimatedTime: (seconds: number | null) => void
  
  // Real-time subscription
  subscribe: (projectId: string) => void
  unsubscribe: () => void
  
  // Utility
  getAgentProgress: (agentName: AgentName) => AgentProgress | null
  canRetryWorkflow: () => boolean
}

export type WorkflowStore = WorkflowStoreState & WorkflowActions

// Agent configuration for display purposes
const agentConfig: Record<AgentName, { displayName: string; description: string; order: number }> = {
  layout_analysis: {
    displayName: 'Layout Analysis',
    description: 'Analyzing presentation structure and requirements',
    order: 1
  },
  presentation_planning: {
    displayName: 'Presentation Planning',
    description: 'Creating detailed presentation outline',
    order: 2
  },
  content_generation: {
    displayName: 'Content Generation',
    description: 'Generating slide content and narratives',
    order: 3
  },
  html_content_generation: {
    displayName: 'HTML Generation',
    description: 'Creating HTML visualizations',
    order: 4
  },
  html_refinement: {
    displayName: 'HTML Refinement',
    description: 'Optimizing and refining HTML content',
    order: 5
  },
  quality_review: {
    displayName: 'Quality Review',
    description: 'Reviewing and validating content quality',
    order: 6
  },
  slide_assembly: {
    displayName: 'Slide Assembly',
    description: 'Assembling final presentation',
    order: 7
  }
}

export const useWorkflowStore = create<WorkflowStore>()(
  subscribeWithSelector((set, get) => ({
    // Initial state
    projectId: null,
    workflowStates: [],
    currentAgent: null,
    overallProgress: 0,
    estimatedTimeRemaining: null,
    isActive: false,
    startedAt: null,
    completedAt: null,
    error: null,
    failedAgent: null,
    isSubscribed: false,
    lastUpdated: null,

    // Workflow lifecycle actions
    startWorkflow: (projectId) =>
      set((state) => ({
        projectId,
        isActive: true,
        startedAt: new Date().toISOString(),
        completedAt: null,
        error: null,
        failedAgent: null,
        overallProgress: 0,
        lastUpdated: new Date().toISOString()
      })),

    completeWorkflow: () =>
      set((state) => ({
        isActive: false,
        completedAt: new Date().toISOString(),
        overallProgress: 100,
        currentAgent: null,
        estimatedTimeRemaining: null,
        lastUpdated: new Date().toISOString()
      })),

    failWorkflow: (error, failedAgent) =>
      set((state) => ({
        isActive: false,
        error,
        failedAgent,
        completedAt: new Date().toISOString(),
        lastUpdated: new Date().toISOString()
      })),

    resetWorkflow: () =>
      set((state) => ({
        projectId: null,
        workflowStates: [],
        currentAgent: null,
        overallProgress: 0,
        estimatedTimeRemaining: null,
        isActive: false,
        startedAt: null,
        completedAt: null,
        error: null,
        failedAgent: null,
        lastUpdated: null
      })),

    // Agent state updates
    updateAgentState: (agentName, stateUpdate) =>
      set((state) => {
        const existingIndex = state.workflowStates.findIndex(
          ws => ws.agent_name === agentName
        )

        let newStates: WorkflowState[]
        
        if (existingIndex >= 0) {
          // Update existing state
          newStates = state.workflowStates.map((ws, index) =>
            index === existingIndex 
              ? { ...ws, ...stateUpdate }
              : ws
          )
        } else {
          // Add new state
          const newState: WorkflowState = {
            id: `temp-${agentName}-${Date.now()}`,
            project_id: state.projectId || '',
            agent_name: agentName,
            status: 'pending',
            input_data: null,
            output_data: null,
            error_message: null,
            started_at: null,
            completed_at: null,
            execution_time_seconds: null,
            created_at: new Date().toISOString(),
            ...stateUpdate
          }
          newStates = [...state.workflowStates, newState]
        }

        // Calculate overall progress
        const totalAgents = Object.keys(agentConfig).length
        const completedAgents = newStates.filter(ws => ws.status === 'completed').length
        const overallProgress = Math.round((completedAgents / totalAgents) * 100)

        // Update current agent if this agent is in progress
        const currentAgent = stateUpdate.status === 'in_progress' 
          ? agentName 
          : state.currentAgent

        return {
          workflowStates: newStates,
          overallProgress,
          currentAgent,
          lastUpdated: new Date().toISOString()
        }
      }),

    setWorkflowStates: (states) =>
      set((state) => ({
        workflowStates: states,
        lastUpdated: new Date().toISOString()
      })),

    // Progress tracking
    updateProgress: (progress) =>
      set((state) => ({
        overallProgress: Math.max(0, Math.min(100, progress)),
        lastUpdated: new Date().toISOString()
      })),

    setCurrentAgent: (agent) =>
      set((state) => ({
        currentAgent: agent,
        lastUpdated: new Date().toISOString()
      })),

    setEstimatedTime: (seconds) =>
      set((state) => ({
        estimatedTimeRemaining: seconds,
        lastUpdated: new Date().toISOString()
      })),

    // Real-time subscription
    subscribe: (projectId) =>
      set((state) => ({
        isSubscribed: true,
        projectId
      })),

    unsubscribe: () =>
      set((state) => ({
        isSubscribed: false
      })),

    // Utility functions
    getAgentProgress: (agentName) => {
      const state = get()
      const workflowState = state.workflowStates.find(ws => ws.agent_name === agentName)
      const config = agentConfig[agentName]
      
      if (!config) return null

      return {
        name: agentName,
        display_name: config.displayName,
        description: config.description,
        status: workflowState?.status || 'pending',
        started_at: workflowState?.started_at,
        completed_at: workflowState?.completed_at,
        execution_time_seconds: workflowState?.execution_time_seconds,
        error_message: workflowState?.error_message
      }
    },

    canRetryWorkflow: () => {
      const state = get()
      return !state.isActive && (!!state.error || !!state.failedAgent)
    }
  }))
)

// Selectors for better performance
export const useWorkflowProgress = () => useWorkflowStore((state) => ({
  overallProgress: state.overallProgress,
  currentAgent: state.currentAgent,
  estimatedTimeRemaining: state.estimatedTimeRemaining,
  isActive: state.isActive,
  startedAt: state.startedAt,
  completedAt: state.completedAt
}))

export const useWorkflowError = () => useWorkflowStore((state) => ({
  error: state.error,
  failedAgent: state.failedAgent,
  canRetry: state.canRetryWorkflow()
}))

export const useWorkflowActions = () => useWorkflowStore((state) => ({
  startWorkflow: state.startWorkflow,
  completeWorkflow: state.completeWorkflow,
  failWorkflow: state.failWorkflow,
  resetWorkflow: state.resetWorkflow,
  updateAgentState: state.updateAgentState,
  setWorkflowStates: state.setWorkflowStates,
  subscribe: state.subscribe,
  unsubscribe: state.unsubscribe
}))

// Get all agent progress in order
export const useAgentProgress = () => useWorkflowStore((state) => {
  const agentNames = Object.keys(agentConfig) as AgentName[]
  
  return agentNames
    .sort((a, b) => agentConfig[a].order - agentConfig[b].order)
    .map(agentName => state.getAgentProgress(agentName))
    .filter(Boolean) as AgentProgress[]
})