"""
Parallel Slide Generation Workflow

This module implements parallel slide generation where each slide is processed
independently through the agent pipeline. This provides real-time feedback
as individual slides are completed.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import concurrent.futures

from langchain_core.runnables import RunnableConfig

from .agents import (
    ContentGenerationAgent,
    HTMLRefinementAgent,
    ImagePromptAgent,
    ImageGenerationAgent,
    ImageRefinementAgent,
    LayoutAnalysisAgent,
    PresentationPlanningAgent,
    QualityReviewAgent,
    SlideAssemblyAgent,
    SlideGenerationState,
)
from .html_content_agent import HTMLContentGenerationAgent
from .monitoring import slide_monitor
from .database import get_supabase_client, DatabaseError
from .llm_client import SlideContent


class SlideStatus:
    """Enum-like class for slide processing status"""
    PENDING = "pending"
    PLANNING = "planning"
    CONTENT_GENERATION = "content_generation"
    HTML_GENERATION = "html_generation"
    HTML_REFINEMENT = "html_refinement"
    IMAGE_PROMPT_GENERATION = "image_prompt_generation"
    IMAGE_GENERATION = "image_generation"
    IMAGE_REFINEMENT = "image_refinement"
    QUALITY_REVIEW = "quality_review"
    COMPLETED = "completed"
    FAILED = "failed"


class IndividualSlideState:
    """State for tracking individual slide processing"""
    def __init__(
        self,
        slide_id: str,
        project_id: str,
        slide_number: int,
        slide_spec: Dict[str, Any],
        template_path: str
    ):
        self.slide_id = slide_id
        self.project_id = project_id
        self.slide_number = slide_number
        self.slide_spec = slide_spec
        self.template_path = template_path
        
        # Processing state
        self.status = SlideStatus.PENDING
        self.error_message: Optional[str] = None
        self.current_agent = None
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        
        # Generated content
        self.slide_content: Optional[SlideContent] = None
        self.html_content: Optional[str] = None
        self.refined_html: Optional[str] = None
        self.image_prompts: Optional[List[str]] = None
        self.generated_images: Optional[List[str]] = None
        
        # Agent execution times
        self.agent_times: Dict[str, int] = {}


class ParallelSlideWorkflow:
    """
    Parallel slide generation workflow that processes each slide independently
    """

    def __init__(self, max_concurrent_slides: int = 3):
        """
        Initialize parallel workflow
        
        Args:
            max_concurrent_slides: Maximum number of slides to process concurrently
        """
        self.max_concurrent_slides = max_concurrent_slides
        
        # Initialize agents (these will be shared across slide processing)
        self.layout_agent = LayoutAnalysisAgent()
        self.planning_agent = PresentationPlanningAgent()
        self.content_agent = ContentGenerationAgent()
        self.html_content_agent = HTMLContentGenerationAgent()
        self.refinement_agent = HTMLRefinementAgent()
        self.image_prompt_agent = ImagePromptAgent()
        self.image_generation_agent = ImageGenerationAgent()
        self.image_refinement_agent = ImageRefinementAgent()
        self.quality_agent = QualityReviewAgent()
        self.assembly_agent = SlideAssemblyAgent()
        
        # Database and callbacks
        self.database_callback: Optional[Callable] = None
        self.supabase = get_supabase_client()

    def set_database_callback(self, callback: Callable):
        """Set database callback for real-time updates"""
        self.database_callback = callback

    async def process_presentation_parallel(
        self,
        topic: str,
        template_path: str,
        output_path: str,
        project_id: str,
        approved_outline: Dict[str, Any],
        title: Optional[str] = None,
        config: Optional[RunnableConfig] = None,
    ) -> Dict[str, Any]:
        """
        Process entire presentation with parallel slide generation
        
        Args:
            topic: Presentation topic
            template_path: Path to PowerPoint template
            output_path: Output path for generated presentation
            project_id: Database project ID for tracking
            approved_outline: Pre-approved presentation outline
            title: Optional presentation title
            config: Optional Langchain configuration
            
        Returns:
            Dictionary with processing results
        """
        print("🚀 Starting parallel slide generation workflow...")
        print(f"🎯 Title: {title}")
        print(f"📋 Topic: {topic}")
        print(f"📄 Slides to process: {len(approved_outline.get('slides', []))}")

        try:
            # Step 1: Layout Analysis (once for entire presentation)
            print("⚡ Step 1: Analyzing template layouts...")
            layout_state = await self._run_layout_analysis(
                topic, template_path, output_path, config
            )
            
            if layout_state.get("error_message"):
                raise Exception(layout_state["error_message"])

            # Step 2: Create individual slide states
            print("⚡ Step 2: Initializing slide processing states...")
            slide_states = await self._create_slide_states(
                project_id, approved_outline, template_path, layout_state
            )
            
            # Step 3: Process slides in parallel
            print(f"⚡ Step 3: Processing {len(slide_states)} slides in parallel...")
            completed_slides = await self._process_slides_parallel(
                slide_states, layout_state, config
            )
            
            # Step 4: Assemble final presentation
            print("⚡ Step 4: Assembling final presentation...")
            final_result = await self._assemble_final_presentation(
                completed_slides, layout_state, output_path, config
            )
            
            print("✅ Parallel slide generation completed successfully!")
            return final_result

        except Exception as e:
            print(f"❌ Parallel workflow failed: {e}")
            # Update project status to failed
            await self._update_project_status(project_id, "failed", str(e))
            
            return {
                "success": False,
                "error": str(e),
                "presentation_path": None,
                "slides_completed": 0,
                "slides_failed": len(approved_outline.get('slides', [])),
                "metadata": {
                    "topic": topic,
                    "template_path": template_path,
                    "output_path": output_path,
                },
            }

    async def _run_layout_analysis(
        self, topic: str, template_path: str, output_path: str, config: Optional[RunnableConfig]
    ) -> SlideGenerationState:
        """Run layout analysis once for the entire presentation"""
        initial_state: SlideGenerationState = {
            "topic": topic,
            "template_path": template_path,
            "output_path": output_path,
            "layout_indices": None,
            "title": None,
            "approved_outline": None,
            "current_step": "starting",
            "error_message": None,
            "retry_count": 0,
            "html_refinement_iteration": 0,
            "html_refinement_slide_index": None,
            "html_slides_to_refine_queue": None,
            "refinement_id": None,
            "layouts_info": None,
            "dynamic_models": None,
            "presentation_plan": None,
            "selected_layouts": None,
            "slide_contents": None,
            "icon_errors": None,
            "icon_corrections": None,
            "needs_icon_retry": False,
            "needs_html_refinement": False,
            "presentation_path": None,
            "success": False,
            "monitor_trace": None,
            "project_id": None,
        }
        
        return self.layout_agent.execute(initial_state, config)

    async def _create_slide_states(
        self,
        project_id: str,
        approved_outline: Dict[str, Any],
        template_path: str,
        layout_state: SlideGenerationState
    ) -> List[IndividualSlideState]:
        """Create individual slide states and insert into database"""
        slide_states = []
        slides_data = approved_outline.get('slides', [])
        
        for i, slide_spec in enumerate(slides_data):
            slide_number = i + 1
            slide_id = str(uuid.uuid4())
            
            # Insert slide into database
            try:
                await self._insert_slide_record(
                    slide_id, project_id, slide_number, slide_spec
                )
                
                # Create slide state object
                slide_state = IndividualSlideState(
                    slide_id=slide_id,
                    project_id=project_id,
                    slide_number=slide_number,
                    slide_spec=slide_spec,
                    template_path=template_path
                )
                
                slide_states.append(slide_state)
                print(f"  ✅ Initialized slide {slide_number}: {slide_spec.get('title', 'Untitled')}")
                
            except Exception as e:
                print(f"  ❌ Failed to initialize slide {slide_number}: {e}")
                continue
        
        return slide_states

    async def _insert_slide_record(
        self, slide_id: str, project_id: str, slide_number: int, slide_spec: Dict[str, Any]
    ):
        """Insert slide record into database"""
        try:
            slide_data = {
                "id": slide_id,
                "project_id": project_id,
                "slide_number": slide_number,
                "title": slide_spec.get("title", "Untitled"),
                "content": slide_spec,
                "layout_type": slide_spec.get("layout_type"),
            }
            
            result = self.supabase.table("slides").insert(slide_data).execute()
            
            if not result.data:
                raise DatabaseError("Failed to insert slide record")
                
        except Exception as e:
            raise DatabaseError(f"Database error inserting slide {slide_number}: {str(e)}")

    async def _process_slides_parallel(
        self,
        slide_states: List[IndividualSlideState],
        layout_state: SlideGenerationState,
        config: Optional[RunnableConfig]
    ) -> List[IndividualSlideState]:
        """Process slides in parallel with controlled concurrency"""
        completed_slides = []
        failed_slides = []
        
        # Create semaphore to limit concurrent processing
        semaphore = asyncio.Semaphore(self.max_concurrent_slides)
        
        async def process_single_slide(slide_state: IndividualSlideState):
            async with semaphore:
                return await self._process_individual_slide(
                    slide_state, layout_state, config
                )
        
        # Start all slide processing tasks
        tasks = [process_single_slide(slide_state) for slide_state in slide_states]
        
        # Process slides as they complete
        for task in asyncio.as_completed(tasks):
            try:
                result = await task
                if result.status == SlideStatus.COMPLETED:
                    completed_slides.append(result)
                    print(f"✅ Slide {result.slide_number} completed")
                else:
                    failed_slides.append(result)
                    print(f"❌ Slide {result.slide_number} failed: {result.error_message}")
                    
            except Exception as e:
                print(f"❌ Unexpected error processing slide: {e}")
                failed_slides.append(None)  # Track failed count
        
        print(f"📊 Parallel processing complete: {len(completed_slides)} succeeded, {len(failed_slides)} failed")
        return completed_slides

    async def _process_individual_slide(
        self,
        slide_state: IndividualSlideState,
        layout_state: SlideGenerationState,
        config: Optional[RunnableConfig]
    ) -> IndividualSlideState:
        """Process a single slide through the agent pipeline"""
        slide_state.started_at = datetime.now()
        
        print(f"🔄 Processing slide {slide_state.slide_number}: {slide_state.slide_spec.get('title', 'Untitled')}")
        
        try:
            # Update slide status in database
            await self._update_slide_status(slide_state, SlideStatus.CONTENT_GENERATION)
            
            # Step 1: Content Generation
            slide_state = await self._run_slide_content_generation(
                slide_state, layout_state, config
            )
            if slide_state.status == SlideStatus.FAILED:
                return slide_state
            
            # Step 2: HTML Generation
            await self._update_slide_status(slide_state, SlideStatus.HTML_GENERATION)
            slide_state = await self._run_slide_html_generation(
                slide_state, layout_state, config
            )
            if slide_state.status == SlideStatus.FAILED:
                return slide_state
            
            # Step 3: HTML Refinement (if needed)
            if slide_state.html_content:
                await self._update_slide_status(slide_state, SlideStatus.HTML_REFINEMENT)
                slide_state = await self._run_slide_html_refinement(
                    slide_state, layout_state, config
                )
                if slide_state.status == SlideStatus.FAILED:
                    return slide_state
            
            # Step 4: Image Processing
            await self._update_slide_status(slide_state, SlideStatus.IMAGE_PROMPT_GENERATION)
            slide_state = await self._run_slide_image_processing(
                slide_state, layout_state, config
            )
            if slide_state.status == SlideStatus.FAILED:
                return slide_state
            
            # Step 5: Quality Review
            await self._update_slide_status(slide_state, SlideStatus.QUALITY_REVIEW)
            slide_state = await self._run_slide_quality_review(
                slide_state, layout_state, config
            )
            
            # Mark as completed
            slide_state.status = SlideStatus.COMPLETED
            slide_state.completed_at = datetime.now()
            await self._update_slide_status(slide_state, SlideStatus.COMPLETED)
            
            print(f"✅ Slide {slide_state.slide_number} processing completed")
            return slide_state
            
        except Exception as e:
            slide_state.status = SlideStatus.FAILED
            slide_state.error_message = str(e)
            slide_state.completed_at = datetime.now()
            await self._update_slide_status(slide_state, SlideStatus.FAILED)
            
            print(f"❌ Slide {slide_state.slide_number} failed: {e}")
            return slide_state

    async def _update_slide_status(
        self, slide_state: IndividualSlideState, status: str
    ):
        """Update slide status in database"""
        try:
            update_data = {"updated_at": datetime.now().isoformat()}
            
            # Add status-specific fields
            if status == SlideStatus.COMPLETED:
                update_data.update({
                    "html_content": slide_state.html_content,
                    "refined_html": slide_state.refined_html
                })
            elif status == SlideStatus.FAILED:
                # Store error in metadata
                current_content = slide_state.slide_spec.copy()
                current_content["error"] = slide_state.error_message
                update_data["content"] = current_content
            
            result = self.supabase.table("slides").update(update_data).eq("id", slide_state.slide_id).execute()
            
            if not result.data:
                print(f"⚠️ Failed to update slide {slide_state.slide_number} status to {status}")
                
        except Exception as e:
            print(f"⚠️ Database error updating slide {slide_state.slide_number}: {e}")

    async def _run_slide_content_generation(
        self, slide_state: IndividualSlideState, layout_state: SlideGenerationState, config: Optional[RunnableConfig]
    ) -> IndividualSlideState:
        """Run content generation for individual slide"""
        try:
            # Create a minimal workflow state for this slide
            workflow_state: SlideGenerationState = {
                **layout_state,
                "presentation_plan": {"slides": [slide_state.slide_spec]},
                "current_step": "content_generation"
            }
            
            result = self.content_agent.execute(workflow_state, config)
            
            if result.get("error_message"):
                slide_state.status = SlideStatus.FAILED
                slide_state.error_message = result["error_message"]
            else:
                slide_contents = result.get("slide_contents", [])
                if slide_contents:
                    slide_state.slide_content = slide_contents[0]  # Should be only one slide
                
            return slide_state
            
        except Exception as e:
            slide_state.status = SlideStatus.FAILED
            slide_state.error_message = f"Content generation failed: {str(e)}"
            return slide_state

    async def _run_slide_html_generation(
        self, slide_state: IndividualSlideState, layout_state: SlideGenerationState, config: Optional[RunnableConfig]
    ) -> IndividualSlideState:
        """Run HTML generation for individual slide"""
        try:
            if not slide_state.slide_content:
                slide_state.status = SlideStatus.FAILED
                slide_state.error_message = "No slide content available for HTML generation"
                return slide_state
            
            workflow_state: SlideGenerationState = {
                **layout_state,
                "slide_contents": [slide_state.slide_content],
                "current_step": "html_generation"
            }
            
            result = await self.html_content_agent.execute_parallel(workflow_state, config)
            
            if result.get("error_message"):
                slide_state.status = SlideStatus.FAILED
                slide_state.error_message = result["error_message"]
            else:
                # Extract HTML content from result
                slide_contents = result.get("slide_contents", [])
                if slide_contents and hasattr(slide_contents[0], 'content'):
                    # Look for HTML in the slide content
                    content = slide_contents[0].content
                    for key, value in content.items():
                        if key.endswith('_html') and value:
                            slide_state.html_content = value
                            break
                
            return slide_state
            
        except Exception as e:
            slide_state.status = SlideStatus.FAILED
            slide_state.error_message = f"HTML generation failed: {str(e)}"
            return slide_state

    async def _run_slide_html_refinement(
        self, slide_state: IndividualSlideState, layout_state: SlideGenerationState, config: Optional[RunnableConfig]
    ) -> IndividualSlideState:
        """Run HTML refinement for individual slide if needed"""
        try:
            # Skip refinement if no HTML content
            if not slide_state.html_content:
                return slide_state
            
            workflow_state: SlideGenerationState = {
                **layout_state,
                "slide_contents": [slide_state.slide_content],
                "html_slides_to_refine_queue": [0],  # Only refine this one slide
                "current_step": "html_refinement"
            }
            
            result = await self.refinement_agent.execute_parallel(workflow_state, config)
            
            if result.get("error_message"):
                slide_state.status = SlideStatus.FAILED
                slide_state.error_message = result["error_message"]
            else:
                # Extract refined HTML
                slide_contents = result.get("slide_contents", [])
                if slide_contents and hasattr(slide_contents[0], 'content'):
                    content = slide_contents[0].content
                    for key, value in content.items():
                        if key.endswith('_html') and value:
                            slide_state.refined_html = value
                            break
                
            return slide_state
            
        except Exception as e:
            slide_state.status = SlideStatus.FAILED
            slide_state.error_message = f"HTML refinement failed: {str(e)}"
            return slide_state

    async def _run_slide_image_processing(
        self, slide_state: IndividualSlideState, layout_state: SlideGenerationState, config: Optional[RunnableConfig]
    ) -> IndividualSlideState:
        """Run image processing pipeline for individual slide"""
        try:
            if not slide_state.slide_content:
                return slide_state
            
            workflow_state: SlideGenerationState = {
                **layout_state,
                "slide_contents": [slide_state.slide_content],
                "current_step": "image_processing"
            }
            
            # Image prompt generation
            result = self.image_prompt_agent.execute(workflow_state, config)
            if result.get("error_message"):
                slide_state.status = SlideStatus.FAILED
                slide_state.error_message = result["error_message"]
                return slide_state
            
            # Image generation
            result = self.image_generation_agent.execute(result, config)
            if result.get("error_message"):
                slide_state.status = SlideStatus.FAILED
                slide_state.error_message = result["error_message"]
                return slide_state
            
            # Image refinement
            result = self.image_refinement_agent.execute(result, config)
            if result.get("error_message"):
                slide_state.status = SlideStatus.FAILED
                slide_state.error_message = result["error_message"]
                return slide_state
            
            # Update slide content with any image data
            slide_contents = result.get("slide_contents", [])
            if slide_contents:
                slide_state.slide_content = slide_contents[0]
            
            return slide_state
            
        except Exception as e:
            slide_state.status = SlideStatus.FAILED
            slide_state.error_message = f"Image processing failed: {str(e)}"
            return slide_state

    async def _run_slide_quality_review(
        self, slide_state: IndividualSlideState, layout_state: SlideGenerationState, config: Optional[RunnableConfig]
    ) -> IndividualSlideState:
        """Run quality review for individual slide"""
        try:
            if not slide_state.slide_content:
                return slide_state
            
            workflow_state: SlideGenerationState = {
                **layout_state,
                "slide_contents": [slide_state.slide_content],
                "current_step": "quality_review"
            }
            
            result = self.quality_agent.execute(workflow_state, config)
            
            if result.get("error_message"):
                slide_state.status = SlideStatus.FAILED
                slide_state.error_message = result["error_message"]
            else:
                # Update slide content with quality review results
                slide_contents = result.get("slide_contents", [])
                if slide_contents:
                    slide_state.slide_content = slide_contents[0]
                
            return slide_state
            
        except Exception as e:
            slide_state.status = SlideStatus.FAILED
            slide_state.error_message = f"Quality review failed: {str(e)}"
            return slide_state

    async def _assemble_final_presentation(
        self,
        completed_slides: List[IndividualSlideState],
        layout_state: SlideGenerationState,
        output_path: str,
        config: Optional[RunnableConfig]
    ) -> Dict[str, Any]:
        """Assemble final presentation from completed slides"""
        try:
            # Sort slides by slide number
            completed_slides.sort(key=lambda s: s.slide_number)
            
            # Extract slide contents
            slide_contents = [slide.slide_content for slide in completed_slides if slide.slide_content]
            
            # Create final workflow state for assembly
            final_state: SlideGenerationState = {
                **layout_state,
                "slide_contents": slide_contents,
                "output_path": output_path,
                "current_step": "slide_assembly"
            }
            
            # Run slide assembly
            result = self.assembly_agent.execute(final_state, config)
            
            if result.get("error_message"):
                raise Exception(result["error_message"])
            
            return {
                "success": True,
                "error": None,
                "presentation_path": result.get("presentation_path"),
                "slides_completed": len(completed_slides),
                "slides_failed": 0,
                "metadata": {
                    "total_slides": len(completed_slides),
                    "processing_time_minutes": self._calculate_total_processing_time(completed_slides),
                },
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "presentation_path": None,
                "slides_completed": len(completed_slides),
                "slides_failed": 1,  # Assembly failure
                "metadata": {},
            }

    def _calculate_total_processing_time(self, completed_slides: List[IndividualSlideState]) -> float:
        """Calculate total processing time across all slides"""
        total_seconds = 0
        for slide in completed_slides:
            if slide.started_at and slide.completed_at:
                duration = (slide.completed_at - slide.started_at).total_seconds()
                total_seconds = max(total_seconds, duration)  # Use max since slides processed in parallel
        
        return round(total_seconds / 60, 2)  # Convert to minutes

    async def _update_project_status(self, project_id: str, status: str, error_message: Optional[str] = None):
        """Update project status in database"""
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.now().isoformat()
            }
            
            if status == "completed":
                update_data["completed_at"] = datetime.now().isoformat()
            elif status == "failed" and error_message:
                update_data["metadata"] = {"error": error_message}
            
            result = self.supabase.table("projects").update(update_data).eq("id", project_id).execute()
            
            if not result.data:
                print(f"⚠️ Failed to update project {project_id} status to {status}")
                
        except Exception as e:
            print(f"⚠️ Database error updating project status: {e}")