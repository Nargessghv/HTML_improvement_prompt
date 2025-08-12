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
}

export function SlidesGrid({ 
  projectId, 
  projectStatus, 
  isParallelProcessing = false,
  expectedSlideCount = 0
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
  }, [projectId, user, supabase, isParallelProcessing])

  // Set up real-time subscription for slides
  useEffect(() => {
    if (!projectId || !user) return

    const subscription = supabase
      .channel(`slides-${projectId}`)
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'slides',
          filter: `project_id=eq.${projectId}`
        },
        (payload) => {
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

    return () => {
      subscription.unsubscribe()
    }
  }, [projectId, user, supabase, isParallelProcessing])

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
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Presentation className="w-5 h-5" />
                Slide Generation Progress
              </CardTitle>
              <Button
                variant="outline"
                size="sm"
                onClick={handleRefresh}
                disabled={isRefreshing}
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Overall Progress */}
              <div>
                <div className="flex items-center justify-between text-sm mb-2">
                  <span className="font-medium">
                    Overall Progress ({Math.round(slideProgress.completion_percentage)}%)
                  </span>
                  <span className="text-gray-500">
                    {slideProgress.completed_slides} of {slideProgress.total_slides} completed
                  </span>
                </div>
                <Progress value={slideProgress.completion_percentage} className="h-3" />
              </div>

              {/* Status Breakdown */}
              <div className="flex flex-wrap gap-2">
                {slideProgress.completed_slides > 0 && (
                  <Badge variant="secondary" className="bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200">
                    <CheckCircle2 className="w-3 h-3 mr-1" />
                    {slideProgress.completed_slides} Completed
                  </Badge>
                )}
                
                {slideProgress.in_progress_slides > 0 && (
                  <Badge variant="secondary" className="bg-primary/10 text-primary">
                    <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                    {slideProgress.in_progress_slides} Processing
                  </Badge>
                )}
                
                {slideProgress.pending_slides > 0 && (
                  <Badge variant="secondary" className="bg-neutral-100 text-neutral-800 dark:bg-neutral-800 dark:text-neutral-200">
                    <Clock className="w-3 h-3 mr-1" />
                    {slideProgress.pending_slides} Pending
                  </Badge>
                )}
                
                {slideProgress.failed_slides > 0 && (
                  <Badge variant="secondary" className="bg-destructive/10 text-destructive">
                    <XCircle className="w-3 h-3 mr-1" />
                    {slideProgress.failed_slides} Failed
                  </Badge>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
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
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
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