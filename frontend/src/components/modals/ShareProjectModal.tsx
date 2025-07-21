'use client'

import { useState } from 'react'
import { toast } from 'sonner'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { 
  Share2, 
  Copy, 
  Check,
  ExternalLink,
  Lock,
  Globe
} from 'lucide-react'

interface Project {
  id: string
  title: string
  topic: string
  status: 'draft' | 'processing' | 'completed' | 'failed'
  created_at: string
  updated_at: string
  completed_at: string | null
}

interface ShareProjectModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  project: Project | null
}

export function ShareProjectModal({ 
  open, 
  onOpenChange, 
  project
}: ShareProjectModalProps) {
  const [copied, setCopied] = useState(false)
  
  const projectUrl = project ? `${window.location.origin}/projects/${project.id}` : ''

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(projectUrl)
      setCopied(true)
      toast.success('Project URL copied to clipboard!')
      
      setTimeout(() => setCopied(false), 2000)
    } catch (error) {
      console.error('Failed to copy:', error)
      toast.error('Failed to copy URL')
    }
  }

  const openInNewTab = () => {
    if (projectUrl) {
      window.open(projectUrl, '_blank')
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Share2 className="w-5 h-5" />
            Share Project
          </DialogTitle>
          <DialogDescription>
            Share this project with others. They will need access to view it.
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="font-medium text-blue-900 mb-2">
              {project?.title}
            </h4>
            <div className="flex items-center gap-2 mb-2">
              <Badge 
                variant={project?.status === 'completed' ? 'default' : 'secondary'}
                className="text-xs"
              >
                {project?.status}
              </Badge>
            </div>
            <p className="text-sm text-blue-600">
              Created on {project ? new Date(project.created_at).toLocaleDateString() : ''}
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="project-url">Project URL</Label>
            <div className="flex gap-2">
              <Input
                id="project-url"
                value={projectUrl}
                readOnly
                className="font-mono text-sm"
              />
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={copyToClipboard}
                className="shrink-0"
              >
                {copied ? (
                  <Check className="w-4 h-4" />
                ) : (
                  <Copy className="w-4 h-4" />
                )}
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={openInNewTab}
                className="shrink-0"
              >
                <ExternalLink className="w-4 h-4" />
              </Button>
            </div>
          </div>

          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Lock className="w-4 h-4 text-amber-600" />
              <h4 className="font-medium text-amber-900">
                Privacy Notice
              </h4>
            </div>
            <p className="text-sm text-amber-700">
              This project is private and can only be accessed by you. 
              Public sharing and collaboration features will be available in a future update.
            </p>
          </div>

          <div className="space-y-3">
            <h4 className="font-medium text-gray-900">Share Options</h4>
            
            <div className="space-y-2">
              <Button
                variant="outline"
                className="w-full justify-start"
                disabled
              >
                <Globe className="w-4 h-4 mr-2" />
                Make Public
                <Badge variant="secondary" className="ml-auto text-xs">
                  Coming Soon
                </Badge>
              </Button>
              
              <Button
                variant="outline"
                className="w-full justify-start"
                disabled
              >
                <Share2 className="w-4 h-4 mr-2" />
                Invite Collaborators
                <Badge variant="secondary" className="ml-auto text-xs">
                  Coming Soon
                </Badge>
              </Button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}