// Re-export everything for clean imports
export { createClient as createBrowserClient } from './client'
export { createClient as createServerClient } from './server'
export { updateSession } from './middleware'
export type { Database } from '../supabase'