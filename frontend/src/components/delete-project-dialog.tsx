"use client"

import { useState } from "react"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Loader2, Trash2, AlertTriangle } from "lucide-react"
import { toast } from "sonner"

interface DeleteProjectDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  project: {
    id: string
    title: string
  } | null
  onDelete: (projectId: string) => Promise<void>
}

export function DeleteProjectDialog({
  open,
  onOpenChange,
  project,
  onDelete,
}: DeleteProjectDialogProps) {
  const [confirmText, setConfirmText] = useState("")
  const [isDeleting, setIsDeleting] = useState(false)

  const expectedText = "DELETE"
  const isConfirmValid = confirmText === expectedText

  const handleDelete = async () => {
    if (!project || !isConfirmValid) return

    setIsDeleting(true)
    try {
      await onDelete(project.id)
      toast.success("Project deleted successfully")
      onOpenChange(false)
      setConfirmText("")
    } catch (error) {
      console.error("Failed to delete project:", error)
      toast.error("Failed to delete project. Please try again.")
    } finally {
      setIsDeleting(false)
    }
  }

  const handleOpenChange = (newOpen: boolean) => {
    if (!isDeleting) {
      onOpenChange(newOpen)
      if (!newOpen) {
        setConfirmText("")
      }
    }
  }

  if (!project) return null

  return (
    <AlertDialog open={open} onOpenChange={handleOpenChange}>
      <AlertDialogContent className="max-w-md">
        <AlertDialogHeader>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/20">
              <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />
            </div>
            <div>
              <AlertDialogTitle className="text-left">Delete Project</AlertDialogTitle>
            </div>
          </div>
          <AlertDialogDescription className="text-left space-y-3">
            <p>
              Are you sure you want to delete <strong>"{project.title}"</strong>?
            </p>
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 dark:border-red-800 dark:bg-red-900/20">
              <div className="flex items-start gap-2">
                <Trash2 className="h-4 w-4 text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0" />
                <div className="text-sm text-red-700 dark:text-red-300">
                  <p className="font-medium mb-1">This action cannot be undone.</p>
                  <p>This will permanently delete:</p>
                  <ul className="list-disc list-inside mt-1 space-y-0.5">
                    <li>The project and all its data</li>
                    <li>All generated slides and content</li>
                    <li>All uploaded files and images</li>
                    <li>All workflow history</li>
                  </ul>
                </div>
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirm-text" className="text-sm font-medium">
                To confirm, type <code className="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 font-mono text-xs">DELETE</code> below:
              </Label>
              <Input
                id="confirm-text"
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                placeholder="Type DELETE to confirm"
                className="font-mono"
                disabled={isDeleting}
              />
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isDeleting}>
            Cancel
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={handleDelete}
            disabled={!isConfirmValid || isDeleting}
            className="bg-red-600 hover:bg-red-700 focus:ring-red-600"
          >
            {isDeleting ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Deleting...
              </>
            ) : (
              <>
                <Trash2 className="w-4 h-4 mr-2" />
                Delete Project
              </>
            )}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}