'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useSupabaseAuth } from '@/hooks/useSupabaseAuthSimple'
import { NewProjectModal } from '@/components/modals/NewProjectModal'
import { FolderOpen, PlayCircle, FileText, TrendingUp, Clock, Plus, Eye, Loader2, CheckCircle2, XCircle } from 'lucide-react'

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
    color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
    icon: Loader2 
  },
  completed: { 
    label: 'Completed', 
    color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
    icon: CheckCircle2 
  },
  failed: { 
    label: 'Failed', 
    color: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
    icon: XCircle 
  }
}

export default function DashboardPage() {
  const { supabase, user } = useSupabaseAuth()
  const [projects, setProjects] = useState<Project[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showNewProjectModal, setShowNewProjectModal] = useState(false)

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

  // Calculate stats
  const stats = {
    total: projects.length,
    active: projects.filter(p => p.status === 'processing').length,
    completed: projects.filter(p => p.status === 'completed').length,
    successRate: projects.length > 0 ? Math.round((projects.filter(p => p.status === 'completed').length / projects.length) * 100) : 0
  }

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
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white">
          Dashboard
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mt-2">
          Welcome back! Here&apos;s what&apos;s happening with your presentations.
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Projects</CardTitle>
            <FolderOpen className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total}</div>
            <p className="text-xs text-muted-foreground">
              {stats.total === 0 ? 'Create your first project' : `${stats.completed} completed`}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Workflows</CardTitle>
            <PlayCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.active}</div>
            <p className="text-xs text-muted-foreground">
              {stats.active === 0 ? 'No active workflows' : 'Currently processing'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Completed</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.completed}</div>
            <p className="text-xs text-muted-foreground">
              {stats.completed === 0 ? 'No completed projects' : 'Successfully generated'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.successRate}%</div>
            <p className="text-xs text-muted-foreground">
              {stats.total === 0 ? 'No data yet' : 'Overall success rate'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              Recent Projects
            </CardTitle>
            <CardDescription>
              Your most recently created and modified projects
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {isLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
                </div>
              ) : recentProjects.length === 0 ? (
                <div className="text-center py-8">
                  <div className="mx-auto w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mb-4">
                    <Plus className="w-6 h-6 text-gray-400" />
                  </div>
                  <p className="text-gray-500 dark:text-gray-400 mb-4">No projects yet</p>
                  <Button 
                    onClick={() => setShowNewProjectModal(true)}
                    size="sm"
                    className="bg-blue-600 hover:bg-blue-700"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Create First Project
                  </Button>
                </div>
              ) : (
                recentProjects.map((project) => {
                  const StatusIcon = statusConfig[project.status].icon
                  return (
                    <div key={project.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                      <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900 rounded-lg flex items-center justify-center">
                          <FileText className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                        </div>
                        <div>
                          <p className="font-medium text-gray-900 dark:text-white">
                            {project.title}
                          </p>
                          <p className="text-sm text-gray-500 dark:text-gray-400">
                            Modified {getRelativeTime(project.updated_at)}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Badge className={statusConfig[project.status].color}>
                          <StatusIcon className={`w-3 h-3 mr-1 ${project.status === 'processing' ? 'animate-spin' : ''}`} />
                          {statusConfig[project.status].label}
                        </Badge>
                        <Link href={`/projects/${project.id}`}>
                          <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                            <Eye className="w-4 h-4" />
                          </Button>
                        </Link>
                      </div>
                    </div>
                  )
                })
              )}
              
              {recentProjects.length > 0 && (
                <div className="text-center pt-2">
                  <Link href="/projects">
                    <Button variant="outline" size="sm">
                      View All Projects
                    </Button>
                  </Link>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <PlayCircle className="h-5 w-5" />
              Active Workflows
            </CardTitle>
            <CardDescription>
              Currently running presentation generation workflows
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {isLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
                </div>
              ) : activeWorkflows.length === 0 ? (
                <div className="text-center py-8">
                  <div className="mx-auto w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mb-4">
                    <PlayCircle className="w-6 h-6 text-gray-400" />
                  </div>
                  <p className="text-gray-500 dark:text-gray-400 text-sm">
                    No active workflows
                  </p>
                  <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                    Start a project to see workflows here
                  </p>
                </div>
              ) : (
                activeWorkflows.map((project) => (
                  <div key={project.id} className="p-3 bg-blue-50 dark:bg-blue-950 rounded-lg border border-blue-200 dark:border-blue-800">
                    <div className="flex items-center justify-between mb-2">
                      <p className="font-medium text-blue-900 dark:text-blue-100">
                        {project.title}
                      </p>
                      <span className="text-sm text-blue-600 dark:text-blue-400">
                        Processing...
                      </span>
                    </div>
                    <div className="w-full bg-blue-200 dark:bg-blue-800 rounded-full h-2">
                      <div className="bg-blue-600 h-2 rounded-full animate-pulse" style={{ width: '45%' }}></div>
                    </div>
                    <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
                      AI agents are working on your presentation...
                    </p>
                    <div className="flex justify-end mt-2">
                      <Link href={`/projects/${project.id}`}>
                        <Button variant="ghost" size="sm" className="text-blue-600 dark:text-blue-400">
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
  )
}