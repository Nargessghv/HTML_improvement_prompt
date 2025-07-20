"""
FastAPI server for frontend integration with the slide generation workflow.
Provides REST endpoints for project management and workflow execution.
"""

import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from .workflow import SlideGenerationWorkflow
from .database import get_supabase_client, SupabaseClient

# Initialize FastAPI app
app = FastAPI(
    title="Slide Creator API",
    description="API for AI-powered slide generation with real-time progress tracking",
    version="1.0.0"
)

# Add CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*.vercel.app"],  # Add your frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database client
db: SupabaseClient = get_supabase_client()

# Security
security = HTTPBearer()

# Pydantic models for API requests/responses
class ProjectCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    topic: str = Field(..., min_length=1, max_length=1000)

class ProjectResponse(BaseModel):
    id: str
    title: str
    topic: str
    status: str
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None

class WorkflowStateResponse(BaseModel):
    id: str
    agent_name: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    execution_time_seconds: Optional[int] = None
    error_message: Optional[str] = None

class SlideResponse(BaseModel):
    id: str
    slide_number: int
    title: Optional[str] = None
    layout_type: Optional[str] = None
    has_html_content: bool
    created_at: str

# Authentication helper
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Extract user from JWT token"""
    try:
        # Verify JWT token with Supabase
        user = db.client.auth.get_user(credentials.credentials)
        if not user or not user.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user.user
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid authentication")

# API Endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db_healthy = db.health_check()
    return {
        "status": "healthy" if db_healthy else "unhealthy", 
        "database": "connected" if db_healthy else "disconnected",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/projects", response_model=ProjectResponse)
async def create_project(
    request: ProjectCreateRequest,
    background_tasks: BackgroundTasks,
    user = Depends(get_current_user)
):
    """Create a new slide generation project"""
    try:
        # Create project using database client
        project = db.create_project(
            user_id=user.id,
            title=request.title,
            topic=request.topic
        )
        
        # Start workflow in background
        background_tasks.add_task(
            start_slide_generation_workflow, 
            project["id"], 
            request.topic,
            user.id
        )
        
        return ProjectResponse(**project)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating project: {str(e)}")

@app.get("/projects", response_model=List[ProjectResponse])
async def get_user_projects(
    user = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0
):
    """Get all projects for the current user"""
    try:
        projects_data = db.get_user_projects(user.id, limit, offset)
        return [ProjectResponse(**project) for project in projects_data]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching projects: {str(e)}")

@app.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    user = Depends(get_current_user)
):
    """Get a specific project"""
    try:
        project = db.get_project(project_id, user.id)
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return ProjectResponse(**project)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching project: {str(e)}")

@app.get("/projects/{project_id}/workflow-states", response_model=List[WorkflowStateResponse])
async def get_project_workflow_states(
    project_id: str,
    user = Depends(get_current_user)
):
    """Get workflow states for a project"""
    try:
        # Verify project belongs to user
        project = db.get_project(project_id, user.id)
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get workflow states
        states_data = db.get_project_workflow_states(project_id)
        return [WorkflowStateResponse(**state) for state in states_data]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching workflow states: {str(e)}")

@app.get("/projects/{project_id}/slides", response_model=List[SlideResponse])
async def get_project_slides(
    project_id: str,
    user = Depends(get_current_user)
):
    """Get slides for a project"""
    try:
        # Verify project belongs to user
        project = db.get_project(project_id, user.id)
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get slides
        slides_data = db.get_project_slides(project_id)
        
        slides = []
        for slide in slides_data:
            slides.append(SlideResponse(
                id=slide["id"],
                slide_number=slide["slide_number"],
                title=slide.get("title"),
                layout_type=slide.get("layout_type"),
                has_html_content=bool(slide.get("html_content") or slide.get("refined_html")),
                created_at=slide["created_at"]
            ))
        
        return slides
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching slides: {str(e)}")

@app.post("/projects/{project_id}/restart")
async def restart_project_workflow(
    project_id: str,
    background_tasks: BackgroundTasks,
    user = Depends(get_current_user)
):
    """Restart workflow for a project"""
    try:
        # Verify project belongs to user
        project = db.get_project(project_id, user.id)
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Update project status
        db.update_project_status(project_id, "processing")
        
        # Start workflow in background
        background_tasks.add_task(
            start_slide_generation_workflow,
            project_id,
            project["topic"],
            user.id
        )
        
        return {"message": "Workflow restarted", "project_id": project_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error restarting workflow: {str(e)}")

@app.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    user = Depends(get_current_user)
):
    """Delete a project and all related data"""
    try:
        # Delete project using database client (CASCADE will handle related records)
        success = db.delete_project(project_id, user.id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return {"message": "Project deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting project: {str(e)}")

# Background task function
async def start_slide_generation_workflow(project_id: str, topic: str, user_id: str):
    """Background task to run the slide generation workflow"""
    try:
        # Update project status to processing
        db.update_project_status(project_id, "processing")
        
        # Initialize workflow with database integration
        workflow = SlideGenerationWorkflow()
        
        # Set up paths
        template_path = "ekona_slides_template_new.pptx"
        output_path = f"generated_presentations/project_{project_id}"
        
        # Create database update callback using the centralized client
        def update_workflow_state(project_id: str, agent_name: str, status: str, **kwargs):
            db.create_workflow_state(project_id, agent_name, status, **kwargs)
        
        # Set database callback on workflow
        workflow.set_database_callback(update_workflow_state, project_id)
        
        # Run workflow
        result = workflow.run(
            topic=topic,
            template_path=template_path,
            output_path=output_path
        )
        
        if result.get("success"):
            # Update project as completed
            db.update_project_status(project_id, "completed")
            
            # Store slides data
            slide_contents = result.get("slide_contents", [])
            for i, slide_content in enumerate(slide_contents):
                db.create_slide(
                    project_id=project_id,
                    slide_number=i + 1,
                    title=slide_content.get("title"),
                    content=slide_content.content,
                    html_content=slide_content.get("html_content"),
                    refined_html=slide_content.get("refined_html"),
                    layout_type=slide_content.get("layout_type")
                )
            
        else:
            # Update project as failed
            db.update_project_status(project_id, "failed")
            
    except Exception as e:
        # Update project as failed
        db.update_project_status(project_id, "failed")
        
        # Log error to workflow_states
        db.create_workflow_state(
            project_id=project_id,
            agent_name="workflow_error",
            status="failed",
            error_message=str(e)
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)