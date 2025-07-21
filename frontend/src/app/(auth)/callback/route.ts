import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'
import { NextResponse, type NextRequest } from 'next/server'
import { env } from '@/lib/env'
import type { Database } from '@/lib/supabase'

export async function GET(request: NextRequest) {
  const requestUrl = new URL(request.url)
  const code = requestUrl.searchParams.get('code')
  const redirectTo = requestUrl.searchParams.get('redirectTo')

  if (code) {
    const cookieStore = await cookies()
    const supabase = createServerClient<Database>(
      env.NEXT_PUBLIC_SUPABASE_URL,
      env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
      {
        cookies: {
          getAll() {
            return cookieStore.getAll()
          },
          setAll(cookiesToSet) {
            try {
              cookiesToSet.forEach(({ name, value, options }) =>
                cookieStore.set(name, value, options)
              )
            } catch {
              // The `setAll` method was called from a Server Component.
              // This can be ignored if you have middleware refreshing
              // user sessions.
            }
          },
        },
      }
    )
    
    try {
      const { error } = await supabase.auth.exchangeCodeForSession(code)
      
      if (error) {
        console.error('Auth callback error:', error.message)
        // Redirect to login with error
        return NextResponse.redirect(
          new URL(`/auth/login?error=${encodeURIComponent(error.message)}`, request.url)
        )
      }
      
      // Successful authentication - redirect to intended destination
      const redirectUrl = redirectTo && redirectTo !== '/' 
        ? redirectTo 
        : '/dashboard'
        
      return NextResponse.redirect(new URL(redirectUrl, request.url))
    } catch (error) {
      console.error('Unexpected auth callback error:', error)
      // Handle unexpected errors
      return NextResponse.redirect(
        new URL('/auth/login?error=Authentication failed', request.url)
      )
    }
  }

  // No code provided - redirect to login
  return NextResponse.redirect(new URL('/auth/login', request.url))
}