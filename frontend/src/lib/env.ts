import { z } from 'zod'

// Environment variable validation schema
const envSchema = z.object({
  // Node Environment
  NODE_ENV: z.enum(['development', 'staging', 'production']).default('development'),
  
  // Supabase Configuration (Required)
  NEXT_PUBLIC_SUPABASE_URL: z.string().min(1, 'Supabase URL is required')
    .refine((url) => {
      // Allow placeholder during deployment
      if (url === 'https://placeholder.supabase.co') return true
      try {
        new URL(url)
        return true
      } catch {
        return false
      }
    }, 'Invalid Supabase URL format'),
  NEXT_PUBLIC_SUPABASE_ANON_KEY: z.string().min(1, 'Supabase anonymous key is required'),
  
  // Backend API Configuration (Required - but can be placeholder during deployment)
  NEXT_PUBLIC_API_URL: z.string().min(1, 'API URL is required')
    .refine((url) => {
      try {
        new URL(url)
        return true
      } catch {
        return false
      }
    }, 'Invalid API URL format').optional().default('http://localhost:8000'),
  
  // Application Configuration
  NEXT_PUBLIC_APP_URL: z.string().url('Invalid app URL').default('http://localhost:3000'),
  NEXT_PUBLIC_APP_NAME: z.string().default('Ekona Slide Creator'),
  NEXT_PUBLIC_COMPANY_NAME: z.string().default('Ekona'),
  
  // File Storage Configuration
  NEXT_PUBLIC_STORAGE_BUCKET: z.string().default('presentations'),
  
  // Feature Flags
  NEXT_PUBLIC_ENABLE_REALTIME: z.string().default('true').transform(val => val === 'true'),
  NEXT_PUBLIC_ENABLE_AI_CHAT: z.string().default('true').transform(val => val === 'true'),
  NEXT_PUBLIC_ENABLE_EXPORT: z.string().default('true').transform(val => val === 'true'),
  NEXT_PUBLIC_ENABLE_COLLABORATION: z.string().default('false').transform(val => val === 'true'),
  
  // Performance Configuration
  NEXT_PUBLIC_ENABLE_SW: z.string().default('false').transform(val => val === 'true'),
  NEXT_PUBLIC_CDN_URL: z.string().url().optional(),
  
  // Analytics (Optional)
  NEXT_PUBLIC_GA_ID: z.string().optional(),
  NEXT_PUBLIC_SENTRY_DSN: z.string().url().optional(),
  NEXT_PUBLIC_POSTHOG_KEY: z.string().optional(),
  NEXT_PUBLIC_POSTHOG_HOST: z.string().url().optional(),
})

// Server-only environment variables
const serverEnvSchema = z.object({
  // Security Configuration
  SUPABASE_SERVICE_ROLE_KEY: z.string().min(1, 'Service role key is required for server operations'),
  NEXTAUTH_SECRET: z.string().min(1, 'NextAuth secret is required'),
  JWT_SECRET: z.string().min(1, 'JWT secret is required'),
  
  // API Configuration
  API_AUTH_TOKEN: z.string().optional(),
  CORS_ORIGINS: z.string().default('http://localhost:3000'),
  
  // File Configuration
  MAX_FILE_SIZE: z.string().default('50MB'),
  MAX_FILES_PER_PROJECT: z.string().default('100').transform(val => parseInt(val, 10)),
  
  // Development Configuration
  DEBUG: z.string().default('false').transform(val => val === 'true'),
  VERBOSE_LOGGING: z.string().default('false').transform(val => val === 'true'),
  ENABLE_DEV_FEATURES: z.string().default('false').transform(val => val === 'true'),
  SKIP_AUTH: z.string().default('false').transform(val => val === 'true'),
  
  // Email Configuration (Optional)
  SMTP_HOST: z.string().optional(),
  SMTP_PORT: z.string().optional().transform(val => val ? parseInt(val, 10) : undefined),
  SMTP_USER: z.string().optional(),
  SMTP_PASS: z.string().optional(),
  SMTP_FROM: z.string().email().optional(),
  
  // Webhook Configuration
  WEBHOOK_SECRET: z.string().optional(),
  WEBHOOK_URL: z.string().url().optional(),
  
  // Performance Configuration
  REDIS_URL: z.string().url().optional(),
})

// Validate and parse environment variables
function validateEnv() {
  try {
    const env = envSchema.parse(process.env)
    return env
  } catch (error) {
    if (error instanceof z.ZodError) {
      const missingVars = error.issues.map(err => err.path.join('.')).join(', ')
      throw new Error(
        `Missing or invalid environment variables: ${missingVars}\n\n` +
        'Please check your .env.local file and ensure all required variables are set.\n' +
        'See .env.example for a complete list of available variables.'
      )
    }
    throw error
  }
}

// Validate server-only environment variables
function validateServerEnv() {
  try {
    const serverEnv = serverEnvSchema.parse(process.env)
    return serverEnv
  } catch (error) {
    if (error instanceof z.ZodError) {
      const missingVars = error.issues.map(err => err.path.join('.')).join(', ')
      throw new Error(
        `Missing or invalid server environment variables: ${missingVars}\n\n` +
        'Please check your .env.local file and ensure all required server variables are set.'
      )
    }
    throw error
  }
}

// Lazy-load environment variables to avoid initialization issues
let _env: z.infer<typeof envSchema> | null = null
let _serverEnv: z.infer<typeof serverEnvSchema> | null = null

// Export validated environment variables (lazy loaded)
export const env = new Proxy({} as z.infer<typeof envSchema>, {
  get(target, prop) {
    if (!_env) {
      _env = validateEnv()
    }
    return _env[prop as keyof typeof _env]
  }
})

// Export server environment variables (only use on server-side, lazy loaded)
export const serverEnv = typeof window === 'undefined' 
  ? new Proxy({} as z.infer<typeof serverEnvSchema>, {
      get(target, prop) {
        if (!_serverEnv) {
          _serverEnv = validateServerEnv()
        }
        return _serverEnv[prop as keyof typeof _serverEnv]
      }
    })
  : null

// Type definitions for better intellisense
export type Env = z.infer<typeof envSchema>
export type ServerEnv = z.infer<typeof serverEnvSchema>

// Helper functions (lazy evaluation)
export const isProduction = () => env.NODE_ENV === 'production'
export const isDevelopment = () => env.NODE_ENV === 'development'
export const isStaging = () => env.NODE_ENV === 'staging'

// Feature flag helpers (lazy evaluation)
export const features = new Proxy({} as {
  readonly realtime: boolean
  readonly aiChat: boolean
  readonly export: boolean
  readonly collaboration: boolean
  readonly serviceWorker: boolean
}, {
  get(target, prop) {
    switch(prop) {
      case 'realtime': return env.NEXT_PUBLIC_ENABLE_REALTIME
      case 'aiChat': return env.NEXT_PUBLIC_ENABLE_AI_CHAT
      case 'export': return env.NEXT_PUBLIC_ENABLE_EXPORT
      case 'collaboration': return env.NEXT_PUBLIC_ENABLE_COLLABORATION
      case 'serviceWorker': return env.NEXT_PUBLIC_ENABLE_SW
      default: return undefined
    }
  }
})

// Validation helper for runtime checks
export function ensureEnvVar(name: string, value: string | undefined): string {
  if (!value) {
    throw new Error(
      `Environment variable ${name} is required but not set.\n` +
      'Please check your .env.local file.'
    )
  }
  return value
}

// Development helper to log environment status
export function logEnvStatus() {
  if (isDevelopment()) {
    console.log('🌍 Environment Configuration:')
    console.log(`   NODE_ENV: ${env.NODE_ENV}`)
    console.log(`   API URL: ${env.NEXT_PUBLIC_API_URL}`)
    console.log(`   App URL: ${env.NEXT_PUBLIC_APP_URL}`)
    console.log(`   Supabase URL: ${env.NEXT_PUBLIC_SUPABASE_URL}`)
    console.log('🎛️  Feature Flags:')
    const flagKeys = ['realtime', 'aiChat', 'export', 'collaboration', 'serviceWorker'] as const
    flagKeys.forEach((key) => {
      console.log(`   ${key}: ${features[key] ? '✅' : '❌'}`)
    })
  }
}