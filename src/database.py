"""
Database Module

Centralized Supabase client and database operations for the slide generation system.
Provides a unified interface for all database interactions with comprehensive error handling and logging.
"""

import os
import uuid
import logging
import traceback
from datetime import datetime
from typing import Optional, Dict, Any, List
from functools import wraps
from supabase import create_client, Client


# Configure logging for database operations
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create dedicated logger for database operations
db_logger = logging.getLogger('slide_creator.database')


class DatabaseError(Exception):
    """Custom exception for database operations"""
    def __init__(self, message: str, operation: str = None, table: str = None, original_error: Exception = None):
        self.message = message
        self.operation = operation
        self.table = table
        self.original_error = original_error
        super().__init__(self.message)


class DatabaseConnectionError(DatabaseError):
    """Exception for database connection issues"""
    pass


class DatabaseValidationError(DatabaseError):
    """Exception for data validation errors"""
    pass


class DatabasePermissionError(DatabaseError):
    """Exception for permission/authentication errors"""
    pass


def log_database_operation(operation_name: str, table_name: str = None):
    """Decorator to log database operations and handle errors"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            operation_id = str(uuid.uuid4())[:8]
            
            # Log operation start
            db_logger.info(f"[{operation_id}] Starting {operation_name} on {table_name or 'unknown'}")
            
            try:
                # Execute operation
                result = func(self, *args, **kwargs)
                
                # Log success
                db_logger.info(f"[{operation_id}] Successfully completed {operation_name}")
                return result
                
            except Exception as e:
                # Log error with details
                error_details = {
                    'operation': operation_name,
                    'table': table_name,
                    'args': str(args)[:200],  # Limit arg logging
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                }
                
                db_logger.error(f"[{operation_id}] Failed {operation_name}: {error_details}")
                
                # Re-raise with enhanced error context
                if "auth" in str(e).lower() or "permission" in str(e).lower():
                    raise DatabasePermissionError(
                        f"Permission error in {operation_name}: {str(e)}", 
                        operation_name, table_name, e
                    )
                elif "connection" in str(e).lower() or "network" in str(e).lower():
                    raise DatabaseConnectionError(
                        f"Connection error in {operation_name}: {str(e)}", 
                        operation_name, table_name, e
                    )
                elif "validation" in str(e).lower() or "constraint" in str(e).lower():
                    raise DatabaseValidationError(
                        f"Validation error in {operation_name}: {str(e)}", 
                        operation_name, table_name, e
                    )
                else:
                    raise DatabaseError(
                        f"Database error in {operation_name}: {str(e)}", 
                        operation_name, table_name, e
                    )
        
        return wrapper
    return decorator


class SupabaseClient:
    """Centralized Supabase client for database operations with comprehensive error handling"""
    
    def __init__(self):
        """Initialize Supabase client with environment variables"""
        try:
            self.supabase_url = os.getenv("SUPABASE_URL")
            self.supabase_key = os.getenv("SUPABASE_ANON_KEY")
            
            if not self.supabase_url or not self.supabase_key:
                raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables")
            
            # Validate URL format
            if not self.supabase_url.startswith(('https://', 'http://')):
                raise ValueError("SUPABASE_URL must be a valid HTTP/HTTPS URL")
            
            self.client: Client = create_client(self.supabase_url, self.supabase_key)
            
            # Test connection on initialization
            db_logger.info("Initializing Supabase client...")
            if not self.health_check():
                raise DatabaseConnectionError("Failed to connect to Supabase on initialization")
            
            db_logger.info("✅ Supabase client initialized successfully")
            
        except Exception as e:
            db_logger.error(f"❌ Failed to initialize Supabase client: {e}")
            raise DatabaseConnectionError(f"Supabase client initialization failed: {str(e)}", original_error=e)
    
    def _validate_uuid(self, value: str, field_name: str) -> None:
        """Validate UUID format"""
        try:
            uuid.UUID(value)
        except (ValueError, TypeError):
            raise DatabaseValidationError(f"Invalid UUID format for {field_name}: {value}")
    
    def _validate_required_fields(self, data: Dict[str, Any], required_fields: List[str]) -> None:
        """Validate required fields are present and not empty"""
        for field in required_fields:
            if field not in data or not data[field]:
                raise DatabaseValidationError(f"Required field '{field}' is missing or empty")
    
    def _handle_supabase_response(self, result, operation: str, table: str = None) -> Any:
        """Handle Supabase response and check for errors"""
        if hasattr(result, 'error') and result.error:
            error_msg = f"Supabase error in {operation}: {result.error}"
            db_logger.error(error_msg)
            raise DatabaseError(error_msg, operation, table)
        
        if not hasattr(result, 'data') or result.data is None:
            error_msg = f"No data returned from {operation}"
            db_logger.warning(error_msg)
            return None
        
        return result.data
    
    # Project operations
    @log_database_operation("create_project", "projects")
    def create_project(self, user_id: str, title: str, topic: str) -> Dict[str, Any]:
        """Create a new project with validation and error handling"""
        # Validate inputs
        self._validate_uuid(user_id, "user_id")
        self._validate_required_fields({"title": title, "topic": topic}, ["title", "topic"])
        
        if len(title.strip()) > 200:
            raise DatabaseValidationError("Project title must be 200 characters or less")
        
        if len(topic.strip()) > 1000:
            raise DatabaseValidationError("Project topic must be 1000 characters or less")
        
        project_data = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": title.strip(),
            "topic": topic.strip(),
            "status": "draft",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        result = self.client.table("projects").insert(project_data).execute()
        data = self._handle_supabase_response(result, "create_project", "projects")
        
        if not data:
            raise DatabaseError("Failed to create project - no data returned", "create_project", "projects")
        
        return data[0]
    
    @log_database_operation("get_project", "projects")
    def get_project(self, project_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get a project by ID, optionally filtered by user"""
        # Validate inputs
        self._validate_uuid(project_id, "project_id")
        if user_id:
            self._validate_uuid(user_id, "user_id")
        
        query = self.client.table("projects").select("*").eq("id", project_id)
        
        if user_id:
            query = query.eq("user_id", user_id)
        
        result = query.execute()
        data = self._handle_supabase_response(result, "get_project", "projects")
        
        return data[0] if data else None
    
    @log_database_operation("update_project_status", "projects")
    def update_project_status(self, project_id: str, status: str, completed_at: Optional[str] = None) -> bool:
        """Update project status with validation"""
        # Validate inputs
        self._validate_uuid(project_id, "project_id")
        valid_statuses = ["draft", "processing", "completed", "failed"]
        if status not in valid_statuses:
            raise DatabaseValidationError(f"Invalid status '{status}'. Must be one of: {valid_statuses}")
        
        update_data = {
            "status": status,
            "updated_at": datetime.now().isoformat()
        }
        
        if completed_at:
            update_data["completed_at"] = completed_at
        elif status == "completed":
            update_data["completed_at"] = datetime.now().isoformat()
        
        result = self.client.table("projects").update(update_data).eq("id", project_id).execute()
        data = self._handle_supabase_response(result, "update_project_status", "projects")
        
        return bool(data)
    
    @log_database_operation("get_user_projects", "projects")
    def get_user_projects(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all projects for a user with pagination validation"""
        # Validate inputs
        self._validate_uuid(user_id, "user_id")
        
        if limit < 1 or limit > 100:
            raise DatabaseValidationError("Limit must be between 1 and 100")
        
        if offset < 0:
            raise DatabaseValidationError("Offset must be non-negative")
        
        result = self.client.table("projects")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        data = self._handle_supabase_response(result, "get_user_projects", "projects")
        return data or []
    
    @log_database_operation("delete_project", "projects")
    def delete_project(self, project_id: str, user_id: Optional[str] = None) -> bool:
        """Delete a project (CASCADE will handle related records)"""
        # Validate inputs
        self._validate_uuid(project_id, "project_id")
        if user_id:
            self._validate_uuid(user_id, "user_id")
        
        query = self.client.table("projects").delete().eq("id", project_id)
        
        if user_id:
            query = query.eq("user_id", user_id)
        
        result = query.execute()
        data = self._handle_supabase_response(result, "delete_project", "projects")
        
        return bool(data)
    
    # Workflow state operations
    @log_database_operation("create_workflow_state", "workflow_states")
    def create_workflow_state(self, project_id: str, agent_name: str, status: str, **kwargs) -> Dict[str, Any]:
        """Create a workflow state record with validation"""
        # Validate inputs
        self._validate_uuid(project_id, "project_id")
        self._validate_required_fields({"agent_name": agent_name, "status": status}, ["agent_name", "status"])
        
        valid_statuses = ["pending", "in_progress", "completed", "failed"]
        if status not in valid_statuses:
            raise DatabaseValidationError(f"Invalid workflow status '{status}'. Must be one of: {valid_statuses}")
        
        valid_agents = [
            "layout_analysis", "presentation_planning", "content_generation", 
            "html_content_generation", "html_refinement", "quality_review", "slide_assembly"
        ]
        if agent_name not in valid_agents:
            db_logger.warning(f"Unusual agent name '{agent_name}' - expected one of: {valid_agents}")
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
    @log_database_operation("health_check", "projects")
    def health_check(self) -> bool:
        """Check if database connection is healthy with detailed logging"""
        try:
            # Simple query to test connection
            result = self.client.table("projects").select("id").limit(1).execute()
            
            # Check for Supabase errors
            if hasattr(result, 'error') and result.error:
                db_logger.error(f"Health check failed with Supabase error: {result.error}")
                return False
            
            db_logger.info("✅ Database health check passed")
            return True
            
        except Exception as e:
            db_logger.error(f"❌ Database health check failed: {e}")
            return False
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information for debugging"""
        return {
            "supabase_url": self.supabase_url,
            "has_client": self.client is not None,
            "health_status": self.health_check()
        }


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