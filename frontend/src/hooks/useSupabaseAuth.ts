// Custom hook for Supabase authentication integration with Zustand
import { useEffect, useCallback, useState } from 'react'
import { useAuthStore, useAuthActions, useNotifications } from '@/stores'
import { supabase } from '@/lib/supabase'
import { useRouter } from 'next/navigation'

export const useSupabaseAuth = () => {
  const router = useRouter()
  const [isHydrated, setIsHydrated] = useState(false)
  
  // Use the store directly instead of selectors to avoid hydration issues
  const authStore = useAuthStore()
  const uiStore = useNotifications()

  // Check if component is hydrated
  useEffect(() => {
    setIsHydrated(true)
  }, [])

  // Initialize auth state on mount (only after hydration)
  useEffect(() => {
    if (!isHydrated) return
    
    let mounted = true

    const initializeAuth = async () => {
      try {
        authStore.initialize()
        
        const { data: { session }, error } = await supabase.auth.getSession()
        
        if (mounted) {
          if (error) {
            console.error('Error getting session:', error)
            authStore.authStore.setLoading(false)
            return
          }

          authStore.setSession(session)
        }
      } catch (error) {
        console.error('Auth initialization error:', error)
        if (mounted) {
          authStore.authStore.setLoading(false)
        }
      }
    }

    initializeAuth()

    return () => {
      mounted = false
    }
  }, [isHydrated])

  // Listen to auth changes (only after hydration)
  useEffect(() => {
    if (!isHydrated) return
    
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (event, session) => {
      // Auth state changed
      
      authStore.setSession(session)
      
      switch (event) {
        case 'SIGNED_IN':
          uiStore.addNotification({
            type: 'success',
            title: 'Welcome!',
            message: `Successfully signed in as ${session?.user?.email}`
          })
          router.push('/dashboard')
          break
          
        case 'SIGNED_OUT':
          uiStore.addNotification({
            type: 'info',
            title: 'Signed out',
            message: 'You have been successfully signed out'
          })
          router.push('/auth/login')
          break
          
        case 'TOKEN_REFRESHED':
          // Token refreshed silently
          break
          
        case 'USER_UPDATED':
          uiStore.addNotification({
            type: 'success',
            title: 'Profile updated',
            message: 'Your profile has been successfully updated'
          })
          break
          
        case 'PASSWORD_RECOVERY':
          uiStore.addNotification({
            type: 'info',
            title: 'Password reset',
            message: 'Please check your email for password reset instructions'
          })
          break
      }
    })

    return () => subscription.unsubscribe()
  }, [isHydrated, router])

  // Sign in with email and password
  const signInWithPassword = useCallback(async (email: string, password: string) => {
    try {
      authStore.authStore.setLoading(true)
      
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      })

      if (error) {
        uiStore.addNotification({
          type: 'error',
          title: 'Sign in failed',
          message: error.message
        })
        return { success: false, error }
      }

      return { success: true, data }
    } catch (error) {
      uiStore.addNotification({
        type: 'error',
        title: 'Sign in failed',
        message: 'An unexpected error occurred'
      })
      return { success: false, error }
    } finally {
      authStore.authStore.setLoading(false)
    }
  }, [])

  // Sign up with email and password
  const signUpWithPassword = useCallback(async (email: string, password: string) => {
    try {
      authStore.authStore.setLoading(true)
      
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          emailRedirectTo: `${window.location.origin}/auth/callback`
        }
      })

      if (error) {
        addNotification({
          type: 'error',
          title: 'Sign up failed',
          message: error.message
        })
        return { success: false, error }
      }

      if (data.user && !data.session) {
        addNotification({
          type: 'info',
          title: 'Check your email',
          message: 'Please check your email for a confirmation link'
        })
      }

      return { success: true, data }
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Sign up failed',
        message: 'An unexpected error occurred'
      })
      return { success: false, error }
    } finally {
      authStore.setLoading(false)
    }
  }, [authStore.setLoading, addNotification])

  // Sign out
  const handleSignOut = useCallback(async () => {
    try {
      authStore.setLoading(true)
      
      const { error } = await supabase.auth.signOut()
      
      if (error) {
        addNotification({
          type: 'error',
          title: 'Sign out failed',
          message: error.message
        })
        return { success: false, error }
      }

      // Clear the store state
      signOut()
      
      return { success: true }
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Sign out failed',
        message: 'An unexpected error occurred'
      })
      return { success: false, error }
    } finally {
      authStore.setLoading(false)
    }
  }, [authStore.setLoading, signOut, addNotification])

  // Reset password
  const resetPassword = useCallback(async (email: string) => {
    try {
      authStore.setLoading(true)
      
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/auth/reset-password`
      })

      if (error) {
        addNotification({
          type: 'error',
          title: 'Password reset failed',
          message: error.message
        })
        return { success: false, error }
      }

      addNotification({
        type: 'success',
        title: 'Password reset sent',
        message: 'Please check your email for reset instructions'
      })

      return { success: true }
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Password reset failed',
        message: 'An unexpected error occurred'
      })
      return { success: false, error }
    } finally {
      authStore.setLoading(false)
    }
  }, [authStore.setLoading, addNotification])

  // Update password
  const updatePassword = useCallback(async (password: string) => {
    try {
      authStore.setLoading(true)
      
      const { error } = await supabase.auth.updateUser({ password })

      if (error) {
        addNotification({
          type: 'error',
          title: 'Password update failed',
          message: error.message
        })
        return { success: false, error }
      }

      addNotification({
        type: 'success',
        title: 'Password updated',
        message: 'Your password has been successfully updated'
      })

      return { success: true }
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Password update failed',
        message: 'An unexpected error occurred'
      })
      return { success: false, error }
    } finally {
      authStore.setLoading(false)
    }
  }, [authStore.setLoading, addNotification])

  // Update profile
  const updateProfile = useCallback(async (profileData: {
    full_name?: string
    display_name?: string
    bio?: string
    avatar_url?: string
  }) => {
    try {
      authStore.setLoading(true)
      
      const { error } = await supabase.auth.updateUser({
        data: profileData
      })

      if (error) {
        addNotification({
          type: 'error',
          title: 'Profile update failed',
          message: error.message
        })
        return { success: false, error }
      }

      addNotification({
        type: 'success',
        title: 'Profile updated',
        message: 'Your profile has been successfully updated'
      })

      return { success: true }
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Profile update failed',
        message: 'An unexpected error occurred'
      })
      return { success: false, error }
    } finally {
      authStore.setLoading(false)
    }
  }, [authStore.setLoading, addNotification])

  return {
    // State
    user: authStore.user,
    isAuthenticated: authStore.isAuthenticated,
    isLoading: authStore.isLoading,
    session: authStore.session,
    
    // Actions
    signInWithPassword,
    signUpWithPassword,
    signOut: handleSignOut,
    resetPassword,
    updatePassword,
    updateProfile,
    
    // Supabase client for advanced usage
    supabase
  }
}