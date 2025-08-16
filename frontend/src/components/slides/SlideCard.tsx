'use client'

import { useState, useEffect } from 'react'
import { SlidePreviewModal } from './SlidePreviewModal'
import { RefinementModal } from '@/components/refinement/RefinementModal'
import { useSupabaseAuth } from '@/hooks/useSupabaseAuthSimple'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { 
  Clock, 
  Loader2, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle,
  Play,
  Eye,
  Download,
  Sparkles
} from 'lucide-react'
import { Button } from '@/components/ui/button'

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
  individual_pptx_url?: string
  current_agent?: string
  error_message?: string
  started_at?: string
  completed_at?: string
  processing_time_seconds?: number
  created_at: string
  updated_at: string
  refinement_count?: number  // Track number of refinements available
}

interface SlideCardProps {
  slide: Slide | null  // null indicates loading/skeleton state
  projectId?: string   // Required for preview functionality
  isParallelProcessing?: boolean
}

const statusConfig = {
  pending: { 
    label: 'Pending', 
    color: 'bg-neutral-100 text-neutral-800 dark:bg-neutral-800 dark:text-neutral-200',
    icon: Clock,
    progress: 0
  },
  planning: { 
    label: 'Planning', 
    color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    icon: Loader2,
    progress: 10
  },
  content_generation: { 
    label: 'Generating Content', 
    color: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
    icon: Loader2,
    progress: 25
  },
  html_generation: { 
    label: 'Creating Visuals', 
    color: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200',
    icon: Loader2,
    progress: 45
  },
  html_refinement: { 
    label: 'Refining Visuals', 
    color: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200',
    icon: Loader2,
    progress: 60
  },
  image_prompt_generation: { 
    label: 'Preparing Images', 
    color: 'bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-200',
    icon: Loader2,
    progress: 70
  },
  image_generation: { 
    label: 'Generating Images', 
    color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    icon: Loader2,
    progress: 80
  },
  image_refinement: { 
    label: 'Optimizing Images', 
    color: 'bg-lime-100 text-lime-800 dark:bg-lime-900 dark:text-lime-200',
    icon: Loader2,
    progress: 85
  },
  quality_review: { 
    label: 'Quality Review', 
    color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    icon: Loader2,
    progress: 95
  },
  completed: { 
    label: 'Completed', 
    color: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200',
    icon: CheckCircle2,
    progress: 100
  },
  failed: { 
    label: 'Failed', 
    color: 'bg-destructive/10 text-destructive dark:bg-destructive/20 dark:text-destructive',
    icon: XCircle,
    progress: 0
  }
}

export function SlideCard({ slide, projectId, isParallelProcessing = false }: SlideCardProps) {
  const { supabase } = useSupabaseAuth()
  const [showPreview, setShowPreview] = useState(false)
  const [showRefinement, setShowRefinement] = useState(false)
  const [refinementCount, setRefinementCount] = useState(0)
  // Fetch refinement count when slide changes
  useEffect(() => {
    if (!slide || !projectId || !supabase) return
    
    const fetchRefinementCount = async () => {
      const { count } = await supabase
        .from('html_refinements')
        .select('*', { count: 'exact', head: true })
        .eq('project_id', projectId)
        .eq('slide_id', slide.id)
      
      setRefinementCount(count || 0)
    }
    
    
    fetchRefinementCount()
    
    // Set up real-time subscription for refinements
    const subscription = supabase
      .channel(`refinements-${slide.id}`)
      .on(
        'postgres_changes',
        {
          event: '*', // Listen to all events (INSERT, UPDATE, DELETE)
          schema: 'public',
          table: 'html_refinements',
          filter: `slide_id=eq.${slide.id}`
        },
        (payload) => {
          console.log('Refinement change detected for slide:', slide.id, payload)
          fetchRefinementCount()
          // Force a re-render by updating state
          setRefinementCount(prev => {
            // This ensures the component re-renders even if count doesn't change
            fetchRefinementCount()
            return prev
          })
        }
      )
      .subscribe((status) => {
        if (status === 'SUBSCRIBED') {
          console.log('Successfully subscribed to refinements for slide:', slide.id)
        }
      })
    
    return () => {
      subscription.unsubscribe()
    }
  }, [slide, projectId, supabase])
  
  // Show skeleton if slide is null (loading state)
  if (!slide) {
    return (
      <Card className="relative min-h-[240px] overflow-hidden">
        <div className="absolute -top-2 -left-2 w-6 h-6 bg-gray-300 rounded-full flex items-center justify-center">
          <Skeleton className="w-3 h-3" />
        </div>
        
        <CardHeader className="pb-3">
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <Skeleton className="w-4 h-4 rounded" />
              <Skeleton className="w-16 h-4 rounded-full" />
            </div>
            <Skeleton className="w-24 h-5" />
          </div>
        </CardHeader>
        
        <CardContent className="pt-0 space-y-3">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Skeleton className="w-12 h-3" />
              <Skeleton className="w-8 h-3" />
            </div>
            <Skeleton className="w-full h-2 rounded" />
          </div>
          
          <div className="p-3 bg-gray-50 dark:bg-gray-900 rounded-lg space-y-2">
            <Skeleton className="w-full h-3" />
            <Skeleton className="w-2/3 h-3" />
            <Skeleton className="w-1/3 h-3" />
          </div>
          
          <div className="pt-2 space-y-1">
            <Skeleton className="w-full h-2" />
            <Skeleton className="w-3/4 h-2" />
          </div>
        </CardContent>
      </Card>
    )
  }

  const status = slide.status || 'pending'
  const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.pending
  const StatusIcon = config.icon
  const isActive = status !== 'pending' && status !== 'completed' && status !== 'failed'
  const isCompleted = status === 'completed'
  const isFailed = status === 'failed'
  const hasRefinements = refinementCount > 0
  const isHtmlRefinementActive = status === 'html_refinement'
  const isHtmlGenerationActive = status === 'html_generation'
  const isClickable = (isCompleted || hasRefinements || isHtmlRefinementActive || isHtmlGenerationActive) && projectId

  return (
    <Card className={`relative transition-all duration-300 min-h-[240px] hover:shadow-lg group ${
      isClickable ? 'cursor-pointer' : ''
    } ${
      isActive ? 'border-primary/30 bg-primary/5 shadow-md ring-1 ring-primary/20' : 
      isCompleted ? 'border-emerald-200 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950 hover:border-emerald-300' :
      isFailed ? 'border-destructive/30 bg-destructive/5 hover:border-destructive/40' : 
      'border-neutral-200 dark:border-neutral-800 hover:border-neutral-300 dark:hover:border-neutral-700'
    }`} onClick={() => {
      if (!isClickable) return
      
      // If slide is in HTML processing or has refinements (and not completed), show refinement modal
      if (isHtmlRefinementActive || isHtmlGenerationActive || (hasRefinements && !isCompleted)) {
        setShowRefinement(true)
      } else {
        // If completed, show the final slide preview
        setShowPreview(true)
      }
    }}>
      {/* Slide number badge */}
      <div className="absolute -top-2 -left-2 w-6 h-6 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-xs font-semibold">
        {slide.slide_number}
      </div>
      
      <CardHeader className="pb-4">
        <div className="space-y-3">
          {/* Status and icon row */}
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <StatusIcon className={`w-5 h-5 flex-shrink-0 ${
                isActive ? 'animate-spin text-primary' :
                isCompleted ? 'text-emerald-600' :
                isFailed ? 'text-destructive' :
                'text-neutral-400'
              }`} />
              <Badge className={`${config.color} text-xs`}>
                {config.label}
              </Badge>
            </div>
            
            {/* Action buttons for slides with content - show on hover */}
            {isClickable && (
              <div className="flex space-x-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                {/* Primary action button - context aware */}
                {isHtmlRefinementActive || isHtmlGenerationActive || (hasRefinements && !isCompleted) ? (
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="h-6 w-6 p-0 hover:bg-purple-100 dark:hover:bg-purple-900"
                    onClick={(e) => { e.stopPropagation(); setShowRefinement(true); }}
                    title="View HTML refinement iterations"
                  >
                    <Sparkles className="w-3 h-3" />
                  </Button>
                ) : (
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="h-6 w-6 p-0 hover:bg-emerald-100 dark:hover:bg-emerald-900"
                    onClick={(e) => { e.stopPropagation(); setShowPreview(true); }}
                    title="Preview final slide"
                  >
                    <Eye className="w-3 h-3" />
                  </Button>
                )}
                
                {/* Secondary actions */}
                {isCompleted && hasRefinements && (
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="h-6 w-6 p-0 hover:bg-purple-100 dark:hover:bg-purple-900"
                    onClick={(e) => { e.stopPropagation(); setShowRefinement(true); }}
                    title="View refinement history"
                  >
                    <Sparkles className="w-3 h-3" />
                  </Button>
                )}
                
                {isCompleted && (
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="h-6 w-6 p-0 hover:bg-emerald-100 dark:hover:bg-emerald-900"
                    onClick={(e) => { e.stopPropagation(); window.open(`/api/projects/${projectId}/slides/${slide.id}/download`, '_blank'); }}
                    title="Download slide"
                  >
                    <Download className="w-3 h-3" />
                  </Button>
                )}
              </div>
            )}
          </div>
          
          {/* Title row */}
          <div>
            <h4 className={`font-medium text-sm leading-tight line-clamp-2 ${
              isActive ? 'text-primary dark:text-primary' :
              isCompleted ? 'text-emerald-900 dark:text-emerald-300' :
              isFailed ? 'text-destructive dark:text-destructive' :
              'text-neutral-700 dark:text-neutral-300'
            }`}>
              {slide.title || 'Untitled Slide'}
            </h4>
            
            {slide.current_agent && isActive && (
              <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1 truncate">
                {slide.current_agent}
              </p>
            )}
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="pt-0 flex-1 flex flex-col">
        {/* Progress bar for active/processing slides */}
        {isParallelProcessing && (isActive || isCompleted) && (
          <div className="space-y-3 mb-4">
            <div className="flex items-center justify-between text-sm">
              <span className="text-neutral-600 dark:text-neutral-400 font-medium">
                Progress
              </span>
              <span className={`font-semibold ${
                isCompleted ? 'text-emerald-600' : 'text-primary'
              }`}>
                {config.progress}%
              </span>
            </div>
            <Progress 
              value={config.progress} 
              className={`h-3 ${
                isCompleted ? 'bg-emerald-100 dark:bg-emerald-900' : ''
              }`} 
            />
          </div>
        )}
        
        {/* Content preview or generation message */}
        <div className="space-y-3 flex-1">
          {isActive && (
            <div className="p-3 bg-primary/5 border border-primary/10 rounded-lg">
              <p className="text-sm text-primary flex items-center">
                <Loader2 className="w-4 h-4 mr-2 animate-spin flex-shrink-0" />
                <span className="leading-tight">{getProcessingMessage(status)}</span>
              </p>
            </div>
          )}
          
          {isCompleted && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                {slide.processing_time_seconds && (
                  <div className="flex items-center text-sm text-emerald-600 dark:text-emerald-400">
                    <CheckCircle2 className="w-4 h-4 mr-2 flex-shrink-0" />
                    <span>Completed in {slide.processing_time_seconds}s</span>
                  </div>
                )}
                
                {/* HTML Content Indicator with refinement count */}
                {hasRefinements && (
                  <div className="flex items-center gap-1">
                    <Badge variant="outline" className="text-xs px-2 py-0.5 bg-purple-50 border-purple-200 text-purple-700 dark:bg-purple-950 dark:border-purple-800 dark:text-purple-300">
                      <Sparkles className="w-3 h-3 mr-1" />
                      {refinementCount} {refinementCount === 1 ? 'iteration' : 'iterations'}
                    </Badge>
                  </div>
                )}
              </div>
              
              {/* Show online PPTX viewer if available, otherwise show text content */}
              {slide.individual_pptx_url ? (
                <div className="space-y-2">
                  <div className="relative rounded-lg border overflow-hidden bg-white dark:bg-neutral-800" style={{ aspectRatio: '16/9' }}>
                    <iframe
                      src={`https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(slide.individual_pptx_url)}`}
                      className="w-full h-full border-0"
                      title={`Slide ${slide.slide_number} preview`}
                      allowFullScreen
                    />
                  </div>
                  <p className="text-xs text-neutral-500 dark:text-neutral-400 text-center">
                    Live PowerPoint preview
                  </p>
                </div>
              ) : (
                <div className="p-3 bg-neutral-50 dark:bg-neutral-900 rounded-lg border">
                  <p className="text-sm text-neutral-700 dark:text-neutral-300 leading-relaxed overflow-hidden" style={{display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical'}}>
                    {getSlidePreview(slide)}
                  </p>
                </div>
              )}
            </div>
          )}
          
          {isFailed && slide.error_message && (
            <div className="p-3 bg-destructive/5 border border-destructive/20 rounded-lg">
              <div className="flex items-start space-x-2">
                <AlertTriangle className="w-4 h-4 text-destructive mt-1 flex-shrink-0" />
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-destructive text-sm">Error occurred</p>
                  <p className="text-destructive/80 text-sm mt-1 overflow-hidden" style={{display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical'}}>{slide.error_message}</p>
                </div>
              </div>
            </div>
          )}
          
          {status === 'pending' && (
            <div className="flex items-center space-x-3 text-neutral-500 dark:text-neutral-400 p-3 bg-neutral-50 dark:bg-neutral-900 rounded-lg border">
              <Play className="w-4 h-4 flex-shrink-0" />
              <span className="text-sm">Waiting to start processing...</span>
            </div>
          )}
        </div>
        
        {/* Timestamps for completed slides */}
        {(slide.started_at || slide.completed_at) && (
          <div className="mt-4 pt-3 border-t border-neutral-200 dark:border-neutral-700">
            <div className="grid grid-cols-1 gap-2 text-xs text-neutral-500 dark:text-neutral-400">
              {slide.started_at && (
                <div className="flex justify-between">
                  <span className="font-medium">Started:</span>
                  <span>{new Date(slide.started_at).toLocaleString()}</span>
                </div>
              )}
              {slide.completed_at && (
                <div className="flex justify-between">
                  <span className="font-medium">Completed:</span>
                  <span>{new Date(slide.completed_at).toLocaleString()}</span>
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>

      {/* Modals */}
      {projectId && (
        <>
          <SlidePreviewModal
            slide={slide}
            projectId={projectId}
            isOpen={showPreview}
            onClose={() => setShowPreview(false)}
          />
          {(hasRefinements || isHtmlRefinementActive || isHtmlGenerationActive) && (
            <RefinementModal
              open={showRefinement}
              onOpenChange={setShowRefinement}
              projectId={projectId}
              slideId={slide.id}
              onViewFinalSlide={(slideId) => {
                setShowRefinement(false)
                setShowPreview(true)
              }}
            />
          )}
        </>
      )}
    </Card>
  )
}

function getProcessingMessage(status: string): string {
  switch (status) {
    case 'planning': return 'Planning slide structure and content...'
    case 'content_generation': return 'Generating slide content and text...'
    case 'html_generation': return 'Creating HTML visualizations...'
    case 'html_refinement': return 'Refining visual elements...'
    case 'image_prompt_generation': return 'Preparing image generation...'
    case 'image_generation': return 'Generating AI-powered images...'
    case 'image_refinement': return 'Optimizing generated images...'
    case 'quality_review': return 'Performing final quality review...'
    default: return 'Processing...'
  }
}

function getSlidePreview(slide: Slide): string {
  if (slide.content) {
    const contentValues = Object.values(slide.content)
    const textContent = contentValues
      .filter(value => typeof value === 'string' && value.length > 10)
      .join(' ')
    
    if (textContent.length > 100) {
      return textContent.substring(0, 97) + '...'
    }
    return textContent || 'Content generated successfully'
  }
  return 'Slide ready'
}

// Add the modal at the end of the SlideCard component by updating the return statement
// The modal should be added right before the closing Card tag