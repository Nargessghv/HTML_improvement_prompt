"""
Enhanced Slide Assembly Agent

This agent replaces the traditional SlideAssemblyAgent to use the dual-path approach
for generating both individual slides (for preview) and final presentation (for download)
with perfect formatting consistency.
"""

import asyncio
import logging
from typing import Dict, Any, Optional

from langchain_core.runnables import RunnableConfig

from .agents import SlideGenerationState
from .dual_path_generator import DualPathGenerator, UnifiedPresentationWorkflow
from .monitoring import slide_monitor, monitor_agent_execution

logger = logging.getLogger(__name__)


class EnhancedSlideAssemblyAgent:
    """
    Enhanced slide assembly agent that uses dual-path generation
    
    This agent:
    1. Generates individual slides for preview with perfect formatting
    2. Creates final presentation using the EXACT SAME process
    3. Ensures 100% consistency between preview and final
    4. Supports future slide regeneration after user adjustments
    """

    def __init__(self):
        self.name = "enhanced_slide_assembler"
        from .database import get_supabase_client
        self.db = get_supabase_client()

    @monitor_agent_execution("enhanced_slide_assembler")
    def execute(
        self, state: SlideGenerationState, config: Optional[RunnableConfig] = None
    ) -> SlideGenerationState:
        """
        Execute dual-path slide generation with perfect formatting consistency
        
        Args:
            state: Current workflow state with all generated content
            config: Optional configuration
            
        Returns:
            Updated state with both individual slides and final presentation
        """
        try:
            logger.info("🔄 Starting enhanced slide assembly with dual-path generation")
            
            # Extract required information from state
            template_path = state["template_path"]
            output_path = state["output_path"]
            slide_contents = state["slide_contents"]
            layouts_info = state["layouts_info"]
            
            # Validate inputs
            if not slide_contents:
                state["error_message"] = "No slide contents available for assembly"
                state["success"] = False
                return state
            
            if not template_path:
                state["error_message"] = "No template path provided"
                state["success"] = False
                return state
            
            logger.info(f"📊 Assembling {len(slide_contents)} slides using dual-path approach")
            
            # Initialize dual-path generator
            dual_generator = DualPathGenerator(template_path)
            
            # Generate both individual slides AND final presentation
            # Use synchronous dual-path generation to avoid event loop conflicts
            result = self._run_dual_path_synchronous(
                dual_generator=dual_generator,
                slide_contents=slide_contents,
                output_path=output_path,
                layouts_info=layouts_info,
                state=state
            )
            
            # Update state based on results
            if result["success"]:
                state["presentation_path"] = result["final_presentation"]["output_path"]
                state["individual_slides"] = result["individual_slides"]
                state["slide_count"] = result["final_presentation"]["slides_added"]
                state["success"] = True
                state["current_step"] = "assembly_completed"
                
                logger.info(f"✅ Enhanced assembly completed: {state['slide_count']} slides generated")
                logger.info(f"📄 Final presentation: {state['presentation_path']}")
                logger.info(f"📱 Individual slides: {len(result['individual_slides'])} for preview")
                
            else:
                state["error_message"] = result.get("error", "Unknown assembly error")
                state["success"] = False
                state["current_step"] = "assembly_failed"
                logger.error(f"❌ Enhanced assembly failed: {state['error_message']}")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Error in enhanced slide assembly: {e}")
            state["error_message"] = f"Assembly error: {str(e)}"
            state["success"] = False
            state["current_step"] = "assembly_error"
            return state

    async def _run_dual_path_generation(
        self,
        dual_generator: DualPathGenerator,
        slide_contents: list,
        output_path: str,
        layouts_info: Optional[Dict[str, Any]],
        state: SlideGenerationState
    ) -> Dict[str, Any]:
        """
        Run the dual-path generation process
        
        This creates both individual slides for preview AND the final presentation
        using the exact same slide creation process.
        """
        try:
            # Generate project ID for tracking
            project_id = state.get("project_id") or f"project_{state['topic'].replace(' ', '_')}"
            
            logger.info("🎯 Phase 1: Generating individual slides for preview...")
            
            # Generate individual slides for preview
            individual_results = []
            for i, slide_content in enumerate(slide_contents):
                try:
                    slide_id = f"slide_{project_id}_{i + 1}"
                    
                    # Check if slide has HTML content
                    html_image_path = None
                    if hasattr(slide_content, 'html_image_path'):
                        html_image_path = slide_content.html_image_path
                    
                    # If no html_image_path but we have project_id, try to fetch from database
                    if not html_image_path and project_id:
                        # Get the slide ID from database
                        slide_db_id = self._get_slide_id_from_database(project_id, i + 1)
                        if slide_db_id:
                            # Get the final refined HTML image path
                            html_image_path = self._get_final_html_image_path(project_id, slide_db_id)
                            if html_image_path:
                                logger.debug(f"Retrieved refined HTML image for slide {i + 1}: {html_image_path}")
                    
                    # Generate individual slide
                    individual_result = await dual_generator.generate_individual_slide_for_preview(
                        slide_id=slide_id,
                        project_id=project_id,
                        slide_content=slide_content,
                        slide_number=i + 1,
                        layouts_info=layouts_info,
                        html_image_path=html_image_path
                    )
                    
                    individual_results.append(individual_result)
                    
                    if individual_result["success"]:
                        logger.info(f"✅ Individual slide {i + 1} generated for preview")
                    else:
                        logger.warning(f"⚠️ Individual slide {i + 1} failed: {individual_result['error']}")
                        
                except Exception as e:
                    logger.error(f"❌ Error generating individual slide {i + 1}: {e}")
                    individual_results.append({"success": False, "error": str(e)})
            
            logger.info("🎯 Phase 2: Generating final presentation with identical process...")
            
            # Attach HTML image paths to slide_contents for final presentation
            for i, slide_content in enumerate(slide_contents):
                if not hasattr(slide_content, 'html_image_path') or not slide_content.html_image_path:
                    # Try to get the HTML image path from database
                    slide_db_id = self._get_slide_id_from_database(project_id, i + 1)
                    if slide_db_id:
                        html_image_path = self._get_final_html_image_path(project_id, slide_db_id)
                        if html_image_path:
                            slide_content.html_image_path = html_image_path
                            logger.debug(f"Attached refined HTML image to slide {i + 1} for final presentation")
            
            # Generate final presentation using the SAME process
            final_result = await dual_generator.generate_complete_presentation(
                project_id=project_id,
                output_path=output_path,
                slide_contents=slide_contents,
                layouts_info=layouts_info
            )
            
            # Combine results
            return {
                "success": final_result["success"],
                "individual_slides": individual_results,
                "final_presentation": final_result,
                "error": final_result.get("error") if not final_result["success"] else None
            }
            
        except Exception as e:
            logger.error(f"❌ Error in dual-path generation: {e}")
            return {
                "success": False,
                "individual_slides": [],
                "final_presentation": {},
                "error": str(e)
            }

    def execute_individual_slide_regeneration(
        self,
        template_path: str,
        slide_id: str,
        project_id: str,
        updated_slide_content: Any,
        slide_number: int,
        layouts_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Regenerate a specific individual slide after user adjustments
        
        This method allows users to request changes to specific slides
        and regenerate only that slide while maintaining consistency.
        """
        try:
            logger.info(f"🔄 Regenerating individual slide {slide_number} after user adjustments")
            
            # Initialize dual-path generator
            dual_generator = DualPathGenerator(template_path)
            
            # Regenerate the specific slide
            result = asyncio.run(dual_generator.regenerate_individual_slide(
                slide_id=slide_id,
                project_id=project_id,
                updated_slide_content=updated_slide_content,
                slide_number=slide_number,
                layouts_info=layouts_info
            ))
            
            if result["success"]:
                logger.info(f"✅ Successfully regenerated slide {slide_number}")
            else:
                logger.error(f"❌ Failed to regenerate slide {slide_number}: {result['error']}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error regenerating slide {slide_number}: {e}")
            return {"success": False, "error": str(e)}

    def _run_dual_path_synchronous(self, dual_generator, slide_contents, output_path, layouts_info, state):
        """Synchronous dual-path generation for real-time individual slide completion"""
        try:
            # Generate project ID for tracking
            project_id = state.get("project_id") or f"project_{state['topic'].replace(' ', '_')}"
            
            logger.info("🎯 Phase 1: Generating individual slides in real-time...")
            
            # Generate individual slides in parallel for immediate preview
            individual_results = []
            for i, slide_content in enumerate(slide_contents):
                try:
                    slide_id = f"slide_{project_id}_{i + 1}"
                    
                    # Check if slide has HTML content
                    html_image_path = None
                    if hasattr(slide_content, 'html_image_path'):
                        html_image_path = slide_content.html_image_path
                    
                    # If no html_image_path but we have project_id, try to fetch from database
                    if not html_image_path and project_id:
                        # Get the slide ID from database
                        slide_db_id = self._get_slide_id_from_database(project_id, i + 1)
                        if slide_db_id:
                            # Get the final refined HTML image path
                            html_image_path = self._get_final_html_image_path(project_id, slide_db_id)
                            if html_image_path:
                                logger.debug(f"Retrieved refined HTML image for slide {i + 1}: {html_image_path}")
                    
                    # Generate individual slide synchronously for immediate availability
                    individual_pptx_path = dual_generator._create_individual_slide_pptx(
                        slide_content=slide_content,
                        slide_number=i + 1,
                        layouts_info=layouts_info,
                        html_image_path=html_image_path
                    )
                    
                    if individual_pptx_path:
                        # This slide is now immediately available for preview!
                        individual_results.append({
                            "success": True,
                            "slide_id": slide_id,
                            "file_path": individual_pptx_path,
                            "slide_number": i + 1
                        })
                        logger.info(f"✅ Individual slide {i + 1} ready for immediate preview!")
                    else:
                        individual_results.append({"success": False, "error": "Failed to create slide"})
                        
                except Exception as e:
                    logger.error(f"❌ Error generating individual slide {i + 1}: {e}")
                    individual_results.append({"success": False, "error": str(e)})
            
            logger.info("🎯 Phase 2: Generating final presentation...")
            
            # Create final presentation using SAME process
            from pptx import Presentation
            
            presentation = Presentation(dual_generator.template_path)
            dual_generator._clear_template_slides(presentation)
            
            slides_added = 0
            for i, slide_content in enumerate(slide_contents):
                try:
                    success = dual_generator._add_slide_using_core_process(
                        presentation=presentation,
                        slide_content=slide_content,
                        slide_number=i + 1,
                        layouts_info=layouts_info
                    )
                    
                    if success:
                        slides_added += 1
                        
                except Exception as e:
                    logger.error(f"❌ Error adding slide {i + 1} to final: {e}")
                    continue
            
            # Save final presentation
            presentation.save(output_path)
            
            return {
                "success": True,
                "individual_slides": individual_results,
                "final_presentation": {
                    "output_path": output_path,
                    "slides_added": slides_added
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error in synchronous dual-path generation: {e}")
            return {
                "success": False,
                "individual_slides": [],
                "final_presentation": {},
                "error": str(e)
            }
    
    def _get_slide_id_from_database(self, project_id: str, slide_number: int) -> Optional[str]:
        """Get slide ID from database using project_id and slide_number"""
        try:
            response = self.db.table('slides').select('id').eq('project_id', project_id).eq('slide_number', slide_number).execute()
            if response.data:
                return response.data[0]['id']
            return None
        except Exception as e:
            logger.error(f"Error getting slide ID: {e}")
            return None
    
    def _get_final_html_image_path(self, project_id: str, slide_id: str) -> Optional[str]:
        """Get the final HTML image path from the last refinement iteration and download it locally"""
        try:
            # Get the final refinement iteration (is_final=true)
            response = self.db.table('html_refinements').select('image_file_url').eq('project_id', project_id).eq('slide_id', slide_id).eq('is_final', True).execute()
            
            image_url = None
            if response.data:
                image_url = response.data[0]['image_file_url']
            else:
                # Fallback: get the latest iteration if no final iteration found
                response = self.db.table('html_refinements').select('image_file_url').eq('project_id', project_id).eq('slide_id', slide_id).order('iteration_number', desc=True).limit(1).execute()
                if response.data:
                    image_url = response.data[0]['image_file_url']
            
            if not image_url:
                return None
            
            # Download the image to a local file
            import requests
            import tempfile
            from pathlib import Path
            
            # Create temp directory if it doesn't exist
            temp_dir = Path(tempfile.gettempdir()) / "html_refined_images"
            temp_dir.mkdir(exist_ok=True)
            
            # Generate local file path
            local_path = temp_dir / f"{slide_id}_refined.png"
            
            # Download the image
            response = requests.get(image_url)
            if response.status_code == 200:
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                logger.debug(f"Downloaded refined HTML image to: {local_path}")
                return str(local_path)
            else:
                logger.error(f"Failed to download HTML image: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting final HTML image path: {e}")
            return None


# For backward compatibility, create an alias
class DualPathSlideAssemblyAgent(EnhancedSlideAssemblyAgent):
    """Alias for EnhancedSlideAssemblyAgent"""
    pass


# Integration helper for existing workflow
def create_enhanced_assembly_agent():
    """
    Factory function to create the enhanced slide assembly agent
    
    This can be used to replace the existing SlideAssemblyAgent in the workflow
    without changing the interface.
    """
    return EnhancedSlideAssemblyAgent()


# Utility function for API integration
async def regenerate_slide_api(
    template_path: str,
    slide_id: str,
    project_id: str,
    user_adjustments: Dict[str, Any],
    slide_number: int,
    layouts_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    API utility function for regenerating slides after user adjustments
    
    Args:
        template_path: Path to the PowerPoint template
        slide_id: Unique identifier for the slide
        project_id: Project identifier
        user_adjustments: Dictionary of user-requested changes
        slide_number: Slide number (1-indexed)
        layouts_info: Layout analysis information
        
    Returns:
        Result dictionary with success status and file URLs
    """
    try:
        # Apply user adjustments to slide content
        # This would integrate with your existing content generation logic
        from .llm_client import SlideContent
        
        # Create updated slide content based on adjustments
        # In a real implementation, this would:
        # 1. Retrieve original slide specification
        # 2. Apply user adjustments
        # 3. Regenerate content using existing agents
        updated_content = SlideContent(
            layout_index=user_adjustments.get("layout_index", 1),
            content=user_adjustments.get("content", {})
        )
        
        # Regenerate the slide
        agent = EnhancedSlideAssemblyAgent()
        result = agent.execute_individual_slide_regeneration(
            template_path=template_path,
            slide_id=slide_id,
            project_id=project_id,
            updated_slide_content=updated_content,
            slide_number=slide_number,
            layouts_info=layouts_info
        )
        
        return result
        
    except Exception as e:
        logger.error(f"❌ API regeneration error: {e}")
        return {"success": False, "error": str(e)}