# PowerPoint Slide Creator - Complete Repository Overview

## Table of Contents
1. [System Architecture Overview](#system-architecture-overview)
2. [Agent-Based Workflow System](#agent-based-workflow-system)
3. [Database Architecture](#database-architecture)
4. [Frontend Architecture](#frontend-architecture)
5. [Key Classes and Components](#key-classes-and-components)
6. [Data Flow Diagrams](#data-flow-diagrams)
7. [File Structure](#file-structure)

## System Architecture Overview

This is an AI-powered PowerPoint slide generation system built with a **6-agent LangGraph workflow**, Next.js frontend, Python FastAPI backend, and Supabase database. The system creates presentations through intelligent content generation, HTML visualizations, image generation, and automated slide assembly.

```mermaid
graph TB
    subgraph "Frontend Layer"
        FE[Next.js Frontend]
        UI[Interactive UI Components]
        WS[WebSocket Client]
        RT[Real-time Updates]
    end
    
    subgraph "API Layer"
        API[FastAPI Server]
        REST[REST Endpoints]
        WSS[WebSocket Server]
    end
    
    subgraph "Workflow Engine"
        WF[LangGraph Workflow]
        AG[6 AI Agents]
        PAR[Parallel Processing]
    end
    
    subgraph "AI Services"
        LLM[OpenAI GPT-4]
        IMG[Image Generation]
        VIS[Vision Models]
    end
    
    subgraph "Database & Storage"
        SUP[Supabase PostgreSQL]
        STOR[Supabase Storage]
        RLS[Row Level Security]
    end
    
    subgraph "External Services"
        LF[Langfuse Monitoring]
        N8N[n8n Image Webhook]
    end
    
    FE --> API
    API --> WF
    WF --> AG
    AG --> LLM
    AG --> IMG
    AG --> VIS
    API --> SUP
    API --> STOR
    WF --> LF
    IMG --> N8N
    
    WS --> WSS
    RT --> SUP
    PAR --> AG
```

## Agent-Based Workflow System

The core of the system is a **6-agent LangGraph workflow** that processes presentations through specialized AI agents:

```mermaid
graph TD
    START([Start Workflow]) --> LA[Layout Analysis Agent]
    
    LA --> |Success| PP[Presentation Planning Agent]
    LA --> |Error| ERR[Error Handler]
    
    PP --> |Success| CG[Content Generation Agent]
    PP --> |Error| ERR
    
    CG --> |Success| HCG[HTML Content Generation Agent]
    CG --> |Error| ERR
    
    HCG --> HR[HTML Refinement Agent]
    
    HR --> |Needs Refinement| HR
    HR --> |Continue| IPG[Image Prompt Agent]
    
    IPG --> IG[Image Generation Agent]
    IG --> IR[Image Refinement Agent]
    
    IR --> |Needs Refinement| IR
    IR --> |Continue| QR[Quality Review Agent]
    
    QR --> SA[Slide Assembly Agent]
    
    SA --> |Success + No Icon Errors| END([End])
    SA --> |Success + Icon Errors| IV[Icon Validation Agent]
    SA --> |Error| ERR
    
    IV --> |Retry Needed| IRT[Icon Retry Agent]
    IV --> |No Retry Needed| END
    
    IRT --> |Success| END
    IRT --> |Error| ERR
    
    ERR --> END
    
    classDef agent fill:#e1f5fe
    classDef decision fill:#fff3e0
    classDef error fill:#ffebee
    classDef endpoint fill:#e8f5e8
    
    class LA,PP,CG,HCG,HR,IPG,IG,IR,QR,SA,IV,IRT agent
    class ERR error
    class START,END endpoint
```

### Agent Details

1. **Layout Analysis Agent** (`src/agents.py:92`) - Analyzes PowerPoint templates and creates dynamic Pydantic models
2. **Presentation Planning Agent** - Creates intelligent slide structure with detailed specifications  
3. **Content Generation Agent** - Generates contextual content with full presentation awareness
4. **HTML Content Generation Agent** (`src/html_content_agent.py`) - Creates HTML visualizations for complex content
5. **HTML Refinement Agent** - Uses visual feedback to iteratively improve HTML content
6. **Slide Assembly Agent** - Creates final PowerPoint presentation with all content and formatting

### Parallel Processing Support

The system supports parallel slide processing for improved performance:

```mermaid
graph TD
    subgraph "Standard Workflow"
        SW[Sequential Processing]
        SWA[Process Slide 1] --> SWB[Process Slide 2] --> SWC[Process Slide N]
    end
    
    subgraph "Parallel Workflow"
        PW[Parallel Processing Engine]
        PWA[Process Slide 1]
        PWB[Process Slide 2] 
        PWC[Process Slide N]
        
        PW --> PWA
        PW --> PWB
        PW --> PWC
    end
    
    ENV[Environment Variables]
    ENV --> |USE_PARALLEL_SLIDE_PROCESSING=true| PW
    ENV --> |USE_PARALLEL_HTML_CONTENT=true| PWA
    ENV --> |USE_PARALLEL_HTML_REFINEMENT=true| PWB
```

## Database Architecture

The system uses **Supabase PostgreSQL** with a comprehensive schema supporting real-time updates, user management, and workflow tracking:

```mermaid
erDiagram
    users {
        uuid id PK
        string email
        jsonb profile_data
        timestamp created_at
    }
    
    projects {
        uuid id PK
        uuid user_id FK
        string title
        string topic
        string status
        jsonb metadata
        string file_url
        timestamp created_at
        timestamp updated_at
    }
    
    workflow_states {
        uuid id PK
        uuid project_id FK
        string agent_name
        string status
        jsonb input_data
        jsonb output_data
        string error_message
        timestamp started_at
        timestamp completed_at
        integer execution_time_seconds
    }
    
    html_refinements {
        uuid id PK
        uuid project_id FK
        integer slide_number
        text html_content
        text image_url
        text pptx_file_url
        integer iteration_number
        text feedback
        string status
        timestamp created_at
    }
    
    chat_sessions {
        uuid id PK
        uuid project_id FK
        jsonb messages
        jsonb context
        jsonb presentation_outline
        timestamp created_at
        timestamp updated_at
    }
    
    slide_drafts {
        uuid id PK
        uuid project_id FK
        integer slide_number
        string title
        jsonb content
        text html_content
        text refined_html
        string status
        jsonb placeholder_info
        string layout_type
        timestamp created_at
        timestamp updated_at
    }
    
    individual_slide_files {
        uuid id PK
        uuid project_id FK
        integer slide_number
        string file_url
        string thumbnail_url
        jsonb metadata
        timestamp created_at
    }
    
    users ||--o{ projects : "owns"
    projects ||--o{ workflow_states : "tracks"
    projects ||--o{ html_refinements : "contains"
    projects ||--o{ chat_sessions : "has"
    projects ||--o{ slide_drafts : "contains"
    projects ||--o{ individual_slide_files : "generates"
```

### Key Database Features

- **Row Level Security (RLS)** - User data isolation
- **Real-time Subscriptions** - Live workflow updates
- **JSONB Storage** - Flexible structured data
- **UUID Primary Keys** - Globally unique identifiers
- **Automated Triggers** - `updated_at` timestamp management

### Database Operations

The `src/database.py` module provides a centralized client with comprehensive error handling:

```python
# Key database classes
class SupabaseClient:
    def create_project(...)
    def update_project_status(...)
    def get_project_workflow_states(...)
    def create_workflow_state(...)
    def create_html_refinement(...)

# Error handling hierarchy
DatabaseError
├── DatabaseConnectionError
├── DatabaseValidationError  
└── DatabasePermissionError
```

## Frontend Architecture

The **Next.js 15** frontend provides a modern, interactive interface with real-time updates:

```mermaid
graph TB
    subgraph "Frontend Architecture"
        subgraph "Pages & Routing"
            APP[App Router]
            DASH[Dashboard Pages]
            AUTH[Auth Pages]
            PROJ[Project Pages]
            INT[Interactive Planning]
        end
        
        subgraph "Components"
            UI[shadcn/ui Components]
            CHAT[Chat Interface]
            WF[Workflow Progress]
            SLIDES[Slide Components]
            MODALS[Modal Components]
        end
        
        subgraph "State Management"
            ZUST[Zustand Stores]
            AUTH_S[Auth Store]
            PROJ_S[Project Store] 
            SLIDE_S[Slide Store]
            WF_S[Workflow Store]
        end
        
        subgraph "Services & Hooks"
            API[API Client]
            SUPA[Supabase Client]
            HOOKS[Custom Hooks]
            WS[WebSocket Client]
        end
        
        subgraph "Real-time Features"
            RT[Realtime Subscriptions]
            NOTIF[Notifications]
            PROGRESS[Live Progress]
        end
    end
    
    APP --> DASH
    APP --> AUTH
    APP --> PROJ
    APP --> INT
    
    DASH --> UI
    CHAT --> UI
    WF --> UI
    SLIDES --> UI
    
    UI --> ZUST
    ZUST --> AUTH_S
    ZUST --> PROJ_S
    ZUST --> SLIDE_S
    ZUST --> WF_S
    
    HOOKS --> API
    HOOKS --> SUPA
    HOOKS --> WS
    
    SUPA --> RT
    RT --> NOTIF
    RT --> PROGRESS
```

### Frontend Key Features

- **Interactive Planning** - Chat-based presentation planning
- **Real-time Updates** - Live workflow progress tracking
- **Slide Management** - Individual slide editing and preview
- **Responsive Design** - Mobile-first Tailwind CSS
- **State Persistence** - Zustand with localStorage
- **Type Safety** - Full TypeScript coverage

### Key Frontend Components

```typescript
// State management
interface ProjectStore {
  projects: Project[]
  currentProject: Project | null
  setProjects: (projects: Project[]) => void
  updateProject: (id: string, updates: Partial<Project>) => void
}

// Real-time hooks
const useWorkflowManagement = (projectId: string) => {
  // WebSocket connection for live updates
  // Workflow state management
  // Progress tracking
}

const useWorkflowNotifications = () => {
  // Toast notifications
  // Status updates
  // Error handling
}
```

## Key Classes and Components

### Backend Core Classes

#### 1. SlideGenerationWorkflow (`src/workflow.py:35`)
```python
class SlideGenerationWorkflow:
    def __init__(self, use_parallel_html_refinement: bool = True)
    def run(self, topic: str, template_path: str, output_path: str, ...) -> Dict[str, Any]
    def run_streamlined_for_approved_outline(self, ...) -> Dict[str, Any]
    def run_parallel_for_approved_outline(self, ...) -> Dict[str, Any]
    
    # Agent instances
    layout_agent: LayoutAnalysisAgent
    planning_agent: PresentationPlanningAgent
    content_agent: ContentGenerationAgent
    html_content_agent: HTMLContentGenerationAgent
    refinement_agent: HTMLRefinementAgent
    assembly_agent: SlideAssemblyAgent
```

#### 2. SupabaseClient (`src/database.py`)
```python
class SupabaseClient:
    def create_project(self, user_id: str, title: str, topic: str) -> str
    def update_project_status(self, project_id: str, status: str, file_url: str = None) -> bool
    def create_workflow_state(self, project_id: str, agent_name: str, status: str, ...) -> str
    def get_project_workflow_states(self, project_id: str) -> List[Dict[str, Any]]
    def create_html_refinement(self, project_id: str, slide_number: int, ...) -> str
```

#### 3. Agent Base Classes
```python
class SlideGenerationState(TypedDict):
    # Input parameters
    topic: str
    template_path: str
    output_path: str
    
    # Workflow state
    current_step: str
    error_message: Optional[str]
    retry_count: int
    
    # Agent results
    layouts_info: Optional[Dict]
    presentation_plan: Optional[List[SlideSpec]]
    slide_contents: Optional[List[SlideContent]]
```

### Frontend Core Components

#### 1. Zustand Stores
```typescript
// Project Store
interface ProjectStore {
  projects: Project[]
  currentProject: Project | null
  filters: ProjectFilters
  pagination: PaginationState
  isLoading: boolean
  error: string | null
  selectedProjects: string[]
}

// Workflow Store  
interface WorkflowStore {
  workflowStates: WorkflowState[]
  isConnected: boolean
  connectionError: string | null
  lastUpdate: Date | null
}
```

#### 2. React Hooks
```typescript
// Workflow Management Hook
const useWorkflowManagement = (projectId: string) => {
  return {
    workflowStates: WorkflowState[],
    isConnected: boolean,
    connectionError: string | null,
    startWorkflow: () => Promise<void>,
    pauseWorkflow: () => Promise<void>,
    resumeWorkflow: () => Promise<void>
  }
}

// Supabase Auth Hook
const useSupabaseAuth = () => {
  return {
    user: User | null,
    session: Session | null,
    loading: boolean,
    signIn: (email: string, password: string) => Promise<void>,
    signOut: () => Promise<void>
  }
}
```

## Data Flow Diagrams

### 1. Presentation Creation Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant Workflow
    participant Agents
    participant Database
    participant Storage
    
    User->>Frontend: Create new presentation
    Frontend->>API: POST /api/projects
    API->>Database: Create project record
    Database-->>API: Project ID
    API-->>Frontend: Project created
    
    User->>Frontend: Start workflow
    Frontend->>API: POST /api/projects/{id}/workflow
    API->>Workflow: Initialize workflow
    
    loop Agent Execution
        Workflow->>Agents: Execute agent
        Agents->>Database: Update workflow state
        Database-->>Frontend: Real-time update
        Agents->>Storage: Save artifacts
    end
    
    Workflow->>Storage: Save final presentation
    Workflow->>Database: Mark completed
    Database-->>Frontend: Completion notification
    Frontend-->>User: Presentation ready
```

### 2. Real-time Updates Flow

```mermaid
graph LR
    subgraph "Backend Updates"
        WF[Workflow Agent] --> DB[(Database)]
        API[API Server] --> DB
        WS[WebSocket Server] --> DB
    end
    
    subgraph "Real-time Sync"
        DB --> RT[Supabase Realtime]
        RT --> SUB[Subscriptions]
    end
    
    subgraph "Frontend Updates"
        SUB --> HOOK[useWorkflowManagement]
        HOOK --> STORE[Zustand Store] 
        STORE --> UI[React Components]
        UI --> NOTIF[Toast Notifications]
    end
    
    classDef backend fill:#e3f2fd
    classDef realtime fill:#f3e5f5
    classDef frontend fill:#e8f5e8
    
    class WF,API,WS backend
    class DB,RT,SUB realtime  
    class HOOK,STORE,UI,NOTIF frontend
```

### 3. HTML Refinement Process

```mermaid
graph TD
    START[HTML Content Generated] --> CHECK{Needs Refinement?}
    
    CHECK -->|No| CONTINUE[Continue to Image Generation]
    CHECK -->|Yes| PARALLEL{Use Parallel Processing?}
    
    PARALLEL -->|No| SEQ[Sequential Refinement]
    PARALLEL -->|Yes| PAR[Parallel Refinement]
    
    subgraph "Sequential Processing"
        SEQ --> RENDER1[Render HTML to Image]
        RENDER1 --> VISION1[Vision Model Analysis]
        VISION1 --> REFINE1[Generate Refinements]
        REFINE1 --> SAVE1[Save to Database]
        SAVE1 --> ITER1{Max Iterations?}
        ITER1 -->|No| RENDER1
        ITER1 -->|Yes| CONTINUE
    end
    
    subgraph "Parallel Processing"
        PAR --> BATCH[Batch Slides]
        BATCH --> PRENDER[Parallel Render]
        PRENDER --> PVISION[Parallel Vision Analysis]
        PVISION --> PREFINE[Parallel Refinements]
        PREFINE --> PSAVE[Parallel Save]
        PSAVE --> CONTINUE
    end
    
    classDef process fill:#e1f5fe
    classDef decision fill:#fff3e0
    classDef endpoint fill:#e8f5e8
    
    class RENDER1,VISION1,REFINE1,SAVE1,PRENDER,PVISION,PREFINE,PSAVE process
    class CHECK,PARALLEL,ITER1 decision
    class START,CONTINUE endpoint
```

## File Structure

```
PowerPoint Slide Creator/
├── README.md
├── CLAUDE.md                          # Development guidelines
├── requirements.txt                   # Python dependencies
├── pyproject.toml                     # Python project config
├── ekona_slides_template_new.pptx    # PowerPoint template
├── layouts_export.json              # Template analysis cache
│
├── src/                              # Backend Python application
│   ├── workflow.py                   # Main LangGraph workflow orchestration
│   ├── agents.py                     # AI agent implementations
│   ├── database.py                   # Centralized Supabase client
│   ├── api_server.py                 # FastAPI REST server
│   ├── html_content_agent.py         # HTML visualization generation
│   ├── html_renderer.py              # Multi-engine HTML rendering
│   ├── layout_analyzer.py            # PowerPoint template analysis
│   ├── llm_client.py                # OpenAI client wrapper
│   ├── monitoring.py                # Langfuse monitoring integration
│   ├── parallel_workflow.py         # Parallel processing engine
│   ├── individual_slide_generator.py # Individual slide processing
│   ├── thumbnail_generator.py        # Slide thumbnail generation
│   └── ...                          # Additional utilities
│
├── frontend/                         # Next.js 15 application
│   ├── src/
│   │   ├── app/                      # App Router pages
│   │   │   ├── (auth)/              # Authentication pages
│   │   │   ├── (dashboard)/         # Dashboard pages
│   │   │   └── api/                 # API routes
│   │   ├── components/               # React components
│   │   │   ├── auth/                # Authentication components
│   │   │   ├── chat/                # Interactive planning
│   │   │   ├── workflow/            # Workflow progress tracking
│   │   │   ├── slides/              # Slide management
│   │   │   └── ui/                  # shadcn/ui components
│   │   ├── stores/                  # Zustand state management
│   │   │   ├── authStore.ts
│   │   │   ├── projectStore.ts
│   │   │   ├── slideStore.ts
│   │   │   └── workflowStore.ts
│   │   ├── hooks/                   # Custom React hooks
│   │   │   ├── useSupabaseAuth.ts
│   │   │   ├── useWorkflowManagement.ts
│   │   │   └── useWorkflowNotifications.ts
│   │   └── lib/                     # Utility libraries
│   │       ├── supabase/            # Supabase client configuration
│   │       └── api.ts               # API client
│   ├── package.json
│   ├── next.config.ts
│   └── tsconfig.json
│
├── database/                         # Database migrations
│   └── migrations/
│       ├── 001_add_interactive_tables.sql
│       ├── 002_add_rls_policies.sql
│       ├── 003_add_slide_status_tracking.sql
│       └── 004_add_individual_slide_files.sql
│
├── generated_presentations/          # Output PowerPoint files (git-ignored)
├── html_debug/                       # HTML refinement debug files (git-ignored)
└── icon_cache/                       # Lucide icon assets for slides
```

### Key Configuration Files

- **Environment Variables** - OpenAI, Supabase, Langfuse, Azure Storage
- **Parallel Processing** - `USE_PARALLEL_SLIDE_PROCESSING`, `USE_PARALLEL_HTML_CONTENT`, `USE_PARALLEL_HTML_REFINEMENT`
- **Template Analysis** - `layouts_export.json` caches PowerPoint template structure
- **Icon Management** - `src/lucide-sprite.svg` provides icon definitions for HTML rendering

## Summary

This PowerPoint Slide Creator is a sophisticated AI-powered system that combines:

- **Advanced AI Workflow** - 6-agent LangGraph system with specialized responsibilities
- **Real-time Frontend** - Modern Next.js interface with live progress tracking
- **Scalable Database** - Supabase with comprehensive schema and RLS
- **Parallel Processing** - Configurable concurrent slide generation
- **Visual Intelligence** - HTML rendering and vision model refinement
- **Comprehensive Monitoring** - Langfuse integration for workflow observability

The system demonstrates modern full-stack architecture with emphasis on AI workflow orchestration, real-time user experience, and scalable data management.