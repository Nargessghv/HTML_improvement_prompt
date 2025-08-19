'use client'

import { useState, useEffect } from 'react'
import Image from 'next/image'
import { useSupabaseAuth } from '@/hooks/useSupabaseAuthSimple'
import { useStorageUrl } from '@/hooks/useStorageUrl'
import { refreshStorageUrlIfNeeded } from '@/lib/storage-urls'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
import { 
  Eye, 
  Code, 
  ImageIcon, 
  ChevronLeft, 
  ChevronRight, 
  RefreshCw,
  CheckCircle,
  Clock,
  Download,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  X,
  Monitor
} from 'lucide-react'
import { toast } from 'sonner'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'

interface RefinementIteration {
  id: string
  project_id: string
  slide_id: string
  iteration_number: number
  html_content: string
  html_file_url?: string
  image_file_url?: string
  refinement_feedback?: string
  refinement_prompt?: string
  is_final: boolean
  created_at: string
  updated_at: string
}

interface Slide {
  id: string
  slide_number: number
  title?: string
  content: Record<string, unknown>
}

interface RefinementModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  projectId: string
  slideId?: string  // Optional: if provided, show only this slide's refinements
  onViewFinalSlide?: (slideId: string) => void  // Callback to transition to final slide view
}

export function RefinementModal({ open, onOpenChange, projectId, slideId, onViewFinalSlide }: RefinementModalProps) {
  const { supabase, user } = useSupabaseAuth()
  const [slides, setSlides] = useState<Slide[]>([])
  const [refinements, setRefinements] = useState<Record<string, RefinementIteration[]>>({})
  const [selectedSlide, setSelectedSlide] = useState<string | null>(null)
  const [selectedIteration, setSelectedIteration] = useState<number>(1)
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [viewMode, setViewMode] = useState<'preview' | 'html'>('preview')
  const [useNativeImg, setUseNativeImg] = useState(false)
  const [zoomLevel, setZoomLevel] = useState(0.75) // Start at 75% for better fit
  const [refreshedUrls, setRefreshedUrls] = useState<Record<string, string>>({})

  useEffect(() => {
    if (!open || !projectId || !user) return

    fetchRefinementData()

    // Set up real-time subscription for refinements
    const subscription = supabase
      .channel(`refinements-modal-${projectId}`)
      .on(
        'postgres_changes',
        {
          event: '*', // Listen to all events (INSERT, UPDATE, DELETE)
          schema: 'public',
          table: 'html_refinements',
          filter: `project_id=eq.${projectId}`
        },
        (payload) => {
          console.log('Refinement change detected in modal:', payload)
          // Refresh data when refinements change (silent to prevent flicker)
          fetchRefinementData(true)
        }
      )
      .subscribe((status) => {
        if (status === 'SUBSCRIBED') {
          console.log('Successfully subscribed to refinements in modal')
        }
      })
    
    return () => {
      subscription.unsubscribe()
    }
  }, [open, projectId, user, supabase]) // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-refresh during active processing (silent background refresh)
  useEffect(() => {
    if (!open) return

    const interval = setInterval(() => {
      // Only auto-refresh if we have no refinements yet or if we're waiting for more
      const hasAnyRefinements = Object.values(refinements).some(arr => arr.length > 0)
      if (!hasAnyRefinements || (slideId && !refinements[slideId]?.some(r => r.is_final))) {
        console.log('Auto-refreshing refinements in background...')
        // Silent refresh - don't trigger loading states or modal flicker
        fetchRefinementData(true)
      }
    }, 3000) // Check every 3 seconds (less frequent)

    return () => clearInterval(interval)
  }, [open, refinements, slideId]) // eslint-disable-line react-hooks/exhaustive-deps

  // Handle ESC key to close modal
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && open) {
        onOpenChange(false)
      }
    }

    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [open, onOpenChange])

  const extractFilePathFromUrl = (url: string): string | null => {
    try {
      // Extract file path from Supabase storage URL
      // URL format: https://*.supabase.co/storage/v1/object/sign/bucket/path/to/file?...
      const urlObj = new URL(url)
      const pathParts = urlObj.pathname.split('/')
      const signIndex = pathParts.indexOf('sign')
      
      if (signIndex !== -1 && pathParts.length > signIndex + 2) {
        // Skip 'sign' and bucket name, get the rest of the path
        return pathParts.slice(signIndex + 2).join('/')
      }
      
      return null
    } catch (error) {
      console.error('Error extracting file path from URL:', error)
      return null
    }
  }

  const refreshSignedUrl = async (originalUrl: string): Promise<string | null> => {
    try {
      // Use the centralized refresh utility
      const refreshedUrl = await refreshStorageUrlIfNeeded(originalUrl)
      if (refreshedUrl) {
        return refreshedUrl
      }

      // Fallback to manual refresh if needed
      const filePath = extractFilePathFromUrl(originalUrl)
      if (!filePath) {
        console.error('Could not extract file path from URL:', originalUrl)
        return null
      }

      const { data, error } = await supabase.storage
        .from('html-refinements')
        .createSignedUrl(filePath, 3600)
      
      if (error) {
        console.error('Failed to refresh signed URL:', error)
        return null
      }
      
      return data?.signedUrl || null
    } catch (error) {
      console.error('Error refreshing signed URL:', error)
      return null
    }
  }

  const fetchRefinementData = async (silent = false) => {
    try {
      if (!silent) {
        setIsLoading(true)
      } else {
        setIsRefreshing(true)
      }
      
      // Build slides query
      let slidesQuery = supabase
        .from('slides')
        .select('*')
        .eq('project_id', projectId)
      
      // If slideId is provided, fetch only that slide
      if (slideId) {
        slidesQuery = slidesQuery.eq('id', slideId)
      }
      
      slidesQuery = slidesQuery.order('slide_number', { ascending: true })
      
      const { data: slidesData, error: slidesError } = await slidesQuery

      if (slidesError) {
        console.error('Error fetching slides:', slidesError)
        toast.error('Failed to load slides')
        return
      }

      setSlides(slidesData || [])

      // Build refinements query
      let refinementsQuery = supabase
        .from('html_refinements')
        .select('*')
        .eq('project_id', projectId)
      
      // If slideId is provided, fetch only refinements for that slide
      if (slideId) {
        refinementsQuery = refinementsQuery.eq('slide_id', slideId)
      }
      
      refinementsQuery = refinementsQuery.order('iteration_number', { ascending: true })
      
      const { data: refinementsData, error: refinementsError } = await refinementsQuery

      if (refinementsError) {
        console.error('Error fetching refinements:', refinementsError)
        toast.error('Failed to load refinements')
        return
      }

      // Group refinements by slide_id
      const grouped = (refinementsData || []).reduce((acc, refinement) => {
        const slideId = refinement.slide_id
        if (!acc[slideId]) {
          acc[slideId] = []
        }
        acc[slideId].push(refinement)
        return acc
      }, {} as Record<string, RefinementIteration[]>)

      setRefinements(grouped)
      
      // If slideId is provided, auto-select it
      if (slideId && grouped[slideId]) {
        setSelectedSlide(slideId)
      } else {
        // Auto-select first slide with refinements
        const firstSlideWithRefinements = slidesData?.find(slide => grouped[slide.id]?.length > 0)
        if (firstSlideWithRefinements && !selectedSlide) {
          setSelectedSlide(firstSlideWithRefinements.id)
        }
      }

    } catch (error) {
      console.error('Error fetching refinement data:', error)
      if (!silent) {
        toast.error('Failed to load refinement data')
      }
    } finally {
      setIsLoading(false)
      setIsRefreshing(false)
    }
  }

  const getCurrentRefinement = (): RefinementIteration | null => {
    if (!selectedSlide) return null
    const slideRefinements = refinements[selectedSlide] || []
    return slideRefinements.find(r => r.iteration_number === selectedIteration) || null
  }

  const getSlideRefinements = (slideId: string): RefinementIteration[] => {
    return refinements[slideId] || []
  }

  const getSlideTitle = (slideId: string): string => {
    const slide = slides.find(s => s.id === slideId)
    return slide?.title || `Slide ${slide?.slide_number || '?'}`
  }

  const handlePrevIteration = () => {
    if (selectedIteration > 1) {
      setSelectedIteration(selectedIteration - 1)
    }
  }

  const handleNextIteration = () => {
    const currentRefinements = selectedSlide ? getSlideRefinements(selectedSlide) : []
    const maxIteration = Math.max(...currentRefinements.map(r => r.iteration_number), 0)
    if (selectedIteration < maxIteration) {
      setSelectedIteration(selectedIteration + 1)
    }
  }

  const handleSlideChange = (slideId: string) => {
    setSelectedSlide(slideId)
    setSelectedIteration(1)
  }

  const getCurrentImageUrl = (refinement: RefinementIteration): string | undefined => {
    if (!refinement.image_file_url) return undefined
    
    // Check if we have a refreshed URL for this refinement
    const refreshedUrl = refreshedUrls[refinement.id]
    if (refreshedUrl) return refreshedUrl
    
    return refinement.image_file_url
  }

  const handleImageError = async (refinement: RefinementIteration, isNextJsImage: boolean = false) => {
    if (!refinement.image_file_url) return

    console.warn('Image load error, attempting to refresh signed URL:', refinement.image_file_url)
    
    try {
      const newUrl = await refreshSignedUrl(refinement.image_file_url)
      if (newUrl) {
        setRefreshedUrls(prev => ({
          ...prev,
          [refinement.id]: newUrl
        }))
        // Force a re-render by toggling useNativeImg if it's a Next.js Image error
        if (isNextJsImage) {
          setUseNativeImg(true)
          // Reset back to Next.js Image after a short delay to retry with new URL
          setTimeout(() => setUseNativeImg(false), 100)
        }
      } else if (isNextJsImage) {
        // Fallback to native img for Next.js Image component
        setUseNativeImg(true)
      }
    } catch (error) {
      console.error('Error refreshing image URL:', error)
      if (isNextJsImage) {
        setUseNativeImg(true)
      }
    }
  }

  // Proactively check if URLs might be expired and refresh them
  useEffect(() => {
    if (!open || Object.keys(refinements).length === 0) return
    
    let isMounted = true
    const refreshedIds = new Set<string>()

    const checkAndRefreshUrls = async () => {
      const urlsToRefresh: Array<{id: string, url: string}> = []
      
      Object.values(refinements).flat().forEach(refinement => {
        // Skip if already refreshed in this session
        if (refinement.image_file_url && !refreshedIds.has(refinement.id)) {
          // Check if the URL looks like it might be expired (basic heuristic)
          try {
            const url = new URL(refinement.image_file_url)
            const params = new URLSearchParams(url.search)
            const token = params.get('token')
            
            if (token) {
              // Try to decode the JWT to check expiration
              try {
                const payload = token.split('.')[1]
                if (payload) {
                  const decoded = JSON.parse(atob(payload))
                  const exp = decoded.exp
                  if (exp) {
                    const now = Math.floor(Date.now() / 1000)
                    // If expired or expires within the next 5 minutes, refresh
                    if (now >= (exp - 300)) {
                      urlsToRefresh.push({id: refinement.id, url: refinement.image_file_url})
                      refreshedIds.add(refinement.id) // Mark as being refreshed
                    }
                  }
                }
              } catch {
                // If we can't decode, assume it needs refresh
                urlsToRefresh.push({id: refinement.id, url: refinement.image_file_url})
                refreshedIds.add(refinement.id)
              }
            }
          } catch {
            // Ignore URL parsing errors
          }
        }
      })

      // Refresh URLs in batches to avoid overwhelming the server
      for (const {id, url} of urlsToRefresh.slice(0, 3)) {
        if (!isMounted) break
        
        try {
          const newUrl = await refreshSignedUrl(url)
          if (newUrl && isMounted) {
            setRefreshedUrls(prev => ({
              ...prev,
              [id]: newUrl
            }))
          }
        } catch (error) {
          console.error('Error proactively refreshing URL:', error)
        }
        // Small delay between requests
        await new Promise(resolve => setTimeout(resolve, 100))
      }
    }

    checkAndRefreshUrls()
    
    return () => {
      isMounted = false
    }
  }, [open, refinements]) // Remove refreshedUrls and refreshSignedUrl from dependencies to avoid loops

  const downloadHtml = () => {
    const current = getCurrentRefinement()
    if (!current) return

    const blob = new Blob([current.html_content], { type: 'text/html' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `slide_${getSlideTitle(current.slide_id)}_iteration_${current.iteration_number}.html`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  if (isLoading) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-7xl h-[90vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>HTML Refinement Viewer</DialogTitle>
          </DialogHeader>
          <div className="flex-1 flex items-center justify-center">
            <div className="flex items-center space-x-2">
              <RefreshCw className="w-4 h-4 animate-spin" />
              <span>Loading refinement data...</span>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    )
  }

  const slidesWithRefinements = slides.filter(slide => getSlideRefinements(slide.id).length > 0)

  if (slidesWithRefinements.length === 0) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>HTML Refinement Viewer</DialogTitle>
          </DialogHeader>
          <div className="text-center py-8 text-gray-500">
            <div className="flex items-center justify-center mb-4">
              <RefreshCw className="w-8 h-8 text-gray-300 animate-spin mr-3" />
              <ImageIcon className="w-12 h-12 text-gray-300" />
            </div>
            <p className="font-medium mb-2">HTML refinements in progress...</p>
            <p className="text-sm mb-1">Refinement iterations will appear here as they are generated</p>
            <p className="text-xs text-gray-400">Auto-refreshing every 3 seconds</p>
            <div className="mt-4">
              <Button variant="outline" size="sm" onClick={() => fetchRefinementData(false)}>
                <RefreshCw className="w-4 h-4 mr-2" />
                Refresh Now
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    )
  }

  const currentRefinement = getCurrentRefinement()
  const currentSlideRefinements = selectedSlide ? getSlideRefinements(selectedSlide) : []
  const maxIteration = Math.max(...currentSlideRefinements.map(r => r.iteration_number), 0)
  const finalRefinement = currentSlideRefinements.find(r => r.is_final)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent 
        className="flex flex-col p-0"
        style={{ 
          width: '95vw',
          height: '95vh',
          maxWidth: '95vw',
          maxHeight: '95vh'
        }}
      >
        <DialogHeader className="flex-row items-center justify-between space-y-0 pb-4 px-6 pt-6">
          <div>
            <DialogTitle className="flex items-center gap-2">
              <Monitor className="w-5 h-5" />
              HTML Refinement Viewer
              {finalRefinement ? (
                <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                  <CheckCircle className="w-3 h-3 mr-1" />
                  Final - Ready for PowerPoint
                </Badge>
              ) : (
                <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                  <Clock className="w-3 h-3 mr-1" />
                  In Progress
                </Badge>
              )}
            </DialogTitle>
          </div>
          <div className="flex items-center space-x-2">
            <Button variant="outline" size="sm" onClick={() => fetchRefinementData(false)}>
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={() => onOpenChange(false)}
              className="hover:bg-gray-100 dark:hover:bg-gray-800"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>
        </DialogHeader>

        {/* Loading indicator at top */}
        {isRefreshing && (
          <div className="bg-blue-50 dark:bg-blue-950 border-b border-blue-200 dark:border-blue-800 px-6 py-2">
            <div className="flex items-center space-x-2 text-blue-700 dark:text-blue-300">
              <RefreshCw className="w-4 h-4 animate-spin" />
              <span className="text-sm font-medium">Checking for new refinement iterations...</span>
            </div>
          </div>
        )}

        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Slide Selection & Controls */}
          <div className="border-b pb-4 px-6 space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <label className="text-sm font-medium">Select Slide:</label>
                <div className="flex flex-wrap gap-2">
                  {slidesWithRefinements.map((slide) => (
                    <Button
                      key={slide.id}
                      variant={selectedSlide === slide.id ? "default" : "outline"}
                      size="sm"
                      onClick={() => handleSlideChange(slide.id)}
                    >
                      {getSlideTitle(slide.id)}
                      <Badge variant="secondary" className="ml-2">
                        {getSlideRefinements(slide.id).length}
                      </Badge>
                    </Button>
                  ))}
                </div>
              </div>
            </div>

            {/* Iteration Navigation */}
            {selectedSlide && currentSlideRefinements.length > 0 && (
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handlePrevIteration}
                    disabled={selectedIteration <= 1}
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </Button>
                  <span className="text-sm font-medium">
                    Iteration {selectedIteration} of {maxIteration}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleNextIteration}
                    disabled={selectedIteration >= maxIteration}
                  >
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                </div>

                <div className="flex items-center space-x-2">
                  {currentRefinement?.is_final && (
                    <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                      <CheckCircle className="w-3 h-3 mr-1" />
                      Final Version
                    </Badge>
                  )}
                  <Badge variant="outline">
                    <Clock className="w-3 h-3 mr-1" />
                    {currentRefinement ? new Date(currentRefinement.created_at).toLocaleTimeString() : ''}
                  </Badge>
                </div>
              </div>
            )}
          </div>

          {/* Main Content Area */}
          {currentRefinement && (
            <div className="flex-1 flex overflow-hidden">
              {/* Left Panel - Preview */}
              <div className="flex-1 flex flex-col border-r">
                <div className="border-b p-3 flex items-center justify-between bg-gray-50">
                  <div className="flex items-center space-x-2">
                    <Monitor className="w-4 h-4" />
                    <span className="font-medium">Live HTML Preview</span>
                    <span className="text-xs text-gray-500">Zoom {Math.round(zoomLevel * 100)}%</span>
                  </div>
                  <div className="flex items-center space-x-1 border rounded px-2">
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      onClick={() => setZoomLevel(Math.max(0.25, zoomLevel - 0.25))}
                      disabled={zoomLevel <= 0.25}
                    >
                      <ZoomOut className="w-3 h-3" />
                    </Button>
                    <span className="text-xs px-2">{Math.round(zoomLevel * 100)}%</span>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      onClick={() => setZoomLevel(Math.min(2, zoomLevel + 0.25))}
                      disabled={zoomLevel >= 2}
                    >
                      <ZoomIn className="w-3 h-3" />
                    </Button>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      onClick={() => setZoomLevel(0.75)}
                    >
                      <RotateCcw className="w-3 h-3" />
                    </Button>
                  </div>
                </div>
                
                <div className="flex-1 overflow-auto bg-gray-100 p-4">
                  <div 
                    style={{ 
                      transform: `scale(${zoomLevel})`,
                      transformOrigin: 'top left',
                      width: `${100 / zoomLevel}%`,
                      height: `${600 / zoomLevel}px`,
                    }}
                  >
                    <iframe
                      srcDoc={currentRefinement.html_content}
                      className="w-full bg-white border border-gray-300 shadow-lg"
                      style={{ 
                        height: '600px',
                        minHeight: '600px',
                        width: '100%',
                      }}
                      sandbox="allow-same-origin allow-scripts allow-popups"
                      title={`HTML Preview - Iteration ${currentRefinement.iteration_number}`}
                    />
                  </div>
                </div>
              </div>

              {/* Right Panel - Details & Code */}
              <div className="w-96 flex flex-col">
                <Tabs value={viewMode} onValueChange={(value) => setViewMode(value as 'preview' | 'html')} className="flex-1 flex flex-col">
                  <div className="border-b p-3 flex items-center justify-between bg-gray-50">
                    <TabsList className="grid w-full grid-cols-2">
                      <TabsTrigger value="preview" className="flex items-center gap-2">
                        <Eye className="w-4 h-4" />
                        Details
                      </TabsTrigger>
                      <TabsTrigger value="html" className="flex items-center gap-2">
                        <Code className="w-4 h-4" />
                        HTML Code
                      </TabsTrigger>
                    </TabsList>
                    {/* Show transition to final slide button if refinement is complete */}
                    {finalRefinement && onViewFinalSlide && selectedSlide && (
                      <Button 
                        variant="default" 
                        size="sm" 
                        onClick={() => {
                          onViewFinalSlide(selectedSlide)
                          onOpenChange(false)
                        }}
                        className="bg-emerald-600 hover:bg-emerald-700"
                      >
                        <Eye className="w-4 h-4 mr-2" />
                        View Final Slide
                      </Button>
                    )}
                    <Button variant="outline" size="sm" onClick={downloadHtml}>
                      <Download className="w-4 h-4 mr-2" />
                      Download HTML
                    </Button>
                  </div>
                  
                  <TabsContent value="preview" className="flex-1 flex flex-col p-4 space-y-4">
                    {/* Thumbnail if available */}
                    {currentRefinement.image_file_url && (
                      <div className="space-y-2">
                        <h4 className="text-sm font-medium">Screenshot Reference</h4>
                        <div className="relative w-full h-32 bg-gray-100 rounded border overflow-hidden">
                          {useNativeImg ? (
                            <img 
                              src={getCurrentImageUrl(currentRefinement)} 
                              alt={`Thumbnail iteration ${currentRefinement.iteration_number}`}
                              className="w-full h-full object-contain"
                              onError={() => handleImageError(currentRefinement, false)}
                            />
                          ) : (
                            <Image 
                              src={getCurrentImageUrl(currentRefinement) || ''} 
                              alt={`Thumbnail iteration ${currentRefinement.iteration_number}`}
                              fill
                              className="object-contain"
                              onError={() => handleImageError(currentRefinement, true)}
                            />
                          )}
                          <div className="absolute inset-0 flex items-center justify-center bg-gray-50">
                            <ImageIcon className="w-8 h-8 text-gray-400" />
                          </div>
                        </div>
                        <div className="text-xs text-gray-500">
                          Generated at render time
                        </div>
                      </div>
                    )}

                    {/* Refinement Feedback */}
                    {currentRefinement.refinement_feedback && (
                      <div className="space-y-2">
                        <h4 className="text-sm font-medium">LLM Feedback</h4>
                        <ScrollArea className="h-32 w-full border rounded">
                          <div className="p-3 text-sm">
                            <pre className="whitespace-pre-wrap font-mono text-xs">
                              {currentRefinement.refinement_feedback}
                            </pre>
                          </div>
                        </ScrollArea>
                      </div>
                    )}

                    {/* HTML Info */}
                    <div className="space-y-2">
                      <h4 className="text-sm font-medium">Technical Details</h4>
                      <div className="text-xs text-gray-600 space-y-1">
                        <div>HTML Size: {(currentRefinement.html_content.length / 1024).toFixed(1)}KB</div>
                        <div>Contains viewport: {currentRefinement.html_content.includes('viewport') ? 'Yes' : 'No'}</div>
                        <div>Has body tag: {currentRefinement.html_content.includes('<body') ? 'Yes' : 'No'}</div>
                      </div>
                    </div>
                  </TabsContent>

                  <TabsContent value="html" className="flex-1 flex flex-col p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-sm font-medium">HTML Source Code</h4>
                      <div className="text-xs text-gray-500">
                        {currentRefinement.html_content.length} characters
                      </div>
                    </div>
                    <ScrollArea className="flex-1 border rounded">
                      <pre className="p-4 text-xs">
                        <code>{currentRefinement.html_content}</code>
                      </pre>
                    </ScrollArea>
                  </TabsContent>
                </Tabs>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}