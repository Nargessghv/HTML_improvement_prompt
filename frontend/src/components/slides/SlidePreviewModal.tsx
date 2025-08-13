'use client'

import { useState, useEffect } from 'react'
import { useSupabaseAuth } from '@/hooks/useSupabaseAuthSimple'
import { RefinementModal } from '@/components/refinement/RefinementModal'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'
import { Card, CardContent } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { 
  Download, 
  ExternalLink, 
  RefreshCw, 
  FileText, 
  AlertTriangle,
  Eye,
  X,
  Sparkles,
  Clock,
  Monitor,
  History,
  ChevronDown
} from 'lucide-react'
import { toast } from 'sonner'

interface SlideFile {
  id: string
  file_type: string
  file_name: string
  file_url: string
  file_size?: number
  created_at: string
  expires_at?: string
  metadata?: any
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

interface RefinementIteration {
  id: string
  iteration_number: number
  html_content: string
  html_file_url?: string
  image_file_url?: string
  pptx_file_url?: string
  refinement_feedback?: string
  is_final: boolean
  created_at: string
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
  const [refinementCount, setRefinementCount] = useState<number>(0)
  const [hasHtmlContent, setHasHtmlContent] = useState(false)
  const [showRefinementModal, setShowRefinementModal] = useState(false)
  const [refinementIterations, setRefinementIterations] = useState<RefinementIteration[]>([])
  const [selectedIteration, setSelectedIteration] = useState<string>('latest')
  const [currentPptxUrl, setCurrentPptxUrl] = useState<string>('')
  const [availableContent, setAvailableContent] = useState({
    hasHtml: false,
    hasImage: false,
    hasPptx: false,
    hasVersions: false
  })

  // Fetch slide files when modal opens
  useEffect(() => {
    if (isOpen && slide && session) {
      fetchSlideFiles()
      fetchRefinementInfo()
    }
  }, [isOpen, slide, session]) // eslint-disable-line react-hooks/exhaustive-deps
  
  // Set up real-time subscriptions for HTML refinements
  useEffect(() => {
    if (!isOpen || !slide || !supabase) return
    
    console.log('Setting up real-time subscription for slide:', slide.id)
    
    // Subscribe to changes in slides table for this specific slide
    const slideSubscription = supabase
      .channel(`slide-${slide.id}`)
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'slides',
          filter: `id=eq.${slide.id}`
        },
        (payload) => {
          console.log('Slide updated:', payload)
          // Refresh refinement info when slide changes
          fetchRefinementInfo()
        }
      )
      .subscribe()
    
    // Subscribe to HTML refinements for this slide
    const refinementSubscription = supabase
      .channel(`html-refinements-${slide.id}`)
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public', 
          table: 'html_refinements',
          filter: `slide_id=eq.${slide.id}`
        },
        (payload) => {
          console.log('HTML refinement updated:', payload)
          // Refresh refinement info when new iterations are added
          fetchRefinementInfo()
        }
      )
      .subscribe()
    
    return () => {
      console.log('Cleaning up subscriptions for slide:', slide.id)
      slideSubscription.unsubscribe()
      refinementSubscription.unsubscribe()
    }
  }, [isOpen, slide, supabase]) // eslint-disable-line react-hooks/exhaustive-deps
  
  const fetchRefinementInfo = async () => {
    if (!slide || !supabase) return
    
    try {
      // Check if slide has HTML content
      const { data: slideData } = await supabase
        .from('slides')
        .select('html_content, refined_html, individual_pptx_url')
        .eq('id', slide.id)
        .single()
      
      let contentAvailable = {
        hasHtml: false,
        hasImage: false,
        hasPptx: false,
        hasVersions: false
      }
      
      if (slideData) {
        contentAvailable.hasHtml = !!(slideData.html_content || slideData.refined_html)
        contentAvailable.hasPptx = !!slideData.individual_pptx_url
        setHasHtmlContent(contentAvailable.hasHtml)
        
        // Set current PPTX URL from slide (base version) as fallback
        if (slideData.individual_pptx_url) {
          setCurrentPptxUrl(slideData.individual_pptx_url)
        }
      }
      
      // Get all refinement iterations
      const { data: refinements, count } = await supabase
        .from('html_refinements')
        .select('*')
        .eq('slide_id', slide.id)
        .order('iteration_number', { ascending: true })
      
      setRefinementCount(count || 0)
      setRefinementIterations(refinements || [])
      
      if (refinements && refinements.length > 0) {
        contentAvailable.hasVersions = true
        contentAvailable.hasImage = refinements.some(r => r.image_file_url)
        
        // Update hasPptx if any refinement has PPTX
        if (!contentAvailable.hasPptx) {
          contentAvailable.hasPptx = refinements.some(r => r.pptx_file_url)
        }
        
        // Update hasHtml if any refinement has HTML content
        if (!contentAvailable.hasHtml) {
          contentAvailable.hasHtml = refinements.some(r => r.html_content)
        }
        
        // Set the latest iteration's PPTX URL as default
        const latestIteration = refinements[refinements.length - 1]
        if (selectedIteration === 'latest' && latestIteration.pptx_file_url) {
          setCurrentPptxUrl(latestIteration.pptx_file_url)
        }
      }
      
      setAvailableContent(contentAvailable)
    } catch (error) {
      console.error('Error fetching refinement info:', error)
    }
  }

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

  const handleVersionChange = (versionId: string) => {
    setSelectedIteration(versionId)
    
    if (versionId === 'latest') {
      // Show the latest refinement iteration PPTX or slide content
      if (refinementIterations.length > 0) {
        const latestIteration = refinementIterations[refinementIterations.length - 1]
        if (latestIteration.pptx_file_url) {
          setCurrentPptxUrl(latestIteration.pptx_file_url)
        }
      }
    } else if (versionId === 'original') {
      // Show original slide PPTX from slides table
      if (slide?.individual_pptx_url) {
        setCurrentPptxUrl(slide.individual_pptx_url)
      }
    } else {
      // Show specific iteration PPTX
      const iteration = refinementIterations.find(r => r.id === versionId)
      if (iteration && iteration.pptx_file_url) {
        setCurrentPptxUrl(iteration.pptx_file_url)
      }
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
    <>
      <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-6xl h-[90vh] flex flex-col p-0" showCloseButton={false}>
        <DialogHeader className="sr-only">
          <DialogTitle>
            Slide {slide.slide_number}: {slide.title || 'Untitled'} - Preview and Download
          </DialogTitle>
        </DialogHeader>
        
        {/* Clean white header with subtle red accents */}
        <div className="bg-white border-b border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="bg-red-50 border border-red-200 rounded-lg p-2">
                <FileText className="w-5 h-5 text-red-600" />
              </div>
              <div className="flex-1">
                <h2 className="text-lg font-semibold text-gray-900 mb-1">
                  Slide {slide.slide_number}: {slide.title || 'Untitled'}
                </h2>
                <div className="flex items-center gap-3 text-sm text-gray-600">
                  <span>Individual slide preview and download</span>
                  <Badge 
                    variant={slide.status === 'completed' ? 'default' : 'secondary'} 
                    className={`text-xs ${
                      slide.status === 'completed' 
                        ? 'bg-green-100 text-green-800 border-green-200' 
                        : 'bg-gray-100 text-gray-600 border-gray-200'
                    }`}
                  >
                    {slide.status}
                  </Badge>
                  {slide.individual_pptx_size && (
                    <span className="text-gray-500">{formatFileSize(slide.individual_pptx_size)}</span>
                  )}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2 ml-4">
              {/* Open button - enabled when PPTX is available */}
              <Button 
                variant="outline" 
                size="sm" 
                onClick={openInNewTab}
                disabled={!availableContent.hasPptx}
                className={`h-9 ${
                  availableContent.hasPptx 
                    ? 'border-gray-300 text-gray-700 hover:bg-gray-50' 
                    : 'border-gray-200 text-gray-400 cursor-not-allowed'
                }`}
                title={availableContent.hasPptx ? 'Open slide in new tab' : 'PPTX not yet available'}
              >
                <ExternalLink className="w-4 h-4 mr-2" />
                Open
              </Button>
              
              {/* Download button - enabled when PPTX is available */}
              <Button 
                size="sm" 
                onClick={downloadSlide}
                disabled={!availableContent.hasPptx}
                className={`h-9 font-medium ${
                  availableContent.hasPptx 
                    ? 'bg-red-600 text-white hover:bg-red-700' 
                    : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                }`}
                title={availableContent.hasPptx ? 'Download slide PPTX' : 'PPTX not yet available'}
              >
                <Download className="w-4 h-4 mr-2" />
                Download
              </Button>
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  onClose()
                }} 
                className="h-9 w-9 p-0 text-gray-400 hover:text-gray-600 hover:bg-gray-100"
              >
                <X className="w-5 h-5" />
              </Button>
            </div>
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 flex flex-col p-4 gap-4">
          {/* Processing Status */}
          <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${
                  slide.status === 'completed' ? 'bg-green-500' : 
                  slide.status === 'failed' ? 'bg-red-500' : 
                  'bg-blue-500 animate-pulse'
                }`}></div>
                <h3 className="text-sm font-semibold text-blue-800">
                  Processing Status: {slide.status.replace(/_/g, ' ').toUpperCase()}
                </h3>
              </div>
              {slide.processing_time_seconds && (
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-blue-600" />
                  <span className="text-sm font-medium text-blue-700">
                    {slide.processing_time_seconds}s
                  </span>
                </div>
              )}
            </div>
            
            {/* Available Content Indicators */}
            <div className="grid grid-cols-4 gap-3">
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${availableContent.hasHtml ? 'bg-green-500' : 'bg-gray-300'}`}></div>
                <span className={`text-xs font-medium ${availableContent.hasHtml ? 'text-green-700' : 'text-gray-500'}`}>
                  HTML Generated
                </span>
              </div>
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${availableContent.hasImage ? 'bg-green-500' : 'bg-gray-300'}`}></div>
                <span className={`text-xs font-medium ${availableContent.hasImage ? 'text-green-700' : 'text-gray-500'}`}>
                  Image Rendered
                </span>
              </div>
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${availableContent.hasPptx ? 'bg-green-500' : 'bg-gray-300'}`}></div>
                <span className={`text-xs font-medium ${availableContent.hasPptx ? 'text-green-700' : 'text-gray-500'}`}>
                  PPTX Created
                </span>
              </div>
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${availableContent.hasVersions ? 'bg-green-500' : 'bg-gray-300'}`}></div>
                <span className={`text-xs font-medium ${availableContent.hasVersions ? 'text-green-700' : 'text-gray-500'}`}>
                  Versions Available
                </span>
              </div>
            </div>
          </div>
          
          {/* HTML Refinements and Processing Info */}
          {(hasHtmlContent || slide.processing_time_seconds) && (
            <div className="p-4 bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-4">
                  {slide.processing_time_seconds && (
                    <div className="flex items-center gap-2">
                      <Clock className="w-4 h-4 text-gray-500" />
                      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Generated in {slide.processing_time_seconds}s
                      </span>
                    </div>
                  )}
                </div>
                {hasHtmlContent && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowRefinementModal(true)}
                    className="h-8 px-4 bg-purple-50 border-purple-200 text-purple-700 hover:bg-purple-100 hover:border-purple-300"
                  >
                    <Sparkles className="w-4 h-4 mr-2 text-purple-500" />
                    <span className="text-sm font-medium">
                      View {refinementCount} iteration{refinementCount !== 1 ? 's' : ''}
                    </span>
                  </Button>
                )}
              </div>
              
              {/* Version Dropdown - Show if ANY versions are available (HTML or PPTX) */}
              {availableContent.hasVersions && refinementIterations.length > 0 && (
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2">
                    <History className="w-4 h-4 text-gray-500" />
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Version:</span>
                  </div>
                  <Select value={selectedIteration} onValueChange={handleVersionChange}>
                    <SelectTrigger className="w-48 h-8 text-sm">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {refinementIterations.length > 0 && (
                        <SelectItem value="latest">
                          <div className="flex items-center gap-2">
                            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                            Latest (v{refinementIterations.length})
                            {refinementIterations[refinementIterations.length - 1]?.pptx_file_url && 
                              <span className="text-xs bg-green-100 text-green-700 px-1 rounded">PPTX</span>
                            }
                          </div>
                        </SelectItem>
                      )}
                      {refinementIterations.slice().reverse().map((iteration) => (
                        <SelectItem key={iteration.id} value={iteration.id}>
                          <div className="flex items-center gap-2">
                            <div className={`w-2 h-2 rounded-full ${
                              iteration.pptx_file_url ? 'bg-green-500' : 
                              iteration.html_content ? 'bg-blue-500' : 'bg-gray-400'
                            }`}></div>
                            Version {iteration.iteration_number}
                            {iteration.is_final && <span className="text-xs text-blue-600">(Final)</span>}
                            {iteration.pptx_file_url && 
                              <span className="text-xs bg-green-100 text-green-700 px-1 rounded">PPTX</span>
                            }
                            {iteration.html_content && !iteration.pptx_file_url &&
                              <span className="text-xs bg-blue-100 text-blue-700 px-1 rounded">HTML</span>
                            }
                            <span className="text-xs text-gray-500">
                              {new Date(iteration.created_at).toLocaleDateString()}
                            </span>
                          </div>
                        </SelectItem>
                      ))}
                      {(slide?.html_content || slide?.refined_html) && (
                        <SelectItem value="original">
                          <div className="flex items-center gap-2">
                            <div className="w-2 h-2 bg-gray-300 rounded-full"></div>
                            Original
                            <span className="text-xs bg-gray-100 text-gray-600 px-1 rounded">HTML</span>
                          </div>
                        </SelectItem>
                      )}
                    </SelectContent>
                  </Select>
                </div>
              )}
            </div>
          )}

          {/* Error Message */}
          {slide.error_message && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-start gap-3">
                <div className="bg-red-100 rounded-full p-1.5">
                  <AlertTriangle className="w-5 h-5 text-red-600" />
                </div>
                <div>
                  <p className="font-semibold text-red-800">Processing Error</p>
                  <p className="text-sm text-red-700 mt-1 leading-relaxed">{slide.error_message}</p>
                </div>
              </div>
            </div>
          )}

          {/* Preview Section - 16:9 Aspect Ratio */}
          <div className="flex-1">
            <Card className="h-full border-2 border-gray-200 dark:border-gray-700 shadow-lg">
              <CardContent className="p-0">
                <div className="w-full" style={{ aspectRatio: '16/9' }}>
                  <div className="w-full h-full rounded-lg overflow-hidden bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700">
                    {(() => {
                      // Show PPTX version if available
                      if (currentPptxUrl && availableContent.hasPptx) {
                        const officeViewerUrl = `https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(currentPptxUrl)}`
                        return (
                          <div className="w-full h-full relative">
                            <iframe
                              src={officeViewerUrl}
                              className="w-full h-full border-0"
                              title={`Slide ${slide.slide_number} PPTX Preview - ${
                                selectedIteration === 'latest' 
                                  ? 'Latest' 
                                  : selectedIteration === 'original' 
                                  ? 'Original' 
                                  : `Version ${refinementIterations.find(r => r.id === selectedIteration)?.iteration_number}`
                              }`}
                              allowFullScreen
                            />
                            <div className="absolute top-2 right-2 bg-black/70 text-white px-2 py-1 rounded text-xs">
                              {selectedIteration === 'latest' 
                                ? `Latest (v${refinementIterations.filter(r => r.pptx_file_url).length})` 
                                : selectedIteration === 'original' 
                                ? 'Original' 
                                : `Version ${refinementIterations.find(r => r.id === selectedIteration)?.iteration_number}`
                              }
                            </div>
                          </div>
                        )
                      }
                      
                      // Show HTML content based on selected version or latest available
                      if (availableContent.hasHtml && (refinementIterations.length > 0 || slide.html_content || slide.refined_html)) {
                        let htmlContent = ''
                        let versionLabel = ''
                        
                        if (selectedIteration === 'latest') {
                          // Show the latest refinement iteration
                          const latestIteration = refinementIterations[refinementIterations.length - 1]
                          htmlContent = latestIteration?.html_content || slide.refined_html || slide.html_content
                          versionLabel = `Latest HTML (v${refinementIterations.length})`
                        } else if (selectedIteration === 'original') {
                          // Show original slide HTML content
                          htmlContent = slide.html_content || slide.refined_html || ''
                          versionLabel = 'Original HTML'
                        } else {
                          // Show specific iteration
                          const iteration = refinementIterations.find(r => r.id === selectedIteration)
                          if (iteration) {
                            htmlContent = iteration.html_content
                            versionLabel = `HTML v${iteration.iteration_number}`
                          }
                        }
                        
                        if (htmlContent) {
                          return (
                            <div className="w-full h-full relative">
                              <iframe
                                srcDoc={htmlContent}
                                className="w-full h-full border-0"
                                title={`Slide ${slide.slide_number} HTML Preview - ${versionLabel}`}
                                sandbox="allow-same-origin allow-scripts"
                              />
                              <div className={`absolute top-2 right-2 text-white px-2 py-1 rounded text-xs ${
                                availableContent.hasPptx ? 'bg-green-600/80' : 'bg-yellow-600/80'
                              }`}>
                                {versionLabel} {!availableContent.hasPptx && '(PPTX Processing...)'}
                              </div>
                            </div>
                          )
                        }
                      }
                      
                      // Show image if available but no HTML/PPTX
                      if (availableContent.hasImage && !availableContent.hasHtml && refinementIterations.length > 0) {
                        const latestIteration = refinementIterations[refinementIterations.length - 1]
                        if (latestIteration?.image_file_url) {
                          return (
                            <div className="w-full h-full relative flex items-center justify-center">
                              <img 
                                src={latestIteration.image_file_url} 
                                alt={`Slide ${slide.slide_number} Preview`}
                                className="max-w-full max-h-full object-contain"
                              />
                              <div className="absolute top-2 right-2 bg-blue-600/80 text-white px-2 py-1 rounded text-xs">
                                Image Preview (Processing...)
                              </div>
                            </div>
                          )
                        }
                      }
                      
                      // If no content is available yet, show processing state
                      if (!availableContent.hasHtml && !availableContent.hasImage && !availableContent.hasPptx) {
                        return (
                          <div className="flex items-center justify-center h-full">
                            <div className="text-center">
                              <div className="w-16 h-16 mx-auto mb-4 border-4 border-blue-200 border-t-blue-500 rounded-full animate-spin"></div>
                              <h3 className="text-lg font-medium text-gray-900 mb-2">
                                Processing Slide {slide.slide_number}
                              </h3>
                              <p className="text-gray-600 mb-4">
                                Status: {slide.status.replace(/_/g, ' ')}
                              </p>
                              <div className="text-sm text-gray-500">
                                {slide.status === 'pending' && 'Waiting to start processing...'}
                                {slide.status === 'planning' && 'Planning slide content...'}
                                {slide.status === 'content_generation' && 'Generating content...'}
                                {slide.status === 'html_generation' && 'Creating HTML visualization...'}
                                {slide.status === 'html_refinement' && 'Refining HTML content...'}
                                {slide.status === 'image_generation' && 'Generating images...'}
                                {slide.current_agent && (
                                  <div className="mt-2 text-xs text-blue-600">
                                    Current: {slide.current_agent}
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        )
                      }
                      
                      const thumbnailFile = slideFiles.find(f => f.file_type === 'preview_image')
                      
                      if (isLoading) {
                        return (
                          <div className="flex flex-col items-center gap-4">
                            <Skeleton className="w-24 h-24 rounded" />
                            <Skeleton className="w-48 h-4" />
                            <Skeleton className="w-32 h-4" />
                          </div>
                        )
                      }
                      
                      if (thumbnailFile?.file_url) {
                        return (
                          <div className="w-full flex justify-center">
                            <img 
                              src={thumbnailFile.file_url} 
                              alt={`Slide ${slide.slide_number} preview`}
                              className="max-w-full h-auto rounded-lg shadow-lg border"
                              style={{ maxHeight: '500px', maxWidth: '100%' }}
                              onError={() => {
                                console.error('Failed to load thumbnail image')
                                setPreviewError('Failed to load preview image')
                              }}
                            />
                          </div>
                        )
                      }
                      
                      if (slide.status === 'completed' && previewUrl) {
                        return (
                          <iframe
                            src={`https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(previewUrl)}`}
                            className="w-full h-full"
                            title={`Slide ${slide.slide_number} Preview`}
                            onError={() => {
                              console.error('Failed to load PPTX viewer')
                              setPreviewError('Failed to load PPTX viewer')
                            }}
                          />
                        )
                      }
                      
                      if (slide.status === 'failed') {
                        return (
                          <div className="flex items-center justify-center h-full">
                            <div className="text-center">
                              <AlertTriangle className="w-16 h-16 mx-auto mb-4 text-destructive" />
                              <p className="text-destructive mb-2 font-medium">Slide generation failed</p>
                              <p className="text-sm text-neutral-600 dark:text-neutral-400">
                                Check the error message for details
                              </p>
                            </div>
                          </div>
                        )
                      }
                      
                      if (slide.status === 'completed' && !previewUrl) {
                        return (
                          <div className="flex items-center justify-center h-full">
                            <div className="text-center">
                              <AlertTriangle className="w-16 h-16 mx-auto mb-4 text-yellow-500" />
                              <p className="text-neutral-600 dark:text-neutral-400 mb-4 font-medium">
                                Slide completed but file not available
                              </p>
                              <Button variant="outline" size="sm" onClick={fetchSlideFiles}>
                                <RefreshCw className="w-4 h-4 mr-2" />
                                Retry Loading
                              </Button>
                            </div>
                          </div>
                        )
                      }
                      
                      return (
                        <div className="flex items-center justify-center h-full">
                          <div className="text-center">
                            <div className="w-16 h-16 mx-auto mb-4 border-2 border-neutral-300 dark:border-neutral-700 rounded-lg flex items-center justify-center">
                              <FileText className="w-8 h-8 text-neutral-400" />
                            </div>
                            <p className="text-neutral-600 dark:text-neutral-400 font-medium">
                              Slide is being processed...
                            </p>
                            <div className="mt-3 w-32 mx-auto">
                              <div className="h-1 bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden">
                                <div className="h-full bg-red-600 rounded-full animate-pulse" style={{ width: '60%' }}></div>
                              </div>
                            </div>
                          </div>
                        </div>
                      )
                    })()}
                  </div>
                </div>
              </CardContent>
            </Card>
            
            {/* Attribution */}
            {slide.status === 'completed' && previewUrl && (
              <div className="mt-3 text-center">
                <div className="flex items-center justify-center gap-2 text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-800 rounded-full px-3 py-1.5 inline-flex">
                  <Monitor className="w-3.5 h-3.5" />
                  <span>Live PowerPoint Preview • Powered by Microsoft Office Online</span>
                </div>
              </div>
            )}
          </div>

        </div>
      </DialogContent>
    </Dialog>

    {/* Refinement Modal */}
    {hasHtmlContent && slide && (
      <RefinementModal
        open={showRefinementModal}
        onOpenChange={setShowRefinementModal}
        projectId={projectId}
        slideId={slide.id}
      />
    )}
    </>
  )
}