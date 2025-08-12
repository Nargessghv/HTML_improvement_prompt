"""
Individual Slide Generator

Simple implementation for generating individual PPTX files for each completed slide.
"""

import os
import uuid
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
import logging

from pptx import Presentation

from .database import get_supabase_client
from .llm_client import SlideContent

logger = logging.getLogger(__name__)


class IndividualSlideGenerator:
    """
    Generates individual PPTX files for each completed slide
    """

    def __init__(self):
        """Initialize the generator with database and storage clients"""
        self.db = get_supabase_client()
        
        # Create temp directory for individual slides
        self.temp_dir = Path(tempfile.gettempdir()) / "individual_slides"
        self.temp_dir.mkdir(exist_ok=True)

    async def generate_individual_slide(
        self,
        slide_id: str,
        project_id: str,
        slide_content: SlideContent,
        template_path: str,
        slide_number: int,
        layouts_info: Optional[Dict[str, Any]] = None,
        dynamic_models: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate an individual PPTX file for a single slide
        """
        try:
            logger.info(f"Generating individual PPTX for slide {slide_number} (ID: {slide_id})")
            
            # Create a simple PPTX with just this slide
            individual_pptx_path = self._create_simple_slide_pptx(
                slide_content=slide_content,
                template_path=template_path,
                slide_number=slide_number
            )
            
            if not individual_pptx_path:
                return {"success": False, "error": "Failed to create PPTX file"}
            
            # Upload to storage
            storage_result = await self._upload_slide_to_storage(
                file_path=individual_pptx_path,
                slide_id=slide_id,
                project_id=project_id,
                slide_number=slide_number
            )
            
            # Update database with file information
            await self._update_slide_file_info(
                slide_id=slide_id,
                project_id=project_id,
                storage_result=storage_result
            )
            
            # Clean up temp file
            if os.path.exists(individual_pptx_path):
                os.remove(individual_pptx_path)
            
            logger.info(f"✅ Successfully generated individual PPTX for slide {slide_number}")
            
            return {
                "success": True,
                "slide_id": slide_id,
                "file_path": storage_result["storage_path"],
                "file_url": storage_result["public_url"],
                "file_size": storage_result["file_size"]
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to generate individual PPTX for slide {slide_number}: {e}")
            return {
                "success": False,
                "slide_id": slide_id,
                "error": str(e)
            }

    def _create_simple_slide_pptx(
        self,
        slide_content: SlideContent,
        template_path: str,
        slide_number: int
    ) -> Optional[str]:
        """
        Create a simple single-slide PPTX file
        """
        try:
            # Create a new presentation
            prs = Presentation(template_path)
            
            # Remove existing slides
            while len(prs.slides) > 0:
                rId = prs.slides._sldIdLst[0].rId
                prs.part.drop_rel(rId)
                del prs.slides._sldIdLst[0]
            
            # Determine layout index from slide content
            layout_index = self._get_layout_index_from_content(slide_content)
            
            # Add our slide with appropriate layout
            print(f"🔍 Template has {len(prs.slide_layouts)} layouts available")
            print(f"🎯 Requested layout index: {layout_index}")
            
            if 0 <= layout_index < len(prs.slide_layouts):
                slide_layout = prs.slide_layouts[layout_index]
                print(f"✅ Using requested layout {layout_index}")
            else:
                print(f"⚠️ Layout index {layout_index} not available (template has {len(prs.slide_layouts)} layouts)")
                # Use the most appropriate fallback
                if len(prs.slide_layouts) > 1:
                    slide_layout = prs.slide_layouts[1]  # Usually a content layout
                    print(f"🔧 Using fallback layout 1")
                else:
                    slide_layout = prs.slide_layouts[0]  # Title slide
                    print(f"🔧 Using fallback layout 0 (only one layout available)")
            
            slide = prs.slides.add_slide(slide_layout)
            
            # Apply content
            self._apply_basic_content(slide, slide_content)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"slide_{slide_number}_{timestamp}_{uuid.uuid4().hex[:8]}.pptx"
            file_path = self.temp_dir / filename
            
            # Save the presentation
            prs.save(str(file_path))
            
            logger.info(f"Created individual PPTX: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Error creating simple slide PPTX: {e}")
            return None

    def _apply_basic_content(self, slide, slide_content: SlideContent):
        """
        Apply basic content to the slide
        """
        try:
            content = slide_content.content if hasattr(slide_content, 'content') else {}
            
            # Debug: Print available content
            print(f"🔍 Individual slide content keys: {list(content.keys())}")
            print(f"🔍 Individual slide content values: {[f'{k}: {str(v)[:50]}...' for k, v in content.items()]}")
            
            # Set title
            if slide.shapes.title:
                title = content.get('Title', content.get('title', content.get('slide_title', f'Slide')))
                slide.shapes.title.text = str(title)
                print(f"✅ Set slide title: {title}")
            
            # Handle picture placeholders first
            from pptx.enum.shapes import MSO_SHAPE_TYPE
            from pptx.enum.shapes import PP_PLACEHOLDER
            
            for shape in slide.shapes:
                if hasattr(shape, 'placeholder_format') and shape.placeholder_format.type == PP_PLACEHOLDER.PICTURE:
                    # This is a picture placeholder, check if we have image content for it
                    placeholder_name = getattr(shape, 'name', '')
                    
                    # Look for image content in the content dictionary
                    image_content = None
                    for key, value in content.items():
                        # Check if the value is an image path (more reliable than key matching)
                        if self._is_image_path(value):
                            image_content = value
                            print(f"🔍 Found image content: {key} -> {value}")
                            break
                    
                    if image_content and os.path.exists(image_content):
                        try:
                            # Insert the image using the same method as main slide generator
                            self._insert_image_into_placeholder(shape, image_content)
                            print(f"✅ Inserted image into placeholder: {placeholder_name}")
                        except Exception as e:
                            print(f"⚠️ Failed to insert image into placeholder {placeholder_name}: {e}")
            
            # Find content placeholders for text
            for shape in slide.shapes:
                if shape.has_text_frame and shape != slide.shapes.title:
                    # Add main content
                    main_content = content.get('content', content.get('main_content', ''))
                    if main_content:
                        if isinstance(main_content, list):
                            # Handle bullet points
                            shape.text_frame.clear()
                            for i, point in enumerate(main_content):
                                p = shape.text_frame.paragraphs[0] if i == 0 else shape.text_frame.add_paragraph()
                                p.text = str(point)
                        else:
                            shape.text_frame.text = str(main_content)
                    break
                    
        except Exception as e:
            logger.error(f"Error applying basic content: {e}")

    def _is_image_path(self, content: str) -> bool:
        """
        Check if content is a file path pointing to an image file
        """
        if not content or not isinstance(content, str):
            return False
            
        content = content.strip()
        
        # Check for common image file extensions
        image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']
        content_lower = content.lower()
        
        # Check if it ends with an image extension
        has_image_extension = any(content_lower.endswith(ext) for ext in image_extensions)
        
        # Check if it looks like a file path (contains directory separators)
        looks_like_path = ('/' in content or '\\' in content or content.startswith('.'))
        
        return has_image_extension and looks_like_path

    def _insert_image_into_placeholder(self, placeholder, image_path: str) -> None:
        """
        Insert an image file into a picture placeholder by replacing the placeholder
        """
        try:
            # Check if image file exists
            if not os.path.exists(image_path):
                print(f"Warning: Image file '{image_path}' not found")
                return
            
            # Get placeholder properties before replacement
            left = placeholder.left
            top = placeholder.top
            width = placeholder.width
            height = placeholder.height
            name = placeholder.name
            
            # Get the slide and shapes collection
            slide = placeholder.part.slide
            shapes = slide.shapes
            
            # Find and remove the placeholder
            placeholder_found = False
            for i, shape in enumerate(shapes):
                if shape == placeholder:
                    # Remove the placeholder from the shapes collection
                    shapes._spTree.remove(shape.element)
                    placeholder_found = True
                    break
            
            if placeholder_found:
                # Add the image in place of the placeholder
                picture = shapes.add_picture(image_path, left, top, width, height)
                
                # Set the picture name
                picture.name = f"{name}_image"
                
                print(f"✅ Individual slide: Inserted image '{image_path}' into picture placeholder")
            else:
                print("Warning: Could not find placeholder in shapes collection")
                
        except Exception as e:
            print(f"Error inserting image '{image_path}': {e}")
            import traceback
            traceback.print_exc()

    def _get_layout_index_from_content(self, slide_content: SlideContent) -> int:
        """
        Extract layout index from slide content
        """
        try:
            print(f"🔍 Extracting layout index from slide content")
            print(f"🔍 Slide content type: {type(slide_content)}")
            
            # Try to get layout_index from the slide content object
            if hasattr(slide_content, 'layout_index'):
                layout_index = slide_content.layout_index
                print(f"✅ Found layout_index attribute: {layout_index}")
                return layout_index
            
            # Fallback: try to get from content dictionary
            if hasattr(slide_content, 'content'):
                content = slide_content.content
                if isinstance(content, dict) and 'layout_index' in content:
                    layout_index = int(content['layout_index'])  # Ensure it's an int
                    print(f"✅ Found layout_index in content dict: {layout_index}")
                    return layout_index
            
            # Another fallback: check if slide content has layout info
            if hasattr(slide_content, '__dict__'):
                print(f"🔍 Slide content attributes: {list(slide_content.__dict__.keys())}")
                for attr_name, attr_value in slide_content.__dict__.items():
                    if 'layout' in attr_name.lower() and isinstance(attr_value, int):
                        print(f"✅ Found layout info in attribute {attr_name}: {attr_value}")
                        return attr_value
            
            # Default fallback - use layout 1 instead of 4 for better compatibility
            logger.warning(f"Could not determine layout index from slide content, using safe fallback layout 1")
            print(f"⚠️ No layout info found, using fallback layout 1")
            return 1  # Usually a content layout that exists in most templates
            
        except Exception as e:
            logger.error(f"Error getting layout index from content: {e}")
            print(f"❌ Error extracting layout index: {e}")
            return 1  # Safe fallback

    async def _upload_slide_to_storage(
        self,
        file_path: str,
        slide_id: str,
        project_id: str,
        slide_number: int
    ) -> Dict[str, Any]:
        """
        Upload individual slide PPTX to Supabase Storage
        """
        try:
            # Read file
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            file_size = len(file_content)
            filename = f"slide_{slide_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pptx"
            
            # Create storage path
            storage_path = f"projects/{project_id}/individual_slides/{slide_id}/{filename}"
            
            # Upload to Supabase Storage
            upload_result = self.db.client.storage.from_("presentations").upload(
                path=storage_path,
                file=file_content,
                file_options={
                    "content-type": "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                }
            )
            
            # Generate signed URL (valid for 24 hours)
            expiry_time = datetime.now() + timedelta(hours=24)
            signed_url_result = self.db.client.storage.from_("presentations").create_signed_url(
                path=storage_path,
                expires_in=86400  # 24 hours
            )
            
            public_url = None
            if signed_url_result:
                if isinstance(signed_url_result, dict) and 'signedURL' in signed_url_result:
                    public_url = signed_url_result['signedURL']
                elif isinstance(signed_url_result, str):
                    public_url = signed_url_result
            
            logger.info(f"Uploaded slide {slide_number} to storage: {storage_path}")
            
            return {
                "storage_path": storage_path,
                "public_url": public_url,
                "file_size": file_size,
                "filename": filename,
                "expires_at": expiry_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to upload slide to storage: {e}")
            raise

    async def _update_slide_file_info(
        self,
        slide_id: str,
        project_id: str,
        storage_result: Dict[str, Any]
    ):
        """
        Update database with slide file information
        """
        try:
            # Update slides table
            slide_update = {
                "individual_pptx_path": storage_result["storage_path"],
                "individual_pptx_url": storage_result["public_url"],
                "individual_pptx_size": storage_result["file_size"],
                "individual_pptx_generated_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            self.db.client.table("slides").update(slide_update).eq("id", slide_id).execute()
            
            # Insert into slide_files table
            file_record = {
                "slide_id": slide_id,
                "project_id": project_id,
                "file_type": "individual_pptx",
                "file_path": storage_result["storage_path"],
                "file_url": storage_result["public_url"],
                "file_name": storage_result["filename"],
                "file_size": storage_result["file_size"],
                "mime_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                "expires_at": storage_result["expires_at"],
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "generator_version": "1.0"
                }
            }
            
            self.db.client.table("slide_files").insert(file_record).execute()
            
            logger.info(f"Updated database with file info for slide {slide_id}")
            
        except Exception as e:
            logger.error(f"Failed to update database with file info: {e}")
            raise

    async def combine_individual_slides(
        self,
        project_id: str,
        output_path: str,
        template_path: str
    ) -> Dict[str, Any]:
        """
        Combine all individual slide PPTX files into a final presentation
        """
        try:
            logger.info(f"Combining individual slides for project {project_id}")
            
            # Get all completed slides for the project using proper database method
            slides = self.db.get_project_slides_with_status(project_id)
            completed_slides = [s for s in slides if s.get("status") == "completed"]
            
            if not completed_slides:
                raise ValueError("No completed slides found for combination")
            
            # For now, just return success - actual combination would be complex
            # and we can fall back to traditional assembly
            logger.info(f"Would combine {len(completed_slides)} individual slides")
            
            return {
                "success": False,  # Force fallback to traditional assembly for now
                "message": "Individual slide combination not yet fully implemented - using fallback",
                "slides_found": len(completed_slides)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to combine individual slides: {e}")
            return {
                "success": False,
                "error": str(e),
                "slides_combined": 0
            }

    def cleanup_temp_files(self):
        """Clean up temporary files"""
        try:
            for file_path in self.temp_dir.glob("*.pptx"):
                file_path.unlink()
            logger.info("Cleaned up temporary slide files")
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {e}")