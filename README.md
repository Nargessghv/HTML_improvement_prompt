# PowerPoint Slide Creator

An AI-powered slide generation system using **agent-based architecture** with **unified Langfuse tracing** for comprehensive monitoring and analytics.

## 🗄️ Database Infrastructure (Completed)

### **Supabase Database Schema**
Complete relational database structure for frontend project management:

#### **`projects` Table**
```sql
id                UUID PRIMARY KEY DEFAULT gen_random_uuid()
user_id           UUID REFERENCES auth.users(id) ON DELETE CASCADE
title             TEXT NOT NULL
topic             TEXT NOT NULL
status            TEXT NOT NULL DEFAULT 'draft' -- draft, processing, completed, failed
created_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW()
updated_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW() -- Auto-updating trigger
completed_at      TIMESTAMP WITH TIME ZONE
metadata          JSONB DEFAULT '{}'::jsonb
```

#### **`workflow_states` Table**
```sql
id                      UUID PRIMARY KEY DEFAULT gen_random_uuid()
project_id              UUID REFERENCES projects(id) ON DELETE CASCADE
agent_name              TEXT NOT NULL -- layout_analysis, planning, content_generation, etc.
status                  TEXT NOT NULL DEFAULT 'pending' -- pending, in_progress, completed, failed
input_data              JSONB
output_data             JSONB
error_message           TEXT
started_at              TIMESTAMP WITH TIME ZONE
completed_at            TIMESTAMP WITH TIME ZONE
execution_time_seconds  INTEGER
created_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW()
```

#### **`slides` Table**
```sql
id            UUID PRIMARY KEY DEFAULT gen_random_uuid()
project_id    UUID REFERENCES projects(id) ON DELETE CASCADE
slide_number  INTEGER NOT NULL
title         TEXT
content       JSONB NOT NULL -- structured slide content
html_content  TEXT -- generated HTML visualizations
refined_html  TEXT -- refined HTML after processing
layout_type   TEXT
created_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW()
updated_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW() -- Auto-updating trigger
```

#### **`conversations` Table**
```sql
id          UUID PRIMARY KEY DEFAULT gen_random_uuid()
project_id  UUID REFERENCES projects(id) ON DELETE CASCADE
slide_id    UUID REFERENCES slides(id) ON DELETE CASCADE
messages    JSONB NOT NULL DEFAULT '[]'::jsonb
created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW() -- Auto-updating trigger
```

#### **`project_files` Table**
```sql
id          UUID PRIMARY KEY DEFAULT gen_random_uuid()
project_id  UUID REFERENCES projects(id) ON DELETE CASCADE
file_type   TEXT NOT NULL -- pptx, html_debug, images
file_path   TEXT NOT NULL -- Supabase Storage path
file_name   TEXT NOT NULL
file_size   INTEGER
created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
```

**Key Features:**
- UUID primary keys with proper foreign key relationships and CASCADE deletes
- JSONB columns for flexible metadata, structured content, and conversation messages
- Timestamp tracking with auto-updating `updated_at` triggers on projects, slides, conversations
- User isolation through `auth.users` references with CASCADE delete protection

### **Security Configuration**
- **Row Level Security (RLS)**: All tables protected with user-scoped policies
- **Storage Buckets**: 3 private buckets with user-folder isolation:
  - `presentations` (PPTX/PDF files, 50MB limit)
  - `html-debug` (HTML/image files, 10MB limit) 
  - `slide-images` (Preview images, 20MB limit)
- **File Access**: Signed URLs with time-limited access for security

### **Performance Optimization**
- **Database Indexes**: Optimized queries on user_id, project_id, status, timestamps
- **Auto-Triggers**: `update_updated_at_column()` function with triggers on projects, slides, conversations tables
- **JSONB Support**: Efficient storage and querying of slide content and workflow metadata

### **Real-time Capabilities**
- Supabase Realtime subscriptions ready for live workflow progress
- Workflow state changes broadcast to frontend for instant UI updates
- Agent status tracking (pending → in_progress → completed → failed)

## 🌐 Frontend Development ✅ **MAJOR MILESTONES COMPLETE**

### **Next.js 15 Frontend Application** ✨ **PRODUCTION READY**
Comprehensive React-based frontend for the AI-powered slide generation system:

**Technology Stack:**
- **Framework**: Next.js 15.4.2 with App Router and TypeScript
- **Styling**: Tailwind CSS with Ekona design system
- **UI Components**: shadcn/ui component library with custom Ekona styling
- **Authentication**: Complete Supabase Auth integration with profile management
- **Database**: Supabase PostgreSQL with real-time subscriptions
- **State Management**: Zustand with persistent stores for auth, projects, workflows
- **Forms**: React Hook Form with Zod validation schemas
- **Real-time**: Supabase Realtime for live workflow updates
- **File Storage**: Supabase Storage integration for refinement tracking
- **Development**: Comprehensive ESLint, Prettier, and TypeScript setup

**Completed Features:**
- ✅ **Complete Authentication System**: Login, register, password reset, email verification, profile management
- ✅ **Professional Dashboard**: Header, sidebar, user management, mobile-responsive navigation
- ✅ **Project Management**: Full CRUD operations with modals (create, edit, delete, duplicate, share)
- ✅ **Real-time Workflow Monitoring**: Live progress tracking for all 7 AI agents with error handling
- ✅ **HTML Refinement Visualization**: Revolutionary iteration tracking with file storage and timeline
- ✅ **Database Integration**: Complete Supabase setup with RLS policies and real-time subscriptions
- ✅ **UI/UX**: Professional Ekona branding, responsive design, toast notifications

**Project Structure:**
```
frontend/
├── src/app/                    # Next.js App Router with route groups
│   ├── (auth)/                # Authentication pages
│   ├── (dashboard)/           # Protected dashboard routes
│   └── api/                   # API routes and health checks
├── src/components/            # Feature-organized components
│   ├── ui/                   # shadcn/ui base components
│   ├── auth/                 # Authentication forms and layouts
│   ├── layout/               # Header, sidebar, navigation
│   ├── projects/             # Project management components
│   ├── workflow/             # Real-time progress tracking
│   ├── refinement/           # HTML refinement visualization
│   ├── modals/               # Reusable modal components
│   └── common/               # Shared utility components
├── src/hooks/                # Custom React hooks (auth, workflow)
├── src/stores/               # Zustand state management
├── src/lib/                  # Utilities, Supabase client, validation
├── src/schemas/              # Zod validation schemas
└── middleware.ts             # Route protection middleware
```

**Current Status:** ✅ **Phase 1-3 Complete** (44% of total roadmap)
- **Weeks 1-7**: Infrastructure, Authentication, Core UI, Workflow Monitoring ✅
- **Remaining**: Slide content management, AI conversation interface, advanced features

## 🚀 Backend API Integration (Completed)

### **FastAPI Server with Real-time Updates**
Complete REST API server for frontend integration with real-time workflow tracking and webhook system:

**Core Project Endpoints:**
- `POST /projects` - Create new slide generation project
- `GET /projects` - List user's projects with pagination
- `GET /projects/{id}` - Get specific project details  
- `GET /projects/{id}/workflow-states` - Get real-time workflow progress
- `GET /projects/{id}/slides` - Get generated slides
- `POST /projects/{id}/restart` - Restart failed workflows
- `DELETE /projects/{id}` - Delete project and related data

**Real-time Communication Endpoints:**
- `ws://localhost:8000/ws/{project_id}` - WebSocket for live updates
- `POST /webhooks/register` - Register webhook URLs for external integrations
- `POST /webhooks/test` - Test webhook delivery with sample payload
- `GET /webhooks/events` - List available webhook event types

**File Management Endpoints:**
- `POST /projects/{id}/files/upload` - Upload files (presentations, images, debug files)
- `GET /projects/{id}/files` - List project files with download URLs
- `GET /projects/{id}/files/{file_id}/download` - Download specific file
- `DELETE /projects/{id}/files/{file_id}` - Delete project file

**Security Features:**
- JWT authentication with Supabase Auth
- User-scoped data access (RLS enforcement)
- CORS configuration for frontend integration
- Background task processing with error handling

**Error Handling & Logging System:** ✨ **NEW**
- Comprehensive error classification and handling
- Structured logging with operation tracking
- Global exception handlers with appropriate HTTP status codes
- Input validation and security-aware error messages
- Performance monitoring and detailed health checks

### **Workflow Database Integration**
The existing AI workflow now automatically updates the database during execution:

**Agent Tracking:**
- `layout_analysis` - Template analysis and dynamic model creation
- `presentation_planning` - LLM-powered slide structure optimization
- `content_generation` - Contextual content with full presentation awareness
- `html_content_generation` - Intelligent HTML visualization creation
- `html_refinement` - Visual feedback and iterative improvement
- `quality_review` - Content assessment and metrics
- `slide_assembly` - Final PowerPoint presentation creation

**Real-time Updates:**
- Execution timestamps (started_at, completed_at, execution_time_seconds)
- Status progression tracking for each agent
- Error message capture and logging
- Project status management (draft → processing → completed/failed)

**Usage Example:**
```python
# API server automatically handles database updates
workflow = SlideGenerationWorkflow()
workflow.set_database_callback(update_callback, project_id)
result = workflow.run(topic="Your Topic", template_path="template.pptx")
# Real-time updates sent to frontend via Supabase subscriptions
```

### **Centralized Database Layer**
Complete Python backend integration with centralized Supabase client:

**Database Module (`src/database.py`):**
- **SupabaseClient Class**: Singleton pattern for connection management
- **Project Operations**: Full CRUD with user isolation (`create_project`, `get_project`, `update_project_status`, `delete_project`)
- **Workflow States**: Real-time tracking (`create_workflow_state`, `get_project_workflow_states`)
- **Slides Management**: Content storage (`create_slide`, `get_project_slides`, `update_slide`)
- **Conversations**: AI chat history (`create_conversation`, `add_conversation_message`)
- **File Management**: Asset tracking (`create_project_file`, `get_project_files`)
- **HTML Refinements**: Iteration tracking (`create_html_refinement`, `get_slide_refinements`, `update_refinement_as_final`)
- **Health Monitoring**: Connection validation (`health_check`)

**Backend Integration Benefits:**
- **Single Source of Truth**: All database operations centralized
- **Type Safety**: Full TypeScript-style hints and validation
- **Error Handling**: Consistent exception management across all operations
- **Performance**: Connection pooling and optimized queries
- **Maintainability**: Clean abstraction over raw Supabase calls

**Usage Example:**
```python
from src.database import get_supabase_client

# Initialize centralized client
db = get_supabase_client()

# Create project with automatic UUID and timestamps
project = db.create_project(user_id="...", title="...", topic="...")

# Track workflow progress in real-time
db.create_workflow_state(project_id, "layout_analysis", "in_progress")
db.create_workflow_state(project_id, "layout_analysis", "completed", 
                        execution_time_seconds=45)

# Store generated slides
db.create_slide(project_id, slide_number=1, content={...}, html_content="...")

# Track HTML refinement iterations
db.create_html_refinement(project_id, slide_id, iteration_number=1, 
                         html_content="...", html_file_url="...", image_file_url="...")
```

### **HTML Refinement Tracking System** ✨ **NEW**
Revolutionary system for tracking and visualizing HTML refinement iterations:

**Supabase Storage Integration (`src/supabase_storage.py`):**
- **Organized File Structure**: `project_id/slide_id/iteration_XX/` hierarchy in `html-refinements` bucket
- **Dual File Storage**: HTML files and PNG screenshots for each refinement iteration
- **Public URL Generation**: Automatic public URLs for frontend access
- **File Management**: Upload, download, and cleanup operations with error handling
- **Security**: Private bucket with RLS policies for user-scoped access

**Backend Agent Integration:**
- **HTMLRefinementAgent**: Automatic tracking of each refinement iteration during workflow
- **File Uploads**: HTML content and rendered screenshots uploaded to Supabase Storage
- **Database Records**: Complete metadata tracking with LLM feedback and execution details
- **Final Version Marking**: Identification of the final/accepted refinement iteration

**Frontend Visualization (`RefinementViewer`):**
- **Slide Selection**: Choose from slides with HTML refinements
- **Iteration Navigation**: Step through refinement progression with timeline
- **Dual View Modes**: Visual preview using screenshots OR HTML code inspection
- **Interactive Features**: Download HTML, full-screen preview, real-time refresh
- **Integration**: Automatic display on project detail pages for processing/completed projects

**Database Schema:**
```sql
-- html_refinements table
CREATE TABLE html_refinements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  slide_id UUID REFERENCES slides(id) ON DELETE CASCADE,
  iteration_number INTEGER NOT NULL DEFAULT 1,
  html_content TEXT NOT NULL,
  html_file_url TEXT,      -- Supabase Storage URL for HTML file
  image_file_url TEXT,     -- Supabase Storage URL for PNG screenshot
  refinement_feedback TEXT, -- LLM feedback/analysis
  refinement_prompt TEXT,  -- Prompt used for this iteration
  is_final BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Usage Example:**
```python
# Backend: Automatic tracking during refinement
refinement_id = db.create_html_refinement(
    project_id="uuid", slide_id="uuid", iteration_number=2,
    html_content="<html>...</html>", 
    html_file_url="https://supabase.co/storage/.../refined_html.html",
    image_file_url="https://supabase.co/storage/.../screenshot.png",
    refinement_feedback="Improved layout spacing and color contrast",
    is_final=True
)

# Frontend: Automatic visualization
// Component shows refinement progression with navigation controls
<RefinementViewer projectId={project.id} />
```

### **Real-time Webhook & WebSocket System** ✨ **NEW**
Comprehensive real-time update system for live progress tracking:

**WebSocket Endpoints:**
- `ws://localhost:8000/ws/{project_id}?token={jwt_token}` - Real-time project updates
- Automatic connection management with user authentication
- Project-specific and user-scoped message routing
- Heartbeat/ping-pong for connection health monitoring

**Webhook Management:**
- `POST /webhooks/register` - Register webhook URLs for external integrations
- `POST /webhooks/test` - Test webhook delivery with sample payload
- `GET /webhooks/events` - List available webhook event types
- Event filtering and user-specific webhook configuration

**Real-time Events:**
```json
{
  "event_type": "workflow_update",
  "project_id": "uuid",
  "agent_name": "layout_analysis", 
  "status": "completed",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "execution_time_seconds": 45,
    "slides_generated": 5
  }
}
```

**Available Event Types:**
- `workflow_update` - Agent status changes (pending → in_progress → completed/failed)
- `project_created` - New project initialization
- `project_completed` - Successful presentation generation
- `project_failed` - Generation failure with error details
- `slide_generated` - Individual slide completion
- `error_occurred` - Any error during processing

**Usage Example:**
```python
# Register webhook for external system integration
webhook_data = {
    "webhook_url": "https://your-app.com/slide-updates",
    "events": ["workflow_update", "project_completed"],
    "description": "Slack notifications"
}

# WebSocket client connection (JavaScript)
const ws = new WebSocket(`ws://localhost:8000/ws/${projectId}?token=${jwtToken}`);
ws.onmessage = (event) => {
    const update = JSON.parse(event.data);
    updateProgressUI(update);
};
```

### **File Upload & Storage System** ✨ **NEW**
Complete file management system with secure upload, download, and storage capabilities:

**Supported File Types:**
- **PowerPoint Files (pptx)**: Generated presentations (50MB max)
- **PDF Exports (pdf)**: Exported presentation files (50MB max)  
- **HTML Debug Files (html_debug)**: HTML visualizations and debug output (10MB max)
- **Images (images)**: General project images (20MB max)
- **Slide Images (slide_images)**: Slide preview thumbnails (20MB max)

**Storage Architecture:**
- **Supabase Storage Integration**: Three organized buckets with user/project isolation
  - `presentations` bucket: PPTX and PDF files
  - `html-debug` bucket: HTML debug files and visualizations
  - `slide-images` bucket: Image files and slide previews
- **Secure File Access**: Time-limited signed URLs (1-hour expiration)
- **Automatic Organization**: Files organized by `{user_id}/{project_id}/{file_type}/` structure
- **Database Tracking**: Complete file metadata stored in `project_files` table

**File Upload Features:**
```python
# Upload file with validation
POST /projects/{project_id}/files/upload
Content-Type: multipart/form-data
{
  "file": <binary_file_content>,
  "file_type": "pptx|pdf|html_debug|images|slide_images"
}

# Response includes download URL
{
  "id": "file_uuid",
  "file_name": "presentation.pptx", 
  "file_size": 2048576,
  "download_url": "https://signed.url/with/auth"
}
```

**Automatic Presentation Upload:**
- Generated presentations are automatically uploaded to storage upon completion
- Files tracked in database with metadata for easy frontend access
- Real-time updates sent when files are uploaded or processed

### **Error Handling & Monitoring System** ✨ **NEW**
Comprehensive error handling and logging infrastructure for production-ready operations:

**Database Layer Error Handling:**
- **Custom Exception Classes**: `DatabaseError`, `DatabaseValidationError`, `DatabaseConnectionError`, `DatabasePermissionError`
- **Operation Logging Decorator**: Automatic logging with unique operation IDs and timing
- **Input Validation**: UUID format, required fields, data type, and length validation
- **Enhanced Error Context**: Operation name, table, original error preservation

**API Layer Error Handling:**
```python
# Global exception handlers with appropriate HTTP status codes
DatabaseValidationError    → 400 Bad Request
DatabasePermissionError    → 403 Forbidden  
DatabaseConnectionError    → 503 Service Unavailable
DatabaseError             → 500 Internal Server Error
```

**Structured Logging:**
```python
# Example log output with operation tracking
[abc12345] Starting create_project on projects
[abc12345] Successfully completed create_project (245ms)

# Error logging with full context
[def67890] Failed get_project: {
  'operation': 'get_project',
  'table': 'projects', 
  'error_type': 'DatabaseValidationError',
  'error_message': 'Invalid UUID format for project_id'
}
```

**Enhanced Health Monitoring:**
- **Detailed Health Endpoint**: `/health` with system status, database connectivity, service status
- **Connection Validation**: Automatic health checks on initialization and periodic monitoring
- **Performance Tracking**: Request timing, operation duration, error rates
- **Service Status**: Real-time status of API, webhooks, file upload, WebSocket services

**Security-Aware Error Handling:**
- No sensitive data in error responses
- User-scoped error messages
- Detailed logging for debugging without exposing internal details
- Graceful degradation for service failures

### **Integration Architecture**
```
Frontend (Next.js) ←→ FastAPI Server ←→ Database Module ←→ Supabase Database
     ↑                      ↓              ↑                    ↓
 WebSocket/Webhooks ←→ AI Workflow ←→ Centralized Client ←→ Row Level Security
   Real-time Updates    Progress Tracking  (src/database.py)      & Auth
     ↑                      ↓                                      ↓
   File Management ←→ Supabase Storage ←→ Signed URLs ←→ Secure File Access
     ↑                      ↓                                      ↓
  Error Handling ←→ Structured Logging ←→ Health Monitoring ←→ Performance Tracking
```

## 🌟 Key Features

### **🤖 Agent-Based Architecture**
- **6 Specialized Agents**: Layout Analysis → Planning → Content Generation → **HTML Visualization** → Quality Review → Assembly
- **LangGraph Orchestration**: Coordinated workflow with error handling and retry logic
- **Unified Generation**: Single workflow system - eliminates duplicate content generation
- **Modular Design**: Each agent handles specific aspects of presentation creation

### **📊 Unified Langfuse Tracing** ✨ **NEW**
- **Single Comprehensive Trace**: Complete workflow visibility in one unified trace
- **End-to-End Monitoring**: Track all 6 agents and LLM calls in sequence
- **Enhanced Analytics**: Better insights into workflow performance and costs
- **Langchain Integration**: Uses `CallbackHandler` for proper trace unification

### **🧠 Enhanced Content Generation**
- **🆕 Unified Generation**: All slides generated in one LLM call with full presentation context for maximum coherence
- **Contextual Awareness**: Each slide generated with full presentation context
- **Presentation Outline**: Shows complete slide structure before generation
- **Dynamic Models**: Perfect placeholder matching using Pydantic models
- **Quality Assessment**: Content completeness and relevance metrics

### **🎨 Advanced Slide Creation**
- **Layout Analysis**: Automatic template analysis and dynamic model creation
- **Intelligent Planning**: LLM-powered slide structure optimization
- **Icon Integration**: Automatic icon insertion with visual elements
- **Chart Generation**: Data visualization with branded styling
- **🆕 HTML Visualizations**: Intelligent detection and generation of custom visualizations
- **🔧 Clean Icon Handling**: HTML content agent generates only icon references, renderer injects sprites

### **⚡ TRUE Parallel Processing** ✨ **NEW**
- **🚀 Parallel HTML Generation**: Multiple HTML visualizations generated simultaneously with TRUE async LLM calls
- **🔄 Parallel HTML Refinement**: All HTML slides refined in parallel for maximum performance  
- **🎯 Async LLM Client**: Native async support for genuinely concurrent LLM operations
- **⏱️ Performance Boost**: Significant time savings when generating multiple HTML visualizations
- **🔧 Configurable**: Enable/disable parallel processing via environment variables
- **🛡️ Graceful Fallback**: Automatic fallback to sequential processing if parallel fails

### **🎯 Parallel Processing Benefits**
- **HTML Content Generation**: When multiple slides need HTML visualizations, they are processed concurrently
- **HTML Refinement**: Visual feedback processing for all HTML slides happens simultaneously  
- **LLM Efficiency**: Maximizes LLM throughput by utilizing async capabilities
- **Scalability**: Performance scales with the number of HTML slides in presentation

### **📐 Viewport Constraint Enforcement** ✨ **NEW**
- **🔒 Strict Content Containment**: All HTML content MUST fit within viewport without cropping
- **📦 Mandatory DaisyUI Cards**: Every HTML visualization uses proper card structure for organization
- **⚠️ Overflow Prevention**: Automatic `overflow: hidden` enforcement to prevent scrollbars
- **📏 Height Constraints**: Mermaid diagrams limited to 400px max height for safe rendering
- **🎨 Font Size Limits**: Headers capped at `text-2xl`, body text at `text-base` for optimal space usage
- **✅ Refinement Validation**: HTML Refinement Agent specifically checks for and fixes content cropping

### **🛡️ Content Protection Features**
- **Anti-Cropping System**: Prevents information loss due to content overflow
- **Smart Layout Distribution**: CSS Grid/Flexbox ensures optimal space utilization  
- **Safe Margin Enforcement**: Minimum 20px margins on all sides for visual breathing room
- **Responsive Scaling**: Content automatically scales to fit available space
- **Visual Validation**: Refinement agent visually inspects rendered output for cropping issues

## 🎯 Enhanced Detailed Purpose Specifications ✨ **NEW**

During presentation planning, content generation, and HTML content generation, the system now uses **comprehensive detailed purpose specifications** to ensure crystal-clear alignment throughout the entire pipeline.

### **Detailed Specification Framework**
For every slide, the presentation planner generates:

- **🎯 Basic Purpose**: Clear 1-2 sentence slide objective
- **📋 Detailed Purpose**: Comprehensive 3-4 sentence explanation of what should be represented
- **🏗️ Content Structure**: Specific organization requirements (e.g., "two-column comparison", "numbered list of 5 steps")
- **🎨 Visual Elements**: Required visual components (e.g., "icons showing growth, timeline markers, comparison arrows")
- **📝 Key Information**: 3-5 essential information points that must be included
- **🖼️ HTML Requirements** *(for HTML slides)*: Specific visualization requirements (e.g., "horizontal timeline with 4 milestones, each with date, title, and description")

### **Enhanced Pipeline Flow**
```python
# Presentation Planning → Detailed Specifications Generated
slide_spec = SlideSpec(
    layout_index=3,
    slide_title="Project Timeline Overview",
    slide_purpose="Present project phases and key milestones",
    is_html=True,
    detailed_purpose="Provide comprehensive project roadmap that demonstrates structured approach...",
    content_structure="Title explaining timeline scope, horizontal timeline with clear phases",
    html_requirements="Horizontal timeline with 5 major milestones spanning 6 months...",
    visual_elements="Timeline markers, phase icons, progress indicators",
    key_information=["Discovery & Planning (Month 1)", "Development Phase (Months 2-4)", ...]
)

# Content Generation → Uses All Specifications
content_agent.generate_content(slide_spec)  # Considers all detailed specs

# HTML Generation → Implements Exact Requirements  
html_agent.generate_visualization(slide_spec)  # Follows HTML requirements precisely
```

### **Benefits of Detailed Specifications**
- **🎯 Precise Content**: Content generation follows exact requirements rather than generic instructions
- **🎨 Targeted HTML**: HTML visualizations implement specific layout and content requirements
- **🔄 Perfect Alignment**: All agents work from the same detailed plan, ensuring consistency
- **📊 Better Results**: More relevant, brand-aligned content that serves the presentation's purpose

## 🎨 HTML Content Generation Agent ✨ **NEW**

The **HTML Content Generation Agent** automatically detects when slide content would benefit from visual representation and generates stunning HTML visualizations that are rendered as ultra-high-resolution images (2560x1440 with 2x scaling) and inserted into picture placeholders.

### **Automatic Detection**
The agent intelligently identifies content that should be visualized based on:
- **Picture Placeholders**: Only processes actual picture/image placeholders (not icons)
- **Content Keywords**: Detects timelines, processes, workflows, comparisons, metrics
- **Structured Data**: Recognizes dates, sequential steps, and multi-item lists

### **Supported Visualization Types**
- **📅 Timelines**: Project phases, roadmaps, chronological events
- **🔄 Process Flows**: Step-by-step workflows, methodologies  
- **📊 Comparison Charts**: Before/after, traditional vs modern
- **📈 Infographics**: Metrics, statistics, key performance indicators
- **🗺️ Diagrams**: Relationships, hierarchies, system architecture

### **Clean Icon Handling** 🔧
The HTML Content Generation Agent now uses a **clean separation** approach for Lucide icons:

- **Content Agent**: Generates only clean icon references like `<svg><use href="#database"></use></svg>`
- **HTML Renderer**: Automatically injects Lucide sprite definitions during rendering
- **No Duplicates**: Prevents visual problems from duplicate sprite definitions
- **Automatic Cleanup**: Built-in sprite removal to ensure clean HTML output

This approach ensures optimal visual quality and eliminates icon display issues.

### **Agent Integration**
```python
# The HTML agent runs automatically in the workflow
workflow = SlideGenerationWorkflow()
results = workflow.run(
    topic="Product Development Timeline",
    template_path="template.pptx",
    output_path="presentation"
)

# Agent workflow sequence:
# 1. Layout Analysis → 2. Planning → 3. Content Generation 
# 4. HTML Visualization → 5. Quality Review → 6. Assembly
```

### **Content Examples That Trigger HTML Generation**

**Timeline Content:**
```
Our development follows this timeline:
- Q1 2024: Requirements gathering and team formation
- Q2 2024: Design phase with user experience focus  
- Q3 2024: Development sprint with agile methodology
- Q4 2024: Testing, quality assurance, and launch prep
```

**Process Flow Content:**
```
Our development process includes these steps:
1. Discovery and planning
2. Design and prototyping
3. Development and testing
4. Quality assurance
5. Deployment and monitoring
```

**Comparison Content:**
```
Performance comparison:
- Traditional approach: 73% efficiency
- Our innovative approach: 96% efficiency
- Cost reduction: 40% compared to industry standard
```

### **Professional Styling**
All HTML visualizations use:
- **Ekona Branding**: Primary color #dc261e, secondary #404040
- **Modern Design**: Clean layouts, professional typography
- **High Resolution**: Ultra-crisp 2560x1440 rendering
- **Responsive Layout**: Optimized for PowerPoint integration

## 🎨 HTML Visualizations Feature

Create beautiful timelines, process flows, and custom visualizations that are automatically rendered as **ultra-high-resolution images** (2560x1440 with 2x device scaling) and inserted into slides:

### **Timeline Example**
```python
# Content that gets detected and rendered as a timeline
timeline_content = """timeline: Product Development Roadmap
2024 Q1 - Project Kickoff
2024 Q2 - Design Phase  
2024 Q3 - Development Sprint
2024 Q4 - Launch Preparation"""

# Use in picture placeholders - automatically rendered as image
slide_content = SlideContent(
    layout_index=4,  # Title and Picture layout
    content={
        "Title 1": "Development Timeline",
        "Picture Placeholder 2": timeline_content
    }
)
```

### **Process Flow Example**
```python
process_content = """process: Customer Onboarding
Welcome & Registration
Account Setup  
Product Training
First Success Milestone"""
```

### **Custom HTML**
```python
# Full custom HTML with CSS styling
custom_html = """
<div style="text-align: center; padding: 40px;">
    <h1 style="color: #dc261e;">Custom Visualization</h1>
    <div style="display: flex; justify-content: space-around;">
        <div style="background: #f8f8f8; padding: 20px; border-radius: 10px;">
            <h3>Before</h3><p>Manual Process</p>
        </div>
        <div style="background: #dc261e; color: white; padding: 20px; border-radius: 10px;">
            <h3>After</h3><p>AI-Powered</p>
        </div>
    </div>
</div>
"""
```

### **High-Resolution Image Quality**
- **Default Resolution**: 2560x1440 (QHD) with 16:9 aspect ratio
- **Device Scaling**: 2x pixel ratio for ultra-crisp rendering  
- **Professional Quality**: Perfect for presentations and large displays
- **Multiple Options**: HD (1920x1080), Standard (1280x720) also available

### **Installation for HTML Rendering**
```bash
# Option 1: Playwright (recommended for best quality)
pip install playwright
playwright install chromium

# Option 2: Selenium (reliable fallback) 
pip install selenium
# Requires Chrome browser installed

# Option 3: WeasyPrint (lightweight)
pip install weasyprint
```

See `example_html_timeline.py` for complete working examples.

## 📁 Project Structure

```
Powerpoint Slide Creator/
├── src/                          # Core application code
│   ├── agents.py                 # AI agent implementations
│   ├── workflow.py               # LangGraph workflow orchestration
│   ├── html_content_agent.py     # HTML visualization agent
│   ├── llm_client.py            # OpenAI/LLM integration
│   └── ...                      # Other core modules
├── generated_presentations/      # Generated PPTX files (git-ignored)
│   ├── agent_generated_*.pptx   # Auto-generated presentations
│   └── tests/                   # Test outputs
├── html_debug/                  # HTML debug files (git-ignored)
├── icon_cache/                  # Cached icon assets
├── ekona_slides_template_new.pptx # PowerPoint template (tracked)
├── auto_slides.py              # Main CLI entry point
├── .gitignore                  # Excludes generated files
└── README.md                   # This file
```

**Key Folders:**
- **`generated_presentations/`** - All output PPTX files (automatically created, git-ignored)
- **`src/`** - Core application logic and AI agents
- **`html_debug/`** - HTML visualization debug files (git-ignored)
- **`icon_cache/`** - Lucide icon assets for presentations

## 🚀 Quick Start

### Using the Agent-Based Workflow (Recommended)

```bash
# Preview the agent workflow
python -m src.agent_main "Your Topic" --preview

# Generate presentation with unified tracing
python -m src.agent_main "Your Topic" --template template.pptx --output result
```

### Using TRUE Parallel Processing ✨ **NEW**

```bash
# Standard workflow (uses parallel processing by default)
python -m src.agent_main "Digital Transformation Timeline" --output my_presentation

# Force sequential processing (if needed)
USE_PARALLEL_HTML_CONTENT=false USE_PARALLEL_HTML_REFINEMENT=false python -m src.agent_main "Your Topic"
```

### Programmatic Usage with Parallel Processing

```python
import asyncio
from src.workflow import SlideGenerationWorkflow

# For maximum performance with HTML visualizations
async def generate_with_parallel_processing():
    workflow = SlideGenerationWorkflow(use_parallel_html_refinement=True)
    
    # Uses both parallel HTML generation AND parallel refinement
    result = await workflow.run_with_parallel_refinement(
        topic="Product Development Roadmap with Timeline",
        template_path="ekona_slides_template_new.pptx",
        output_path="parallel_presentation"
    )
    
    return result

# Run the async workflow
result = asyncio.run(generate_with_parallel_processing())
```

### Performance Comparison

```python
# Sequential Processing (slower)
workflow = SlideGenerationWorkflow(use_parallel_html_refinement=False)
result = workflow.run(topic="Your Topic", ...)

# Parallel Processing (faster) ✨
workflow = SlideGenerationWorkflow(use_parallel_html_refinement=True) 
result = await workflow.run_with_parallel_refinement(topic="Your Topic", ...)
```

### Environment Configuration

```env
# Enable/disable parallel processing (default: true)
USE_PARALLEL_HTML_CONTENT=true
USE_PARALLEL_HTML_REFINEMENT=true

# LLM Configuration
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o
OPENAI_MODEL_FAST=gpt-4o-mini  # Used for fast operations like icon validation
```

**📁 Output Organization**: Generated presentations are automatically saved in the `generated_presentations/` folder, which is excluded from git tracking for clean repository management.

## 📈 Monitoring & Analytics

### **Langfuse Dashboard Integration**
- **Unified Traces**: See complete workflow in single trace view
- **Agent Performance**: Track each agent's execution time and success rate
- **LLM Usage**: Comprehensive token usage and cost tracking
- **Quality Metrics**: Content completeness and relevance scores

### **What You'll See in Langfuse:**

**Before (Individual Traces):**
```
❌ OpenAI-generation (slide 1)
❌ OpenAI-generation (slide 2) 
❌ OpenAI-generation (slide 3)
```

**Now (Unified Trace):**
```
✅ slide_generation_workflow
   ├── Layout Analysis Agent
   ├── Presentation Planning Agent  
   ├── Content Generation Agent
   ├── Quality Review Agent
   └── Slide Assembly Agent
```

## 📋 PowerPoint Template & Placeholder Guidelines

### **Placeholder Naming Conventions**
The system recognizes and handles different placeholder types based on naming:

#### **Regular Content Placeholders**
- **Title placeholders**: Any name containing "Title", "Heading", "Header"
- **Body placeholders**: Any name containing "Content", "Body", "Text"
- **Picture placeholders**: Must be type 18 (PP_PLACEHOLDER.PICTURE) OR contain "Picture", "Image", "Photo" in name
- **Icon placeholders**: Must contain "icon" in name (case-insensitive) - generates icon references

#### **Special System Placeholders**

##### **🔒 LOCKED_ Placeholders**
Placeholders starting with `LOCKED_` are reserved for background system handling:
- **Naming Format**: `LOCKED_Background_1`, `LOCKED_Background_2`, etc.
- **File Requirements**: Corresponding SVG file must exist in template folder (e.g., `LOCKED_Background_1.svg`)
- **Automatic Handling**: System automatically inserts SVG backgrounds, no content generation
- **Type**: Should be Picture placeholder (type 18) in PowerPoint
- **Important**: NEVER generate content for LOCKED_ placeholders - they're handled by the background system

Example template structure:
```
templates/
├── YourTemplate/
│   ├── YourTemplate.pptx
│   ├── LOCKED_Background_1.svg  # Automatically inserted into LOCKED_Background_1 placeholder
│   └── LOCKED_Background_2.svg  # Automatically inserted into LOCKED_Background_2 placeholder
```

### **Layout Naming Best Practices**
When creating PowerPoint templates, use descriptive layout names for better agent understanding:

#### **Recommended Layout Names**
- **"Title Slide"** - Opening slide with main title
- **"Title and Content"** - Standard content slide
- **"Title and Picture"** - Slide with image placeholder
- **"Picture and Text content in multiple places"** - Mixed media layout
- **"Two Content"** - Side-by-side content areas
- **"Comparison"** - Before/after or comparative layouts
- **"Content with Caption"** - Content with descriptive text
- **"Blank"** - Minimal layout for custom content

#### **Layout Detection Keywords**
The system looks for these keywords when selecting layouts:
- **Picture layouts**: "picture", "image", "photo", "visual"
- **Content layouts**: "content", "text", "body"
- **Title layouts**: "title", "heading", "header"
- **HTML layouts**: "html", "chart", "diagram", "timeline"

### **Placeholder Type Reference**
PowerPoint placeholder types (numeric values) recognized by the system:

| Type ID | Type Name | Description | System Handling |
|---------|-----------|-------------|-----------------|
| 0 | MIXED | Mixed content | Text content |
| 1 | TITLE | Title text | Title formatting |
| 2 | BODY/OBJECT | Body content | Bullet points/paragraphs |
| 18 | PICTURE | Picture/Image | Image generation or HTML rendering |

### **Image Generation Rules**

#### **Automatic Image Detection**
Images are generated for placeholders when:
1. **Layout-based**: Placeholder is type 18 (PICTURE) AND not LOCKED_
2. **Content-based**: Content contains visual descriptions like:
   - "image of", "picture of", "photo of"
   - "shows a", "displays a", "depicts a"
   - Visual keywords: woman, man, scene, professional, medical, etc.

#### **Excluded from Image Generation**
- **LOCKED_ placeholders**: Reserved for background system
- **Icon placeholders**: Generate icon references instead
- **Text placeholders**: Types 1, 2 (TITLE, BODY)

## 🔧 Agent Workflow Details

### **1. 🔍 Layout Analysis Agent**
- Analyzes PowerPoint template layouts
- Creates dynamic Pydantic models for exact placeholder matching
- Identifies suitable layouts for different content types
- **NEW**: Automatically skips LOCKED_ placeholders from content generation

### **2. 📋 Presentation Planning Agent** 
- Uses LLM to create intelligent slide structure
- Selects optimal layouts for each slide's purpose
- Ensures logical flow and narrative coherence

### **3. ✍️ Content Generation Agent**
- Generates contextual content with full presentation awareness
- Shows complete presentation outline before generation
- Uses dynamic models for perfect placeholder alignment

### **4. 🎯 Quality Review Agent**
- Assesses content completeness and topic relevance
- Provides quality metrics and improvement suggestions
- Ensures professional presentation standards

### **5. 🔧 Slide Assembly Agent**
- Creates final PowerPoint presentation
- Applies formatting, icons, and visual elements
- Handles template mapping and content placement

## 🛠️ Requirements

```bash
pip install -r requirements.txt
```

### Environment Setup

Create a `.env` file:
```env
OPENAI_API_KEY=your_openai_api_key
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com
```

## 🔍 Troubleshooting Guide

### **Images Not Being Generated**

**Problem**: Slides describing images don't trigger image generation.

**Solutions**:
1. **Check placeholder type**: Ensure picture placeholders are type 18 in PowerPoint
2. **Verify placeholder names**: Don't start with "LOCKED_" (reserved for backgrounds)
3. **Content analysis**: Include visual keywords like "image of", "picture of", "shows a"
4. **Layout selection**: Ensure the slide uses a layout with picture placeholders

**Debug Script**:
```python
# Run debug_brochure_template.py to analyze your template
python debug_brochure_template.py
```

### **Locked Backgrounds Not Inserted**

**Problem**: LOCKED_Background placeholders show text instead of SVG backgrounds.

**Solutions**:
1. **File existence**: Verify SVG files exist in template folder (e.g., `LOCKED_Background_1.svg`)
2. **Naming match**: Ensure SVG filename matches placeholder name exactly
3. **Placeholder prefix**: Must start with "LOCKED_" to trigger background system
4. **Template structure**:
```
templates/YourTemplate/
├── YourTemplate.pptx
└── LOCKED_Background_1.svg  # Must exist!
```

### **Content in Wrong Placeholders**

**Problem**: Content appears in unexpected placeholders.

**Solutions**:
1. **Custom names**: Use descriptive placeholder names in slide master
2. **Layout analysis**: Check if layouts_info is properly initialized
3. **Dynamic models**: Verify Pydantic models match placeholder names
4. **Fallback behavior**: System uses partial name matching if exact match fails

### **Template Not Recognized Properly**

**Problem**: Agent can't identify appropriate layouts.

**Solutions**:
1. **Layout names**: Use standard names like "Title and Content", "Title and Picture"
2. **Placeholder count**: Ensure layouts have appropriate placeholders
3. **Template location**: Place templates in `templates/` folder
4. **Run analysis**:
```bash
python -m src.agent_main --analyze --template your_template.pptx
```

## 📊 Example Output

```
🚀 Starting AI-powered slide generation workflow...
✅ Unified Langfuse tracing enabled for workflow
⚡ Executing agent workflow...

🔍 layout_analyzer: Analyzed 10 layouts
📋 presentation_planner: Created plan with 5 slides
✍️ content_generator: Generated content for 5 slides
🎯 quality_reviewer: Quality review complete (100% completeness)
🔧 slide_assembler: Presentation saved to output.pptx

🎉 Agent-based presentation generation completed successfully!
📈 View detailed analytics at your Langfuse dashboard
```

## 🎯 Benefits

- **🔄 Complete Workflow Visibility**: Unified traces show entire agent flow
- **📈 Better Analytics**: Comprehensive metrics across all agents  
- **🐛 Improved Debugging**: Full context when issues occur
- **💰 Cost Tracking**: Complete token usage across workflow
- **⚡ Performance Insights**: End-to-end workflow timing
- **🤖 Agent Performance**: Individual agent success rates and bottlenecks

## 🔬 Technical Architecture

- **Framework**: LangGraph for agent orchestration
- **LLM Integration**: Langchain with OpenAI ChatGPT
- **Monitoring**: Langfuse with unified callback tracing
- **Template Processing**: python-pptx for PowerPoint manipulation
- **Content Models**: Dynamic Pydantic models for structured output

## 📝 Recent Updates

### 🔒 Latest Fixes - Placeholder & Image Generation System
- **🖼️ Fixed Picture Placeholder Detection**: Now correctly identifies type 18 (PICTURE) placeholders by numeric type
- **🔒 LOCKED_ Placeholder Handling**: System now properly skips LOCKED_ placeholders for content generation
- **🎯 Enhanced Image Generation**: Detects visual content in any layout, not just "Title and Picture"
- **📋 Dynamic Model Updates**: Pydantic models exclude LOCKED_ placeholders preventing LLM content generation
- **🔧 SlideGenerator Fix**: Both layout mapping methods now skip LOCKED_ placeholders
- **✨ Background System Integration**: SVG backgrounds properly inserted into LOCKED_ placeholders

### 🔧 Latest Bug Fixes - True Parallel Processing 
- **🚀 Parallel LLM Calls**: HTML refinement now uses TRUE parallel LLM calls (3x faster!)
- **⚡ Async LLM Processing**: Added `_get_html_correction_async()` with ThreadPoolExecutor
- **🎯 Purpose-Driven Refinement**: Rewritten prompts to focus on slide purpose fulfillment
- **🛠️ HTMLRenderer Async Fix**: Resolved Playwright sync API conflict in async contexts
- **🔄 Smart Context Detection**: Automatic async/sync detection with selenium fallback
- **✅ Enhanced Performance**: Simultaneous processing of multiple HTML slides

### ✨ Version 2.0 - Unified Tracing & Enhanced Agents
- **🎯 Unified Langfuse Tracing**: Complete workflow in single trace
- **🤖 Agent-Based Architecture**: 5 specialized agents with LangGraph
- **📊 Enhanced Monitoring**: Comprehensive analytics and performance tracking
- **🧠 Contextual Content**: Presentation-aware slide generation
- **🎨 Quality Assessment**: Content completeness and relevance metrics

---

**🚀 Ready to create intelligent presentations with unified tracing!** 