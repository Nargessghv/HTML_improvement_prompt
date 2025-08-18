import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'
import { Database } from '@/lib/supabase'
import { env } from '@/lib/env'

// Define route patterns for different types of pages
const publicRoutes = [
  '/',
  '/health',
]

const authRoutes = [
  '/login',
  '/callback',
]

const protectedRoutes = [
  '/dashboard',
  '/projects',
  '/workflow',
  '/settings',
]

function isPublicRoute(pathname: string): boolean {
  return publicRoutes.some(route => pathname === route || pathname.startsWith(`${route}/`))
}

function isAuthRoute(pathname: string): boolean {
  return authRoutes.some(route => pathname === route || pathname.startsWith(`${route}/`))
}

function isProtectedRoute(pathname: string): boolean {
  return protectedRoutes.some(route => pathname === route || pathname.startsWith(`${route}/`))
}

export async function updateSession(request: NextRequest) {
  const { pathname } = request.nextUrl
  
  // Debug logging for development
  console.log('🔐 Middleware called for:', pathname)
  
  // Skip middleware for API routes and static files
  if (pathname.startsWith('/api/') || pathname.startsWith('/_next/')) {
    console.log('⏭️  Skipping middleware for API/static route:', pathname)
    return NextResponse.next()
  }

  const supabaseResponse = NextResponse.next({
    request,
  })

  const supabase = createServerClient<Database>(
    env.NEXT_PUBLIC_SUPABASE_URL,
    env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) => {
            request.cookies.set(name, value)
            supabaseResponse.cookies.set(name, value, options)
          })
        },
      },
    }
  )

  // IMPORTANT: Avoid writing any logic between createServerClient and
  // supabase.auth.getUser(). A simple mistake could make it very hard to debug
  // issues with users being randomly logged out.

  const {
    data: { user }
  } = await supabase.auth.getUser()

  console.log('👤 User status:', user ? `Authenticated (${user.email})` : 'Not authenticated')
  console.log('🛣️  Route type:', {
    isPublic: isPublicRoute(pathname),
    isAuth: isAuthRoute(pathname), 
    isProtected: isProtectedRoute(pathname)
  })

  // Handle authentication redirects based on route type and user status
  
  // If user is authenticated and trying to access auth routes, redirect to dashboard
  if (user && isAuthRoute(pathname)) {
    console.log('↩️  Redirecting authenticated user from auth route to dashboard')
    const url = request.nextUrl.clone()
    url.pathname = '/dashboard'
    return NextResponse.redirect(url)
  }

  // If user is not authenticated and trying to access protected routes, redirect to login
  if (!user && isProtectedRoute(pathname)) {
    console.log('🚫 Redirecting unauthenticated user to login')
    const url = request.nextUrl.clone()
    url.pathname = '/login'
    // Preserve the attempted URL for post-login redirect
    url.searchParams.set('redirectTo', pathname)
    return NextResponse.redirect(url)
  }

  // Allow access to public routes regardless of auth status
  if (isPublicRoute(pathname)) {
    return supabaseResponse
  }

  // Default redirect for unauthenticated users on unknown routes
  if (!user && !isAuthRoute(pathname) && !isPublicRoute(pathname)) {
    const url = request.nextUrl.clone()
    url.pathname = '/login'
    url.searchParams.set('redirectTo', pathname)
    return NextResponse.redirect(url)
  }

  // IMPORTANT: You *must* return the supabaseResponse object as it is. If you're
  // creating a new response object with NextResponse.next() make sure to:
  // 1. Pass the request in it, like so:
  //    const myNewResponse = NextResponse.next({ request })
  // 2. Copy over the cookies, like so:
  //    myNewResponse.cookies.setAll(supabaseResponse.cookies.getAll())
  // 3. Change the myNewResponse object instead of the supabaseResponse object

  return supabaseResponse
}