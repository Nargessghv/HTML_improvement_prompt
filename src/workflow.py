"""
Workflow Module

Langgraph workflow orchestration for the slide generation process.
Coordinates agents and manages the overall presentation creation flow.
"""

import asyncio
import os
from typing import Any, Dict, List, Optional

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from .agents import (
    ContentGenerationAgent,
    HTMLRefinementAgent,
    IconValidationAgent,
    LayoutAnalysisAgent,
    PresentationPlanningAgent,
    QualityReviewAgent,
    SlideAssemblyAgent,
    SlideGenerationState,
)
from .html_content_agent import HTMLContentGenerationAgent
from .monitoring import slide_monitor


class SlideGenerationWorkflow:
    """
    Langgraph workflow for coordinated slide generation using AI agents

    This workflow orchestrates multiple specialized agents to create
    PowerPoint presentations with comprehensive monitoring and error handling.
    """

    def __init__(self, use_parallel_html_refinement: bool = True):
        """Initialize the workflow with all agent instances

        Args:
            use_parallel_html_refinement: Whether to use parallel HTML refinement (default: True)
        """
        self.layout_agent = LayoutAnalysisAgent()
        self.planning_agent = PresentationPlanningAgent()
        self.content_agent = ContentGenerationAgent()
        self.html_content_agent = HTMLContentGenerationAgent()  # Add HTML agent
        self.refinement_agent = HTMLRefinementAgent()  # Add Refinement agent
        self.assembly_agent = SlideAssemblyAgent()
        self.quality_agent = QualityReviewAgent()
        self.icon_validator = IconValidationAgent()

        # Configuration options
        self.use_parallel_html_refinement = (
            use_parallel_html_refinement
            or os.getenv("USE_PARALLEL_HTML_REFINEMENT", "true").lower() == "true"
        )

        # Build the workflow graph
        self.workflow = self._build_workflow_graph()

    def _build_workflow_graph(self):
        """
        Build the Langgraph workflow graph with agent coordination

        Returns:
            Configured CompiledStateGraph for slide generation workflow
        """
        # Create the state graph
        workflow = StateGraph(SlideGenerationState)

        # Add agent nodes
        workflow.add_node("layout_analysis", self._layout_analysis_node)
        workflow.add_node("presentation_planning", self._presentation_planning_node)
        workflow.add_node("content_generation", self._content_generation_node)
        workflow.add_node(
            "html_content_generation", self._html_content_generation_node
        )  # Add HTML node
        workflow.add_node("html_refinement", self._html_refinement_node)
        workflow.add_node("quality_review", self._quality_review_node)
        workflow.add_node("slide_assembly", self._slide_assembly_node)
        workflow.add_node("icon_validation", self._icon_validation_node)
        workflow.add_node("icon_retry", self._icon_retry_node)
        workflow.add_node("error_handler", self._error_handler_node)

        # Define the workflow edges (execution flow)
        workflow.set_entry_point("layout_analysis")

        # Layout analysis -> Planning or Error
        workflow.add_conditional_edges(
            "layout_analysis",
            self._check_analysis_success,
            {"success": "presentation_planning", "error": "error_handler"},
        )

        # Planning -> Content generation or Error
        workflow.add_conditional_edges(
            "presentation_planning",
            self._check_planning_success,
            {"success": "content_generation", "error": "error_handler"},
        )

        # Content generation -> HTML content generation or Error
        workflow.add_conditional_edges(
            "content_generation",
            self._check_content_success,
            {"success": "html_content_generation", "error": "error_handler"},
        )

        # HTML content generation -> HTML Refinement
        workflow.add_edge("html_content_generation", "html_refinement")

        # HTML refinement -> Quality review or loop
        workflow.add_conditional_edges(
            "html_refinement",
            self._check_html_refinement_status,
            {"continue": "quality_review", "refine": "html_refinement"},
        )

        # Quality review -> Assembly (always proceed, as quality is optional)
        workflow.add_edge("quality_review", "slide_assembly")

        # Assembly -> Icon validation or End or Error
        workflow.add_conditional_edges(
            "slide_assembly",
            self._check_assembly_success,
            {
                "success_no_icon_errors": END,
                "success_with_icon_errors": "icon_validation",
                "error": "error_handler",
            },
        )

        # Icon validation -> Icon retry or End or Error
        workflow.add_conditional_edges(
            "icon_validation",
            self._check_icon_validation_success,
            {
                "retry_needed": "icon_retry",
                "no_retry_needed": END,
                "error": "error_handler",
            },
        )

        # Icon retry -> End or Error
        workflow.add_conditional_edges(
            "icon_retry",
            self._check_icon_retry_success,
            {"success": END, "error": "error_handler"},
        )

        # Error handler always ends the workflow
        workflow.add_edge("error_handler", END)

        return workflow.compile()

    def run(
        self,
        topic: str,
        template_path: str,
        output_path: str,
        layout_indices: Optional[List[int]] = None,
        config: Optional[RunnableConfig] = None,
    ) -> Dict[str, Any]:
        """
        Execute the complete slide generation workflow

        Args:
            topic: Presentation topic
            template_path: Path to PowerPoint template
            output_path: Output path for generated presentation
            layout_indices: Optional specific layouts to use
            config: Optional Langchain configuration

        Returns:
            Dictionary with workflow results and metadata
        """
        print("🚀 Starting AI-powered slide generation workflow...")
        print(f"📋 Topic: {topic}")
        print(f"📁 Template: {template_path}")
        print(f"💾 Output: {output_path}")

        # Initialize workflow state
        initial_state: SlideGenerationState = {
            "topic": topic,
            "template_path": template_path,
            "output_path": output_path,
            "layout_indices": layout_indices,
            "current_step": "starting",
            "error_message": None,
            "retry_count": 0,
            "html_refinement_iteration": 0,
            "refinement_id": None,
            "layouts_info": None,
            "dynamic_models": None,
            "presentation_plan": None,
            "selected_layouts": None,
            "slide_contents": None,
            "icon_errors": None,
            "icon_corrections": None,
            "needs_icon_retry": False,
            "presentation_path": None,
            "success": False,
            "monitor_trace": None,
        }

        # Setup configuration with Langfuse callback handler for unified tracing
        if config is None:
            config = {}

        # Get Langfuse callback handler for unified workflow tracing
        langfuse_handler = slide_monitor.get_callback_handler()
        if langfuse_handler:
            config = {
                **config,
                "callbacks": [langfuse_handler],
                "metadata": {
                    "workflow_type": "slide_generation",
                    "topic": topic,
                    "template_path": template_path,
                    "output_path": output_path,
                },
            }
            print("✅ Unified Langfuse tracing enabled for workflow")

        try:
            # Execute workflow with unified tracing
            print("⚡ Executing agent workflow...")
            final_state = self.workflow.invoke(initial_state, config=config)

            # Process and return results
            # Cast to SlideGenerationState for type safety
            typed_final_state: SlideGenerationState = final_state  # type: ignore
            return self._process_workflow_results(typed_final_state)

        except Exception as e:
            print(f"❌ Workflow execution failed: {e}")
            # Ensure we flush any pending traces
            slide_monitor.flush()
            return {
                "success": False,
                "error": str(e),
                "presentation_path": None,
                "agent_results": {},
                "metadata": {
                    "topic": topic,
                    "template_path": template_path,
                    "output_path": output_path,
                    "execution_time": 0,
                    "total_tokens": 0,
                    "cost_estimate": 0.0,
                },
            }

    async def run_with_parallel_refinement(
        self,
        topic: str,
        template_path: str,
        output_path: str,
        config: Optional[RunnableConfig] = None,
    ) -> SlideGenerationState:
        """
        Run the slide generation workflow with parallel HTML refinement

        This method runs the standard workflow but uses parallel processing
        for HTML refinement to improve performance.

        Args:
            topic: Presentation topic
            template_path: Path to PowerPoint template
            output_path: Path to save generated presentation
            config: Langchain configuration with callbacks

        Returns:
            Final workflow state
        """
        # Initialize state
        state = self._create_initial_state(topic, template_path, output_path)

        # Create monitoring trace
        with slide_monitor.trace_workflow(
            "slide_generation_parallel", topic, {"parallel_refinement": True}
        ) as trace:
            state["monitor_trace"] = trace

            # Run layout analysis
            state = self.layout_agent.execute(state, config)
            if state.get("error_message"):
                return state

            # Run presentation planning
            state = self.planning_agent.execute(state, config)
            if state.get("error_message"):
                return state

            # Run content generation
            state = self.content_agent.execute(state, config)
            if state.get("error_message"):
                return state

            # Run HTML content generation (if needed)
            state = self.html_content_agent.execute(state, config)
            if state.get("error_message"):
                return state

            # Run parallel HTML refinement
            state = await self.refinement_agent.execute_parallel(state, config)
            if state.get("error_message"):
                return state

            # Run slide assembly
            state = self.assembly_agent.execute(state, config)
            if state.get("error_message"):
                return state

            # Run icon validation if needed
            if state.get("needs_icon_retry"):
                state = self.icon_validator.execute(state, config)
                if state.get("error_message"):
                    return state

            # Run quality review
            state = self.quality_agent.execute(state, config)

            # Mark as successful
            state["success"] = True

        return state

    def _create_initial_state(
        self, topic: str, template_path: str, output_path: str
    ) -> SlideGenerationState:
        """Create initial workflow state"""
        initial_state: SlideGenerationState = {
            "topic": topic,
            "template_path": template_path,
            "output_path": output_path,
            "layout_indices": None,
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
        }
        return initial_state

    def _process_workflow_results(
        self, final_state: SlideGenerationState
    ) -> Dict[str, Any]:
        """
        Process workflow results and prepare return data

        Args:
            final_state: Final workflow state

        Returns:
            Dictionary with comprehensive workflow results
        """
        # Determine success - check various completion states
        success = final_state.get("success", False) or final_state.get(
            "current_step"
        ) in ["assembly_complete", "icon_validation_complete", "icon_retry_complete"]

        # Get presentation path and metadata
        presentation_path = final_state.get("presentation_path")
        slide_contents = final_state.get("slide_contents", [])
        selected_layouts = final_state.get("selected_layouts", [])

        # Icon validation results
        icon_errors = final_state.get("icon_errors", [])
        icon_corrections = final_state.get("icon_corrections", {})

        # Calculate metrics
        slide_count = len(slide_contents) if slide_contents else 0
        execution_time = 0  # Could be calculated from monitoring

        # Flush monitoring data
        slide_monitor.flush()

        return {
            "success": success,
            "error": final_state.get("error_message"),
            "current_step": final_state.get("current_step", "unknown"),
            "presentation_path": presentation_path,
            "slide_count": slide_count,
            "layouts_used": selected_layouts,
            "icon_errors_found": len(icon_errors) if icon_errors else 0,
            "icon_corrections_applied": (
                len(icon_corrections) if icon_corrections else 0
            ),
            "agent_results": {
                "layout_analysis": bool(final_state.get("layouts_info")),
                "presentation_planning": bool(final_state.get("presentation_plan")),
                "content_generation": bool(final_state.get("slide_contents")),
                "quality_review": True,  # Always runs
                "slide_assembly": bool(final_state.get("presentation_path")),
                "icon_validation": bool(final_state.get("icon_errors") is not None),
                "icon_retry": bool(final_state.get("icon_corrections")),
            },
            "metadata": {
                "topic": final_state.get("topic", "Unknown"),
                "template_path": final_state.get("template_path", "Unknown"),
                "execution_time": execution_time,
                "total_tokens": 0,  # Could be calculated from monitoring
                "cost_estimate": 0.0,  # Could be calculated from monitoring
            },
        }

    # Agent node wrapper methods
    def _layout_analysis_node(
        self, state: SlideGenerationState, config: Optional[RunnableConfig] = None
    ) -> SlideGenerationState:
        """Layout analysis agent node"""
        return self.layout_agent.execute(state, config)

    def _presentation_planning_node(
        self, state: SlideGenerationState, config: Optional[RunnableConfig] = None
    ) -> SlideGenerationState:
        """Presentation planning agent node"""
        return self.planning_agent.execute(state, config)

    def _content_generation_node(
        self, state: SlideGenerationState, config: Optional[RunnableConfig] = None
    ) -> SlideGenerationState:
        """Content generation agent node"""
        return self.content_agent.execute(state, config)

    def _html_content_generation_node(
        self, state: SlideGenerationState, config: Optional[RunnableConfig] = None
    ) -> SlideGenerationState:
        """HTML content generation agent node"""
        return self.html_content_agent.execute(state, config)

    def _html_refinement_node(
        self, state: SlideGenerationState, config: Optional[RunnableConfig] = None
    ) -> SlideGenerationState:
        """HTML refinement agent node with configurable parallel processing"""

        if not self.use_parallel_html_refinement:
            print("🔄 Using sequential HTML refinement")
            return self.refinement_agent.execute(state, config)

        # Try to use parallel refinement
        try:
            # Check if we're already in an async context
            try:
                loop = asyncio.get_running_loop()
                # If we're in an async context, we need to handle this differently
                print(
                    "⚠️ Running in async context, using sequential fallback for HTML refinement"
                )
                return self.refinement_agent.execute(state, config)
            except RuntimeError:
                # No running loop, we can safely use asyncio.run
                print("🔄 Using parallel HTML refinement for better performance")
                return asyncio.run(
                    self.refinement_agent.execute_parallel(state, config)
                )
        except Exception as e:
            print(f"❌ Parallel HTML refinement failed: {e}")
            print("🔄 Falling back to sequential HTML refinement")
            return self.refinement_agent.execute(state, config)

    def _quality_review_node(
        self, state: SlideGenerationState, config: Optional[RunnableConfig] = None
    ) -> SlideGenerationState:
        """Quality review agent node"""
        return self.quality_agent.execute(state, config)

    def _slide_assembly_node(
        self, state: SlideGenerationState, config: Optional[RunnableConfig] = None
    ) -> SlideGenerationState:
        """Slide assembly agent node"""
        return self.assembly_agent.execute(state, config)

    def _icon_validation_node(
        self, state: SlideGenerationState, config: Optional[RunnableConfig] = None
    ) -> SlideGenerationState:
        """Icon validation agent node"""
        return self.icon_validator.execute(state, config)

    def _icon_retry_node(
        self, state: SlideGenerationState, config: Optional[RunnableConfig] = None
    ) -> SlideGenerationState:
        """Icon retry node - applies corrections and re-runs slide assembly"""
        print("🔄 icon_retry: Applying icon corrections and retrying assembly...")

        try:
            # Check if we have corrections to apply
            icon_corrections = state.get("icon_corrections", {})
            if not icon_corrections:
                print("✅ icon_retry: No corrections to apply")
                state["needs_icon_retry"] = False
                state["current_step"] = "icon_retry_complete"
                return state

            # Apply icon corrections to slide contents
            slide_contents = state.get("slide_contents")
            if not slide_contents:
                raise ValueError("No slide contents to correct")

            corrected_contents = self._apply_icon_corrections(
                slide_contents, icon_corrections
            )

            print(f"🔧 icon_retry: Applied {len(icon_corrections)} corrections")

            # Update state with corrected contents
            state["slide_contents"] = corrected_contents

            # Re-run slide assembly with corrected icons
            updated_state = self.assembly_agent.execute(state, config)

            # Check if we still have icon errors after correction
            remaining_errors = updated_state.get("icon_errors", [])
            if remaining_errors:
                error_count = len(remaining_errors)
                print(f"⚠️ icon_retry: Still have {error_count} errors after fix")
                # Could implement further retry logic here
                updated_state["needs_icon_retry"] = False
            else:
                print("✅ icon_retry: All icon errors resolved")
                updated_state["needs_icon_retry"] = False

            updated_state["current_step"] = "icon_retry_complete"
            return updated_state

        except Exception as e:
            print(f"❌ icon_retry: Error during icon retry: {e}")
            state["error_message"] = f"Icon retry failed: {str(e)}"
            state["current_step"] = "error"
            return state

    def _apply_icon_corrections(
        self, slide_contents: List[Any], icon_corrections: Dict[str, str]
    ) -> List[Any]:
        """
        Apply icon corrections to slide contents

        Args:
            slide_contents: List of slide content objects
            icon_corrections: Dictionary mapping invalid to valid icon names

        Returns:
            Updated slide contents with corrected icon names
        """
        corrected_contents = []

        for slide_content in slide_contents:
            if hasattr(slide_content, "content") and slide_content.content:
                # Apply corrections to the content dictionary
                corrected_content = {}
                for key, value in slide_content.content.items():
                    # Check if this is an icon field and needs correction
                    if key.lower().startswith("icon") and value in icon_corrections:
                        corrected_value = icon_corrections[value]
                        print(
                            f"   📝 Correcting '{value}' → '{corrected_value}' in {key}"
                        )
                        corrected_content[key] = corrected_value
                    else:
                        corrected_content[key] = value

                # Create new slide content with corrected content
                new_slide_content = type(slide_content)(
                    layout_index=slide_content.layout_index, content=corrected_content
                )
                corrected_contents.append(new_slide_content)
            else:
                # No content to correct, keep original
                corrected_contents.append(slide_content)

        return corrected_contents

    def _error_handler_node(
        self, state: SlideGenerationState, config: Optional[RunnableConfig] = None
    ) -> SlideGenerationState:
        """Error handling node"""
        print("🚨 Workflow error handler activated")
        error_message = state.get("error_message", "Unknown error")
        print(f"💭 Error details: {error_message}")

        state["success"] = False
        state["current_step"] = "workflow_failed"

        return state

    # Conditional edge functions
    def _check_analysis_success(self, state: SlideGenerationState) -> str:
        """Check if layout analysis was successful"""
        if state.get("current_step") == "layout_analysis_complete":
            return "success"
        return "error"

    def _check_planning_success(self, state: SlideGenerationState) -> str:
        """Check if presentation planning was successful"""
        if state.get("current_step") == "planning_complete":
            return "success"
        return "error"

    def _check_content_success(self, state: SlideGenerationState) -> str:
        """Check if content generation was successful"""
        if state.get("current_step") == "content_generation_complete":
            return "success"
        return "error"

    def _check_html_refinement_status(self, state: SlideGenerationState) -> str:
        """Check if HTML refinement should continue"""
        if state.get("current_step") == "html_refinement_complete":
            return "continue"

        iteration = state.get("html_refinement_iteration", 0)
        if iteration < 3:
            return "refine"
        return "continue"

    def _check_assembly_success(self, state: SlideGenerationState) -> str:
        """Check if slide assembly was successful"""
        if state.get("current_step") == "assembly_complete":
            # Check if there are icon errors that need validation
            icon_errors = state.get("icon_errors", [])
            if icon_errors:
                return "success_with_icon_errors"
            return "success_no_icon_errors"
        return "error"

    def _check_icon_validation_success(self, state: SlideGenerationState) -> str:
        """Check if icon validation was successful"""
        if state.get("current_step") == "icon_validation_complete":
            if state.get("needs_icon_retry"):
                return "retry_needed"
            return "no_retry_needed"
        return "error"

    def _check_icon_retry_success(self, state: SlideGenerationState) -> str:
        """Check if icon retry was successful"""
        if state.get("current_step") == "icon_retry_complete":
            return "success"
        return "error"


# Convenience function for easy workflow execution
def create_presentation_with_agents(
    topic: str,
    template_path: str = "ekona_slides_template_new.pptx",
    output_path: str = "generated_presentation",
    layout_indices: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """
    Create a PowerPoint presentation using the AI agent workflow

    Args:
        topic: Presentation topic
        template_path: Path to PowerPoint template
        output_path: Output path for generated presentation
        layout_indices: Optional specific layouts to use

    Returns:
        Dictionary with creation results and metadata
    """
    workflow = SlideGenerationWorkflow()

    return workflow.run(
        topic=topic,
        template_path=template_path,
        output_path=output_path,
        layout_indices=layout_indices,
    )
