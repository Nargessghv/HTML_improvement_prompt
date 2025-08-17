'use client'

import { useParams, useRouter } from 'next/navigation'
import { PresentationPlanner } from '@/components/chat'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ArrowLeft, Sparkles, Loader2 } from 'lucide-react'
import { useState, useEffect } from 'react'
import { toast } from 'sonner'
import { useSupabaseAuth } from '@/hooks/useSupabaseAuthSimple'

interface Project {
  id: string
  title: string
  topic: string
  status: string
}

export default function InteractivePlanningPage() {
  const params = useParams()
  const router = useRouter()
  const { supabase, user } = useSupabaseAuth()
  const projectId = params?.id as string
  const [isGenerating, setIsGenerating] = useState(false)
  const [project, setProject] = useState<Project | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (!projectId || !user) return

    const fetchProject = async () => {
      try {
        const { data, error } = await supabase
          .from('projects')
          .select('*')
          .eq('id', projectId)
          .eq('user_id', user.id)
          .single()

        if (error) {
          console.error('Error fetching project:', error)
          toast.error('Failed to load project')
          router.push('/projects')
          return
        }

        setProject(data)
      } catch (error) {
        console.error('Unexpected error:', error)
        toast.error('An unexpected error occurred')
      } finally {
        setIsLoading(false)
      }
    }

    fetchProject()
  }, [projectId, user, supabase, router])

  const handleApproveOutline = async (fullOutline: unknown) => {
    setIsGenerating(true)
    
    try {
      // Get the auth token for API request
      const { data: { session } } = await supabase.auth.getSession()
      
      if (!session) {
        toast.error('Authentication required')
        return
      }

      // Trigger slide generation workflow with approved outline
      const response = await fetch(`/api/projects`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`
        },
        body: JSON.stringify({
          title: project?.title || 'Interactive Presentation',
          topic: project?.topic || 'Generated from interactive planning',
          project_id: projectId, // This tells the API to start workflow on existing project
          approved_outline: fullOutline // Include the approved outline for the agents
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.message || 'Failed to start generation')
      }

      toast.success('Presentation outline approved! Generation will begin shortly.')
      
      // Navigate back to project page to show progress
      setTimeout(() => {
        router.push(`/projects/${projectId}`)
      }, 1500)
    } catch (error) {
      console.error('Error starting generation:', error)
      toast.error(error instanceof Error ? error.message : 'Failed to start generation')
    } finally {
      setIsGenerating(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex items-center space-x-2">
          <Loader2 className="w-6 h-6 animate-spin text-primary" />
          <span className="text-muted-foreground">Loading project...</span>
        </div>
      </div>
    )
  }

  if (!project) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <h2 className="text-xl font-semibold mb-2">Project not found</h2>
          <p className="text-muted-foreground mb-4">The project you&apos;re looking for doesn&apos;t exist or you don&apos;t have access to it.</p>
          <Button onClick={() => router.push('/projects')}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Projects
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="p-6 flex-shrink-0">
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => router.push(`/projects/${projectId}`)}
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Project
            </Button>
            <div>
              <h1 className="text-2xl font-bold flex items-center gap-2">
                <Sparkles className="w-6 h-6 text-primary" />
                Interactive Presentation Planning
              </h1>
              <p className="text-muted-foreground">
                Chat with AI to plan and structure your presentation for &quot;{project.title}&quot;
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 px-6 pb-6 min-h-0">
        <Card className="max-w-7xl mx-auto h-full flex flex-col">
          <CardHeader className="flex-shrink-0">
            <CardTitle>Plan Your Presentation</CardTitle>
          </CardHeader>
          <CardContent className="p-6 flex-1 min-h-0">
            <PresentationPlanner
              projectId={projectId}
              initialTopic={project.topic}
              onApproveOutline={handleApproveOutline}
            />
          </CardContent>
        </Card>
      </div>

      {isGenerating && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm flex items-center justify-center z-50">
          <Card className="p-6">
            <div className="flex items-center gap-3">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              <p>Starting presentation generation...</p>
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}