'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useSupabaseAuth } from '@/hooks/useSupabaseAuthSimple'
import { NewProjectModal } from '@/components/modals/NewProjectModal'
import { FolderOpen, FileText, Clock, Plus, Loader2, CheckCircle2, XCircle, PlayCircle } from 'lucide-react'

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
    color: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300',
    icon: Clock 
  },
  processing: { 
    label: 'Processing', 
    color: 'bg-red-50 text-red-700 dark:bg-red-950/30 dark:text-red-400 border border-red-200 dark:border-red-800/30',
    icon: Loader2 
  },
  completed: { 
    label: 'Completed', 
    color: 'bg-red-50 text-red-700 dark:bg-red-950/30 dark:text-red-400 border border-red-200 dark:border-red-800/30',
    icon: CheckCircle2 
  },
  failed: { 
    label: 'Failed', 
    color: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300 border border-gray-200 dark:border-gray-700',
    icon: XCircle 
  }
}

export default function DashboardPage() {
  const { supabase, user, isAuthenticated, isLoading: authLoading } = useSupabaseAuth()
  const [projects, setProjects] = useState<Project[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showNewProjectModal, setShowNewProjectModal] = useState(false)

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      window.location.href = '/login?redirectTo=/dashboard'
      return
    }
  }, [authLoading, isAuthenticated])

  useEffect(() => {
    if (!user) return

    const fetchProjects = async () => {
      try {
        const { data, error } = await supabase
          .from('projects')
          .select('*')
          .eq('user_id', user.id)
          .order('updated_at', { ascending: false })
          .limit(10)

        if (error) {
          console.error('Error fetching projects:', error)
          return
        }

        setProjects(data || [])
      } catch (error) {
        console.error('Unexpected error:', error)
      } finally {
        setIsLoading(false)
      }
    }

    fetchProjects()
  }, [user, supabase])


  const recentProjects = projects.slice(0, 5)
  const activeWorkflows = projects.filter(p => p.status === 'processing')

  const getRelativeTime = (date: string) => {
    const now = new Date()
    const past = new Date(date)
    const diffInHours = Math.floor((now.getTime() - past.getTime()) / (1000 * 60 * 60))
    
    if (diffInHours < 1) return 'Just now'
    if (diffInHours < 24) return `${diffInHours} hours ago`
    const diffInDays = Math.floor(diffInHours / 24)
    if (diffInDays === 1) return '1 day ago'
    if (diffInDays < 7) return `${diffInDays} days ago`
    return past.toLocaleDateString()
  }
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-gray-50 dark:from-gray-900 dark:via-gray-900 dark:to-gray-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-12">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
          <div className="flex-1">
            <h1 className="text-4xl font-bold bg-gradient-to-r from-gray-900 via-red-700 to-gray-900 dark:from-white dark:via-red-400 dark:to-white bg-clip-text text-transparent">
              Dashboard
            </h1>
            <p className="text-lg text-gray-600 dark:text-gray-400 mt-3">
              Welcome back! Here&apos;s what&apos;s happening with your presentations.
            </p>
          </div>
          <div className="mt-4 sm:mt-0 sm:ml-4">
            <Button 
              onClick={() => setShowNewProjectModal(true)}
              className="bg-red-600 hover:bg-red-700 text-white shadow-lg hover:shadow-xl transition-all duration-300 px-6 py-3"
              size="lg"
            >
              <Plus className="w-5 h-5 mr-2" />
              New Project
            </Button>
          </div>
        </div>

        {/* Quick Actions */}
        <Card className="bg-gradient-to-r from-red-50 to-gray-50 dark:from-red-950/20 dark:to-gray-800 border-red-200 dark:border-red-800/30 shadow-lg">
          <CardHeader className="pb-4">
            <CardTitle className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <div className="p-1 rounded-md bg-red-100 dark:bg-red-900/30">
                <Plus className="w-4 h-4 text-red-600 dark:text-red-400" />
              </div>
              Quick Actions
            </CardTitle>
            <CardDescription className="text-gray-600 dark:text-gray-400 mt-2">
              Get started with your presentation workflow
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-3">
              <Button 
                onClick={() => setShowNewProjectModal(true)}
                variant="outline" 
                className="h-auto p-4 flex flex-col items-start gap-2 bg-white dark:bg-gray-800 hover:bg-red-50 dark:hover:bg-red-950/20 border-red-200 dark:border-red-800/30 group"
              >
                <div className="flex items-center gap-2 w-full">
                  <div className="p-1 rounded-md bg-red-100 dark:bg-red-900/30 group-hover:bg-red-200 dark:group-hover:bg-red-900/50 transition-colors">
                    <FileText className="w-4 h-4 text-red-600 dark:text-red-400" />
                  </div>
                  <span className="font-medium text-gray-900 dark:text-white">New Project</span>
                </div>
                <p className="text-xs text-gray-600 dark:text-gray-400 text-left">Create a presentation from scratch</p>
              </Button>
              
              <Link href="/projects">
                <Button 
                  variant="outline" 
                  className="h-auto p-4 flex flex-col items-start gap-2 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 w-full group"
                >
                  <div className="flex items-center gap-2 w-full">
                    <div className="p-1 rounded-md bg-gray-100 dark:bg-gray-700 group-hover:bg-gray-200 dark:group-hover:bg-gray-600 transition-colors">
                      <FolderOpen className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                    </div>
                    <span className="font-medium text-gray-900 dark:text-white">All Projects</span>
                  </div>
                  <p className="text-xs text-gray-600 dark:text-gray-400 text-left">Browse your presentations</p>
                </Button>
              </Link>
              
              <Link href="/workflow">
                <Button 
                  variant="outline" 
                  className="h-auto p-4 flex flex-col items-start gap-2 bg-white dark:bg-gray-800 hover:bg-blue-50 dark:hover:bg-blue-950/20 w-full group"
                >
                  <div className="flex items-center gap-2 w-full">
                    <div className="p-1 rounded-md bg-blue-100 dark:bg-blue-900/30 group-hover:bg-blue-200 dark:group-hover:bg-blue-900/50 transition-colors">
                      <PlayCircle className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                    </div>
                    <span className="font-medium text-gray-900 dark:text-white">Workflows</span>
                  </div>
                  <p className="text-xs text-gray-600 dark:text-gray-400 text-left">Monitor AI generation</p>
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <div className="grid gap-8 lg:grid-cols-2">
          <Card className="bg-white dark:bg-gray-800 border-0 shadow-lg">
            <CardHeader className="pb-6">
              <CardTitle className="flex items-center gap-2 text-lg font-semibold">
                <div className="p-1 rounded-md bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800/30">
                  <Clock className="h-4 w-4 text-red-600 dark:text-red-400" />
                </div>
                Recent Projects
              </CardTitle>
              <CardDescription className="mt-2">
                Your most recently created and modified projects
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {isLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <div className="text-center">
                      <Loader2 className="w-8 h-8 animate-spin text-red-600 dark:text-red-400 mx-auto mb-3" />
                      <p className="text-sm text-gray-600 dark:text-gray-400">Loading projects...</p>
                    </div>
                  </div>
                ) : recentProjects.length === 0 ? (
                  <div className="text-center py-12">
                    <div className="mx-auto w-20 h-20 bg-gradient-to-br from-red-50 to-gray-50 dark:from-red-950/20 dark:to-gray-800 rounded-2xl flex items-center justify-center mb-6 border border-red-100 dark:border-red-900/30">
                      <FileText className="w-8 h-8 text-red-600 dark:text-red-400" />
                    </div>
                    <h3 className="font-semibold text-gray-900 dark:text-white mb-2">No projects yet</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">Start by creating your first presentation project</p>
                    <Button 
                      onClick={() => setShowNewProjectModal(true)}
                      className="bg-red-600 hover:bg-red-700 text-white shadow-lg hover:shadow-xl transition-all duration-300"
                    >
                      <Plus className="w-4 h-4 mr-2" />
                      Create First Project
                    </Button>
                  </div>
                ) : (
                  recentProjects.map((project) => {
                    const StatusIcon = statusConfig[project.status].icon
                    return (
                      <Link key={project.id} href={`/projects/${project.id}`}>
                        <div className="group relative p-4 bg-gradient-to-r from-gray-50 to-white dark:from-gray-700 dark:to-gray-800 rounded-xl border border-gray-200 dark:border-gray-600 hover:border-red-200 dark:hover:border-red-700/50 hover:shadow-lg transition-all duration-300 cursor-pointer">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-3 flex-1 min-w-0">
                              <div className="w-12 h-12 bg-gradient-to-br from-red-100 to-red-50 dark:from-red-900/30 dark:to-red-800/30 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                                <FileText className="w-5 h-5 text-red-600 dark:text-red-400" />
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="font-semibold text-gray-900 dark:text-white truncate">
                                  {project.title}
                                </p>
                                <p className="text-sm text-gray-600 dark:text-gray-400">
                                  Modified {getRelativeTime(project.updated_at)}
                                </p>
                              </div>
                            </div>
                            <div className="flex items-center ml-4">
                              <Badge className={`${statusConfig[project.status].color} px-3 py-1`}>
                                <StatusIcon className={`w-3 h-3 mr-1.5 ${project.status === 'processing' ? 'animate-spin' : ''}`} />
                                {statusConfig[project.status].label}
                              </Badge>
                            </div>
                          </div>
                        </div>
                      </Link>
                    )
                  })
                )}
                
                {recentProjects.length > 0 && (
                  <div className="text-center pt-4">
                    <Link href="/projects">
                      <Button variant="outline" size="sm" className="hover:bg-red-50 dark:hover:bg-red-950/20 hover:border-red-300 dark:hover:border-red-700">
                        View All Projects
                      </Button>
                    </Link>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-white dark:bg-gray-800 border-0 shadow-lg">
            <CardHeader className="pb-6">
              <CardTitle className="flex items-center gap-2 text-lg font-semibold">
                <div className="p-1 rounded-md bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
                  <PlayCircle className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                </div>
                Active Workflows
              </CardTitle>
              <CardDescription className="mt-2">
                Currently running presentation generation workflows
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {isLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <div className="text-center">
                      <Loader2 className="w-8 h-8 animate-spin text-gray-600 dark:text-gray-400 mx-auto mb-3" />
                      <p className="text-sm text-gray-600 dark:text-gray-400">Loading workflows...</p>
                    </div>
                  </div>
                ) : activeWorkflows.length === 0 ? (
                  <div className="text-center py-12">
                    <div className="mx-auto w-20 h-20 bg-gradient-to-br from-gray-50 to-white dark:from-gray-800 dark:to-gray-700 rounded-2xl flex items-center justify-center mb-6 border border-gray-200 dark:border-gray-700">
                      <PlayCircle className="w-8 h-8 text-gray-600 dark:text-gray-400" />
                    </div>
                    <h3 className="font-semibold text-gray-900 dark:text-white mb-2">No active workflows</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Start a project to see AI workflows in action</p>
                  </div>
                ) : (
                  activeWorkflows.map((project) => (
                    <div key={project.id} className="relative p-4 bg-gradient-to-r from-red-50 to-white dark:from-red-950/20 dark:to-gray-800 rounded-xl border border-red-200 dark:border-red-800/50 shadow-sm hover:shadow-lg transition-all duration-300">
                      <div className="flex items-center justify-between mb-3">
                        <p className="font-semibold text-red-900 dark:text-red-100 truncate pr-4">
                          {project.title}
                        </p>
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                          <span className="text-sm font-medium text-red-600 dark:text-red-400 whitespace-nowrap">
                            Processing...
                          </span>
                        </div>
                      </div>
                      <div className="w-full bg-red-100 dark:bg-red-900/30 rounded-full h-2 mb-3 overflow-hidden">
                        <div className="bg-gradient-to-r from-red-500 to-red-600 h-2 rounded-full animate-pulse transition-all duration-1000" style={{ width: '45%' }}></div>
                      </div>
                      <div className="flex items-center justify-between">
                        <p className="text-sm text-red-700 dark:text-red-300 flex items-center gap-2">
                          <Loader2 className="w-3 h-3 animate-spin" />
                          AI agents are working on your presentation...
                        </p>
                        <Link href={`/projects/${project.id}`}>
                          <Button variant="ghost" size="sm" className="text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-950/30 px-3">
                            View Details
                          </Button>
                        </Link>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* New Project Modal */}
        <NewProjectModal 
          open={showNewProjectModal}
          onOpenChange={setShowNewProjectModal}
        />
      </div>
    </div>
  )
}