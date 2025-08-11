'use client'

import { useState, useEffect } from 'react'
import Image from 'next/image'
import { useSupabaseAuth } from '@/hooks/useSupabaseAuthSimple'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
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
  Maximize2,
  Download,
  ZoomIn,
  ZoomOut,
  RotateCcw
} from 'lucide-react'
import { toast } from 'sonner'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'

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

interface RefinementViewerProps {
  projectId: string
  className?: string
}

export function RefinementViewer({ projectId, className }: RefinementViewerProps) {
  const { supabase, user } = useSupabaseAuth()
  const [slides, setSlides] = useState<Slide[]>([])
  const [refinements, setRefinements] = useState<Record<string, RefinementIteration[]>>({})
  const [selectedSlide, setSelectedSlide] = useState<string | null>(null)
  const [selectedIteration, setSelectedIteration] = useState<number>(1)
  const [isLoading, setIsLoading] = useState(true)
  const [viewMode, setViewMode] = useState<'preview' | 'html'>('preview')
  const [useNativeImg, setUseNativeImg] = useState(false)
  const [zoomLevel, setZoomLevel] = useState(1)

  useEffect(() => {
    if (!projectId || !user) return

    fetchRefinementData()
  }, [projectId, user, supabase]) // eslint-disable-line react-hooks/exhaustive-deps

  const refreshSignedUrl = async (refinementId: string, filePath: string): Promise<string | null> => {
    try {
      // Generate a new signed URL for the file
      const { data, error } = await supabase.storage
        .from('html-refinements')
        .createSignedUrl(filePath, 3600)
      
      if (error) {
        // Failed to refresh signed URL
        return null
      }
      
      return data?.signedUrl || null
    } catch {
      // Error refreshing signed URL
      return null
    }
  }

  const fetchRefinementData = async () => {
    try {
      setIsLoading(true)
      
      // Fetch slides for this project
      const { data: slidesData, error: slidesError } = await supabase
        .from('slides')
        .select('*')
        .eq('project_id', projectId)
        .order('slide_number', { ascending: true })

      if (slidesError) {
        // Error fetching slides
        toast.error('Failed to load slides')
        return
      }

      setSlides(slidesData || [])

      // Fetch all refinements for this project
      const { data: refinementsData, error: refinementsError } = await supabase
        .from('html_refinements')
        .select('*')
        .eq('project_id', projectId)
        .order('iteration_number', { ascending: true })

      if (refinementsError) {
        // Error fetching refinements
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
      
      // Auto-select first slide with refinements
      const firstSlideWithRefinements = slidesData?.find(slide => grouped[slide.id]?.length > 0)
      if (firstSlideWithRefinements && !selectedSlide) {
        setSelectedSlide(firstSlideWithRefinements.id)
      }

    } catch {
      // Error fetching refinement data
      toast.error('Failed to load refinement data')
    } finally {
      setIsLoading(false)
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
    setSelectedIteration(1) // Reset to first iteration when switching slides
  }

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
      <Card className={className}>
        <CardHeader>
          <CardTitle>HTML Refinement Viewer</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center space-x-2">
            <RefreshCw className="w-4 h-4 animate-spin" />
            <span>Loading refinement data...</span>
          </div>
        </CardContent>
      </Card>
    )
  }

  const slidesWithRefinements = slides.filter(slide => getSlideRefinements(slide.id).length > 0)

  if (slidesWithRefinements.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>HTML Refinement Viewer</CardTitle>
          <CardDescription>
            View HTML refinement iterations with visual previews
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-gray-500">
            <ImageIcon className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p>No HTML refinements found for this project</p>
            <p className="text-sm">Refinements will appear here after the HTML generation process</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  const currentRefinement = getCurrentRefinement()
  const currentSlideRefinements = selectedSlide ? getSlideRefinements(selectedSlide) : []
  const maxIteration = Math.max(...currentSlideRefinements.map(r => r.iteration_number), 0)
  const finalRefinement = currentSlideRefinements.find(r => r.is_final)

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              HTML Refinement Viewer
              {finalRefinement && (
                <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                  <CheckCircle className="w-3 h-3 mr-1" />
                  Final
                </Badge>
              )}
            </CardTitle>
            <CardDescription>
              View and compare HTML refinement iterations with visual previews
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={fetchRefinementData}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Slide Selection */}
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

        {/* Content Viewer */}
        {currentRefinement && (
          <Tabs value={viewMode} onValueChange={(value) => setViewMode(value as 'preview' | 'html')}>
            <div className="flex items-center justify-between">
              <TabsList>
                <TabsTrigger value="preview" className="flex items-center gap-2">
                  <Eye className="w-4 h-4" />
                  Preview
                </TabsTrigger>
                <TabsTrigger value="html" className="flex items-center gap-2">
                  <Code className="w-4 h-4" />
                  HTML Code
                </TabsTrigger>
              </TabsList>
              
              <div className="flex items-center space-x-2">
                {/* Zoom Controls */}
                <div className="flex items-center space-x-1 border rounded px-2">
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={() => setZoomLevel(Math.max(0.5, zoomLevel - 0.25))}
                    disabled={zoomLevel <= 0.5}
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
                    onClick={() => setZoomLevel(1)}
                  >
                    <RotateCcw className="w-3 h-3" />
                  </Button>
                </div>
                
                <Button variant="outline" size="sm" onClick={downloadHtml}>
                  <Download className="w-4 h-4 mr-2" />
                  Download HTML
                </Button>
                <Dialog>
                  <DialogTrigger asChild>
                    <Button variant="outline" size="sm">
                      <Maximize2 className="w-4 h-4 mr-2" />
                      Full Screen
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="max-w-6xl h-[80vh]">
                    <DialogHeader>
                      <DialogTitle>
                        {getSlideTitle(currentRefinement.slide_id)} - Iteration {currentRefinement.iteration_number}
                      </DialogTitle>
                    </DialogHeader>
                    <div className="h-full">
                      {/* Thumbnail bar if available */}
                      {currentRefinement.image_file_url && (
                        <div className="flex items-center gap-3 p-4 bg-gray-50 border-b">
                          <div className="relative w-16 h-12 bg-white rounded border overflow-hidden">
                            <Image 
                              src={currentRefinement.image_file_url} 
                              alt={`Thumbnail iteration ${currentRefinement.iteration_number}`}
                              fill
                              className="object-contain"
                            />
                          </div>
                          <div className="text-sm text-gray-600">
                            <div className="font-medium">Screenshot Reference</div>
                            <div>Generated at render time</div>
                          </div>
                        </div>
                      )}
                      
                      {/* Full-size HTML Preview in isolated iframe */}
                      <iframe
                        srcDoc={currentRefinement.html_content}
                        className="w-full bg-white border-0"
                        style={{ 
                          height: currentRefinement.image_file_url ? 'calc(100% - 80px)' : '100%',
                          width: '100%'
                        }}
                        sandbox="allow-same-origin allow-scripts"
                        title={`HTML Preview - Iteration ${currentRefinement.iteration_number}`}
                      />
                    </div>
                  </DialogContent>
                </Dialog>
              </div>
            </div>

            <TabsContent value="preview" className="space-y-4">
              {/* Thumbnail if available */}
              {currentRefinement.image_file_url && (
                <div className="flex items-center gap-3">
                  <div className="relative w-20 h-16 bg-gray-100 rounded border overflow-hidden">
                    {useNativeImg ? (
                      // Fallback to native img tag
                      <img 
                        src={currentRefinement.image_file_url} 
                        alt={`Thumbnail iteration ${currentRefinement.iteration_number}`}
                        className="w-full h-full object-contain"
                        onError={(e) => {
                          // Native img load error
                          e.currentTarget.style.display = 'none';
                        }}
                      />
                    ) : (
                      <Image 
                        src={currentRefinement.image_file_url} 
                        alt={`Thumbnail iteration ${currentRefinement.iteration_number}`}
                        fill
                        className="object-contain"
                        onError={async () => {
                          // Image load failed - attempt URL refresh
                          
                          // Try to extract the file path from the URL for refreshing signed URL
                          try {
                            const urlParts = currentRefinement.image_file_url.split('/storage/v1/object/sign/html-refinements/')[1];
                            if (urlParts) {
                              const filePath = urlParts.split('?')[0]; // Remove query params
                              // Attempting to refresh signed URL
                              
                              const newSignedUrl = await refreshSignedUrl(currentRefinement.id, filePath);
                              if (newSignedUrl) {
                                // Got new signed URL
                                // Update the refinement data with new URL
                                setRefinements(prev => {
                                  const updated = { ...prev };
                                  if (updated[currentRefinement.slide_id]) {
                                    updated[currentRefinement.slide_id] = updated[currentRefinement.slide_id].map(r => 
                                      r.id === currentRefinement.id ? { ...r, image_file_url: newSignedUrl } : r
                                    );
                                  }
                                  return updated;
                                });
                                return;
                              }
                            }
                          } catch {
                            // Failed to refresh signed URL
                          }
                          
                          // Switching to native img tag
                          setUseNativeImg(true);
                        }}
                      />
                    )}
                    {/* Fallback icon if image fails to load */}
                    <div className="absolute inset-0 flex items-center justify-center bg-gray-50">
                      <ImageIcon className="w-6 h-6 text-gray-400" />
                    </div>
                  </div>
                  <div className="text-sm text-gray-600">
                    <div className="font-medium">Screenshot Available</div>
                    <div>Generated at render time</div>
                    <div className="text-xs text-gray-400 mt-1">
                      {currentRefinement.image_file_url.split('/').pop()}
                    </div>
                  </div>
                </div>
              )}

              {/* Live HTML Preview in isolated iframe */}
              <div className="border rounded-lg overflow-hidden">
                <div className="bg-gray-50 px-3 py-2 border-b text-sm font-medium text-gray-700 flex items-center justify-between">
                  <span>Live HTML Preview</span>
                  <span className="text-xs text-gray-500">Rendered in isolated frame • Zoom {Math.round(zoomLevel * 100)}%</span>
                </div>
                <div className="relative overflow-auto bg-gray-100">
                  <div 
                    style={{ 
                      transform: `scale(${zoomLevel})`,
                      transformOrigin: 'top left',
                      width: `${100 / zoomLevel}%`,
                      height: `${450 / zoomLevel}px`,
                    }}
                  >
                    <iframe
                      srcDoc={currentRefinement.html_content}
                      className="w-full bg-white border-0"
                      style={{ 
                        height: '450px',
                        minHeight: '450px',
                        width: '100%',
                      }}
                      sandbox="allow-same-origin allow-scripts allow-popups"
                      title={`HTML Preview - Iteration ${currentRefinement.iteration_number}`}
                    />
                  </div>
                  
                  {/* Debug info */}
                  <div className="absolute bottom-2 right-2 text-xs bg-black bg-opacity-50 text-white px-2 py-1 rounded">
                    <div>HTML Size: {(currentRefinement.html_content.length / 1024).toFixed(1)}KB</div>
                    <div>Contains viewport: {currentRefinement.html_content.includes('viewport') ? 'Yes' : 'No'}</div>
                    <div>Has body tag: {currentRefinement.html_content.includes('<body') ? 'Yes' : 'No'}</div>
                  </div>
                  
                  {/* Debug button to view raw HTML */}
                  <button
                    onClick={() => {
                      // HTML content debugging information available
                    }}
                    className="absolute top-2 right-2 text-xs bg-blue-500 text-white px-2 py-1 rounded"
                  >
                    Debug HTML
                  </button>
                </div>
              </div>

              {/* Refinement Feedback */}
              {currentRefinement.refinement_feedback && (
                <div className="space-y-2">
                  <h4 className="text-sm font-medium">LLM Feedback:</h4>
                  <div className="bg-gray-50 p-3 rounded text-sm">
                    <pre className="whitespace-pre-wrap font-mono text-xs">
                      {currentRefinement.refinement_feedback}
                    </pre>
                  </div>
                </div>
              )}
            </TabsContent>

            <TabsContent value="html" className="space-y-4">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-medium">HTML Source Code</h4>
                  <div className="text-xs text-gray-500">
                    {currentRefinement.html_content.length} characters
                  </div>
                </div>
                <ScrollArea className="h-96 w-full border rounded">
                  <pre className="p-4 text-xs">
                    <code>{currentRefinement.html_content}</code>
                  </pre>
                </ScrollArea>
              </div>
            </TabsContent>
          </Tabs>
        )}

        {/* Iteration Timeline */}
        {selectedSlide && currentSlideRefinements.length > 1 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium">Refinement Timeline:</h4>
            <div className="flex space-x-2 overflow-x-auto pb-2">
              {currentSlideRefinements.map((refinement) => (
                <Button
                  key={refinement.id}
                  variant={selectedIteration === refinement.iteration_number ? "default" : "outline"}
                  size="sm"
                  onClick={() => setSelectedIteration(refinement.iteration_number)}
                  className="flex-shrink-0"
                >
                  <div className="text-center">
                    <div className="flex items-center gap-1">
                      <span>#{refinement.iteration_number}</span>
                      {refinement.is_final && <CheckCircle className="w-3 h-3" />}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {new Date(refinement.created_at).toLocaleTimeString()}
                    </div>
                  </div>
                </Button>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}