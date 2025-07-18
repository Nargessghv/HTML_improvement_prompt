"""
Agent Nodes Module

Langgraph agent implementations for the slide generation workflow.
Each agent handles a specific step in the presentation creation process.
"""

import os
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

    # Icon validation results
    icon_errors: Optional[List[str]]
    icon_corrections: Optional[Dict[str, str]]
    needs_icon_retry: bool

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

            # Add debugging to detect sequential layout assignment
            if len(selected_layouts) >= 5:
                is_sequential = all(
                    selected_layouts[i] == selected_layouts[i - 1] + 1
                    for i in range(1, min(5, len(selected_layouts)))
                )
                if is_sequential:
                    print("⚠️ WARNING: Detected sequential layout assignment!")
                    print(f"   Layout pattern: {selected_layouts}")
                    print("   This suggests the LLM defaulted to sequential ordering")
                    print("   instead of strategic content-based selection.")

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
        """Create enhanced prompt for strategic presentation planning with explicit HTML decisions"""
        # Analyze layouts to identify HTML-capable ones
        layout_descriptions = []
        html_capable_layouts = []

        for layout_index, layout_info in layouts_info.items():
            layout_name = layout_info.get("name", f"Layout {layout_index}")
            placeholders = layout_info.get("placeholders", [])

            # Build placeholder description
            placeholder_text = "No placeholders"
            if placeholders:
                placeholder_names = []
                has_picture_placeholder = False

                for placeholder in placeholders:
                    if isinstance(placeholder, dict):
                        name = placeholder.get("name", "Unknown")
                        placeholder_names.append(name)
                        # Check if this layout has picture placeholders for HTML
                        html_keywords = ["picture", "image", "visual", "html"]
                        if any(keyword in name.lower() for keyword in html_keywords):
                            has_picture_placeholder = True
                    else:
                        placeholder_names.append(str(placeholder))

                placeholder_text = ", ".join(placeholder_names)

                # Track HTML-capable layouts
                if has_picture_placeholder:
                    html_capable_layouts.append(layout_index)

            layout_descriptions.append(
                f"Layout {layout_index} - {layout_name}: {placeholder_text}"
            )

        layouts_text = "\n".join(layout_descriptions)
        html_layouts_text = (
            ", ".join(map(str, html_capable_layouts))
            if html_capable_layouts
            else "None identified"
        )

        return f"""
Create a strategic presentation plan for the topic: "{topic}"

Available layouts for you to choose from, you can use the same layout for
multiple slides when it makes sense.

Here are the layouts:
{layouts_text}

🎯 HTML-CAPABLE LAYOUTS: {html_layouts_text}
These layouts have picture placeholders that can display rich HTML visualizations.

🎯 CRITICAL DECISION REQUIREMENTS:
1. **EXPLICITLY DECIDE** which slides should use HTML visualizations
2. **DO NOT use layouts sequentially** (0,1,2,3,4,5,6,7,8,9)
3. **CHOOSE layouts based on CONTENT TYPE**, not sequence
4. **PRIORITIZE HTML** for visual content types
5. **REUSE effective layouts** for similar content types

🎨 WHEN TO USE HTML VISUALIZATIONS (set is_html: true):
- **Timelines, roadmaps, chronological sequences** → Perfect for HTML
- **Process flows, workflows, step-by-step procedures** → Ideal for HTML  
- **Comparisons, before/after scenarios** → Great for HTML
- **Data visualizations, metrics, statistics** → Excellent for HTML
- **Complex diagrams, hierarchies, relationships** → Best with HTML
- **Any content requiring custom graphics or visual flow** → Use HTML

🚫 WHEN NOT TO USE HTML (set is_html: false):
- **Simple text content** → Regular text placeholders
- **Basic bullet points** → Standard text formatting  
- **Icon-heavy content** → Use icon placeholders instead
- **Chart data** → Use chart placeholders
- **Simple titles and descriptions** → Regular text

Strategic Guidelines:
- **Title slides**: Use layouts with title placeholders (0, 1, 2, 3)  
- **HTML Visualizations**: Use HTML-capable layouts with is_html: true
- **Content with icons**: Prefer layouts with multiple icon placeholders (7, 8)
- **Charts/Data**: Use chart-specific layouts (5, 6) with is_html: false for simple data
- **Images**: Use picture-focused layouts (2, 4)
- **Conclusion**: Use conclusion-specific layouts (8, 9)

Content Planning Requirements:
1. Use the right number of slides for comprehensive coverage, but do not 
   exceed 15 slides
2. Create a logical flow from introduction to conclusion  
3. **EXPLICITLY SET is_html flag** for each slide based on content type
4. Ensure each slide has a clear purpose and advances the narrative
5. IMPORTANT: You can and SHOULD use the same layout for multiple slides 
   when it makes sense
6. Make the presentation engaging and informative
7. Use HTML visualizations strategically for maximum visual impact
8. Some slides are available in the template for branding (e.g Logo, why 
   ekona etc..) add them to the presentation plan.

🚫 AVOID THESE ANTI-PATTERNS:
- Sequential layout usage (0,1,2,3,4,5,6,7,8,9)
- Using every available layout regardless of content fit
- Forcing layout variety over content quality
- Setting is_html: true for simple text content
- Missing HTML opportunities for visual content

✅ PREFERRED PATTERNS:
- Content-driven selection: [0,1,3(HTML),7,7,7,2,8] 
- Strategic HTML use: [0,1,3(HTML),3(HTML),5,7,8]
- Purpose-focused: [0,3(HTML),2,7,7,7,7,8]
- HTML-focused: [0,3(HTML),3(HTML),7,3(HTML),8]

CRITICAL: For each slide in your plan, you MUST explicitly decide whether 
is_html should be true or false based on the content type and visualization needs.

🎯 DETAILED PURPOSE SPECIFICATIONS REQUIRED:
For EVERY slide, provide:
1. **slide_purpose**: Clear basic purpose (1-2 sentences)
2. **detailed_purpose**: Comprehensive explanation of what should be 
   represented (3-4 sentences)
3. **content_structure**: Specific content organization requirements 
   (e.g., "two-column comparison", "numbered list of 5 steps")
4. **visual_elements**: Required visual elements 
   (e.g., "icons showing growth, timeline markers, comparison arrows")
5. **key_information**: List of 3-5 key information points that must be included

🎨 FOR HTML SLIDES (when is_html: true), ALSO provide:
6. **html_requirements**: Specific HTML visualization requirements:
   - Timeline: "horizontal timeline with 4 milestones, each with date, title, 
     and description"
   - Process: "4-step process flow in 2x2 grid, each step with icon, title, 
     and 2-3 bullet points"
   - Comparison: "side-by-side comparison table with 3 categories and 
     5 comparison points each"
   - Data viz: "infographic with 3 key metrics, each with large number, icon, 
     and trend indicator"

📝 EXAMPLES OF DETAILED SPECIFICATIONS:

Standard Slide Example:
- slide_purpose: "Introduce the company and establish credibility"
- detailed_purpose: "Present Ekona as a trusted partner with proven expertise 
  in digital transformation. Build confidence through showcasing experience, 
  client success stories, and key differentiators that make us the right choice."
- content_structure: "Title with company tagline, 3-column layout with 
  expertise areas, testimonial quote"
- visual_elements: "Company logo, 3 icons representing key service areas, 
  star rating or badge"
- key_information: ["15+ years of experience", "200+ successful projects", 
  "95% client satisfaction rate", "Award-winning innovation approach"]

HTML Slide Example:
- slide_purpose: "Show project timeline and key milestones"
- detailed_purpose: "Present a comprehensive project roadmap that demonstrates 
  structured approach, realistic timelines, and clear deliverables. Help client 
  understand project phases and feel confident about the planned approach."
- content_structure: "Title explaining timeline scope, horizontal timeline 
  with clear phases"
- html_requirements: "Horizontal timeline with 5 major milestones spanning 
  6 months. Each milestone should include: month indicator, phase name, 
  2-3 key deliverables, and icon representing the phase type. Use Ekona red 
  for completed phases and grey for future phases."
- visual_elements: "Timeline markers, phase icons (planning, development, 
  testing, launch, support), progress indicators"
- key_information: ["Discovery & Planning (Month 1)", 
  "Development Phase (Months 2-4)", "Testing & QA (Month 5)", 
  "Launch & Deployment (Month 6)", "Ongoing Support"]

Consider the audience and the topic's complexity when planning the structure.
Focus on telling a compelling story with strategic HTML visualizations that 
enhance understanding and engagement.
"""

    def _get_planning_system_prompt(self) -> str:
        """Get the system prompt for presentation planning"""
        return """You are an expert presentation designer specialized in creating 
engaging, data-rich presentations with detailed purpose specifications and 
strategic HTML visualization decisions.

🎯 PRIMARY MISSION: Create comprehensive presentation plans with detailed purpose 
specifications that flow through the entire content generation pipeline.

CRITICAL RESPONSIBILITIES:
1. **DETAILED PURPOSE SPECIFICATIONS**: For every slide, provide comprehensive 
   specifications including detailed_purpose, content_structure, visual_elements, 
   key_information, and html_requirements (for HTML slides)
2. **HTML VISUALIZATION DECISIONS**: Explicitly decide which slides should use 
   HTML visualizations and provide specific HTML requirements
3. **Strategic Layout Selection**: Choose layouts based on content type, not sequence
4. **Content Flow Planning**: Ensure each slide's purpose aligns with overall 
   presentation narrative and provides clear guidance for content generation

DETAILED SPECIFICATION REQUIREMENTS:
✅ ALWAYS PROVIDE for every slide:
- slide_purpose: Clear, concise purpose statement
- detailed_purpose: 3-4 sentence comprehensive explanation
- content_structure: Specific organization requirements
- visual_elements: Required visual components
- key_information: 3-5 essential information points

✅ ADDITIONALLY PROVIDE for HTML slides (is_html: true):
- html_requirements: Detailed HTML visualization specifications

HTML DECISION FRAMEWORK:
✅ SET is_html: true FOR:
- Timelines, roadmaps, chronological sequences
- Process flows, workflows, step-by-step procedures  
- Comparisons, before/after scenarios, competitive analysis
- Data visualizations, metrics dashboards, statistics
- Complex diagrams, hierarchies, organizational charts
- Any content requiring custom graphics or interactive-style visuals

❌ SET is_html: false FOR:
- Simple text content, bullet points
- Basic titles and descriptions
- Icon-heavy content (use icon placeholders instead)
- Standard chart data (use chart placeholders)
- Introductory or concluding slides with minimal visuals

STRATEGIC PRINCIPLES:
- **Purpose-Driven Design**: Every specification must serve the slide's purpose
- **Content Generation Guidance**: Specifications must provide clear guidance 
  for content and HTML generation agents
- **Audience Engagement**: Prioritize visual elements that enhance understanding
- **Presentation Coherence**: Ensure all slides work together as a unified story
- **Implementation Clarity**: Specifications must be detailed enough for 
  accurate implementation

Focus on creating presentations with crystal-clear specifications that enable 
precise content generation and compelling visual storytelling."""

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
        Generate content for all slides with full presentation context using
        unified generation for better coherence, with HTML-awareness

        Args:
            topic: Presentation topic
            presentation_plan: Complete presentation plan with HTML flags
            layouts_info: Layout information for all slides
            dynamic_models: Dynamic models for content generation

        Returns:
            List of generated slide content with HTML-awareness
        """
        print("  📋 Presentation Outline:")
        for i, slide_spec in enumerate(presentation_plan, 1):
            html_indicator = " (HTML)" if slide_spec.is_html else ""
            print(f"    {i}. {slide_spec.slide_title}{html_indicator}")

        print(
            f"  🔄 Generating ALL {len(presentation_plan)} slides with HTML-awareness..."
        )

        # Use unified generation for better context and coherence with HTML flags
        slide_contents = self.llm_client.generate_unified_presentation_content(
            topic=topic,
            presentation_plan=presentation_plan,
            layouts_info=layouts_info,
            config=config,
        )

        if slide_contents:
            print(f"  ✅ Generated unified content for {len(slide_contents)} slides")
            return slide_contents
        print("  ⚠️ Unified generation failed, falling back to individual generation")
        # Fallback to individual generation if unified fails
        return self._generate_individual_slide_content(
            topic, presentation_plan, layouts_info, dynamic_models, config
        )

    def _generate_individual_slide_content(
        self,
        topic: str,
        presentation_plan: List[SlideSpec],
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

            # Generate content with full presentation context
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

            # Initialize slide generator with icon management
            slide_generator = SlideGenerator(state["template_path"])

            # Set up layout information for proper placeholder mapping
            # Use the layouts_info from the LayoutAnalysisAgent
            slide_generator.content_generator.layouts_info = layouts_info

            # Pass topic to slide generator for icon-aware content population
            slide_generator._current_topic = state["topic"]

            # Capture icon errors during presentation creation
            import io
            from contextlib import redirect_stderr, redirect_stdout

            # Capture stdout and stderr to collect icon warning messages
            captured_output = io.StringIO()
            captured_errors = io.StringIO()

            with redirect_stdout(captured_output), redirect_stderr(captured_errors):
                # Create presentation using existing working method
                # The SlideGenerator already has icon support built-in
                presentation = slide_generator._create_powerpoint_presentation(
                    slide_contents
                )

            # Extract icon errors from captured output
            all_output = captured_output.getvalue() + captured_errors.getvalue()
            icon_errors = self._extract_icon_errors_from_output(all_output)

            # Print the captured output to user so they can see progress
            if captured_output.getvalue():
                print(captured_output.getvalue(), end="")

            # Determine if we need icon validation
            needs_icon_retry = len(icon_errors) > 0

            # Save the presentation
            full_output_path = slide_generator._ensure_output_path(state["output_path"])
            presentation.save(full_output_path)

            # Update state with results
            state["presentation_path"] = full_output_path
            state["icon_errors"] = icon_errors
            state["needs_icon_retry"] = needs_icon_retry
            state["current_step"] = "assembly_complete"
            state["success"] = True

            if icon_errors:
                print(f"⚠️ {self.name}: Found {len(icon_errors)} icon errors")
                print(f"🔄 {self.name}: Will proceed to icon validation")
            else:
                print(f"✅ {self.name}: No icon errors detected")

            print(f"✅ {self.name}: Presentation saved to {full_output_path}")

            return state

        except Exception as e:
            print(f"❌ {self.name}: Error during slide assembly: {e}")
            state["error_message"] = f"Slide assembly failed: {str(e)}"
            state["current_step"] = "error"
            state["success"] = False
            return state

    def _extract_icon_errors_from_output(self, output: str) -> List[str]:
        """
        Extract icon error messages from the output stream.
        This is a placeholder and needs to be implemented based on
        the actual output format of the SlideGenerator.
        """
        icon_errors = []
        # Example: Look for lines starting with "Warning: SVG icon not found:"
        # or "Warning: Icon '... not found or failed to prepare"
        for line in output.splitlines():
            if line.startswith("Warning: SVG icon not found:"):
                icon_name = line.replace("Warning: SVG icon not found:", "").strip()
                icon_errors.append(icon_name)
            elif line.startswith("Warning: Icon '"):
                icon_name = (
                    line.replace("Warning: Icon '", "")
                    .replace("' not found or failed to prepare", "")
                    .strip()
                )
                icon_errors.append(icon_name)
        return list(set(icon_errors))  # Remove duplicates


class IconValidationAgent:
    """
    Agent responsible for validating and correcting invalid icon names
    when icon errors are detected during slide assembly
    """

    def __init__(self):
        self.name = "icon_validator"
        # Use OPENAI_MODEL_FAST for icon validation (fast, simple model)
        fast_model = os.getenv("OPENAI_MODEL_FAST", "gpt-4o-mini")
        self.llm_client = LangchainLLMClient(model=fast_model)
        # Initialize icon manager to get list of available icons
        from .icon_manager import IconManager

        self.icon_manager = IconManager()

    @monitor_agent_execution("icon_validator")
    def execute(
        self, state: SlideGenerationState, config: Optional[RunnableConfig] = None
    ) -> SlideGenerationState:
        """
        Validate and correct invalid icon names using LLM knowledge

        Args:
            state: Current workflow state
            config: Langchain configuration with callbacks

        Returns:
            Updated state with corrected icon names
        """
        print(f"�� {self.name}: Validating and correcting icon names...")

        try:
            # Check if we have icon errors to process
            icon_errors = state.get("icon_errors", [])
            if not icon_errors:
                print(f"✅ {self.name}: No icon errors to correct")
                state["needs_icon_retry"] = False
                state["current_step"] = "icon_validation_complete"
                return state

            print(f"⚠️ {self.name}: Found {len(icon_errors)} icon errors to correct")

            # Extract invalid icon names from error messages
            invalid_icons = self._extract_invalid_icon_names(icon_errors)

            if not invalid_icons:
                print(f"✅ {self.name}: No extractable icon names to correct")
                state["needs_icon_retry"] = False
                state["current_step"] = "icon_validation_complete"
                return state

            print(f"🔍 {self.name}: Correcting icons: {invalid_icons}")

            # Use LLM to suggest correct icon names
            icon_corrections = self._get_icon_corrections_from_llm(
                invalid_icons, state["topic"], config
            )

            if icon_corrections:
                print(f"✅ {self.name}: Generated corrections: {icon_corrections}")
                state["icon_corrections"] = icon_corrections
                state["needs_icon_retry"] = True
                state["current_step"] = "icon_validation_complete"
            else:
                print(f"⚠️ {self.name}: No corrections generated")
                state["needs_icon_retry"] = False
                state["current_step"] = "icon_validation_complete"

            return state

        except Exception as e:
            print(f"❌ {self.name}: Error during icon validation: {e}")
            state["error_message"] = f"Icon validation failed: {str(e)}"
            state["current_step"] = "error"
            return state

    def _extract_invalid_icon_names(self, icon_errors: List[str]) -> List[str]:
        """
        Extract invalid icon names from error messages

        Args:
            icon_errors: List of error messages from icon insertion

        Returns:
            List of invalid icon names
        """
        import re

        invalid_icons = []

        for error in icon_errors:
            # Pattern to extract icon name from error messages like:
            # "Warning: SVG icon not found:
            #   node_modules/lucide-static/icons/bar-chart.svg"
            # "Warning: Icon 'money' not found or failed to prepare"

            # Try pattern 1: from SVG path
            match = re.search(r"icons/([^/\.]+)\.svg", error)
            if match:
                invalid_icons.append(match.group(1))
                continue

            # Try pattern 2: from quoted icon name
            match = re.search(r"Icon '([^']+)' not found", error)
            if match:
                invalid_icons.append(match.group(1))
                continue

        return list(set(invalid_icons))  # Remove duplicates

    def _get_icon_corrections_from_llm(
        self,
        invalid_icons: List[str],
        topic: str,
        config: Optional[RunnableConfig] = None,
    ) -> Dict[str, str]:
        """
        Use LLM to suggest correct lucide-static icon names

        Args:
            invalid_icons: List of invalid icon names
            topic: Presentation topic for context
            config: Langchain configuration

        Returns:
            Dictionary mapping invalid icons to corrected icons
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        # Create the correction prompt
        prompt = self._create_icon_correction_prompt(invalid_icons, topic)
        system_prompt = self._get_icon_correction_system_prompt()

        try:
            # Create messages
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=prompt),
            ]

            # Generate corrections using Langchain
            response = self.llm_client.chat_client.invoke(messages, config=config)

            if response and response.content:
                content = str(response.content) if response.content else ""
                return self._parse_icon_corrections(content, invalid_icons)

            print("⚠️ No response received from LLM for icon corrections")
            return {}

        except Exception as e:
            print(f"❌ Error getting icon corrections from LLM: {e}")
            return {}

    def _create_icon_correction_prompt(
        self, invalid_icons: List[str], topic: str
    ) -> str:
        """Create prompt for LLM icon correction"""
        invalid_list = ", ".join(invalid_icons)

        # Get the actual list of available icons from the IconManager
        all_available_icons = self.icon_manager.icons_database.get("all_icons", [])

        # Take a sample of available icons to show in prompt (first 50)
        # Sort alphabetically for better organization
        sample_icons = sorted(all_available_icons)
        available_icons_text = ", ".join(sample_icons)

        # Also get categorized suggestions for context
        icon_categories = self.icon_manager.icons_database.get("categories", {})
        category_samples = {}
        for category, icons in icon_categories.items():
            if icons:
                category_samples[category] = icons[:5]  # First 5 from each category

        return f"""
The following icon names are INVALID in the lucide-static library and need correction:
{invalid_list}

Presentation topic: {topic}

🎯 AVAILABLE LUCIDE-STATIC ICONS:
{available_icons_text}

📊 ICON CATEGORIES WITH EXAMPLES:
{self._format_category_samples(category_samples)}

📋 TOTAL AVAILABLE: {len(all_available_icons)} icons in the lucide-static library

For each invalid icon, suggest the closest valid lucide-static icon name that:
1. ✅ EXISTS in the lucide-static library (from the list above)
2. 🎯 Has similar meaning/purpose to the invalid icon
3. 📝 Fits the presentation topic: "{topic}"
4. 🔤 Uses exact lucide-static naming (hyphen-separated, lowercase)
5. 🔤 Is a possible abstraction of the invalid icon (e.g circle-dot for molecule)

Please respond in this EXACT format:
invalid_icon1 -> valid_icon1
invalid_icon2 -> valid_icon2

Example:
bar-chart -> bar-chart-3
money -> coins
tools -> wrench
time -> clock
check-circle -> circle-check
"""

    def _format_category_samples(self, category_samples: Dict[str, List[str]]) -> str:
        """Format category samples for the prompt"""
        formatted = []
        for category, icons in category_samples.items():
            if icons:
                icons_text = ", ".join(icons)
                formatted.append(f"  • {category}: {icons_text}")
        return "\n".join(formatted)

    def _get_icon_correction_system_prompt(self) -> str:
        """Get system prompt for icon correction"""
        return """You are an expert lucide-static icon validation specialist with 
access to the COMPLETE database of all available lucide-static icons.

🎯 YOUR TASK: Correct invalid icon names to valid lucide-static alternatives using 
the provided comprehensive list of available icons.

🚨 CRITICAL REQUIREMENTS:
- You have been provided with the COMPLETE list of available lucide-static icons
- ONLY suggest icon names that appear in the provided list
- Do NOT rely on general knowledge - use ONLY the provided icon list
- Choose icons with similar semantic meaning to the invalid ones
- Consider the presentation context when choosing alternatives
- Use exact lucide-static naming conventions (lowercase, hyphen-separated)

📋 VALIDATION PROCESS:
1. Review the invalid icon name
2. Find semantically similar icons from the provided available list
3. Select the best match considering the presentation topic
4. Ensure the suggested icon exists in the provided list

You have been given the actual database of available icons - use this authoritative 
source to make accurate corrections."""

    def _parse_icon_corrections(
        self, response_text: str, invalid_icons: List[str]
    ) -> Dict[str, str]:
        """
        Parse LLM response to extract icon corrections

        Args:
            response_text: Raw LLM response
            invalid_icons: Original invalid icon names

        Returns:
            Dictionary mapping invalid to corrected icon names
        """
        corrections = {}

        lines = response_text.strip().split("\n")

        for line in lines:
            line = line.strip()
            if "->" in line:
                parts = line.split("->")
                if len(parts) == 2:
                    invalid = parts[0].strip()
                    valid = parts[1].strip()

                    # Only include if the invalid icon was in our original list
                    if invalid in invalid_icons:
                        corrections[invalid] = valid

        return corrections


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
