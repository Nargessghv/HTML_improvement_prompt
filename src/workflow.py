"""
Workflow Module

Langgraph workflow orchestration for the slide generation process.
Coordinates agents and manages the overall presentation creation flow.
"""

from typing import Any, Dict, List, Optional

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from .agents import (
    ContentGenerationAgent,
    LayoutAnalysisAgent,
    PresentationPlanningAgent,
    QualityReviewAgent,
    SlideAssemblyAgent,
    SlideGenerationState,
)
from .monitoring import slide_monitor


class SlideGenerationWorkflow:
    """
    Langgraph workflow for coordinated slide generation using AI agents

    This workflow orchestrates multiple specialized agents to create
    PowerPoint presentations with comprehensive monitoring and error handling.
    """

    def __init__(self):
        """Initialize the workflow with all agent instances"""
        self.layout_agent = LayoutAnalysisAgent()
        self.planning_agent = PresentationPlanningAgent()
        self.content_agent = ContentGenerationAgent()
        self.assembly_agent = SlideAssemblyAgent()
        self.quality_agent = QualityReviewAgent()

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
        workflow.add_node("quality_review", self._quality_review_node)
        workflow.add_node("slide_assembly", self._slide_assembly_node)
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

        # Content generation -> Quality review or Error
        workflow.add_conditional_edges(
            "content_generation",
            self._check_content_success,
            {"success": "quality_review", "error": "error_handler"},
        )

        # Quality review -> Assembly (always proceed, as quality is optional)
        workflow.add_edge("quality_review", "slide_assembly")

        # Assembly -> End or Error
        workflow.add_conditional_edges(
            "slide_assembly",
            self._check_assembly_success,
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
            "layouts_info": None,
            "dynamic_models": None,
            "presentation_plan": None,
            "selected_layouts": None,
            "slide_contents": None,
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
            return self._process_workflow_results(final_state)

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

    def _process_workflow_results(self, final_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and format final workflow results

        Args:
            final_state: Final workflow state

        Returns:
            Formatted results dictionary
        """
        success = final_state.get("success", False)
        error_message = final_state.get("error_message")
        presentation_path = final_state.get("presentation_path")
        current_step = final_state.get("current_step", "unknown")

        if success and presentation_path:
            print("🎉 Slide generation workflow completed successfully!")
            print(f"📄 Presentation saved: {presentation_path}")

            return {
                "success": True,
                "presentation_path": presentation_path,
                "current_step": current_step,
                "slide_count": len(final_state.get("slide_contents") or []),
                "layouts_used": final_state.get("selected_layouts", []),
                "error": None,
            }
        print("❌ Slide generation workflow failed")
        if error_message:
            print(f"💭 Error: {error_message}")

        return {
            "success": False,
            "presentation_path": None,
            "current_step": current_step,
            "error": error_message or "Unknown workflow error",
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

    def _check_assembly_success(self, state: SlideGenerationState) -> str:
        """Check if slide assembly was successful"""
        if state.get("current_step") == "assembly_complete":
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
