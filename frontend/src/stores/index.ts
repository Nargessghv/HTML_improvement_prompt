// Zustand stores barrel export
// Re-export all stores and their utilities from this directory

// Main stores
export * from './authStore'
export * from './projectStore'
export * from './workflowStore'
export * from './slideStore'
export * from './uiStore'

// Store types for convenience
import type { AuthStore } from './authStore'
import type { ProjectStore } from './projectStore'
import type { WorkflowStore } from './workflowStore'
import type { SlideStore } from './slideStore'
import type { UIStore } from './uiStore'

export type { AuthStore, ProjectStore, WorkflowStore, SlideStore, UIStore }

// Combined store type for providers
export interface AppStores {
  auth: AuthStore
  project: ProjectStore
  workflow: WorkflowStore
  slide: SlideStore
  ui: UIStore
}

// Utility function to reset all stores (useful for logout)
export const resetAllStores = () => {
  // Import stores dynamically to avoid circular dependencies
  const { useAuthStore } = require('./authStore')
  const { useProjectStore } = require('./projectStore')
  const { useWorkflowStore } = require('./workflowStore')
  const { useSlideStore } = require('./slideStore')
  const { useUIStore } = require('./uiStore')

  // Reset auth store
  useAuthStore.getState().signOut()
  
  // Reset project store
  useProjectStore.setState({
    projects: [],
    currentProject: null,
    selectedProjects: [],
    filters: { sortBy: 'updated_at', sortOrder: 'desc' },
    pagination: { page: 1, limit: 20, total: 0 },
    isLoading: false,
    error: null
  })
  
  // Reset workflow store
  useWorkflowStore.getState().resetWorkflow()
  useWorkflowStore.getState().unsubscribe()
  
  // Reset slide store
  useSlideStore.getState().resetSlideEditor()
  useSlideStore.setState({
    slides: [],
    conversations: {},
    htmlHistory: {}
  })
  
  // Don't reset UI store preferences, but close modals and clear notifications
  useUIStore.getState().closeAllModals()
  useUIStore.getState().clearNotifications()
  useUIStore.setState({
    globalLoading: false,
    loadingStates: {},
    searchQuery: '',
    activeFilters: {},
    selectedSlideId: null,
    editorMode: 'view'
  })
}

// Store persistence utility
export const clearPersistedStores = () => {
  localStorage.removeItem('auth-storage')
  localStorage.removeItem('ui-storage')
}

// Development utilities
export const getStoreStates = () => {
  const { useAuthStore } = require('./authStore')
  const { useProjectStore } = require('./projectStore')
  const { useWorkflowStore } = require('./workflowStore')
  const { useSlideStore } = require('./slideStore')
  const { useUIStore } = require('./uiStore')

  return {
    auth: useAuthStore.getState(),
    project: useProjectStore.getState(),
    workflow: useWorkflowStore.getState(),
    slide: useSlideStore.getState(),
    ui: useUIStore.getState()
  }
}

// Store subscription utilities for debugging
export const subscribeToAllStores = (callback: (storeName: string, state: any) => void) => {
  const { useAuthStore } = require('./authStore')
  const { useProjectStore } = require('./projectStore')
  const { useWorkflowStore } = require('./workflowStore')
  const { useSlideStore } = require('./slideStore')
  const { useUIStore } = require('./uiStore')

  const unsubscribers = [
    useAuthStore.subscribe((state: any) => callback('auth', state)),
    useProjectStore.subscribe((state: any) => callback('project', state)),
    useWorkflowStore.subscribe((state: any) => callback('workflow', state)),
    useSlideStore.subscribe((state: any) => callback('slide', state)),
    useUIStore.subscribe((state: any) => callback('ui', state))
  ]

  return () => {
    unsubscribers.forEach(unsub => unsub())
  }
}