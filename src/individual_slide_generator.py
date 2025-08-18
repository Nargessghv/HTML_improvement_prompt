"""
Individual Slide Generator

Implementation for generating individual PPTX files for each completed slide
and combining them while preserving slide-layout relationships.

Key Features:
- Individual slide generation with proper layout structure
- Content-based slide combination that preserves formatting
- Image extraction and reapplication
- LOCKED_ background handling
- Fallback mechanisms for robust operation

The combination process uses a content extraction and reapplication approach
instead of direct shape copying to maintain the slide-layout relationship
that provides proper styling, positioning, and theme inheritance.
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
from .debug_variables import get_variable_tracker

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
        
        # Initialize variable tracker
        self.variable_tracker = get_variable_tracker()

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
            
            # Track individual slide generation start
            self.variable_tracker.track_individual_slide(
                slide_id, slide_number, "generating",
                template_path=template_path,
                has_html_image=html_image_path is not None
            )
            
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
                self.variable_tracker.track_individual_slide(
                    slide_id, slide_number, "failed",
                    error="Failed to create PPTX file"
                )
                return {"success": False, "error": "Failed to create PPTX file"}
            
            # Upload to storage (no thumbnail generation - using online PPTX viewer instead)
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
            
            logger.info(f"✅ Successfully generated individual PPTX for slide {slide_number}")
            
            # Track successful completion
            self.variable_tracker.track_individual_slide(
                slide_id, slide_number, "completed",
                file_path=individual_pptx_path,
                storage_path=storage_result["storage_path"],
                file_url=storage_result["public_url"],
                file_size=storage_result["file_size"]
            )
            
            return {
                "success": True,
                "slide_id": slide_id,
                "file_path": individual_pptx_path,  # Return local path for further processing
                "storage_path": storage_result["storage_path"],
                "file_url": storage_result["public_url"],
                "file_size": storage_result["file_size"]
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to generate individual PPTX for slide {slide_number}: {e}")
            
            # Track failed slide generation
            self.variable_tracker.track_individual_slide(
                slide_id, slide_number, "failed",
                error=str(e)
            )
            
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
        Create a simple single-slide PPTX file with proper structure
        """
        try:
            # Create a fresh presentation from template
            prs = Presentation(template_path)
            
            # Clear existing slides using the same method as final deck generation
            while len(prs.slides) > 0:
                rId = prs.slides._sldIdLst[0].rId
                prs.part.drop_rel(rId)
                del prs.slides._sldIdLst[0]
            
            # Determine layout index from slide content
            layout_index = self._get_layout_index_from_content(slide_content)
            
            # Validate layout index
            print(f"🔍 Template has {len(prs.slide_layouts)} layouts available")
            print(f"🎯 Requested layout index: {layout_index}")
            
            if layout_index < 0 or layout_index >= len(prs.slide_layouts):
                print(f"⚠️ Invalid layout index {layout_index}, using default layout 0")
                layout_index = 0
            
            # Create new slide with proper layout
            slide_layout = prs.slide_layouts[layout_index]
            slide = prs.slides.add_slide(slide_layout)
            print(f"✅ Created slide with layout {layout_index}")
            
            # Apply content to the slide
            self._apply_content_to_slide(
                slide,
                slide_content,
                template_path,
                layouts_info,
                dynamic_models,
                slide_content.html_image_path if hasattr(slide_content, 'html_image_path') else None
            )
            
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"slide_{slide_number}_{timestamp}_{uuid.uuid4().hex[:8]}.pptx"
            file_path = self.temp_dir / filename
            
            # Note: Removed relationship rebuild as it may be causing corruption
            # The final deck generation doesn't do this and works correctly
            
            # Note: We don't cleanup empty placeholders as it can cause issues
            # The final deck generation handles this properly
            
            # CRITICAL FIX: Ensure grpSpPr is in the correct position
            # The grpSpPr element MUST come immediately after nvGrpSpPr in the XML structure
            for slide in prs.slides:
                try:
                    # Access the slide's shape tree XML
                    spTree = slide.shapes._spTree
                    
                    # Find nvGrpSpPr and grpSpPr elements
                    nvGrpSpPr = None
                    grpSpPr = None
                    
                    for child in spTree:
                        if child.tag.endswith('nvGrpSpPr'):
                            nvGrpSpPr = child
                        elif child.tag.endswith('grpSpPr'):
                            grpSpPr = child
                    
                    # If both exist and grpSpPr is not immediately after nvGrpSpPr, fix it
                    if nvGrpSpPr is not None and grpSpPr is not None:
                        nvGrpSpPr_index = list(spTree).index(nvGrpSpPr)
                        grpSpPr_index = list(spTree).index(grpSpPr)
                        
                        # Check if grpSpPr is not immediately after nvGrpSpPr
                        if grpSpPr_index != nvGrpSpPr_index + 1:
                            # Remove grpSpPr from its current position
                            spTree.remove(grpSpPr)
                            # Insert it right after nvGrpSpPr
                            spTree.insert(nvGrpSpPr_index + 1, grpSpPr)
                            print(f"✅ Fixed grpSpPr position in slide XML structure")
                            
                except Exception as e:
                    print(f"Warning: Could not fix grpSpPr position: {e}")
            
            # Force python-pptx to finalize all image relationships before saving
            # This ensures all image data is properly written to the internal XML
            try:
                # Access the presentation part to trigger any lazy loading
                _ = prs.part
                # Access all slide parts to ensure images are fully loaded
                for slide in prs.slides:
                    _ = slide.part
                    # Force relationship resolution for all shapes
                    for shape in slide.shapes:
                        try:
                            # Access shape properties to ensure they're materialized
                            _ = shape.shape_type
                            _ = shape.name
                            # For picture shapes, ensure the image is fully loaded
                            if hasattr(shape, 'image'):
                                _ = shape.image
                                # Access image properties to force loading
                                if shape.image:
                                    _ = shape.image.blob
                                    _ = shape.image.ext
                        except:
                            pass
                    
                    # Force slide's relationship collection to be fully resolved
                    try:
                        for rel in slide.part.rels.values():
                            _ = rel.target_part
                    except:
                        pass
                        
            except Exception as e:
                print(f"Note: Could not pre-access parts: {e}")
            
            # Save the presentation exactly like final deck generation
            prs.save(str(file_path))
            
            # Only verify file exists, don't try to re-open (matches final deck approach)
            if not file_path.exists():
                raise Exception(f"Failed to save PPTX file to {file_path}")
            
            logger.info(f"Created individual PPTX: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Error creating PPTX: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _cleanup_empty_placeholders(self, slide):
        """
        Clean up empty picture placeholders that can cause issues in single-slide presentations
        
        Args:
            slide: The slide to clean up
        """
        from pptx.enum.shapes import PP_PLACEHOLDER
        
        try:
            placeholders_to_remove = []
            
            # Find empty picture placeholders
            for placeholder in slide.placeholders:
                if hasattr(placeholder, 'placeholder_format'):
                    # Check if it's a picture placeholder
                    if placeholder.placeholder_format.type == PP_PLACEHOLDER.PICTURE:
                        # Check if it's empty (no image inserted)
                        has_image = False
                        try:
                            # If it has an image, this will succeed
                            if hasattr(placeholder, 'image') and placeholder.image:
                                has_image = True
                        except:
                            pass
                        
                        # Get placeholder name
                        placeholder_name = getattr(placeholder, 'name', '')
                        
                        # Only remove empty non-LOCKED picture placeholders
                        # LOCKED_ placeholders should already be filled with background images
                        # If they're empty, there was an issue finding/inserting the background
                        if not has_image and not placeholder_name.startswith('LOCKED_'):
                            placeholders_to_remove.append(placeholder)
                            print(f"  🧹 Cleaning up empty picture placeholder: {placeholder_name}")
            
            # Remove empty picture placeholders
            for placeholder in placeholders_to_remove:
                try:
                    # Remove from shapes collection
                    for shape in slide.shapes:
                        if shape == placeholder:
                            slide.shapes._spTree.remove(shape._element)
                            break
                except Exception as e:
                    print(f"  ⚠️ Could not remove placeholder: {e}")
                    # As fallback, try to make it invisible
                    try:
                        placeholder.width = 0
                        placeholder.height = 0
                    except:
                        pass
                        
        except Exception as e:
            print(f"  ⚠️ Error during placeholder cleanup: {e}")
            # Non-critical error, continue with saving

    def _apply_content_to_slide(
        self,
        slide,
        slide_content: SlideContent,
        template_path: str,
        layouts_info: Optional[Dict[str, Any]] = None,
        dynamic_models: Optional[Dict[str, Any]] = None,
        html_image_path: Optional[str] = None
    ):
        """
        Apply complete content to the slide using the proven SlideGenerator methods
        """
        try:
            content = slide_content.content if hasattr(slide_content, 'content') else {}
            
            # Process LOCKED_ placeholders - automatically add them based on layout
            # Use the template_path passed to this function (not resolve_template_path which gets default)
            template_folder = self.get_template_folder_from_path(template_path)
            
            if template_folder:
                # First, check what LOCKED_ files exist in the template folder
                template_folder_path = Path(template_folder)
                locked_files = list(template_folder_path.glob("LOCKED_*.png"))
                
                # Get the slide layout to check for LOCKED_ placeholders
                slide_layout = slide.slide_layout
                for layout_ph in slide_layout.placeholders:
                    ph_name = layout_ph.name
                    if ph_name and ph_name.startswith("LOCKED_"):
                        # Check if we have a PNG file for this LOCKED_ placeholder
                        png_path = template_folder_path / f"{ph_name}.png"
                        if png_path.exists():
                            # Auto-add the LOCKED_ background to content
                            content[ph_name] = str(png_path)
                            print(f"🔒 Auto-adding LOCKED_ background: {ph_name} -> {png_path}")
                        else:
                            print(f"⚠️ PNG file not found for {ph_name}: {png_path}")
                
                # Also process any LOCKED_ keys already in content (for backwards compatibility)
                content_copy = content.copy()
                for key in content_copy:
                    if key.startswith("LOCKED_"):
                        png_path = Path(template_folder) / f"{key}.png"
                        if png_path.exists() and key not in content:
                            content[key] = str(png_path)
                            print(f"🔒 Processing existing LOCKED_ key: {key} -> {png_path}")
            
            # Debug: Print available content
            print(f"🔍 Individual slide content keys: {list(content.keys())}")
            
            # Get layout index for this slide
            layout_index = slide_content.layout_index if hasattr(slide_content, 'layout_index') else 0
            
            # Map content using dynamic models if available, otherwise fall back to fuzzy matching
            if dynamic_models and layout_index in dynamic_models:
                print(f"🎯 Using dynamic model for exact placeholder matching (layout {layout_index})")
                dynamic_model = dynamic_models[layout_index]
                mapped_content = self._validate_content_with_dynamic_model(content, dynamic_model, layout_index)
            else:
                print(f"🔄 Using fallback fuzzy mapping (layout {layout_index})")
                if dynamic_models:
                    print(f"   Available dynamic models for layouts: {list(dynamic_models.keys())}")
                else:
                    print(f"   No dynamic models provided")
                mapped_content = self._map_content_to_placeholders(content, layouts_info, layout_index)
            
            # Use the proven SlideGenerator content application logic
            # Import here to avoid circular imports
            from .slide_generator import SlideGenerator
            
            # Create temporary SlideGenerator instance to use its proven methods
            slide_generator = SlideGenerator(template_path)
            
            # Log content mapping results for debugging
            print(f"📊 Content mapping summary:")
            print(f"   - Layout {layout_index}: {len(mapped_content)} fields mapped")
            print(f"   - Method used: {'Dynamic Model' if (dynamic_models and layout_index in dynamic_models) else 'Fuzzy Matching'}")
            if mapped_content:
                print(f"   - Mapped fields: {list(mapped_content.keys())}")
            
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
            
            # Use the proven _populate_slide_placeholders method with mapped content
            slide_generator._populate_slide_placeholders(slide, mapped_content)
            
            # Handle HTML image insertion if available
            if html_image_path and os.path.exists(html_image_path):
                print(f"📸 Inserting HTML rendered image: {html_image_path}")
                self._insert_html_image_into_slide(slide, html_image_path)
            
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
            # Find picture placeholders - look for both PICTURE type and named placeholders
            picture_placeholders = []
            html_specific_placeholder = None
            
            for placeholder in slide.placeholders:
                # Check if it's specifically named for HTML pictures
                if hasattr(placeholder, 'name'):
                    placeholder_name = placeholder.name.lower()
                    if 'picture from html' in placeholder_name or 'html' in placeholder_name:
                        html_specific_placeholder = placeholder
                        print(f"✅ Found HTML-specific placeholder: {placeholder.name}")
                        break
                
                # Also check for generic picture placeholders
                if hasattr(placeholder, 'placeholder_format'):
                    if placeholder.placeholder_format.type == PP_PLACEHOLDER.PICTURE:
                        picture_placeholders.append(placeholder)
            
            # Use HTML-specific placeholder if found, otherwise use first picture placeholder
            if html_specific_placeholder:
                placeholder = html_specific_placeholder
                print(f"📸 Using HTML-specific placeholder for image insertion")
            elif picture_placeholders:
                placeholder = picture_placeholders[0]
                print(f"📸 Using generic picture placeholder for image insertion")
            else:
                print(f"⚠️ No picture placeholder found for HTML image")
                
                # Fallback: Add image directly to slide if no placeholder found
                from pptx.util import Inches
                left = Inches(0.5)
                top = Inches(1.5)
                width = Inches(9)
                height = Inches(5)
                slide.shapes.add_picture(html_image_path, left, top, width=width, height=height)
                print(f"📸 Added HTML image directly to slide (no placeholder)")
                return
            
            # Insert image into the found placeholder
            # Import here to avoid circular imports
            from .slide_generator import SlideGenerator
            # We need a dummy template path for the SlideGenerator instance
            slide_generator = SlideGenerator("dummy_template.pptx")
            slide_generator._insert_image_into_placeholder(placeholder, html_image_path)
            print(f"✅ Inserted HTML image into placeholder: {placeholder.name if hasattr(placeholder, 'name') else 'unnamed'}")
                
        except Exception as e:
            print(f"⚠️ Error inserting HTML image: {e}")
    
    def _validate_content_with_dynamic_model(self, content: Dict[str, str], dynamic_model, layout_index: int) -> Dict[str, str]:
        """
        Validate and map content using dynamic Pydantic model for exact placeholder matching
        
        Args:
            content: Original content dictionary
            dynamic_model: Pydantic model class for the layout
            layout_index: Layout index for logging
            
        Returns:
            Validated content dictionary with exact field names
        """
        try:
            print(f"🎯 Using dynamic model for layout {layout_index} - exact placeholder matching")
            
            # Get the model's field names (these are exact placeholder names)
            model_fields = list(dynamic_model.__fields__.keys())
            print(f"📋 Dynamic model expects fields: {model_fields}")
            print(f"📋 Content provides fields: {list(content.keys())}")
            
            # Create validated content dict with only matching fields
            validated_content = {}
            matched_fields = []
            unmatched_content = []
            
            # Direct field matching - content keys should exactly match model fields
            for field_name in model_fields:
                if field_name in content:
                    validated_content[field_name] = content[field_name]
                    matched_fields.append(field_name)
                    print(f"✅ Exact match: '{field_name}'")
                else:
                    # Field expected by model but not in content
                    print(f"⚠️ Missing content for field: '{field_name}'")
            
            # Check for content that doesn't match any model field
            for content_key in content.keys():
                if content_key not in model_fields:
                    unmatched_content.append(content_key)
                    print(f"⚠️ Unmatched content key: '{content_key}' (not in dynamic model)")
            
            # Handle LOCKED_ content (should be preserved even if not in model)
            for content_key, content_value in content.items():
                if content_key.startswith('LOCKED_') and content_key not in validated_content:
                    validated_content[content_key] = content_value
                    print(f"🔒 Preserved LOCKED_ content: '{content_key}'")
            
            print(f"🎯 Dynamic model validation: {len(matched_fields)} exact matches, {len(unmatched_content)} unmatched")
            
            # Try to validate with the Pydantic model to catch any issues
            try:
                # Create a dict with all model fields, using empty strings for missing ones
                model_input = {}
                for field_name in model_fields:
                    model_input[field_name] = validated_content.get(field_name, "")
                
                # Validate with Pydantic model
                validated_model = dynamic_model(**model_input)
                print(f"✅ Pydantic model validation successful")
                
                # Return only non-empty fields plus LOCKED_ content
                final_content = {}
                for key, value in validated_content.items():
                    if value or key.startswith('LOCKED_'):
                        final_content[key] = value
                
                return final_content
                
            except Exception as validation_error:
                print(f"⚠️ Pydantic validation warning: {validation_error}")
                # Still return the matched content even if validation has issues
                return validated_content
            
        except Exception as e:
            print(f"❌ Dynamic model validation failed: {e}")
            print(f"🔄 Falling back to original content")
            return content

    def _map_content_to_placeholders(self, content: Dict[str, str], layouts_info: Dict[str, Any], layout_index: int = 0) -> Dict[str, str]:
        """
        Map content keys to actual placeholder names based on layouts_info
        
        Args:
            content: Original content dictionary
            layouts_info: Layout analysis information
            layout_index: Index of the layout being used
            
        Returns:
            Mapped content dictionary with placeholder names as keys
        """
        mapped_content = {}
        
        if not layouts_info or layout_index not in layouts_info:
            print(f"🔧 No layout info available, using original content keys")
            return content
        
        layout_info = layouts_info[layout_index]
        placeholders = layout_info.get('placeholders', [])
        placeholder_names = [ph.get('name', '') for ph in placeholders]
        
        print(f"🎯 Layout {layout_index} has placeholders: {placeholder_names}")
        
        # Define mapping rules from content keys to common placeholder patterns
        content_mappings = {
            'title': ['title', 'slide_title', 'heading', 'header'],
            'key_points': ['content', 'body', 'text', 'bullet_points', 'points'],
            'main_content': ['content', 'body', 'text', 'main_text'],
            'notes': ['notes', 'speaker_notes', 'footnote'],
            'subtitle': ['subtitle', 'subheading', 'sub_title'],
            'content_type': [],  # Skip this meta field
            'layout_type': [],   # Skip this meta field
            'slide_number': [],  # Skip this meta field
            'html_visualization': []  # This will be handled separately as an image
        }
        
        # First, copy LOCKED_ content directly
        for key, value in content.items():
            if key.startswith('LOCKED_'):
                mapped_content[key] = value
                print(f"🔒 Mapped LOCKED_ content: {key}")
        
        # Map regular content
        for content_key, content_value in content.items():
            if content_key.startswith('LOCKED_') or content_key in ['content_type', 'layout_type', 'slide_number', 'html_visualization']:
                continue
                
            possible_names = content_mappings.get(content_key, [content_key])
            mapped = False
            
            # Try to find matching placeholder
            for possible_name in possible_names:
                for placeholder_name in placeholder_names:
                    if (possible_name.lower() in placeholder_name.lower() or 
                        placeholder_name.lower() in possible_name.lower()):
                        mapped_content[placeholder_name] = content_value
                        print(f"✅ Mapped '{content_key}' -> '{placeholder_name}'")
                        mapped = True
                        break
                if mapped:
                    break
            
            if not mapped:
                # Use original key as fallback
                mapped_content[content_key] = content_value
                print(f"⚠️ No mapping found for '{content_key}', using original key")
        
        return mapped_content

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
            print(f"🔍 DEBUG: slide_content.__dict__ = {slide_content.__dict__ if hasattr(slide_content, '__dict__') else 'No __dict__'}")
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
            
            # No thumbnail upload - using online PowerPoint viewer instead
            
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
            # Update slides table with file info and completed status
            slide_update = {
                "individual_pptx_path": storage_result["storage_path"],
                "individual_pptx_url": storage_result["public_url"],
                "individual_pptx_size": storage_result["file_size"],
                "individual_pptx_generated_at": datetime.now().isoformat(),
                "status": "completed",
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
            
            # Note: No thumbnail generation - using online PowerPoint viewer instead
            
            logger.info(f"Updated database with file info for slide {slide_id}")
            
        except Exception as e:
            logger.error(f"Failed to update database with file info: {e}")
            raise

    async def combine_individual_slides(
        self,
        project_id: str,
        output_path: str,
        template_path: str,
        dynamic_models: Optional[Dict[int, Any]] = None,
        layouts_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Combine all individual slides into a final presentation by recreating them from stored content
        
        This method now uses the original content from the database instead of copying from PPTX files,
        which preserves the layout-placeholder relationships and maintains proper styling.
        
        Args:
            project_id: Project identifier
            output_path: Path where to save the final presentation
            template_path: Path to the PowerPoint template
            dynamic_models: Optional dictionary of dynamic Pydantic models for precise content mapping
        
        Returns:
            Dictionary with success status and operation details
        """
        try:
            logger.info(f"Combining individual slides for project {project_id}")
            
            # Store template path for use in content application
            self._current_template_path = template_path
            
            # Log dynamic model availability
            if dynamic_models:
                logger.info(f"🎯 Dynamic models available for layouts: {list(dynamic_models.keys())}")
            else:
                logger.info("🔄 Using fuzzy matching for placeholder mapping")
            
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
                    
                    logger.info(f"Processing slide {slide_number} (ID: {slide_id})")
                    
                    # CRITICAL FIX: Get layout_index from the database correctly
                    # The layout_index is stored at the top level of slide_data, not in content
                    layout_index = slide_data.get("layout_index", 0)
                    print(f"✅ Layout index retrieved from database: {layout_index}")
                    
                    # Log what we're getting from the database
                    logger.info(f"Database slide_data keys: {list(slide_data.keys())}")
                    logger.info(f"Retrieved layout_index from database: {layout_index}")
                    
                    # Recreate the SlideContent object from database
                    slide_content = SlideContent(
                        content=slide_data.get("content", {}),
                        layout_index=layout_index
                    )
                    
                    # Check for refined HTML image if available
                    html_image_path = None
                    latest_refinement = self.db.get_latest_refinement(slide_id)
                    if latest_refinement and latest_refinement.get("image_url"):
                        # Download the refined HTML image
                        html_image_path = await self._download_refined_image(
                            latest_refinement["image_url"], 
                            slide_id, 
                            slide_number
                        )
                        if html_image_path:
                            logger.info(f"Using refined HTML image for slide {slide_number}")
                    
                    # Use the layout_index we retrieved from the database
                    if layout_index < 0 or layout_index >= len(final_prs.slide_layouts):
                        logger.warning(f"Invalid layout index {layout_index}, using default layout 0")
                        layout_index = 0
                    
                    logger.info(f"Creating slide with layout index: {layout_index}")
                    
                    # Create new slide with correct layout
                    slide_layout = final_prs.slide_layouts[layout_index]
                    new_slide = final_prs.slides.add_slide(slide_layout)
                    
                    # Apply content using the same proven method used for individual slides
                    self._apply_content_to_slide(
                        new_slide,
                        slide_content,
                        template_path,
                        layouts_info,
                        dynamic_models,
                        html_image_path
                    )
                    
                    slides_combined += 1
                    logger.info(f"✅ Successfully added slide {slide_number} to final presentation")
                        
                except Exception as e:
                    logger.error(f"❌ Error adding slide {slide_data.get('slide_number', 'unknown')}: {e}")
                    import traceback
                    traceback.print_exc()
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
            
            result = {
                "success": True,
                "output_path": output_path,
                "slides_combined": slides_combined,
                "total_slides": len(completed_slides),
                "file_size": file_size,
                "message": f"Combined {slides_combined} slides using content-based approach"
            }
            
            # Track final presentation results
            self.variable_tracker.track_final_presentation(result)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to combine slides: {e}")
            import traceback
            traceback.print_exc()
            
            result = {
                "success": False,
                "error": str(e),
                "slides_combined": 0
            }
            
            # Track failed final presentation
            self.variable_tracker.track_final_presentation(result)
            
            return result

    async def _download_refined_image(
        self,
        image_url: str,
        slide_id: str,
        slide_number: int
    ) -> Optional[str]:
        """
        Download refined HTML image from URL to temporary location
        
        Args:
            image_url: URL of the refined image
            slide_id: Slide ID for naming
            slide_number: Slide number for logging
            
        Returns:
            Path to downloaded image file or None if download failed
        """
        import tempfile
        import requests
        
        try:
            if not image_url:
                return None
                
            # Download image
            logger.info(f"Downloading refined HTML image for slide {slide_number}")
            response = requests.get(image_url, stream=True)
            response.raise_for_status()
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png', prefix=f'slide_{slide_number}_') as temp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    temp_file.write(chunk)
                temp_path = temp_file.name
                
            logger.info(f"Downloaded refined image to: {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"Failed to download refined image: {e}")
            return None

    # All deprecated slide copying methods have been removed
    # The system now uses content-based reconstruction from database
    
    def cleanup_temp_files(
        self,
        final_prs: Presentation,
        pptx_source_url: str,
        slide_number: int,
        source_type: str,
        layout_index: int = 0
    ) -> bool:
        """
        Download and combine a single slide from its PPTX source using content-based approach
        
        This method preserves the slide-layout relationship by:
        1. Extracting content from the source slide's placeholders
        2. Creating a fresh slide with the correct layout in the final presentation
        3. Applying content using the proven SlideGenerator methods
        
        Args:
            final_prs: The final presentation to add slides to
            pptx_source_url: URL or path to the source PPTX file
            slide_number: Slide number for logging
            source_type: Type of source ("refinement" or "individual")
            layout_index: Layout index to use for the slide
            
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
            
            # Extract content from the source slide
            source_slide = source_prs.slides[0]
            extracted_content = self._extract_slide_content_DEPRECATED(source_slide)
            
            if not extracted_content:
                logger.warning(f"No content extracted from slide {slide_number}")
                return False
            
            # Validate layout index
            if layout_index < 0 or layout_index >= len(final_prs.slide_layouts):
                logger.warning(f"⚠️ Invalid layout index {layout_index} for slide {slide_number}, using default layout 0")
                layout_index = 0
            else:
                logger.info(f"✅ Using layout {layout_index} for slide {slide_number}")
            
            # Create a fresh slide with the correct layout
            target_layout = final_prs.slide_layouts[layout_index]
            new_slide = final_prs.slides.add_slide(target_layout)
            
            # Apply the extracted content using proven methods
            self._apply_extracted_content_to_slide_DEPRECATED(new_slide, extracted_content, layout_index)
            
            logger.info(f"✅ Successfully combined slide {slide_number} preserving layout relationship")
            
            # Clean up temporary file if we downloaded it
            if temp_pptx_path != pptx_source_url and temp_pptx_path and os.path.exists(temp_pptx_path):
                try:
                    os.unlink(temp_pptx_path)
                except:
                    pass
            
            return True
            
        except Exception as e:
            logger.error(f"Error combining slide {slide_number} from {source_type}: {e}")
            import traceback
            traceback.print_exc()
            
            # Clean up temporary file on error
            if temp_pptx_path and temp_pptx_path != pptx_source_url and os.path.exists(temp_pptx_path):
                try:
                    os.unlink(temp_pptx_path)
                except:
                    pass
            
            return False
    
    def _extract_slide_content_DEPRECATED(self, source_slide) -> Dict[str, str]:
        """
        Extract content from a source slide's placeholders and shapes
        
        This method extracts:
        1. Text content from placeholders
        2. Image paths from picture shapes
        3. Special content like LOCKED_ backgrounds
        
        Args:
            source_slide: Source slide to extract content from
            
        Returns:
            Dictionary mapping placeholder names/types to content
        """
        extracted_content = {}
        
        try:
            # Extract content from placeholders
            for placeholder in source_slide.placeholders:
                try:
                    placeholder_name = getattr(placeholder, 'name', None)
                    placeholder_idx = getattr(placeholder.placeholder_format, 'idx', None)
                    placeholder_type = getattr(placeholder.placeholder_format, 'type', None)
                    
                    # Generate a content key - prefer name, fall back to type-based naming
                    if placeholder_name:
                        content_key = placeholder_name
                    elif placeholder_type is not None:
                        content_key = f"placeholder_{placeholder_type}_{placeholder_idx}"
                    else:
                        content_key = f"placeholder_{placeholder_idx}"
                    
                    # Extract text content
                    if hasattr(placeholder, 'text_frame') and placeholder.text_frame:
                        if placeholder.text_frame.text.strip():
                            extracted_content[content_key] = placeholder.text_frame.text
                            logger.debug(f"Extracted text from {content_key}: {placeholder.text_frame.text[:50]}...")
                    
                    # Extract image content for picture placeholders
                    elif hasattr(placeholder, 'placeholder_format'):
                        from pptx.enum.shapes import PP_PLACEHOLDER
                        if placeholder.placeholder_format.type == PP_PLACEHOLDER.PICTURE:
                            # Check if this placeholder has been filled with an image
                            # For picture placeholders, check if they contain shapes (indicating filled)
                            logger.debug(f"Found picture placeholder: {content_key}")
                            
                            # Special handling for LOCKED_ placeholders
                            if placeholder_name and placeholder_name.startswith("LOCKED_"):
                                # For LOCKED_ placeholders, we'll try to extract the image
                                try:
                                    # Check if this placeholder has been replaced with an image shape
                                    for shape in source_slide.shapes:
                                        if (hasattr(shape, 'image') and 
                                            hasattr(shape, 'name') and 
                                            shape.name == placeholder_name):
                                            image_path = self._extract_image_from_shape_DEPRECATED(shape, placeholder_name)
                                            if image_path:
                                                extracted_content[placeholder_name] = image_path
                                                logger.debug(f"Extracted LOCKED_ image: {placeholder_name}")
                                            break
                                except Exception as e:
                                    logger.debug(f"Error extracting LOCKED_ image: {e}")
                    
                except Exception as e:
                    logger.debug(f"Error extracting from placeholder: {e}")
                    continue
            
            # Extract content from non-placeholder shapes (like images, textboxes)
            for shape in source_slide.shapes:
                try:
                    # Skip placeholders (already handled above)
                    if hasattr(shape, 'placeholder_format'):
                        continue
                    
                    # Extract text from textboxes
                    if hasattr(shape, 'text_frame') and shape.text_frame:
                        if shape.text_frame.text.strip():
                            shape_name = getattr(shape, 'name', f"textbox_{shape.shape_id}")
                            extracted_content[shape_name] = shape.text_frame.text
                            logger.debug(f"Extracted text from shape {shape_name}")
                    
                    # Extract images
                    elif hasattr(shape, 'image'):
                        try:
                            # Extract the image data and save it temporarily
                            shape_name = getattr(shape, 'name', f"image_{shape.shape_id}")
                            image_path = self._extract_image_from_shape_DEPRECATED(shape, shape_name)
                            if image_path:
                                extracted_content[shape_name] = image_path
                                logger.debug(f"Extracted image from shape {shape_name}: {image_path}")
                        except Exception as e:
                            logger.debug(f"Error extracting image from shape: {e}")
                            pass
                            
                except Exception as e:
                    logger.debug(f"Error extracting from shape: {e}")
                    continue
            
            logger.info(f"Extracted {len(extracted_content)} content items from slide")
            return extracted_content
            
        except Exception as e:
            logger.error(f"Error extracting slide content: {e}")
            return {}
    
    def _apply_extracted_content_to_slide_DEPRECATED(self, target_slide, extracted_content: Dict[str, str], layout_index: int):
        """
        Apply extracted content to a target slide using the proven SlideGenerator methods
        
        This method:
        1. Uses the existing _apply_content_to_slide method from individual slide generation
        2. Leverages the proven placeholder mapping logic
        3. Maintains all the formatting and styling benefits
        
        Args:
            target_slide: Target slide to apply content to
            extracted_content: Dictionary of extracted content
            layout_index: Layout index for the slide
        """
        try:
            # Create a SlideContent object to use with the proven method
            from .llm_client import SlideContent
            
            # Create a SlideContent object with the extracted content
            slide_content = SlideContent(
                content=extracted_content,
                layout_index=layout_index
            )
            
            # Use the proven _apply_content_to_slide method
            # This leverages all the existing logic for placeholder mapping, LOCKED_ backgrounds, etc.
            self._apply_content_to_slide(
                slide=target_slide,
                slide_content=slide_content,
                template_path=self.get_template_path_from_final_presentation(target_slide),
                layouts_info=None,  # Will use fallback fuzzy matching
                dynamic_models=None,  # Will use fallback fuzzy matching
                html_image_path=None  # No HTML images in this case
            )
            
            logger.info(f"Successfully applied extracted content to slide using proven methods")
            
        except Exception as e:
            logger.error(f"Error applying extracted content: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback: apply content directly to placeholders
            self._apply_content_directly_to_placeholders(target_slide, extracted_content)
    
    def _apply_content_directly_to_placeholders(self, target_slide, content: Dict[str, str]):
        """
        Fallback method: Apply content directly to placeholders by name/index matching
        
        Args:
            target_slide: Target slide to apply content to
            content: Dictionary of content to apply
        """
        try:
            logger.info("Using fallback direct placeholder mapping")
            
            # Create mapping of placeholder names and indices to placeholder objects
            placeholder_map = {}
            
            for placeholder in target_slide.placeholders:
                # Map by name if available
                if hasattr(placeholder, 'name') and placeholder.name:
                    placeholder_map[placeholder.name] = placeholder
                
                # Map by index
                if hasattr(placeholder, 'placeholder_format'):
                    idx = placeholder.placeholder_format.idx
                    placeholder_map[f"placeholder_{idx}"] = placeholder
                    
                    # Map by type_index combination
                    if hasattr(placeholder.placeholder_format, 'type'):
                        ptype = placeholder.placeholder_format.type
                        placeholder_map[f"placeholder_{ptype}_{idx}"] = placeholder
            
            # Apply content to matching placeholders
            applied_count = 0
            for content_key, content_value in content.items():
                if content_key in placeholder_map:
                    placeholder = placeholder_map[content_key]
                    
                    # Apply text content
                    if hasattr(placeholder, 'text_frame') and placeholder.text_frame:
                        placeholder.text_frame.text = content_value
                        applied_count += 1
                        logger.debug(f"Applied content to {content_key}")
            
            logger.info(f"Applied {applied_count}/{len(content)} content items using fallback method")
            
        except Exception as e:
            logger.error(f"Error in fallback content application: {e}")
    
    def get_template_path_from_final_presentation(self, slide) -> str:
        """
        Determine the template path to use for the given slide
        
        This is needed for the _apply_content_to_slide method
        
        Args:
            slide: PowerPoint slide object
            
        Returns:
            Template path string
        """
        # Use the template path that was passed to combine_individual_slides
        return getattr(self, '_current_template_path', "/path/to/template.pptx")
    
    def _extract_image_from_shape_DEPRECATED(self, shape, shape_name: str) -> Optional[str]:
        """
        Extract image data from a shape and save it temporarily
        
        Args:
            shape: PowerPoint shape containing an image
            shape_name: Name for the temporary image file
            
        Returns:
            Path to the temporary image file, or None if extraction failed
        """
        try:
            # Get image data
            image_bytes = shape.image.blob
            
            # Determine file extension from image format
            # Default to PNG if we can't determine the format
            file_extension = ".png"
            try:
                # Try to determine format from image headers
                if image_bytes.startswith(b'\xff\xd8\xff'):
                    file_extension = ".jpg"
                elif image_bytes.startswith(b'\x89PNG'):
                    file_extension = ".png"
                elif image_bytes.startswith(b'GIF'):
                    file_extension = ".gif"
            except:
                pass
            
            # Create temporary file
            temp_dir = self.temp_dir / "extracted_images"
            temp_dir.mkdir(exist_ok=True)
            
            temp_filename = f"{shape_name}_{uuid.uuid4().hex[:8]}{file_extension}"
            temp_path = temp_dir / temp_filename
            
            # Save image data
            with open(temp_path, 'wb') as f:
                f.write(image_bytes)
            
            logger.debug(f"Extracted image to: {temp_path}")
            return str(temp_path)
            
        except Exception as e:
            logger.debug(f"Failed to extract image from shape {shape_name}: {e}")
            return None
    
    def _copy_slide_content(self, source_slide, target_slide):
        """
        IMPROVED: Copy ALL content from source slide to target slide preserving formatting
        
        This method now properly preserves:
        - All shapes and their properties
        - Images and their positions
        - Text formatting (fonts, colors, sizes) WITHOUT fallbacks
        - Theme color relationships
        - Z-order of elements
        - LOCKED_ backgrounds
        
        Args:
            source_slide: Source slide to copy from
            target_slide: Target slide to copy to
        """
        from pptx.enum.shapes import MSO_SHAPE_TYPE
        import io
        
        try:
            logger.info("Starting enhanced slide content copying with formatting preservation")
            
            # IMPROVED: Clear target slide more safely
            self._clear_slide_shapes_safely(target_slide)
            
            # Copy shapes in order to preserve z-order
            copied_shapes = 0
            for shape_index, source_shape in enumerate(source_slide.shapes):
                try:
                    if self._copy_single_shape_with_formatting(source_shape, target_slide, shape_index):
                        copied_shapes += 1
                except Exception as shape_error:
                    logger.warning(f"Failed to copy shape {shape_index}: {shape_error}")
                    continue
            
            logger.info(f"Successfully copied {copied_shapes}/{len(source_slide.shapes)} shapes with formatting")
                    
        except Exception as e:
            logger.error(f"Error copying slide content: {e}")
            raise

    def _clear_slide_shapes_safely(self, slide):
        """Safely clear shapes from slide while preserving structure"""
        shapes_to_remove = list(slide.shapes)
        for shape in reversed(shapes_to_remove):
            try:
                slide.shapes._spTree.remove(shape._element)
            except Exception as e:
                logger.debug(f"Could not remove shape: {e}")

    def _copy_single_shape_with_formatting(self, source_shape, target_slide, shape_index):
        """Copy a single shape preserving ALL formatting properties"""
        from pptx.enum.shapes import MSO_SHAPE_TYPE
        
        try:
            shape_type = source_shape.shape_type
            
            if shape_type == MSO_SHAPE_TYPE.PICTURE or hasattr(source_shape, 'image'):
                return self._copy_picture_shape_enhanced(source_shape, target_slide)
            
            elif hasattr(source_shape, 'text_frame') and source_shape.text_frame:
                return self._copy_text_shape_enhanced(source_shape, target_slide)
            
            elif hasattr(source_shape, 'placeholder_format'):
                return self._copy_placeholder_shape_enhanced(source_shape, target_slide)
            
            else:
                logger.debug(f"Skipping unsupported shape type: {shape_type}")
                return False
                
        except Exception as e:
            logger.warning(f"Error copying shape {shape_index}: {e}")
            return False

    def _copy_picture_shape_enhanced(self, source_shape, target_slide):
        """Enhanced picture copying with better error handling"""
        try:
            # Multiple methods to extract image data
            image_bytes = None
            
            # Method 1: Direct image access
            if hasattr(source_shape, 'image'):
                try:
                    image_bytes = source_shape.image.blob
                except:
                    pass
            
            # Method 2: Through relationships
            if not image_bytes:
                try:
                    slide_part = source_shape.part
                    # Look for blip relationship
                    blip_rIds = source_shape._element.xpath('.//a:blip/@r:embed')
                    if blip_rIds:
                        blip_rId = blip_rIds[0]
                        image_rel = slide_part.rels[blip_rId]
                        image_bytes = image_rel.target_part.blob
                except Exception as e:
                    logger.debug(f"Method 2 failed: {e}")
            
            # Method 3: Legacy approach
            if not image_bytes:
                try:
                    image_part = source_shape._element.blip_rId
                    if image_part:
                        slide_part = source_shape.part
                        image_rel = slide_part.rels[image_part]
                        image_bytes = image_rel.target_part.blob
                except Exception as e:
                    logger.debug(f"Method 3 failed: {e}")
            
            if image_bytes:
                # Add picture with exact dimensions
                target_slide.shapes.add_picture(
                    io.BytesIO(image_bytes),
                    source_shape.left,
                    source_shape.top,
                    source_shape.width,
                    source_shape.height
                )
                logger.debug("Successfully copied picture shape")
                return True
            else:
                logger.warning("Could not extract image data from source shape")
                return False
                
        except Exception as e:
            logger.warning(f"Failed to copy picture shape: {e}")
            return False

    def _copy_text_shape_enhanced(self, source_shape, target_slide):
        """CRITICAL: Enhanced text shape copying that preserves ALL formatting"""
        try:
            # Create target text box with exact dimensions
            target_shape = target_slide.shapes.add_textbox(
                source_shape.left,
                source_shape.top,
                source_shape.width,
                source_shape.height
            )
            
            source_tf = source_shape.text_frame
            target_tf = target_shape.text_frame
            
            # Copy text frame properties first
            self._copy_text_frame_properties(source_tf, target_tf)
            
            # Clear target and copy content
            target_tf.clear()
            
            # Copy all paragraphs with complete formatting preservation
            for para_idx, source_para in enumerate(source_tf.paragraphs):
                if para_idx == 0:
                    target_para = target_tf.paragraphs[0]
                else:
                    target_para = target_tf.add_paragraph()
                
                # Copy paragraph with ALL formatting
                self._copy_paragraph_with_complete_formatting(source_para, target_para)
            
            logger.debug("Successfully copied text shape with enhanced formatting")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to copy text shape: {e}")
            return False

    def _copy_paragraph_with_complete_formatting(self, source_para, target_para):
        """Copy paragraph preserving ALL formatting without fallbacks"""
        try:
            # Copy paragraph-level properties
            target_para.alignment = source_para.alignment
            target_para.level = source_para.level
            
            # Copy paragraph spacing if available
            if hasattr(source_para, 'space_before'):
                try:
                    target_para.space_before = source_para.space_before
                except:
                    pass
            if hasattr(source_para, 'space_after'):
                try:
                    target_para.space_after = source_para.space_after
                except:
                    pass
            
            # Clear target paragraph and copy runs
            target_para.clear()
            
            # Copy all runs with complete formatting
            for source_run in source_para.runs:
                target_run = target_para.add_run()
                target_run.text = source_run.text
                
                # CRITICAL: Copy font properties without fallbacks
                self._copy_font_properties_enhanced(source_run.font, target_run.font)
                
        except Exception as e:
            logger.debug(f"Error copying paragraph formatting: {e}")

    def _copy_font_properties_enhanced(self, source_font, target_font):
        """
        CRITICAL FIX: Copy font properties without destructive fallbacks
        
        This method preserves original formatting by:
        1. Only copying properties that actually exist
        2. Not applying fallback values that override original formatting
        3. Preserving theme color relationships
        """
        try:
            # Copy font name only if it exists
            if hasattr(source_font, 'name') and source_font.name:
                target_font.name = source_font.name
            
            # CRITICAL: Copy font size only if it exists - NO FALLBACKS
            if hasattr(source_font, 'size') and source_font.size is not None:
                target_font.size = source_font.size
            # DO NOT set fallback size - let it inherit from theme/layout
            
            # Copy style properties only if explicitly set
            if hasattr(source_font, 'bold') and source_font.bold is not None:
                target_font.bold = source_font.bold
            
            if hasattr(source_font, 'italic') and source_font.italic is not None:
                target_font.italic = source_font.italic
            
            if hasattr(source_font, 'underline') and source_font.underline is not None:
                target_font.underline = source_font.underline
            
            # CRITICAL: Enhanced color copying that preserves theme relationships
            if hasattr(source_font, 'color') and source_font.color:
                self._copy_color_properties_enhanced(source_font.color, target_font.color)
            
            logger.debug("Enhanced font properties copied successfully")
            
        except Exception as e:
            logger.debug(f"Some font properties could not be copied: {e}")

    def _copy_color_properties_enhanced(self, source_color, target_color):
        """Enhanced color copying that preserves theme relationships"""
        try:
            # Priority 1: RGB color (explicit color)
            if hasattr(source_color, 'rgb') and source_color.rgb is not None:
                target_color.rgb = source_color.rgb
                return
            
            # Priority 2: Theme color (preserves theme relationships)
            if hasattr(source_color, 'theme_color') and source_color.theme_color is not None:
                target_color.theme_color = source_color.theme_color
                
                # Copy brightness/tint if available
                if hasattr(source_color, 'brightness') and source_color.brightness is not None:
                    try:
                        target_color.brightness = source_color.brightness
                    except:
                        pass
                return
            
            # Priority 3: Scheme color
            if hasattr(source_color, 'scheme_color') and source_color.scheme_color is not None:
                target_color.scheme_color = source_color.scheme_color
                return
            
            # If no explicit color is set, don't set anything - let it inherit
            logger.debug("No explicit color found - preserving inheritance")
            
        except Exception as e:
            logger.debug(f"Could not copy color properties: {e}")

    def _copy_text_frame_properties(self, source_tf, target_tf):
        """Copy text frame properties like margins and word wrap"""
        try:
            # Copy margin properties if they exist
            margin_properties = ['margin_left', 'margin_right', 'margin_top', 'margin_bottom']
            for prop in margin_properties:
                if hasattr(source_tf, prop):
                    try:
                        setattr(target_tf, prop, getattr(source_tf, prop))
                    except:
                        pass
            
            # Copy other text frame properties
            other_properties = ['word_wrap', 'auto_size']
            for prop in other_properties:
                if hasattr(source_tf, prop):
                    try:
                        setattr(target_tf, prop, getattr(source_tf, prop))
                    except:
                        pass
                        
        except Exception as e:
            logger.debug(f"Some text frame properties could not be copied: {e}")

    def _copy_placeholder_shape_enhanced(self, source_shape, target_slide):
        """Enhanced placeholder handling"""
        try:
            if not hasattr(source_shape, 'placeholder_format'):
                return False
                
            ph_type = source_shape.placeholder_format.type
            ph_idx = getattr(source_shape.placeholder_format, 'idx', None)
            
            # Find matching placeholder in target
            target_placeholder = None
            for target_shape in target_slide.placeholders:
                if hasattr(target_shape, 'placeholder_format'):
                    target_ph = target_shape.placeholder_format
                    if target_ph.type == ph_type:
                        if ph_idx is None or getattr(target_ph, 'idx', None) == ph_idx:
                            target_placeholder = target_shape
                            break
            
            if target_placeholder and hasattr(source_shape, 'text_frame') and source_shape.text_frame:
                # Copy to placeholder preserving layout formatting
                return self._copy_text_to_placeholder(source_shape, target_placeholder)
            
            return False
            
        except Exception as e:
            logger.debug(f"Could not copy placeholder: {e}")
            return False

    def _copy_text_to_placeholder(self, source_shape, target_placeholder):
        """Copy text to placeholder while preserving layout-based formatting"""
        try:
            if not (hasattr(target_placeholder, 'text_frame') and target_placeholder.text_frame):
                return False
            
            source_tf = source_shape.text_frame
            target_tf = target_placeholder.text_frame
            
            # Clear target but preserve placeholder structure
            target_tf.clear()
            
            # Copy content with formatting
            for para_idx, source_para in enumerate(source_tf.paragraphs):
                if para_idx == 0:
                    target_para = target_tf.paragraphs[0]
                else:
                    target_para = target_tf.add_paragraph()
                
                # Copy paragraph with enhanced formatting
                self._copy_paragraph_with_complete_formatting(source_para, target_para)
            
            logger.debug("Successfully copied text to placeholder")
            return True
            
        except Exception as e:
            logger.debug(f"Could not copy text to placeholder: {e}")
            return False

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
    
    # LOCKED backgrounds are now handled by passing PNG paths directly as content
    # All SVG-related methods have been removed for simplification
    
    def get_template_folder_from_path(self, template_path: str) -> Optional[str]:
        """
        Extract template folder path from template file path
        
        Args:
            template_path: Path to the PPTX template file
            
        Returns:
            Path to the template folder containing PNG files for LOCKED_ placeholders
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