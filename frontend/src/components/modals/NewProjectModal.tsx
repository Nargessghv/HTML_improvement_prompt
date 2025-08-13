'use client'

import React, { useState, useEffect, useCallback } from 'react'
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useSupabaseAuth } from '@/hooks/useSupabaseAuthSimple'
import { Loader2, Sparkles, FileText } from 'lucide-react'

const projectSchema = z.object({
  title: z.string()
    .min(3, 'Title must be at least 3 characters')
    .max(100, 'Title must be less than 100 characters'),
  topic: z.string()
    .min(20, 'Topic description must be at least 20 characters')
    .max(5000, 'Topic description must be less than 5000 characters'),
  templateName: z.string().optional(),
})

type ProjectFormData = z.infer<typeof projectSchema>

interface Template {
  filename: string
  name: string
  display_name: string
  size_mb: number
  slide_count: number
  is_valid: boolean
  error_message?: string
}

interface NewProjectModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  initialTopic?: string
}

export function NewProjectModal({ open, onOpenChange, initialTopic }: NewProjectModalProps) {
  const router = useRouter()
  const { user, supabase } = useSupabaseAuth()
  const [isCreating, setIsCreating] = useState(false)
  const [templates, setTemplates] = useState<Template[]>([])
  const [loadingTemplates, setLoadingTemplates] = useState(false)

  const form = useForm<ProjectFormData>({
    resolver: zodResolver(projectSchema),
    defaultValues: {
      title: '',
      topic: initialTopic || '',
      templateName: 'auto',
    },
  })

  // Update form when initialTopic changes
  React.useEffect(() => {
    if (initialTopic) {
      form.setValue('topic', initialTopic)
    }
  }, [initialTopic, form])

  // Load templates when modal opens
  const loadTemplates = useCallback(async () => {
    if (!user) return
    
    setLoadingTemplates(true)
    try {
      const response = await fetch('http://localhost:8000/templates', {
        headers: {
          'Authorization': `Bearer dummy-token`, // Backend doesn't validate tokens yet
        }
      })
      
      if (!response.ok) {
        throw new Error('Failed to fetch templates')
      }
      
      const data = await response.json()
      setTemplates(data.templates?.filter((t: Template) => t.is_valid) || [])
    } catch (error) {
      console.error('Error loading templates:', error)
      toast.error('Failed to load templates')
    } finally {
      setLoadingTemplates(false)
    }
  }, [user])

  useEffect(() => {
    if (open && user) {
      loadTemplates()
    }
  }, [open, user, loadTemplates])

  const onSubmit = async (data: ProjectFormData) => {
    if (!user) {
      toast.error('You must be logged in to create a project')
      return
    }

    setIsCreating(true)
    
    try {
      // Create project in Supabase with template selection
      const { data: project, error } = await supabase
        .from('projects')
        .insert({
          user_id: user.id,
          title: data.title,
          topic: data.topic,
          status: 'draft',
          // Store template selection in metadata for now
          metadata: {
            template_name: data.templateName === 'auto' ? undefined : data.templateName
          }
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
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl">
            <div className="p-1.5 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800/30">
              <FileText className="h-5 w-5 text-red-600 dark:text-red-400" />
            </div>
            Create New Presentation
          </DialogTitle>
          <DialogDescription>
            Let AI agents create a professional PowerPoint for you.
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
                      className="focus:border-red-300 focus:ring-red-200 dark:focus:border-red-700 dark:focus:ring-red-800/30"
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
                    <div className="relative">
                      <Textarea
                        placeholder="Describe what you want your presentation to cover. Include key points, target audience, specific data or themes you'd like included."
                        className="min-h-[120px] max-h-[300px] focus:border-red-300 focus:ring-red-200 dark:focus:border-red-700 dark:focus:ring-red-800/30 resize-none overflow-y-auto"
                        {...field}
                      />
                      <div className="absolute bottom-2 right-2 text-xs text-gray-400 dark:text-gray-500">
                        {field.value.length}/5000
                      </div>
                    </div>
                  </FormControl>
                  <FormDescription>
                    Be specific about your content needs. More details help our AI create better presentations.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            
            <FormField
              control={form.control}
              name="templateName"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Presentation Template</FormLabel>
                  <FormControl>
                    <Select 
                      value={field.value} 
                      onValueChange={field.onChange}
                      disabled={loadingTemplates}
                    >
                      <SelectTrigger className="focus:border-red-300 focus:ring-red-200 dark:focus:border-red-700 dark:focus:ring-red-800/30">
                        <SelectValue placeholder={loadingTemplates ? "Loading templates..." : "Auto-select (recommended)"} />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="auto">
                          <div className="flex flex-col items-start">
                            <span className="font-medium">Auto-select</span>
                            <span className="text-xs text-gray-500">Use the default template</span>
                          </div>
                        </SelectItem>
                        {templates.map((template) => (
                          <SelectItem key={template.filename} value={template.filename}>
                            <div className="flex flex-col items-start">
                              <span className="font-medium">{template.display_name}</span>
                              <span className="text-xs text-gray-500">
                                {template.slide_count} slides • {template.size_mb.toFixed(1)} MB
                              </span>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormControl>
                  <FormDescription>
                    Choose a PowerPoint template for your presentation, or let us auto-select the best one.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            
            <div className="flex justify-end space-x-3 pt-4">
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
                className="bg-red-600 hover:bg-red-700 text-white"
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