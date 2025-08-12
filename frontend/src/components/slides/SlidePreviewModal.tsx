'use client'

import { useState, useEffect } from 'react'
import { useSupabaseAuth } from '@/hooks/useSupabaseAuthSimple'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { 
  Download, 
  ExternalLink, 
  RefreshCw, 
  FileText, 
  AlertTriangle,
  Eye,
  X
} from 'lucide-react'
import { toast } from 'sonner'

interface SlideFile {
  id: string
  file_type: string
  file_name: string
  file_url: string
  file_size: number
  created_at: string
  expires_at?: string
}

interface SlideData {
  id: string
  slide_number: number
  title: string
  status: string
  individual_pptx_url?: string
  individual_pptx_size?: number
  processing_time_seconds?: number
  error_message?: string
}

interface SlidePreviewModalProps {
  slide: SlideData | null
  projectId: string
  isOpen: boolean
  onClose: () => void
}

export function SlidePreviewModal({ slide, projectId, isOpen, onClose }: SlidePreviewModalProps) {
  const { session, supabase } = useSupabaseAuth()
  const [slideFiles, setSlideFiles] = useState<SlideFile[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [previewError, setPreviewError] = useState<string | null>(null)

  // Fetch slide files when modal opens
  useEffect(() => {
    if (isOpen && slide && session) {
      fetchSlideFiles()
    }
  }, [isOpen, slide, session]) // eslint-disable-line react-hooks/exhaustive-deps

  const fetchSlideFiles = async () => {
    if (!slide) return

    setIsLoading(true)
    try {
      // Check if user is authenticated
      if (!session?.access_token) {
        console.warn('No valid session found for slide files')
        toast.error('Please sign in to view slide details')
        return
      }

      const response = await fetch(`/api/projects/${projectId}/slides/${slide.id}`, {
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      })
      
      if (!response.ok) {
        const errorText = await response.text()
        console.error('Failed to fetch slide files:', response.status, errorText)
        throw new Error(`Failed to fetch slide files: ${response.status} ${response.statusText}`)
      }

      const data = await response.json()
      console.log('Slide data received:', data)
      
      // Check if data has the expected structure
      if (data && data.files) {
        setSlideFiles(data.files)
      } else if (Array.isArray(data)) {
        // Handle if backend returns array directly
        setSlideFiles(data)
      } else {
        console.warn('Unexpected response structure:', data)
        setSlideFiles([])
      }
      
      // Set preview URL if available
      if (slide.individual_pptx_url) {
        setPreviewUrl(slide.individual_pptx_url)
      }

    } catch (error) {
      console.error('Error fetching slide files:', error)
      toast.error('Failed to load slide files')
    } finally {
      setIsLoading(false)
    }
  }

  const refreshSlideUrl = async () => {
    if (!slide) return

    setIsRefreshing(true)
    try {
      // Check if user is authenticated
      if (!session?.access_token) {
        toast.error('Please sign in to refresh download links')
        return
      }

      const response = await fetch(`/api/projects/${projectId}/slides/${slide.id}/refresh-url`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`
        }
      })

      if (!response.ok) {
        throw new Error('Failed to refresh URL')
      }

      const data = await response.json()
      if (data.success) {
        setPreviewUrl(data.new_url)
        toast.success('Download link refreshed')
      }

    } catch (error) {
      console.error('Error refreshing URL:', error)
      toast.error('Failed to refresh download link')
    } finally {
      setIsRefreshing(false)
    }
  }

  const downloadSlide = async () => {
    if (!slide) return

    try {
      // Check if user is authenticated
      if (!session?.access_token) {
        toast.error('Please sign in to download files')
        return
      }

      // Make authenticated request to get download URL
      const response = await fetch(`/api/projects/${projectId}/slides/${slide.id}/download`, {
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      })

      if (response.ok) {
        // Check if response contains a redirect URL
        const contentType = response.headers.get('content-type')
        if (contentType?.includes('application/json')) {
          const data = await response.json()
          if (data.redirect_url) {
            // Open the signed URL directly
            window.open(data.redirect_url, '_blank')
            toast.success('Download started')
            return
          }
        }
        
        // If it's a direct file response, create a blob URL
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `slide_${slide.slide_number}_${slide.title?.replace(/[^a-zA-Z0-9]/g, '_') || 'untitled'}.pptx`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        window.URL.revokeObjectURL(url)
        toast.success('Download started')
      } else {
        const errorData = await response.json().catch(() => ({ error: 'Download failed' }))
        throw new Error(errorData.error || 'Download failed')
      }
    } catch (error) {
      console.error('Error downloading slide:', error)
      toast.error(`Failed to download slide: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  const openInNewTab = async () => {
    if (!slide || !previewUrl) return

    try {
      // Check if user is authenticated
      if (!session?.access_token) {
        toast.error('Please sign in to view files')
        return
      }

      // Make authenticated request to get download URL
      const response = await fetch(`/api/projects/${projectId}/slides/${slide.id}/download`, {
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      })

      if (response.ok) {
        // Check if response contains a redirect URL
        const contentType = response.headers.get('content-type')
        if (contentType?.includes('application/json')) {
          const data = await response.json()
          if (data.redirect_url) {
            window.open(data.redirect_url, '_blank')
            return
          }
        }
      }
      
      // Fallback to the original URL if available
      window.open(previewUrl, '_blank')
    } catch (error) {
      console.error('Error opening slide:', error)
      // Fallback to the original URL if available
      window.open(previewUrl, '_blank')
    }
  }

  const formatFileSize = (bytes: number) => {
    const units = ['B', 'KB', 'MB', 'GB']
    let size = bytes
    let unitIndex = 0
    
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024
      unitIndex++
    }
    
    return `${size.toFixed(1)} ${units[unitIndex]}`
  }

  if (!slide) return null

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl h-[80vh] flex flex-col">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <div>
              <DialogTitle className="flex items-center gap-2">
                <FileText className="w-5 h-5" />
                Slide {slide.slide_number}: {slide.title || 'Untitled'}
              </DialogTitle>
              <DialogDescription>
                Individual slide preview and download
              </DialogDescription>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant={slide.status === 'completed' ? 'default' : 'secondary'}>
                {slide.status}
              </Badge>
              <Button variant="ghost" size="sm" onClick={onClose}>
                <X className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </DialogHeader>

        <div className="flex-1 flex flex-col gap-4">
          {/* Slide Information */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-neutral-50 dark:bg-neutral-900 rounded-lg">
            <div>
              <label className="text-sm font-medium text-neutral-600 dark:text-neutral-400">Status</label>
              <div className="mt-1">
                <Badge variant={slide.status === 'completed' ? 'default' : 'secondary'}>
                  {slide.status}
                </Badge>
              </div>
            </div>
            
            {slide.individual_pptx_size && (
              <div>
                <label className="text-sm font-medium text-neutral-600 dark:text-neutral-400">File Size</label>
                <div className="mt-1 text-sm">{formatFileSize(slide.individual_pptx_size)}</div>
              </div>
            )}
            
            {slide.processing_time_seconds && (
              <div>
                <label className="text-sm font-medium text-neutral-600 dark:text-neutral-400">Processing Time</label>
                <div className="mt-1 text-sm">{slide.processing_time_seconds}s</div>
              </div>
            )}
          </div>

          {/* Error Message */}
          {slide.error_message && (
            <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-destructive mt-0.5" />
                <div>
                  <p className="font-medium text-destructive">Processing Error</p>
                  <p className="text-sm text-destructive/80 mt-1">{slide.error_message}</p>
                </div>
              </div>
            </div>
          )}

          {/* Preview Section */}
          <div className="flex-1 border rounded-lg p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-medium">Preview</h3>
              <div className="flex gap-2">
                {slide.status === 'completed' && slide.individual_pptx_url && (
                  <>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={refreshSlideUrl}
                      disabled={isRefreshing}
                    >
                      <RefreshCw className={`w-4 h-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
                      Refresh Link
                    </Button>
                    
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={openInNewTab}
                    >
                      <ExternalLink className="w-4 h-4 mr-2" />
                      Open
                    </Button>
                    
                    <Button 
                      size="sm" 
                      onClick={downloadSlide}
                    >
                      <Download className="w-4 h-4 mr-2" />
                      Download
                    </Button>
                  </>
                )}
              </div>
            </div>

            <div className="h-96 border-2 border-dashed border-neutral-200 dark:border-neutral-800 rounded-lg flex items-center justify-center">
              {isLoading ? (
                <div className="flex flex-col items-center gap-4">
                  <Skeleton className="w-16 h-16 rounded" />
                  <Skeleton className="w-32 h-4" />
                </div>
              ) : slide.status === 'completed' && previewUrl ? (
                <div className="text-center">
                  <FileText className="w-16 h-16 mx-auto mb-4 text-neutral-400" />
                  <p className="text-neutral-600 dark:text-neutral-400 mb-4">
                    PowerPoint slide is ready for download
                  </p>
                  <div className="flex gap-2 justify-center">
                    <Button variant="outline" size="sm" onClick={openInNewTab}>
                      <Eye className="w-4 h-4 mr-2" />
                      View File
                    </Button>
                    <Button size="sm" onClick={downloadSlide}>
                      <Download className="w-4 h-4 mr-2" />
                      Download PPTX
                    </Button>
                  </div>
                </div>
              ) : slide.status === 'failed' ? (
                <div className="text-center">
                  <AlertTriangle className="w-16 h-16 mx-auto mb-4 text-destructive" />
                  <p className="text-destructive mb-2">Slide generation failed</p>
                  <p className="text-sm text-neutral-600 dark:text-neutral-400">
                    Check the error message above for details
                  </p>
                </div>
              ) : slide.status === 'completed' && !previewUrl ? (
                <div className="text-center">
                  <AlertTriangle className="w-16 h-16 mx-auto mb-4 text-yellow-500" />
                  <p className="text-neutral-600 dark:text-neutral-400 mb-4">
                    Slide completed but file not available
                  </p>
                  <Button variant="outline" size="sm" onClick={fetchSlideFiles}>
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Retry
                  </Button>
                </div>
              ) : (
                <div className="text-center">
                  <div className="w-16 h-16 mx-auto mb-4 border-2 border-neutral-300 dark:border-neutral-700 rounded-lg flex items-center justify-center">
                    <FileText className="w-8 h-8 text-neutral-400" />
                  </div>
                  <p className="text-neutral-600 dark:text-neutral-400">
                    Slide is still being processed...
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* File List */}
          {slideFiles.length > 0 && (
            <div className="border rounded-lg p-4">
              <h3 className="font-medium mb-3">Associated Files</h3>
              <div className="space-y-2">
                {slideFiles.map((file) => (
                  <div key={file.id} className="flex items-center justify-between p-2 bg-neutral-50 dark:bg-neutral-900 rounded">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-neutral-500" />
                      <div>
                        <p className="text-sm font-medium">{file.file_name}</p>
                        <p className="text-xs text-neutral-500">
                          {file.file_type} • {formatFileSize(file.file_size)}
                        </p>
                      </div>
                    </div>
                    {file.file_url && (
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={() => window.open(file.file_url, '_blank')}
                      >
                        <Download className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}