// Application constants and configuration

// API Configuration
export const API_ROUTES = {
  PROJECTS: '/api/projects',
  HEALTH: '/api/health',
  WEBHOOKS: '/api/webhooks',
} as const

// Application Routes
export const APP_ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  REGISTER: '/register',
  DASHBOARD: '/dashboard',
  PROJECTS: '/dashboard/projects',
  WORKFLOW: '/dashboard/workflow',
  SETTINGS: '/dashboard/settings',
} as const

// Project Status
export const PROJECT_STATUS = {
  DRAFT: 'draft',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  FAILED: 'failed',
} as const

export type ProjectStatus = typeof PROJECT_STATUS[keyof typeof PROJECT_STATUS]

// Workflow Agent Names
export const AGENT_NAMES = {
  LAYOUT_ANALYSIS: 'layout_analysis',
  PRESENTATION_PLANNING: 'presentation_planning',
  CONTENT_GENERATION: 'content_generation',
  HTML_CONTENT_GENERATION: 'html_content_generation',
  HTML_REFINEMENT: 'html_refinement',
  QUALITY_REVIEW: 'quality_review',
  SLIDE_ASSEMBLY: 'slide_assembly',
} as const

export type AgentName = typeof AGENT_NAMES[keyof typeof AGENT_NAMES]

// Workflow State Status
export const WORKFLOW_STATUS = {
  PENDING: 'pending',
  IN_PROGRESS: 'in_progress',
  COMPLETED: 'completed',
  FAILED: 'failed',
} as const

export type WorkflowStatus = typeof WORKFLOW_STATUS[keyof typeof WORKFLOW_STATUS]

// UI Constants
export const UI_CONSTANTS = {
  MAX_FILE_SIZE: 50 * 1024 * 1024, // 50MB
  ITEMS_PER_PAGE: 20,
  DEBOUNCE_DELAY: 300,
  TOAST_DURATION: 5000,
  ANIMATION_DURATION: 200,
} as const

// Viewport Constants (for slide rendering)
export const SLIDE_VIEWPORT = {
  WIDTH: 1577,
  HEIGHT: 603,
  ASPECT_RATIO: 1577 / 603,
} as const

// Error Messages
export const ERROR_MESSAGES = {
  GENERIC: 'Something went wrong. Please try again.',
  NETWORK: 'Network error. Please check your connection.',
  UNAUTHORIZED: 'You are not authorized to perform this action.',
  NOT_FOUND: 'The requested resource was not found.',
  VALIDATION: 'Please check your input and try again.',
  FILE_TOO_LARGE: 'File is too large. Maximum size is 50MB.',
} as const

// Success Messages
export const SUCCESS_MESSAGES = {
  PROJECT_CREATED: 'Project created successfully!',
  PROJECT_UPDATED: 'Project updated successfully!',
  PROJECT_DELETED: 'Project deleted successfully!',
  SETTINGS_SAVED: 'Settings saved successfully!',
} as const

// Feature Flags (can be overridden by environment variables)
export const FEATURE_FLAGS = {
  ENABLE_COLLABORATION: false,
  ENABLE_EXPORT: true,
  ENABLE_AI_CHAT: true,
  ENABLE_REALTIME: true,
} as const

// Local Storage Keys
export const STORAGE_KEYS = {
  THEME: 'ekona-theme',
  SIDEBAR_COLLAPSED: 'ekona-sidebar-collapsed',
  LAST_PROJECT: 'ekona-last-project',
  USER_PREFERENCES: 'ekona-user-preferences',
} as const

// Theme Configuration
export const THEME = {
  COLORS: {
    PRIMARY: 'hsl(var(--primary))',
    SECONDARY: 'hsl(var(--secondary))',
    ACCENT: 'hsl(var(--accent))',
    DESTRUCTIVE: 'hsl(var(--destructive))',
  },
  BREAKPOINTS: {
    SM: '640px',
    MD: '768px',
    LG: '1024px',
    XL: '1280px',
    '2XL': '1536px',
  },
} as const