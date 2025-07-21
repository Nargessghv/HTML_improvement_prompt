// Zod validation schemas
// Re-export all validation schemas from this directory

import { z } from 'zod'

// Authentication Schemas
export const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
})

export const registerSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"],
})

export const passwordResetSchema = z.object({
  email: z.string().email('Invalid email address'),
})

// Project Schemas
export const createProjectSchema = z.object({
  title: z.string().min(1, 'Title is required').max(100, 'Title must be less than 100 characters'),
  topic: z.string().min(1, 'Topic is required').max(500, 'Topic must be less than 500 characters'),
})

export const updateProjectSchema = z.object({
  title: z.string().min(1, 'Title is required').max(100, 'Title must be less than 100 characters').optional(),
  topic: z.string().min(1, 'Topic is required').max(500, 'Topic must be less than 500 characters').optional(),
})

// Workflow Schemas
export const startGenerationSchema = z.object({
  projectId: z.string().uuid('Invalid project ID'),
  topic: z.string().min(1, 'Topic is required'),
  templatePath: z.string().optional(),
})

// User Preferences Schema
export const userPreferencesSchema = z.object({
  theme: z.enum(['light', 'dark', 'system']).default('system'),
  sidebarCollapsed: z.boolean().default(false),
  itemsPerPage: z.number().min(10).max(100).default(20),
  enableNotifications: z.boolean().default(true),
  enableAutoSave: z.boolean().default(true),
})

// API Response Schemas
export const projectResponseSchema = z.object({
  id: z.string().uuid(),
  user_id: z.string().uuid(),
  title: z.string(),
  topic: z.string(),
  status: z.enum(['draft', 'processing', 'completed', 'failed']),
  created_at: z.string(),
  updated_at: z.string(),
  completed_at: z.string().nullable(),
  metadata: z.record(z.string(), z.unknown()),
})

export const workflowStateResponseSchema = z.object({
  id: z.string().uuid(),
  project_id: z.string().uuid(),
  agent_name: z.string(),
  status: z.enum(['pending', 'in_progress', 'completed', 'failed']),
  input_data: z.record(z.string(), z.unknown()).nullable(),
  output_data: z.record(z.string(), z.unknown()).nullable(),
  error_message: z.string().nullable(),
  started_at: z.string().nullable(),
  completed_at: z.string().nullable(),
  execution_time_seconds: z.number().nullable(),
  created_at: z.string(),
})

// Form Validation Helpers
export type LoginForm = z.infer<typeof loginSchema>
export type RegisterForm = z.infer<typeof registerSchema>
export type PasswordResetForm = z.infer<typeof passwordResetSchema>
export type CreateProjectForm = z.infer<typeof createProjectSchema>
export type UpdateProjectForm = z.infer<typeof updateProjectSchema>
export type StartGenerationForm = z.infer<typeof startGenerationSchema>
export type UserPreferences = z.infer<typeof userPreferencesSchema>

// Generic validation helper
export const validateSchema = <T>(schema: z.ZodSchema<T>, data: unknown): { success: true; data: T } | { success: false; errors: string[] } => {
  const result = schema.safeParse(data)
  
  if (result.success) {
    return { success: true, data: result.data }
  }
  
  return {
    success: false,
    errors: result.error.issues.map((err: z.ZodIssue) => err.message)
  }
}