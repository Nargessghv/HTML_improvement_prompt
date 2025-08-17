"""
Layout Analysis Agent Module

Agent responsible for analyzing PowerPoint template layouts
and creating dynamic models for content generation.
"""

from typing import Optional

from langchain_core.runnables import RunnableConfig

from ..dynamic_models import create_presentation_models
from ..layout_analyzer import LayoutAnalyzer
from ..monitoring import monitor_agent_execution
from ..state import SlideGenerationState


class LayoutAnalysisAgent:
    """
    Agent responsible for analyzing PowerPoint template layouts
    and creating dynamic models for content generation
    """

    def __init__(self):
        self.name = "layout_analyzer"

    @monitor_agent_execution("layout_analyzer")
    def execute(
        self, state: SlideGenerationState, config: Optional[RunnableConfig] = None
    ) -> SlideGenerationState:
        """
        Analyze template layouts and create dynamic models

        Args:
            state: Current workflow state
            config: Langchain configuration with callbacks

        Returns:
            Updated state with layout analysis results
        """
        print(f"🔍 {self.name}: Analyzing template layouts...")

        try:
            # Initialize layout analyzer
            layout_analyzer = LayoutAnalyzer(state["template_path"])

            # Analyze all layouts in the template
            layouts_info = layout_analyzer.analyze_all_layouts()

            # Create dynamic Pydantic models for structured content generation
            dynamic_models = create_presentation_models(layouts_info)

            # Update state with analysis results
            state["layouts_info"] = layouts_info
            state["dynamic_models"] = dynamic_models
            state["current_step"] = "layout_analysis_complete"

            print(f"✅ {self.name}: Analyzed {len(layouts_info)} layouts")
            print(f"✅ {self.name}: Layout_info: {layouts_info}")
            print(f"✅ {self.name}: Created {len(dynamic_models)} dynamic models")

            return state

        except Exception as e:
            print(f"❌ {self.name}: Error during layout analysis: {e}")
            state["error_message"] = f"Layout analysis failed: {str(e)}"
            state["current_step"] = "error"
            return state