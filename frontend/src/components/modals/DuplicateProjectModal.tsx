'use client'

import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { useSupabaseAuth } from '@/hooks/useSupabaseAuthSimple'
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
import { Textarea } from '@/components/ui/textarea'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Label } from '@/components/ui/label'
import { Copy, Loader2 } from 'lucide-react'

const duplicateProjectSchema = z.object({
  title: z
    .string()
    .min(1, 'Project title is required')
    .max(100, 'Title must be less than 100 characters'),
  topic: z
    .string()
    .min(10, 'Topic must be at least 10 characters'),
})

type DuplicateProjectFormData = z.infer<typeof duplicateProjectSchema>

interface Project {
  id: string
  title: string
  topic: string
  status: 'draft' | 'processing' | 'completed' | 'failed'
  created_at: string
  updated_at: string
  completed_at: string | null
}

interface DuplicateProjectModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  project: Project | null
  onProjectDuplicated: (newProject: Project) => void
}

export function DuplicateProjectModal({ 
  open, 
  onOpenChange, 
  project,
  onProjectDuplicated
}: DuplicateProjectModalProps) {
  const { supabase, user } = useSupabaseAuth()

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting }
  } = useForm<DuplicateProjectFormData>({
    resolver: zodResolver(duplicateProjectSchema),
    defaultValues: {
      title: project ? `${project.title} (Copy)` : '',
      topic: project?.topic || ''
    }
  })

  const onSubmit = async (data: DuplicateProjectFormData) => {
    if (!project || !user) return

    try {
      const { data: newProject, error } = await supabase
        .from('projects')
        .insert({
          user_id: user.id,
          title: data.title,
          topic: data.topic,
          status: 'draft' // Always create duplicates as drafts
        })
        .select()
        .single()

      if (error) {
        console.error('Project duplication error:', error)
        toast.error(error.message || 'Failed to duplicate project')
        return
      }

      toast.success('Project duplicated successfully!')
      onProjectDuplicated(newProject)
      onOpenChange(false)
      reset()
    } catch (error) {
      console.error('Unexpected error:', error)
      toast.error('An unexpected error occurred')
    }
  }

  const handleClose = () => {
    if (!isSubmitting) {
      onOpenChange(false)
      reset()
    }
  }

  // Update default values when project changes
  useEffect(() => {
    if (project && open) {
      reset({
        title: `${project.title} (Copy)`,
        topic: project.topic
      })
    }
  }, [project, open, reset])

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Copy className="w-5 h-5" />
            Duplicate Project
          </DialogTitle>
          <DialogDescription>
            Create a copy of this project. The new project will be created as a draft.
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="font-medium text-blue-900 mb-2">
              Original project:
            </h4>
            <p className="text-sm text-blue-700 font-medium">
              {project?.title}
            </p>
            <p className="text-sm text-blue-600 mt-1">
              Status: {project?.status}
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="title">New Project Title</Label>
            <Input
              id="title"
              placeholder="Enter a title for the duplicated project"
              {...register('title')}
              disabled={isSubmitting}
            />
            {errors.title && (
              <p className="text-sm text-red-600">{errors.title.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="topic">Topic Description</Label>
            <ScrollArea className="h-[140px]">
              <Textarea
                id="topic"
                placeholder="Modify the topic description if needed"
                className="min-h-[140px] max-h-none resize-none border-0 shadow-none focus-visible:ring-0"
                {...register('topic')}
                disabled={isSubmitting}
              />
            </ScrollArea>
            {errors.topic && (
              <p className="text-sm text-red-600">{errors.topic.message}</p>
            )}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting}
              className="bg-blue-600 hover:bg-blue-700"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Duplicating...
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4 mr-2" />
                  Duplicate Project
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}