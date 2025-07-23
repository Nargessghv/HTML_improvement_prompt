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
import { Loader2 } from 'lucide-react'

const editProjectSchema = z.object({
  title: z
    .string()
    .min(1, 'Project title is required')
    .max(100, 'Title must be less than 100 characters'),
  topic: z
    .string()
    .min(10, 'Topic must be at least 10 characters'),
})

type EditProjectFormData = z.infer<typeof editProjectSchema>

interface Project {
  id: string
  title: string
  topic: string
  status: 'draft' | 'processing' | 'completed' | 'failed'
  created_at: string
  updated_at: string
  completed_at: string | null
}

interface EditProjectModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  project: Project | null
  onProjectUpdated: (updatedProject: Project) => void
}

export function EditProjectModal({ 
  open, 
  onOpenChange, 
  project,
  onProjectUpdated
}: EditProjectModalProps) {
  const { supabase } = useSupabaseAuth()

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting }
  } = useForm<EditProjectFormData>({
    resolver: zodResolver(editProjectSchema),
    defaultValues: {
      title: '',
      topic: ''
    }
  })

  // Reset form when project changes
  useEffect(() => {
    if (project) {
      reset({
        title: project.title,
        topic: project.topic
      })
    }
  }, [project, reset])

  const onSubmit = async (data: EditProjectFormData) => {
    if (!project) return

    try {
      const { data: updatedProject, error } = await supabase
        .from('projects')
        .update({
          title: data.title,
          topic: data.topic
        })
        .eq('id', project.id)
        .select()
        .single()

      if (error) {
        console.error('Project update error:', error)
        toast.error(error.message || 'Failed to update project')
        return
      }

      toast.success('Project updated successfully!')
      onProjectUpdated(updatedProject)
      onOpenChange(false)
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

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Edit Project</DialogTitle>
          <DialogDescription>
            Update your project title and topic description.
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="title">Project Title</Label>
            <Input
              id="title"
              placeholder="Enter a descriptive title for your presentation"
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
                placeholder="Describe what you want your presentation to be about. Be as detailed as possible - this helps our AI create better slides."
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
                  Updating...
                </>
              ) : (
                'Update Project'
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}