import { useState, useEffect } from 'react'
import { 
  refreshStorageUrlIfNeeded, 
  isUrlExpired,
  getRefreshableStorageUrl,
  extractStoragePathFromUrl 
} from '@/lib/storage-urls'

interface UseStorageUrlOptions {
  autoRefresh?: boolean // Automatically refresh when expired
  refreshInterval?: number // Check for expiration every X milliseconds
  bucketName?: string // If provided with filePath, generate URL from scratch
  filePath?: string // Relative file path in the bucket
}

export function useStorageUrl(
  initialUrl: string | null | undefined,
  options: UseStorageUrlOptions = {}
) {
  const { 
    autoRefresh = true, 
    refreshInterval = 60000, // Check every minute by default
    bucketName,
    filePath
  } = options
  
  const [url, setUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Initialize and refresh URL
  useEffect(() => {
    let isMounted = true
    let intervalId: NodeJS.Timeout | null = null

    const refreshUrl = async () => {
      try {
        setLoading(true)
        setError(null)
        
        let freshUrl: string | null = null
        
        // If we have bucket and file path, generate fresh URL
        if (bucketName && filePath) {
          freshUrl = await getRefreshableStorageUrl({
            bucketName,
            filePath
          })
        } 
        // Otherwise refresh the provided URL if needed
        else if (initialUrl) {
          freshUrl = await refreshStorageUrlIfNeeded(initialUrl)
        }
        
        if (isMounted) {
          // If we couldn't refresh but have an initial URL, use it anyway
          setUrl(freshUrl || initialUrl || null)
          setLoading(false)
        }
      } catch (err) {
        if (isMounted) {
          console.warn('Error refreshing storage URL:', err)
          // On error, fall back to initial URL
          setUrl(initialUrl || null)
          setError(err instanceof Error ? err.message : 'Failed to refresh URL')
          setLoading(false)
        }
      }
    }

    // Initial load
    refreshUrl()

    // Set up auto-refresh interval if enabled
    if (autoRefresh && refreshInterval > 0) {
      intervalId = setInterval(() => {
        // Only refresh if the current URL is expired or about to expire
        if (url && isUrlExpired(url)) {
          refreshUrl()
        }
      }, refreshInterval)
    }

    return () => {
      isMounted = false
      if (intervalId) {
        clearInterval(intervalId)
      }
    }
  }, [initialUrl, bucketName, filePath, autoRefresh, refreshInterval])

  // Manual refresh function
  const refresh = async () => {
    try {
      setLoading(true)
      setError(null)
      
      let freshUrl: string | null = null
      
      if (bucketName && filePath) {
        freshUrl = await getRefreshableStorageUrl({
          bucketName,
          filePath
        })
      } else if (url || initialUrl) {
        freshUrl = await refreshStorageUrlIfNeeded(url || initialUrl)
      }
      
      setUrl(freshUrl)
      setLoading(false)
      
      return freshUrl
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to refresh URL')
      setLoading(false)
      return null
    }
  }

  return {
    url,
    loading,
    error,
    refresh,
    isExpired: url ? isUrlExpired(url) : false
  }
}

/**
 * Hook for managing multiple storage URLs
 */
export function useStorageUrls(
  urls: (string | null | undefined)[],
  options: UseStorageUrlOptions = {}
) {
  const [refreshedUrls, setRefreshedUrls] = useState<(string | null)[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let isMounted = true

    const refreshAllUrls = async () => {
      try {
        setLoading(true)
        setError(null)
        
        const promises = urls.map(url => 
          url ? refreshStorageUrlIfNeeded(url) : Promise.resolve(null)
        )
        
        const results = await Promise.all(promises)
        
        if (isMounted) {
          setRefreshedUrls(results)
          setLoading(false)
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : 'Failed to refresh URLs')
          setLoading(false)
        }
      }
    }

    refreshAllUrls()

    return () => {
      isMounted = false
    }
  }, [urls])

  return {
    urls: refreshedUrls,
    loading,
    error
  }
}