'use client'

import { useState, useEffect } from 'react'
import { useSupabaseAuth } from '@/hooks/useSupabaseAuthSimple'
import { refreshStorageUrlIfNeeded } from '@/lib/storage-urls'
import { RefinementModal } from '@/components/refinement/RefinementModal'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Card, CardContent } from '@/components/ui/card'
import { 
  Download, 
  ExternalLink, 
  FileText, 
  AlertTriangle,
  X,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  Maximize2,
  Image as ImageIcon,
  ChevronUp,
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
  slides?: SlideData[]  // All slides for navigation
  projectId: string
  isOpen: boolean
  onClose: () => void
  onSlideChange?: (slide: SlideData) => void  // Callback for slide navigation
}

export function SlidePreviewModal({ slide, slides = [], projectId, isOpen, onClose, onSlideChange }: SlidePreviewModalProps) {
  const { session, supabase } = useSupabaseAuth() // Use the supabase from the hook
  const [slideFiles, setSlideFiles] = useState<SlideFile[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [previewError, setPreviewError] = useState<string | null>(null)
  const [refinementCount, setRefinementCount] = useState<number>(0)
  const [hasHtmlContent, setHasHtmlContent] = useState(false)
  const [showRefinementModal, setShowRefinementModal] = useState(false)
  const [refinementIterations, setRefinementIterations] = useState<RefinementIteration[]>([])
  const [currentPptxUrl, setCurrentPptxUrl] = useState<string>('')
  const [availableContent, setAvailableContent] = useState({
    hasHtml: false,
    hasImage: false,
    hasPptx: false,
    hasVersions: false
  })
  const [showFullscreen, setShowFullscreen] = useState(false)
  const [showIterationsCarousel, setShowIterationsCarousel] = useState(false)
  const [previewImageUrl, setPreviewImageUrl] = useState<string | null>(null)
  const [selectedIterationIndex, setSelectedIterationIndex] = useState(0)
  
  // Navigation state
  const currentSlideIndex = slides.findIndex(s => s.id === slide?.id)
  const hasNext = currentSlideIndex >= 0 && currentSlideIndex < slides.length - 1
  const hasPrev = currentSlideIndex > 0
  
  // Navigation handlers
  const handlePrevSlide = () => {
    if (hasPrev && onSlideChange) {
      onSlideChange(slides[currentSlideIndex - 1])
    }
  }
  
  const handleNextSlide = () => {
    if (hasNext && onSlideChange) {
      onSlideChange(slides[currentSlideIndex + 1])
    }
  }

  // Fetch slide files when modal opens
  useEffect(() => {
    if (isOpen && slide && session) {
      fetchSlideFiles()
      fetchRefinementInfo()
    }
  }, [isOpen, slide, session]) // eslint-disable-line react-hooks/exhaustive-deps
  
  // Auto-open iterations carousel when there are iterations
  useEffect(() => {
    if (refinementIterations.length > 0) {
      setShowIterationsCarousel(true)
    }
  }, [refinementIterations])
  
  // Set up real-time subscriptions for HTML refinements
  useEffect(() => {
    if (!isOpen || !slide || !supabase) return
    
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
          fetchRefinementInfo()
        }
      )
      .subscribe()
    
    return () => {
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
        
        if (slideData.individual_pptx_url) {
          setCurrentPptxUrl(slideData.individual_pptx_url)
        }
      }
      
      // Get all refinement iterations including the final one
      const { data: refinements, count } = await supabase
        .from('html_refinements')
        .select('*')
        .eq('slide_id', slide.id)
        .order('iteration_number', { ascending: true })
      
      setRefinementCount(count || 0)
      
      // Refresh URLs for old refinements if needed
      if (refinements && refinements.length > 0) {
        const refreshedRefinements = await Promise.all(
          refinements.map(async (refinement) => {
            // Try to refresh image URLs
            if (refinement.image_file_url) {
              try {
                console.log('Attempting to refresh URL for refinement:', refinement.id)
                
                // Always try to create a new signed URL directly
                const urlObj = new URL(refinement.image_file_url)
                const pathMatch = urlObj.pathname.match(/\/storage\/v1\/object\/sign\/html-refinements\/(.+)/)
                
                if (pathMatch) {
                  const filePath = decodeURIComponent(pathMatch[1].split('?')[0])
                  console.log('Extracted file path:', filePath)
                  
                  const { data, error } = await supabase.storage
                    .from('html-refinements')
                    .createSignedUrl(filePath, 3600) // 1 hour expiry
                  
                  if (error) {
                    console.error('Error creating signed URL:', error)
                  } else if (data?.signedUrl) {
                    console.log('Successfully created new signed URL')
                    refinement.image_file_url = data.signedUrl
                  }
                } else {
                  console.warn('Could not extract file path from URL')
                }
              } catch (error) {
                console.error('Error refreshing image URL:', error)
              }
            }
            
            // Try to refresh PPTX URLs
            if (refinement.pptx_file_url) {
              try {
                const freshUrl = await refreshStorageUrlIfNeeded(refinement.pptx_file_url)
                if (freshUrl) {
                  refinement.pptx_file_url = freshUrl
                }
              } catch (error) {
                console.warn('Could not refresh PPTX URL:', error)
              }
            }
            
            return refinement
          })
        )
        
        setRefinementIterations(refreshedRefinements)
        contentAvailable.hasVersions = true
        contentAvailable.hasImage = refreshedRefinements.some(r => r.image_file_url)
        
        if (!contentAvailable.hasPptx) {
          contentAvailable.hasPptx = refinements.some(r => r.pptx_file_url)
        }
        
        if (!contentAvailable.hasHtml) {
          contentAvailable.hasHtml = refinements.some(r => r.html_content)
        }
        
        // Set the latest PPTX URL
        const latestWithPptx = [...refinements].reverse().find(r => r.pptx_file_url)
        if (latestWithPptx?.pptx_file_url) {
          setCurrentPptxUrl(latestWithPptx.pptx_file_url)
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
      if (!session?.access_token) {
        toast.error('Please sign in to view slide details')
        return
      }

      const response = await fetch(`/api/projects/${projectId}/slides/${slide.id}`, {
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      })
      
      if (!response.ok) {
        throw new Error(`Failed to fetch slide files: ${response.status} ${response.statusText}`)
      }

      const data = await response.json()
      
      if (data && data.files) {
        setSlideFiles(data.files)
      } else if (Array.isArray(data)) {
        setSlideFiles(data)
      } else {
        setSlideFiles([])
      }
      
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

  const downloadSlide = async () => {
    if (!slide) return

    try {
      if (!session?.access_token) {
        toast.error('Please sign in to download files')
        return
      }

      const response = await fetch(`/api/projects/${projectId}/slides/${slide.id}/download`, {
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      })

      if (response.ok) {
        const contentType = response.headers.get('content-type')
        if (contentType?.includes('application/json')) {
          const data = await response.json()
          if (data.redirect_url) {
            window.open(data.redirect_url, '_blank')
            toast.success('Download started')
            return
          }
        }
        
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

  if (!slide) return null

  // Fullscreen modal for the Open button
  const FullscreenPreview = () => (
    <Dialog open={showFullscreen} onOpenChange={setShowFullscreen}>
      <DialogContent className="max-w-[95vw] max-h-[95vh] w-[95vw] h-[95vh] p-0 bg-gray-900" showCloseButton={false}>
        <DialogHeader className="sr-only">
          <DialogTitle>Fullscreen Preview - Slide {slide.slide_number}</DialogTitle>
        </DialogHeader>
        
        {/* Minimal header */}
        <div className="absolute top-4 right-4 z-50 flex items-center gap-2">
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={() => setShowFullscreen(false)}
            className="bg-black/50 text-white hover:bg-black/70 backdrop-blur"
          >
            <X className="w-5 h-5" />
          </Button>
        </div>
        
        {/* Slide info overlay */}
        <div className="absolute top-4 left-4 z-50">
          <div className="bg-black/50 text-white px-3 py-2 rounded-lg backdrop-blur">
            <p className="text-sm font-medium">Slide {slide.slide_number}: {slide.title}</p>
          </div>
        </div>
        
        {/* Fullscreen iframe */}
        <div className="w-full h-full bg-gray-900">
          {currentPptxUrl && (
            <iframe
              src={`https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(currentPptxUrl)}&wdAr=1.7777777777777777&wdEaaCheck=0&wdPrint=0`}
              className="w-full h-full border-0"
              style={{ 
                height: '100%',
                width: '100%'
              }}
              title={`Fullscreen - Slide ${slide.slide_number}`}
              frameBorder="0"
            />
          )}
        </div>
      </DialogContent>
    </Dialog>
  )

  return (
    <>
      <Dialog open={isOpen} onOpenChange={(open) => { if (!open) onClose() }}>
        <DialogContent 
          className="!w-[80vw] !h-[80vh] !max-w-[80vw] !max-h-[80vh] !p-0 !gap-0 overflow-hidden bg-white sm:!max-w-[80vw] flex flex-col"
          onPointerDownOutside={(e) => {
            e.preventDefault()
            onClose()
          }}
          onEscapeKeyDown={onClose}
          showCloseButton={false}
        >
          <DialogHeader className="sr-only">
            <DialogTitle>
              Slide {slide.slide_number}: {slide.title || 'Untitled'}
            </DialogTitle>
          </DialogHeader>
          
          {/* Header */}
          <div className="bg-white border-b border-gray-200 px-4 py-3">
            {/* Title row - full width */}
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center gap-3 flex-1">
                <div className="bg-red-600 rounded p-1.5 flex-shrink-0">
                  <FileText className="w-4 h-4 text-white" />
                </div>
                <h2 className="text-lg font-semibold text-gray-900 flex-1">
                  Slide {slide.slide_number}: {slide.title || 'Untitled'}
                </h2>
              </div>
              
              {/* Close button - always visible */}
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={(e) => {
                  e.stopPropagation()
                  onClose()
                }} 
                className="h-8 w-8 p-0 hover:bg-gray-100 flex-shrink-0 ml-4"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
            
            {/* Second row - status, navigation, and actions */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                {/* Status badge */}
                <Badge 
                  variant={slide.status === 'completed' ? 'default' : 'secondary'} 
                  className={`text-xs ${
                    slide.status === 'completed' 
                      ? 'bg-green-100 text-green-700' 
                      : 'bg-gray-100 text-gray-600'
                  }`}
                >
                  {slide.status}
                </Badge>
                
                {/* Navigation */}
                {slides.length > 0 && (
                  <>
                    <div className="h-5 w-px bg-gray-200" />
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={handlePrevSlide}
                        disabled={!hasPrev}
                        className="h-7 w-7 p-0"
                      >
                        <ChevronLeft className="w-4 h-4" />
                      </Button>
                      <span className="text-sm text-gray-600 px-2 min-w-[60px] text-center">
                        {currentSlideIndex + 1} / {slides.length}
                      </span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleNextSlide}
                        disabled={!hasNext}
                        className="h-7 w-7 p-0"
                      >
                        <ChevronRight className="w-4 h-4" />
                      </Button>
                    </div>
                  </>
                )}
              </div>
              
              {/* Action buttons */}
              <div className="flex items-center gap-2">
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={() => setShowFullscreen(true)}
                  disabled={!availableContent.hasPptx}
                  className="h-8"
                >
                  <Maximize2 className="w-3.5 h-3.5 mr-1.5" />
                  Open
                </Button>
                
                <Button 
                  size="sm" 
                  onClick={downloadSlide}
                  disabled={!availableContent.hasPptx}
                  className="h-8 bg-red-600 text-white hover:bg-red-700 disabled:bg-gray-300"
                >
                  <Download className="w-3.5 h-3.5 mr-1.5" />
                  Download
                </Button>
              </div>
            </div>
          </div>

          {/* Content Area */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Iterations Carousel (Collapsible) */}
            {refinementIterations.length > 0 && (
              <div className="border-b border-gray-200 bg-white flex-shrink-0">
                <button
                  onClick={() => setShowIterationsCarousel(!showIterationsCarousel)}
                  className="w-full px-4 py-1.5 flex items-center justify-between hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <ImageIcon className="w-3 h-3 text-gray-600" />
                    <span className="text-xs text-gray-700">
                      {refinementIterations.length} Iteration{refinementIterations.length !== 1 ? 's' : ''} Available
                    </span>
                  </div>
                  {showIterationsCarousel ? 
                    <ChevronUp className="w-3 h-3 text-gray-600" /> : 
                    <ChevronDown className="w-3 h-3 text-gray-600" />
                  }
                </button>
                
                {showIterationsCarousel && (
                  <div className="px-4 pb-3 bg-gray-50">
                    <div className="flex gap-3 overflow-x-auto py-2">
                      {refinementIterations.map((iteration, index) => {
                        // Check if this is the final iteration (either marked as final or last in the list)
                        const isFinalIteration = iteration.is_final || 
                          (index === refinementIterations.length - 1)
                        
                        return (
                          <button
                            key={iteration.id}
                            onClick={() => {
                              setSelectedIterationIndex(index)
                              if (iteration.pptx_file_url) {
                                setCurrentPptxUrl(iteration.pptx_file_url)
                              } else if (iteration.image_file_url) {
                                // If no PPTX, show image preview
                                setPreviewImageUrl(iteration.image_file_url)
                              }
                            }}
                            className={`relative flex-shrink-0 rounded-md overflow-hidden border-2 transition-all cursor-pointer ${
                              selectedIterationIndex === index 
                                ? 'border-red-600 shadow-md ring-2 ring-red-600/20' 
                                : isFinalIteration
                                  ? 'border-green-500 hover:border-green-600'
                                  : 'border-gray-300 hover:border-gray-400'
                            }`}
                            title={`Click to view iteration ${iteration.iteration_number}${isFinalIteration ? ' (Final)' : ''}`}
                          >
                            {iteration.image_file_url ? (
                              <img 
                                src={iteration.image_file_url} 
                                alt={`Iteration ${iteration.iteration_number}`}
                                className="w-48 h-32 object-cover"
                                loading="lazy"
                              />
                            ) : (
                              <div className="w-48 h-32 bg-gray-200 flex items-center justify-center">
                                <span className="text-sm text-gray-500">No preview</span>
                              </div>
                            )}
                            <div className={`absolute bottom-0 left-0 right-0 ${isFinalIteration ? 'bg-green-600/80' : 'bg-black/70'} text-white text-xs py-0.5 px-1 text-center`}>
                              v{iteration.iteration_number}
                              {isFinalIteration && ' (Final)'}
                            </div>
                          </button>
                        )
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Error Message */}
            {slide.error_message && (
              <div className="mx-3 mt-2 p-2 bg-red-50 border border-red-200 rounded flex-shrink-0">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="w-3.5 h-3.5 text-red-600 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-xs font-medium text-red-800">Error: {slide.error_message}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Main Preview - PowerPoint iframe */}
            <div className="flex-1 min-h-0 overflow-hidden bg-black">
              {currentPptxUrl && availableContent.hasPptx ? (
                <div className="w-full h-full relative">
                  <iframe
                    src={`https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(currentPptxUrl)}&wdAr=1.7777777777777777&wdEaaCheck=0&wdPrint=0`}
                    className="absolute w-full h-full border-0"
                    style={{ 
                      transform: 'scale(1)',
                      transformOrigin: 'center center',
                      width: '100%',
                      height: '100%'
                    }}
                    title={`Slide ${slide.slide_number} Preview`}
                    frameBorder="0"
                    scrolling="no"
                  />
                </div>
              ) : (
                <div className="flex items-center justify-center h-full bg-gray-50">
                  <div className="text-center">
                    <div className="w-12 h-12 mx-auto mb-3 border-4 border-gray-200 border-t-red-600 rounded-full animate-spin"></div>
                    <h3 className="text-base font-medium text-gray-900 mb-1">
                      Processing Slide {slide.slide_number}
                    </h3>
                    <p className="text-sm text-gray-600">
                      {slide.status.replace(/_/g, ' ')}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Fullscreen Preview Modal */}
      <FullscreenPreview />
      
      {/* Image Preview Modal */}
      {previewImageUrl && (
        <Dialog open={!!previewImageUrl} onOpenChange={() => setPreviewImageUrl(null)}>
          <DialogContent className="!max-w-[80vw] !w-[80vw] !max-h-[90vh] p-0 overflow-hidden">
            <DialogHeader className="sr-only">
              <DialogTitle>Iteration Preview</DialogTitle>
            </DialogHeader>
            <div className="relative bg-black flex items-center justify-center" style={{ maxHeight: '90vh' }}>
              {/* Close button */}
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => setPreviewImageUrl(null)}
                className="absolute top-4 right-4 z-10 bg-black/50 text-white hover:bg-black/70"
              >
                <X className="w-5 h-5" />
              </Button>
              
              {/* Iteration info */}
              <div className="absolute top-4 left-4 z-10 bg-black/50 text-white px-3 py-2 rounded-lg backdrop-blur">
                <p className="text-sm font-medium">
                  Iteration {selectedIterationIndex + 1} of {refinementIterations.length}
                  {refinementIterations[selectedIterationIndex]?.is_final && ' (Final)'}
                </p>
              </div>
              
              {/* Previous button */}
              {selectedIterationIndex > 0 && (
                <Button
                  variant="ghost"
                  size="lg"
                  onClick={() => {
                    const newIndex = selectedIterationIndex - 1
                    setSelectedIterationIndex(newIndex)
                    const iteration = refinementIterations[newIndex]
                    if (iteration?.image_file_url) {
                      setPreviewImageUrl(iteration.image_file_url)
                    }
                    if (iteration?.pptx_file_url) {
                      setCurrentPptxUrl(iteration.pptx_file_url)
                    }
                  }}
                  className="absolute left-4 top-1/2 -translate-y-1/2 z-10 bg-black/50 text-white hover:bg-black/70 h-12 w-12 p-0"
                >
                  <ChevronLeft className="w-6 h-6" />
                </Button>
              )}
              
              {/* Next button */}
              {selectedIterationIndex < refinementIterations.length - 1 && (
                <Button
                  variant="ghost"
                  size="lg"
                  onClick={() => {
                    const newIndex = selectedIterationIndex + 1
                    setSelectedIterationIndex(newIndex)
                    const iteration = refinementIterations[newIndex]
                    if (iteration?.image_file_url) {
                      setPreviewImageUrl(iteration.image_file_url)
                    }
                    if (iteration?.pptx_file_url) {
                      setCurrentPptxUrl(iteration.pptx_file_url)
                    }
                  }}
                  className="absolute right-4 top-1/2 -translate-y-1/2 z-10 bg-black/50 text-white hover:bg-black/70 h-12 w-12 p-0"
                >
                  <ChevronRight className="w-6 h-6" />
                </Button>
              )}
              
              {/* Image */}
              <img 
                src={previewImageUrl} 
                alt={`Iteration ${selectedIterationIndex + 1}`}
                className="max-w-full max-h-[90vh] object-contain"
              />
              
              {/* Bottom navigation dots */}
              <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-10 flex gap-2 bg-black/50 px-3 py-2 rounded-full backdrop-blur">
                {refinementIterations.map((_, index) => (
                  <button
                    key={index}
                    onClick={() => {
                      setSelectedIterationIndex(index)
                      const iteration = refinementIterations[index]
                      if (iteration?.image_file_url) {
                        setPreviewImageUrl(iteration.image_file_url)
                      }
                      if (iteration?.pptx_file_url) {
                        setCurrentPptxUrl(iteration.pptx_file_url)
                      }
                    }}
                    className={`w-2 h-2 rounded-full transition-all ${
                      index === selectedIterationIndex 
                        ? 'bg-white w-6' 
                        : 'bg-white/50 hover:bg-white/75'
                    }`}
                    title={`Go to iteration ${index + 1}`}
                  />
                ))}
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}

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