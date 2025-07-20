"""
Database Module

Centralized Supabase client and database operations for the slide generation system.
Provides a unified interface for all database interactions.
"""

import os
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from supabase import create_client, Client


class SupabaseClient:
    """Centralized Supabase client for database operations"""
    
    def __init__(self):
        """Initialize Supabase client with environment variables"""
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables")
        
        self.client: Client = create_client(self.supabase_url, self.supabase_key)
    
    # Project operations
    def create_project(self, user_id: str, title: str, topic: str) -> Dict[str, Any]:
        """Create a new project"""
        project_data = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": title,
            "topic": topic,
            "status": "draft",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        result = self.client.table("projects").insert(project_data).execute()
        if not result.data:
            raise Exception("Failed to create project")
        
        return result.data[0]
    
    def get_project(self, project_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get a project by ID, optionally filtered by user"""
        query = self.client.table("projects").select("*").eq("id", project_id)
        
        if user_id:
            query = query.eq("user_id", user_id)
        
        result = query.execute()
        return result.data[0] if result.data else None
    
    def update_project_status(self, project_id: str, status: str, completed_at: Optional[str] = None) -> bool:
        """Update project status"""
        update_data = {
            "status": status,
            "updated_at": datetime.now().isoformat()
        }
        
        if completed_at:
            update_data["completed_at"] = completed_at
        elif status == "completed":
            update_data["completed_at"] = datetime.now().isoformat()
        
        result = self.client.table("projects").update(update_data).eq("id", project_id).execute()
        return bool(result.data)
    
    def get_user_projects(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all projects for a user"""
        result = self.client.table("projects")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        return result.data or []
    
    def delete_project(self, project_id: str, user_id: Optional[str] = None) -> bool:
        """Delete a project (CASCADE will handle related records)"""
        query = self.client.table("projects").delete().eq("id", project_id)
        
        if user_id:
            query = query.eq("user_id", user_id)
        
        result = query.execute()
        return bool(result.data)
    
    # Workflow state operations
    def create_workflow_state(self, project_id: str, agent_name: str, status: str, **kwargs) -> Dict[str, Any]:
        """Create a workflow state record"""
        state_data = {
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "agent_name": agent_name,
            "status": status,
            "created_at": datetime.now().isoformat()
        }
        
        # Add optional fields
        if "started_at" in kwargs:
            state_data["started_at"] = kwargs["started_at"]
        elif status == "in_progress":
            state_data["started_at"] = datetime.now().isoformat()
        
        if status in ["completed", "failed"]:
            state_data["completed_at"] = datetime.now().isoformat()
        
        if "error_message" in kwargs:
            state_data["error_message"] = kwargs["error_message"]
        
        if "execution_time_seconds" in kwargs:
            state_data["execution_time_seconds"] = kwargs["execution_time_seconds"]
        
        if "input_data" in kwargs:
            state_data["input_data"] = kwargs["input_data"]
        
        if "output_data" in kwargs:
            state_data["output_data"] = kwargs["output_data"]
        
        result = self.client.table("workflow_states").insert(state_data).execute()
        if not result.data:
            raise Exception(f"Failed to create workflow state for {agent_name}")
        
        return result.data[0]
    
    def get_project_workflow_states(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all workflow states for a project"""
        result = self.client.table("workflow_states")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("created_at")\
            .execute()
        
        return result.data or []
    
    def update_workflow_state(self, state_id: str, status: str, **kwargs) -> bool:
        """Update an existing workflow state"""
        update_data = {
            "status": status
        }
        
        if status in ["completed", "failed"]:
            update_data["completed_at"] = datetime.now().isoformat()
        
        if "error_message" in kwargs:
            update_data["error_message"] = kwargs["error_message"]
        
        if "execution_time_seconds" in kwargs:
            update_data["execution_time_seconds"] = kwargs["execution_time_seconds"]
        
        if "output_data" in kwargs:
            update_data["output_data"] = kwargs["output_data"]
        
        result = self.client.table("workflow_states").update(update_data).eq("id", state_id).execute()
        return bool(result.data)
    
    # Slide operations
    def create_slide(self, project_id: str, slide_number: int, title: Optional[str] = None, 
                    content: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """Create a slide record"""
        slide_data = {
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "slide_number": slide_number,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        if title:
            slide_data["title"] = title
        
        if content:
            slide_data["content"] = content
        
        # Add optional fields
        for field in ["html_content", "refined_html", "layout_type"]:
            if field in kwargs:
                slide_data[field] = kwargs[field]
        
        result = self.client.table("slides").insert(slide_data).execute()
        if not result.data:
            raise Exception(f"Failed to create slide {slide_number}")
        
        return result.data[0]
    
    def get_project_slides(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all slides for a project"""
        result = self.client.table("slides")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("slide_number")\
            .execute()
        
        return result.data or []
    
    def update_slide(self, slide_id: str, **kwargs) -> bool:
        """Update a slide record"""
        update_data = {
            "updated_at": datetime.now().isoformat()
        }
        
        # Add fields to update
        for field in ["title", "content", "html_content", "refined_html", "layout_type"]:
            if field in kwargs:
                update_data[field] = kwargs[field]
        
        result = self.client.table("slides").update(update_data).eq("id", slide_id).execute()
        return bool(result.data)
    
    # Conversation operations
    def create_conversation(self, project_id: str, slide_id: str, messages: List[Dict] = None) -> Dict[str, Any]:
        """Create a conversation record"""
        conversation_data = {
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "slide_id": slide_id,
            "messages": messages or [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        result = self.client.table("conversations").insert(conversation_data).execute()
        if not result.data:
            raise Exception("Failed to create conversation")
        
        return result.data[0]
    
    def add_conversation_message(self, conversation_id: str, message: Dict[str, Any]) -> bool:
        """Add a message to a conversation"""
        # Get current conversation
        result = self.client.table("conversations").select("messages").eq("id", conversation_id).execute()
        
        if not result.data:
            return False
        
        current_messages = result.data[0]["messages"] or []
        current_messages.append(message)
        
        # Update conversation
        update_result = self.client.table("conversations")\
            .update({
                "messages": current_messages,
                "updated_at": datetime.now().isoformat()
            })\
            .eq("id", conversation_id)\
            .execute()
        
        return bool(update_result.data)
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get a conversation by ID"""
        result = self.client.table("conversations").select("*").eq("id", conversation_id).execute()
        return result.data[0] if result.data else None
    
    # File operations
    def create_project_file(self, project_id: str, file_type: str, file_path: str, 
                           file_name: str, file_size: Optional[int] = None) -> Dict[str, Any]:
        """Create a project file record"""
        file_data = {
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "file_type": file_type,
            "file_path": file_path,
            "file_name": file_name,
            "created_at": datetime.now().isoformat()
        }
        
        if file_size:
            file_data["file_size"] = file_size
        
        result = self.client.table("project_files").insert(file_data).execute()
        if not result.data:
            raise Exception(f"Failed to create file record for {file_name}")
        
        return result.data[0]
    
    def get_project_files(self, project_id: str, file_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all files for a project, optionally filtered by type"""
        query = self.client.table("project_files").select("*").eq("project_id", project_id)
        
        if file_type:
            query = query.eq("file_type", file_type)
        
        result = query.order("created_at", desc=True).execute()
        return result.data or []
    
    # Utility methods
    def health_check(self) -> bool:
        """Check if database connection is healthy"""
        try:
            # Simple query to test connection
            result = self.client.table("projects").select("id").limit(1).execute()
            return True
        except Exception as e:
            print(f"Database health check failed: {e}")
            return False


# Global instance
_supabase_client: Optional[SupabaseClient] = None

def get_supabase_client() -> SupabaseClient:
    """Get or create the global Supabase client instance"""
    global _supabase_client
    
    if _supabase_client is None:
        _supabase_client = SupabaseClient()
    
    return _supabase_client

def init_database() -> SupabaseClient:
    """Initialize the database connection"""
    return get_supabase_client()