# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Backend (Python)
```bash
# Run the main slide generation CLI
python -m src.agent_main "Your Topic" --output my_presentation

# Start the FastAPI server for frontend integration
cd src && python api_server.py

# Install dependencies
pip install -r requirements.txt

# Test database connection
python test_database_connection.py

# Test file uploads
python test_file_upload.py

# Test webhook system
python test_webhook_system.py
```

### Frontend (Next.js)
```bash
cd frontend

# Development server with Turbopack
npm run dev

# Production build
npm run build

# Code quality
npm run lint
npm run lint:fix
npm run format
npm run type-check
```

### HTML Rendering Setup
Choose one HTML rendering engine:
```bash
# Playwright (recommended)
pip install playwright
playwright install chromium

# Selenium (fallback)
pip install selenium

# WeasyPrint (lightweight)
pip install weasyprint
```

## High-Level Architecture

### Agent-Based Workflow System
The core of this system is a **6-agent LangGraph workflow** that creates PowerPoint presentations:

1. **Layout Analysis Agent** (`src/agents.py`) - Analyzes PowerPoint templates and creates dynamic Pydantic models for placeholder matching
2. **Presentation Planning Agent** - Uses LLM to create intelligent slide structure with detailed specifications
3. **Content Generation Agent** - Generates contextual content with full presentation awareness 
4. **HTML Content Generation Agent** (`src/html_content_agent.py`) - Automatically detects and creates HTML visualizations for complex content
5. **HTML Refinement Agent** - Uses visual feedback to iteratively improve HTML content
6. **Slide Assembly Agent** - Creates final PowerPoint presentation with all content and formatting

### Key Technical Concepts

#### Dynamic Placeholder Dimensions
**IMPORTANT**: The system now uses **dynamic placeholder dimensions** instead of hardcoded values:
- HTML renderer functions require `width` and `height` parameters: `render_html_to_image(html_content, output_path, width, height)`
- Dimensions are extracted from PowerPoint placeholders using EMU to pixel conversion: `int(placeholder.width.emu / 9525)`
- HTML content includes viewport dimensions in body classes: `class="w-[1577px] h-[603px]"`
- When working with HTML rendering, always pass actual placeholder dimensions

#### HTML Rendering Architecture  
- **HTMLRenderer** (`src/html_renderer.py`) supports multiple engines (Playwright, Selenium, WeasyPrint)
- **HTML Content Agent** generates HTML visualizations for timelines, processes, comparisons
- **HTML Refinement Agent** uses vision models to iteratively improve visual quality
- All HTML content is rendered at 2x resolution (width*2, height*2) for crisp PowerPoint integration

#### Database Integration
- **Centralized Database Layer** (`src/database.py`) - Single Supabase client for all operations
- **Real-time Tracking** - Workflow states, project progress, HTML refinements stored in Supabase
- **File Storage** - Supabase Storage for presentations, HTML debug files, images with signed URLs
- All database operations use UUIDs, JSONB for flexible data, and Row Level Security (RLS)

#### Frontend Integration
- **Next.js 15 Frontend** (`frontend/`) with TypeScript, Tailwind CSS, shadcn/ui components
- **Real-time Updates** - Supabase Realtime subscriptions for live workflow progress
- **State Management** - Zustand stores for auth, projects, slides with persistence
- **API Integration** - FastAPI server (`src/api_server.py`) provides REST endpoints and WebSocket connections
- **Interactive Planning** - Chat-based presentation planning with outline approval triggers workflow execution

### Critical Implementation Details

#### HTML Dimension Extraction
When working with HTML refinement or rendering, always extract dimensions from HTML content:
```python
def _extract_html_dimensions(self, html_content: str) -> tuple[int, int]:
    width_match = re.search(r'w-\[(\d+)px\]', html_content)
    height_match = re.search(r'h-\[(\d+)px\]', html_content)
    if width_match and height_match:
        return int(width_match.group(1)), int(height_match.group(1))
    return 1577, 603  # Default fallback
```

#### Parallel Processing Configuration
The system supports true parallel HTML processing:
```bash
# Environment variables for parallel processing
USE_PARALLEL_HTML_CONTENT=true
USE_PARALLEL_HTML_REFINEMENT=true
```

#### Error Handling Pattern
All database operations use structured error handling:
```python
from src.database import DatabaseError, DatabaseValidationError, DatabaseConnectionError
# Operations automatically log with unique operation IDs and timing
```

## Environment Setup

### Required Environment Variables
```env
# LLM Integration
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o
OPENAI_MODEL_FAST=gpt-4o-mini

# Database
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_key

# Monitoring
LANGFUSE_PUBLIC_KEY=your_public_key
LANGFUSE_SECRET_KEY=your_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com

# Azure Storage (optional)
AZURE_STORAGE_CONNECTION_STRING=your_connection_string
AZURE_STORAGE_CONTAINER_NAME=your_container_name
```

## File Organization

### Key Directories
- **`src/`** - Core Python application with agents, workflow, API server
- **`frontend/`** - Complete Next.js application with authentication, project management, real-time UI
- **`generated_presentations/`** - Auto-generated PowerPoint files (git-ignored)
- **`html_debug/`** - HTML visualization debug files and refinement iterations (git-ignored)
- **`icon_cache/`** - Lucide icon assets for slide integration

### Template and Assets
- **`ekona_slides_template_new.pptx`** - Main PowerPoint template (version controlled)
- **`layouts_export.json`** - Template layout analysis results
- **`src/lucide-sprite.svg`** - Icon sprite definitions for HTML rendering

## Development Notes

### When Debugging HTML Issues
1. Check `html_debug/` folder for rendered images and HTML files
2. Verify dimensions are properly extracted from HTML content body classes
3. Ensure HTML renderer receives width/height parameters
4. Check Supabase Storage for HTML refinement iteration files

### When Adding New Agents
1. Inherit from base patterns in `src/agents.py`
2. Implement `execute()` method with state management
3. Add monitoring/tracing with `slide_monitor.trace_agent_execution()`
4. Update workflow graph in `src/workflow.py`

### When Working with Database
1. Always use the centralized `get_supabase_client()` from `src/database.py`
2. Follow UUID patterns for all primary keys
3. Use JSONB columns for flexible/structured data
4. Implement proper error handling with custom exception classes

### Frontend Development Workflow
1. Use existing components from `frontend/src/components/ui/` (shadcn/ui)
2. Follow the established hook patterns in `frontend/src/hooks/`
3. Maintain Zustand store patterns for state management
4. Use the established database schema and real-time subscription patterns