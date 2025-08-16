"""
Supabase Storage Module

Handles file uploads to Supabase Storage for HTML refinement iterations.
Provides methods for uploading HTML files and PNG screenshots with proper organization.
"""

import os
import uuid
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from supabase import create_client, Client
import logging

# Configure logging
logger = logging.getLogger('slide_creator.storage')

class SupabaseStorageError(Exception):
    """Custom exception for Supabase Storage operations"""
    pass

class SupabaseStorageClient:
    """Client for managing Supabase Storage operations"""
    
    def __init__(self, bucket_name: str = "html-refinements"):
        """
        Initialize Supabase Storage client
        
        Args:
            bucket_name: Name of the Supabase storage bucket
        """
        try:
            self.supabase_url = os.getenv("SUPABASE_URL")
            # Use service role key for storage operations to bypass RLS
            self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            
            if not self.supabase_url or not self.supabase_key:
                raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set for storage operations")
            
            self.client: Client = create_client(self.supabase_url, self.supabase_key)
            self.bucket_name = bucket_name
            
            logger.info(f"✅ Supabase Storage client initialized for bucket: {bucket_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase Storage client: {e}")
            raise SupabaseStorageError(f"Storage client initialization failed: {str(e)}")
    
    def _generate_file_path(self, project_id: str, slide_id: str, iteration: int, 
                           file_type: str, extension: str) -> str:
        """
        Generate organized file path for storage
        
        Args:
            project_id: Project UUID
            slide_id: Slide UUID 
            iteration: Refinement iteration number
            file_type: Type of file (html, image)
            extension: File extension (html, png, etc.)
            
        Returns:
            Organized file path for storage
        """
        # Create organized folder structure: project_id/slide_id/iteration_X/file_type.extension
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{file_type}_{timestamp}.{extension}"
        return f"{project_id}/{slide_id}/iteration_{iteration:02d}/{filename}"
    
    def upload_html_file(self, project_id: str, slide_id: str, iteration: int, 
                        html_content: str) -> str:
        """
        Upload HTML content to Supabase Storage
        
        Args:
            project_id: Project UUID
            slide_id: Slide UUID
            iteration: Refinement iteration number
            html_content: HTML content as string
            
        Returns:
            Public URL of uploaded file
            
        Raises:
            SupabaseStorageError: If upload fails
        """
        try:
            # Generate file path
            file_path = self._generate_file_path(project_id, slide_id, iteration, "refined_html", "html")
            
            # Convert string to bytes
            html_bytes = html_content.encode('utf-8')
            
            # Upload to Supabase Storage
            result = self.client.storage.from_(self.bucket_name).upload(
                path=file_path,
                file=html_bytes,
                file_options={
                    "content-type": "text/html",
                    "cache-control": "3600"
                }
            )
            
            # Check if upload was successful by checking if result has the expected structure
            # In newer versions of supabase-py, successful uploads return the file path
            if not result or (hasattr(result, 'error') and result.error):
                error_msg = getattr(result, 'error', 'Unknown upload error')
                raise SupabaseStorageError(f"HTML upload failed: {error_msg}")
            
            # Generate signed URL for private bucket (valid for 1 hour)
            signed_url_response = self.client.storage.from_(self.bucket_name).create_signed_url(file_path, 3600)
            
            if signed_url_response.get('error'):
                raise SupabaseStorageError(f"Failed to generate signed URL: {signed_url_response['error']}")
            
            signed_url = signed_url_response.get('signedURL') or signed_url_response.get('url')
            
            # Clean up any trailing parameters that might cause issues
            if isinstance(signed_url, str) and signed_url.endswith('?'):
                signed_url = signed_url.rstrip('?')
            
            logger.info(f"✅ Uploaded HTML file: {file_path}")
            logger.info(f"   - Signed URL: {signed_url}")
            return signed_url
            
        except Exception as e:
            logger.error(f"❌ Failed to upload HTML file: {e}")
            raise SupabaseStorageError(f"HTML upload failed: {str(e)}")
    
    def upload_image_file(self, project_id: str, slide_id: str, iteration: int, 
                         image_path: Path) -> str:
        """
        Upload image file to Supabase Storage
        
        Args:
            project_id: Project UUID
            slide_id: Slide UUID  
            iteration: Refinement iteration number
            image_path: Local path to image file
            
        Returns:
            Public URL of uploaded file
            
        Raises:
            SupabaseStorageError: If upload fails
        """
        try:
            if not image_path.exists():
                logger.error(f"❌ Image file not found: {image_path}")
                logger.info(f"   - Checking parent directory: {image_path.parent}")
                if image_path.parent.exists():
                    files_in_dir = list(image_path.parent.glob("*"))
                    logger.info(f"   - Files in directory: {[f.name for f in files_in_dir[:10]]}")
                else:
                    logger.error(f"   - Parent directory does not exist: {image_path.parent}")
                raise FileNotFoundError(f"Image file not found: {image_path}")
            
            # Get file extension and detect MIME type
            extension = image_path.suffix.lstrip('.')
            mime_type, _ = mimetypes.guess_type(str(image_path))
            mime_type = mime_type or "image/png"  # Default to PNG
            
            logger.info(f"📁 Found image file: {image_path} (size: {image_path.stat().st_size} bytes)")
            
            # Generate file path
            file_path = self._generate_file_path(project_id, slide_id, iteration, "screenshot", extension)
            
            # Read image file
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
            
            # Upload to Supabase Storage
            result = self.client.storage.from_(self.bucket_name).upload(
                path=file_path,
                file=image_bytes,
                file_options={
                    "content-type": mime_type,
                    "cache-control": "3600"
                }
            )
            
            # Check if upload was successful by checking if result has the expected structure
            # In newer versions of supabase-py, successful uploads return the file path
            if not result or (hasattr(result, 'error') and result.error):
                error_msg = getattr(result, 'error', 'Unknown upload error')
                raise SupabaseStorageError(f"Image upload failed: {error_msg}")
            
            # Generate signed URL for private bucket (valid for 1 hour)
            signed_url_response = self.client.storage.from_(self.bucket_name).create_signed_url(file_path, 3600)
            
            if signed_url_response.get('error'):
                raise SupabaseStorageError(f"Failed to generate signed URL: {signed_url_response['error']}")
            
            signed_url = signed_url_response.get('signedURL') or signed_url_response.get('url')
            
            # Clean up any trailing parameters that might cause issues
            if isinstance(signed_url, str) and signed_url.endswith('?'):
                signed_url = signed_url.rstrip('?')
            
            logger.info(f"✅ Uploaded image file: {file_path}")
            logger.info(f"   - Signed URL: {signed_url}")
            return signed_url
            
        except Exception as e:
            logger.error(f"❌ Failed to upload image file: {e}")
            raise SupabaseStorageError(f"Image upload failed: {str(e)}")
    
    def upload_file(self, file_path: str, storage_path: str, content_type: Optional[str] = None, bucket_name: Optional[str] = None) -> str:
        """
        Upload a file to Supabase Storage
        
        Args:
            file_path: Local path to the file
            storage_path: Remote storage path (key) for the file
            content_type: MIME type of the file (auto-detected if not provided)
            bucket_name: Storage bucket name (uses default if not provided)
            
        Returns:
            Public URL of uploaded file
            
        Raises:
            SupabaseStorageError: If upload fails
        """
        try:
            file_path_obj = Path(file_path)
            
            if not file_path_obj.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Use specified bucket or default
            target_bucket = bucket_name or self.bucket_name
            
            # Auto-detect content type if not provided
            if not content_type:
                content_type, _ = mimetypes.guess_type(file_path)
                content_type = content_type or "application/octet-stream"
            
            logger.info(f"📁 Found file: {file_path} (size: {file_path_obj.stat().st_size} bytes)")
            
            # Read file
            with open(file_path, 'rb') as f:
                file_bytes = f.read()
            
            # Upload to Supabase Storage
            result = self.client.storage.from_(target_bucket).upload(
                path=storage_path,
                file=file_bytes,
                file_options={
                    "content-type": content_type,
                    "cache-control": "3600"
                }
            )
            
            # Check if upload was successful
            if not result or (hasattr(result, 'error') and result.error):
                error_msg = getattr(result, 'error', 'Unknown upload error')
                raise SupabaseStorageError(f"File upload failed: {error_msg}")
            
            # Generate signed URL for private bucket (valid for 1 hour)
            signed_url_response = self.client.storage.from_(target_bucket).create_signed_url(storage_path, 3600)
            
            if signed_url_response.get('error'):
                raise SupabaseStorageError(f"Failed to generate signed URL: {signed_url_response['error']}")
            
            signed_url = signed_url_response.get('signedURL') or signed_url_response.get('url')
            
            # Clean up any trailing parameters that might cause issues
            if isinstance(signed_url, str) and signed_url.endswith('?'):
                signed_url = signed_url.rstrip('?')
            
            logger.info(f"✅ Uploaded file to bucket '{target_bucket}': {storage_path}")
            logger.info(f"   - Signed URL: {signed_url}")
            return signed_url
            
        except Exception as e:
            logger.error(f"❌ Failed to upload file: {e}")
            raise SupabaseStorageError(f"File upload failed: {str(e)}")

    def upload_refinement_files(self, project_id: str, slide_id: str, iteration: int,
                               html_content: str, image_path: Path) -> Tuple[str, str]:
        """
        Upload both HTML and image files for a refinement iteration
        
        Args:
            project_id: Project UUID
            slide_id: Slide UUID
            iteration: Refinement iteration number
            html_content: HTML content as string
            image_path: Local path to image file
            
        Returns:
            Tuple of (html_url, image_url)
            
        Raises:
            SupabaseStorageError: If either upload fails
        """
        try:
            # Upload HTML file
            html_url = self.upload_html_file(project_id, slide_id, iteration, html_content)
            
            # Upload image file
            image_url = self.upload_image_file(project_id, slide_id, iteration, image_path)
            
            logger.info(f"✅ Uploaded refinement files for iteration {iteration}")
            return html_url, image_url
            
        except Exception as e:
            logger.error(f"❌ Failed to upload refinement files: {e}")
            raise SupabaseStorageError(f"Refinement files upload failed: {str(e)}")
    
    def delete_refinement_files(self, project_id: str, slide_id: str, iteration: int) -> bool:
        """
        Delete all files for a specific refinement iteration
        
        Args:
            project_id: Project UUID
            slide_id: Slide UUID
            iteration: Refinement iteration number
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            # List all files in the iteration folder
            folder_path = f"{project_id}/{slide_id}/iteration_{iteration:02d}/"
            
            result = self.client.storage.from_(self.bucket_name).list(folder_path)
            
            if not result or (hasattr(result, 'error') and result.error):
                error_msg = getattr(result, 'error', 'Unknown list error')
                logger.warning(f"Could not list files for deletion: {error_msg}")
                return False
            
            # Delete each file
            for file_info in result.data:
                file_path = f"{folder_path}{file_info['name']}"
                delete_result = self.client.storage.from_(self.bucket_name).remove([file_path])
                
                if not delete_result or (hasattr(delete_result, 'error') and delete_result.error):
                    error_msg = getattr(delete_result, 'error', 'Unknown delete error')
                    logger.error(f"Failed to delete file {file_path}: {error_msg}")
                    return False
            
            logger.info(f"✅ Deleted refinement files for iteration {iteration}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete refinement files: {e}")
            return False
    
    def get_refinement_files_info(self, project_id: str, slide_id: str) -> Dict[int, Dict[str, Any]]:
        """
        Get information about all refinement files for a slide
        
        Args:
            project_id: Project UUID
            slide_id: Slide UUID
            
        Returns:
            Dictionary mapping iteration numbers to file info
        """
        try:
            folder_path = f"{project_id}/{slide_id}/"
            
            result = self.client.storage.from_(self.bucket_name).list(folder_path)
            
            if not result or (hasattr(result, 'error') and result.error):
                error_msg = getattr(result, 'error', 'Unknown list error')
                logger.warning(f"Could not list refinement files: {error_msg}")
                return {}
            
            # Organize files by iteration
            iterations = {}
            for folder_info in result.data:
                if folder_info['name'].startswith('iteration_'):
                    iteration_num = int(folder_info['name'].split('_')[1])
                    
                    # List files in this iteration folder
                    iteration_path = f"{folder_path}{folder_info['name']}/"
                    files_result = self.client.storage.from_(self.bucket_name).list(iteration_path)
                    
                    if files_result and not (hasattr(files_result, 'error') and files_result.error):
                        iterations[iteration_num] = {
                            'files': files_result.data,
                            'folder_path': iteration_path
                        }
            
            return iterations
            
        except Exception as e:
            logger.error(f"❌ Failed to get refinement files info: {e}")
            return {}


# Global instance
_storage_client: Optional[SupabaseStorageClient] = None

def get_storage_client() -> SupabaseStorageClient:
    """Get or create the global Supabase Storage client instance"""
    global _storage_client
    
    if _storage_client is None:
        _storage_client = SupabaseStorageClient()
    
    return _storage_client