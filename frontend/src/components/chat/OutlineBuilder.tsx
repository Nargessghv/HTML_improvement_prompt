'use client'

import { useState } from 'react'
import { 
  DragDropContext, 
  Droppable, 
  Draggable,
  DropResult 
} from '@hello-pangea/dnd'
import { 
  GripVertical, 
  Plus, 
  Trash2, 
  Edit3, 
  Check,
  X,
  FileText,
  BarChart3,
  Clock,
  GitBranch,
  Layers
} from 'lucide-react'
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

const contentTypeIcons = {
  text: FileText,
  visual: Layers,
  chart: BarChart3,
  timeline: Clock,
  comparison: GitBranch
}

const contentTypeColors = {
  text: 'bg-blue-100 text-blue-700',
  visual: 'bg-purple-100 text-purple-700',
  chart: 'bg-green-100 text-green-700',
  timeline: 'bg-orange-100 text-orange-700',
  comparison: 'bg-pink-100 text-pink-700'
}

export function OutlineBuilder({ 
  outline: initialOutline, 
  onUpdate, 
  onApprove,
  className 
}: OutlineBuilderProps) {
  const [outline, setOutline] = useState<PresentationOutline | null>(initialOutline)
  const [editingSlide, setEditingSlide] = useState<number | null>(null)
  const [editingTitle, setEditingTitle] = useState('')

  if (!outline) {
    return (
      <Card className={cn("h-full", className)}>
        <CardContent className="flex items-center justify-center h-full text-muted-foreground">
          <p className="text-sm">No outline generated yet. Continue chatting to create one.</p>
        </CardContent>
      </Card>
    )
  }

  const handleDragEnd = (result: DropResult) => {
    if (!result.destination || !outline) return

    const slides = Array.from(outline.slides)
    const [reorderedSlide] = slides.splice(result.source.index, 1)
    slides.splice(result.destination.index, 0, reorderedSlide)

    // Update slide numbers
    const updatedSlides = slides.map((slide, index) => ({
      ...slide,
      slide_number: index + 1
    }))

    const updatedOutline = { ...outline, slides: updatedSlides }
    setOutline(updatedOutline)
    onUpdate(updatedOutline)
  }

  const addSlide = (afterIndex: number) => {
    if (!outline) return

    const newSlide: SlideOutline = {
      slide_number: afterIndex + 2,
      title: 'New Slide',
      content_type: 'text',
      key_points: ['Add your content here'],
      suggested_layout: 'Content'
    }

    const slides = [...outline.slides]
    slides.splice(afterIndex + 1, 0, newSlide)

    // Update slide numbers
    const updatedSlides = slides.map((slide, index) => ({
      ...slide,
      slide_number: index + 1
    }))

    const updatedOutline = { ...outline, slides: updatedSlides }
    setOutline(updatedOutline)
    onUpdate(updatedOutline)
  }

  const removeSlide = (index: number) => {
    if (!outline || outline.slides.length <= 1) return

    const slides = outline.slides.filter((_, i) => i !== index)
    
    // Update slide numbers
    const updatedSlides = slides.map((slide, idx) => ({
      ...slide,
      slide_number: idx + 1
    }))

    const updatedOutline = { ...outline, slides: updatedSlides }
    setOutline(updatedOutline)
    onUpdate(updatedOutline)
  }

  const startEditingSlide = (index: number) => {
    setEditingSlide(index)
    setEditingTitle(outline.slides[index].title)
  }

  const saveSlideEdit = () => {
    if (!outline || editingSlide === null) return

    const updatedSlides = [...outline.slides]
    updatedSlides[editingSlide] = {
      ...updatedSlides[editingSlide],
      title: editingTitle
    }

    const updatedOutline = { ...outline, slides: updatedSlides }
    setOutline(updatedOutline)
    onUpdate(updatedOutline)
    setEditingSlide(null)
    setEditingTitle('')
  }

  const cancelSlideEdit = () => {
    setEditingSlide(null)
    setEditingTitle('')
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

        <DragDropContext onDragEnd={handleDragEnd}>
          <Droppable droppableId="slides">
            {(provided) => (
              <div
                {...provided.droppableProps}
                ref={provided.innerRef}
                className="space-y-2 max-h-[500px] overflow-y-auto pr-2"
              >
                {outline.slides.map((slide, index) => {
                  const Icon = contentTypeIcons[slide.content_type]
                  const colorClass = contentTypeColors[slide.content_type]

                  return (
                    <Draggable
                      key={`slide-${slide.slide_number}`}
                      draggableId={`slide-${slide.slide_number}`}
                      index={index}
                    >
                      {(provided, snapshot) => (
                        <div
                          ref={provided.innerRef}
                          {...provided.draggableProps}
                          className={cn(
                            "group",
                            snapshot.isDragging && "opacity-50"
                          )}
                        >
                          <Card className="p-3">
                            <div className="flex items-start gap-2">
                              <div
                                {...provided.dragHandleProps}
                                className="mt-1 opacity-0 group-hover:opacity-100 transition-opacity cursor-grab"
                              >
                                <GripVertical className="w-4 h-4 text-muted-foreground" />
                              </div>

                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-1">
                                  <Badge variant="outline" className="text-xs">
                                    #{slide.slide_number}
                                  </Badge>
                                  <Badge className={cn("text-xs", colorClass)}>
                                    <Icon className="w-3 h-3 mr-1" />
                                    {slide.content_type}
                                  </Badge>
                                </div>

                                {editingSlide === index ? (
                                  <div className="flex items-center gap-2">
                                    <Input
                                      value={editingTitle}
                                      onChange={(e) => setEditingTitle(e.target.value)}
                                      className="h-7 text-sm"
                                      autoFocus
                                      onKeyPress={(e) => {
                                        if (e.key === 'Enter') saveSlideEdit()
                                        if (e.key === 'Escape') cancelSlideEdit()
                                      }}
                                    />
                                    <Button
                                      size="icon"
                                      variant="ghost"
                                      className="h-7 w-7"
                                      onClick={saveSlideEdit}
                                    >
                                      <Check className="w-3 h-3" />
                                    </Button>
                                    <Button
                                      size="icon"
                                      variant="ghost"
                                      className="h-7 w-7"
                                      onClick={cancelSlideEdit}
                                    >
                                      <X className="w-3 h-3" />
                                    </Button>
                                  </div>
                                ) : (
                                  <h4 className="font-medium text-sm">{slide.title}</h4>
                                )}

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

                              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                <Button
                                  size="icon"
                                  variant="ghost"
                                  className="h-7 w-7"
                                  onClick={() => startEditingSlide(index)}
                                >
                                  <Edit3 className="w-3 h-3" />
                                </Button>
                                <Button
                                  size="icon"
                                  variant="ghost"
                                  className="h-7 w-7"
                                  onClick={() => addSlide(index)}
                                >
                                  <Plus className="w-3 h-3" />
                                </Button>
                                <Button
                                  size="icon"
                                  variant="ghost"
                                  className="h-7 w-7 text-destructive"
                                  onClick={() => removeSlide(index)}
                                  disabled={outline.slides.length <= 1}
                                >
                                  <Trash2 className="w-3 h-3" />
                                </Button>
                              </div>
                            </div>
                          </Card>
                        </div>
                      )}
                    </Draggable>
                  )
                })}
                {provided.placeholder}
              </div>
            )}
          </Droppable>
        </DragDropContext>

        <Button
          variant="outline"
          size="sm"
          className="w-full mt-4"
          onClick={() => addSlide(outline.slides.length - 1)}
        >
          <Plus className="w-4 h-4 mr-2" />
          Add Slide
        </Button>
      </CardContent>
    </Card>
  )
}