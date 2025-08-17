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
from .individual_slide_generator import IndividualSlideGenerator
from .debug_variables import get_variable_tracker


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
        
        # Individual slide generator
        self.slide_generator = IndividualSlideGenerator()
        
        # Variable tracker
        self.variable_tracker = get_variable_tracker()

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
        html_refinement_iterations: int = 3,
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

        # Track parallel workflow start
        self.variable_tracker.set_workflow_type("parallel_slide_processing")

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
                slide_states, layout_state, config, html_refinement_iterations
            )
            
            # Step 4: Assemble final presentation
            print("⚡ Step 4: Assembling final presentation...")
            final_result = await self._assemble_final_presentation(
                completed_slides, layout_state, output_path, config
            )
            
            print("✅ Parallel slide generation completed successfully!")
            
            # Track final results
            self.variable_tracker.track_final_presentation(final_result)
            
            return final_result

        except Exception as e:
            print(f"❌ Parallel workflow failed: {e}")
            # Update project status to failed
            await self._update_project_status(project_id, "failed", str(e))
            
            # Track failed result
            failed_result = {
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
            
            self.variable_tracker.track_final_presentation(failed_result)
            self.variable_tracker.track_error("parallel_workflow", str(e), {
                "topic": topic,
                "template_path": template_path,
                "slides_count": len(approved_outline.get('slides', []))
            })
            
            return failed_result

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
        
        result = self.layout_agent.execute(initial_state, config)
        
        # Track layout analysis results
        self.variable_tracker.track_layout_analysis(
            result.get("layouts_info"), 
            result.get("dynamic_models")
        )
        
        return result

    async def _create_slide_states(
        self,
        project_id: str,
        approved_outline: Dict[str, Any],
        template_path: str,
        layout_state: SlideGenerationState
    ) -> List[IndividualSlideState]:
        """Create individual slide states and get/update database records"""
        slide_states = []
        slides_data = approved_outline.get('slides', [])
        
        # Check if slides already exist in database (created during outline approval)
        existing_slides_result = self.supabase.client.table("slides").select("*").eq("project_id", project_id).execute()
        existing_slides = {slide["slide_number"]: slide for slide in existing_slides_result.data or []}
        
        for i, slide_spec in enumerate(slides_data):
            slide_number = i + 1
            
            # Use existing slide if available, otherwise create new one
            if slide_number in existing_slides:
                slide_record = existing_slides[slide_number]
                slide_id = slide_record["id"]
                print(f"  ✅ Using existing slide record {slide_number}: {slide_spec.get('title', 'Untitled')}")
            else:
                slide_id = str(uuid.uuid4())
                # Insert slide into database if it doesn't exist
                try:
                    await self._insert_slide_record(
                        slide_id, project_id, slide_number, slide_spec
                    )
                    print(f"  ✅ Created new slide record {slide_number}: {slide_spec.get('title', 'Untitled')}")
                except Exception as e:
                    print(f"  ❌ Failed to create slide {slide_number}: {e}")
                    continue
            
            # Create slide state object
            slide_state = IndividualSlideState(
                slide_id=slide_id,
                project_id=project_id,
                slide_number=slide_number,
                slide_spec=slide_spec,
                template_path=template_path
            )
            
            slide_states.append(slide_state)
        
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
                "layout_index": slide_spec.get("layout_index"),  # CRITICAL FIX: Store layout_index
            }
            
            result = self.supabase.client.table("slides").insert(slide_data).execute()
            
            if not result.data:
                raise DatabaseError("Failed to insert slide record")
                
        except Exception as e:
            raise DatabaseError(f"Database error inserting slide {slide_number}: {str(e)}")

    async def _process_slides_parallel(
        self,
        slide_states: List[IndividualSlideState],
        layout_state: SlideGenerationState,
        config: Optional[RunnableConfig],
        html_refinement_iterations: int = 3
    ) -> List[IndividualSlideState]:
        """Process slides in parallel with controlled concurrency, starting in outline order"""
        completed_slides = []
        failed_slides = []
        
        # Sort slides by slide number to ensure outline order
        sorted_slides = sorted(slide_states, key=lambda s: s.slide_number)
        total_slides = len(sorted_slides)
        print(f"📋 Processing {total_slides} slides in outline order (slides {sorted_slides[0].slide_number}-{sorted_slides[-1].slide_number})")
        
        # Track running tasks and remaining slides
        running_tasks = {}  # task -> slide_state mapping
        remaining_slides = list(sorted_slides)
        
        async def process_single_slide(slide_state: IndividualSlideState):
            return await self._process_individual_slide(
                slide_state, layout_state, config, html_refinement_iterations
            )
        
        # Start initial batch of slides (up to max_concurrent)
        print(f"📋 Starting initial batch of {min(self.max_concurrent_slides, len(remaining_slides))} slides in outline order...")
        while len(running_tasks) < self.max_concurrent_slides and remaining_slides:
            slide_state = remaining_slides.pop(0)
            task = asyncio.create_task(process_single_slide(slide_state))
            running_tasks[task] = slide_state
            print(f"🚀 Started processing slide {slide_state.slide_number}: {slide_state.slide_spec.get('title', 'Untitled')}")
        
        print(f"⚡ Processing {len(running_tasks)} slides concurrently, {len(remaining_slides)} queued...")
        
        # Process slides as they complete, starting new ones immediately
        while running_tasks:
            # Wait for any task to complete
            done, pending = await asyncio.wait(running_tasks.keys(), return_when=asyncio.FIRST_COMPLETED)
            
            for completed_task in done:
                slide_state = running_tasks.pop(completed_task)
                
                try:
                    result = await completed_task
                    if result.status == SlideStatus.COMPLETED:
                        completed_slides.append(result)
                        print(f"✅ Slide {result.slide_number} completed")
                    else:
                        failed_slides.append(result)
                        print(f"❌ Slide {result.slide_number} failed: {result.error_message}")
                        
                except Exception as e:
                    print(f"❌ Unexpected error processing slide {slide_state.slide_number}: {e}")
                    failed_slides.append(slide_state)
                
                # Start next slide if any remaining
                if remaining_slides:
                    next_slide = remaining_slides.pop(0)
                    new_task = asyncio.create_task(process_single_slide(next_slide))
                    running_tasks[new_task] = next_slide
                    print(f"🚀 Started processing slide {next_slide.slide_number}: {next_slide.slide_spec.get('title', 'Untitled')} ({len(remaining_slides)} slides remaining in queue)")
        
        print(f"📊 Parallel processing complete: {len(completed_slides)} succeeded, {len(failed_slides)} failed")
        
        # Sort completed slides by slide number to maintain outline order
        completed_slides.sort(key=lambda s: s.slide_number)
        return completed_slides

    async def _process_individual_slide(
        self,
        slide_state: IndividualSlideState,
        layout_state: SlideGenerationState,
        config: Optional[RunnableConfig],
        html_refinement_iterations: int = 3
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
            
            # Step 3: HTML Refinement (if needed - check the workflow flag)
            html_generation_result = getattr(slide_state, 'html_generation_result', {})
            needs_refinement = html_generation_result.get("needs_html_refinement", False)
            
            print(f"🔍 Checking HTML refinement need for slide {slide_state.slide_number}:")
            print(f"  - needs_html_refinement flag: {needs_refinement}")
            print(f"  - html_content exists: {bool(slide_state.html_content)}")
            
            if needs_refinement and slide_state.html_content:
                await self._update_slide_status(slide_state, SlideStatus.HTML_REFINEMENT)
                slide_state = await self._run_slide_html_refinement(
                    slide_state, layout_state, config, html_refinement_iterations
                )
                if slide_state.status == SlideStatus.FAILED:
                    return slide_state
            else:
                print(f"⚠️ Skipping HTML refinement for slide {slide_state.slide_number} - needs_refinement: {needs_refinement}, has_html: {bool(slide_state.html_content)}")
            
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
            
            # Generate individual PPTX file
            await self._generate_individual_slide_file(slide_state, layout_state)
            
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
            update_data = {
                "status": status,
                "updated_at": datetime.now().isoformat()
            }
            
            # Add status-specific fields
            if status == SlideStatus.COMPLETED:
                update_data.update({
                    "html_content": slide_state.html_content,
                    "refined_html": slide_state.refined_html
                })
                
                # Store the layout_index for proper PPTX generation
                # Extract layout index from slide_content if available
                if slide_state.slide_content and hasattr(slide_state.slide_content, 'layout_index'):
                    update_data["layout_index"] = slide_state.slide_content.layout_index
                    print(f"📝 Storing layout_index {slide_state.slide_content.layout_index} in database for slide {slide_state.slide_number}")
                else:
                    print(f"⚠️ No layout_index found in slide_content for slide {slide_state.slide_number}")
                
                # Store the main slide content when completed
                if slide_state.slide_content and hasattr(slide_state.slide_content, 'content'):
                    update_data["content"] = slide_state.slide_content.content
            elif status == SlideStatus.FAILED:
                # Store error in metadata
                current_content = slide_state.slide_spec.copy()
                current_content["error"] = slide_state.error_message
                update_data["content"] = current_content
            
            result = self.supabase.client.table("slides").update(update_data).eq("id", slide_state.slide_id).execute()
            
            if not result.data:
                print(f"⚠️ Failed to update slide {slide_state.slide_number} status to {status}")
                
        except Exception as e:
            print(f"⚠️ Database error updating slide {slide_state.slide_number}: {e}")

    async def _run_slide_content_generation(
        self, slide_state: IndividualSlideState, layout_state: SlideGenerationState, config: Optional[RunnableConfig]
    ) -> IndividualSlideState:
        """Run content generation for individual slide"""
        try:
            # Convert slide_spec dict to proper SlideSpec object if needed
            from .llm_models import SlideSpec, PresentationPlan
            
            if isinstance(slide_state.slide_spec, dict):
                # Determine appropriate layout based on content type
                layout_index = self._select_appropriate_layout(slide_state.slide_spec, layout_state)
                
                # Convert dictionary to SlideSpec object
                slide_spec_obj = SlideSpec(
                    layout_index=layout_index,
                    slide_title=slide_state.slide_spec.get("title", "Untitled"),
                    slide_purpose=f"Create content for: {slide_state.slide_spec.get('title', 'Untitled')}",
                    is_html=slide_state.slide_spec.get("is_html", False) or slide_state.slide_spec.get("content_type") in ["timeline", "chart", "comparison", "process"],
                    is_image=slide_state.slide_spec.get("is_image", False) or slide_state.slide_spec.get("content_type") == "visual",
                    detailed_purpose=", ".join(slide_state.slide_spec.get("key_points", [])),
                    content_structure=slide_state.slide_spec.get("content_type", "text"),
                    html_requirements=slide_state.slide_spec.get("notes"),
                    key_information=slide_state.slide_spec.get("key_points", [])
                )
            else:
                slide_spec_obj = slide_state.slide_spec
            
            # Create a proper PresentationPlan object with full context
            # This is what the content agent actually expects
            presentation_plan = PresentationPlan(
                total_slides=1,
                slides=[slide_spec_obj],
                presentation_flow=f"Single slide presentation: {slide_state.slide_spec.get('title', 'Untitled')}",
                reasoning=f"Generating content for individual slide: {slide_state.slide_spec.get('title', 'Untitled')}"
            )
            
            # Create a proper workflow state with all required fields
            workflow_state: SlideGenerationState = {
                **layout_state,
                "presentation_plan": presentation_plan,  # Pass the full plan object
                "selected_layouts": [layout_index],  # Content agent may need this
                "current_step": "content_generation"
            }
            
            # Content generation - run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.content_agent.execute,
                workflow_state,
                config
            )
            
            if result.get("error_message"):
                slide_state.status = SlideStatus.FAILED
                slide_state.error_message = result["error_message"]
            else:
                slide_contents = result.get("slide_contents", [])
                if slide_contents:
                    slide_state.slide_content = slide_contents[0]  # Should be only one slide
                    print(f"✅ content_generator: Generated content for slide {slide_state.slide_number}")
                else:
                    print(f"⚠️ content_generator: No content generated for slide {slide_state.slide_number}")
                
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
            
            # Create a proper PresentationPlan object for context
            from .llm_models import PresentationPlan, SlideSpec
            
            # Extract layout index from slide_content
            layout_index = slide_state.slide_content.layout_index if hasattr(slide_state.slide_content, 'layout_index') else 0
            
            # Create a presentation plan with the single slide
            presentation_plan = PresentationPlan(
                total_slides=1,
                slides=[SlideSpec(
                    layout_index=layout_index,
                    slide_title=slide_state.slide_spec.get("title", "Untitled"),
                    slide_purpose=f"HTML generation for: {slide_state.slide_spec.get('title', 'Untitled')}",
                    is_html=slide_state.slide_spec.get("is_html", False) or slide_state.slide_spec.get("content_type") in ["timeline", "chart", "comparison", "process"],
                    is_image=slide_state.slide_spec.get("is_image", False) or slide_state.slide_spec.get("content_type") == "visual",
                    detailed_purpose=", ".join(slide_state.slide_spec.get("key_points", [])),
                    content_structure=slide_state.slide_spec.get("content_type", "text"),
                    html_requirements=slide_state.slide_spec.get("notes"),
                    key_information=slide_state.slide_spec.get("key_points", [])
                )],
                presentation_flow=f"HTML generation for slide: {slide_state.slide_spec.get('title', 'Untitled')}",
                reasoning=f"Generating HTML visualization for: {slide_state.slide_spec.get('title', 'Untitled')}"
            )
            
            workflow_state: SlideGenerationState = {
                **layout_state,
                "slide_contents": [slide_state.slide_content],
                "presentation_plan": presentation_plan,  # Include presentation plan for context
                "current_step": "html_generation",
                "project_id": slide_state.project_id,  # Add project_id for tracking
                "slide_ids": [slide_state.slide_id]  # Add slide_id for tracking
            }
            
            result = await self.html_content_agent.execute_parallel(workflow_state, config)
            
            # Store the HTML generation result for refinement decision
            slide_state.html_generation_result = result
            
            if result.get("error_message"):
                slide_state.status = SlideStatus.FAILED
                slide_state.error_message = result["error_message"]
            else:
                # Extract HTML content from result
                slide_contents = result.get("slide_contents", [])
                if slide_contents and hasattr(slide_contents[0], 'content'):
                    # Update the slide content with any HTML generated
                    slide_state.slide_content = slide_contents[0]
                    
                    # Look for HTML in the slide content (check multiple patterns)
                    content = slide_contents[0].content
                    html_found = False
                    for key, value in content.items():
                        if isinstance(value, str) and value.strip():
                            # Check for HTML patterns
                            if (key.endswith('_html') or 
                                ('<' in value and '>' in value and value.strip().startswith('<')) or
                                ('html' in key.lower())):
                                slide_state.html_content = value
                                print(f"✅ html_content_generator: Found HTML content in '{key}' for slide {slide_state.slide_number}")
                                print(f"🔍 HTML content preview: {value[:100]}...")
                                html_found = True
                                break
                    
                    if not html_found:
                        print(f"⚠️ html_content_generator: No HTML content found for slide {slide_state.slide_number}")
                        print(f"🔍 Available content keys: {list(content.keys())}")
                        for key, value in content.items():
                            if isinstance(value, str):
                                print(f"  - {key}: {value[:50]}...")
                
                # Check the needs_html_refinement flag from the result
                needs_refinement = result.get("needs_html_refinement", False)
                print(f"🔍 HTML generation result: needs_html_refinement = {needs_refinement}")
                
            return slide_state
            
        except Exception as e:
            slide_state.status = SlideStatus.FAILED
            slide_state.error_message = f"HTML generation failed: {str(e)}"
            return slide_state

    async def _run_slide_html_refinement(
        self, slide_state: IndividualSlideState, layout_state: SlideGenerationState, config: Optional[RunnableConfig], html_refinement_iterations: int = 3
    ) -> IndividualSlideState:
        """Run HTML refinement for individual slide using the complete refinement process"""
        try:
            # Skip refinement if no HTML content
            if not slide_state.html_content:
                print(f"⚠️ Skipping HTML refinement for slide {slide_state.slide_number} - no HTML content found")
                print(f"🔍 slide_state.html_content: {slide_state.html_content}")
                if hasattr(slide_state, 'slide_content') and slide_state.slide_content:
                    print(f"🔍 Available slide content keys: {list(slide_state.slide_content.content.keys()) if hasattr(slide_state.slide_content, 'content') else 'No content attr'}")
                return slide_state
            
            print(f"🎨 Starting HTML refinement for slide {slide_state.slide_number}...")
            
            # Generate a refinement ID for this slide
            import uuid
            refinement_id = str(uuid.uuid4())
            
            # Get slide purpose for refinement context
            slide_purpose = f"Refining HTML visualization for: {slide_state.slide_spec.get('title', 'Untitled')}"
            if slide_state.slide_spec.get('key_points'):
                slide_purpose += f". Key points: {', '.join(slide_state.slide_spec.get('key_points', []))}"
            
            # Call the individual slide refinement method directly (max 5 iterations)
            # CRITICAL FIX: Use correct global slide index (0-based) instead of hardcoded 0
            refined_html = await self.refinement_agent._refine_one_slide_fully_async(
                slide_index=slide_state.slide_number - 1,
                initial_html_content=slide_state.html_content,
                slide_purpose=slide_purpose,
                refinement_id=refinement_id,
                project_id=slide_state.project_id,
                slide_content=slide_state.slide_content,
                config=config,
                max_iterations=html_refinement_iterations
            )
            
            if refined_html:
                slide_state.refined_html = refined_html
                print(f"✅ HTML refinement completed for slide {slide_state.slide_number}")
                
                # Update the slide content with refined HTML
                if hasattr(slide_state.slide_content, 'content'):
                    # Find the HTML placeholder and update it
                    for key, value in slide_state.slide_content.content.items():
                        if isinstance(value, str) and ("<" in value and ">" in value):
                            slide_state.slide_content.content[key] = refined_html
                            break
            else:
                print(f"⚠️ HTML refinement returned no content for slide {slide_state.slide_number}")
                
            return slide_state
            
        except Exception as e:
            slide_state.status = SlideStatus.FAILED
            slide_state.error_message = f"HTML refinement failed: {str(e)}"
            print(f"❌ HTML refinement failed for slide {slide_state.slide_number}: {e}")
            return slide_state

    async def _run_slide_image_processing(
        self, slide_state: IndividualSlideState, layout_state: SlideGenerationState, config: Optional[RunnableConfig]
    ) -> IndividualSlideState:
        """Run image processing pipeline for individual slide"""
        try:
            if not slide_state.slide_content:
                return slide_state
            
            # Create a proper PresentationPlan object for context
            from .llm_models import PresentationPlan, SlideSpec
            
            # Extract layout index from slide_content
            layout_index = slide_state.slide_content.layout_index if hasattr(slide_state.slide_content, 'layout_index') else 0
            
            # Create a presentation plan with the single slide
            presentation_plan = PresentationPlan(
                total_slides=1,
                slides=[SlideSpec(
                    layout_index=layout_index,
                    slide_title=slide_state.slide_spec.get("title", "Untitled"),
                    slide_purpose=f"Image processing for: {slide_state.slide_spec.get('title', 'Untitled')}",
                    is_html=slide_state.slide_spec.get("is_html", False) or slide_state.slide_spec.get("content_type") in ["timeline", "chart", "comparison", "process"],
                    is_image=slide_state.slide_spec.get("is_image", False) or slide_state.slide_spec.get("content_type") == "visual",
                    detailed_purpose=", ".join(slide_state.slide_spec.get("key_points", [])),
                    content_structure=slide_state.slide_spec.get("content_type", "text"),
                    html_requirements=slide_state.slide_spec.get("notes"),
                    key_information=slide_state.slide_spec.get("key_points", [])
                )],
                presentation_flow=f"Image processing for slide: {slide_state.slide_spec.get('title', 'Untitled')}",
                reasoning=f"Processing images for: {slide_state.slide_spec.get('title', 'Untitled')}"
            )
            
            workflow_state: SlideGenerationState = {
                **layout_state,
                "slide_contents": [slide_state.slide_content],
                "presentation_plan": presentation_plan,  # Include presentation plan for context
                "current_step": "image_processing"
            }
            
            # Image prompt generation - run in executor
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.image_prompt_agent.execute,
                workflow_state,
                config
            )
            if result.get("error_message"):
                slide_state.status = SlideStatus.FAILED
                slide_state.error_message = result["error_message"]
                return slide_state
            
            # Image generation - run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,  # Use default executor
                self.image_generation_agent.execute,
                result,
                config
            )
            if result.get("error_message"):
                slide_state.status = SlideStatus.FAILED
                slide_state.error_message = result["error_message"]
                return slide_state
            
            # Image refinement - also run in executor
            result = await loop.run_in_executor(
                None,  # Use default executor
                self.image_refinement_agent.execute,
                result,
                config
            )
            if result.get("error_message"):
                slide_state.status = SlideStatus.FAILED
                slide_state.error_message = result["error_message"]
                return slide_state
            
            # Update slide content with any image data
            slide_contents = result.get("slide_contents", [])
            if slide_contents:
                slide_state.slide_content = slide_contents[0]
                print(f"✅ image_processing: Completed for slide {slide_state.slide_number}")
            
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
            
            # Quality review - run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.quality_agent.execute,
                workflow_state,
                config
            )
            
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

    async def _generate_individual_slide_file(
        self, slide_state: IndividualSlideState, layout_state: SlideGenerationState
    ):
        """Generate individual PPTX file for the completed slide"""
        try:
            if not slide_state.slide_content:
                print(f"⚠️ No slide content available for individual PPTX generation: {slide_state.slide_number}")
                return
            
            print(f"📄 Generating individual PPTX for slide {slide_state.slide_number}")
            
            # Generate individual slide PPTX
            result = await self.slide_generator.generate_individual_slide(
                slide_id=slide_state.slide_id,
                project_id=slide_state.project_id,
                slide_content=slide_state.slide_content,
                template_path=slide_state.template_path,
                slide_number=slide_state.slide_number,
                layouts_info=layout_state.get("layouts_info") or {},
                dynamic_models=layout_state.get("dynamic_models") or {}
            )
            
            if result.get("success"):
                print(f"✅ Individual PPTX generated for slide {slide_state.slide_number}: {result.get('file_url')}")
            else:
                print(f"❌ Failed to generate individual PPTX for slide {slide_state.slide_number}: {result.get('error')}")
                
        except Exception as e:
            print(f"❌ Error generating individual PPTX for slide {slide_state.slide_number}: {e}")

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
            
            # Try to use individual slides for assembly first
            try:
                print("🔗 Attempting to combine individual slide PPTX files...")
                project_id = completed_slides[0].project_id if completed_slides else None
                
                if project_id:
                    combination_result = await self.slide_generator.combine_individual_slides(
                        project_id=project_id,
                        output_path=output_path,
                        template_path=completed_slides[0].template_path if completed_slides else layout_state.get("template_path"),
                        dynamic_models=layout_state.get("dynamic_models")
                    )
                    
                    if combination_result.get("success"):
                        print(f"✅ Successfully combined {combination_result['slides_combined']} individual slides")
                        return {
                            "success": True,
                            "error": None,
                            "presentation_path": combination_result["output_path"],
                            "slides_completed": len(completed_slides),
                            "slides_failed": 0,
                            "metadata": {
                                "total_slides": len(completed_slides),
                                "processing_time_minutes": self._calculate_total_processing_time(completed_slides),
                                "assembly_method": "individual_combination"
                            },
                        }
                    else:
                        print(f"⚠️ Individual slide combination failed: {combination_result.get('error')}")
                        print("🔄 Falling back to traditional assembly...")
                
            except Exception as e:
                print(f"⚠️ Individual slide combination failed: {e}")
                print("🔄 Falling back to traditional assembly...")
            
            # Check if we have any slide contents to assemble
            if not slide_contents:
                raise Exception("No slide contents available for assembly - all slides failed during processing")
            
            # Fallback to traditional slide assembly
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
                    "assembly_method": "traditional"
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
            # Use the proper database method instead of directly accessing client
            completed_at = datetime.now().isoformat() if status == "completed" else None
            success = self.supabase.update_project_status(project_id, status, completed_at)
            
            if not success:
                print(f"⚠️ Failed to update project {project_id} status to {status}")
                
        except Exception as e:
            print(f"⚠️ Database error updating project status: {e}")

    def _select_appropriate_layout(self, slide_spec: Dict[str, Any], layout_state: SlideGenerationState) -> int:
        """
        Select appropriate layout based on slide content type using same logic as presentation planning agent
        """
        try:
            layouts_info = layout_state.get("layouts_info", {})
            
            # Debug: Print layout state keys
            print(f"🔍 Layout state keys: {list(layout_state.keys())}")
            print(f"🔍 Layouts info available: {bool(layouts_info)}")
            if layouts_info:
                print(f"🔍 Available layouts: {list(layouts_info.keys())}")
            
            if not layouts_info:
                print("⚠️ No layouts_info available in layout_state!")
                # Try to get the first available layout from template analysis
                first_layout = 0  # Always start with layout 0 as the safest fallback
                print(f"🔧 Using fallback layout {first_layout}")
                return first_layout
            
            # Check for is_html and is_image flags first (modern approach)
            is_html = slide_spec.get("is_html", False)
            is_image = slide_spec.get("is_image", False)
            
            # Fallback to content_type for backward compatibility
            content_type = slide_spec.get("content_type", "text")
            
            print(f"🎯 Selecting layout - is_html: {is_html}, is_image: {is_image}, content_type: '{content_type}'")
            
            # Determine preferred layout type based on flags
            if is_html:
                # HTML content needs picture placeholder
                print(f"📊 Slide requires HTML visualization")
                layout_index = self._find_best_layout_for_content(layouts_info, "html")
            elif is_image:
                # AI-generated image needs picture placeholder
                print(f"🖼️ Slide requires AI-generated image")
                layout_index = self._find_best_layout_for_content(layouts_info, "picture")
            else:
                # Check content_type for backward compatibility
                if content_type in ["chart", "timeline", "comparison", "process"]:
                    print(f"📊 Content type '{content_type}' suggests HTML visualization")
                    layout_index = self._find_best_layout_for_content(layouts_info, "html")
                elif content_type == "visual":
                    print(f"🖼️ Content type 'visual' suggests image")
                    layout_index = self._find_best_layout_for_content(layouts_info, "picture")
                else:
                    # Default to text layout
                    print(f"📝 Using text layout for content")
                    layout_index = self._find_best_layout_for_content(layouts_info, "text")
            
            if layout_index is None:
                # Ultimate fallback to text layout
                try:
                    print(f"⚠️ No specific layout found, falling back to text layout")
                    layout_index = self._find_best_layout_for_content(layouts_info, "text")
                except Exception as fallback_error:
                    print(f"⚠️ Error with text fallback: {fallback_error}")
                    layout_index = next(iter(layouts_info.keys())) if layouts_info else 0
            
            # Validate that the selected layout exists
            if layout_index not in layouts_info:
                print(f"⚠️ Selected layout {layout_index} not found in layouts_info!")
                layout_index = next(iter(layouts_info.keys())) if layouts_info else 0
                print(f"🔧 Using first available layout {layout_index} instead")
            
            print(f"✅ Selected layout {layout_index} for content_type '{content_type}'")
            return layout_index
                
        except Exception as e:
            print(f"❌ Error selecting layout for slide: {e}")
            print(f"🔍 Slide spec: {slide_spec}")
            print(f"🔍 Layout state keys: {list(layout_state.keys()) if layout_state else 'None'}")
            # Ultimate fallback - use layout 0 which should always exist
            return 0

    def _find_best_layout_for_content(
        self, 
        layouts_info: Dict[int, Dict[str, Any]], 
        preferred_type: str
    ) -> int:
        """
        Find the best layout index for a given content type dynamically
        
        Args:
            layouts_info: Available layout information
            preferred_type: Preferred layout type (text, picture, html)
            
        Returns:
            Layout index (defaults to first available layout if no match found)
        """
        if not layouts_info:
            print(f"⚠️ Empty layouts_info provided to _find_best_layout_for_content")
            return 0
            
        print(f"🔍 Finding layout for preferred_type: '{preferred_type}'")
        print(f"🔍 Available layouts: {[(idx, info.get('name', 'Unknown')) for idx, info in layouts_info.items()]}")
        
        # Special handling for HTML content - look for specific placeholders
        if preferred_type == "html":
            # First, look for layouts with HTML-specific picture placeholders
            for layout_idx, layout_info in layouts_info.items():
                placeholders = layout_info.get('placeholders', [])
                for placeholder in placeholders:
                    ph_name = placeholder.get('name', '').lower()
                    # Look for HTML picture placeholders
                    if 'html' in ph_name and ('picture' in ph_name or 'image' in ph_name):
                        print(f"✅ Found HTML-capable layout {layout_idx} with placeholder '{placeholder.get('name')}'")
                        return layout_idx
            
            # Fallback to any picture layout for HTML
            preferred_type = "picture"
        
        # Look for picture layouts
        if preferred_type == "picture":
            for layout_idx, layout_info in layouts_info.items():
                # Check layout name first
                layout_name = layout_info.get("name", "").lower()
                if 'picture' in layout_name and 'title' in layout_name:
                    print(f"✅ Found picture layout {layout_idx} ('{layout_info.get('name')}')")
                    return layout_idx
                
                # Check for picture placeholders
                placeholders = layout_info.get('placeholders', [])
                for placeholder in placeholders:
                    ph_type = placeholder.get('type', 0)
                    ph_name = placeholder.get('name', '').lower()
                    # Type 18 is typically PICTURE placeholder
                    if ph_type == 18 or 'picture' in ph_name or 'image' in ph_name:
                        print(f"✅ Found layout {layout_idx} with picture placeholder")
                        return layout_idx
        
        # Look for text layouts
        if preferred_type == "text":
            for layout_idx, layout_info in layouts_info.items():
                layout_name = layout_info.get("name", "").lower()
                # Look for text content layouts
                if 'text' in layout_name and 'content' in layout_name:
                    print(f"✅ Found text layout {layout_idx} ('{layout_info.get('name')}')")
                    return layout_idx
            
            # Fallback: find any layout with content placeholders
            for layout_idx, layout_info in layouts_info.items():
                placeholders = layout_info.get('placeholders', [])
                for placeholder in placeholders:
                    ph_name = placeholder.get('name', '').lower()
                    if 'content' in ph_name or 'text' in ph_name or 'body' in ph_name:
                        print(f"✅ Found layout {layout_idx} with text placeholder '{placeholder.get('name')}'")
                        return layout_idx
        
        # Final fallback to first non-special layout
        for layout_idx, layout_info in layouts_info.items():
            layout_name = layout_info.get("name", "").lower()
            # Skip special layouts like "Main Logo Start Slide" or "Branding Slide"
            if not any(skip in layout_name for skip in ['logo', 'start', 'branding', 'end']):
                print(f"⚠️ Using first general layout {layout_idx} ('{layout_info.get('name')}')")
                return layout_idx
        
        # Ultimate fallback
        first_layout = next(iter(layouts_info.keys())) if layouts_info else 0
        print(f"❌ No suitable layout found, using first available: {first_layout}")
        return first_layout