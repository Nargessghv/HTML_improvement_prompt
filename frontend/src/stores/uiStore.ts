// UI state management with Zustand
import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'
import { UserPreferences } from '@/types'

interface UIState {
  // Theme and preferences
  preferences: UserPreferences
  
  // Layout state
  sidebarCollapsed: boolean
  sidebarWidth: number
  
  // Modal states
  modals: {
    createProject: boolean
    deleteProject: boolean
    userSettings: boolean
    slideEditor: boolean
    chatInterface: boolean
  }
  
  // Loading states
  globalLoading: boolean
  loadingStates: Record<string, boolean>
  
  // Notifications
  notifications: Notification[]
  
  // Editor state
  selectedSlideId: string | null
  editorMode: 'view' | 'edit'
  
  // Search and filters
  searchQuery: string
  activeFilters: Record<string, unknown>
}

interface Notification {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
  timestamp: string
  autoClose?: boolean
  duration?: number
}

interface UIActions {
  // Preferences
  updatePreferences: (preferences: Partial<UserPreferences>) => void
  resetPreferences: () => void
  
  // Layout
  toggleSidebar: () => void
  setSidebarCollapsed: (collapsed: boolean) => void
  setSidebarWidth: (width: number) => void
  
  // Modals
  openModal: (modal: keyof UIState['modals']) => void
  closeModal: (modal: keyof UIState['modals']) => void
  closeAllModals: () => void
  
  // Loading states
  setGlobalLoading: (loading: boolean) => void
  setLoading: (key: string, loading: boolean) => void
  clearLoadingState: (key: string) => void
  
  // Notifications
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp'>) => void
  removeNotification: (id: string) => void
  clearNotifications: () => void
  
  // Editor
  setSelectedSlide: (slideId: string | null) => void
  setEditorMode: (mode: 'view' | 'edit') => void
  
  // Search and filters
  setSearchQuery: (query: string) => void
  setFilter: (key: string, value: unknown) => void
  clearFilters: () => void
}

export type UIStore = UIState & UIActions

const defaultPreferences: UserPreferences = {
  theme: 'system',
  sidebarCollapsed: false,
  itemsPerPage: 20,
  enableNotifications: true,
  enableAutoSave: true
}

const defaultModals = {
  createProject: false,
  deleteProject: false,
  userSettings: false,
  slideEditor: false,
  chatInterface: false
}

export const useUIStore = create<UIStore>()(
  persist(
    (set, get) => ({
      // Initial state
      preferences: defaultPreferences,
      sidebarCollapsed: false,
      sidebarWidth: 280,
      modals: defaultModals,
      globalLoading: false,
      loadingStates: {},
      notifications: [],
      selectedSlideId: null,
      editorMode: 'view',
      searchQuery: '',
      activeFilters: {},

      // Preferences actions
      updatePreferences: (newPreferences) =>
        set((state) => ({
          preferences: { ...state.preferences, ...newPreferences }
        })),

      resetPreferences: () =>
        set((state) => ({
          preferences: defaultPreferences
        })),

      // Layout actions
      toggleSidebar: () =>
        set((state) => ({
          sidebarCollapsed: !state.sidebarCollapsed,
          preferences: {
            ...state.preferences,
            sidebarCollapsed: !state.sidebarCollapsed
          }
        })),

      setSidebarCollapsed: (collapsed) =>
        set((state) => ({
          sidebarCollapsed: collapsed,
          preferences: {
            ...state.preferences,
            sidebarCollapsed: collapsed
          }
        })),

      setSidebarWidth: (width) =>
        set((state) => ({
          sidebarWidth: Math.max(200, Math.min(400, width))
        })),

      // Modal actions
      openModal: (modal) =>
        set((state) => ({
          modals: { ...state.modals, [modal]: true }
        })),

      closeModal: (modal) =>
        set((state) => ({
          modals: { ...state.modals, [modal]: false }
        })),

      closeAllModals: () =>
        set((state) => ({
          modals: defaultModals
        })),

      // Loading actions
      setGlobalLoading: (loading) =>
        set((state) => ({
          globalLoading: loading
        })),

      setLoading: (key, loading) =>
        set((state) => ({
          loadingStates: {
            ...state.loadingStates,
            [key]: loading
          }
        })),

      clearLoadingState: (key) =>
        set((state) => {
          const { [key]: removed, ...rest } = state.loadingStates
          return { loadingStates: rest }
        }),

      // Notification actions
      addNotification: (notification) => {
        const id = `notification-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
        const newNotification: Notification = {
          id,
          timestamp: new Date().toISOString(),
          autoClose: notification.type === 'success' || notification.type === 'info',
          duration: 5000,
          ...notification
        }

        set((state) => ({
          notifications: [...state.notifications, newNotification]
        }))

        // Auto-remove notification if configured
        if (newNotification.autoClose) {
          setTimeout(() => {
            get().removeNotification(id)
          }, newNotification.duration)
        }
      },

      removeNotification: (id) =>
        set((state) => ({
          notifications: state.notifications.filter(n => n.id !== id)
        })),

      clearNotifications: () =>
        set((state) => ({
          notifications: []
        })),

      // Editor actions
      setSelectedSlide: (slideId) =>
        set((state) => ({
          selectedSlideId: slideId
        })),

      setEditorMode: (mode) =>
        set((state) => ({
          editorMode: mode
        })),

      // Search and filter actions
      setSearchQuery: (query) =>
        set((state) => ({
          searchQuery: query
        })),

      setFilter: (key, value) =>
        set((state) => ({
          activeFilters: {
            ...state.activeFilters,
            [key]: value
          }
        })),

      clearFilters: () =>
        set((state) => ({
          activeFilters: {}
        }))
    }),
    {
      name: 'ui-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        preferences: state.preferences,
        sidebarCollapsed: state.sidebarCollapsed,
        sidebarWidth: state.sidebarWidth
      })
    }
  )
)

// Selectors for better performance
export const useTheme = () => useUIStore((state) => state.preferences.theme)

export const useSidebar = () => useUIStore((state) => ({
  collapsed: state.sidebarCollapsed,
  width: state.sidebarWidth,
  toggle: state.toggleSidebar,
  setCollapsed: state.setSidebarCollapsed,
  setWidth: state.setSidebarWidth
}))

export const useModals = () => useUIStore((state) => ({
  modals: state.modals,
  openModal: state.openModal,
  closeModal: state.closeModal,
  closeAllModals: state.closeAllModals
}))

export const useNotifications = () => useUIStore((state) => ({
  notifications: state.notifications,
  addNotification: state.addNotification,
  removeNotification: state.removeNotification,
  clearNotifications: state.clearNotifications
}))

export const useLoading = () => useUIStore((state) => ({
  globalLoading: state.globalLoading,
  loadingStates: state.loadingStates,
  setGlobalLoading: state.setGlobalLoading,
  setLoading: state.setLoading,
  clearLoadingState: state.clearLoadingState,
  isLoading: (key: string) => state.loadingStates[key] || false
}))

export const useEditor = () => useUIStore((state) => ({
  selectedSlideId: state.selectedSlideId,
  editorMode: state.editorMode,
  setSelectedSlide: state.setSelectedSlide,
  setEditorMode: state.setEditorMode
}))

export const useSearch = () => useUIStore((state) => ({
  searchQuery: state.searchQuery,
  activeFilters: state.activeFilters,
  setSearchQuery: state.setSearchQuery,
  setFilter: state.setFilter,
  clearFilters: state.clearFilters
}))