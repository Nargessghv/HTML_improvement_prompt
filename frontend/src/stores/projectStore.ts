// Project state management with Zustand
import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'
import { Project, ProjectFilters, PaginationState, ApiResponse } from '@/types'

interface ProjectState {
  // Project data
  projects: Project[]
  currentProject: Project | null
  
  // UI state
  filters: ProjectFilters
  pagination: PaginationState
  isLoading: boolean
  error: string | null
  
  // Selection state
  selectedProjects: string[]
}

interface ProjectActions {
  // Project CRUD
  setProjects: (projects: Project[]) => void
  addProject: (project: Project) => void
  updateProject: (id: string, updates: Partial<Project>) => void
  removeProject: (id: string) => void
  setCurrentProject: (project: Project | null) => void
  
  // UI actions
  setFilters: (filters: Partial<ProjectFilters>) => void
  setPagination: (pagination: Partial<PaginationState>) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  
  // Selection actions
  selectProject: (id: string) => void
  selectProjects: (ids: string[]) => void
  clearSelection: () => void
  toggleProjectSelection: (id: string) => void
  
  // Utility actions
  resetFilters: () => void
  refreshProjects: () => void
}

export type ProjectStore = ProjectState & ProjectActions

const initialFilters: ProjectFilters = {
  sortBy: 'updated_at',
  sortOrder: 'desc'
}

const initialPagination: PaginationState = {
  page: 1,
  limit: 20,
  total: 0
}

export const useProjectStore = create<ProjectStore>()(
  subscribeWithSelector((set, get) => ({
    // Initial state
    projects: [],
    currentProject: null,
    filters: initialFilters,
    pagination: initialPagination,
    isLoading: false,
    error: null,
    selectedProjects: [],

    // Project CRUD actions
    setProjects: (projects) =>
      set((state) => ({
        projects,
        error: null
      })),

    addProject: (project) =>
      set((state) => ({
        projects: [project, ...state.projects]
      })),

    updateProject: (id, updates) =>
      set((state) => ({
        projects: state.projects.map(p => 
          p.id === id ? { ...p, ...updates } : p
        ),
        currentProject: state.currentProject?.id === id 
          ? { ...state.currentProject, ...updates }
          : state.currentProject
      })),

    removeProject: (id) =>
      set((state) => ({
        projects: state.projects.filter(p => p.id !== id),
        currentProject: state.currentProject?.id === id 
          ? null 
          : state.currentProject,
        selectedProjects: state.selectedProjects.filter(pId => pId !== id)
      })),

    setCurrentProject: (project) =>
      set((state) => ({
        currentProject: project
      })),

    // UI actions
    setFilters: (newFilters) =>
      set((state) => ({
        filters: { ...state.filters, ...newFilters },
        pagination: { ...state.pagination, page: 1 } // Reset to first page
      })),

    setPagination: (newPagination) =>
      set((state) => ({
        pagination: { ...state.pagination, ...newPagination }
      })),

    setLoading: (loading) =>
      set((state) => ({
        isLoading: loading
      })),

    setError: (error) =>
      set((state) => ({
        error
      })),

    // Selection actions
    selectProject: (id) =>
      set((state) => ({
        selectedProjects: [id]
      })),

    selectProjects: (ids) =>
      set((state) => ({
        selectedProjects: ids
      })),

    clearSelection: () =>
      set((state) => ({
        selectedProjects: []
      })),

    toggleProjectSelection: (id) =>
      set((state) => ({
        selectedProjects: state.selectedProjects.includes(id)
          ? state.selectedProjects.filter(pId => pId !== id)
          : [...state.selectedProjects, id]
      })),

    // Utility actions
    resetFilters: () =>
      set((state) => ({
        filters: initialFilters,
        pagination: initialPagination
      })),

    refreshProjects: () =>
      set((state) => ({
        isLoading: true,
        error: null
      }))
  }))
)

// Selectors for better performance
export const useProjects = () => useProjectStore((state) => ({
  projects: state.projects,
  isLoading: state.isLoading,
  error: state.error,
  pagination: state.pagination,
  filters: state.filters
}))

export const useCurrentProject = () => useProjectStore((state) => state.currentProject)

export const useProjectSelection = () => useProjectStore((state) => ({
  selectedProjects: state.selectedProjects,
  selectProject: state.selectProject,
  selectProjects: state.selectProjects,
  clearSelection: state.clearSelection,
  toggleProjectSelection: state.toggleProjectSelection
}))

export const useProjectActions = () => useProjectStore((state) => ({
  setProjects: state.setProjects,
  addProject: state.addProject,
  updateProject: state.updateProject,
  removeProject: state.removeProject,
  setCurrentProject: state.setCurrentProject,
  setFilters: state.setFilters,
  setPagination: state.setPagination,
  setLoading: state.setLoading,
  setError: state.setError,
  resetFilters: state.resetFilters,
  refreshProjects: state.refreshProjects
}))

// Computed selectors
export const useFilteredProjects = () => useProjectStore((state) => {
  const { projects, filters } = state
  
  let filtered = [...projects]
  
  // Apply status filter
  if (filters.status) {
    filtered = filtered.filter(p => p.status === filters.status)
  }
  
  // Apply search filter
  if (filters.search) {
    const searchLower = filters.search.toLowerCase()
    filtered = filtered.filter(p => 
      p.title.toLowerCase().includes(searchLower) ||
      p.topic.toLowerCase().includes(searchLower)
    )
  }
  
  // Apply sorting
  if (filters.sortBy) {
    filtered.sort((a, b) => {
      const aVal = a[filters.sortBy!]
      const bVal = b[filters.sortBy!]
      
      if (!aVal || !bVal) return 0
      
      const comparison = aVal < bVal ? -1 : aVal > bVal ? 1 : 0
      return filters.sortOrder === 'desc' ? -comparison : comparison
    })
  }
  
  return filtered
})