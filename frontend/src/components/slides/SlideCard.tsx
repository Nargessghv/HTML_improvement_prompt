'use client'

import { useState, useEffect } from 'react'
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
  Download
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
  current_agent?: string
  error_message?: string
  started_at?: string
  completed_at?: string
  processing_time_seconds?: number
  created_at: string
  updated_at: string
}

interface SlideCardProps {
  slide: Slide | null  // null indicates loading/skeleton state
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

export function SlideCard({ slide, isParallelProcessing = false }: SlideCardProps) {
  // Show skeleton if slide is null (loading state)
  if (!slide) {
    return (
      <Card className="relative">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Skeleton className="w-8 h-8 rounded-full" />
              <div>
                <Skeleton className="w-24 h-4 mb-2" />
                <Skeleton className="w-32 h-3" />
              </div>
            </div>
            <Skeleton className="w-16 h-5 rounded-full" />
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="space-y-3">
            <div>
              <Skeleton className="w-20 h-3 mb-2" />
              <Skeleton className="w-full h-2" />
            </div>
            <div className="space-y-2">
              <Skeleton className="w-full h-3" />
              <Skeleton className="w-3/4 h-3" />
              <Skeleton className="w-1/2 h-3" />
            </div>
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

  return (
    <Card className={`relative transition-all duration-300 ${
      isActive ? 'border-primary/20 bg-primary/5 shadow-md' : 
      isCompleted ? 'border-emerald-200 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950' :
      isFailed ? 'border-destructive/20 bg-destructive/5' : 
      'border-neutral-200 dark:border-neutral-800'
    }`}>
      {/* Slide number badge */}
      <div className="absolute -top-2 -left-2 w-6 h-6 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-xs font-semibold">
        {slide.slide_number}
      </div>
      
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="flex-shrink-0">
              <StatusIcon className={`w-5 h-5 ${
                isActive ? 'animate-spin text-primary' :
                isCompleted ? 'text-emerald-600' :
                isFailed ? 'text-destructive' :
                'text-neutral-400'
              }`} />
            </div>
            
            <div className="min-w-0 flex-1">
              <h4 className={`font-medium text-sm truncate ${
                isActive ? 'text-primary dark:text-primary' :
                isCompleted ? 'text-emerald-900 dark:text-emerald-300' :
                isFailed ? 'text-destructive dark:text-destructive' :
                'text-neutral-700 dark:text-neutral-300'
              }`}>
                {slide.title || 'Untitled Slide'}
              </h4>
              
              <div className="flex items-center space-x-2 mt-1">
                <Badge className={`${config.color} text-xs`}>
                  {config.label}
                </Badge>
                
                {slide.current_agent && isActive && (
                  <span className="text-xs text-neutral-500 dark:text-neutral-400">
                    {slide.current_agent}
                  </span>
                )}
              </div>
            </div>
          </div>
          
          {/* Action buttons for completed slides */}
          {isCompleted && (
            <div className="flex space-x-1">
              {slide.html_content && (
                <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                  <Eye className="w-3 h-3" />
                </Button>
              )}
              <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                <Download className="w-3 h-3" />
              </Button>
            </div>
          )}
        </div>
      </CardHeader>
      
      <CardContent className="pt-0">
        {/* Progress bar for active/processing slides */}
        {isParallelProcessing && (isActive || isCompleted) && (
          <div className="space-y-2 mb-4">
            <div className="flex items-center justify-between text-xs">
              <span className="text-neutral-600 dark:text-neutral-400">
                Progress
              </span>
              <span className={`font-medium ${
                isCompleted ? 'text-emerald-600' : 'text-primary'
              }`}>
                {config.progress}%
              </span>
            </div>
            <Progress 
              value={config.progress} 
              className={`h-2 ${
                isCompleted ? 'bg-emerald-100 dark:bg-emerald-900' : ''
              }`} 
            />
          </div>
        )}
        
        {/* Content preview or generation message */}
        <div className="space-y-2">
          {isActive && (
            <p className="text-sm text-primary/70">
              <Loader2 className="w-3 h-3 inline mr-1 animate-spin" />
              {getProcessingMessage(status)}
            </p>
          )}
          
          {isCompleted && (
            <div className="space-y-2">
              {slide.processing_time_seconds && (
                <p className="text-xs text-emerald-600 dark:text-emerald-400">
                  ✓ Completed in {slide.processing_time_seconds}s
                </p>
              )}
              
              {/* Show a preview of the slide content */}
              <div className="p-2 bg-neutral-50 dark:bg-neutral-900 rounded text-xs text-neutral-600 dark:text-neutral-400 max-h-16 overflow-hidden">
                {getSlidePreview(slide)}
              </div>
            </div>
          )}
          
          {isFailed && slide.error_message && (
            <div className="p-2 bg-destructive/5 border border-destructive/20 rounded text-xs">
              <div className="flex items-start space-x-1">
                <AlertTriangle className="w-3 h-3 text-destructive mt-0.5 flex-shrink-0" />
                <div>
                  <p className="font-medium text-destructive">Error:</p>
                  <p className="text-destructive/80 mt-1">{slide.error_message}</p>
                </div>
              </div>
            </div>
          )}
          
          {status === 'pending' && (
            <div className="flex items-center space-x-2 text-sm text-neutral-500 dark:text-neutral-400">
              <Play className="w-3 h-3" />
              <span>Waiting to start...</span>
            </div>
          )}
        </div>
        
        {/* Timestamps for completed slides */}
        {(slide.started_at || slide.completed_at) && (
          <div className="mt-3 pt-2 border-t border-neutral-100 dark:border-neutral-800">
            <div className="grid grid-cols-2 gap-2 text-xs text-neutral-500 dark:text-neutral-400">
              {slide.started_at && (
                <div>
                  <span className="block font-medium">Started</span>
                  <span>{new Date(slide.started_at).toLocaleTimeString()}</span>
                </div>
              )}
              {slide.completed_at && (
                <div>
                  <span className="block font-medium">Completed</span>
                  <span>{new Date(slide.completed_at).toLocaleTimeString()}</span>
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>
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