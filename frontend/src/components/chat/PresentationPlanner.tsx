'use client'

import { useState } from 'react'
import { ChatInterface } from './ChatInterface'
import { OutlineBuilder } from './OutlineBuilder'
import { Card, CardContent } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { MessageSquare, FileText, CheckCircle } from 'lucide-react'
import { Badge } from '@/components/ui/badge'

interface PresentationOutline {
  title: string
  topic: string
  target_audience?: string
  objectives: string[]
  key_themes: string[]
  estimated_duration?: number
  style_preferences: Record<string, unknown>
  slides: Array<{
    slide_number: number
    title: string
    is_html: boolean
    is_image: boolean
    key_points: string[]
  }>
}

interface PresentationPlannerProps {
  projectId: string
  initialTopic?: string
  onApproveOutline?: (fullOutline: PresentationOutline) => void
}

export function PresentationPlanner({ 
  projectId, 
  initialTopic,
  onApproveOutline 
}: PresentationPlannerProps) {
  const [outline, setOutline] = useState<PresentationOutline | null>(null)
  const [fullOutline, setFullOutline] = useState<PresentationOutline | null>(null)
  const [activeTab, setActiveTab] = useState('chat')
  const [isApproved, setIsApproved] = useState(false)

  const handleOutlineGenerated = (newOutline: PresentationOutline, newFullOutline?: PresentationOutline) => {
    // console.log('📋 PresentationPlanner received outline:', newOutline)
    // console.log('📋 PresentationPlanner received full outline:', newFullOutline)
    setOutline(newOutline)
    setFullOutline(newFullOutline || newOutline)
    // Automatically switch to outline tab when generated
    setActiveTab('outline')
  }

  const handleOutlineUpdate = (updatedOutline: PresentationOutline) => {
    setOutline(updatedOutline)
  }

  const handleApproveOutline = () => {
    setIsApproved(true)
    if (onApproveOutline && outline) {
      // Use the full outline for workflow processing, fallback to simplified outline
      onApproveOutline(fullOutline || outline)
    }
  }

  return (
    <div className="h-full flex flex-col min-h-0">
      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col min-h-0">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="chat" className="flex items-center gap-2">
            <MessageSquare className="w-4 h-4" />
            Chat Planning
          </TabsTrigger>
          <TabsTrigger value="outline" className="flex items-center gap-2">
            <FileText className="w-4 h-4" />
            Presentation Outline
            {outline && (
              <Badge variant={isApproved ? "default" : "secondary"} className="ml-2">
                {isApproved ? <CheckCircle className="w-3 h-3 mr-1" /> : null}
                {outline.slides?.length || 0} slides
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="chat" className="flex-1 mt-4 min-h-0">
          <ChatInterface
            projectId={projectId}
            initialTopic={initialTopic}
            onOutlineGenerated={handleOutlineGenerated}
            className="h-full"
          />
        </TabsContent>

        <TabsContent value="outline" className="flex-1 mt-4 min-h-0">
          {outline ? (
            <OutlineBuilder
              outline={outline}
              onUpdate={handleOutlineUpdate}
              onApprove={handleApproveOutline}
              className="h-full"
            />
          ) : (
            <Card className="h-full">
              <CardContent className="flex items-center justify-center h-full">
                <div className="text-center text-muted-foreground">
                  <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p className="text-sm">
                    No outline yet. Use the chat to plan your presentation.
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}