#!/usr/bin/env python3
"""
Temporary backend fix to get the system working.
This creates a simple API endpoint that bypasses RLS for now.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import uuid
from datetime import datetime
import asyncio
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Slide Creator API (Temp Fix)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Supabase
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_ANON_KEY")
)

class ProjectRequest(BaseModel):
    title: str
    topic: str
    project_id: str = None

@app.get("/health")
async def health():
    return {"status": "healthy", "message": "Temporary backend is running"}

@app.post("/projects")
async def create_project(request: ProjectRequest):
    """Create project and start workflow simulation"""
    try:
        print(f"Received project request: {request.title} - {request.topic}")
        
        # For now, just return success and simulate workflow start
        project_id = request.project_id or str(uuid.uuid4())
        
        # Simulate starting a workflow by creating workflow states
        workflow_stages = [
            "layout_analysis",
            "planning", 
            "content_generation",
            "html_generation",
            "refinement",
            "quality_review",
            "assembly"
        ]
        
        # Create workflow states in database (this will work with RLS if user_id matches)
        for i, stage in enumerate(workflow_stages):
            workflow_data = {
                "project_id": project_id,
                "agent_name": stage,
                "status": "pending",
                "created_at": datetime.now().isoformat()
            }
            
            try:
                result = supabase.table('workflow_states').insert(workflow_data).execute()
                print(f"Created workflow state for {stage}")
            except Exception as e:
                print(f"Warning: Could not create workflow state for {stage}: {e}")
                # Continue anyway - the frontend will still work
        
        # Start a background task to simulate workflow progression
        asyncio.create_task(simulate_workflow_progress(project_id, workflow_stages))
        
        return {
            "message": "Project workflow started successfully",
            "project_id": project_id,
            "status": "processing",
            "workflow_stages": len(workflow_stages)
        }
        
    except Exception as e:
        print(f"Error creating project: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

async def simulate_workflow_progress(project_id: str, stages: list):
    """Simulate workflow progress for demo purposes"""
    try:
        await asyncio.sleep(2)  # Initial delay
        
        for i, stage in enumerate(stages):
            # Update stage to in_progress
            try:
                supabase.table('workflow_states').update({
                    "status": "in_progress",
                    "started_at": datetime.now().isoformat()
                }).eq("project_id", project_id).eq("agent_name", stage).execute()
                
                print(f"Stage {stage} started")
            except Exception as e:
                print(f"Could not update {stage} to in_progress: {e}")
            
            # Simulate processing time
            processing_time = 5 + (i * 2)  # Increasing time per stage
            await asyncio.sleep(processing_time)
            
            # Update stage to completed  
            try:
                supabase.table('workflow_states').update({
                    "status": "completed",
                    "completed_at": datetime.now().isoformat(),
                    "execution_time_seconds": processing_time
                }).eq("project_id", project_id).eq("agent_name", stage).execute()
                
                print(f"Stage {stage} completed")
            except Exception as e:
                print(f"Could not update {stage} to completed: {e}")
        
        # Update project to completed
        try:
            supabase.table('projects').update({
                "status": "completed",
                "completed_at": datetime.now().isoformat()
            }).eq("id", project_id).execute()
            
            print(f"Project {project_id} completed")
        except Exception as e:
            print(f"Could not update project to completed: {e}")
            
    except Exception as e:
        print(f"Error in workflow simulation: {e}")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting temporary backend fix...")
    print("📝 This will simulate the workflow process")
    print("🔧 Access at http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")