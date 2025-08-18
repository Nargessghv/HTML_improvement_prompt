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
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { useSupabaseAuth } from '@/hooks/useSupabaseAuthSimple'
import { Loader2, Sparkles, FileText, ChevronDown } from 'lucide-react'
import { DocumentUpload } from '@/components/DocumentUpload'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"

const projectSchema = z.object({
  title: z.string()
    .min(3, 'Title must be at least 3 characters')
    .max(100, 'Title must be less than 100 characters'),
  topic: z.string()
    .min(20, 'Topic description must be at least 20 characters')
    .max(5000, 'Topic description must be less than 5000 characters'),
  templateName: z.string().min(1, 'Please select a template'),
  htmlRefinementIterations: z.number()
    .min(1, 'Must be at least 1 iteration')
    .max(5, 'Maximum 5 iterations allowed')
    .default(3),
  imageQuality: z.enum(['low', 'medium', 'high', 'auto']).default('auto'),
  imageSize: z.enum(['1024x1024', '1536x1024', '1024x1536', 'auto']).default('auto'),
})

type ProjectFormData = z.infer<typeof projectSchema>

interface Template {
  filename: string
  name: string
  display_name: string
  size_mb: number
  slide_count: number
  layout_count: number
  is_valid: boolean
  error_message?: string
  folder_path?: string
  locked_backgrounds?: number
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
  const [uploadedDocuments, setUploadedDocuments] = useState<any[]>([])
  const [showDocuments, setShowDocuments] = useState(false)

  const form = useForm<ProjectFormData>({
    resolver: zodResolver(projectSchema),
    defaultValues: {
      title: '',
      topic: initialTopic || '',
      templateName: undefined,
      htmlRefinementIterations: 3,
      imageQuality: 'auto',
      imageSize: 'auto',
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
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/templates`, {
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
      // Create project in Supabase with template selection and refinement iterations
      const { data: project, error } = await supabase
        .from('projects')
        .insert({
          user_id: user.id,
          title: data.title,
          topic: data.topic,
          status: 'draft',
          // Store template selection and refinement iterations in metadata
          metadata: {
            template_name: data.templateName,
            html_refinement_iterations: data.htmlRefinementIterations,
            image_quality: data.imageQuality,
            image_size: data.imageSize
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

      // Upload documents if any were added
      if (uploadedDocuments.length > 0 && project?.id) {
        console.log(`Uploading ${uploadedDocuments.length} documents for project ${project.id}`)
        try {
          const uploadPromises = uploadedDocuments.map(async (doc) => {
            console.log(`Uploading document: ${doc.file.name} (${doc.file.size} bytes)`)
            const formData = new FormData()
            formData.append('file', doc.file)
            
            const uploadUrl = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/projects/${project.id}/documents`
            console.log(`Upload URL: ${uploadUrl}`)
            
            // Get the Supabase session token
            const { data: { session } } = await supabase.auth.getSession()
            const token = session?.access_token
            console.log(`Got auth token: ${token ? 'yes' : 'no'}`)
            
            const response = await fetch(uploadUrl, {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${token}`
              },
              body: formData
            })
            
            console.log(`Upload response status: ${response.status}`)
            
            if (!response.ok) {
              const errorText = await response.text()
              console.error(`Upload failed: ${errorText}`)
              throw new Error(`Failed to upload ${doc.file.name}: ${response.status} ${errorText}`)
            }
            
            return response.json()
          })
          
          const results = await Promise.all(uploadPromises)
          console.log('All documents uploaded successfully:', results)
          toast.success(`Uploaded ${uploadedDocuments.length} document(s) as context`)
        } catch (uploadError) {
          console.error('Document upload error:', uploadError)
          toast.warning('Project created but some documents failed to upload')
        }
      } else {
        console.log(`No documents to upload. Documents count: ${uploadedDocuments.length}, Project ID: ${project?.id}`)
      }

      toast.success(`Project "${data.title}" created successfully!`)
      
      // Reset form and documents
      form.reset()
      setUploadedDocuments([])
      setShowDocuments(false)
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
      <DialogContent className="max-w-md p-0 gap-0 overflow-hidden">
        <div className="p-8">
          {/* Header */}
          <DialogHeader className="text-center mb-8">
            <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-900 flex items-center justify-center">
              <Sparkles className="w-8 h-8 text-gray-600 dark:text-gray-400" />
            </div>
            <DialogTitle className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
              Create Presentation
            </DialogTitle>
            <DialogDescription className="text-sm text-gray-500 dark:text-gray-400">
              AI will generate a professional presentation for you
            </DialogDescription>
          </DialogHeader>

          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              {/* Title */}
              <FormField
                control={form.control}
                name="title"
                render={({ field }) => (
                  <FormItem className="space-y-2">
                    <FormLabel className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Title
                    </FormLabel>
                    <FormControl>
                      <Input 
                        placeholder="Q4 Business Review"
                        className="h-12 border-gray-200 dark:border-gray-700 focus:border-gray-400 dark:focus:border-gray-500 focus:ring-0 text-base bg-white dark:bg-gray-800"
                        {...field} 
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Topic */}
              <FormField
                control={form.control}
                name="topic"
                render={({ field }) => (
                  <FormItem className="space-y-2">
                    <FormLabel className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Content
                    </FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Textarea
                          placeholder="Describe what you want to present..."
                          className="min-h-[100px] border-gray-200 dark:border-gray-700 focus:border-gray-400 dark:focus:border-gray-500 focus:ring-0 text-base resize-none bg-white dark:bg-gray-800"
                          {...field}
                        />
                        <div className="absolute bottom-3 right-3 text-xs text-gray-400">
                          {field.value.length}/5000
                        </div>
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Template */}
              <FormField
                control={form.control}
                name="templateName"
                render={({ field }) => (
                  <FormItem className="space-y-2">
                    <FormLabel className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Template
                    </FormLabel>
                    <FormControl>
                      <Select 
                        value={field.value} 
                        onValueChange={field.onChange}
                        disabled={loadingTemplates}
                      >
                        <SelectTrigger className="w-full h-12 border-gray-200 dark:border-gray-700 focus:border-gray-400 dark:focus:border-gray-500 focus:ring-0 text-base">
                          <SelectValue placeholder={loadingTemplates ? "Loading templates..." : "Choose a template"} />
                        </SelectTrigger>
                        <SelectContent>
                          {templates.map((template) => (
                            <SelectItem key={template.name} value={template.name}>
                              <div className="flex flex-col items-start">
                                <span className="font-medium">{template.display_name}</span>
                                <span className="text-xs text-gray-500">
                                  {template.layout_count} layouts
                                </span>
                              </div>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Quality */}
              <FormField
                control={form.control}
                name="htmlRefinementIterations"
                render={({ field }) => (
                  <FormItem className="space-y-3">
                    <FormLabel className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Quality
                    </FormLabel>
                    <FormControl>
                      <RadioGroup
                        value={field.value?.toString()}
                        onValueChange={(value) => field.onChange(parseInt(value))}
                        className="space-y-2"
                      >
                        {[
                          { value: '1', label: 'Draft', time: '1 min', desc: 'Quick draft generation' },
                          { value: '3', label: 'Balanced', time: '3 min', desc: 'Good quality and speed' },
                          { value: '5', label: 'High Quality', time: '5 min', desc: 'Best visual results' }
                        ].map((option) => (
                          <div key={option.value} className="flex items-center space-x-3">
                            <RadioGroupItem value={option.value} id={option.value} />
                            <label
                              htmlFor={option.value}
                              className="flex-1 cursor-pointer"
                            >
                              <div className="flex items-center justify-between">
                                <div>
                                  <div className="text-sm font-medium text-gray-700 dark:text-gray-300">
                                    {option.label}
                                  </div>
                                  <div className="text-xs text-gray-500">
                                    {option.desc}
                                  </div>
                                </div>
                                <span className="text-xs text-gray-500">
                                  ~{option.time}
                                </span>
                              </div>
                            </label>
                          </div>
                        ))}
                      </RadioGroup>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Image Quality */}
              <FormField
                control={form.control}
                name="imageQuality"
                render={({ field }) => (
                  <FormItem className="space-y-2">
                    <FormLabel className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Image Quality
                    </FormLabel>
                    <FormControl>
                      <Select 
                        value={field.value} 
                        onValueChange={field.onChange}
                      >
                        <SelectTrigger className="w-full h-12 border-gray-200 dark:border-gray-700 focus:border-gray-400 dark:focus:border-gray-500 focus:ring-0 text-base">
                          <SelectValue placeholder="Select image quality" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="auto">
                            <div className="flex flex-col items-start">
                              <span className="font-medium">Auto</span>
                              <span className="text-xs text-gray-500">
                                Let AI decide based on content
                              </span>
                            </div>
                          </SelectItem>
                          <SelectItem value="low">
                            <div className="flex flex-col items-start">
                              <span className="font-medium">Low</span>
                              <span className="text-xs text-gray-500">
                                Fast generation, lower quality
                              </span>
                            </div>
                          </SelectItem>
                          <SelectItem value="medium">
                            <div className="flex flex-col items-start">
                              <span className="font-medium">Medium</span>
                              <span className="text-xs text-gray-500">
                                Balanced quality and speed
                              </span>
                            </div>
                          </SelectItem>
                          <SelectItem value="high">
                            <div className="flex flex-col items-start">
                              <span className="font-medium">High</span>
                              <span className="text-xs text-gray-500">
                                Best quality, slower generation
                              </span>
                            </div>
                          </SelectItem>
                        </SelectContent>
                      </Select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Image Size */}
              <FormField
                control={form.control}
                name="imageSize"
                render={({ field }) => (
                  <FormItem className="space-y-2">
                    <FormLabel className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Image Resolution
                    </FormLabel>
                    <FormControl>
                      <Select 
                        value={field.value} 
                        onValueChange={field.onChange}
                      >
                        <SelectTrigger className="w-full h-12 border-gray-200 dark:border-gray-700 focus:border-gray-400 dark:focus:border-gray-500 focus:ring-0 text-base">
                          <SelectValue placeholder="Select image resolution" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="auto">
                            <div className="flex flex-col items-start">
                              <span className="font-medium">Auto</span>
                              <span className="text-xs text-gray-500">
                                Let AI decide based on content
                              </span>
                            </div>
                          </SelectItem>
                          <SelectItem value="1024x1024">
                            <div className="flex flex-col items-start">
                              <span className="font-medium">Square (1024x1024)</span>
                              <span className="text-xs text-gray-500">
                                Best for icons and balanced content
                              </span>
                            </div>
                          </SelectItem>
                          <SelectItem value="1024x1536">
                            <div className="flex flex-col items-start">
                              <span className="font-medium">Portrait (1024x1536)</span>
                              <span className="text-xs text-gray-500">
                                Best for vertical content
                              </span>
                            </div>
                          </SelectItem>
                          <SelectItem value="1536x1024">
                            <div className="flex flex-col items-start">
                              <span className="font-medium">Landscape (1536x1024)</span>
                              <span className="text-xs text-gray-500">
                                Best for horizontal content
                              </span>
                            </div>
                          </SelectItem>
                        </SelectContent>
                      </Select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Document Upload (Optional) */}
              <Collapsible open={showDocuments} onOpenChange={setShowDocuments}>
                <CollapsibleTrigger className="w-full">
                  <div className="flex items-center justify-between p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors cursor-pointer">
                    <div className="flex items-center space-x-2">
                      <FileText className="w-4 h-4 text-gray-500" />
                      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Add Context Documents
                      </span>
                      {uploadedDocuments.length > 0 && (
                        <span className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 px-2 py-0.5 rounded-full">
                          {uploadedDocuments.length} file{uploadedDocuments.length !== 1 ? 's' : ''}
                        </span>
                      )}
                    </div>
                    <ChevronDown className={`w-4 h-4 text-gray-500 transition-transform ${showDocuments ? 'rotate-180' : ''}`} />
                  </div>
                </CollapsibleTrigger>
                <CollapsibleContent className="mt-3">
                  <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                      Upload PDF, Word, PowerPoint, or text files to provide context for your presentation
                    </p>
                    <DocumentUpload
                      onDocumentsUploaded={setUploadedDocuments}
                      maxFiles={5}
                      maxSizeMB={10}
                    />
                  </div>
                </CollapsibleContent>
              </Collapsible>

              {/* Actions */}
              <div className="flex space-x-3 pt-6">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => onOpenChange(false)}
                  disabled={isCreating}
                  className="flex-1 h-12 border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
                >
                  Cancel
                </Button>
                <Button 
                  type="submit" 
                  disabled={isCreating}
                  className="flex-1 h-12 bg-gray-900 hover:bg-gray-800 dark:bg-gray-100 dark:hover:bg-gray-200 dark:text-gray-900 text-white"
                >
                  {isCreating ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    <>
                      Create
                    </>
                  )}
                </Button>
              </div>
            </form>
          </Form>
        </div>
      </DialogContent>
    </Dialog>
  )
}