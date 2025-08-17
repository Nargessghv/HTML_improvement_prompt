'use client'

import { useState } from 'react'
import { toast } from 'sonner'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { AlertTriangle, Loader2, Trash2 } from 'lucide-react'

interface Project {
  id: string
  title: string
  topic: string
  status: 'draft' | 'processing' | 'completed' | 'failed'
  created_at: string
  updated_at: string
  completed_at: string | null
}

interface DeleteProjectModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  project: Project | null
  onProjectDeleted: () => void
}

export function DeleteProjectModal({ 
  open, 
  onOpenChange, 
  project,
  onProjectDeleted
}: DeleteProjectModalProps) {
  const [confirmationText, setConfirmationText] = useState('')
  const [isDeleting, setIsDeleting] = useState(false)

  const expectedText = 'DELETE'
  const isConfirmed = confirmationText === expectedText

  const handleDelete = async () => {
    if (!project || !isConfirmed) return

    setIsDeleting(true)
    try {
      const response = await fetch(`/api/projects/${project.id}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Failed to delete project' }))
        console.error('Project deletion error:', errorData)
        toast.error(errorData.error || 'Failed to delete project')
        return
      }

      const result = await response.json()
      
      // Show success message with details
      const successMessage = result.files_deleted 
        ? `Project deleted successfully. ${result.files_deleted} files removed from storage.`
        : 'Project deleted successfully.'
      
      toast.success(successMessage)
      
      // Show warnings if any
      if (result.storage_warnings && result.storage_warnings.length > 0) {
        toast.warning('Some storage files could not be deleted. Project data has been removed.')
      }

      onProjectDeleted()
      handleClose()
    } catch (error) {
      console.error('Unexpected error:', error)
      toast.error('An unexpected error occurred')
    } finally {
      setIsDeleting(false)
    }
  }

  const handleClose = () => {
    if (!isDeleting) {
      onOpenChange(false)
      setConfirmationText('')
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-red-600">
            <AlertTriangle className="w-5 h-5" />
            Delete Project
          </DialogTitle>
          <DialogDescription>
            This action cannot be undone. This will permanently delete the project
            and all associated data including workflow states, slides, and files.
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <h4 className="font-medium text-red-900 mb-2">
              Project to be deleted:
            </h4>
            <p className="text-sm text-red-700 font-medium">
              {project?.title}
            </p>
            <p className="text-sm text-red-600 mt-1">
              Status: {project?.status}
            </p>
          </div>

          <div className="rounded-lg border border-red-200 bg-red-50 p-3">
            <div className="flex items-start gap-2">
              <Trash2 className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
              <div className="text-sm text-red-700">
                <p className="font-medium mb-1">This action will permanently delete:</p>
                <ul className="list-disc list-inside space-y-0.5">
                  <li>The project and all its data</li>
                  <li>All generated slides and content</li>
                  <li>All uploaded files and images from storage</li>
                  <li>All workflow history</li>
                </ul>
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirmation">
              Type <span className="font-mono bg-gray-100 px-1 rounded text-xs">
                {expectedText}
              </span> to confirm deletion:
            </Label>
            <Input
              id="confirmation"
              value={confirmationText}
              onChange={(e) => setConfirmationText(e.target.value)}
              placeholder="Type DELETE to confirm"
              className="font-mono"
              disabled={isDeleting}
            />
          </div>
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={handleClose}
            disabled={isDeleting}
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="destructive"
            onClick={handleDelete}
            disabled={!isConfirmed || isDeleting}
          >
            {isDeleting ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Deleting...
              </>
            ) : (
              <>
                <AlertTriangle className="w-4 h-4 mr-2" />
                Delete Project
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}