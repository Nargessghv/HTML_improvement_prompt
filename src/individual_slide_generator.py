"""
Individual Slide Generator

Simple implementation for generating individual PPTX files for each completed slide.
"""

import os
import uuid
import tempfile
import io
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
import logging

from pptx import Presentation

from .database import get_supabase_client
from .llm_client import SlideContent
from .thumbnail_generator import ThumbnailGenerator

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
        
        # Initialize thumbnail generator
        self.thumbnail_generator = ThumbnailGenerator()

    async def generate_individual_slide(
        self,
        slide_id: str,
        project_id: str,
        slide_content: SlideContent,
        template_path: str,
        slide_number: int,
        layouts_info: Optional[Dict[str, Any]] = None,
        dynamic_models: Optional[Dict[str, Any]] = None,
        html_image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate an individual PPTX file for a single slide
        """
        try:
            logger.info(f"Generating individual PPTX for slide {slide_number} (ID: {slide_id})")
            
            # Add HTML image path to slide content if available
            if html_image_path:
                slide_content.html_image_path = html_image_path
                logger.info(f"HTML image available for slide: {html_image_path}")
            
            # Create a simple PPTX with just this slide
            individual_pptx_path = self._create_simple_slide_pptx(
                slide_content=slide_content,
                template_path=template_path,
                slide_number=slide_number,
                layouts_info=layouts_info,
                dynamic_models=dynamic_models
            )
            
            if not individual_pptx_path:
                return {"success": False, "error": "Failed to create PPTX file"}
            
            # Generate thumbnail
            thumbnail_path = None
            try:
                thumbnail_path = self.thumbnail_generator.generate_thumbnail(
                    pptx_path=individual_pptx_path,
                    size=(800, 600),  # Larger size for better quality
                    slide_number=0  # First slide
                )
                if thumbnail_path:
                    logger.info(f"Generated thumbnail: {thumbnail_path}")
            except Exception as e:
                logger.warning(f"Failed to generate thumbnail: {e}")
            
            # Upload to storage
            storage_result = await self._upload_slide_to_storage(
                file_path=individual_pptx_path,
                slide_id=slide_id,
                project_id=project_id,
                slide_number=slide_number,
                thumbnail_path=thumbnail_path
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
        slide_number: int,
        layouts_info: Optional[Dict[str, Any]] = None,
        dynamic_models: Optional[Dict[str, Any]] = None
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
            
            # Apply content with layout info for proper placeholder mapping
            self._apply_basic_content(slide, slide_content, layouts_info, dynamic_models)
            
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

    def _apply_basic_content(
        self, 
        slide, 
        slide_content: SlideContent, 
        layouts_info: Optional[Dict[str, Any]] = None,
        dynamic_models: Optional[Dict[str, Any]] = None
    ):
        """
        Apply complete content to the slide using the proven SlideGenerator methods
        """
        try:
            content = slide_content.content if hasattr(slide_content, 'content') else {}
            
            # Process LOCKED_ placeholders - replace their content with SVG paths
            from .template_manager import resolve_template_path
            template_path = resolve_template_path()
            template_folder = self.get_template_folder_from_path(template_path)
            
            if template_folder:
                content_copy = content.copy()
                for key in content_copy:
                    if key.startswith("LOCKED_"):
                        svg_path = Path(template_folder) / f"{key}.svg"
                        if svg_path.exists():
                            # Convert SVG to PNG for PowerPoint insertion
                            png_path = self._convert_svg_to_png(svg_path)
                            if png_path:
                                content[key] = str(png_path)
                                print(f"🔒 Replacing LOCKED_ placeholder content: {key} -> {png_path}")
                            else:
                                print(f"❌ Failed to convert SVG to PNG for {key}")
                        else:
                            print(f"⚠️ SVG file not found for {key}: {svg_path}")
            
            # Debug: Print available content
            print(f"🔍 Individual slide content keys: {list(content.keys())}")
            print(f"🔍 Content details:")
            for key, value in content.items():
                if isinstance(value, str):
                    print(f"   {key} (str): '{value[:50]}...'")
                elif isinstance(value, list):
                    print(f"   {key} (list): {len(value)} items - {value[:2]}...")
                else:
                    print(f"   {key} ({type(value).__name__}): {str(value)[:50]}...")
            
            # Check for HTML generated images in slide state
            html_image_path = None
            if hasattr(slide_content, 'html_image_path'):
                html_image_path = slide_content.html_image_path
                print(f"🎨 Found HTML rendered image: {html_image_path}")
            
            # Use the proven SlideGenerator content application logic
            # Import here to avoid circular imports
            from .slide_generator import SlideGenerator
            
            # Create temporary SlideGenerator instance to use its proven methods
            from .template_manager import resolve_template_path
            template_path = resolve_template_path()
            slide_generator = SlideGenerator(template_path)
            
            # Set up the slide generator's topic context
            slide_generator._current_topic = "Individual Slide Generation"
            
            # CRITICAL FIX: Initialize layouts_info for proper placeholder mapping
            if layouts_info:
                # Ensure content_generator exists with layouts_info
                if not hasattr(slide_generator, 'content_generator'):
                    # Create a simple object to hold layouts_info
                    class SimpleContentGenerator:
                        def __init__(self, layouts_info):
                            self.layouts_info = layouts_info
                    slide_generator.content_generator = SimpleContentGenerator(layouts_info)
                else:
                    slide_generator.content_generator.layouts_info = layouts_info
                print(f"🔧 Using proven SlideGenerator with layout mapping...")
            else:
                print(f"🔧 Using proven SlideGenerator with fallback name matching...")
            
            # Use the proven _populate_slide_placeholders method
            slide_generator._populate_slide_placeholders(slide, content)
            
            # Handle HTML image insertion if available
            if html_image_path and os.path.exists(html_image_path):
                print(f"📸 Inserting HTML rendered image: {html_image_path}")
                self._insert_html_image_into_slide(slide, html_image_path)
            
            # LOCKED backgrounds are now handled by converting SVG to PNG and passing as content
            # No need for separate locked background detection
            
            print(f"✅ Applied content using proven SlideGenerator methods")
                
        except Exception as e:
            logger.error(f"Error applying content: {e}")
            import traceback
            traceback.print_exc()
    
    def _insert_html_image_into_slide(self, slide, html_image_path: str):
        """
        Insert HTML rendered image into the most appropriate placeholder
        """
        from pptx.enum.shapes import PP_PLACEHOLDER
        
        try:
            # Find picture placeholders
            picture_placeholders = []
            for placeholder in slide.placeholders:
                if hasattr(placeholder, 'placeholder_format'):
                    if placeholder.placeholder_format.type == PP_PLACEHOLDER.PICTURE:
                        picture_placeholders.append(placeholder)
            
            if picture_placeholders:
                # Use the first available picture placeholder
                placeholder = picture_placeholders[0]
                self._insert_image_into_placeholder(placeholder, html_image_path)
                print(f"✅ Inserted HTML image into picture placeholder")
            else:
                print(f"⚠️ No picture placeholder found for HTML image")
                
        except Exception as e:
            print(f"⚠️ Error inserting HTML image: {e}")

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

    def _insert_image_into_placeholder(self, placeholder, image_path: str, preserve_zorder: bool = True) -> None:
        """
        Insert an image file into a picture placeholder by replacing the placeholder
        
        Args:
            placeholder: The placeholder shape to replace
            image_path: Path to the image file
            preserve_zorder: Whether to maintain the original z-order position (default: True)
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
            
            # Find placeholder's z-order position if preserving order
            original_zorder_index = None
            if preserve_zorder:
                original_zorder_index = self._find_shape_zorder_index(shapes, placeholder)
            
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
                
                # Restore z-order position if requested and found
                if preserve_zorder and original_zorder_index is not None:
                    self._move_shape_to_zorder_index(shapes, picture, original_zorder_index)
                    print(f"  → Preserved z-order position {original_zorder_index}")
                
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
        slide_number: int,
        thumbnail_path: Optional[str] = None
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
            
            # Upload thumbnail if available
            thumbnail_url = None
            thumbnail_storage_path = None
            if thumbnail_path and os.path.exists(thumbnail_path):
                try:
                    with open(thumbnail_path, 'rb') as f:
                        thumbnail_content = f.read()
                    
                    thumbnail_filename = f"slide_{slide_number}_thumbnail.png"
                    thumbnail_storage_path = f"projects/{project_id}/thumbnails/{slide_id}/{thumbnail_filename}"
                    
                    # Upload thumbnail
                    self.db.client.storage.from_("presentations").upload(
                        path=thumbnail_storage_path,
                        file=thumbnail_content,
                        file_options={"content-type": "image/png"}
                    )
                    
                    # Create signed URL for thumbnail
                    thumbnail_signed = self.db.client.storage.from_("presentations").create_signed_url(
                        path=thumbnail_storage_path,
                        expires_in=86400  # 24 hours
                    )
                    
                    if thumbnail_signed and 'signedURL' in thumbnail_signed:
                        thumbnail_url = thumbnail_signed['signedURL']
                        logger.info(f"Uploaded thumbnail to storage: {thumbnail_storage_path}")
                        
                except Exception as e:
                    logger.warning(f"Failed to upload thumbnail: {e}")
            
            return {
                "storage_path": storage_path,
                "public_url": public_url,
                "file_size": file_size,
                "filename": filename,
                "expires_at": expiry_time.isoformat(),
                "thumbnail_path": thumbnail_storage_path,
                "thumbnail_url": thumbnail_url
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
            
            # Insert into slide_files table for PPTX
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
            
            # Insert thumbnail record if available
            if storage_result.get("thumbnail_url"):
                thumbnail_record = {
                    "slide_id": slide_id,
                    "project_id": project_id,
                    "file_type": "preview_image",
                    "file_path": storage_result["thumbnail_path"],
                    "file_url": storage_result["thumbnail_url"],
                    "file_name": f"slide_{slide_id}_thumbnail.png",
                    "mime_type": "image/png",
                    "expires_at": storage_result["expires_at"],
                    "metadata": {
                        "generated_at": datetime.now().isoformat(),
                        "type": "thumbnail"
                    }
                }
                self.db.client.table("slide_files").insert(thumbnail_record).execute()
                logger.info(f"Stored thumbnail for slide {slide_id}")
            
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
        Combine all individual slide PPTX files into a final presentation using latest versions
        """
        try:
            logger.info(f"Combining individual slides for project {project_id}")
            
            # Get all completed slides for the project
            slides = self.db.get_project_slides_with_status(project_id)
            completed_slides = [s for s in slides if s.get("status") == "completed"]
            
            if not completed_slides:
                raise ValueError("No completed slides found for combination")
            
            # Sort slides by slide number to ensure correct order
            completed_slides.sort(key=lambda x: x.get("slide_number", 0))
            
            logger.info(f"Found {len(completed_slides)} completed slides to combine")
            
            # Create a new presentation from template
            final_prs = Presentation(template_path)
            
            # Remove existing slides from template
            while len(final_prs.slides) > 0:
                rId = final_prs.slides._sldIdLst[0].rId
                final_prs.part.drop_rel(rId)
                del final_prs.slides._sldIdLst[0]
            
            slides_combined = 0
            
            for slide_data in completed_slides:
                try:
                    slide_id = slide_data.get("id")
                    slide_number = slide_data.get("slide_number", slides_combined + 1)
                    
                    # First, try to get the latest PPTX from HTML refinements
                    latest_refinement = self.db.get_latest_refinement(slide_id)
                    pptx_source = None
                    source_type = None
                    
                    if latest_refinement and latest_refinement.get("pptx_file_url"):
                        pptx_source = latest_refinement["pptx_file_url"]
                        source_type = "refinement"
                        logger.info(f"Using refined PPTX for slide {slide_number}: iteration {latest_refinement.get('iteration_number', 'unknown')}")
                    elif slide_data.get("individual_pptx_url"):
                        pptx_source = slide_data["individual_pptx_url"]
                        source_type = "individual"
                        logger.info(f"Using individual PPTX for slide {slide_number}")
                    else:
                        logger.warning(f"No PPTX source found for slide {slide_number}, skipping")
                        continue
                    
                    # Download and combine the slide
                    slide_combined = await self._combine_single_slide(
                        final_prs, pptx_source, slide_number, source_type
                    )
                    
                    if slide_combined:
                        slides_combined += 1
                        logger.info(f"✅ Combined slide {slide_number} from {source_type} source")
                    else:
                        logger.warning(f"⚠️ Failed to combine slide {slide_number}")
                        
                except Exception as e:
                    logger.error(f"❌ Error combining slide {slide_data.get('slide_number', 'unknown')}: {e}")
                    continue
            
            if slides_combined == 0:
                logger.error("No slides were successfully combined")
                return {
                    "success": False,
                    "error": "No slides could be combined",
                    "slides_combined": 0
                }
            
            # Save the final presentation
            final_prs.save(output_path)
            
            # Get file size
            file_size = os.path.getsize(output_path)
            
            logger.info(f"✅ Successfully combined {slides_combined}/{len(completed_slides)} slides")
            
            return {
                "success": True,
                "output_path": output_path,
                "slides_combined": slides_combined,
                "total_slides": len(completed_slides),
                "file_size": file_size,
                "message": f"Combined {slides_combined} slides using latest versions"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to combine individual slides: {e}")
            return {
                "success": False,
                "error": str(e),
                "slides_combined": 0
            }

    async def _combine_single_slide(
        self,
        final_prs: Presentation,
        pptx_source_url: str,
        slide_number: int,
        source_type: str
    ) -> bool:
        """
        Download and combine a single slide from its PPTX source
        
        Args:
            final_prs: The final presentation to add slides to
            pptx_source_url: URL or path to the source PPTX file
            slide_number: Slide number for logging
            source_type: Type of source ("refinement" or "individual")
            
        Returns:
            True if slide was successfully combined, False otherwise
        """
        import tempfile
        import requests
        from urllib.parse import urlparse
        
        try:
            temp_pptx_path = None
            
            # Handle different source types
            if pptx_source_url.startswith('http'):
                # Download from URL
                logger.info(f"Downloading {source_type} PPTX for slide {slide_number}...")
                response = requests.get(pptx_source_url, stream=True)
                response.raise_for_status()
                
                # Create temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pptx') as temp_file:
                    temp_pptx_path = temp_file.name
                    for chunk in response.iter_content(chunk_size=8192):
                        temp_file.write(chunk)
                        
            elif os.path.exists(pptx_source_url):
                # Local file
                temp_pptx_path = pptx_source_url
            else:
                logger.error(f"PPTX source not accessible: {pptx_source_url}")
                return False
            
            # Load the source presentation
            source_prs = Presentation(temp_pptx_path)
            
            if len(source_prs.slides) == 0:
                logger.warning(f"Source PPTX for slide {slide_number} contains no slides")
                return False
            
            # Copy the first slide from source to final presentation
            source_slide = source_prs.slides[0]
            
            # Get the layout from the final presentation that matches the source slide
            layout_index = 0  # Default to first layout
            if hasattr(source_slide.slide_layout, 'slide_layout_id'):
                # Try to find matching layout in final presentation
                for i, layout in enumerate(final_prs.slide_layouts):
                    if layout.slide_layout_id == source_slide.slide_layout.slide_layout_id:
                        layout_index = i
                        break
            
            target_layout = final_prs.slide_layouts[layout_index]
            new_slide = final_prs.slides.add_slide(target_layout)
            
            # Copy content from source slide to new slide
            self._copy_slide_content(source_slide, new_slide)
            
            # Clean up temporary file if we downloaded it
            if temp_pptx_path != pptx_source_url and temp_pptx_path and os.path.exists(temp_pptx_path):
                try:
                    os.unlink(temp_pptx_path)
                except:
                    pass
            
            return True
            
        except Exception as e:
            logger.error(f"Error combining slide {slide_number} from {source_type}: {e}")
            
            # Clean up temporary file on error
            if temp_pptx_path and temp_pptx_path != pptx_source_url and os.path.exists(temp_pptx_path):
                try:
                    os.unlink(temp_pptx_path)
                except:
                    pass
            
            return False
    
    def _copy_slide_content(self, source_slide, target_slide):
        """
        Copy content from source slide to target slide
        
        Args:
            source_slide: Source slide to copy from
            target_slide: Target slide to copy to
        """
        from pptx.enum.shapes import MSO_SHAPE_TYPE
        
        try:
            # Copy slide title if both have titles
            if source_slide.shapes.title and target_slide.shapes.title:
                target_slide.shapes.title.text = source_slide.shapes.title.text
                
            # Copy other shapes, focusing on text and images
            for source_shape in source_slide.shapes:
                # Skip title shape as we already handled it
                if source_shape == source_slide.shapes.title:
                    continue
                
                try:
                    # Handle text shapes
                    if source_shape.has_text_frame:
                        # Find corresponding text placeholder in target
                        target_shape = self._find_corresponding_text_shape(source_shape, target_slide)
                        if target_shape and target_shape.has_text_frame:
                            target_shape.text_frame.clear()
                            for paragraph in source_shape.text_frame.paragraphs:
                                p = target_shape.text_frame.add_paragraph()
                                p.text = paragraph.text
                                # Copy basic formatting
                                if paragraph.runs:
                                    run = p.runs[0] if p.runs else p.add_run()
                                    source_run = paragraph.runs[0]
                                    try:
                                        run.font.size = source_run.font.size
                                        run.font.bold = source_run.font.bold
                                        run.font.italic = source_run.font.italic
                                    except:
                                        pass  # Skip if formatting copy fails
                                        
                    # Handle image shapes
                    elif source_shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                        # Find corresponding picture placeholder in target
                        target_shape = self._find_corresponding_picture_shape(source_shape, target_slide)
                        if target_shape:
                            # Replace the target shape with the source image
                            self._replace_image_shape(source_shape, target_shape, target_slide)
                            
                except Exception as shape_error:
                    logger.warning(f"Failed to copy shape content: {shape_error}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error copying slide content: {e}")
    
    def _find_corresponding_text_shape(self, source_shape, target_slide):
        """Find the corresponding text shape in the target slide"""
        # Simple heuristic: find the first available text shape that's not the title
        for target_shape in target_slide.shapes:
            if (target_shape != target_slide.shapes.title and 
                target_shape.has_text_frame and 
                not target_shape.text_frame.text.strip()):
                return target_shape
        return None
    
    def _find_corresponding_picture_shape(self, source_shape, target_slide):
        """Find the corresponding picture placeholder in the target slide"""
        from pptx.enum.shapes import PP_PLACEHOLDER
        
        # Look for picture placeholders first
        for target_shape in target_slide.shapes:
            if (hasattr(target_shape, 'placeholder_format') and 
                target_shape.placeholder_format.type == PP_PLACEHOLDER.PICTURE):
                return target_shape
        return None
    
    def _replace_image_shape(self, source_shape, target_shape, target_slide):
        """Replace target shape with source image"""
        try:
            # Get image data from source shape
            # Access the image through the slide part's rels
            slide_part = source_shape.part
            blip_rId = source_shape._element.blip_rId
            
            # Get the image part from the slide's relationships
            image_part = slide_part.rels[blip_rId].target_part
            image_bytes = image_part.blob
            
            # Get target shape dimensions and position
            left = target_shape.left
            top = target_shape.top
            width = target_shape.width
            height = target_shape.height
            
            # Remove target shape
            target_slide.shapes._spTree.remove(target_shape._element)
            
            # Add new image at the same position
            target_slide.shapes.add_picture(
                io.BytesIO(image_bytes), left, top, width, height
            )
            
            print(f"✅ Successfully replaced image shape in combined presentation")
            
        except Exception as e:
            logger.warning(f"Failed to replace image shape: {e}")
            # If we can't get the image data, skip the replacement
            print(f"⚠️ Could not replace image shape, keeping original placeholder")

    def cleanup_temp_files(self):
        """Clean up temporary files"""
        try:
            for file_path in self.temp_dir.glob("*.pptx"):
                file_path.unlink()
            logger.info("Cleaned up temporary slide files")
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {e}")
    
    # Z-Order Management Utilities
    
    def _find_shape_zorder_index(self, shapes, target_shape) -> Optional[int]:
        """
        Find the z-order index of a shape in the slide's shape tree
        
        Args:
            shapes: The slide's shapes collection
            target_shape: The shape to find
            
        Returns:
            The z-order index (position in _spTree) or None if not found
        """
        try:
            for i, element in enumerate(shapes._spTree):
                # Compare elements - need to handle different attribute names
                shape_element = getattr(target_shape, 'element', None)
                if shape_element is None:
                    shape_element = getattr(target_shape, '_element', None)
                if element == shape_element:
                    return i
            return None
        except Exception as e:
            print(f"Warning: Could not determine z-order index: {e}")
            return None
    
    def _move_shape_to_zorder_index(self, shapes, shape, target_index: int) -> bool:
        """
        Move a shape to a specific z-order index
        
        Args:
            shapes: The slide's shapes collection
            shape: The shape to move
            target_index: The desired z-order position
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Remove shape from current position
            shapes._spTree.remove(shape._element)
            
            # Insert at target position (clamped to valid range)
            max_index = len(shapes._spTree)
            safe_index = max(0, min(target_index, max_index))
            shapes._spTree.insert(safe_index, shape._element)
            
            return True
        except Exception as e:
            print(f"Warning: Could not move shape to z-order index {target_index}: {e}")
            return False
    
    def send_shape_to_back(self, slide, shape):
        """
        Send a shape behind all other shapes (background layer)
        
        Args:
            slide: The PowerPoint slide
            shape: The shape to send to back
        """
        try:
            shapes = slide.shapes
            # Position 2 is typically safe for background (after slide master elements)
            self._move_shape_to_zorder_index(shapes, shape, 2)
            print(f"✅ Sent shape '{getattr(shape, 'name', 'unnamed')}' to back")
        except Exception as e:
            print(f"❌ Failed to send shape to back: {e}")
    
    def bring_shape_to_front(self, slide, shape):
        """
        Bring a shape in front of all other shapes (foreground layer)
        
        Args:
            slide: The PowerPoint slide
            shape: The shape to bring to front
        """
        try:
            shapes = slide.shapes
            # Move to last position (front)
            shapes._spTree.remove(shape._element)
            shapes._spTree.append(shape._element)
            print(f"✅ Brought shape '{getattr(shape, 'name', 'unnamed')}' to front")
        except Exception as e:
            print(f"❌ Failed to bring shape to front: {e}")
    
    def move_shape_forward(self, slide, shape):
        """
        Move a shape one layer forward (towards front)
        
        Args:
            slide: The PowerPoint slide
            shape: The shape to move forward
        """
        try:
            shapes = slide.shapes
            current_index = self._find_shape_zorder_index(shapes, shape)
            if current_index is not None and current_index < len(shapes._spTree) - 1:
                self._move_shape_to_zorder_index(shapes, shape, current_index + 1)
                print(f"✅ Moved shape '{getattr(shape, 'name', 'unnamed')}' forward")
            else:
                print(f"Shape '{getattr(shape, 'name', 'unnamed')}' is already at front")
        except Exception as e:
            print(f"❌ Failed to move shape forward: {e}")
    
    def move_shape_backward(self, slide, shape):
        """
        Move a shape one layer backward (towards back)
        
        Args:
            slide: The PowerPoint slide
            shape: The shape to move backward
        """
        try:
            shapes = slide.shapes
            current_index = self._find_shape_zorder_index(shapes, shape)
            if current_index is not None and current_index > 2:  # Don't go behind master elements
                self._move_shape_to_zorder_index(shapes, shape, current_index - 1)
                print(f"✅ Moved shape '{getattr(shape, 'name', 'unnamed')}' backward")
            else:
                print(f"Shape '{getattr(shape, 'name', 'unnamed')}' is already at back")
        except Exception as e:
            print(f"❌ Failed to move shape backward: {e}")
    
    # Locked Background System
    
    def _detect_and_insert_locked_backgrounds(self, slide, template_folder: str) -> None:
        """
        Detect LOCKED_* placeholders and automatically insert corresponding SVG backgrounds
        
        Args:
            slide: PowerPoint slide object
            template_folder: Path to the template folder containing SVG files
        """
        try:
            # Get the layout to access original placeholder names
            layout = slide.slide_layout
            locked_placeholders = []
            
            # Build a mapping of idx to layout placeholder name
            layout_placeholder_names = {}
            for layout_ph in layout.placeholders:
                layout_name = getattr(layout_ph, 'name', '')
                idx = layout_ph.placeholder_format.idx
                layout_placeholder_names[idx] = layout_name
                if layout_name.startswith('LOCKED_'):
                    print(f"🔒 Found LOCKED placeholder in layout: {layout_name} (idx: {idx})")
            
            # Find corresponding placeholders in the slide by matching idx
            for placeholder in slide.placeholders:
                idx = placeholder.placeholder_format.idx
                layout_name = layout_placeholder_names.get(idx, '')
                if layout_name.startswith('LOCKED_'):
                    locked_placeholders.append((placeholder, layout_name))
                    print(f"🔒 Matched LOCKED placeholder in slide: {layout_name} (idx: {idx})")
            
            if not locked_placeholders:
                print(f"⚠️ No LOCKED placeholders found in slide")
                return
            
            print(f"🎨 Processing {len(locked_placeholders)} LOCKED placeholders...")
            
            # Process each locked placeholder
            for placeholder, layout_name in locked_placeholders:
                self._insert_locked_background_with_name(placeholder, layout_name, template_folder)
                
        except Exception as e:
            print(f"❌ Error processing locked backgrounds: {e}")
    
    def _insert_locked_background_with_name(self, placeholder, layout_name: str, template_folder: str) -> bool:
        """
        Insert SVG background for a specific locked placeholder using layout name
        
        Args:
            placeholder: The placeholder to fill
            layout_name: The original name from the layout (e.g., "LOCKED_Background_1")
            template_folder: Path to template folder containing SVG files
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not layout_name.startswith('LOCKED_'):
                print(f"⚠️ Placeholder {layout_name} is not a locked background")
                return False
            
            # Extract the background file name from placeholder name
            # LOCKED_Background_1 -> LOCKED_Background_1.svg
            svg_filename = f"{layout_name}.svg"
            svg_path = Path(template_folder) / svg_filename
            
            if not svg_path.exists():
                print(f"❌ SVG file not found: {svg_path}")
                return False
            
            print(f"🎨 Inserting locked background: {svg_filename}")
            
            # Convert SVG to PNG for PowerPoint insertion
            png_path = self._convert_svg_to_png(svg_path)
            if not png_path:
                print(f"❌ Failed to convert SVG to PNG: {svg_path}")
                return False
            
            # Insert the PNG into the placeholder with z-order preservation
            self._insert_image_into_placeholder(placeholder, str(png_path), preserve_zorder=True)
            
            # Clean up temporary PNG
            try:
                Path(png_path).unlink()
            except:
                pass
            
            print(f"✅ Successfully inserted locked background: {layout_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error inserting locked background for {layout_name}: {e}")
            return False
    
    def _insert_locked_background(self, placeholder, template_folder: str) -> bool:
        """
        Legacy method - kept for backward compatibility
        Insert SVG background for a specific locked placeholder
        
        Args:
            placeholder: The LOCKED_* placeholder to fill
            template_folder: Path to template folder containing SVG files
            
        Returns:
            True if successful, False otherwise
        """
        placeholder_name = getattr(placeholder, 'name', '')
        return self._insert_locked_background_with_name(placeholder, placeholder_name, template_folder)
    
    def _convert_svg_to_png(self, svg_path: Path) -> Optional[str]:
        """
        Convert SVG file to PNG for PowerPoint insertion
        
        Args:
            svg_path: Path to the SVG file
            
        Returns:
            Path to the generated PNG file, or None if conversion failed
        """
        try:
            # Try different SVG conversion methods
            
            # Method 1: Using cairosvg (if available)
            try:
                import cairosvg
                import warnings
                import os
                
                output_path = svg_path.with_suffix('.png')
                
                # Suppress pixman warnings on macOS
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore")
                    # Also redirect stderr temporarily to suppress pixman bug messages
                    import sys
                    old_stderr = sys.stderr
                    try:
                        # Redirect stderr to devnull
                        sys.stderr = open(os.devnull, 'w')
                        cairosvg.svg2png(url=str(svg_path), write_to=str(output_path), dpi=96)
                    finally:
                        # Restore stderr
                        sys.stderr.close()
                        sys.stderr = old_stderr
                
                # Check if the PNG was actually created
                if output_path.exists() and output_path.stat().st_size > 0:
                    print(f"  ✅ Converted SVG using cairosvg: {output_path}")
                    return str(output_path)
                else:
                    print(f"  ⚠️ cairosvg produced empty or no file")
                    
            except ImportError:
                pass
            except Exception as e:
                print(f"  ⚠️ cairosvg conversion failed: {e}")
            
            # Method 2: Using svglib + reportlab (often more reliable on macOS)
            try:
                from svglib.svglib import svg2rlg
                from reportlab.graphics import renderPM
                
                output_path = svg_path.with_suffix('.png')
                drawing = svg2rlg(str(svg_path))
                renderPM.drawToFile(drawing, str(output_path), fmt="PNG", dpi=96)
                
                if output_path.exists() and output_path.stat().st_size > 0:
                    print(f"  ✅ Converted SVG using svglib: {output_path}")
                    return str(output_path)
                    
            except ImportError:
                pass
            except Exception as e:
                print(f"  ⚠️ svglib conversion failed: {e}")
            
            # Method 3: Using Pillow with wand/ImageMagick (if available)
            try:
                from PIL import Image
                import io
                
                # Read SVG content
                with open(svg_path, 'r', encoding='utf-8') as f:
                    svg_content = f.read()
                
                # Try to use wand (ImageMagick) if available
                try:
                    from wand.image import Image as WandImage
                    from wand.color import Color
                    
                    with WandImage(blob=svg_content.encode(), format='svg') as img:
                        img.format = 'png'
                        img.background_color = Color('transparent')
                        
                        output_path = svg_path.with_suffix('.png')
                        img.save(filename=str(output_path))
                        print(f"  ✅ Converted SVG using ImageMagick: {output_path}")
                        return str(output_path)
                except ImportError:
                    pass
                except Exception as e:
                    print(f"  ⚠️ ImageMagick conversion failed: {e}")
                
            except ImportError:
                pass
            except Exception as e:
                print(f"  ⚠️ Pillow conversion failed: {e}")
            
            # Method 4: Fallback - create a simple colored rectangle PNG
            print(f"  ⚠️ No SVG conversion library available, creating fallback PNG...")
            return self._create_fallback_background_png(svg_path)
            
        except Exception as e:
            print(f"❌ SVG conversion failed completely: {e}")
            return None
    
    def _create_fallback_background_png(self, svg_path: Path) -> Optional[str]:
        """
        Create a fallback PNG when SVG conversion is not available
        
        Args:
            svg_path: Original SVG path (for naming)
            
        Returns:
            Path to created PNG file
        """
        try:
            from PIL import Image, ImageDraw
            
            # Create a simple background image
            width, height = 1920, 1080  # Standard slide dimensions
            img = Image.new('RGB', (width, height), color='#dc261e')  # ekona red
            draw = ImageDraw.Draw(img)
            
            # Add some basic styling
            draw.rectangle([0, 0, width, 20], fill='#ffffff')
            draw.rectangle([0, height-20, width, height], fill='#ffffff')
            
            # Add text indicator
            try:
                draw.text((50, height-60), f"Locked Background: {svg_path.stem}", 
                         fill='#ffffff', anchor='lm')
            except:
                pass
            
            output_path = svg_path.with_suffix('.png')
            img.save(output_path)
            print(f"  ✅ Created fallback background PNG: {output_path}")
            return str(output_path)
            
        except Exception as e:
            print(f"❌ Failed to create fallback PNG: {e}")
            return None
    
    def get_template_folder_from_path(self, template_path: str) -> Optional[str]:
        """
        Extract template folder path from template file path
        
        Args:
            template_path: Path to the PPTX template file
            
        Returns:
            Path to the template folder containing SVG files
        """
        try:
            template_file = Path(template_path)
            if template_file.parent.name == 'templates':
                # Old structure: templates/file.pptx
                template_name = template_file.stem
                return str(template_file.parent / template_name)
            else:
                # New structure: templates/template_name/file.pptx
                return str(template_file.parent)
        except Exception as e:
            print(f"❌ Error determining template folder: {e}")
            return None