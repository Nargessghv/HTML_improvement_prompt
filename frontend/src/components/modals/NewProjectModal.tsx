'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import * as z from 'zod'
import { toast } from 'sonner'
import { 
  Dialog, 
  DialogContent, 
  DialogDescription, 
  DialogHeader, 
  DialogTitle 
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useSupabaseAuth } from '@/hooks/useSupabaseAuthSimple'
import { Loader2, Sparkles } from 'lucide-react'

const projectSchema = z.object({
  title: z.string()
    .min(3, 'Title must be at least 3 characters')
    .max(100, 'Title must be less than 100 characters'),
  topic: z.string()
    .min(10, 'Topic description must be at least 10 characters'),
})

type ProjectFormData = z.infer<typeof projectSchema>

interface NewProjectModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function NewProjectModal({ open, onOpenChange }: NewProjectModalProps) {
  const router = useRouter()
  const { user, supabase } = useSupabaseAuth()
  const [isCreating, setIsCreating] = useState(false)

  const form = useForm<ProjectFormData>({
    resolver: zodResolver(projectSchema),
    defaultValues: {
      title: '',
      topic: '',
    },
  })

  const onSubmit = async (data: ProjectFormData) => {
    if (!user) {
      toast.error('You must be logged in to create a project')
      return
    }

    setIsCreating(true)
    
    try {
      // Create project in Supabase
      const { data: project, error } = await supabase
        .from('projects')
        .insert({
          user_id: user.id,
          title: data.title,
          topic: data.topic,
          status: 'draft'
        })
        .select()
        .single()

      if (error) {
        console.error('Project creation error:', error)
        console.error('Error details:', JSON.stringify(error, null, 2))
        toast.error(error.message || 'Failed to create project')
        return
      }

      toast.success(`Project "${data.title}" created successfully!`)
      
      // Reset form
      form.reset()
      onOpenChange(false)
      
      // Navigate to project detail page
      router.push(`/projects/${project.id}`)

    } catch (error) {
      console.error('Unexpected error:', error)
      toast.error('An unexpected error occurred')
    } finally {
      setIsCreating(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[525px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-blue-600" />
            Create New Presentation
          </DialogTitle>
          <DialogDescription>
            Describe your presentation topic and let our AI agents create a professional PowerPoint for you.
          </DialogDescription>
        </DialogHeader>
        
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            <FormField
              control={form.control}
              name="title"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Presentation Title</FormLabel>
                  <FormControl>
                    <Input 
                      placeholder="e.g., Q4 Business Review, Marketing Strategy 2024"
                      {...field} 
                    />
                  </FormControl>
                  <FormDescription>
                    Give your presentation a clear, descriptive title.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            
            <FormField
              control={form.control}
              name="topic"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Topic Description</FormLabel>
                  <FormControl>
                    <ScrollArea className="h-[120px]">
                      <Textarea
                        placeholder="Describe what you want your presentation to cover. Include key points, target audience, specific data or themes you'd like included..."
                        className="min-h-[120px] max-h-none resize-none border-0 shadow-none focus-visible:ring-0"
                        {...field}
                      />
                    </ScrollArea>
                  </FormControl>
                  <FormDescription>
                    Be specific about your content needs. The more detail you provide, the better our AI can tailor the presentation.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            
            <div className="flex justify-end space-x-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isCreating}
              >
                Cancel
              </Button>
              <Button 
                type="submit" 
                disabled={isCreating}
                className="bg-blue-600 hover:bg-blue-700"
              >
                {isCreating ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Sparkles className="mr-2 h-4 w-4" />
                    Create Presentation
                  </>
                )}
              </Button>
            </div>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}