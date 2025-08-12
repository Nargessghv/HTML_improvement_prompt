'use client'

import { useState } from 'react'
import { Plus, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

interface SlideOutline {
  slide_number: number
  title: string
  content_type: 'text' | 'visual' | 'chart' | 'timeline' | 'comparison'
  key_points: string[]
  suggested_layout?: string
  notes?: string
}

interface PresentationOutline {
  title: string
  topic: string
  target_audience?: string
  objectives: string[]
  key_themes: string[]
  slides: SlideOutline[]
  estimated_duration?: number
  style_preferences: Record<string, unknown>
}

interface OutlineBuilderProps {
  outline: PresentationOutline | null
  onUpdate: (outline: PresentationOutline) => void
  onApprove: () => void
  className?: string
}

export function OutlineBuilder({ 
  outline: initialOutline, 
  onUpdate, 
  onApprove,
  className 
}: OutlineBuilderProps) {
  const [outline, setOutline] = useState<PresentationOutline | null>(initialOutline)

  if (!outline) {
    return (
      <Card className={cn("h-full", className)}>
        <CardContent className="flex items-center justify-center h-full text-muted-foreground">
          <p className="text-sm">No outline generated yet. Continue chatting to create one.</p>
        </CardContent>
      </Card>
    )
  }


  return (
    <Card className={cn("flex flex-col h-full", className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>{outline.title}</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              {outline.slides.length} slides • ~{outline.estimated_duration || outline.slides.length * 2} minutes
            </p>
          </div>
          <Button onClick={onApprove} size="sm">
            <Check className="w-4 h-4 mr-2" />
            Approve & Generate
          </Button>
        </div>
      </CardHeader>

      <CardContent className="flex-1 overflow-hidden">
        <div className="mb-4 space-y-2">
          {outline.target_audience && (
            <div className="text-sm">
              <span className="font-medium">Audience:</span> {outline.target_audience}
            </div>
          )}
          {outline.objectives.length > 0 && (
            <div className="text-sm">
              <span className="font-medium">Objectives:</span>
              <ul className="list-disc list-inside mt-1">
                {outline.objectives.map((obj, idx) => (
                  <li key={idx} className="text-muted-foreground">{obj}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="space-y-2 max-h-[500px] overflow-y-auto pr-2">
          {outline.slides.map((slide, index) => (
            <div key={`slide-${slide.slide_number}`} className="group">
              <Card className="p-3">
                <div className="flex items-start gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant="outline" className="text-xs">
                        #{slide.slide_number}
                      </Badge>
                      <Badge className="text-xs bg-blue-100 text-blue-700">
                        {slide.content_type}
                      </Badge>
                    </div>
                    <h4 className="font-medium text-sm">{slide.title}</h4>
                    {slide.key_points.length > 0 && (
                      <ul className="text-xs text-muted-foreground mt-1 space-y-0.5">
                        {slide.key_points.slice(0, 2).map((point, idx) => (
                          <li key={idx} className="truncate">• {point}</li>
                        ))}
                        {slide.key_points.length > 2 && (
                          <li className="text-xs opacity-70">
                            +{slide.key_points.length - 2} more points
                          </li>
                        )}
                      </ul>
                    )}
                  </div>
                </div>
              </Card>
            </div>
          ))}
        </div>

      </CardContent>
    </Card>
  )
}