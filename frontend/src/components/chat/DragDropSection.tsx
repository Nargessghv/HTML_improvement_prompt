'use client'

import { useEffect, useState } from 'react'
import type { DropResult } from '@hello-pangea/dnd'

// Dynamic import to avoid SSR issues
let DragDropContext: any = null
let Droppable: any = null
let Draggable: any = null
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
import { Card } from '@/components/ui/card'
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

interface DragDropSectionProps {
  outline: PresentationOutline
  editingSlide: number | null
  editingTitle: string
  onDragEnd: (result: DropResult) => void
  onAddSlide: (afterIndex: number) => void
  onRemoveSlide: (index: number) => void
  onStartEditingSlide: (index: number) => void
  onSaveSlideEdit: () => void
  onCancelSlideEdit: () => void
  onEditingTitleChange: (value: string) => void
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

export function DragDropSection({
  outline,
  editingSlide,
  editingTitle,
  onDragEnd,
  onAddSlide,
  onRemoveSlide,
  onStartEditingSlide,
  onSaveSlideEdit,
  onCancelSlideEdit,
  onEditingTitleChange
}: DragDropSectionProps) {
  const [isReady, setIsReady] = useState(false)

  useEffect(() => {
    const loadDragDropComponents = async () => {
      try {
        const dnd = await import('@hello-pangea/dnd')
        DragDropContext = dnd.DragDropContext
        Droppable = dnd.Droppable
        Draggable = dnd.Draggable
        setIsReady(true)
      } catch (error) {
        console.error('Failed to load drag-and-drop components:', error)
      }
    }

    loadDragDropComponents()
  }, [])

  if (!isReady || !DragDropContext || !Droppable || !Draggable) {
    return (
      <div className="space-y-2 max-h-[500px] overflow-y-auto pr-2">
        {outline.slides.map((slide, index) => {
          const Icon = contentTypeIcons[slide.content_type]
          const colorClass = contentTypeColors[slide.content_type]

          return (
            <div key={`slide-${slide.slide_number}`} className="group">
              <Card className="p-3">
                <div className="flex items-start gap-2">
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
          )
        })}
      </div>
    )
  }

  return (
    <DragDropContext onDragEnd={onDragEnd}>
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
                                  onChange={(e) => onEditingTitleChange(e.target.value)}
                                  className="h-7 text-sm"
                                  autoFocus
                                  onKeyPress={(e) => {
                                    if (e.key === 'Enter') onSaveSlideEdit()
                                    if (e.key === 'Escape') onCancelSlideEdit()
                                  }}
                                />
                                <Button
                                  size="icon"
                                  variant="ghost"
                                  className="h-7 w-7"
                                  onClick={onSaveSlideEdit}
                                >
                                  <Check className="w-3 h-3" />
                                </Button>
                                <Button
                                  size="icon"
                                  variant="ghost"
                                  className="h-7 w-7"
                                  onClick={onCancelSlideEdit}
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
                              onClick={() => onStartEditingSlide(index)}
                            >
                              <Edit3 className="w-3 h-3" />
                            </Button>
                            <Button
                              size="icon"
                              variant="ghost"
                              className="h-7 w-7"
                              onClick={() => onAddSlide(index)}
                            >
                              <Plus className="w-3 h-3" />
                            </Button>
                            <Button
                              size="icon"
                              variant="ghost"
                              className="h-7 w-7 text-destructive"
                              onClick={() => onRemoveSlide(index)}
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
  )
}