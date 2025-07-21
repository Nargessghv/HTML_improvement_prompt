# Ekona Slide Creator - Frontend

This is the frontend application for the Ekona AI-Powered PowerPoint Slide Creator system. Built with [Next.js](https://nextjs.org) and bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Technology Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript with strict type checking
- **UI**: Tailwind CSS + shadcn/ui components
- **Database**: Supabase (PostgreSQL)
- **Authentication**: Supabase Auth
- **State Management**: Zustand with persistent stores
- **Real-time**: Supabase Realtime subscriptions
- **Validation**: Zod schemas for forms and API
- **Development**: ESLint, Prettier, Husky, lint-staged
- **IDE**: VS Code with optimized configuration

## Prerequisites

Before running this application, you need:

1. **Supabase Project**: Set up a Supabase project with the required database schema
2. **Environment Configuration**: Configure environment variables (see setup below)
3. **Backend API**: The Python backend API should be running (typically on port 8000)

## Environment Setup

1. **Copy environment template:**
   ```bash
   cp .env.local.example .env.local
   ```

2. **Configure your environment variables** in `.env.local`:
   - `NEXT_PUBLIC_SUPABASE_URL`: Your Supabase project URL
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Your Supabase anonymous key
   - `NEXT_PUBLIC_API_URL`: Backend API URL (default: http://localhost:8000)

3. **For detailed environment setup**, see [ENVIRONMENT_SETUP.md](./ENVIRONMENT_SETUP.md)

## Development Setup

For a comprehensive development environment setup including code quality tools, see [DEVELOPMENT_SETUP.md](./DEVELOPMENT_SETUP.md).

## Getting Started

After setting up your environment, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## Available Scripts

```bash
# Development
npm run dev              # Start development server with Turbopack
npm run build           # Build for production
npm run start           # Start production server

# Code Quality
npm run lint            # Run ESLint
npm run lint:fix        # Run ESLint with auto-fix
npm run format          # Format all files with Prettier
npm run format:check    # Check if files are formatted
npm run type-check      # Run TypeScript type checking
```

## Health Check

Visit [http://localhost:3000/health](http://localhost:3000/health) to verify your environment configuration and check service connectivity.

## Development Tools

This project includes a comprehensive development environment:

- **ESLint**: Code linting with TypeScript, React, and Next.js rules
- **Prettier**: Automatic code formatting with Tailwind CSS class sorting
- **TypeScript**: Strict type checking for better code quality
- **Husky**: Git hooks for code quality enforcement
- **VS Code**: Optimized configuration with recommended extensions
- **Environment Validation**: Runtime checks for required configuration

## Project Structure

The project follows a feature-based organization for scalability and maintainability:

```
src/
├── app/                 # Next.js 14 App Router
│   ├── (auth)/         # Authentication route group
│   ├── (dashboard)/    # Protected dashboard routes
│   └── api/            # API routes
├── components/          # Feature-based component organization
│   ├── ui/             # Base UI components (shadcn/ui)
│   ├── layout/         # Navigation, headers, sidebars
│   ├── auth/           # Authentication components
│   ├── projects/       # Project management components
│   ├── workflow/       # Workflow progress components
│   ├── slides/         # Slide viewing/editing components
│   ├── common/         # Shared utility components
│   └── forms/          # Reusable form components
├── hooks/              # Custom React hooks (useSupabaseAuth, etc.)
├── lib/                # Utility libraries
│   ├── supabase/       # Supabase client configuration
│   ├── env.ts          # Environment validation
│   └── utils.ts        # Utility functions
├── stores/             # Zustand state stores (auth, project, workflow, slide, ui)
├── schemas/            # Zod validation schemas
├── constants/          # Application constants
├── middleware/         # Custom middleware functions
├── contexts/           # React contexts
└── types/              # TypeScript type definitions
```

For detailed structure documentation, see [PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md).

## Key Features

### Route Organization
- **Route Groups**: Authentication and dashboard pages are logically grouped
- **Layouts**: Specialized layouts for auth pages and dashboard
- **Type Safety**: All routes are properly typed with metadata

### Component Architecture
- **Feature-Based Organization**: Components grouped by functionality
- **Barrel Exports**: Clean imports with `@/components/ui` syntax
- **Reusable Design**: Consistent UI components across the application

### Development Experience
- **Hot Reload**: Instant feedback with Turbopack
- **Type Checking**: Real-time TypeScript validation
- **Code Quality**: Automated linting and formatting
- **Environment Validation**: Runtime checks for configuration

### State Management
- **Centralized Stores**: 5 specialized Zustand stores (auth, project, workflow, slide, ui)
- **Persistent Storage**: Auth and UI preferences persist across sessions
- **Real-time Updates**: Workflow progress tracked via Supabase subscriptions
- **Form Validation**: Zod schemas for type-safe forms and API validation
- **Optimized Performance**: Selective subscriptions and computed selectors

## Development Guidelines

### Working with State Management

The application uses Zustand for state management with 5 specialized stores:

1. **`authStore`** - User authentication and session management
   ```typescript
   import { useAuth, useAuthActions } from '@/stores'
   
   const { user, isAuthenticated } = useAuth()
   const { signOut } = useAuthActions()
   ```

2. **`projectStore`** - Project CRUD operations, filtering, and pagination
   ```typescript
   import { useProjects, useProjectActions } from '@/stores'
   
   const { projects, isLoading } = useProjects()
   const { addProject, updateProject } = useProjectActions()
   ```

3. **`workflowStore`** - Real-time workflow progress tracking
   ```typescript
   import { useWorkflowProgress, useWorkflowActions } from '@/stores'
   
   const { overallProgress, currentAgent } = useWorkflowProgress()
   const { startWorkflow, updateAgentState } = useWorkflowActions()
   ```

4. **`slideStore`** - Slide management with HTML editing and chat
   ```typescript
   import { useSlides, useSlideEditor } from '@/stores'
   
   const { slides } = useSlides()
   const { isEditing, startEditing } = useSlideEditor()
   ```

5. **`uiStore`** - UI state, preferences, modals, and notifications
   ```typescript
   import { useNotifications, useModals } from '@/stores'
   
   const { addNotification } = useNotifications()
   const { openModal } = useModals()
   ```

### Custom Hooks

- **`useSupabaseAuth`** - Complete authentication integration with Supabase
  - Handles sign in/up, password reset, session management
  - Automatically updates auth store and shows notifications
  - Integrates with Next.js router for redirects

### TypeScript Integration

All stores are fully typed with:
- Strict type checking for state and actions
- Zod schema validation for forms and API responses
- Type-safe selectors and computed values
- IntelliSense support for all store operations

### Performance Considerations

- Use selective subscriptions to avoid unnecessary re-renders
- Leverage computed selectors for derived state
- Store persistence is optimized for auth and UI preferences only
- Real-time subscriptions are managed automatically

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
