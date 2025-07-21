// Authentication state management with Zustand
import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'
import { User } from '@supabase/supabase-js'

export interface AuthUser extends User {
  // Add any custom user properties here
}

interface AuthState {
  user: AuthUser | null
  isLoading: boolean
  isAuthenticated: boolean
  session: any | null
}

interface AuthActions {
  setUser: (user: AuthUser | null) => void
  setSession: (session: any | null) => void
  setLoading: (loading: boolean) => void
  signOut: () => void
  initialize: () => void
}

export type AuthStore = AuthState & AuthActions

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      // State
      user: null,
      isLoading: true,
      isAuthenticated: false,
      session: null,

      // Actions
      setUser: (user) => 
        set((state) => ({
          user,
          isAuthenticated: !!user,
          isLoading: false
        })),

      setSession: (session) =>
        set((state) => ({
          session,
          isAuthenticated: !!session?.user,
          user: session?.user || null
        })),

      setLoading: (loading) =>
        set((state) => ({
          isLoading: loading
        })),

      signOut: () =>
        set((state) => ({
          user: null,
          session: null,
          isAuthenticated: false,
          isLoading: false
        })),

      initialize: () =>
        set((state) => ({
          isLoading: true
        }))
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        session: state.session,
        isAuthenticated: state.isAuthenticated
      })
    }
  )
)

// Selectors for better performance
export const useAuth = () => useAuthStore((state) => ({
  user: state.user,
  isAuthenticated: state.isAuthenticated,
  isLoading: state.isLoading,
  session: state.session
}))

export const useAuthActions = () => useAuthStore((state) => ({
  setUser: state.setUser,
  setSession: state.setSession,
  setLoading: state.setLoading,
  signOut: state.signOut,
  initialize: state.initialize
}))