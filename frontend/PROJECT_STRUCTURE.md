# Project Structure Documentation

This document outlines the comprehensive folder structure and organization of the Ekona Slide Creator frontend application.

## Root Directory Structure

```
frontend/
├── public/                          # Static assets
├── src/                            # Source code
├── .env.example                    # Environment variables template
├── .env.local.example             # Local development template
├── .vscode/                       # VS Code configuration
├── package.json                   # Project dependencies and scripts
├── next.config.ts                 # Next.js configuration
├── tailwind.config.ts             # Tailwind CSS configuration
├── tsconfig.json                  # TypeScript configuration
├── eslint.config.mjs              # ESLint configuration
├── .prettierrc                    # Prettier configuration
├── .editorconfig                  # Editor configuration
├── .gitignore                     # Git ignore rules
└── README.md                      # Project documentation
```

## Source Code Structure (`src/`)

### Application Directory (`src/app/`)
Next.js 14 App Router structure with route groups:

```
src/app/
├── (auth)/                        # Authentication route group
│   ├── login/
│   │   └── page.tsx              # Login page
│   ├── register/
│   │   └── page.tsx              # Registration page
│   └── layout.tsx                # Auth layout wrapper
├── (dashboard)/                   # Protected dashboard routes
│   ├── projects/
│   │   └── page.tsx              # Projects management page
│   ├── workflow/
│   │   └── page.tsx              # Workflow progress page
│   ├── settings/
│   │   └── page.tsx              # User settings page
│   └── layout.tsx                # Dashboard layout wrapper
├── api/                          # API routes
│   └── health/
│       └── route.ts              # Health check endpoint
├── favicon.ico                   # App favicon
├── globals.css                   # Global styles
├── layout.tsx                    # Root layout
└── page.tsx                      # Homepage
```

### Components Directory (`src/components/`)
Organized by feature and functionality:

```
src/components/
├── ui/                           # Base UI components (shadcn/ui)
│   ├── button.tsx
│   ├── card.tsx
│   ├── input.tsx
│   └── index.ts                  # UI components barrel export
├── layout/                       # Layout components
│   └── index.ts                  # Layout components barrel export
├── auth/                         # Authentication components
│   └── index.ts                  # Auth components barrel export
├── projects/                     # Project management components
│   └── index.ts                  # Project components barrel export
├── workflow/                     # Workflow progress components
│   └── index.ts                  # Workflow components barrel export
├── slides/                       # Slide viewing/editing components
│   └── index.ts                  # Slide components barrel export
├── common/                       # Common/shared components
│   └── index.ts                  # Common components barrel export
├── forms/                        # Reusable form components
│   └── index.ts                  # Form components barrel export
└── index.ts                      # Main components barrel export
```

### Hooks Directory (`src/hooks/`)
Custom React hooks:

```
src/hooks/
├── useSupabase.ts               # Supabase integration hooks
└── index.ts                     # Hooks barrel export (future)
```

### Library Directory (`src/lib/`)
Utility libraries and configurations:

```
src/lib/
├── supabase/                    # Supabase client configurations
│   ├── admin.ts                 # Admin client (server-side)
│   ├── client.ts                # Browser client
│   ├── server.ts                # Server client
│   ├── middleware.ts            # Authentication middleware
│   └── index.ts                 # Supabase barrel export
├── api.ts                       # API integration layer
├── env.ts                       # Environment validation
├── supabase.ts                  # Main Supabase configuration
└── utils.ts                     # Utility functions
```

### Stores Directory (`src/stores/`)
Zustand state management stores:

```
src/stores/
└── index.ts                     # Stores barrel export
```

### Types Directory (`src/types/`)
TypeScript type definitions:

```
src/types/
└── index.ts                     # Type definitions
```

### Constants Directory (`src/constants/`)
Application-wide constants:

```
src/constants/
└── index.ts                     # Constants and configuration
```

### Schemas Directory (`src/schemas/`)
Zod validation schemas:

```
src/schemas/
└── index.ts                     # Validation schemas
```

### Middleware Directory (`src/middleware/`)
Custom middleware functions:

```
src/middleware/
└── index.ts                     # Middleware helpers
```

### Contexts Directory (`src/contexts/`)
React contexts:

```
src/contexts/
└── index.ts                     # React contexts
```

## Key Design Patterns

### 1. Barrel Exports
Each directory includes an `index.ts` file for clean imports:

```typescript
// Instead of:
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'

// Use:
import { Button, Card } from '@/components/ui'
```

### 2. Route Groups
App Router uses route groups for logical organization:

- `(auth)` - Authentication pages with special layout
- `(dashboard)` - Protected dashboard pages with navigation

### 3. Feature-Based Organization
Components are organized by feature rather than type:

- `components/auth/` - All authentication-related components
- `components/projects/` - All project management components
- `components/workflow/` - All workflow tracking components

### 4. Type Safety
Comprehensive TypeScript support:

- Database types from Supabase
- Zod schemas for validation
- Environment variable validation
- API response types

### 5. State Management
Zustand stores organized by domain:

- Authentication state
- Project management state
- UI state
- Workflow progress state

## Component Categories

### UI Components (`components/ui/`)
Base design system components from shadcn/ui:
- Buttons, Cards, Inputs, Dialogs, etc.
- Consistent styling with Tailwind CSS
- Accessible and reusable

### Layout Components (`components/layout/`)
Application structure components:
- Header, Sidebar, Navigation
- Page layouts and wrappers
- Responsive design components

### Feature Components
Domain-specific components:
- **Auth**: Login forms, registration, password reset
- **Projects**: Project cards, lists, creation forms
- **Workflow**: Progress bars, agent status, timelines
- **Slides**: Viewers, editors, thumbnails

### Common Components (`components/common/`)
Shared utility components:
- Loading spinners, empty states
- Confirmation dialogs, notifications
- Search inputs, filters

## File Naming Conventions

- **Components**: PascalCase (`UserProfile.tsx`)
- **Hooks**: camelCase with `use` prefix (`useAuth.ts`)
- **Pages**: lowercase (`page.tsx`, `layout.tsx`)
- **Utilities**: camelCase (`formatDate.ts`)
- **Constants**: UPPER_SNAKE_CASE (`API_ROUTES`)

## Import Path Structure

Using TypeScript path mapping for clean imports:

```typescript
// Absolute imports with @ prefix
import { Button } from '@/components/ui'
import { env } from '@/lib/env'
import { PROJECT_STATUS } from '@/constants'
import { useAuth } from '@/hooks'
```

## Future Expansion

The structure is designed to accommodate future features:

- **Testing**: `__tests__/` directories alongside components
- **Storybook**: `.stories.tsx` files for component documentation
- **Internationalization**: `locales/` directory for translations
- **Assets**: `assets/` directory for images, icons, fonts

## Benefits

1. **Scalability**: Easy to add new features and components
2. **Maintainability**: Clear separation of concerns
3. **Developer Experience**: Intuitive navigation and imports
4. **Consistency**: Standardized patterns throughout the codebase
5. **Type Safety**: Comprehensive TypeScript coverage
6. **Performance**: Barrel exports enable tree shaking