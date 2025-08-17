'use client'

import { useState, useEffect } from 'react'
import { useSupabaseAuth } from '@/hooks/useSupabaseAuthSimple'
import { SlideCard } from './SlideCard'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { 
  Loader2, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  Presentation,
  Download,
  RefreshCw
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { toast } from 'sonner'

interface Slide {
  id: string
  slide_number: number
  title: string
  status: 'pending' | 'planning' | 'content_generation' | 'html_generation' | 
          'html_refinement' | 'image_prompt_generation' | 'image_generation' | 
          'image_refinement' | 'quality_review' | 'completed' | 'failed'
  content: any
  html_content?: string
  refined_html?: string
  current_agent?: string
  error_message?: string
  started_at?: string
  completed_at?: string
  processing_time_seconds?: number
  created_at: string
  updated_at: string
}

interface SlideProgress {
  total_slides: number
  completed_slides: number
  failed_slides: number
  in_progress_slides: number
  pending_slides: number
  completion_percentage: number
}

interface SlidesGridProps {
  projectId: string
  projectStatus: 'draft' | 'processing' | 'completed' | 'failed'
  isParallelProcessing?: boolean
  expectedSlideCount?: number
  autoRefreshEnabled?: boolean
}

export function SlidesGrid({ 
  projectId, 
  projectStatus, 
  isParallelProcessing = false,
  expectedSlideCount = 0,
  autoRefreshEnabled = true
}: SlidesGridProps) {
  const { supabase, user } = useSupabaseAuth()
  const [slides, setSlides] = useState<Slide[]>([])
  const [slideProgress, setSlideProgress] = useState<SlideProgress | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)

  // Fetch slides data
  const fetchSlides = async (showRefreshing = false) => {
    if (!projectId || !user) return

    try {
      if (showRefreshing) setIsRefreshing(true)
      
      const { data, error } = await supabase
        .from('slides')
        .select('*')
        .eq('project_id', projectId)
        .order('slide_number', { ascending: true })

      if (error) {
        console.error('Error fetching slides:', error)
        toast.error('Failed to load slides')
        return
      }

      setSlides(data || [])
      
      // Fetch slide progress if in parallel processing mode
      if (isParallelProcessing && data && data.length > 0) {
        await fetchSlideProgress()
      }
      
    } catch (error) {
      console.error('Unexpected error:', error)
      toast.error('An unexpected error occurred')
    } finally {
      setIsLoading(false)
      if (showRefreshing) setIsRefreshing(false)
    }
  }

  // Fetch slide progress summary
  const fetchSlideProgress = async () => {
    if (!projectId || !user) return

    try {
      const { data, error } = await supabase
        .rpc('get_project_slide_progress', { p_project_id: projectId })

      if (error) {
        console.error('Error fetching slide progress:', error)
        return
      }

      if (data && data.length > 0) {
        setSlideProgress(data[0])
      }
      
    } catch (error) {
      console.error('Error fetching slide progress:', error)
    }
  }

  useEffect(() => {
    fetchSlides()

    // Set up auto-refresh interval for processing projects (reduced from 20s to 60s as fallback only)
    let refreshInterval: NodeJS.Timeout | null = null
    let isSubscribed = true
    let realtimeWorking = false

    // Only use polling as a fallback if real-time is not working
    const setupPollingFallback = () => {
      if (autoRefreshEnabled && (projectStatus === 'processing') && !realtimeWorking) {
        refreshInterval = setInterval(() => {
          if (isSubscribed) {
            console.log('Using polling fallback for slides refresh')
            fetchSlides()
          }
        }, 60000) // Refresh slides every 60 seconds instead of 20
      }
    }

    // Set up real-time subscription first
    let slideSubscription: any = null
    try {
      slideSubscription = supabase
        .channel(`slides-grid-${projectId}`)
        .on(
          'postgres_changes',
          {
            event: '*',
            schema: 'public',
            table: 'slides',
            filter: `project_id=eq.${projectId}`
          },
          (payload) => {
            realtimeWorking = true
            // Clear polling since real-time is working
            if (refreshInterval) {
              clearInterval(refreshInterval)
              refreshInterval = null
            }
            
            if (payload.eventType === 'INSERT') {
              setSlides(prev => [...prev, payload.new as Slide].sort((a, b) => a.slide_number - b.slide_number))
            } else if (payload.eventType === 'UPDATE') {
              setSlides(prev => 
                prev.map(slide => 
                  slide.id === payload.new.id ? payload.new as Slide : slide
                )
              )
            } else if (payload.eventType === 'DELETE') {
              setSlides(prev => prev.filter(slide => slide.id !== payload.old.id))
            }

            // Update progress when slides change in parallel processing mode
            if (isParallelProcessing) {
              fetchSlideProgress()
            }
          }
        )
        .subscribe()

      // Give real-time subscription a chance to connect, then setup polling fallback
      setTimeout(() => {
        if (isSubscribed && !realtimeWorking) {
          console.warn('Real-time subscription may not be working, setting up polling fallback')
          setupPollingFallback()
        }
      }, 5000)
    } catch (error) {
      console.warn('Real-time subscription setup failed, using polling fallback', error)
      setupPollingFallback()
    }

    return () => {
      isSubscribed = false
      realtimeWorking = false
      if (refreshInterval) {
        clearInterval(refreshInterval)
      }
      if (slideSubscription) {
        slideSubscription.unsubscribe()
      }
    }
  }, [projectId, user, supabase, isParallelProcessing, autoRefreshEnabled, projectStatus])


  const handleRefresh = () => {
    fetchSlides(true)
  }

  // Generate skeleton slides if we know the expected count but haven't loaded yet
  const renderSlides = () => {
    const existingSlides = slides.length
    const totalExpected = Math.max(existingSlides, expectedSlideCount)
    
    const slideElements = []
    
    // Show actual slides
    for (let i = 0; i < existingSlides; i++) {
      slideElements.push(
        <SlideCard 
          key={slides[i].id} 
          slide={slides[i]} 
          slides={slides}  // Pass all slides for navigation
          projectId={projectId}
          isParallelProcessing={isParallelProcessing}
        />
      )
    }
    
    // Show skeleton slides for expected but not yet created slides
    if (isLoading || (projectStatus === 'processing' && existingSlides < totalExpected)) {
      for (let i = existingSlides; i < totalExpected; i++) {
        slideElements.push(
          <SlideCard 
            key={`skeleton-${i}`} 
            slide={null}
            projectId={projectId} 
            isParallelProcessing={isParallelProcessing}
          />
        )
      }
    }
    
    return slideElements
  }

  if (projectStatus === 'draft') {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Presentation className="w-5 h-5" />
            Slides Preview
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12 text-gray-500">
            <Presentation className="w-16 h-16 mx-auto mb-4 text-gray-300" />
            <p className="text-lg font-medium mb-2">No slides yet</p>
            <p>Start processing your presentation to see individual slides appear here.</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Progress Summary for Parallel Processing */}
      {isParallelProcessing && slideProgress && (
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950 dark:to-indigo-950 border border-blue-200 dark:border-blue-800 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
                <Presentation className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <h3 className="font-semibold text-blue-900 dark:text-blue-100">Slide Generation Progress</h3>
                <p className="text-sm text-blue-700 dark:text-blue-300">
                  {slideProgress.completed_slides} of {slideProgress.total_slides} slides completed
                </p>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="border-blue-300 text-blue-700 hover:bg-blue-100 dark:border-blue-700 dark:text-blue-300 dark:hover:bg-blue-900"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>

          <div className="space-y-4">
            {/* Overall Progress */}
            <div>
              <div className="flex items-center justify-between text-sm mb-2">
                <span className="font-medium text-blue-900 dark:text-blue-100">
                  Overall Progress
                </span>
                <span className="text-blue-700 dark:text-blue-300">
                  {Math.round(slideProgress.completion_percentage)}%
                </span>
              </div>
              <Progress value={slideProgress.completion_percentage} className="h-3 bg-blue-100 dark:bg-blue-900" />
            </div>

            {/* Status Breakdown */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {slideProgress.completed_slides > 0 && (
                <div className="flex items-center gap-2 p-3 bg-emerald-50 dark:bg-emerald-950 border border-emerald-200 dark:border-emerald-800 rounded-lg">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                  <div>
                    <p className="text-sm font-medium text-emerald-900 dark:text-emerald-100">{slideProgress.completed_slides}</p>
                    <p className="text-xs text-emerald-700 dark:text-emerald-300">Completed</p>
                  </div>
                </div>
              )}
              
              {slideProgress.in_progress_slides > 0 && (
                <div className="flex items-center gap-2 p-3 bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg">
                  <Loader2 className="w-4 h-4 text-blue-600 dark:text-blue-400 animate-spin" />
                  <div>
                    <p className="text-sm font-medium text-blue-900 dark:text-blue-100">{slideProgress.in_progress_slides}</p>
                    <p className="text-xs text-blue-700 dark:text-blue-300">Processing</p>
                  </div>
                </div>
              )}
              
              {slideProgress.pending_slides > 0 && (
                <div className="flex items-center gap-2 p-3 bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-800 rounded-lg">
                  <Clock className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                  <div>
                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{slideProgress.pending_slides}</p>
                    <p className="text-xs text-gray-700 dark:text-gray-300">Pending</p>
                  </div>
                </div>
              )}
              
              {slideProgress.failed_slides > 0 && (
                <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg">
                  <XCircle className="w-4 h-4 text-red-600 dark:text-red-400" />
                  <div>
                    <p className="text-sm font-medium text-red-900 dark:text-red-100">{slideProgress.failed_slides}</p>
                    <p className="text-xs text-red-700 dark:text-red-300">Failed</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Slides Grid */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Presentation className="w-5 h-5" />
              Individual Slides
              {slides.length > 0 && (
                <Badge variant="secondary">
                  {slides.length} slide{slides.length !== 1 ? 's' : ''}
                </Badge>
              )}
            </CardTitle>
            
            {projectStatus === 'completed' && slides.some(s => s.status === 'completed') && (
              <Button variant="outline" size="sm">
                <Download className="w-4 h-4 mr-2" />
                Download All
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {isLoading && slides.length === 0 ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin mr-2" />
              <span>Loading slides...</span>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 3xl:grid-cols-6 gap-4">
              {renderSlides()}
            </div>
          )}
          
          {!isLoading && slides.length === 0 && projectStatus === 'processing' && (
            <div className="text-center py-12 text-gray-500">
              <Loader2 className="w-12 h-12 mx-auto mb-3 animate-spin text-primary" />
              <p className="text-lg font-medium mb-2">Preparing slides...</p>
              <p>Individual slides will appear here as they are being processed.</p>
            </div>
          )}
          
          {!isLoading && slides.length === 0 && projectStatus === 'completed' && (
            <div className="text-center py-12 text-gray-500">
              <Presentation className="w-16 h-16 mx-auto mb-4 text-gray-300" />
              <p className="text-lg font-medium mb-2">No slides found</p>
              <p>This presentation doesn't appear to have any individual slides recorded.</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}