'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { useSupabaseAuth } from '@/hooks/useSupabaseAuthSimple'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { 
  EditProjectModal,
  DeleteProjectModal,
  DuplicateProjectModal,
  ShareProjectModal
} from '@/components/modals'
import { 
  ArrowLeft, 
  Calendar, 
  Clock, 
  User, 
  PlayCircle,
  CheckCircle2,
  XCircle,
  Loader2,
  Edit3,
  Trash2,
  Copy,
  Share2,
  MoreHorizontal
} from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

interface Project {
  id: string
  title: string
  topic: string
  status: 'draft' | 'processing' | 'completed' | 'failed'
  created_at: string
  updated_at: string
  completed_at: string | null
}

const statusConfig = {
  draft: { 
    label: 'Draft', 
    color: 'bg-gray-100 text-gray-800',
    icon: Clock 
  },
  processing: { 
    label: 'Processing', 
    color: 'bg-blue-100 text-blue-800',
    icon: Loader2 
  },
  completed: { 
    label: 'Completed', 
    color: 'bg-green-100 text-green-800',
    icon: CheckCircle2 
  },
  failed: { 
    label: 'Failed', 
    color: 'bg-red-100 text-red-800',
    icon: XCircle 
  }
}

export default function ProjectDetailPage() {
  const params = useParams()
  const router = useRouter()
  const { supabase, user } = useSupabaseAuth()
  const [project, setProject] = useState<Project | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isStarting, setIsStarting] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [showDuplicateModal, setShowDuplicateModal] = useState(false)
  const [showShareModal, setShowShareModal] = useState(false)

  const projectId = params?.id as string

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
          router.push('/dashboard')
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

  const startProcessing = async () => {
    if (!project) return

    setIsStarting(true)
    try {
      // Update project status to processing
      const { error } = await supabase
        .from('projects')
        .update({ status: 'processing' })
        .eq('id', project.id)

      if (error) {
        toast.error('Failed to start processing')
        return
      }

      setProject({ ...project, status: 'processing' })
      toast.success('Project processing started!')

      // TODO: Call backend API to start the AI workflow
      // This will be implemented when we add backend integration

    } catch (error) {
      console.error('Error starting processing:', error)
      toast.error('An unexpected error occurred')
    } finally {
      setIsStarting(false)
    }
  }

  const handleProjectUpdated = (updatedProject: Project) => {
    setProject(updatedProject)
    toast.success('Project updated successfully!')
  }

  const handleProjectDeleted = () => {
    toast.success('Project deleted successfully')
    router.push('/projects')
  }

  const handleProjectDuplicated = (newProject: Project) => {
    toast.success('Project duplicated successfully!')
    router.push(`/projects/${newProject.id}`)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex items-center space-x-2">
          <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
          <span className="text-gray-600">Loading project...</span>
        </div>
      </div>
    )
  }

  if (!project) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Project not found</h2>
          <p className="text-gray-600 mb-4">The project you&apos;re looking for doesn&apos;t exist or you don&apos;t have access to it.</p>
          <Button onClick={() => router.push('/dashboard')}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Dashboard
          </Button>
        </div>
      </div>
    )
  }

  const StatusIcon = statusConfig[project.status].icon

  return (
    <div className="p-6 max-w-4xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-4">
          <Button 
            variant="ghost" 
            size="sm"
            onClick={() => router.push('/dashboard')}
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{project.title}</h1>
            <div className="flex items-center space-x-4 mt-1 text-sm text-gray-500">
              <div className="flex items-center space-x-1">
                <Calendar className="w-4 h-4" />
                <span>Created {new Date(project.created_at).toLocaleDateString()}</span>
              </div>
              <div className="flex items-center space-x-1">
                <User className="w-4 h-4" />
                <span>Project ID: {project.id.slice(0, 8)}</span>
              </div>
            </div>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          <Badge className={statusConfig[project.status].color}>
            <StatusIcon className={`w-4 h-4 mr-1 ${project.status === 'processing' ? 'animate-spin' : ''}`} />
            {statusConfig[project.status].label}
          </Badge>
          {project.status === 'draft' && (
            <Button 
              onClick={startProcessing}
              disabled={isStarting}
              className="bg-blue-600 hover:bg-blue-700"
            >
              {isStarting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Starting...
                </>
              ) : (
                <>
                  <PlayCircle className="w-4 h-4 mr-2" />
                  Start Processing
                </>
              )}
            </Button>
          )}
          
          {/* Project Actions Menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm">
                <MoreHorizontal className="w-4 h-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => setShowEditModal(true)}>
                <Edit3 className="w-4 h-4 mr-2" />
                Edit Project
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setShowDuplicateModal(true)}>
                <Copy className="w-4 h-4 mr-2" />
                Duplicate
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setShowShareModal(true)}>
                <Share2 className="w-4 h-4 mr-2" />
                Share
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem 
                onClick={() => setShowDeleteModal(true)}
                className="text-red-600 focus:text-red-600"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Delete Project
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Project Details */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Project Description</CardTitle>
              <CardDescription>
                The topic and requirements for this presentation
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="whitespace-pre-wrap text-gray-700">
                {project.topic}
              </div>
            </CardContent>
          </Card>

          {/* Workflow Progress - Placeholder for now */}
          <Card className="mt-6">
            <CardHeader>
              <CardTitle>Workflow Progress</CardTitle>
              <CardDescription>
                AI agents working on your presentation
              </CardDescription>
            </CardHeader>
            <CardContent>
              {project.status === 'draft' ? (
                <div className="text-center py-8 text-gray-500">
                  <PlayCircle className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                  <p>Click "Start Processing" to begin the AI workflow</p>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="text-sm text-gray-600">
                    Workflow visualization will be implemented here
                  </div>
                  {/* TODO: Implement real workflow progress visualization */}
                  {project.status === 'processing' && (
                    <div className="flex items-center space-x-2 text-blue-600">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>AI agents are working on your presentation...</span>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Project Info */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Project Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium text-gray-500">Status</label>
                <div className="mt-1">
                  <Badge className={statusConfig[project.status].color}>
                    <StatusIcon className={`w-4 h-4 mr-1 ${project.status === 'processing' ? 'animate-spin' : ''}`} />
                    {statusConfig[project.status].label}
                  </Badge>
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">Created</label>
                <div className="mt-1 text-sm text-gray-900">
                  {new Date(project.created_at).toLocaleString()}
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">Last Updated</label>
                <div className="mt-1 text-sm text-gray-900">
                  {new Date(project.updated_at).toLocaleString()}
                </div>
              </div>
              {project.completed_at && (
                <div>
                  <label className="text-sm font-medium text-gray-500">Completed</label>
                  <div className="mt-1 text-sm text-gray-900">
                    {new Date(project.completed_at).toLocaleString()}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Actions */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {project.status === 'draft' && (
                <Button 
                  onClick={startProcessing}
                  disabled={isStarting}
                  className="w-full bg-blue-600 hover:bg-blue-700"
                >
                  {isStarting ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Starting...
                    </>
                  ) : (
                    <>
                      <PlayCircle className="w-4 h-4 mr-2" />
                      Start Processing
                    </>
                  )}
                </Button>
              )}
              <Button 
                variant="outline" 
                className="w-full"
                onClick={() => setShowEditModal(true)}
              >
                <Edit3 className="w-4 h-4 mr-2" />
                Edit Project
              </Button>
              <Button 
                variant="outline" 
                className="w-full"
                onClick={() => setShowDuplicateModal(true)}
              >
                <Copy className="w-4 h-4 mr-2" />
                Duplicate
              </Button>
              <Button 
                variant="outline" 
                className="w-full"
                onClick={() => setShowShareModal(true)}
              >
                <Share2 className="w-4 h-4 mr-2" />
                Share
              </Button>
              <Button variant="outline" className="w-full" disabled>
                Download Results
                <span className="ml-2 text-xs text-gray-400">(Coming Soon)</span>
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Modals */}
      <EditProjectModal
        open={showEditModal}
        onOpenChange={setShowEditModal}
        project={project}
        onProjectUpdated={handleProjectUpdated}
      />
      
      <DeleteProjectModal
        open={showDeleteModal}
        onOpenChange={setShowDeleteModal}
        project={project}
        onProjectDeleted={handleProjectDeleted}
      />
      
      <DuplicateProjectModal
        open={showDuplicateModal}
        onOpenChange={setShowDuplicateModal}
        project={project}
        onProjectDuplicated={handleProjectDuplicated}
      />
      
      <ShareProjectModal
        open={showShareModal}
        onOpenChange={setShowShareModal}
        project={project}
      />
    </div>
  )
}