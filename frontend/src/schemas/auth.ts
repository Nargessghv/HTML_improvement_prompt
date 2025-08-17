// Authentication form validation schemas
import { z } from 'zod'

// Note: Login/Register schemas kept for profile management forms only
// Azure AD handles actual authentication

export const profileSchema = z.object({
  full_name: z
    .string()
    .min(1, 'Full name is required')
    .max(100, 'Full name must be less than 100 characters'),
  display_name: z
    .string()
    .optional()
    .refine((val) => !val || val.length <= 50, {
      message: 'Display name must be less than 50 characters'
    }),
  bio: z
    .string()
    .optional()
    .refine((val) => !val || val.length <= 500, {
      message: 'Bio must be less than 500 characters'
    }),
  avatar_url: z
    .string()
    .url('Please enter a valid URL')
    .optional()
    .or(z.literal(''))
})

export type ProfileFormData = z.infer<typeof profileSchema>