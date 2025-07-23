'use client'

import { useState, useEffect } from 'react'
import { useSupabaseAuth } from '@/hooks/useSupabaseAuthSimple'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { 
  FileText,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  AlertTriangle,
  Copy,
  Download,
  Search
} from 'lucide-react'
import { Input } from '@/components/ui/input'
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue 
} from '@/components/ui/select'
import { toast } from 'sonner'

interface WorkflowState {
  id: string
  project_id: string
  agent_name: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  input_data: any
  output_data: any
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  execution_time_seconds: number | null
  created_at: string
}

interface WorkflowLogViewerProps {
  projectId: string
  trigger?: React.ReactNode
}

const statusConfig = {
  pending: { 
    label: 'Pending', 
    color: 'bg-gray-100 text-gray-800',
    icon: Clock
  },
  in_progress: { 
    label: 'In Progress', 
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

export function WorkflowLogViewer({ projectId, trigger }: WorkflowLogViewerProps) {
  const { supabase, user } = useSupabaseAuth()
  const [workflowStates, setWorkflowStates] = useState<WorkflowState[]>([])
  const [filteredStates, setFilteredStates] = useState<WorkflowState[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (!open || !projectId || !user) return

    const fetchWorkflowStates = async () => {
      try {
        setIsLoading(true)
        const { data, error } = await supabase
          .from('workflow_states')
          .select('*')
          .eq('project_id', projectId)
          .order('created_at', { ascending: true })

        if (error) {
          console.error('Error fetching workflow states:', error)
          toast.error('Failed to load workflow logs')
          return
        }

        setWorkflowStates(data || [])
      } catch (error) {
        console.error('Unexpected error:', error)
        toast.error('An unexpected error occurred')
      } finally {
        setIsLoading(false)
      }
    }

    fetchWorkflowStates()
  }, [open, projectId, user, supabase])

  useEffect(() => {
    let filtered = workflowStates

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(state => 
        state.agent_name.toLowerCase().includes(query) ||
        state.error_message?.toLowerCase().includes(query) ||
        JSON.stringify(state.input_data).toLowerCase().includes(query) ||
        JSON.stringify(state.output_data).toLowerCase().includes(query)
      )
    }

    // Apply status filter
    if (statusFilter !== 'all') {
      filtered = filtered.filter(state => state.status === statusFilter)
    }

    setFilteredStates(filtered)
  }, [workflowStates, searchQuery, statusFilter])

  const copyToClipboard = async (content: string, label: string) => {
    try {
      await navigator.clipboard.writeText(content)
      toast.success(`${label} copied to clipboard`)
    } catch (error) {
      console.error('Failed to copy:', error)
      toast.error('Failed to copy to clipboard')
    }
  }

  const exportLogs = () => {
    const logData = filteredStates.map(state => ({
      agent: state.agent_name,
      status: state.status,
      started: state.started_at,
      completed: state.completed_at,
      duration: state.execution_time_seconds,
      error: state.error_message,
      input: state.input_data,
      output: state.output_data
    }))

    const blob = new Blob([JSON.stringify(logData, null, 2)], { 
      type: 'application/json' 
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `workflow-logs-${projectId}-${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    
    toast.success('Workflow logs exported successfully')
  }

  const formatTimestamp = (timestamp: string | null) => {
    if (!timestamp) return 'N/A'
    return new Date(timestamp).toLocaleString()
  }

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return 'N/A'
    if (seconds < 60) return `${seconds}s`
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}m ${remainingSeconds}s`
  }

  const defaultTrigger = (
    <Button variant="outline" size="sm">
      <FileText className="w-4 h-4 mr-2" />
      View Logs
    </Button>
  )

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || defaultTrigger}
      </DialogTrigger>
      <DialogContent className="max-w-4xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5" />
            Workflow Logs & Debug Information
          </DialogTitle>
          <DialogDescription>
            Detailed execution logs for all workflow stages and AI agents
          </DialogDescription>
        </DialogHeader>
        
        {/* Filters */}
        <div className="flex gap-4 items-center">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <Input
                placeholder="Search logs..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>
          
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="in_progress">In Progress</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
            </SelectContent>
          </Select>

          <Button 
            variant="outline" 
            size="sm"
            onClick={exportLogs}
            disabled={filteredStates.length === 0}
          >
            <Download className="w-4 h-4 mr-2" />
            Export
          </Button>
        </div>

        {/* Content */}
        <ScrollArea className="flex-1 min-h-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="flex items-center space-x-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Loading workflow logs...</span>
              </div>
            </div>
          ) : filteredStates.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <FileText className="w-12 h-12 mx-auto mb-3 text-gray-300" />
              <p>No workflow logs found</p>
              {workflowStates.length === 0 ? (
                <p className="text-sm mt-2">The workflow hasn&apos;t started yet</p>
              ) : (
                <p className="text-sm mt-2">Try adjusting your search or filter</p>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              {filteredStates.map((state, index) => {
                const StatusIcon = statusConfig[state.status].icon
                
                return (
                  <Card key={state.id} className={`
                    ${state.status === 'failed' ? 'border-red-200 bg-red-50' : ''}
                    ${state.status === 'in_progress' ? 'border-blue-200 bg-blue-50' : ''}
                    ${state.status === 'completed' ? 'border-green-200 bg-green-50' : ''}
                  `}>
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                          <div className="flex items-center space-x-2">
                            <span className="text-sm font-mono text-gray-500">
                              #{index + 1}
                            </span>
                            <StatusIcon className={`w-4 h-4 ${
                              state.status === 'in_progress' ? 'animate-spin text-blue-600' :
                              state.status === 'completed' ? 'text-green-600' :
                              state.status === 'failed' ? 'text-red-600' :
                              'text-gray-400'
                            }`} />
                          </div>
                          <CardTitle className="text-lg">
                            {state.agent_name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                          </CardTitle>
                        </div>
                        <Badge className={statusConfig[state.status].color}>
                          {statusConfig[state.status].label}
                        </Badge>
                      </div>
                      
                      <div className="grid grid-cols-3 gap-4 text-sm text-gray-600">
                        <div>
                          <span className="font-medium">Started:</span>
                          <br />
                          {formatTimestamp(state.started_at)}
                        </div>
                        <div>
                          <span className="font-medium">Completed:</span>
                          <br />
                          {formatTimestamp(state.completed_at)}
                        </div>
                        <div>
                          <span className="font-medium">Duration:</span>
                          <br />
                          {formatDuration(state.execution_time_seconds)}
                        </div>
                      </div>
                    </CardHeader>
                    
                    <CardContent className="space-y-4">
                      {/* Error Message */}
                      {state.error_message && (
                        <div className="p-3 bg-red-100 border border-red-200 rounded-lg">
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center space-x-2">
                              <AlertTriangle className="w-4 h-4 text-red-600" />
                              <span className="font-medium text-red-900">Error Message</span>
                            </div>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => copyToClipboard(state.error_message || '', 'Error message')}
                            >
                              <Copy className="w-3 h-3" />
                            </Button>
                          </div>
                          <pre className="text-sm text-red-800 whitespace-pre-wrap font-mono">
                            {state.error_message}
                          </pre>
                        </div>
                      )}

                      {/* Input Data */}
                      {state.input_data && Object.keys(state.input_data).length > 0 && (
                        <div>
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-medium text-gray-700">Input Data</span>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => copyToClipboard(JSON.stringify(state.input_data, null, 2), 'Input data')}
                            >
                              <Copy className="w-3 h-3" />
                            </Button>
                          </div>
                          <pre className="bg-gray-100 p-3 rounded text-xs font-mono overflow-auto max-h-32">
                            {JSON.stringify(state.input_data, null, 2)}
                          </pre>
                        </div>
                      )}

                      {/* Output Data */}
                      {state.output_data && Object.keys(state.output_data).length > 0 && (
                        <div>
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-medium text-gray-700">Output Data</span>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => copyToClipboard(JSON.stringify(state.output_data, null, 2), 'Output data')}
                            >
                              <Copy className="w-3 h-3" />
                            </Button>
                          </div>
                          <pre className="bg-gray-100 p-3 rounded text-xs font-mono overflow-auto max-h-32">
                            {JSON.stringify(state.output_data, null, 2)}
                          </pre>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          )}
        </ScrollArea>
      </DialogContent>
    </Dialog>
  )
}