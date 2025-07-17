"""
Agent Nodes Module

Langgraph agent implementations for the slide generation workflow.
Each agent handles a specific step in the presentation creation process.
"""

from typing import Any, Dict, List, Optional, TypedDict

from langchain_core.runnables import RunnableConfig

from .dynamic_models import create_presentation_models
from .layout_analyzer import LayoutAnalyzer
from .llm_client import LangchainLLMClient, SlideContent
from .llm_models import SlideSpec
from .monitoring import monitor_agent_execution, slide_monitor


class SlideGenerationState(TypedDict):
    """
    State object that flows through the agent workflow

    Tracks all data needed for slide generation across different agent steps
    """

    # Input parameters
    topic: str
    template_path: str
    output_path: str
    layout_indices: Optional[List[int]]

    # Workflow state
    current_step: str
    error_message: Optional[str]
    retry_count: int

    # Analysis results
    layouts_info: Optional[Dict[int, Dict[str, Any]]]
    dynamic_models: Optional[Dict[int, Any]]

    # Planning results
    presentation_plan: Optional[List[SlideSpec]]
    selected_layouts: Optional[List[int]]

    # Content generation results
    slide_contents: Optional[List[SlideContent]]

    # Final output
    presentation_path: Optional[str]
    success: bool

    # Monitoring context
    monitor_trace: Optional[Any]


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
            print(f"✅ {self.name}: Created {len(dynamic_models)} dynamic models")

            return state

        except Exception as e:
            print(f"❌ {self.name}: Error during layout analysis: {e}")
            state["error_message"] = f"Layout analysis failed: {str(e)}"
            state["current_step"] = "error"
            return state


class PresentationPlanningAgent:
    """
    Agent responsible for creating intelligent presentation plans
    using LLM to determine optimal slide structure and flow
    """

    def __init__(self):
        self.name = "presentation_planner"
        self.llm_client = LangchainLLMClient()

    @monitor_agent_execution("presentation_planner")
    def execute(
        self, state: SlideGenerationState, config: Optional[RunnableConfig] = None
    ) -> SlideGenerationState:
        """
        Create intelligent presentation plan based on topic and available layouts

        Args:
            state: Current workflow state
            config: Langchain configuration with callbacks

        Returns:
            Updated state with presentation plan
        """
        print(f"📋 {self.name}: Creating presentation plan...")

        try:
            # Check if we have layout analysis results
            layouts_info = state.get("layouts_info")
            if not layouts_info:
                raise ValueError("Layout analysis must be completed first")

            # Handle both list and dictionary formats for layouts_info
            if isinstance(layouts_info, list):
                # Convert list to dictionary if needed
                layouts_dict = {}
                for i, layout in enumerate(layouts_info):
                    layouts_dict[i] = layout
                layouts_info = layouts_dict

            topic = state["topic"]

            # Use LLM to create intelligent presentation plan with callback tracing
            presentation_plan = self._plan_presentation_with_tracing(
                layouts_info, topic, config
            )

            # Extract layout indices from the plan
            selected_layouts = [spec.layout_index for spec in presentation_plan]

            # Update state with planning results
            state["presentation_plan"] = presentation_plan
            state["selected_layouts"] = selected_layouts
            state["current_step"] = "planning_complete"

            print(f"✅ {self.name}: Created plan with {len(presentation_plan)} slides")
            print(f"✅ {self.name}: Selected layouts: {selected_layouts}")

            return state

        except Exception as e:
            print(f"❌ {self.name}: Error during planning: {e}")
            state["error_message"] = f"Presentation planning failed: {str(e)}"
            state["current_step"] = "error"
            return state

    def _plan_presentation_with_tracing(
        self,
        layouts_info: Dict[int, Dict[str, Any]],
        topic: str,
        config: Optional[RunnableConfig] = None,
    ) -> List[SlideSpec]:
        """
        Create intelligent presentation plan using Langchain LLM with tracing

        Args:
            layouts_info: Dictionary of layout information
            topic: The presentation topic
            config: Langchain configuration with callbacks

        Returns:
            List of SlideSpec objects defining the presentation structure
        """
        from .llm_models import PresentationPlan

        # Create the planning prompt
        prompt = self._create_presentation_planning_prompt(layouts_info, topic)
        system_prompt = self._get_planning_system_prompt()

        try:
            # Use structured output with Langchain
            response = self.llm_client.generate_structured_content(
                system_prompt=system_prompt,
                user_prompt=prompt,
                response_model=PresentationPlan,
                config=config,
            )

            if response and hasattr(response, "slides"):
                print(f"Presentation plan created: {response.total_slides} slides")
                print(f"Flow: {response.presentation_flow}")
                print(f"Reasoning: {response.reasoning}")
                return response.slides
            print("Warning: No structured response received")
            return self._create_default_plan(layouts_info)

        except Exception as e:
            print(f"Structured planning failed: {e}")
            return self._create_default_plan(layouts_info)

    def _create_presentation_planning_prompt(
        self, layouts_info: Dict[int, Dict[str, Any]], topic: str
    ) -> str:
        """Create a detailed prompt for presentation planning"""
        # Build layout descriptions
        layout_descriptions = []

        # Handle case where layouts_info might be a list
        # (fix for data structure mismatch)
        if isinstance(layouts_info, list):
            for i, layout_info in enumerate(layouts_info):
                layout_name = (
                    layout_info.get("name", f"Layout {i}")
                    if isinstance(layout_info, dict)
                    else f"Layout {i}"
                )
                placeholders = (
                    layout_info.get("placeholders", {})
                    if isinstance(layout_info, dict)
                    else {}
                )

                if isinstance(placeholders, list) and placeholders:
                    # Handle list of placeholder objects with descriptions
                    placeholder_details = []
                    for p in placeholders:
                        if isinstance(p, dict):
                            name = p.get("name", "Placeholder")
                            instructions = p.get("instructions", "")
                            if instructions:
                                placeholder_details.append(f"{name} ({instructions})")
                            else:
                                placeholder_details.append(name)
                        else:
                            placeholder_details.append(str(p))
                    placeholder_text = f"Placeholders: {'; '.join(placeholder_details)}"
                elif isinstance(placeholders, dict) and placeholders:
                    placeholder_text = f"Placeholders: {', '.join(placeholders.keys())}"
                else:
                    placeholder_text = "No placeholders"

                layout_descriptions.append(
                    f"Layout {i} - {layout_name}: {placeholder_text}"
                )
        else:
            # Original dictionary handling
            for layout_index, layout_info in layouts_info.items():
                layout_name = layout_info.get("name", f"Layout {layout_index}")

                # Check if layout_info has placeholders
                if "placeholders" in layout_info:
                    placeholders = layout_info.get("placeholders", {})
                    if isinstance(placeholders, dict):
                        placeholder_text = (
                            f"Placeholders: {', '.join(placeholders.keys())}"
                        )
                    elif isinstance(placeholders, list):
                        # Handle list of placeholder objects with descriptions
                        placeholder_details = []
                        for p in placeholders:
                            if isinstance(p, dict):
                                name = p.get("name", "Placeholder")
                                instructions = p.get("instructions", "")
                                if instructions:
                                    placeholder_details.append(
                                        f"{name} ({instructions})"
                                    )
                                else:
                                    placeholder_details.append(name)
                            else:
                                placeholder_details.append(str(p))

                        if placeholder_details:
                            placeholder_text = (
                                f"Placeholders: {'; '.join(placeholder_details)}"
                            )
                        else:
                            placeholder_text = "No placeholders"
                    else:
                        placeholder_text = "No placeholders"
                else:
                    placeholder_text = "No placeholders"

                layout_descriptions.append(
                    f"Layout {layout_index} - {layout_name}: {placeholder_text}"
                )

        layouts_text = "\n".join(layout_descriptions)

        return f"""
Create a strategic presentation plan for the topic: "{topic}"

Available layouts:
{layouts_text}

Requirements:
1. Use the right number of slides for comprehensive coverage, but do not 
   exceed 10 slides
2. Create a logical flow from introduction to conclusion
3. Select appropriate layouts for each slide's content type
4. Ensure each slide has a clear purpose and advances the narrative
5. IMPORTANT: You can and SHOULD use the same layout for multiple slides 
   when it makes sense
6. Make the presentation engaging and informative
7. Use icons as much as possible when conveying information
8. Some slides are available in the template for branding (e.g Logo, why 
   ekona etc..) add them to the presentation plan.

STRATEGIC LAYOUT REUSE GUIDELINES:
- Don't feel obligated to use every layout - focus on what serves the content 
  best
- Quality content with repeated effective layouts is better than forced layout 
  variety

Consider the audience and the topic's complexity when planning the structure.
"""

    def _get_planning_system_prompt(self) -> str:
        """Get the system prompt for presentation planning"""
        return """You are an expert presentation designer. Create strategic, 
engaging presentation plans that tell a compelling story. Focus on logical flow, 
audience engagement, and clear communication of key messages."""

    def _create_default_plan(
        self, layouts_info: Dict[int, Dict[str, Any]]
    ) -> List[SlideSpec]:
        """Create a basic default plan if LLM planning fails"""
        from .llm_models import SlideSpec

        # Get the first available layout
        first_layout = next(iter(layouts_info.keys()))

        return [
            SlideSpec(
                layout_index=first_layout,
                slide_title="Introduction",
                slide_purpose="Introduce the topic and key objectives",
            ),
            SlideSpec(
                layout_index=first_layout,
                slide_title="Main Content",
                slide_purpose="Present core information and analysis",
            ),
            SlideSpec(
                layout_index=first_layout,
                slide_title="Conclusion",
                slide_purpose="Summarize key points and next steps",
            ),
        ]


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

            # Generate content for all slides with full presentation context
            slide_contents = self._generate_contextual_presentation_content(
                topic=topic,
                presentation_plan=presentation_plan,
                layouts_info=layouts_info,
                dynamic_models=dynamic_models,
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
        presentation_plan: List[SlideSpec],
        layouts_info: Dict[int, Dict[str, Any]],
        dynamic_models: Dict[int, Any],
        config: Optional[RunnableConfig] = None,
    ) -> List[SlideContent]:
        """
        Generate content for all slides with full presentation context

        Args:
            topic: Presentation topic
            presentation_plan: Complete presentation plan
            layouts_info: Layout information for all slides
            dynamic_models: Dynamic models for content generation

        Returns:
            List of generated slide content with full contextual awareness
        """
        slide_contents = []

        print("  📋 Presentation Outline:")
        for i, slide_spec in enumerate(presentation_plan, 1):
            print(f"    {i}. {slide_spec.slide_title}")

        # Generate content for all slides with awareness of the full presentation
        for i, slide_spec in enumerate(presentation_plan, 1):
            slide_title = slide_spec.slide_title
            print(f"  📝 Generating slide {i}/{len(presentation_plan)}: {slide_title}")

            # Get layout information
            layout_info = layouts_info.get(slide_spec.layout_index)
            if not layout_info:
                error_msg = f"Layout {slide_spec.layout_index} not found"
                raise ValueError(error_msg)

            # Get dynamic model for this layout
            dynamic_model = dynamic_models.get(slide_spec.layout_index)

            # Note: Context tracking for future enhancements

            # Generate content with full presentation context
            # Note: Enhanced contextual information is used internally by the agent
            # but passed through the existing LLM client interface
            slide_content = self.llm_client.generate_contextual_slide_content(
                layout_info=layout_info,
                topic=topic,
                slide_spec=slide_spec,
                slide_number=i,
                total_slides=len(presentation_plan),
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


class SlideAssemblyAgent:
    """
    Agent responsible for assembling the final PowerPoint presentation
    from generated content and template layouts
    """

    def __init__(self):
        self.name = "slide_assembler"

    @monitor_agent_execution("slide_assembler")
    def execute(
        self, state: SlideGenerationState, config: Optional[RunnableConfig] = None
    ) -> SlideGenerationState:
        """
        Assemble final PowerPoint presentation from generated content

        Args:
            state: Current workflow state
            config: Langchain configuration with callbacks

        Returns:
            Updated state with final presentation path
        """
        print(f"🔧 {self.name}: Assembling PowerPoint presentation...")

        try:
            # Check prerequisites
            slide_contents = state.get("slide_contents")
            layouts_info = state.get("layouts_info")

            if not slide_contents or not layouts_info:
                raise ValueError("Slide contents and layout info required")

            # Import here to avoid circular imports
            from .slide_generator import SlideGenerator

            # Initialize slide generator
            slide_generator = SlideGenerator(state["template_path"])

            # Set up layout information for proper placeholder mapping
            # Use the layouts_info from the LayoutAnalysisAgent
            slide_generator.content_generator.layouts_info = layouts_info

            # Create presentation using the already generated slide contents
            # from the workflow. This ensures we use the content created
            # by the ContentGenerationAgent

            # Create PowerPoint presentation from the agent-generated content
            presentation = slide_generator._create_powerpoint_presentation(
                slide_contents
            )

            # Save the presentation
            full_output_path = slide_generator._ensure_output_path(state["output_path"])
            presentation.save(full_output_path)

            output_path = full_output_path

            # Update state with final results
            state["presentation_path"] = output_path
            state["current_step"] = "assembly_complete"
            state["success"] = True

            print(f"✅ {self.name}: Presentation saved to {output_path}")

            return state

        except Exception as e:
            print(f"❌ {self.name}: Error during slide assembly: {e}")
            state["error_message"] = f"Slide assembly failed: {str(e)}"
            state["current_step"] = "error"
            state["success"] = False
            return state


class QualityReviewAgent:
    """
    Agent responsible for reviewing generated content quality
    and providing feedback for improvements
    """

    def __init__(self):
        self.name = "quality_reviewer"
        self.llm_client = LangchainLLMClient()

    @monitor_agent_execution("quality_reviewer")
    def execute(
        self, state: SlideGenerationState, config: Optional[RunnableConfig] = None
    ) -> SlideGenerationState:
        """
        Review content quality and provide improvement suggestions

        Args:
            state: Current workflow state
            config: Langchain configuration with callbacks

        Returns:
            Updated state with quality review results
        """
        print(f"🔍 {self.name}: Reviewing content quality...")

        try:
            # Check prerequisites
            slide_contents = state.get("slide_contents")
            if not slide_contents:
                print(f"⚠️ {self.name}: No content to review, skipping...")
                return state

            topic = state["topic"]

            # Calculate quality metrics
            quality_metrics = self._calculate_quality_metrics(slide_contents, topic)

            # Track quality metrics in monitoring
            monitor_trace = state.get("monitor_trace")
            if monitor_trace:
                slide_monitor.track_content_quality(
                    monitor_trace,
                    {"slide_count": len(slide_contents), "topic": topic},
                    quality_metrics,
                )

            print(f"✅ {self.name}: Quality review complete")
            completeness = quality_metrics.get("completeness", 0)
            relevance = quality_metrics.get("relevance", 0)
            print(f"   📊 Content completeness: {completeness:.1%}")
            print(f"   📊 Topic relevance: {relevance:.1%}")

            return state

        except Exception as e:
            print(f"❌ {self.name}: Error during quality review: {e}")
            # Don't fail the entire workflow for quality review errors
            return state

    def _calculate_quality_metrics(
        self, slide_contents: List[SlideContent], topic: str
    ) -> Dict[str, float]:
        """
        Calculate quality metrics for generated content

        Args:
            slide_contents: List of generated slide content
            topic: Presentation topic

        Returns:
            Dictionary of quality metrics (0.0 to 1.0)
        """
        if not slide_contents:
            return {"completeness": 0.0, "relevance": 0.0}

        # Calculate content completeness
        total_placeholders = sum(
            len(slide.content) for slide in slide_contents if slide.content
        )
        filled_placeholders = sum(
            len([v for v in slide.content.values() if v and str(v).strip()])
            for slide in slide_contents
            if slide.content
        )

        completeness = filled_placeholders / max(total_placeholders, 1)

        # Calculate topic relevance (simple keyword-based approach)
        topic_words = set(topic.lower().split())
        relevant_content_count = 0
        total_content_count = 0

        for slide in slide_contents:
            if slide.content:
                for content in slide.content.values():
                    if content and str(content).strip():
                        total_content_count += 1
                        content_words = set(str(content).lower().split())
                        if topic_words.intersection(content_words):
                            relevant_content_count += 1

        relevance = relevant_content_count / max(total_content_count, 1)

        return {
            "completeness": completeness,
            "relevance": relevance,
            "slide_count": len(slide_contents),
            "total_placeholders": total_placeholders,
            "filled_placeholders": filled_placeholders,
        }
