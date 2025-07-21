# Frontend Development Plan: Slide Creator Management System

## Project Overview

This plan outlines the development of a comprehensive frontend application to manage the AI-powered PowerPoint Slide Creator system. The frontend will provide user authentication, project management, real-time progress tracking, and interactive slide editing capabilities.

## System Architecture Overview

### Current Backend
- **AI-Powered Slide Generation**: 7 specialized AI agents orchestrated through LangGraph
- **Workflow States**: Layout Analysis → Planning → Content Generation → HTML Generation → Refinement → Quality Review → Assembly
- **Technologies**: Python, OpenAI GPT-4o, LangGraph, Langfuse monitoring, Azure Blob Storage
- **Output**: PowerPoint presentations with HTML visualizations

### Proposed Frontend Stack
- **Framework**: Next.js 14 (App Router)
- **Authentication**: Supabase Auth
- **Database**: Supabase (PostgreSQL)
- **UI Framework**: Tailwind CSS + shadcn/ui
- **State Management**: Zustand or Redux Toolkit
- **Real-time Updates**: Supabase Realtime subscriptions
- **HTML Rendering**: React component with iframe/sandbox
- **File Handling**: Supabase Storage

---

## Phase 1: Infrastructure Setup

### 1.1 Supabase Database Setup
**Estimated Time**: 2-3 days  
**Dependencies**: None  
**Can be done in parallel**: Yes

#### Database Schema Design

```sql
-- Users table (handled by Supabase Auth)
-- projects table
CREATE TABLE projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  topic TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft', -- draft, processing, completed, failed
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  completed_at TIMESTAMP WITH TIME ZONE,
  metadata JSONB DEFAULT '{}'::jsonb
);

-- workflow_states table
CREATE TABLE workflow_states (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  agent_name TEXT NOT NULL, -- layout_analysis, planning, content_generation, etc.
  status TEXT NOT NULL DEFAULT 'pending', -- pending, in_progress, completed, failed
  input_data JSONB,
  output_data JSONB,
  error_message TEXT,
  started_at TIMESTAMP WITH TIME ZONE,
  completed_at TIMESTAMP WITH TIME ZONE,
  execution_time_seconds INTEGER,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- slides table
CREATE TABLE slides (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  slide_number INTEGER NOT NULL,
  title TEXT,
  content JSONB NOT NULL, -- structured slide content
  html_content TEXT, -- generated HTML visualizations
  refined_html TEXT, -- refined HTML after processing
  layout_type TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- conversations table (for HTML optimization chat)
CREATE TABLE conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  slide_id UUID REFERENCES slides(id) ON DELETE CASCADE,
  messages JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- project_files table (for storing generated assets)
CREATE TABLE project_files (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  file_type TEXT NOT NULL, -- pptx, html_debug, images
  file_path TEXT NOT NULL, -- Supabase Storage path
  file_name TEXT NOT NULL,
  file_size INTEGER,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### Tasks:
- [x] **1.1.1** Create Supabase project and obtain credentials
- [x] **1.1.2** Set up database schema with all tables
- [x] **1.1.3** Configure Row Level Security (RLS) policies for all tables
- [x] **1.1.4** Set up Supabase Storage buckets for file uploads
- [x] **1.1.5** Configure database indexes for performance
- [x] **1.1.6** Set up database functions and triggers for updated_at timestamps

### 1.2 Frontend Project Setup
**Estimated Time**: 1-2 days  
**Dependencies**: 1.1.1 (Supabase credentials)  
**Can be done in parallel**: Partially (after 1.1.1)

#### Tasks:
- [x] **1.2.1** Initialize Next.js 14 project with TypeScript
- [x] **1.2.2** Install and configure Tailwind CSS + shadcn/ui
- [x] **1.2.3** Set up Supabase client configuration
- [x] **1.2.4** Configure environment variables and .env files
- [x] **1.2.5** Set up ESLint, Prettier, and development tooling
- [x] **1.2.6** Create basic project structure and folder organization
- [x] **1.2.7** Set up state management (Zustand/Redux Toolkit)

### 1.3 Backend API Integration Layer
**Estimated Time**: 2-3 days  
**Dependencies**: Existing Python backend understanding  
**Can be done in parallel**: Yes

#### Tasks:
- [x] **1.3.1** Create API endpoints in existing Python backend for frontend integration
- [x] **1.3.2** Modify workflow.py to update Supabase database during processing
- [x] **1.3.3** Add Supabase client to Python backend
- [x] **1.3.4** Create webhook/callback system for real-time status updates
- [x] **1.3.5** Implement file upload endpoints for presentations
- [x] **1.3.6** Add error handling and logging for database operations

---

## Phase 2: Authentication & Core UI

### 2.1 Authentication System ✅ **COMPLETED**
**Estimated Time**: 2-3 days  
**Dependencies**: 1.1, 1.2  
**Can be done in parallel**: No

#### Implementation Details:
- **Components**: LoginForm, RegisterForm, ResetPasswordForm, AuthLayout, ProfileForm
- **Pages**: `/login`, `/register`, `/reset-password`, `/auth/callback` (updated routing)
- **Validation**: Zod schemas with React Hook Form integration
- **State Management**: Simplified authentication system with `useSupabaseAuthSimple` hook (fixed infinite loops)
- **Security**: Password strength indicators, secure redirects, session management
- **Route Protection**: Comprehensive middleware protecting all application routes
- **Email Verification**: Secure callback handling for email confirmations
- **Smart Redirects**: Post-login redirects to intended destinations with `redirectTo` parameter
- **UX**: Professional Ekona branding, responsive design, loading states
- **Toast Notifications**: Modern feedback system using Sonner for auth actions
- **Dependencies Added**: react-hook-form@^7.60.0, @hookform/resolvers@^5.1.1, @supabase/auth-helpers-nextjs@^0.10.0, sonner
- **Profile Management**: Complete user profile editing system:
  - ProfileForm component with avatar upload functionality
  - Profile schema validation with Zod (full_name, display_name, bio, avatar_url)
  - Dedicated profile page at `/settings/profile`
  - updateProfile function in useSupabaseAuth hook
  - Integration with Supabase Auth user metadata
  - Toast notifications for profile updates

#### Route Classification System:
- **Public Routes**: `/`, `/health` - Always accessible
- **Auth Routes**: `/login`, `/register`, `/reset-password`, `/auth/callback` - Redirect authenticated users to dashboard
- **Protected Routes**: `/dashboard`, `/projects`, `/workflow`, `/settings` - Require authentication
- **Middleware**: `src/lib/supabase/middleware.ts` - Handles all route protection logic with updated route patterns

#### Tasks:
- [x] **2.1.1** Implement Supabase Auth login/register components
- [x] **2.1.2** Create protected route middleware
- [x] **2.1.3** Build login/register pages with form validation
- [x] **2.1.4** Implement password reset functionality
- [x] **2.1.5** Add user profile management components
- [x] **2.1.6** Set up authentication state management
- [x] **2.1.7** Test authentication flows and error handling

### 2.2 Main Dashboard Layout ✅ **COMPLETED**
**Estimated Time**: 3-4 days  
**Dependencies**: 2.1  
**Can be done in parallel**: No

#### Implementation Details:
- **Header Component**: Professional header with search bar, notifications, and user dropdown menu
- **Sidebar Component**: Collapsible navigation with route highlighting and "New Project" CTA
- **Mobile Navigation**: Responsive design with hamburger menu using shadcn/ui Sheet component
- **User Dropdown**: Complete menu with profile settings, account settings, help, dark mode toggle, and sign out
- **Dashboard Layout**: Integrated header and sidebar with proper responsive behavior
- **Toast Notifications**: Modern notification system using Sonner for user feedback
- **Route Integration**: Active route highlighting with Next.js usePathname
- **Simplified Auth**: Streamlined authentication system without Zustand infinite loops
- **Real-time Dashboard**: Shows actual project statistics and recent projects
- **Dependencies Added**: sonner for notifications, additional shadcn/ui components (dropdown-menu, sheet, badge, card)

#### Tasks:
- [x] **2.2.1** Create main dashboard layout with navigation
- [x] **2.2.2** Build responsive sidebar with project navigation
- [x] **2.2.3** Implement project list view with filtering/sorting
- [x] **2.2.4** Create project cards with status indicators
- [x] **2.2.5** Add search functionality for projects
- [x] **2.2.6** Implement pagination for large project lists
- [x] **2.2.7** Add user menu and settings access

### 2.3 Project Management Interface ✅ **COMPLETED**
**Estimated Time**: 4-5 days  
**Dependencies**: 2.2  
**Can be done in parallel**: No

#### Implementation Details:
- **New Project Modal**: Professional modal with topic input, validation, and Zod schemas
- **Project Detail Pages**: Individual project view with status tracking and workflow information
- **Projects List**: Complete projects page with search, filtering by status, and real-time updates
- **Status Management**: Visual status indicators (draft, processing, completed, failed) with icons
- **Real-time Updates**: Supabase subscriptions for live project updates across all pages
- **Dashboard Integration**: Recent projects displayed on dashboard with stats
- **Database Integration**: Complete Supabase setup with all required tables and RLS policies
- **Search & Filter**: Full-text search and status-based filtering functionality
- **Responsive Design**: Mobile-first approach with cards and grid layouts
- **Navigation**: Seamless navigation between dashboard, projects list, and individual projects
- **Dependencies Added**: dialog, form, textarea components from shadcn/ui

#### Tasks:
- [x] **2.3.1** Create "New Project" modal with topic input
- [x] **2.3.2** Build project detail page layout
- [x] **2.3.3** Implement project status tracking UI
- [x] **2.3.4** Add project editing capabilities (title, topic)
- [x] **2.3.5** Create project deletion with confirmation
- [x] **2.3.6** Implement project duplication functionality
- [x] **2.3.7** Add project sharing capabilities

---

## Phase 3: Workflow Progress Tracking

### 3.1 Real-time Progress Monitoring
**Estimated Time**: 5-6 days  
**Dependencies**: 1.3, 2.3  
**Can be done in parallel**: No

#### Tasks:
- [ ] **3.1.1** Create workflow progress visualization component
- [ ] **3.1.2** Implement real-time Supabase subscriptions for status updates
- [ ] **3.1.3** Build progress bar with step indicators
- [ ] **3.1.4** Add estimated time remaining calculations
- [ ] **3.1.5** Create error state handling and retry mechanisms
- [ ] **3.1.6** Implement workflow cancellation functionality
- [ ] **3.1.7** Add detailed log viewer for debugging
- [ ] **3.1.8** Create notifications system for workflow completion

### 3.2 Workflow State Visualization
**Estimated Time**: 3-4 days  
**Dependencies**: 3.1  
**Can be done in parallel**: Partially

#### Tasks:
- [ ] **3.2.1** Build agent-specific progress indicators
- [ ] **3.2.2** Create expandable sections for each workflow stage
- [ ] **3.2.3** Display input/output data for each agent
- [ ] **3.2.4** Add execution time and performance metrics
- [ ] **3.2.5** Implement error state visualization
- [ ] **3.2.6** Create workflow restart from specific stages

---

## Phase 4: Slide Content Management

### 4.1 Slide Preview System
**Estimated Time**: 4-5 days  
**Dependencies**: Phase 3  
**Can be done in parallel**: No

#### Tasks:
- [ ] **4.1.1** Create slide thumbnail generation system
- [ ] **4.1.2** Build slide list/grid view interface
- [ ] **4.1.3** Implement slide reordering functionality
- [ ] **4.1.4** Add slide selection and multi-select capabilities
- [ ] **4.1.5** Create slide deletion and duplication
- [ ] **4.1.6** Implement slide content preview modal

### 4.2 HTML Content Rendering
**Estimated Time**: 6-7 days  
**Dependencies**: 4.1  
**Can be done in parallel**: No

#### Tasks:
- [ ] **4.2.1** Create secure HTML renderer component with iframe/sandbox
- [ ] **4.2.2** Implement viewport constraints (1577x603px) preview
- [ ] **4.2.3** Add HTML element selection highlighting
- [ ] **4.2.4** Create element inspector with HTML structure
- [ ] **4.2.5** Implement click-to-select functionality
- [ ] **4.2.6** Add zoom and pan controls for detailed editing
- [ ] **4.2.7** Create responsive design for different screen sizes

### 4.3 Interactive HTML Editor
**Estimated Time**: 8-10 days  
**Dependencies**: 4.2  
**Can be done in parallel**: No

#### Tasks:
- [ ] **4.3.1** Build HTML element property editor
- [ ] **4.3.2** Create live preview with real-time updates
- [ ] **4.3.3** Implement undo/redo functionality
- [ ] **4.3.4** Add CSS style editor for selected elements
- [ ] **4.3.5** Create text content editing interface
- [ ] **4.3.6** Implement drag-and-drop for element positioning
- [ ] **4.3.7** Add copy/paste functionality between slides
- [ ] **4.3.8** Create save/revert changes functionality

---

## Phase 5: AI Agent Conversation Interface

### 5.1 Chat Interface for HTML Optimization
**Estimated Time**: 6-7 days  
**Dependencies**: 4.3  
**Can be done in parallel**: No

#### Tasks:
- [ ] **5.1.1** Create chat interface component with message history
- [ ] **5.1.2** Implement AI agent communication backend
- [ ] **5.1.3** Add context-aware conversation (current slide, selected elements)
- [ ] **5.1.4** Create message threading for complex discussions
- [ ] **5.1.5** Implement typing indicators and message status
- [ ] **5.1.6** Add conversation persistence to database
- [ ] **5.1.7** Create conversation export/import functionality

### 5.2 Smart Suggestions and Quick Actions
**Estimated Time**: 4-5 days  
**Dependencies**: 5.1  
**Can be done in parallel**: Partially

#### Tasks:
- [ ] **5.2.1** Implement quick action buttons for common requests
- [ ] **5.2.2** Create smart suggestions based on content analysis
- [ ] **5.2.3** Add one-click optimization presets
- [ ] **5.2.4** Implement auto-suggestions while typing
- [ ] **5.2.5** Create template library for common modifications
- [ ] **5.2.6** Add batch operations for multiple slides

---

## Phase 6: File Management & Export

### 6.1 File Storage Integration
**Estimated Time**: 3-4 days  
**Dependencies**: Phase 1  
**Can be done in parallel**: Yes (after Phase 1)

#### Tasks:
- [ ] **6.1.1** Implement Supabase Storage integration for presentations
- [ ] **6.1.2** Create file upload/download progress indicators
- [ ] **6.1.3** Add file versioning and history tracking
- [ ] **6.1.4** Implement automatic file cleanup and retention policies
- [ ] **6.1.5** Create file sharing and permission management
- [ ] **6.1.6** Add file size optimization and compression

### 6.2 Export and Download System
**Estimated Time**: 4-5 days  
**Dependencies**: 6.1, Phase 4  
**Can be done in parallel**: No

#### Tasks:
- [ ] **6.2.1** Create presentation download interface
- [ ] **6.2.2** Implement multiple export formats (PPTX, PDF, images)
- [ ] **6.2.3** Add custom export settings and quality options
- [ ] **6.2.4** Create batch download for multiple presentations
- [ ] **6.2.5** Implement email sharing functionality
- [ ] **6.2.6** Add watermarking and branding options
- [ ] **6.2.7** Create download history and tracking

---

## Phase 7: Advanced Features & Optimization

### 7.1 Performance Optimization
**Estimated Time**: 3-4 days  
**Dependencies**: All previous phases  
**Can be done in parallel**: No

#### Tasks:
- [ ] **7.1.1** Implement lazy loading for slide previews
- [ ] **7.1.2** Add caching strategies for API calls
- [ ] **7.1.3** Optimize bundle size and code splitting
- [ ] **7.1.4** Implement service worker for offline functionality
- [ ] **7.1.5** Add database query optimization
- [ ] **7.1.6** Create CDN integration for static assets

### 7.2 User Experience Enhancements
**Estimated Time**: 4-5 days  
**Dependencies**: All previous phases  
**Can be done in parallel**: Partially

#### Tasks:
- [ ] **7.2.1** Add keyboard shortcuts for power users
- [ ] **7.2.2** Implement drag-and-drop file uploads
- [ ] **7.2.3** Create guided tutorials and onboarding
- [ ] **7.2.4** Add dark/light theme toggle
- [ ] **7.2.5** Implement accessibility features (WCAG compliance)
- [ ] **7.2.6** Create mobile-responsive design
- [ ] **7.2.7** Add user preference persistence

### 7.3 Analytics and Monitoring
**Estimated Time**: 2-3 days  
**Dependencies**: All previous phases  
**Can be done in parallel**: Yes

#### Tasks:
- [ ] **7.3.1** Integrate analytics tracking (user behavior)
- [ ] **7.3.2** Add error monitoring and reporting
- [ ] **7.3.3** Create usage dashboards for administrators
- [ ] **7.3.4** Implement performance monitoring
- [ ] **7.3.5** Add user feedback collection system

---

## Phase 8: Testing & Deployment

### 8.1 Testing Implementation
**Estimated Time**: 5-6 days  
**Dependencies**: All development phases  
**Can be done in parallel**: Partially (unit tests during development)

#### Tasks:
- [ ] **8.1.1** Set up Jest and React Testing Library
- [ ] **8.1.2** Write unit tests for all components
- [ ] **8.1.3** Create integration tests for API endpoints
- [ ] **8.1.4** Implement end-to-end tests with Playwright
- [ ] **8.1.5** Add database migration and seeding tests
- [ ] **8.1.6** Create performance testing suite
- [ ] **8.1.7** Set up continuous integration (CI) pipeline

### 8.2 Deployment Setup
**Estimated Time**: 3-4 days  
**Dependencies**: 8.1  
**Can be done in parallel**: No

#### Tasks:
- [ ] **8.2.1** Set up production Supabase environment
- [ ] **8.2.2** Configure Vercel/Netlify deployment
- [ ] **8.2.3** Set up environment-specific configurations
- [ ] **8.2.4** Create database backup and recovery procedures
- [ ] **8.2.5** Implement SSL certificates and security headers
- [ ] **8.2.6** Set up monitoring and alerting
- [ ] **8.2.7** Create deployment documentation

---

## Technical Implementation Details

### Frontend Technology Stack

```typescript
// Core Dependencies
"dependencies": {
  "next": "^14.0.0",
  "@supabase/supabase-js": "^2.38.0",
  "@supabase/auth-helpers-nextjs": "^0.8.0",
  "react": "^18.0.0",
  "react-dom": "^18.0.0",
  "typescript": "^5.0.0",
  "tailwindcss": "^3.3.0",
  "@radix-ui/react-*": "^1.0.0", // shadcn/ui components
  "zustand": "^4.4.0", // State management
  "react-hook-form": "^7.47.0",
  "zod": "^3.22.0", // Form validation
  "react-query": "^3.39.0", // Data fetching
  "framer-motion": "^10.16.0", // Animations
  "lucide-react": "^0.292.0" // Icons
}
```

### Database Integration Patterns

```typescript
// Supabase client setup
const supabase = createClientComponentClient();

// Real-time subscriptions
const useProjectUpdates = (projectId: string) => {
  useEffect(() => {
    const subscription = supabase
      .channel(`project:${projectId}`)
      .on('postgres_changes', 
        { event: '*', schema: 'public', table: 'workflow_states' },
        (payload) => {
          // Update UI with real-time workflow progress
        }
      )
      .subscribe();

    return () => subscription.unsubscribe();
  }, [projectId]);
};
```

### Workflow State Management

```typescript
// Zustand store for workflow state
interface WorkflowStore {
  currentProject: Project | null;
  workflowStates: WorkflowState[];
  updateWorkflowState: (state: WorkflowState) => void;
  resetWorkflow: () => void;
}

const useWorkflowStore = create<WorkflowStore>((set) => ({
  currentProject: null,
  workflowStates: [],
  updateWorkflowState: (state) => 
    set((prev) => ({
      workflowStates: prev.workflowStates.map(s => 
        s.agent_name === state.agent_name ? state : s
      )
    })),
  resetWorkflow: () => set({ workflowStates: [] })
}));
```

---

## Parallel Development Blocks

### Block A: Infrastructure (Weeks 1-2)
- **Parallel Tasks**: 1.1, 1.2 (partial), 1.3, 6.1
- **Team**: Backend + DevOps + Frontend Lead

### Block B: Core UI (Weeks 3-4)
- **Sequential Tasks**: 2.1 → 2.2 → 2.3
- **Team**: Frontend Developers

### Block C: Workflow Features (Weeks 5-7)
- **Sequential Tasks**: 3.1 → 3.2 → 4.1
- **Team**: Frontend + Backend Integration

### Block D: Advanced Editing (Weeks 8-11)
- **Sequential Tasks**: 4.2 → 4.3 → 5.1 → 5.2
- **Team**: Frontend + AI Integration

### Block E: Export & Polish (Weeks 12-14)
- **Parallel Tasks**: 6.2, 7.1, 7.2 (partial)
- **Sequential Tasks**: 7.3
- **Team**: Full Team

### Block F: Testing & Deployment (Weeks 15-16)
- **Sequential Tasks**: 8.1 → 8.2
- **Team**: Full Team + QA

---

## Success Metrics

### Technical Metrics
- [ ] **Performance**: Page load times < 2 seconds
- [ ] **Reliability**: 99.9% uptime
- [ ] **Scalability**: Support 1000+ concurrent users
- [ ] **Security**: All data encrypted, GDPR compliant

### User Experience Metrics
- [ ] **Usability**: < 5 minutes to create first presentation
- [ ] **Engagement**: > 80% user retention after first use
- [ ] **Satisfaction**: > 4.5/5 user rating
- [ ] **Productivity**: 50% faster than manual slide creation

### Business Metrics
- [ ] **Adoption**: 100+ active users in first month
- [ ] **Usage**: 500+ presentations generated monthly
- [ ] **Quality**: < 5% presentations requiring manual fixes
- [ ] **Support**: < 1% support tickets requiring escalation

---

## Risk Mitigation

### Technical Risks
1. **Real-time Performance**: Implement efficient caching and optimistic updates
2. **HTML Security**: Use sandboxed iframes and content sanitization
3. **File Storage Limits**: Implement file compression and cleanup policies
4. **Database Performance**: Add proper indexing and query optimization

### User Experience Risks
1. **Complex Workflow**: Provide guided tutorials and progressive disclosure
2. **Learning Curve**: Implement contextual help and smart defaults
3. **Mobile Compatibility**: Use responsive design from the start
4. **Accessibility**: Follow WCAG guidelines throughout development

### Business Risks
1. **Scope Creep**: Maintain strict phase boundaries and MVP focus
2. **Integration Complexity**: Start with backend integration early
3. **User Adoption**: Include user feedback loops in every phase
4. **Maintenance Overhead**: Document all decisions and create maintainable code

---

## Estimated Total Timeline: 16 weeks (4 months)

**Team Composition Recommendation**:
- 1 Frontend Lead
- 2 Frontend Developers  
- 1 Backend Developer (for integration)
- 1 DevOps/Infrastructure Engineer
- 1 UI/UX Designer
- 1 QA Engineer

This comprehensive plan provides a clear roadmap for building a robust, scalable frontend application that seamlessly integrates with the existing AI-powered slide generation system while providing an exceptional user experience.