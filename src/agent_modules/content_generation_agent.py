"""
Content Generation Agent Module

Agent responsible for generating content for each slide
using dynamic models and contextual awareness of the full presentation.
"""

from typing import Any, Dict, List, Optional

from langchain_core.runnables import RunnableConfig

from ..llm_client import LangchainLLMClient, SlideContent
from ..monitoring import monitor_agent_execution
from ..state import SlideGenerationState


class ContentGenerationAgent:
    """
    Agent responsible for generating content for each slide
    using dynamic models and contextual awareness of the full presentation
    """

    def __init__(self):
        self.name = "content_generator"
        self.llm_client = LangchainLLMClient()

    @monitor_agent_execution("content_generator")
    def execute(
        self, state: SlideGenerationState, config: Optional[RunnableConfig] = None
    ) -> SlideGenerationState:
        """
        Generate content for all slides in the presentation plan with full context

        Args:
            state: Current workflow state
            config: Langchain configuration with callbacks

        Returns:
            Updated state with generated slide contents
        """
        print(f"✍️ {self.name}: Generating slide content...")

        try:
            # Check prerequisites
            presentation_plan = state.get("presentation_plan")
            layouts_info = state.get("layouts_info")

            if not presentation_plan or not layouts_info:
                raise ValueError("Presentation plan and layout info required")

            dynamic_models = state.get("dynamic_models") or {}
            topic = state["topic"]
            approved_outline = state.get("approved_outline")

            # Generate content for all slides with full presentation context
            slide_contents = self._generate_contextual_presentation_content(
                topic=topic,
                presentation_plan=presentation_plan,
                layouts_info=layouts_info,
                dynamic_models=dynamic_models,
                approved_outline=approved_outline,
                config=config,
            )

            # Update state with generated content
            state["slide_contents"] = slide_contents
            state["current_step"] = "content_generation_complete"

            print(f"✅ {self.name}: Generated content for {len(slide_contents)} slides")

            return state

        except Exception as e:
            print(f"❌ {self.name}: Error during content generation: {e}")
            state["error_message"] = f"Content generation failed: {str(e)}"
            state["current_step"] = "error"
            return state

    def _generate_contextual_presentation_content(
        self,
        topic: str,
        presentation_plan,  # Can be either List[SlideSpec] or PresentationPlan object
        layouts_info: Dict[int, Dict[str, Any]],
        dynamic_models: Dict[int, Any],
        approved_outline: Optional[Dict[str, Any]] = None,
        config: Optional[RunnableConfig] = None,
    ) -> List[SlideContent]:
        """
        Generate content for all slides with full presentation context using
        unified generation for better coherence, with HTML-awareness

        Args:
            topic: Presentation topic
            presentation_plan: Complete presentation plan with HTML flags (can be List[SlideSpec] or PresentationPlan)
            layouts_info: Layout information for all slides
            dynamic_models: Dynamic models for content generation

        Returns:
            List of generated slide content with HTML-awareness
        """
        # Handle both List[SlideSpec] and PresentationPlan object
        from ..llm_models import PresentationPlan

        if isinstance(presentation_plan, PresentationPlan):
            slides_to_process = presentation_plan.slides
        else:
            slides_to_process = presentation_plan

        print("  📋 Presentation Outline:")
        for i, slide_spec in enumerate(slides_to_process, 1):
            html_indicator = " (HTML)" if slide_spec.is_html else ""
            print(f"    {i}. {slide_spec.slide_title}{html_indicator}")

        print(
            f"  🔄 Generating ALL {len(slides_to_process)} slides with HTML-awareness..."
        )

        # Use unified generation for better context and coherence with HTML flags
        slide_contents = self.llm_client.generate_unified_presentation_content(
            topic=topic,
            presentation_plan=slides_to_process,  # Pass the slides list
            layouts_info=layouts_info,
            config=config,
        )

        if slide_contents:
            print(f"  ✅ Generated unified content for {len(slide_contents)} slides")
            return slide_contents
        # Print the first 50 characters of each generated slide content for inspection
        if slide_contents:
            for idx, slide_content in enumerate(slide_contents, 1):
                # Get the content dict for this slide
                content_dict = getattr(slide_content, "content", {})
                # Concatenate all placeholder values into a single string
                all_content = " ".join(str(v) for v in content_dict.values())
                preview = all_content[:50]
                print(f"    Slide {idx} content preview: {preview!r}")
        print("  ⚠️ Unified generation failed, falling back to individual generation")
        # Fallback to individual generation if unified fails
        return self._generate_individual_slide_content(
            topic, slides_to_process, layouts_info, dynamic_models, config
        )

    def _generate_individual_slide_content(
        self,
        topic: str,
        presentation_plan,  # Can be either List[SlideSpec] or slides to process
        layouts_info: Dict[int, Dict[str, Any]],
        dynamic_models: Dict[int, Any],
        config: Optional[RunnableConfig] = None,
    ) -> List[SlideContent]:
        """
        Fallback method: Generate content for slides individually
        (used only if unified generation fails)
        """
        slide_contents = []

        print("  🔄 Fallback: Generating slides individually...")

        # Ensure we have a list of slides to process
        slides_to_process = (
            presentation_plan
            if isinstance(presentation_plan, list)
            else presentation_plan.slides
        )

        # Generate content for all slides with awareness of the full presentation
        for i, slide_spec in enumerate(slides_to_process, 1):
            slide_title = slide_spec.slide_title
            print(f"  📝 Generating slide {i}/{len(slides_to_process)}: {slide_title}")

            # Get layout information
            layout_info = layouts_info.get(slide_spec.layout_index)
            if not layout_info:
                error_msg = f"Layout {slide_spec.layout_index} not found"
                raise ValueError(error_msg)

            # Get dynamic model for this layout
            dynamic_model = dynamic_models.get(slide_spec.layout_index)

            # Generate content with full presentation context
            slide_content = self.llm_client.generate_contextual_slide_content(
                layout_info=layout_info,
                topic=topic,
                slide_spec=slide_spec,
                slide_number=i,
                total_slides=len(slides_to_process),
                dynamic_model=dynamic_model,
                config=config,
            )

            if slide_content:
                slide_contents.append(slide_content)
                print(f"  ✅ Generated content for slide {i}")
            else:
                print(f"  ⚠️ Failed to generate content for slide {i}")

        return slide_contents

    # TODO: Add context methods for enhanced slide generation
    # These will pass full presentation context to improve content coherence