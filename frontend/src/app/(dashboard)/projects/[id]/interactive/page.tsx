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

  const handleApproveOutline = async (_outline: unknown) => {
    setIsGenerating(true)
    
    try {
      // TODO: Trigger slide generation based on outline
      toast.success('Presentation outline approved! Generation will begin shortly.')
      
      // For now, just navigate back to project page
      setTimeout(() => {
        router.push(`/projects/${projectId}`)
      }, 2000)
    } catch (error) {
      console.error('Error starting generation:', error)
      toast.error('Failed to start generation')
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
    <div className="p-6">
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

      <Card className="max-w-7xl mx-auto">
        <CardHeader>
          <CardTitle>Plan Your Presentation</CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <div className="h-[600px]">
            <PresentationPlanner
              projectId={projectId}
              initialTopic={project.topic}
              onApproveOutline={handleApproveOutline}
            />
          </div>
        </CardContent>
      </Card>

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