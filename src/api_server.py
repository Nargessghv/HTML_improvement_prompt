"""
FastAPI server for frontend integration with the slide generation workflow.
Provides REST endpoints for project management and workflow execution.
"""

import asyncio
import json
import os
import mimetypes
import logging
import traceback
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Set
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, WebSocket, WebSocketDisconnect, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from pydantic import BaseModel, Field
import httpx
from supabase import create_client
from .workflow import SlideGenerationWorkflow
from .database import get_supabase_client, SupabaseClient, DatabaseError, DatabaseConnectionError, DatabaseValidationError, DatabasePermissionError
from .chat_agent import PresentationPlanningAgent, PresentationOutline

# Configure logging for API server
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create dedicated logger for API operations
api_logger = logging.getLogger('slide_creator.api')

# Initialize FastAPI app
app = FastAPI(
    title="Slide Creator API",
    description="API for AI-powered slide generation with real-time progress tracking",
    version="1.0.0"
)

# Add CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3005", "https://*.vercel.app"],  # Add your frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database client with error handling
try:
    db: SupabaseClient = get_supabase_client()
    api_logger.info("✅ Database client initialized successfully")
except Exception as e:
    api_logger.error(f"❌ Failed to initialize database client: {e}")
    raise RuntimeError(f"Database initialization failed: {e}")

# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests with timing"""
    start_time = datetime.now()
    request_id = str(uuid.uuid4())[:8]
    
    # Log request start
    api_logger.info(f"[{request_id}] {request.method} {request.url.path} - Request started")
    
    try:
        response = await call_next(request)
        
        # Calculate duration
        duration = (datetime.now() - start_time).total_seconds() * 1000
        
        # Log successful response
        api_logger.info(f"[{request_id}] {request.method} {request.url.path} - {response.status_code} ({duration:.2f}ms)")
        
        return response
        
    except Exception as e:
        # Calculate duration
        duration = (datetime.now() - start_time).total_seconds() * 1000
        
        # Log error
        api_logger.error(f"[{request_id}] {request.method} {request.url.path} - ERROR ({duration:.2f}ms): {str(e)}")
        
        # Re-raise for global handler
        raise

# Global exception handlers
@app.exception_handler(DatabaseValidationError)
async def database_validation_error_handler(request: Request, exc: DatabaseValidationError):
    """Handle database validation errors"""
    api_logger.warning(f"Validation error on {request.url.path}: {exc.message}")
    return JSONResponse(
        status_code=400,
        content={
            "error": "Validation Error", 
            "message": exc.message,
            "operation": exc.operation,
            "table": exc.table
        }
    )

@app.exception_handler(DatabasePermissionError)
async def database_permission_error_handler(request: Request, exc: DatabasePermissionError):
    """Handle database permission errors"""
    api_logger.error(f"Permission error on {request.url.path}: {exc.message}")
    return JSONResponse(
        status_code=403,
        content={
            "error": "Permission Denied", 
            "message": "You don't have permission to access this resource",
            "operation": exc.operation
        }
    )

@app.exception_handler(DatabaseConnectionError)
async def database_connection_error_handler(request: Request, exc: DatabaseConnectionError):
    """Handle database connection errors"""
    api_logger.error(f"Database connection error on {request.url.path}: {exc.message}")
    return JSONResponse(
        status_code=503,
        content={
            "error": "Service Unavailable", 
            "message": "Database service is temporarily unavailable. Please try again later.",
            "operation": exc.operation
        }
    )

@app.exception_handler(DatabaseError)
async def database_error_handler(request: Request, exc: DatabaseError):
    """Handle general database errors"""
    api_logger.error(f"Database error on {request.url.path}: {exc.message}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Database Error", 
            "message": "An internal database error occurred",
            "operation": exc.operation,
            "table": exc.table
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions"""
    api_logger.error(f"Unhandled error on {request.url.path}: {str(exc)}")
    api_logger.error(f"Traceback: {traceback.format_exc()}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please contact support if this persists."
        }
    )

# Security
security = HTTPBearer()

# WebSocket connection manager for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.project_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str, project_id: Optional[str] = None):
        await websocket.accept()
        
        # Add to user connections
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        
        # Add to project-specific connections if project_id provided
        if project_id:
            if project_id not in self.project_connections:
                self.project_connections[project_id] = set()
            self.project_connections[project_id].add(websocket)
    
    def disconnect(self, websocket: WebSocket, user_id: str, project_id: Optional[str] = None):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        if project_id and project_id in self.project_connections:
            self.project_connections[project_id].discard(websocket)
            if not self.project_connections[project_id]:
                del self.project_connections[project_id]
    
    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            dead_connections = set()
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception:
                    dead_connections.add(connection)
            
            # Clean up dead connections
            for dead_conn in dead_connections:
                self.active_connections[user_id].discard(dead_conn)
    
    async def send_project_message(self, message: dict, project_id: str):
        if project_id in self.project_connections:
            dead_connections = set()
            for connection in self.project_connections[project_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception:
                    dead_connections.add(connection)
            
            # Clean up dead connections
            for dead_conn in dead_connections:
                self.project_connections[project_id].discard(dead_conn)

manager = ConnectionManager()

# Webhook configuration
class WebhookConfig:
    def __init__(self):
        self.webhook_urls: Dict[str, str] = {}
        self.webhook_events: Dict[str, List[str]] = {}
    
    def register_webhook(self, user_id: str, webhook_url: str, events: List[str]):
        self.webhook_urls[user_id] = webhook_url
        self.webhook_events[user_id] = events
    
    def get_webhook_url(self, user_id: str) -> Optional[str]:
        return self.webhook_urls.get(user_id)
    
    def should_send_event(self, user_id: str, event_type: str) -> bool:
        events = self.webhook_events.get(user_id, [])
        return event_type in events or "all" in events

webhook_config = WebhookConfig()

# Pydantic models for API requests/responses
class ProjectCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    topic: str = Field(..., min_length=1)
    project_id: Optional[str] = None  # For starting workflow on existing project
    approved_outline: Optional[Dict[str, Any]] = None  # Approved outline from interactive planning
    template_name: Optional[str] = None  # PowerPoint template to use

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
    # New fields for individual slide files
    status: Optional[str] = None
    individual_pptx_url: Optional[str] = None
    individual_pptx_size: Optional[int] = None
    processing_time_seconds: Optional[int] = None
    error_message: Optional[str] = None

class WebhookRegistrationRequest(BaseModel):
    webhook_url: str = Field(..., pattern=r'^https?://.+')
    events: List[str] = Field(..., min_length=1)
    description: Optional[str] = None

class WebhookTestRequest(BaseModel):
    webhook_url: str = Field(..., pattern=r'^https?://.+')

class RealtimeEventResponse(BaseModel):
    event_type: str
    project_id: str
    agent_name: Optional[str] = None
    status: Optional[str] = None
    timestamp: str
    data: Optional[Dict[str, Any]] = None

class FileUploadResponse(BaseModel):
    id: str
    file_name: str
    file_type: str
    file_size: int
    file_path: str
    download_url: str
    created_at: str

class ProjectFileResponse(BaseModel):
    id: str
    file_name: str
    file_type: str
    file_size: Optional[int] = None
    created_at: str
    download_url: str

# Chat-related models
class ChatStartRequest(BaseModel):
    project_id: str
    initial_topic: str

class ChatMessageRequest(BaseModel):
    session_id: str
    message: str

class ChatMessageResponse(BaseModel):
    response: str
    outline: Optional[Dict[str, Any]] = None
    suggestions: List[str] = Field(default_factory=list)
    session_id: Optional[str] = None

class ChatSessionResponse(BaseModel):
    session_id: str
    project_id: str
    messages: List[Dict[str, Any]]
    created_at: str
    
class ChatContextResponse(BaseModel):
    chat_history: List[Dict[str, Any]]
    key_points: List[str]
    style_preferences: Dict[str, Any]
    target_audience: Optional[str] = None
    objectives: List[str]
    presentation_outline: Optional[Dict[str, Any]] = None

# Authentication helper
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Extract user from JWT token and set database context"""
    try:
        # Create a temporary client to verify the token without affecting the main client
        temp_client = create_client(
            os.getenv("SUPABASE_URL"), 
            os.getenv("SUPABASE_ANON_KEY")  # Always use anon key for token verification
        )
        
        # Verify JWT token with Supabase
        auth_response = temp_client.auth.get_user(credentials.credentials)
        
        if auth_response.user is None:
            api_logger.warning("Authentication failed: No user found for provided token")
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        
        # User context will be set per-operation when needed
        
        api_logger.info(f"User authenticated successfully: {auth_response.user.id}")
        return auth_response.user
        
    except Exception as e:
        api_logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid authentication token")

# Helper function to create slide records from outline
async def create_slide_records_from_outline(project_id: str, approved_outline: Dict[str, Any]):
    """Create slide records in database immediately when outline is approved"""
    try:
        slides_data = approved_outline.get('slides', [])
        api_logger.info(f"Creating {len(slides_data)} slide records for immediate display")
        
        for slide_spec in slides_data:
            slide_data = {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "slide_number": slide_spec.get("slide_number"),
                "title": slide_spec.get("title", "Untitled"),
                "content": slide_spec,
                "layout_type": slide_spec.get("layout_type"),
                "status": "pending"  # Initially pending, will be updated during processing
            }
            
            result = db.client.table("slides").insert(slide_data).execute()
            
            if result.data:
                api_logger.info(f"✅ Created slide record {slide_spec.get('slide_number')}: {slide_spec.get('title', 'Untitled')}")
            else:
                api_logger.error(f"❌ Failed to create slide record {slide_spec.get('slide_number')}")
                
    except Exception as e:
        api_logger.error(f"Error creating slide records from outline: {e}")
        import traceback
        traceback.print_exc()

# Real-time notification system
async def send_realtime_update(project_id: str, user_id: str, event_type: str, **kwargs):
    """Send real-time updates via WebSocket and webhooks"""
    
    event_data = RealtimeEventResponse(
        event_type=event_type,
        project_id=project_id,
        agent_name=kwargs.get("agent_name"),
        status=kwargs.get("status"),
        timestamp=datetime.now().isoformat(),
        data=kwargs.get("data", {})
    )
    
    # Send WebSocket update
    await manager.send_project_message(event_data.dict(), project_id)
    await manager.send_personal_message(event_data.dict(), user_id)
    
    # Send webhook if configured
    webhook_url = webhook_config.get_webhook_url(user_id)
    if webhook_url and webhook_config.should_send_event(user_id, event_type):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                await client.post(
                    webhook_url,
                    json=event_data.dict(),
                    headers={"Content-Type": "application/json"}
                )
        except Exception as e:
            print(f"Webhook delivery failed for {webhook_url}: {e}")

# Enhanced callback for real-time updates
def create_realtime_callback(project_id: str, user_id: str):
    """Create callback function for real-time workflow updates"""
    
    def update_callback(project_id: str, agent_name: str, status: str, **kwargs):
        # Update or create workflow state in database
        try:
            # First, try to find existing workflow state for this agent
            existing_states = db.get_project_workflow_states(project_id)
            existing_state = next((state for state in existing_states if state["agent_name"] == agent_name), None)
            
            if existing_state:
                # Update existing state
                api_logger.info(f"Updating existing workflow state for {agent_name}: {status}")
                db.update_workflow_state(existing_state["id"], status, **kwargs)
            else:
                # Create new state
                api_logger.info(f"Creating new workflow state for {agent_name}: {status}")
                db.create_workflow_state(project_id, agent_name, status, **kwargs)
                
        except Exception as e:
            api_logger.error(f"Error updating workflow state for {agent_name}: {e}")
            # Fallback to create (original behavior)
            db.create_workflow_state(project_id, agent_name, status, **kwargs)
        
        # Send real-time updates
        asyncio.create_task(send_realtime_update(
            project_id=project_id,
            user_id=user_id,
            event_type="workflow_update",
            agent_name=agent_name,
            status=status,
            data=kwargs
        ))
    
    return update_callback

# API Endpoints

@app.get("/health")
async def health_check():
    """Enhanced health check endpoint with detailed status"""
    try:
        # Check database health
        db_healthy = db.health_check()
        
        # Get detailed connection info
        connection_info = db.get_connection_info()
        
        # Determine overall health
        overall_status = "healthy" if db_healthy else "unhealthy"
        
        health_data = {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "database": {
                "status": "connected" if db_healthy else "disconnected",
                "url": connection_info.get("supabase_url", "").split("//")[1].split(".")[0] if connection_info.get("supabase_url") else "unknown",
                "has_client": connection_info.get("has_client", False)
            },
            "services": {
                "api_server": "operational",
                "webhook_system": "operational", 
                "file_upload": "operational",
                "websockets": "operational"
            }
        }
        
        # Log health check
        if db_healthy:
            api_logger.info("✅ Health check passed - all systems operational")
        else:
            api_logger.warning("⚠️ Health check failed - database connection issues")
        
        return health_data
        
    except Exception as e:
        api_logger.error(f"❌ Health check error: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": "Health check failed",
            "database": {"status": "error"},
            "services": {"api_server": "error"}
        }

@app.websocket("/ws/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str, token: str):
    """Enhanced WebSocket endpoint for real-time project updates and interactive features"""
    try:
        # Verify authentication
        user = db.client.auth.get_user(token)
        if not user or not user.user:
            await websocket.close(code=1008, reason="Unauthorized")
            return
        
        user_id = user.user.id
        
        # Verify project access
        project = db.get_project(project_id, user_id)
        if not project:
            await websocket.close(code=1008, reason="Project not found")
            return
        
        await manager.connect(websocket, user_id, project_id)
        
        # Send initial state including new interactive features
        workflow_states = db.get_project_workflow_states(project_id)
        
        # Get slide drafts if any
        slide_drafts_result = db.client.table("slide_drafts").select("*").eq(
            "project_id", project_id
        ).order("slide_number").execute()
        
        # Get chat sessions
        chat_sessions_result = db.client.table("chat_sessions").select("id, created_at").eq(
            "project_id", project_id
        ).order("created_at", desc=True).limit(1).execute()
        
        await websocket.send_text(json.dumps({
            "event_type": "initial_state",
            "project_id": project_id,
            "workflow_states": workflow_states,
            "project_status": project["status"],
            "slide_drafts": slide_drafts_result.data or [],
            "has_chat_session": len(chat_sessions_result.data) > 0,
            "chat_session_id": chat_sessions_result.data[0]["id"] if chat_sessions_result.data else None
        }))
        
        try:
            while True:
                # Handle incoming messages
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "event_type": "pong",
                        "timestamp": datetime.now().isoformat()
                    }))
                
                elif message.get("type") == "generate_slide":
                    # Queue slide generation
                    slide_number = message.get("slide_number")
                    await websocket.send_text(json.dumps({
                        "event_type": "slide_generation_queued",
                        "slide_number": slide_number,
                        "timestamp": datetime.now().isoformat()
                    }))
                    # TODO: Trigger actual slide generation
                
                elif message.get("type") == "edit_slide":
                    # Handle slide edit request
                    slide_id = message.get("slide_id")
                    edit_request = message.get("request")
                    
                    # Create edit request in database
                    edit_result = db.client.table("slide_edit_requests").insert({
                        "slide_draft_id": slide_id,
                        "user_id": user_id,
                        "request_type": edit_request.get("type", "content"),
                        "request_details": edit_request,
                        "status": "pending"
                    }).execute()
                    
                    await websocket.send_text(json.dumps({
                        "event_type": "edit_request_created",
                        "edit_request_id": edit_result.data[0]["id"],
                        "slide_id": slide_id,
                        "timestamp": datetime.now().isoformat()
                    }))
                
                elif message.get("type") == "approve_slide":
                    # Handle slide approval
                    slide_id = message.get("slide_id")
                    db.client.table("slide_drafts").update({
                        "status": "approved"
                    }).eq("id", slide_id).execute()
                    
                    await websocket.send_text(json.dumps({
                        "event_type": "slide_approved",
                        "slide_id": slide_id,
                        "timestamp": datetime.now().isoformat()
                    }))
                    
        except WebSocketDisconnect:
            pass
    except Exception as e:
        api_logger.error(f"WebSocket error: {e}")
        await websocket.close(code=1011, reason="Internal error")
    finally:
        manager.disconnect(websocket, user_id, project_id)

@app.post("/webhooks/register")
async def register_webhook(
    request: WebhookRegistrationRequest,
    user = Depends(get_current_user)
):
    """Register a webhook URL for real-time updates"""
    try:
        webhook_config.register_webhook(
            user_id=user.id,
            webhook_url=request.webhook_url,
            events=request.events
        )
        
        return {
            "message": "Webhook registered successfully",
            "webhook_url": request.webhook_url,
            "events": request.events
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error registering webhook: {str(e)}")

@app.post("/webhooks/test")
async def test_webhook(
    request: WebhookTestRequest,
    user = Depends(get_current_user)
):
    """Test webhook delivery"""
    try:
        test_payload = {
            "event_type": "webhook_test",
            "project_id": "test",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "message": "This is a test webhook delivery",
                "user_id": user.id
            }
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                request.webhook_url,
                json=test_payload,
                headers={"Content-Type": "application/json"}
            )
            
            return {
                "message": "Webhook test sent",
                "status_code": response.status_code,
                "response_text": response.text[:200] if response.text else None
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook test failed: {str(e)}")

@app.get("/webhooks/events")
async def get_webhook_events():
    """Get list of available webhook events"""
    return {
        "available_events": [
            "workflow_update",
            "project_created",
            "project_completed",
            "project_failed",
            "slide_generated",
            "error_occurred",
            "all"
        ],
        "event_descriptions": {
            "workflow_update": "Sent when any agent in the workflow updates status",
            "project_created": "Sent when a new project is created",
            "project_completed": "Sent when project generation completes successfully",
            "project_failed": "Sent when project generation fails",
            "slide_generated": "Sent when individual slides are generated",
            "error_occurred": "Sent when any error occurs during processing",
            "all": "Subscribe to all events"
        }
    }

@app.post("/projects", response_model=ProjectResponse)
async def create_or_start_project(
    request: ProjectCreateRequest,
    background_tasks: BackgroundTasks,
    user = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a new project OR start workflow on existing project"""
    try:
        project = None
        event_type = "project_created"
        
        if request.project_id:
            # Frontend is requesting to start workflow on existing project
            api_logger.info(f"Starting workflow on existing project: {request.project_id}")
            
            # Verify project exists and belongs to user
            project = db.get_project(request.project_id, user.id, credentials.credentials)
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")
            
            # Update project status to processing
            db.update_project_status(request.project_id, "processing")
            project["status"] = "processing"
            
            event_type = "workflow_started"
            api_logger.info(f"Updated existing project {request.project_id} to processing status")
            
        else:
            # Create new project
            api_logger.info(f"Creating new project: {request.title}")
            project = db.create_project(
                user_id=user.id,
                title=request.title,
                topic=request.topic,
                jwt_token=credentials.credentials
            )
            api_logger.info(f"Created new project with ID: {project['id']}")
        
        # Send appropriate event
        await send_realtime_update(
            project_id=project["id"],
            user_id=user.id,
            event_type=event_type,
            data={"title": request.title, "topic": request.topic}
        )
        
        # Start workflow in background
        background_tasks.add_task(
            start_slide_generation_workflow, 
            project["id"], 
            project["topic"],  # Use topic from database
            user.id,
            request.approved_outline,  # Pass approved outline to workflow
            request.template_name  # Pass template selection
        )
        
        api_logger.info(f"Workflow background task started for project: {project['id']}")
        return ProjectResponse(**project)
        
    except HTTPException:
        raise
    except Exception as e:
        api_logger.error(f"Error in create_or_start_project: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing project: {str(e)}")

@app.get("/projects", response_model=List[ProjectResponse])
async def get_user_projects(
    user = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    limit: int = 50,
    offset: int = 0
):
    """Get all projects for the current user"""
    try:
        projects_data = db.get_user_projects(user.id, limit, offset, credentials.credentials)
        return [ProjectResponse(**project) for project in projects_data]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching projects: {str(e)}")

@app.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    user = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get a specific project"""
    try:
        project = db.get_project(project_id, user.id, credentials.credentials)
        
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
    """Get slides for a project with file information"""
    try:
        # Verify project belongs to user
        project = db.get_project(project_id, user.id)
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get slides with enhanced status information
        slides_data = db.get_project_slides_with_status(project_id)
        
        slides = []
        for slide in slides_data:
            slides.append(SlideResponse(
                id=slide["id"],
                slide_number=slide["slide_number"],
                title=slide.get("title"),
                layout_type=slide.get("layout_type"),
                has_html_content=bool(slide.get("html_content") or slide.get("refined_html")),
                created_at=slide["created_at"],
                # Add new fields for individual slide files
                status=slide.get("status", "pending"),
                individual_pptx_url=slide.get("individual_pptx_url"),
                individual_pptx_size=slide.get("individual_pptx_size"),
                processing_time_seconds=slide.get("processing_time_seconds"),
                error_message=slide.get("error_message")
            ))
        
        return slides
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching slides: {str(e)}")

@app.get("/projects/{project_id}/slides/{slide_id}")
async def get_slide_details(
    project_id: str,
    slide_id: str,
    user = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get detailed information about a specific slide including files"""
    try:
        # Verify project belongs to user
        project = db.get_project(project_id, user.id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get slide details
        slide = db.get_slide_details(slide_id, credentials.credentials)
        if not slide or slide["project_id"] != project_id:
            raise HTTPException(status_code=404, detail="Slide not found")
        
        # Get slide files - use authenticated client for RLS
        user_client = db.create_user_client(credentials.credentials) if credentials.credentials and not db.using_service_role else db.client
        files_result = user_client.table("slide_files")\
            .select("*")\
            .eq("slide_id", slide_id)\
            .order("created_at", desc=True)\
            .execute()
        
        files = files_result.data if files_result.data else []
        
        # Refresh expired URLs
        for file_record in files:
            try:
                expires_at_str = file_record.get("expires_at")
                if expires_at_str:
                    # Handle different datetime formats
                    if isinstance(expires_at_str, str):
                        # Convert UTC Z format to +00:00 format for fromisoformat
                        if expires_at_str.endswith('Z'):
                            expires_at_str = expires_at_str.replace('Z', '+00:00')
                        elif not expires_at_str.endswith('+00:00') and not expires_at_str.endswith('-00:00'):
                            # Add timezone if missing
                            expires_at_str = expires_at_str + '+00:00'
                    
                    expires_at = datetime.fromisoformat(expires_at_str)
                    # Use timezone-aware comparison
                    now = datetime.now()
                    if expires_at.tzinfo is not None:
                        # Make now timezone-aware for comparison
                        now = datetime.now(timezone.utc)
                    
                    if expires_at < now:
                        # Generate new signed URL
                        try:
                            signed_url_result = user_client.storage.from_("presentations").create_signed_url(
                                path=file_record["file_path"],
                                expires_in=86400  # 24 hours
                            )
                            
                            if signed_url_result and signed_url_result.get('signedURL'):
                                new_url = signed_url_result['signedURL']
                                # Use timezone-aware datetime for expiry
                                new_expiry = datetime.now(timezone.utc) + timedelta(hours=24)
                                
                                # Update database
                                user_client.table("slide_files").update({
                                    "file_url": new_url,
                                    "expires_at": new_expiry.isoformat()
                                }).eq("id", file_record["id"]).execute()
                                
                                # Update in-memory data
                                file_record["file_url"] = new_url
                                file_record["expires_at"] = new_expiry.isoformat()
                                
                        except Exception as e:
                            api_logger.warning(f"Failed to refresh signed URL for file {file_record['id']}: {e}")
            except Exception as e:
                api_logger.warning(f"Failed to parse expires_at for file {file_record.get('id', 'unknown')}: {e}")
                # Continue with the next file record without failing the entire request
        
        return {
            "slide": slide,
            "files": files
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching slide details: {str(e)}")

@app.get("/projects/{project_id}/slides/{slide_id}/download")
async def download_individual_slide(
    project_id: str,
    slide_id: str,
    user = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Download individual slide PPTX file"""
    try:
        # Verify project belongs to user
        project = db.get_project(project_id, user.id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get slide with PPTX file
        slide = db.get_slide_details(slide_id, credentials.credentials)
        if not slide or slide["project_id"] != project_id:
            raise HTTPException(status_code=404, detail="Slide not found")
        
        if not slide.get("individual_pptx_path"):
            raise HTTPException(status_code=404, detail="Individual PPTX file not available")
        
        # Generate fresh signed URL for download
        signed_url_result = db.client.storage.from_("presentations").create_signed_url(
            path=slide["individual_pptx_path"],
            expires_in=300  # 5 minutes for download
        )
        
        if not signed_url_result or not signed_url_result.get('signedURL'):
            raise HTTPException(status_code=500, detail="Failed to generate download URL")
        
        # Return redirect to signed URL
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=signed_url_result['signedURL'])
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading slide: {str(e)}")

@app.post("/projects/{project_id}/slides/{slide_id}/refresh-url")
async def refresh_slide_url(
    project_id: str,
    slide_id: str,
    user = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Refresh expired signed URL for a slide file"""
    try:
        # Verify project belongs to user
        project = db.get_project(project_id, user.id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get slide details
        slide = db.get_slide_details(slide_id, credentials.credentials)
        if not slide or slide["project_id"] != project_id:
            raise HTTPException(status_code=404, detail="Slide not found")
        
        if not slide.get("individual_pptx_path"):
            raise HTTPException(status_code=404, detail="No file to refresh")
        
        # Generate new signed URL
        signed_url_result = db.client.storage.from_("presentations").create_signed_url(
            path=slide["individual_pptx_path"],
            expires_in=86400  # 24 hours
        )
        
        if not signed_url_result or not signed_url_result.get('signedURL'):
            raise HTTPException(status_code=500, detail="Failed to generate signed URL")
        
        new_url = signed_url_result['signedURL']
        new_expiry = datetime.now() + timedelta(hours=24)
        
        # Update slide record
        db.client.table("slides").update({
            "individual_pptx_url": new_url,
            "updated_at": datetime.now().isoformat()
        }).eq("id", slide_id).execute()
        
        # Update slide files record
        db.client.table("slide_files").update({
            "file_url": new_url,
            "expires_at": new_expiry.isoformat(),
            "updated_at": datetime.now().isoformat()
        }).eq("slide_id", slide_id).eq("file_type", "individual_pptx").execute()
        
        return {
            "success": True,
            "new_url": new_url,
            "expires_at": new_expiry.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refreshing URL: {str(e)}")

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
            user.id,
            None,  # No approved outline for restart
            None   # Use default template for restart
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

# File management endpoints

@app.post("/projects/{project_id}/files/upload", response_model=FileUploadResponse)
async def upload_project_file(
    project_id: str,
    file: UploadFile = File(...),
    file_type: str = Form(...),
    user = Depends(get_current_user)
):
    """Upload a file for a project (presentations, images, debug files)"""
    try:
        # Verify project belongs to user
        project = db.get_project(project_id, user.id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Validate file type
        allowed_types = ["pptx", "pdf", "html_debug", "images", "slide_images"]
        if file_type not in allowed_types:
            raise HTTPException(status_code=400, detail=f"Invalid file_type. Must be one of: {allowed_types}")
        
        # Validate file size limits based on type
        file_size_limits = {
            "pptx": 50 * 1024 * 1024,      # 50MB for presentations
            "pdf": 50 * 1024 * 1024,       # 50MB for PDF exports
            "html_debug": 10 * 1024 * 1024, # 10MB for HTML debug files
            "images": 20 * 1024 * 1024,     # 20MB for images
            "slide_images": 20 * 1024 * 1024 # 20MB for slide preview images
        }
        
        # Read file content to get size
        file_content = await file.read()
        file_size = len(file_content)
        
        if file_size > file_size_limits.get(file_type, 10 * 1024 * 1024):
            raise HTTPException(
                status_code=413, 
                detail=f"File too large. Maximum size for {file_type}: {file_size_limits.get(file_type) // (1024*1024)}MB"
            )
        
        # Create unique file path for Supabase Storage
        # Format: {user_id}/{project_id}/{file_type}/{timestamp}_{filename}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = "".join(c for c in file.filename if c.isalnum() or c in "._-")
        storage_path = f"{user.id}/{project_id}/{file_type}/{timestamp}_{safe_filename}"
        
        # Upload to Supabase Storage
        bucket_name = _get_storage_bucket_for_type(file_type)
        upload_result = db.client.storage.from_(bucket_name).upload(
            path=storage_path,
            file=file_content,
            file_options={
                "content-type": file.content_type or mimetypes.guess_type(file.filename)[0] or "application/octet-stream"
            }
        )
        
        # Check upload result - handle different Supabase response formats
        upload_error = None
        if hasattr(upload_result, 'error') and upload_result.error:
            upload_error = str(upload_result.error)
        elif isinstance(upload_result, dict) and upload_result.get("error"):
            upload_error = str(upload_result["error"])
        
        if upload_error:
            raise HTTPException(status_code=500, detail=f"Storage upload failed: {upload_error}")
        
        # Create file record in database
        file_record = db.create_project_file(
            project_id=project_id,
            file_type=file_type,
            file_path=storage_path,
            file_name=file.filename,
            file_size=file_size
        )
        
        # Generate signed download URL (valid for 1 hour)
        download_url_result = db.client.storage.from_(bucket_name).create_signed_url(
            path=storage_path,
            expires_in=3600  # 1 hour
        )
        
        download_url = download_url_result.get("signedURL", "")
        
        return FileUploadResponse(
            id=file_record["id"],
            file_name=file_record["file_name"],
            file_type=file_record["file_type"],
            file_size=file_record["file_size"],
            file_path=file_record["file_path"],
            download_url=download_url,
            created_at=file_record["created_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

@app.get("/projects/{project_id}/files", response_model=List[ProjectFileResponse])
async def get_project_files(
    project_id: str,
    file_type: Optional[str] = None,
    user = Depends(get_current_user)
):
    """Get all files for a project, optionally filtered by type"""
    try:
        # Verify project belongs to user
        project = db.get_project(project_id, user.id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get file records from database
        files_data = db.get_project_files(project_id, file_type)
        
        files = []
        for file_data in files_data:
            # Generate signed download URL for each file
            bucket_name = _get_storage_bucket_for_type(file_data["file_type"])
            download_url_result = db.client.storage.from_(bucket_name).create_signed_url(
                path=file_data["file_path"],
                expires_in=3600  # 1 hour
            )
            
            download_url = download_url_result.get("signedURL", "")
            
            files.append(ProjectFileResponse(
                id=file_data["id"],
                file_name=file_data["file_name"],
                file_type=file_data["file_type"],
                file_size=file_data.get("file_size"),
                created_at=file_data["created_at"],
                download_url=download_url
            ))
        
        return files
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching files: {str(e)}")

@app.get("/projects/{project_id}/files/{file_id}/download")
async def download_project_file(
    project_id: str,
    file_id: str,
    user = Depends(get_current_user)
):
    """Download a specific project file"""
    try:
        # Verify project belongs to user
        project = db.get_project(project_id, user.id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get file record
        files = db.get_project_files(project_id)
        file_record = next((f for f in files if f["id"] == file_id), None)
        
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Download from Supabase Storage
        bucket_name = _get_storage_bucket_for_type(file_record["file_type"])
        download_result = db.client.storage.from_(bucket_name).download(file_record["file_path"])
        
        if not download_result:
            raise HTTPException(status_code=404, detail="File not found in storage")
        
        # Determine content type
        content_type = mimetypes.guess_type(file_record["file_name"])[0] or "application/octet-stream"
        
        # Return file as streaming response
        def generate():
            yield download_result
        
        return StreamingResponse(
            generate(),
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename=\"{file_record['file_name']}\"",
                "Content-Length": str(file_record.get("file_size", len(download_result)))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading file: {str(e)}")

@app.delete("/projects/{project_id}/files/{file_id}")
async def delete_project_file(
    project_id: str,
    file_id: str,
    user = Depends(get_current_user)
):
    """Delete a specific project file"""
    try:
        # Verify project belongs to user
        project = db.get_project(project_id, user.id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get file record
        files = db.get_project_files(project_id)
        file_record = next((f for f in files if f["id"] == file_id), None)
        
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Delete from Supabase Storage
        bucket_name = _get_storage_bucket_for_type(file_record["file_type"])
        delete_result = db.client.storage.from_(bucket_name).remove([file_record["file_path"]])
        
        # Delete from database (even if storage deletion fails)
        db_delete_result = db.client.table("project_files").delete().eq("id", file_id).execute()
        
        return {"message": "File deleted successfully", "file_name": file_record["file_name"]}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")

def _get_storage_bucket_for_type(file_type: str) -> str:
    """Get the appropriate Supabase Storage bucket for a file type"""
    bucket_mapping = {
        "pptx": "presentations",
        "pdf": "presentations", 
        "html_debug": "html-debug",
        "images": "slide-images",
        "slide_images": "slide-images"
    }
    return bucket_mapping.get(file_type, "presentations")

# Chat endpoints for interactive presentation planning

# Initialize chat agent
chat_agent = PresentationPlanningAgent()

@app.post("/chat/start", response_model=ChatMessageResponse)
async def start_chat_session(
    request: ChatStartRequest,
    user = Depends(get_current_user)
):
    """Start a new chat session for presentation planning"""
    try:
        # Verify project belongs to user
        project = db.get_project(request.project_id, user.id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Start chat session
        result = await chat_agent.start_session(
            project_id=request.project_id,
            initial_topic=request.initial_topic
        )
        
        # Update project topic if different
        if project["topic"] != request.initial_topic:
            db.client.table("projects").update({
                "topic": request.initial_topic
            }).eq("id", request.project_id).execute()
        
        return ChatMessageResponse(
            response=result["response"],
            suggestions=result["suggestions"],
            session_id=result["session_id"]
        )
        
    except Exception as e:
        api_logger.error(f"Error starting chat session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error starting chat session: {str(e)}")

@app.post("/chat/message", response_model=ChatMessageResponse)
async def send_chat_message(
    request: ChatMessageRequest,
    user = Depends(get_current_user)
):
    """Send a message to the chat agent"""
    try:
        # Verify session belongs to user's project
        session_result = db.client.table("chat_sessions").select("project_id").eq(
            "id", request.session_id
        ).execute()
        
        if not session_result.data:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        project_id = session_result.data[0]["project_id"]
        project = db.get_project(project_id, user.id)
        if not project:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Process message
        result = await chat_agent.send_message(
            session_id=request.session_id,
            message=request.message
        )
        
        # Send real-time update if outline generated
        if result.get("outline"):
            await send_realtime_update(
                project_id=project_id,
                user_id=user.id,
                event_type="outline_generated",
                data={"outline": result["outline"]}
            )
        
        return ChatMessageResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        api_logger.error(f"Error processing chat message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

@app.get("/api/chat/{session_id}/context", response_model=ChatContextResponse)
async def get_chat_context(
    session_id: str,
    user = Depends(get_current_user)
):
    """Get chat context for downstream agents"""
    try:
        # Verify session belongs to user's project
        session_result = db.client.table("chat_sessions").select("project_id").eq(
            "id", session_id
        ).execute()
        
        if not session_result.data:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        project_id = session_result.data[0]["project_id"]
        project = db.get_project(project_id, user.id)
        if not project:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get context
        context = await chat_agent.get_context(session_id)
        return ChatContextResponse(**context)
        
    except HTTPException:
        raise
    except Exception as e:
        api_logger.error(f"Error getting chat context: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting context: {str(e)}")

@app.post("/chat/{session_id}/regenerate-outline", response_model=ChatMessageResponse)
async def regenerate_outline(
    session_id: str,
    feedback: str = Form(...),
    user = Depends(get_current_user)
):
    """Regenerate presentation outline based on feedback"""
    try:
        # Verify session belongs to user's project
        session_result = db.client.table("chat_sessions").select("project_id").eq(
            "id", session_id
        ).execute()
        
        if not session_result.data:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        project_id = session_result.data[0]["project_id"]
        project = db.get_project(project_id, user.id)
        if not project:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Regenerate outline
        result = await chat_agent.regenerate_outline(session_id, feedback)
        
        # Send real-time update
        await send_realtime_update(
            project_id=project_id,
            user_id=user.id,
            event_type="outline_updated",
            data={"outline": result["outline"]}
        )
        
        return ChatMessageResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        api_logger.error(f"Error regenerating outline: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error regenerating outline: {str(e)}")

@app.get("/projects/{project_id}/chat-sessions", response_model=List[ChatSessionResponse])
async def get_project_chat_sessions(
    project_id: str,
    user = Depends(get_current_user),
    limit: int = 10
):
    """Get chat sessions for a project"""
    try:
        # Verify project belongs to user
        project = db.get_project(project_id, user.id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get chat sessions
        result = db.client.table("chat_sessions").select("*").eq(
            "project_id", project_id
        ).order("created_at", desc=True).limit(limit).execute()
        
        return [ChatSessionResponse(**session) for session in result.data]
        
    except HTTPException:
        raise
    except Exception as e:
        api_logger.error(f"Error getting chat sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting chat sessions: {str(e)}")

# Background task function
async def start_slide_generation_workflow(project_id: str, topic: str, user_id: str, approved_outline: Optional[Dict[str, Any]] = None, template_name: Optional[str] = None):
    """Background task to run the slide generation workflow"""
    try:
        # Get project details from database (in case title/topic were updated)
        project = db.get_project(project_id, user_id)
        if not project:
            api_logger.error(f"Project {project_id} not found for workflow execution")
            return
            
        # Use the actual topic from the database
        actual_topic = project.get("topic", topic)
        api_logger.info(f"Starting workflow for project {project_id} with topic: {actual_topic[:100]}...")
        
        # Extract template selection and refinement iterations from project metadata
        html_refinement_iterations = 2  # Default value
        if not template_name:
            metadata = project.get("metadata", {})
            if isinstance(metadata, dict):
                template_name = metadata.get("template_name")
                html_refinement_iterations = metadata.get("html_refinement_iterations", 2)
        else:
            # Still extract refinement iterations even if template_name is provided
            metadata = project.get("metadata", {})
            if isinstance(metadata, dict):
                html_refinement_iterations = metadata.get("html_refinement_iterations", 2)
        
        # Update project status to processing
        db.update_project_status(project_id, "processing")
        
        # Send processing started event
        await send_realtime_update(
            project_id=project_id,
            user_id=user_id,
            event_type="workflow_update",
            status="processing",
            data={"message": "Workflow started", "topic": actual_topic}
        )
        
        # Initialize workflow with database integration
        workflow = SlideGenerationWorkflow()
        
        # Set up paths
        from .template_manager import resolve_template_path, get_template_manager
        template_path = resolve_template_path(template_name)
        output_path = f"generated_presentations/project_{project_id}"
        
        # Get template folder path for locked backgrounds
        template_folder_path = None
        if template_name:
            manager = get_template_manager()
            template_folder_path = manager.get_template_folder_path(template_name)
        
        api_logger.info(f"Template path: {template_path}")
        api_logger.info(f"Template folder path: {template_folder_path}")
        api_logger.info(f"HTML refinement iterations: {html_refinement_iterations}")
        
        # Create enhanced callback with real-time updates
        realtime_callback = create_realtime_callback(project_id, user_id)
        
        # Set database callback on workflow
        workflow.set_database_callback(realtime_callback, project_id)
        
        # Debug logging for approved outline
        api_logger.info(f"Approved outline received: {approved_outline is not None}")
        if approved_outline:
            api_logger.info(f"Approved outline slides count: {len(approved_outline.get('slides', []))}")
            
            # Create slide records immediately so they appear in the frontend
            await create_slide_records_from_outline(project_id, approved_outline)
        
        # Check if parallel processing is enabled
        use_parallel_processing = os.getenv("USE_PARALLEL_SLIDE_PROCESSING", "false").lower() == "true"
        max_concurrent = os.getenv("MAX_CONCURRENT_SLIDES", "5")
        api_logger.info(f"Parallel processing enabled: {use_parallel_processing}, Max concurrent: {max_concurrent}")
        
        if use_parallel_processing:
            # If no approved outline for parallel processing, generate one automatically
            if not approved_outline:
                api_logger.info("🎯 No approved outline provided - generating outline for parallel processing")
                
                # Use the planning agent to generate an outline
                planning_agent = PresentationPlanningAgent()
                try:
                    # Generate outline using the new quickstart method that respects project description
                    outline_result = await planning_agent.generate_outline_for_quickstart(
                        topic=actual_topic,
                        project_id=project_id
                    )
                    
                    if outline_result and hasattr(outline_result, 'slides'):
                        # Convert PresentationOutline object to dict format expected by parallel workflow
                        approved_outline = {
                            "title": outline_result.title,
                            "topic": outline_result.topic,
                            "slides": [
                                {
                                    "slide_number": slide.slide_number,
                                    "title": slide.title,
                                    "content_type": slide.content_type,
                                    "key_points": slide.key_points,
                                    "layout_type": slide.suggested_layout or "content",
                                    "notes": slide.notes
                                }
                                for slide in outline_result.slides
                            ]
                        }
                        api_logger.info(f"✅ Auto-generated outline with {len(approved_outline.get('slides', []))} slides")
                        
                        # Create slide records for auto-generated outline too
                        await create_slide_records_from_outline(project_id, approved_outline)
                    else:
                        api_logger.warning("⚠️ Failed to auto-generate outline - falling back to sequential workflow")
                        use_parallel_processing = False
                        
                except Exception as e:
                    api_logger.error(f"❌ Error auto-generating outline: {e}")
                    api_logger.warning("⚠️ Falling back to sequential workflow")
                    use_parallel_processing = False
            
            if use_parallel_processing and approved_outline:
                api_logger.info("🚀 Using parallel slide processing")
                # Run parallel workflow
                result = await workflow.run_parallel_for_approved_outline(
                    topic=actual_topic,
                    template_path=template_path,
                    output_path=output_path,
                    approved_outline=approved_outline,
                    title=project.get("title"),
                    template_folder_path=template_folder_path,
                    html_refinement_iterations=html_refinement_iterations
                )
            else:
                # Run standard workflow
                api_logger.info("🔄 Using standard sequential workflow")
                result = workflow.run(
                    topic=actual_topic,
                    template_path=template_path,
                    template_folder_path=template_folder_path,
                    output_path=output_path,
                    title=project.get("title"),
                    approved_outline=approved_outline,
                    html_refinement_iterations=html_refinement_iterations
                )
        else:
            # Run standard workflow
            api_logger.info("🔄 Using standard sequential workflow (parallel processing disabled)")
            result = workflow.run(
                topic=actual_topic,
                template_path=template_path,
                template_folder_path=template_folder_path,
                output_path=output_path,
                title=project.get("title"),
                approved_outline=approved_outline,
                html_refinement_iterations=html_refinement_iterations
            )
        
        if result.get("success"):
            # Update project as completed
            db.update_project_status(project_id, "completed")
            
            # Upload generated presentation file to storage
            presentation_path = result.get("presentation_path")
            if presentation_path and os.path.exists(presentation_path):
                try:
                    # Read presentation file
                    with open(presentation_path, "rb") as f:
                        file_content = f.read()
                    
                    # Create storage path
                    filename = os.path.basename(presentation_path)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    storage_path = f"{user_id}/{project_id}/pptx/{timestamp}_{filename}"
                    
                    # Upload to presentations bucket
                    upload_result = db.client.storage.from_("presentations").upload(
                        path=storage_path,
                        file=file_content,
                        file_options={"content-type": "application/vnd.openxmlformats-officedocument.presentationml.presentation"}
                    )
                    
                    # Debug: Log upload result format
                    api_logger.info(f"Upload result type: {type(upload_result)}")
                    api_logger.info(f"Upload result: {upload_result}")
                    
                    # Check upload result - Supabase returns different response formats
                    upload_successful = False
                    if hasattr(upload_result, 'error') and upload_result.error is None:
                        upload_successful = True
                    elif isinstance(upload_result, dict) and not upload_result.get("error"):
                        upload_successful = True
                    elif upload_result and not hasattr(upload_result, 'error'):
                        # Some versions return the upload response directly
                        upload_successful = True
                    
                    if upload_successful:
                        # Create file record in database
                        db.create_project_file(
                            project_id=project_id,
                            file_type="pptx",
                            file_path=storage_path,
                            file_name=filename,
                            file_size=len(file_content)
                        )
                        print(f"✅ Uploaded presentation to storage: {storage_path}")
                    else:
                        error_msg = "Unknown upload error"
                        if hasattr(upload_result, 'error') and upload_result.error:
                            error_msg = str(upload_result.error)
                        elif isinstance(upload_result, dict) and upload_result.get("error"):
                            error_msg = str(upload_result["error"])
                        print(f"❌ Failed to upload presentation: {error_msg}")
                        
                except Exception as e:
                    print(f"❌ Error uploading presentation file: {e}")
            
            # Send completion event
            await send_realtime_update(
                project_id=project_id,
                user_id=user_id,
                event_type="project_completed",
                status="completed",
                data={
                    "presentation_path": result.get("presentation_path"),
                    "slide_count": result.get("slide_count", 0)
                }
            )
            
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
                    layout_type=slide_content.get("layout_type"),
                    layout_index=getattr(slide_content, 'layout_index', 0)  # CRITICAL FIX: Store layout_index
                )
                
                # Send slide generated event
                await send_realtime_update(
                    project_id=project_id,
                    user_id=user_id,
                    event_type="slide_generated",
                    data={
                        "slide_number": i + 1,
                        "title": slide_content.get("title"),
                        "has_html_content": bool(slide_content.get("html_content"))
                    }
                )
            
        else:
            # Update project as failed
            db.update_project_status(project_id, "failed")
            
            # Send failure event
            await send_realtime_update(
                project_id=project_id,
                user_id=user_id,
                event_type="project_failed",
                status="failed",
                data={"error": result.get("error", "Unknown error")}
            )
            
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
        
        # Send error event
        await send_realtime_update(
            project_id=project_id,
            user_id=user_id,
            event_type="error_occurred",
            status="failed",
            data={"error": str(e), "agent": "workflow_error"}
        )

# Template Management Endpoints

@app.get("/templates")
async def get_templates():
    """Get list of available PowerPoint templates"""
    try:
        from .template_manager import list_available_templates
        
        templates = list_available_templates()
        
        return {
            "templates": [
                {
                    "filename": template.filename,
                    "name": template.name,
                    "display_name": template.display_name,
                    "size_mb": round(template.size_mb, 2),
                    "slide_count": template.slide_count,
                    "is_valid": template.is_valid,
                    "error_message": template.error_message,
                    "folder_path": template.folder_path,
                    "locked_backgrounds": template.locked_backgrounds
                }
                for template in templates
            ]
        }
    except Exception as e:
        logger.error(f"Error getting templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/templates/default")
async def get_default_template():
    """Get the default template path"""
    try:
        from .template_manager import get_template_manager
        
        manager = get_template_manager()
        default_path = manager.get_default_template()
        
        if not default_path:
            raise HTTPException(
                status_code=404, 
                detail="No valid templates found"
            )
        
        # Extract template info
        templates = manager.list_templates()
        default_template = next(
            (t for t in templates if t.path == default_path),
            None
        )
        
        if not default_template:
            raise HTTPException(
                status_code=404,
                detail="Default template not found in template list"
            )
        
        return {
            "filename": default_template.filename,
            "name": default_template.name,
            "display_name": default_template.display_name,
            "path": default_template.path,
            "size_mb": round(default_template.size_mb, 2),
            "slide_count": default_template.slide_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting default template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/templates/validate")
async def validate_template_endpoint(template_name: str = None):
    """Validate a specific template or all templates"""
    try:
        from .template_manager import get_template_manager
        
        manager = get_template_manager()
        
        if template_name:
            # Validate specific template
            template_path = manager.get_template_path(template_name)
            if not template_path:
                raise HTTPException(
                    status_code=404,
                    detail=f"Template '{template_name}' not found"
                )
            
            is_valid = manager.validate_template(template_path)
            return {
                "template_name": template_name,
                "is_valid": is_valid,
                "path": template_path
            }
        else:
            # Validate all templates
            templates = manager.list_templates()
            return {
                "validation_results": [
                    {
                        "filename": template.filename,
                        "is_valid": template.is_valid,
                        "error_message": template.error_message
                    }
                    for template in templates
                ]
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating template(s): {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)