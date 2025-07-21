// Custom middleware functions
// Re-export all middleware from this directory

// Example exports (to be implemented):
// export { authMiddleware } from './authMiddleware'
// export { rateLimitMiddleware } from './rateLimitMiddleware'
// export { loggingMiddleware } from './loggingMiddleware'

// API Middleware helpers
export type MiddlewareFunction<T = unknown> = (
  req: Request,
  context?: T
) => Promise<Response | void>

// Error handling middleware
export const errorHandler = (error: Error): Response => {
  console.error('Middleware error:', error)
  
  return new Response(
    JSON.stringify({
      error: 'Internal server error',
      message: process.env.NODE_ENV === 'development' ? error.message : 'Something went wrong',
    }),
    {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    }
  )
}

// CORS middleware helper
export const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
}

// Request validation middleware
export const validateRequest = async <T>(
  request: Request,
  schema: (data: unknown) => { success: boolean; data?: T; errors?: string[] }
): Promise<{ success: true; data: T } | { success: false; response: Response }> => {
  try {
    const body = await request.json()
    const validation = schema(body)
    
    if (!validation.success) {
      return {
        success: false,
        response: new Response(
          JSON.stringify({
            error: 'Validation failed',
            details: validation.errors,
          }),
          {
            status: 400,
            headers: { 'Content-Type': 'application/json' },
          }
        ),
      }
    }
    
    return { success: true, data: validation.data! }
  } catch (_error) {
    return {
      success: false,
      response: new Response(
        JSON.stringify({
          error: 'Invalid JSON',
          message: 'Request body must be valid JSON',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      ),
    }
  }
}

// Placeholder - remove when actual middleware are added
export const customMiddleware = {
  // Custom middleware functions will be exported here
}