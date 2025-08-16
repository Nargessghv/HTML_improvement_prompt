"""
Dual Path Presentation Generator

This module provides both individual slide generation (for preview) and complete 
presentation generation (for final output) using the EXACT SAME slide creation process
to ensure 100% consistency.
"""

import os
import uuid
import tempfile
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from pptx import Presentation

from .database import get_supabase_client
from .llm_client import SlideContent
from .thumbnail_generator import ThumbnailGenerator

logger = logging.getLogger(__name__)


class DualPathGenerator:
    """
    Generates both individual slides (for preview) and complete presentations (final)
    using the EXACT SAME slide creation process to ensure perfect consistency.
    
    Key Features:
    - Individual slides for preview with perfect formatting
    - Final presentation with identical formatting (no copying between presentations)
    - Supports slide regeneration when user requests adjustments
    - Maintains complete consistency between preview and final
    """

    def __init__(self, template_path: str):
        """Initialize with template path"""
        self.template_path = template_path
        self.db = get_supabase_client()
        self.thumbnail_generator = ThumbnailGenerator()
        
        # Create temp directory for individual slides
        self.temp_dir = Path(tempfile.gettempdir()) / "dual_path_slides"
        self.temp_dir.mkdir(exist_ok=True)

    async def generate_individual_slide_for_preview(
        self,
        slide_id: str,
        project_id: str,
        slide_content: SlideContent,
        slide_number: int,
        layouts_info: Optional[Dict[str, Any]] = None,
        html_image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate individual PPTX file for preview using the core slide creation process
        
        This creates the slide exactly as it will appear in the final presentation.
        """
        try:
            logger.info(f"Generating individual slide {slide_number} for preview")
            
            # Create individual PPTX using the core process
            individual_pptx_path = await self._create_individual_slide_pptx(
                slide_content=slide_content,
                slide_number=slide_number,
                layouts_info=layouts_info,
                html_image_path=html_image_path
            )
            
            if not individual_pptx_path:
                return {"success": False, "error": "Failed to create individual PPTX"}
            
            # Generate thumbnail
            thumbnail_path = None
            try:
                thumbnail_path = self.thumbnail_generator.generate_thumbnail(
                    pptx_path=individual_pptx_path,
                    size=(800, 600),
                    slide_number=0
                )
            except Exception as e:
                logger.warning(f"Failed to generate thumbnail: {e}")
            
            # Upload to storage
            storage_result = await self._upload_individual_slide(
                file_path=individual_pptx_path,
                slide_id=slide_id,
                project_id=project_id,
                slide_number=slide_number,
                thumbnail_path=thumbnail_path
            )
            
            # Update database
            await self._update_slide_file_info(slide_id, project_id, storage_result)
            
            # Clean up temp file
            if os.path.exists(individual_pptx_path):
                os.remove(individual_pptx_path)
            
            logger.info(f"✅ Generated individual slide {slide_number} for preview")
            
            return {
                "success": True,
                "slide_id": slide_id,
                "file_path": storage_result["storage_path"],
                "file_url": storage_result["public_url"],
                "thumbnail_url": storage_result.get("thumbnail_url")
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to generate individual slide {slide_number}: {e}")
            return {"success": False, "slide_id": slide_id, "error": str(e)}

    async def generate_complete_presentation(
        self,
        project_id: str,
        output_path: str,
        slide_contents: List[SlideContent],
        layouts_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate complete presentation using the EXACT SAME process as individual slides
        
        This ensures 100% consistency between individual previews and final presentation.
        """
        try:
            logger.info(f"Generating complete presentation with {len(slide_contents)} slides")
            
            # Create presentation from template
            presentation = Presentation(self.template_path)
            
            # Clear any existing slides from template
            self._clear_template_slides(presentation)
            
            # Add each slide using the SAME process as individual generation
            slides_added = 0
            for i, slide_content in enumerate(slide_contents):
                try:
                    success = await self._add_slide_using_core_process(
                        presentation=presentation,
                        slide_content=slide_content,
                        slide_number=i + 1,
                        layouts_info=layouts_info
                    )
                    
                    if success:
                        slides_added += 1
                        logger.info(f"✅ Added slide {i + 1} to final presentation")
                    else:
                        logger.warning(f"⚠️ Failed to add slide {i + 1}")
                        
                except Exception as e:
                    logger.error(f"❌ Error adding slide {i + 1}: {e}")
                    continue
            
            if slides_added == 0:
                return {"success": False, "error": "No slides were successfully added"}
            
            # Save the complete presentation
            presentation.save(output_path)
            file_size = os.path.getsize(output_path)
            
            # Update database
            await self._update_project_final_presentation(
                project_id, output_path, file_size, slides_added
            )
            
            logger.info(f"✅ Generated complete presentation: {slides_added}/{len(slide_contents)} slides")
            
            return {
                "success": True,
                "output_path": output_path,
                "slides_added": slides_added,
                "file_size": file_size,
                "message": f"Generated presentation with perfect formatting consistency"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to generate complete presentation: {e}")
            return {"success": False, "error": str(e)}

    async def regenerate_individual_slide(
        self,
        slide_id: str,
        project_id: str,
        updated_slide_content: SlideContent,
        slide_number: int,
        layouts_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Regenerate a specific individual slide after user adjustments
        
        This allows users to request changes to specific slides and regenerate
        only that slide while maintaining consistency.
        """
        try:
            logger.info(f"Regenerating slide {slide_number} after user adjustments")
            
            # Generate new individual slide using the same process
            result = await self.generate_individual_slide_for_preview(
                slide_id=slide_id,
                project_id=project_id,
                slide_content=updated_slide_content,
                slide_number=slide_number,
                layouts_info=layouts_info
            )
            
            # Mark slide as updated in database
            if result["success"]:
                await self._mark_slide_as_updated(slide_id, updated_slide_content)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to regenerate slide {slide_number}: {e}")
            return {"success": False, "error": str(e)}

    async def _create_individual_slide_pptx(
        self,
        slide_content: SlideContent,
        slide_number: int,
        layouts_info: Optional[Dict[str, Any]] = None,
        html_image_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Create individual PPTX using the core slide creation process
        
        This is the CORE PROCESS that will be replicated exactly in the final presentation.
        """
        try:
            # Create fresh presentation from template
            prs = Presentation(self.template_path)
            
            # Clear existing slides
            self._clear_template_slides(prs)
            
            # Add slide using core process
            success = await self._add_slide_using_core_process(
                presentation=prs,
                slide_content=slide_content,
                slide_number=slide_number,
                layouts_info=layouts_info,
                html_image_path=html_image_path
            )
            
            if not success:
                return None
            
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"slide_{slide_number}_{timestamp}_{uuid.uuid4().hex[:8]}.pptx"
            file_path = self.temp_dir / filename
            
            # Save presentation
            prs.save(str(file_path))
            
            # Verify file was created
            if not file_path.exists():
                raise Exception(f"Failed to save PPTX file to {file_path}")
            
            logger.info(f"Created individual PPTX: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Error creating individual PPTX: {e}")
            return None

    async def _add_slide_using_core_process(
        self,
        presentation: Presentation,
        slide_content: SlideContent,
        slide_number: int,
        layouts_info: Optional[Dict[str, Any]] = None,
        html_image_path: Optional[str] = None
    ) -> bool:
        """
        CORE SLIDE CREATION PROCESS
        
        This is the single source of truth for how slides are created.
        Both individual slides and final presentation slides use this exact process.
        """
        try:
            # Get layout index
            layout_index = self._get_layout_index(slide_content)
            
            # Validate layout index
            if layout_index < 0 or layout_index >= len(presentation.slide_layouts):
                logger.warning(f"Invalid layout index {layout_index}, using default")
                layout_index = 1
            
            # Create slide with proper layout
            slide_layout = presentation.slide_layouts[layout_index]
            slide = presentation.slides.add_slide(slide_layout)
            
            # Apply content using the proven SlideGenerator methods
            self._apply_content_to_slide_core(
                slide=slide,
                slide_content=slide_content,
                layouts_info=layouts_info,
                slide_number=slide_number,
                html_image_path=html_image_path
            )
            
            logger.debug(f"Successfully added slide {slide_number} using core process")
            return True
            
        except Exception as e:
            logger.error(f"Error in core slide creation process for slide {slide_number}: {e}")
            return False

    def _apply_content_to_slide_core(
        self,
        slide,
        slide_content: SlideContent,
        layouts_info: Optional[Dict[str, Any]] = None,
        slide_number: int = 1,
        html_image_path: Optional[str] = None
    ):
        """
        CORE CONTENT APPLICATION PROCESS
        
        This applies content to a slide using the exact proven methods from SlideGenerator.
        This process must be identical for both individual and final presentation slides.
        """
        try:
            # Import here to avoid circular imports
            from .slide_generator import SlideGenerator
            
            # Create SlideGenerator instance to use proven methods
            slide_generator = SlideGenerator(self.template_path)
            
            # Process content
            content = slide_content.content if hasattr(slide_content, 'content') else {}
            
            # Auto-add LOCKED_ backgrounds
            content = self._process_locked_placeholders(content, slide)
            
            # Set up layouts_info for proper placeholder mapping
            if layouts_info:
                if not hasattr(slide_generator, 'content_generator'):
                    # Create minimal content generator for layouts_info
                    class LayoutInfoHolder:
                        def __init__(self, layouts_info):
                            self.layouts_info = layouts_info
                    slide_generator.content_generator = LayoutInfoHolder(layouts_info)
                else:
                    slide_generator.content_generator.layouts_info = layouts_info
            
            # Apply content using the proven placeholder population method
            slide_generator._populate_slide_placeholders(slide, content)
            
            # Handle HTML image if provided
            if html_image_path and os.path.exists(html_image_path):
                self._insert_html_image_into_slide(slide, html_image_path)
            
            logger.debug(f"Applied content to slide {slide_number} using core process")
            
        except Exception as e:
            logger.error(f"Error applying content to slide {slide_number}: {e}")

    def _process_locked_placeholders(self, content: Dict[str, str], slide) -> Dict[str, str]:
        """Process LOCKED_ placeholders by adding PNG paths"""
        try:
            template_folder = Path(self.template_path).parent
            
            # Check slide layout for LOCKED_ placeholders
            slide_layout = slide.slide_layout
            for layout_ph in slide_layout.placeholders:
                ph_name = layout_ph.name
                if ph_name and ph_name.startswith("LOCKED_"):
                    png_path = template_folder / f"{ph_name}.png"
                    if png_path.exists() and ph_name not in content:
                        content[ph_name] = str(png_path)
                        logger.debug(f"Auto-added LOCKED_ background: {ph_name}")
            
            return content
            
        except Exception as e:
            logger.warning(f"Error processing LOCKED_ placeholders: {e}")
            return content

    def _insert_html_image_into_slide(self, slide, html_image_path: str):
        """Insert HTML rendered image into appropriate placeholder"""
        from pptx.enum.shapes import PP_PLACEHOLDER
        
        try:
            # Find picture placeholders
            for placeholder in slide.placeholders:
                if (hasattr(placeholder, 'placeholder_format') and 
                    placeholder.placeholder_format.type == PP_PLACEHOLDER.PICTURE):
                    # Use SlideGenerator method for consistent image insertion
                    from .slide_generator import SlideGenerator
                    slide_generator = SlideGenerator(self.template_path)
                    slide_generator._insert_image_into_placeholder(placeholder, html_image_path)
                    logger.debug("Inserted HTML image into picture placeholder")
                    break
                    
        except Exception as e:
            logger.warning(f"Error inserting HTML image: {e}")

    def _get_layout_index(self, slide_content: SlideContent) -> int:
        """Extract layout index from slide content"""
        try:
            if hasattr(slide_content, 'layout_index'):
                return slide_content.layout_index
            
            if hasattr(slide_content, 'content') and isinstance(slide_content.content, dict):
                if 'layout_index' in slide_content.content:
                    return int(slide_content.content['layout_index'])
            
            return 1  # Default to content layout
            
        except Exception:
            return 1

    def _clear_template_slides(self, presentation: Presentation):
        """Remove any existing slides from template"""
        try:
            while len(presentation.slides) > 0:
                rId = presentation.slides._sldIdLst[0].rId
                presentation.part.drop_rel(rId)
                del presentation.slides._sldIdLst[0]
            logger.debug("Cleared template slides")
        except Exception as e:
            logger.warning(f"Could not clear template slides: {e}")

    # Database and storage methods
    async def _upload_individual_slide(self, file_path, slide_id, project_id, slide_number, thumbnail_path):
        """Upload individual slide to storage"""
        try:
            from datetime import timedelta
            
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
            
            # Generate signed URL
            signed_url_result = self.db.client.storage.from_("presentations").create_signed_url(
                path=storage_path,
                expires_in=86400  # 24 hours
            )
            
            public_url = None
            if signed_url_result and 'signedURL' in signed_url_result:
                public_url = signed_url_result['signedURL']
            
            # Upload thumbnail if available
            thumbnail_url = None
            if thumbnail_path and os.path.exists(thumbnail_path):
                try:
                    with open(thumbnail_path, 'rb') as f:
                        thumbnail_content = f.read()
                    
                    thumbnail_filename = f"slide_{slide_number}_thumbnail.png"
                    thumbnail_storage_path = f"projects/{project_id}/thumbnails/{slide_id}/{thumbnail_filename}"
                    
                    self.db.client.storage.from_("presentations").upload(
                        path=thumbnail_storage_path,
                        file=thumbnail_content,
                        file_options={"content-type": "image/png"}
                    )
                    
                    thumbnail_signed = self.db.client.storage.from_("presentations").create_signed_url(
                        path=thumbnail_storage_path,
                        expires_in=86400
                    )
                    
                    if thumbnail_signed and 'signedURL' in thumbnail_signed:
                        thumbnail_url = thumbnail_signed['signedURL']
                        
                except Exception as e:
                    logger.warning(f"Failed to upload thumbnail: {e}")
            
            return {
                "storage_path": storage_path,
                "public_url": public_url,
                "file_size": file_size,
                "filename": filename,
                "thumbnail_url": thumbnail_url
            }
            
        except Exception as e:
            logger.error(f"Failed to upload individual slide: {e}")
            raise

    async def _update_slide_file_info(self, slide_id, project_id, storage_result):
        """Update database with slide file info"""
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
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "generator_version": "dual_path_v1.0"
                }
            }
            
            self.db.client.table("slide_files").insert(file_record).execute()
            logger.info(f"Updated database with file info for slide {slide_id}")
            
        except Exception as e:
            logger.error(f"Failed to update slide file info: {e}")
            raise

    async def _update_project_final_presentation(self, project_id, file_path, file_size, slides_count):
        """Update database with final presentation info"""
        try:
            update_data = {
                "final_presentation_path": file_path,
                "final_presentation_size": file_size,
                "final_presentation_slides": slides_count,
                "final_presentation_generated_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "generation_method": "dual_path_consistent"
            }
            
            self.db.client.table("projects").update(update_data).eq("id", project_id).execute()
            logger.info(f"Updated project {project_id} with final presentation info")
            
        except Exception as e:
            logger.error(f"Failed to update project final presentation info: {e}")
            raise

    async def _mark_slide_as_updated(self, slide_id: str, updated_content: SlideContent):
        """Mark slide as updated after regeneration"""
        try:
            update_data = {
                "updated_at": datetime.now().isoformat(),
                "regeneration_count": 1,  # Could increment this
                "last_modification": "user_adjustment"
            }
            self.db.client.table("slides").update(update_data).eq("id", slide_id).execute()
            logger.info(f"Marked slide {slide_id} as updated")
        except Exception as e:
            logger.error(f"Failed to mark slide as updated: {e}")


# Integration class for easy workflow adoption
class UnifiedPresentationWorkflow:
    """
    Unified workflow that provides both individual slides and complete presentations
    """
    
    def __init__(self, template_path: str):
        self.dual_generator = DualPathGenerator(template_path)
    
    async def generate_presentation_with_previews(
        self,
        project_id: str,
        slide_contents: List[SlideContent],
        output_path: str,
        layouts_info: Optional[Dict[str, Any]] = None,
        generate_previews: bool = True
    ) -> Dict[str, Any]:
        """
        Generate both individual slide previews AND final presentation
        using identical slide creation processes
        """
        results = {
            "individual_slides": [],
            "final_presentation": None,
            "success": False
        }
        
        try:
            # Step 1: Generate individual slides for preview (if requested)
            if generate_previews:
                logger.info("Generating individual slides for preview...")
                for i, slide_content in enumerate(slide_contents):
                    slide_id = f"slide_{project_id}_{i + 1}"
                    individual_result = await self.dual_generator.generate_individual_slide_for_preview(
                        slide_id=slide_id,
                        project_id=project_id,
                        slide_content=slide_content,
                        slide_number=i + 1,
                        layouts_info=layouts_info
                    )
                    results["individual_slides"].append(individual_result)
            
            # Step 2: Generate complete presentation using SAME process
            logger.info("Generating final presentation...")
            final_result = await self.dual_generator.generate_complete_presentation(
                project_id=project_id,
                output_path=output_path,
                slide_contents=slide_contents,
                layouts_info=layouts_info
            )
            
            results["final_presentation"] = final_result
            results["success"] = final_result["success"]
            
            return results
            
        except Exception as e:
            logger.error(f"Unified workflow failed: {e}")
            results["error"] = str(e)
            return results