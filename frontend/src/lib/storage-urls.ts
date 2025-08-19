import type { SupabaseClient } from '@supabase/supabase-js'

interface StorageUrlOptions {
  bucketName: string
  filePath: string
  expiresIn?: number // seconds, default 3600 (1 hour)
}

interface RefreshableUrl {
  url: string
  expiresAt: Date
  filePath: string
  bucketName: string
}

const urlCache = new Map<string, RefreshableUrl>()

// Lazy load the Supabase client to avoid initialization issues
let supabaseClient: SupabaseClient | null = null

function getSupabaseClient(): SupabaseClient | null {
  try {
    if (!supabaseClient) {
      // Check if we're in a browser environment and env vars are available
      if (typeof window !== 'undefined' && 
          process.env.NEXT_PUBLIC_SUPABASE_URL && 
          process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
        // Only import and create client when actually needed
        const { createClient } = require('@/lib/supabase/client')
        supabaseClient = createClient()
      }
    }
    return supabaseClient
  } catch (error) {
    console.warn('Could not initialize Supabase client:', error)
    return null
  }
}

/**
 * Extract the storage path from a Supabase storage URL
 */
export function extractStoragePathFromUrl(url: string): { bucketName: string; filePath: string } | null {
  try {
    // Handle both signed URLs and public URLs
    const urlObj = new URL(url)
    const pathname = urlObj.pathname
    
    // Pattern 1: /storage/v1/object/sign/bucket-name/path/to/file
    const signedMatch = pathname.match(/\/storage\/v1\/object\/sign\/([^/]+)\/(.+)/)
    if (signedMatch) {
      return {
        bucketName: signedMatch[1],
        filePath: decodeURIComponent(signedMatch[2])
      }
    }
    
    // Pattern 2: /storage/v1/object/public/bucket-name/path/to/file
    const publicMatch = pathname.match(/\/storage\/v1\/object\/public\/([^/]+)\/(.+)/)
    if (publicMatch) {
      return {
        bucketName: publicMatch[1],
        filePath: decodeURIComponent(publicMatch[2])
      }
    }
    
    // Pattern 3: Direct bucket path (for relative paths stored in DB)
    const directMatch = pathname.match(/^\/([^/]+)\/(.+)/)
    if (directMatch) {
      return {
        bucketName: directMatch[1],
        filePath: decodeURIComponent(directMatch[2])
      }
    }
    
    return null
  } catch (error) {
    console.error('Error extracting storage path:', error)
    return null
  }
}

/**
 * Check if a signed URL has expired based on the exp claim in the URL
 */
export function isUrlExpired(url: string): boolean {
  try {
    const urlObj = new URL(url)
    const token = urlObj.searchParams.get('token')
    
    if (!token) {
      // Not a signed URL, might be a public URL
      return false
    }
    
    // Try to decode the JWT token to check expiration
    const payload = token.split('.')[1]
    if (!payload) return true
    
    const decoded = JSON.parse(atob(payload))
    const exp = decoded.exp
    
    if (!exp) return true
    
    // Check if expired (with 5 minute buffer for safety)
    const now = Math.floor(Date.now() / 1000)
    return now >= (exp - 300) // Consider expired 5 minutes before actual expiration
  } catch (error) {
    // If we can't parse the URL or token, assume it's expired to be safe
    console.warn('Could not check URL expiration:', error)
    return true
  }
}

/**
 * Get a fresh signed URL for a storage file, with caching
 */
export async function getRefreshableStorageUrl(options: StorageUrlOptions): Promise<string | null> {
  const { bucketName, filePath, expiresIn = 3600 } = options
  const cacheKey = `${bucketName}/${filePath}`
  
  // Check cache first
  const cached = urlCache.get(cacheKey)
  if (cached && cached.expiresAt > new Date()) {
    return cached.url
  }
  
  try {
    const supabase = getSupabaseClient()
    if (!supabase) {
      // Can't refresh without Supabase client
      console.warn('Supabase client not available for URL refresh')
      return null
    }
    
    const { data, error } = await supabase.storage
      .from(bucketName)
      .createSignedUrl(filePath, expiresIn)
    
    if (error) {
      console.error('Error creating signed URL:', error)
      return null
    }
    
    if (data?.signedUrl) {
      // Cache the URL with its expiration time
      urlCache.set(cacheKey, {
        url: data.signedUrl,
        expiresAt: new Date(Date.now() + (expiresIn - 60) * 1000), // Expire 1 minute early
        filePath,
        bucketName
      })
      
      return data.signedUrl
    }
    
    return null
  } catch (error) {
    console.error('Error getting storage URL:', error)
    return null
  }
}

/**
 * Refresh a storage URL if it's expired or about to expire
 */
export async function refreshStorageUrlIfNeeded(url: string | null | undefined): Promise<string | null> {
  if (!url) return null
  
  try {
    // Check if URL is expired
    if (!isUrlExpired(url)) {
      return url
    }
    
    // Extract storage path from the expired URL
    const pathInfo = extractStoragePathFromUrl(url)
    if (!pathInfo) {
      console.warn('Could not extract storage path from URL, returning original:', url)
      // Return the original URL if we can't parse it - it might still work
      return url
    }
    
    // Try to get a fresh URL
    const freshUrl = await getRefreshableStorageUrl({
      bucketName: pathInfo.bucketName,
      filePath: pathInfo.filePath
    })
    
    // If we couldn't refresh, return the original URL (might still work or fail gracefully)
    return freshUrl || url
  } catch (error) {
    console.warn('Error in refreshStorageUrlIfNeeded, returning original URL:', error)
    // Return the original URL on any error
    return url
  }
}

/**
 * Hook-friendly version that returns both the URL and a loading state
 */
export async function useRefreshableStorageUrl(
  initialUrl: string | null | undefined,
  options?: { autoRefresh?: boolean }
): Promise<{ url: string | null; loading: boolean }> {
  if (!initialUrl) {
    return { url: null, loading: false }
  }
  
  // For synchronous initial return, check if we have a cached version
  const pathInfo = extractStoragePathFromUrl(initialUrl)
  if (pathInfo) {
    const cacheKey = `${pathInfo.bucketName}/${pathInfo.filePath}`
    const cached = urlCache.get(cacheKey)
    if (cached && cached.expiresAt > new Date()) {
      return { url: cached.url, loading: false }
    }
  }
  
  // If expired or not cached, refresh
  const refreshedUrl = await refreshStorageUrlIfNeeded(initialUrl)
  return { url: refreshedUrl, loading: false }
}

/**
 * Clear the URL cache (useful for testing or when user logs out)
 */
export function clearStorageUrlCache() {
  urlCache.clear()
}

/**
 * Convert a relative storage path to a refreshable URL
 */
export async function storagePathToUrl(
  bucketName: string,
  filePath: string | null | undefined
): Promise<string | null> {
  if (!filePath) return null
  
  return getRefreshableStorageUrl({
    bucketName,
    filePath
  })
}