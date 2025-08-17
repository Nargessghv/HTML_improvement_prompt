// Simplified Supabase authentication hook
import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import { useRouter } from 'next/navigation'
import type { User, Session } from '@supabase/supabase-js'
import { toast } from "sonner"

export const useSupabaseAuth = () => {
  const router = useRouter()
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Get initial session
    const getSession = async () => {
      const { data: { session } } = await supabase.auth.getSession()
      setSession(session)
      setUser(session?.user ?? null)
      setIsLoading(false)
    }

    getSession()

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        setSession(session)
        setUser(session?.user ?? null)
        setIsLoading(false)

        if (event === 'SIGNED_IN') {
          toast.success(`Welcome! Successfully signed in as ${session?.user?.email}`)
          router.push('/dashboard')
        } else if (event === 'SIGNED_OUT') {
          toast.success('You have been successfully signed out')
          router.push('/')
        } else if (event === 'USER_UPDATED') {
          toast.success('Your profile has been successfully updated')
        }
      }
    )

    return () => subscription.unsubscribe()
  }, [router])

  const signOut = async () => {
    await supabase.auth.signOut()
  }

  const signInWithOAuth = async (provider: 'azure', redirectTo?: string) => {
    setIsLoading(true)
    try {
      const { data, error } = await supabase.auth.signInWithOAuth({
        provider,
        options: {
          redirectTo: `${window.location.origin}/callback${redirectTo ? `?redirectTo=${encodeURIComponent(redirectTo)}` : ''}`
        }
      })

      if (error) {
        toast.error(error.message || 'Sign in failed')
        return { success: false, error }
      }

      return { success: true, data }
    } catch (error: any) {
      toast.error('An unexpected error occurred')
      return { success: false, error }
    } finally {
      setIsLoading(false)
    }
  }

  const updateProfile = async (profileData: {
    full_name?: string
    display_name?: string
    bio?: string
    avatar_url?: string
  }) => {
    try {
      const { error } = await supabase.auth.updateUser({
        data: profileData
      })

      if (error) {
        toast.error(error.message || 'Profile update failed')
        return { success: false, error }
      }

      toast.success('Your profile has been successfully updated')
      return { success: true }
    } catch (error: any) {
      toast.error('An unexpected error occurred')
      return { success: false, error }
    }
  }

  return {
    user,
    session,
    isLoading,
    isAuthenticated: !!user,
    signOut,
    signInWithOAuth,
    updateProfile,
    supabase
  }
}