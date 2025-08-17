'use client'

import { useState, useEffect } from 'react'
import { Plus, Check, ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { cn } from '@/lib/utils'

interface SlideOutline {
  slide_number: number
  title: string
  is_html: boolean
  is_image: boolean
  layout_index?: number
  layout_name?: string
  key_points: string[]
  suggested_layout?: string
  notes?: string
}

interface LayoutOption {
  index: number
  name: string
  description: string
  supports_html: boolean
  supports_image: boolean
  placeholder_count: number
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
  sessionId?: string
  templateName?: string
  onUpdate: (outline: PresentationOutline) => void
  onApprove: () => void
  className?: string
}

export function OutlineBuilder({ 
  outline: initialOutline, 
  sessionId,
  templateName = 'ekona_slides_template_new',
  onUpdate, 
  onApprove,
  className 
}: OutlineBuilderProps) {
  const [outline, setOutline] = useState<PresentationOutline | null>(initialOutline)
  const [availableLayouts, setAvailableLayouts] = useState<LayoutOption[]>([])
  const [loadingLayouts, setLoadingLayouts] = useState(false)

  // Load available layouts when component mounts or template changes
  useEffect(() => {
    const loadLayouts = async () => {
      if (!templateName) return
      
      setLoadingLayouts(true)
      try {
        const response = await fetch(`/api/layouts/${templateName}`, {
          credentials: 'include'
        })
        
        if (response.ok) {
          const data = await response.json()
          setAvailableLayouts(data.layouts || [])
        }
      } catch (error) {
        console.error('Error loading layouts:', error)
      } finally {
        setLoadingLayouts(false)
      }
    }

    loadLayouts()
  }, [templateName])

  // Update outline when initialOutline changes
  useEffect(() => {
    setOutline(initialOutline)
  }, [initialOutline])

  const handleLayoutChange = async (slideNumber: number, layoutIndex: number) => {
    if (!sessionId || !outline) return

    try {
      const response = await fetch(`/api/chat/${sessionId}/slides/${slideNumber}/layout`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ layout_index: layoutIndex })
      })

      if (response.ok) {
        const result = await response.json()
        
        // Update local outline
        const updatedOutline = { ...outline }
        const slideIndex = updatedOutline.slides.findIndex(s => s.slide_number === slideNumber)
        if (slideIndex !== -1) {
          updatedOutline.slides[slideIndex] = {
            ...updatedOutline.slides[slideIndex],
            ...result.updated_slide
          }
          setOutline(updatedOutline)
          onUpdate(updatedOutline)
        }
      }
    } catch (error) {
      console.error('Error updating slide layout:', error)
    }
  }

  const getLayoutTypeBadge = (slide: SlideOutline) => {
    if (slide.is_html && slide.is_image) return 'html+image'
    if (slide.is_html) return 'html'
    if (slide.is_image) return 'image'
    return 'text'
  }

  const getLayoutBadgeColor = (type: string) => {
    switch (type) {
      case 'html': return 'bg-blue-100 text-blue-700'
      case 'image': return 'bg-green-100 text-green-700'
      case 'html+image': return 'bg-purple-100 text-purple-700'
      default: return 'bg-gray-100 text-gray-700'
    }
  }

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
              {outline.slides?.length || 0} slides • ~{outline.estimated_duration || (outline.slides?.length || 0) * 2} minutes
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
          {outline.objectives && outline.objectives.length > 0 && (
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
          {outline.slides && outline.slides.map((slide, index) => (
            <div key={`slide-${slide.slide_number}`} className="group">
              <Card className="p-3">
                <div className="flex items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant="outline" className="text-xs">
                        #{slide.slide_number}
                      </Badge>
                      <Badge className={`text-xs ${getLayoutBadgeColor(getLayoutTypeBadge(slide))}`}>
                        {getLayoutTypeBadge(slide)}
                      </Badge>
                    </div>
                    <h4 className="font-medium text-sm mb-2">{slide.title}</h4>
                    
                    {/* Layout Selector */}
                    {sessionId && availableLayouts.length > 0 && (
                      <div className="mb-2">
                        <Select
                          value={slide.layout_index?.toString() || ""}
                          onValueChange={(value) => handleLayoutChange(slide.slide_number, parseInt(value))}
                          disabled={loadingLayouts}
                        >
                          <SelectTrigger className="h-7 text-xs w-full max-w-xs">
                            <SelectValue placeholder={slide.layout_name || "Select layout"} />
                          </SelectTrigger>
                          <SelectContent>
                            {availableLayouts.map((layout) => (
                              <SelectItem key={layout.index} value={layout.index.toString()}>
                                <div className="flex items-center gap-2 w-full">
                                  <div className="flex gap-1">
                                    {layout.supports_html && (
                                      <Badge variant="secondary" className="text-xs px-1 py-0">H</Badge>
                                    )}
                                    {layout.supports_image && (
                                      <Badge variant="secondary" className="text-xs px-1 py-0">I</Badge>
                                    )}
                                  </div>
                                  <span className="text-xs">{layout.name}</span>
                                </div>
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    )}
                    {slide.key_points && slide.key_points.length > 0 && (
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