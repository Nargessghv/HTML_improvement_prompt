'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { useSupabaseAuth } from '@/hooks/useSupabaseAuthSimple'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { 
  EditProjectModal,
  DeleteProjectModal,
  DuplicateProjectModal,
  ShareProjectModal
} from '@/components/modals'
import { WorkflowProgress } from '@/components/workflow/WorkflowProgress'
import { SlidesGrid } from '@/components/slides/SlidesGrid'
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
  MoreHorizontal,
  Download,
  FileText,
  Image,
  RefreshCw,
  Sparkles
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

interface ProjectFile {
  id: string
  file_name: string
  file_type: string
  file_size?: number
  created_at: string
  download_url: string
}

const statusConfig = {
  draft: { 
    label: 'Draft', 
    color: 'bg-neutral-100 text-neutral-800 dark:bg-neutral-800 dark:text-neutral-200',
    icon: Clock 
  },
  processing: { 
    label: 'Processing', 
    color: 'bg-primary/10 text-primary dark:bg-primary/20 dark:text-primary',
    icon: Loader2 
  },
  completed: { 
    label: 'Completed', 
    color: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200',
    icon: CheckCircle2 
  },
  failed: { 
    label: 'Failed', 
    color: 'bg-destructive/10 text-destructive dark:bg-destructive/20 dark:text-destructive',
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
  const [projectFiles, setProjectFiles] = useState<ProjectFile[]>([])
  const [isLoadingFiles, setIsLoadingFiles] = useState(false)

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

  // Fetch project files when project is loaded and completed
  useEffect(() => {
    if (!projectId || !user || !project) return
    if (project.status !== 'completed') return

    fetchProjectFiles()
  }, [projectId, user, supabase, project]) // eslint-disable-line react-hooks/exhaustive-deps

  const fetchProjectFiles = async () => {
    if (!projectId || !user) return

    setIsLoadingFiles(true)
    try {
      // Get the session to access the JWT token
      const { data: { session } } = await supabase.auth.getSession()
      if (!session?.access_token) {
        console.warn('No valid session found')
        return
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/projects/${projectId}/files`, {
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch files: ${response.status}`)
      }

      const files: ProjectFile[] = await response.json()
      setProjectFiles(files)
    } catch (error) {
      console.error('Error fetching project files:', error)
      toast.error('Failed to load project files')
    } finally {
      setIsLoadingFiles(false)
    }
  }

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

      // Call backend API to start the AI workflow
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        
        // Get the current session to access the JWT token
        const { data: { session } } = await supabase.auth.getSession()
        if (!session?.access_token) {
          throw new Error('No valid session found')
        }
        
        const response = await fetch(`${apiUrl}/projects`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${session.access_token}` // Pass the session's JWT token
          },
          body: JSON.stringify({
            title: project.title,
            topic: project.topic,
            project_id: project.id // Pass existing project ID so backend can update it
          })
        })

        if (!response.ok) {
          throw new Error(`Backend API error: ${response.status}`)
        }

        await response.json()
        toast.success('AI workflow has been initiated!')
        
      } catch (backendError) {
        console.error('Failed to start backend workflow:', backendError)
        toast.error('Started locally but could not connect to AI backend. Ensure the Python API server is running.')
        
        // Don't fail the whole process - the frontend workflow tracking will still work
      }

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

  const downloadFile = async (file: ProjectFile) => {
    try {
      // Use the signed download URL directly
      const link = document.createElement('a')
      link.href = file.download_url
      link.download = file.file_name
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      toast.success(`Downloaded ${file.file_name}`)
    } catch (error) {
      console.error('Error downloading file:', error)
      toast.error(`Failed to download ${file.file_name}`)
    }
  }

  const getFileIcon = (fileType: string) => {
    switch (fileType) {
      case 'pptx':
        return FileText
      case 'pdf':
        return FileText
      case 'images':
      case 'slide_images':
        return Image
      default:
        return FileText
    }
  }

  const getDisplayName = (file: ProjectFile) => {
    switch (file.file_type) {
      case 'pptx':
        return 'PowerPoint Presentation'
      case 'pdf':
        return 'PDF Document'
      case 'images':
        return 'Slide Images'
      case 'slide_images':
        return 'Individual Slide Images'
      default:
        return file.file_type.toUpperCase() + ' File'
    }
  }

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'Unknown size'
    
    const units = ['B', 'KB', 'MB', 'GB']
    let size = bytes
    let unitIndex = 0
    
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024
      unitIndex++
    }
    
    return `${size.toFixed(1)} ${units[unitIndex]}`
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
            <div className="flex gap-3">
              <Button 
                onClick={() => router.push(`/projects/${projectId}/interactive`)}
                variant="outline"
                className="border-primary text-primary hover:bg-primary/10"
              >
                <Sparkles className="w-4 h-4 mr-2" />
                Interactive Planning
              </Button>
              <Button 
                onClick={startProcessing}
                disabled={isStarting}
                className="bg-primary hover:bg-primary/90 text-primary-foreground"
              >
                {isStarting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Starting...
                  </>
                ) : (
                  <>
                    <PlayCircle className="w-4 h-4 mr-2" />
                    Quick Generate
                  </>
                )}
              </Button>
            </div>
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
            <CardContent className="p-0">
              <ScrollArea className="h-[400px] w-full">
                <div className="p-6">
                  <div className="prose prose-sm max-w-none">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        h1: ({ children }) => <h1 className="text-lg font-bold text-gray-900 mb-3 mt-0">{children}</h1>,
                        h2: ({ children }) => <h2 className="text-base font-semibold text-gray-800 mb-2 mt-4">{children}</h2>,
                        h3: ({ children }) => <h3 className="text-sm font-semibold text-gray-800 mb-2 mt-3">{children}</h3>,
                        h4: ({ children }) => <h4 className="text-sm font-medium text-gray-700 mb-1 mt-2">{children}</h4>,
                        p: ({ children }) => <p className="text-gray-700 mb-2 leading-relaxed">{children}</p>,
                        ul: ({ children }) => <ul className="list-disc list-inside text-gray-700 mb-2 ml-2">{children}</ul>,
                        ol: ({ children }) => <ol className="list-decimal list-inside text-gray-700 mb-2 ml-2">{children}</ol>,
                        li: ({ children }) => <li className="mb-1">{children}</li>,
                        strong: ({ children }) => <strong className="font-semibold text-gray-900">{children}</strong>,
                        em: ({ children }) => <em className="italic text-gray-800">{children}</em>,
                        code: ({ children }) => <code className="bg-gray-100 px-1 py-0.5 rounded text-sm font-mono text-gray-800">{children}</code>,
                        pre: ({ children }) => <pre className="bg-gray-100 p-3 rounded-md overflow-x-auto text-sm font-mono mb-3">{children}</pre>,
                        blockquote: ({ children }) => <blockquote className="border-l-4 border-gray-300 pl-4 italic text-gray-600 mb-3">{children}</blockquote>,
                        hr: () => <hr className="border-gray-300 my-4" />,
                        a: ({ href, children }) => <a href={href} className="text-blue-600 hover:text-blue-800 underline" target="_blank" rel="noopener noreferrer">{children}</a>,
                      }}
                    >
                      {project.topic}
                    </ReactMarkdown>
                  </div>
                </div>
              </ScrollArea>
            </CardContent>
          </Card>

          {/* Workflow Progress */}
          <div className="mt-6">
            <WorkflowProgress project={project} />
          </div>

          {/* Individual Slides Grid */}
          <div className="mt-6">
            <SlidesGrid 
              projectId={project.id}
              projectStatus={project.status}
              isParallelProcessing={process.env.NEXT_PUBLIC_USE_PARALLEL_SLIDE_PROCESSING === 'true'}
              expectedSlideCount={0} // This could be determined from the approved outline
            />
          </div>

{/* HTML Refinement Viewer - Now accessed via modal button in WorkflowProgress */}

          {/* Download Section for Completed Projects */}
          {project.status === 'completed' && (
            <div className="mt-6">
              <Card>
                <CardHeader>
                  <CardTitle>Download Results</CardTitle>
                  <CardDescription>
                    Download your generated presentation files
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {isLoadingFiles ? (
                    <div className="flex items-center justify-center py-4">
                      <Loader2 className="w-6 h-6 animate-spin mr-2" />
                      <span>Loading available files...</span>
                    </div>
                  ) : projectFiles.length > 0 ? (
                    <div className="space-y-3">
                      {projectFiles.map((file) => {
                        const FileIcon = getFileIcon(file.file_type)
                        return (
                          <div key={file.id} className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50">
                            <div className="flex items-center space-x-3">
                              <FileIcon className="w-5 h-5 text-gray-500" />
                              <div>
                                <p className="font-medium">{getDisplayName(file)}</p>
                                <p className="text-sm text-gray-500">
                                  {formatFileSize(file.file_size)} • Created {new Date(file.created_at).toLocaleDateString()}
                                </p>
                              </div>
                            </div>
                            <Button 
                              variant="outline" 
                              size="sm"
                              onClick={() => downloadFile(file)}
                            >
                              <Download className="w-4 h-4 mr-2" />
                              Download
                            </Button>
                          </div>
                        )
                      })}
                      <div className="pt-3 border-t">
                        <Button 
                          variant="outline" 
                          onClick={fetchProjectFiles}
                          disabled={isLoadingFiles}
                        >
                          {isLoadingFiles ? (
                            <>
                              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                              Refreshing...
                            </>
                          ) : (
                            <>
                              <RefreshCw className="w-4 h-4 mr-2" />
                              Refresh Files
                            </>
                          )}
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <Download className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                      <p className="text-gray-500 mb-3">No files available for download yet</p>
                      <Button 
                        variant="outline"
                        onClick={fetchProjectFiles}
                        disabled={isLoadingFiles}
                      >
                        {isLoadingFiles ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            Checking...
                          </>
                        ) : (
                          <>
                            <RefreshCw className="w-4 h-4 mr-2" />
                            Check for Files
                          </>
                        )}
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          )}
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
                  className="w-full bg-primary hover:bg-primary/90 text-primary-foreground"
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
              {project.status === 'completed' && projectFiles.length > 0 ? (
                <div className="space-y-2">
                  <p className="text-sm font-medium text-gray-700">Download Files:</p>
                  {projectFiles.map((file) => {
                    const FileIcon = getFileIcon(file.file_type)
                    return (
                      <Button 
                        key={file.id}
                        variant="outline" 
                        className="w-full justify-start"
                        onClick={() => downloadFile(file)}
                      >
                        <FileIcon className="w-4 h-4 mr-2" />
                        <div className="flex-1 text-left">
                          <div className="text-sm font-medium">{getDisplayName(file)}</div>
                          <div className="text-xs text-gray-500">{formatFileSize(file.file_size)}</div>
                        </div>
                        <Download className="w-4 h-4 ml-2" />
                      </Button>
                    )
                  })}
                  <Button 
                    variant="outline" 
                    size="sm" 
                    className="w-full"
                    onClick={fetchProjectFiles}
                    disabled={isLoadingFiles}
                  >
                    {isLoadingFiles ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Refreshing...
                      </>
                    ) : (
                      <>
                        <RefreshCw className="w-4 h-4 mr-2" />
                        Refresh Files
                      </>
                    )}
                  </Button>
                </div>
              ) : project.status === 'completed' ? (
                <Button 
                  variant="outline" 
                  className="w-full"
                  onClick={fetchProjectFiles}
                  disabled={isLoadingFiles}
                >
                  {isLoadingFiles ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Loading Files...
                    </>
                  ) : (
                    <>
                      <Download className="w-4 h-4 mr-2" />
                      Check for Downloads
                    </>
                  )}
                </Button>
              ) : (
                <Button variant="outline" className="w-full" disabled>
                  <Download className="w-4 h-4 mr-2" />
                  Download Results
                  <span className="ml-2 text-xs text-gray-400">(Available after completion)</span>
                </Button>
              )}
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