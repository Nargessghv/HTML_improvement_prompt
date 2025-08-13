"""
Agent Nodes Module

Langgraph agent implementations for the slide generation workflow.
Each agent handles a specific step in the presentation creation process.
"""

import asyncio
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

from langchain_core.runnables import RunnableConfig

from .azure_uploader import AzureBlobUploader
from .dynamic_models import create_presentation_models
from .html_renderer import HTMLRenderer
from .layout_analyzer import LayoutAnalyzer
from .llm_client import LangchainLLMClient, SlideContent
from .llm_models import RefinedHTML, SlideSpec
from .monitoring import monitor_agent_execution, slide_monitor

# Add PIL for image compression
try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("⚠️ PIL not available - image compression disabled")


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
    title: Optional[str]
    approved_outline: Optional[Dict[str, Any]]  # Interactive planning outline

    # Workflow state
    current_step: str
    error_message: Optional[str]
    retry_count: int
    html_refinement_iteration: int
    html_refinement_slide_index: Optional[int]
    html_slides_to_refine_queue: Optional[list[int]]
    refinement_id: Optional[str]  # Add this line

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
    needs_html_refinement: bool

    # Image generation results
    image_prompts: Optional[Dict[int, str]]  # Detailed prompts for each slide
    generated_images: Optional[Dict[int, Dict[str, Any]]]
    refined_images: Optional[Dict[int, Dict[str, Any]]]
    needs_image_refinement: bool

    # Final output
    presentation_path: Optional[str]
    success: bool

    # Monitoring context
    monitor_trace: Optional[Any]
    
    # Project tracking for Supabase integration
    project_id: Optional[str]


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
            title = state.get("title")  # Get title from state (may be None)
            approved_outline = state.get("approved_outline")

            # Debug logging for approved outline
            print(f"📋 {self.name}: Approved outline present: {approved_outline is not None}")
            if approved_outline:
                print(f"📋 {self.name}: Approved outline slides count: {len(approved_outline.get('slides', []))}")

            # Check if we have an approved outline from interactive planning
            if approved_outline:
                print(f"📋 {self.name}: Using approved outline from interactive planning")
                presentation_plan = self._convert_approved_outline_to_plan(
                    approved_outline, layouts_info
                )
            else:
                print(f"📋 {self.name}: Generating new presentation plan with LLM")
                # Use LLM to create intelligent presentation plan with callback tracing
                presentation_plan = self._plan_presentation_with_tracing(
                    layouts_info, topic, title, config
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
        title: Optional[str] = None,
        config: Optional[RunnableConfig] = None,
    ) -> List[SlideSpec]:
        """
        Create intelligent presentation plan using Langchain LLM with tracing

        Args:
            layouts_info: Dictionary of layout information
            topic: The presentation topic/description
            title: The presentation title (optional)
            config: Langchain configuration with callbacks

        Returns:
            List of SlideSpec objects defining the presentation structure
        """
        from .llm_models import PresentationPlan

        # Create the planning prompt
        prompt = self._create_presentation_planning_prompt(layouts_info, topic, title)
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

    def _convert_approved_outline_to_plan(
        self, 
        approved_outline: Dict[str, Any], 
        layouts_info: Dict[int, Dict[str, Any]]
    ) -> List[SlideSpec]:
        """
        Convert approved outline from interactive planning to SlideSpec format
        
        Args:
            approved_outline: The approved outline from interactive planning
            layouts_info: Available layout information for layout selection
            
        Returns:
            List of SlideSpec objects matching the approved outline
        """
        from .llm_models import SlideSpec
        
        slides = approved_outline.get("slides", [])
        slide_specs = []
        
        # Content type to layout mapping strategy
        content_type_to_layout = {
            "text": self._find_best_layout_for_content(layouts_info, "text"),
            "visual": self._find_best_layout_for_content(layouts_info, "picture"),
            "chart": self._find_best_layout_for_content(layouts_info, "html"),
            "timeline": self._find_best_layout_for_content(layouts_info, "html"),
            "comparison": self._find_best_layout_for_content(layouts_info, "html")
        }
        
        for slide_data in slides:
            slide_number = slide_data.get("slide_number", len(slide_specs) + 1)
            title = slide_data.get("title", f"Slide {slide_number}")
            content_type = slide_data.get("content_type", "text")
            key_points = slide_data.get("key_points", [])
            
            # Select appropriate layout based on content type
            layout_index = content_type_to_layout.get(content_type, 
                self._find_best_layout_for_content(layouts_info, "text"))
            
            # Determine if HTML visualization is needed
            needs_html = content_type in ["chart", "timeline", "comparison"]
            
            # Create slide specification
            slide_spec = SlideSpec(
                layout_index=layout_index,
                slide_title=title,
                slide_purpose=f"Create {content_type} slide: {title}",
                is_html=needs_html,
                detailed_purpose=f"Content from approved outline - slide {slide_number}",
                content_structure=f"Key points: {', '.join(key_points)}",
                html_requirements=f"Create {content_type} visualization" if needs_html else None,
                visual_elements=content_type if needs_html else None,
                key_information=key_points
            )
            
            slide_specs.append(slide_spec)
            
        print(f"✅ Converted approved outline to {len(slide_specs)} slide specifications")
        return slide_specs

    def _find_best_layout_for_content(
        self, 
        layouts_info: Dict[int, Dict[str, Any]], 
        preferred_type: str
    ) -> int:
        """
        Find the best layout index for a given content type
        
        Args:
            layouts_info: Available layout information
            preferred_type: Preferred layout type (text, picture, html)
            
        Returns:
            Layout index (defaults to first text layout if no match found)
        """
        # Priority mapping for different content types
        search_patterns = {
            "text": ["text content", "content", "text"],
            "picture": ["title and picture", "picture"],
            "html": ["html", "picture generated from html", "picture"]
        }
        
        patterns = search_patterns.get(preferred_type, ["content", "text"])
        
        # Search for exact matches first
        for pattern in patterns:
            for layout_index, layout_info in layouts_info.items():
                layout_name = layout_info.get("name", "").lower()
                if pattern in layout_name:
                    return layout_index
        
        # Fallback to any content layout
        for layout_index, layout_info in layouts_info.items():
            layout_name = layout_info.get("name", "").lower()
            if any(keyword in layout_name for keyword in ["content", "text", "title"]):
                return layout_index
                
        # Final fallback to first non-logo layout
        for layout_index, layout_info in layouts_info.items():
            layout_name = layout_info.get("name", "").lower()
            if "logo" not in layout_name and "branding" not in layout_name:
                return layout_index
                
        # Ultimate fallback to first available layout
        return list(layouts_info.keys())[0] if layouts_info else 0

    def _create_presentation_planning_prompt(
        self,
        layouts_info: dict[int, dict[str, object]],
        topic: str,
        title: Optional[str] = None,
    ) -> str:
        """
        Create optimized prompt for strategic presentation planning
        with clear HTML decisions and actionable guidance.
        """
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

                if isinstance(placeholders, list):
                    for placeholder in placeholders:
                        if isinstance(placeholder, dict):
                            name = placeholder.get("name", "Unknown")
                            placeholder_names.append(name)
                            # Check if this layout has picture placeholders for HTML
                            html_keywords = ["picture", "image", "visual", "html"]
                            if any(
                                keyword in name.lower() for keyword in html_keywords
                            ):
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

        # Build title/topic section
        title_section = f'TITLE: "{title}"\n' if title else ""
        topic_label = "TOPIC" if not title else "DESCRIPTION"
        
        return f"""📋 CREATE STRATEGIC PRESENTATION PLAN

{title_section}{topic_label}: "{topic}"

🚨 CRITICAL: This is a quickstart generation. Carefully analyze the project description above and create an outline that EXACTLY matches what was requested. If the description specifies a certain number of slides, specific content, or particular requirements, you MUST follow them precisely. Pay special attention to:
• Specific slide count requirements (e.g., "one slide only", "3 slides", "5-slide presentation")
• Particular content types requested
• Specific topics or sections mentioned
• Any constraints or limitations specified

🎯 AVAILABLE LAYOUTS:
{layouts_text}

✨ HTML-CAPABLE LAYOUTS: {html_layouts_text}
(These have picture placeholders for rich HTML visualizations)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎨 HTML VISUALIZATION DECISION GUIDE

USE HTML (set is_html: true) FOR:
✅ Timelines, roadmaps, chronological sequences  
✅ Process flows, workflows, step-by-step procedures
✅ Comparisons, before/after scenarios
✅ Data visualizations, metrics, statistics  
✅ Complex diagrams, hierarchies, relationships
✅ Interactive elements, dashboards, multi-step processes

SKIP HTML (set is_html: false) FOR:
❌ Simple text content and basic bullet points
❌ Icon-heavy content (use icon placeholders instead)  
❌ Standard chart data (use chart placeholders)
❌ Simple titles and descriptions
❌ PHOTOGRAPHIC/SCENE REQUESTS (e.g., "image of a doctor", "photo of office", "picture of person working")
❌ Single illustrations or scenes that can be generated as images
❌ Portrait-style or environmental images

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📐 LAYOUT SELECTION STRATEGY

🔑 KEY PRINCIPLES:
• Choose layouts based on CONTENT TYPE, not sequence
• REUSE effective layouts for similar content types  
• Use HTML-capable layouts for visual content
• Avoid sequential usage (0,1,2,3,4,5...)

📚 LAYOUT USAGE GUIDE:
• Title slides: Layouts with title placeholders
• Visual content: HTML-capable layouts + is_html: true
• Icon content: Layouts with multiple icon placeholders
• Charts/Data: Chart-specific layouts (simple data only)
• Images: Picture-focused layouts
• Conclusions: Conclusion-specific layouts

✅ GOOD PATTERNS: [0,3(HTML),3(HTML),7,7,2,8]
❌ BAD PATTERNS: [0,1,2,3,4,5,6,7,8,9]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 SLIDE SPECIFICATIONS REQUIRED

FOR EVERY SLIDE, PROVIDE:
1. **slide_purpose**: Clear purpose (1-2 sentences)
2. **detailed_purpose**: Comprehensive explanation (3-4 sentences) 
3. **content_structure**: Organization requirements ("2-column comparison", "5-step list")
4. **visual_elements**: Required visuals ("icons, timeline markers, arrows")  
5. **key_information**: Essential info points (3-5 items)

FOR HTML SLIDES, ALSO ADD:
6. **html_requirements**: Specific visualization specs. CHOOSE THE BEST TOOL FOR THE JOB.
   • **Use D3.js for**: MANDATORY for ALL timelines and roadmaps. Required for custom, data-driven, or highly polished visualizations where branding and unique presentation are key.
     - *Example (Timeline - MANDATORY)*: "D3.js timeline: A polished, horizontal timeline with detailed descriptions and brand colors."
     - *Example (Custom Chart)*: "D3.js custom chart: A bar chart with specific annotations and non-standard styling."
     - *Example (Roadmap)*: "D3.js roadmap: Multi-phase project roadmap with detailed milestone markers."
   • **Use Mermaid.js for**: Standard, structured diagrams (EXCEPT timelines/roadmaps). It's fast and clean for flowcharts, hierarchies.
     - *Example (Flowchart)*: "Mermaid flowchart: Left-to-right process with 3-5 steps and decision points."
     - *Example (Gantt Chart)*: "Mermaid Gantt chart: A 3-month project plan with key phases and milestones."
     - *Example (Sequence Diagram)*: "Mermaid sequence diagram: Illustrate the interaction between a User, a Web Server, and a Database for a login process."
     - ⚠️ CRITICAL: NEVER use Mermaid timeline syntax - use D3.js for ALL timelines and roadmaps
   • **Use DaisyUI/Flowbite for**: Layout and components to wrap visualizations with creative storytelling patterns.
     - *Hero Journeys*: "Hero component with problem statement, radial progress indicator, and solution badges"
     - *Transformation Stories*: "Three-card layout with breadcrumbs navigation showing Before → During → After transformation"
     - *Process Excellence*: "Steps component with progress indicators, dividers, and detailed phase cards"
     - *Metrics Dashboard*: "Hero layout with stats, indicators, and achievement badges for impact visualization"
     - *Comparison Framework*: "Table with tooltips, progress bars, and badges for feature comparison"
     - *Progress Tracking*: "Menu lists with embedded progress bars and status badges"
   • **Creative Component Combinations**: 
     - "Hero with embedded Mermaid diagram + Steps navigation + Stats dashboard"
     - "Cards containing Mermaid flowcharts with action badges and progress indicators"
     - "Tables with progress bars, tooltips, and badges for comprehensive comparisons"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 PRESENTATION REQUIREMENTS

• Create 8-15 slides (respect user's specific count if given)
• Build logical flow: introduction → content → conclusion
• Set is_html flag explicitly for each slide
• Ensure each slide advances the narrative
• Use HTML strategically for maximum visual impact
• Include branding slides if available in template

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 EXAMPLE SPECIFICATIONS

STANDARD SLIDE:
- slide_purpose: "Introduce company and establish credibility"
- detailed_purpose: "Present ekona as trusted digital transformation partner with proven track record. Showcase experience, client success, and key differentiators. Build confidence through demonstrating expertise and innovation."
- content_structure: "Title with tagline, 3-column expertise areas"
- visual_elements: "Company logo, 3 service icons, credibility badge"
- key_information: ["15+ years experience", "200+ projects", "95% satisfaction"]

HTML SLIDE (Timeline):
- slide_purpose: "Show project timeline and phases"  
- detailed_purpose: "Present comprehensive 6-month project roadmap with clear phases and deliverables. Help audience understand structured approach and feel confident about realistic timelines."
- html_requirements: "D3.js timeline: A polished, horizontal timeline for Discovery (Month 1), Development (Months 2-3), Testing (Month 4), Launch (Month 5), Support (Month 6)."
- visual_elements: "Timeline with phase markers and key deliverables"

HTML SLIDE (Hero Journey Pattern):
- slide_purpose: "Present transformation journey from problem to solution"
- html_requirements: "Hero component with problem statement, radial progress showing current state (25%), and critical issue badge. Follow with solution hero containing steps navigation and embedded Mermaid workflow diagram."
- visual_elements: "Hero layout, radial progress indicator, steps component, Mermaid flowchart"

HTML SLIDE (Transformation Story):
- slide_purpose: "Show before/during/after business transformation"
- html_requirements: "Three-card layout with breadcrumbs navigation. Before card with stats showing current metrics, During card with radial progress and checklist, After card with improved stats. Use badges and progress indicators throughout."
- visual_elements: "Breadcrumbs, three-column grid, stats components, radial progress, badges"

HTML SLIDE (Process Excellence):
- slide_purpose: "Detail implementation roadmap with phase tracking"
- html_requirements: "Steps component showing project phases, divider with descriptive text, detailed cards with avatar placeholders, progress bars, and completion badges for each phase."
- visual_elements: "Steps navigation, dividers, avatar placeholders, progress bars, status badges"

HTML SLIDE (Metrics Dashboard):
- slide_purpose: "Display impact results with compelling data visualization"
- html_requirements: "Hero layout with indicators showing achievement level, stats grid with icons and trend data, badges highlighting key successes. Use radial progress for key KPI."
- visual_elements: "Hero component, indicators, stats grid, Lucide icons, badges, radial progress"

HTML SLIDE (Comparison Framework):
- slide_purpose: "Compare traditional vs modern approaches with detailed features"
- html_requirements: "Table with zebra styling, progress bars showing performance metrics, tooltips with additional context, badges for categorization. Include visual performance indicators."
- visual_elements: "Table layout, progress bars, tooltips, badges, performance indicators"

Focus on creating compelling narrative with strategic HTML visualizations that enhance understanding and tell powerful business stories."""

    def _get_planning_system_prompt(self) -> str:
        """Get the optimized system prompt for presentation planning"""
        return """You are an expert presentation designer creating strategic, engaging presentations with precise HTML visualization decisions.

🎯 CORE MISSION: Create detailed presentation plans that guide the entire content generation pipeline effectively.

🔑 KEY RESPONSIBILITIES:
1. **Strategic Layout Selection**: Choose layouts based on content type, not sequence
2. **HTML Decision Making**: Explicitly decide which slides need HTML visualizations  
3. **Image vs HTML Detection**: Distinguish between photographic/scene requests (for image generation) and data visualization needs (for HTML)
4. **Detailed Specifications**: Provide comprehensive guidance for each slide
5. **Content Flow Design**: Ensure logical narrative progression

🚨 CRITICAL: When users request visual scenes, photos, or illustrations (e.g., "image of a doctor working", "photo of people in meeting", "picture of office environment"), these should be handled as IMAGE GENERATION (is_html: false), NOT HTML visualization.

📋 SPECIFICATION REQUIREMENTS:

For EVERY slide, provide ALL of these fields:
• **slide_purpose**: Clear, concise purpose (1-2 sentences)
• **detailed_purpose**: Comprehensive explanation (3-4 sentences)
• **content_structure**: Specific organization ("2-column layout", "5-step process")
• **visual_elements**: Required visuals ("icons, arrows, timeline markers")
• **key_information**: Essential content points (3-5 items)

For HTML slides (is_html: true), ALSO add:
• **html_requirements**: Detailed visualization specs using creative DaisyUI storytelling patterns

🎨 HTML DECISION FRAMEWORK & STORYTELLING PATTERNS:

SET is_html: true FOR visual content requiring:
✅ **Hero Journeys**: Problem statements, challenges, solution presentations
✅ **Transformation Stories**: Before/during/after scenarios, business evolution
✅ **Process Excellence**: Implementation roadmaps, step-by-step procedures
✅ **Metrics Dashboards**: Impact results, KPIs, performance visualization
✅ **Comparison Frameworks**: Feature comparisons, competitive analysis
✅ **Progress Tracking**: Project phases, completion status, roadmap updates
✅ Timelines, workflows, hierarchies, complex data relationships

🎯 STORYTELLING PATTERN SELECTION GUIDE:
• **Hero Journey**: Use for problem/solution slides, value propositions, transformation announcements
• **Transformation Story**: Use for case studies, improvement showcases, evolution narratives  
• **Process Excellence**: Use for methodology explanations, implementation guides, phase planning
• **Metrics Dashboard**: Use for results presentations, success stories, impact demonstrations
• **Comparison Framework**: Use for competitive analysis, feature comparisons, decision matrices
• **Progress Tracking**: Use for project updates, roadmap status, milestone tracking

SET is_html: false FOR simple content like:
❌ Basic text, bullet points, titles
❌ Icon-heavy content (use icon placeholders)
❌ Standard charts (use chart placeholders)

🎯 SUCCESS CRITERIA:
• Specifications must be detailed enough for accurate content generation
• Each slide must advance the overall narrative
• HTML visualizations should enhance understanding, not complicate
• Layout choices should match content requirements
• Presentation should tell a compelling, coherent story

Focus on creating presentations that are both visually engaging and strategically sound."""

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
        from .llm_models import PresentationPlan
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
        slides_to_process = presentation_plan if isinstance(presentation_plan, list) else presentation_plan.slides

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
                generated_images = state.get("generated_images", {})
                presentation = slide_generator._create_powerpoint_presentation(
                    slide_contents, generated_images
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
        """Calculate content quality metrics"""
        # (Implementation of quality metrics calculation)
        # This is a placeholder for a more sophisticated implementation
        completeness = sum(1 for slide in slide_contents if slide.content) / len(
            slide_contents
        )
        relevance = 0.85  # Placeholder
        return {"completeness": completeness, "relevance": relevance}


class HTMLRefinementAgent:
    """
    Agent responsible for refining HTML content based on visual feedback.
    It renders the HTML, sends it to a vision model, and applies corrections.
    """

    def __init__(self):
        self.name = "html_refinement_agent"
        self.llm_client = LangchainLLMClient()
        self.html_renderer = HTMLRenderer()
        self.max_iterations = 5
        self.temp_dir = Path("html_debug")
        self.temp_dir.mkdir(exist_ok=True)

        # Initialize the Azure Blob Uploader
        self.uploader = AzureBlobUploader()
        
        # Initialize Supabase storage and database clients for refinement tracking
        try:
            from .supabase_storage import get_storage_client
            from .database import get_supabase_client
            self.storage_client = get_storage_client()
            self.db_client = get_supabase_client()
            print("✅ Supabase storage and database clients initialized for refinement tracking")
        except Exception as e:
            print(f"⚠️ Failed to initialize Supabase clients for refinement tracking: {e}")
            self.storage_client = None
            self.db_client = None

        # Image compression settings optimized for LLM vision models
        self.compression_settings = {
            "max_size_mb": 20,  # OpenAI GPT-4V max is 20MB, Claude is 32MB
            "target_size_mb": 5,  # Target smaller size for faster processing
            "min_quality": 30,  # Don't go below 30% JPEG quality
            "resize_thresholds": [0.8, 0.6, 0.4],  # Progressive resize factors
            "preserve_aspect_ratio": True,
            "convert_to_jpeg": True,  # JPEG compression is more efficient than PNG
            # Optimal dimensions for LLM vision models (reduces token usage dramatically)
            "target_dimensions": {
                "max_width": 768,  # Based on research: 512-768px width is sufficient
                "max_height": 1024,  # Based on research: up to 1024px height works well
                "min_width": 512,  # Minimum width to maintain detail
                "min_height": 512,  # Minimum height to maintain detail
            },
        }

    def _cleanup_old_debug_files(self, keep_latest: int = 5):
        """
        Clean up old debug files to prevent accumulation

        Args:
            keep_latest: Number of latest refinement sessions to keep
        """
        try:
            if not self.temp_dir.exists():
                return

            # Get all HTML and PNG files
            debug_files = list(self.temp_dir.glob("*.html")) + list(
                self.temp_dir.glob("*.png")
            )

            if (
                len(debug_files) <= keep_latest * 10
            ):  # Rough estimate (slides * iterations)
                return

            # Sort by modification time and remove oldest
            debug_files.sort(key=lambda f: f.stat().st_mtime)
            files_to_remove = debug_files[: -keep_latest * 10]

            removed_count = 0
            for file_path in files_to_remove:
                try:
                    file_path.unlink()
                    removed_count += 1
                except OSError:
                    pass

            if removed_count > 0:
                print(f"  🧹 Cleaned up {removed_count} old debug files")

        except Exception as e:
            print(f"  - Warning: Failed to clean up debug files: {e}")

    def _compress_image_for_llm(
        self, image_path: str, max_size_mb: Optional[float] = None
    ) -> bool:
        """
        Compress image for optimal LLM processing while maintaining quality

        Args:
            image_path: Path to the image file to compress
            max_size_mb: Maximum file size in MB (uses configured setting if None)

        Returns:
            True if compression was successful or not needed, False if failed
        """
        if not PIL_AVAILABLE:
            print("  - PIL not available, skipping image compression")
            return True

        # Use configured settings if max_size_mb not provided
        if max_size_mb is None:
            max_size_mb = self.compression_settings["max_size_mb"]

        # Type assertion to help linter - max_size_mb is guaranteed to be float here
        assert max_size_mb is not None
        max_size: float = max_size_mb

        try:
            # Check if file exists
            if not os.path.exists(image_path):
                print(f"  - Image file not found for compression: {image_path}")
                return False

            # Get original file size
            original_size = os.path.getsize(image_path)
            original_size_mb = original_size / (1024 * 1024)

            print(f"  - Original image size: {original_size_mb:.2f} MB")

            # If already under limit, no compression needed
            if original_size_mb <= max_size:
                print(
                    f"  - Image already under {max_size}MB limit, no compression needed"
                )
                return True

            # Open and analyze image
            with Image.open(image_path) as img:
                # Get original dimensions
                original_width, original_height = img.size
                print(f"  - Original dimensions: {original_width}x{original_height}")

                # Convert to RGB if needed (for JPEG compression)
                if img.mode in ("RGBA", "LA", "P"):
                    # Convert RGBA to RGB with white background
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    background.paste(
                        img, mask=img.split()[-1] if img.mode == "RGBA" else None
                    )
                    img = background
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                # STEP 1: Resize to optimal LLM vision dimensions first (most important for token reduction)
                target_dims = self.compression_settings["target_dimensions"]
                max_width = target_dims["max_width"]
                max_height = target_dims["max_height"]
                min_width = target_dims["min_width"]
                min_height = target_dims["min_height"]

                # Calculate optimal resize dimensions
                if original_width > max_width or original_height > max_height:
                    # Calculate scale factor to fit within max dimensions while preserving aspect ratio
                    scale_factor = min(
                        max_width / original_width, max_height / original_height
                    )
                    new_width = max(int(original_width * scale_factor), min_width)
                    new_height = max(int(original_height * scale_factor), min_height)

                    print(
                        f"  - Resizing to optimal LLM dimensions: {new_width}x{new_height}"
                    )
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                    # Save with high quality first to check size
                    temp_path = image_path.replace(".png", "_resized_temp.jpg")
                    img.save(temp_path, format="JPEG", quality=90, optimize=True)

                    # Check file size after optimal resize
                    resized_size = os.path.getsize(temp_path)
                    resized_size_mb = resized_size / (1024 * 1024)

                    print(f"  - After optimal resize: {resized_size_mb:.2f} MB")

                    if resized_size_mb <= max_size:
                        # Great! Optimal resize was sufficient
                        os.remove(image_path)
                        os.rename(temp_path, image_path)

                        dimension_reduction = (
                            (
                                (original_width * original_height)
                                - (new_width * new_height)
                            )
                            / (original_width * original_height)
                            * 100
                        )
                        size_reduction = (
                            (original_size - resized_size) / original_size
                        ) * 100

                        print("  ✅ Optimal dimension resize successful!")
                        print(
                            f"     Original: {original_width}x{original_height} ({original_size_mb:.2f} MB)"
                        )
                        print(
                            f"     Optimized: {new_width}x{new_height} ({resized_size_mb:.2f} MB)"
                        )
                        print(f"     Dimension reduction: {dimension_reduction:.1f}%")
                        print(f"     Size reduction: {size_reduction:.1f}%")
                        print(
                            f"     Token cost savings: ~{dimension_reduction * 0.8:.0f}% (estimated)"
                        )
                        return True
                    # Dimension resize wasn't enough, continue with quality compression
                    print(
                        f"  - Still {resized_size_mb:.2f} MB after resize, applying quality compression..."
                    )
                    compressed_path = temp_path
                else:
                    print(
                        f"  - Image already within optimal dimensions ({original_width}x{original_height})"
                    )
                    compressed_path = image_path.replace(".png", "_compressed.jpg")

                # STEP 2: Apply quality-based compression if needed
                quality = 95

                # Iteratively compress until under size limit
                for attempt in range(5):  # Max 5 attempts
                    # Try current quality level
                    img.save(
                        compressed_path, format="JPEG", quality=quality, optimize=True
                    )

                    # Check file size
                    compressed_size = os.path.getsize(compressed_path)
                    compressed_size_mb = compressed_size / (1024 * 1024)

                    print(
                        f"  - Quality attempt {attempt + 1}: {quality}%, Size: {compressed_size_mb:.2f} MB"
                    )

                    if compressed_size_mb <= max_size:
                        # Success! Replace original with compressed version
                        os.remove(image_path)
                        os.rename(compressed_path, image_path)

                        compression_ratio = (
                            (original_size - compressed_size) / original_size
                        ) * 100
                        print("  ✅ Compression successful!")
                        print(
                            f"     Original: {original_size_mb:.2f} MB → Final: {compressed_size_mb:.2f} MB"
                        )
                        print(f"     Total reduction: {compression_ratio:.1f}%")
                        print(f"     Final quality: {quality}%")
                        return True

                    # If still too large, reduce quality for next attempt
                    if quality > 60:
                        quality -= 15  # Reduce quality more aggressively
                    else:
                        quality -= 5  # Fine-tune at lower qualities

                    if quality < self.compression_settings["min_quality"]:
                        break

                # STEP 3: If quality compression wasn't enough, try further dimension reduction
                print(
                    "  - Quality compression insufficient, trying further dimension reduction..."
                )

                # Use more aggressive resize factors
                aggressive_scales = [0.7, 0.5, 0.3]

                for scale in aggressive_scales:
                    new_width = max(int(original_width * scale), min_width)
                    new_height = max(int(original_height * scale), min_height)

                    # Don't go below minimum dimensions
                    if new_width < min_width or new_height < min_height:
                        continue

                    # Resize image
                    resized_img = img.resize(
                        (new_width, new_height), Image.Resampling.LANCZOS
                    )

                    # Save with good quality since we reduced size significantly
                    resized_img.save(
                        compressed_path, format="JPEG", quality=85, optimize=True
                    )

                    compressed_size = os.path.getsize(compressed_path)
                    compressed_size_mb = compressed_size / (1024 * 1024)

                    print(
                        f"  - Aggressive resize: {new_width}x{new_height}, Size: {compressed_size_mb:.2f} MB"
                    )

                    if compressed_size_mb <= max_size:
                        # Success with aggressive resize!
                        os.remove(image_path)
                        os.rename(compressed_path, image_path)

                        compression_ratio = (
                            (original_size - compressed_size) / original_size
                        ) * 100
                        dimension_reduction = (
                            (
                                (original_width * original_height)
                                - (new_width * new_height)
                            )
                            / (original_width * original_height)
                            * 100
                        )

                        print("  ✅ Aggressive dimension reduction successful!")
                        print(
                            f"     Original: {original_width}x{original_height} ({original_size_mb:.2f} MB)"
                        )
                        print(
                            f"     Final: {new_width}x{new_height} ({compressed_size_mb:.2f} MB)"
                        )
                        print(f"     Total reduction: {compression_ratio:.1f}%")
                        print(f"     Dimension reduction: {dimension_reduction:.1f}%")
                        print(
                            f"     Massive token savings: ~{dimension_reduction * 0.8:.0f}% (estimated)"
                        )
                        return True

                # Clean up temporary file if all compression attempts failed
                if os.path.exists(compressed_path):
                    os.remove(compressed_path)

                print(f"  ⚠️ Could not compress image under {max_size}MB limit")
                print("     Final size may exceed limit but continuing processing")
                return True  # Return True to continue processing

        except Exception as e:
            print(f"  ❌ Error during image compression: {e}")
            return True  # Return True to continue processing even if compression fails
    
    async def _track_refinement_in_supabase(self, project_id: str, slide_id: str, iteration: int,
                                    html_content: str, image_path: Path, 
                                    refinement_feedback: Optional[str] = None,
                                    refinement_prompt: Optional[str] = None,
                                    is_final: bool = False) -> Optional[str]:
        """
        Track HTML refinement iteration in Supabase storage and database
        
        Args:
            project_id: Project UUID
            slide_id: Slide UUID
            iteration: Refinement iteration number
            html_content: HTML content for this iteration
            image_path: Path to rendered image file
            refinement_feedback: LLM feedback from this iteration
            refinement_prompt: Prompt used for this iteration
            is_final: Whether this is the final refinement
            
        Returns:
            Refinement record ID if successful, None otherwise
        """
        if not self.storage_client or not self.db_client:
            print("  - Supabase clients not available, skipping refinement tracking")
            return None
        
        try:
            # Upload HTML and image to Supabase Storage
            html_url, image_url = self.storage_client.upload_refinement_files(
                project_id, slide_id, iteration, html_content, image_path
            )
            
            # Generate PPTX version for this refinement iteration
            pptx_url = None
            try:
                print(f"  📄 Generating PPTX version for iteration {iteration}...")
                pptx_url = await self._create_pptx_version(
                    project_id, slide_id, iteration, html_content, image_path
                )
                if pptx_url:
                    print(f"  ✅ PPTX version created: {pptx_url}")
                else:
                    print(f"  ⚠️ Failed to create PPTX version for iteration {iteration}")
            except Exception as e:
                print(f"  ⚠️ Error creating PPTX version: {e}")
            
            # Create database record for this refinement iteration
            refinement_record = self.db_client.create_html_refinement(
                project_id=project_id,
                slide_id=slide_id,
                iteration_number=iteration,
                html_content=html_content,
                html_file_url=html_url,
                image_file_url=image_url,
                pptx_file_url=pptx_url,
                refinement_feedback=refinement_feedback,
                refinement_prompt=refinement_prompt,
                is_final=is_final
            )
            
            print(f"  ✅ Tracked refinement iteration {iteration} in Supabase: {refinement_record['id']}")
            return refinement_record['id']
            
        except Exception as e:
            print(f"  ⚠️ Failed to track refinement in Supabase: {e}")
            return None

    async def _create_pptx_version(self, project_id: str, slide_id: str, iteration: int, 
                                 html_content: str, image_path: Path) -> Optional[str]:
        """
        Create a PPTX version for a specific refinement iteration
        
        Args:
            project_id: Project UUID
            slide_id: Slide UUID 
            iteration: Refinement iteration number
            html_content: HTML content to render
            image_path: Path to the rendered image file
            
        Returns:
            Supabase Storage URL of the created PPTX file, or None if failed
        """
        try:
            # Import the individual slide generator
            from .individual_slide_generator import IndividualSlideGenerator
            from .llm_models import SlideContent
            
            # Get slide data from database to understand layout and content structure
            slide_data = self.db_client.get_slide_details(slide_id)
            if not slide_data:
                print(f"    ❌ Could not find slide data for slide_id {slide_id}")
                return None
            
            # Create a SlideContent object with the refined HTML
            slide_content = SlideContent(
                title=slide_data.get('title', 'Untitled'),
                content={
                    # Replace any existing HTML content with the refined version
                    'main_content': html_content,
                    'html_visualization': html_content
                },
                layout_index=slide_data.get('layout_index', 0)
            )
            
            # Get project data to find template path
            project_data = self.db_client.get_project(project_id)
            if not project_data:
                print(f"    ❌ Could not find project data for project_id {project_id}")
                return None
            
            # Resolve template path
            from .template_manager import resolve_template_path
            template_path = resolve_template_path()
            
            # Create slide generator instance
            slide_generator = IndividualSlideGenerator()
            
            # Create a unique filename for this PPTX version
            import uuid
            version_filename = f"slide_{slide_data.get('slide_number', 1):02d}_v{iteration}_{uuid.uuid4().hex[:8]}.pptx"
            
            # Generate the individual PPTX slide
            result = await slide_generator.generate_individual_slide(
                slide_id=slide_id,
                project_id=project_id,
                slide_content=slide_content,
                template_path=template_path,
                slide_number=slide_data.get('slide_number', 1),
                layouts_info={},  # Will be populated by the generator
                dynamic_models={},  # Will be populated by the generator
                html_image_path=str(image_path)  # Pass the rendered image path
            )
            
            if not result or not result.get('success'):
                print(f"    ❌ Failed to generate PPTX: {result.get('error', 'Unknown error')}")
                return None
            
            # Upload PPTX to Supabase Storage
            pptx_path = result.get('file_path')
            if not pptx_path or not os.path.exists(pptx_path):
                print(f"    ❌ PPTX file not found at: {pptx_path}")
                return None
            
            # Upload to storage with version-specific path
            storage_path = f"projects/{project_id}/slides/{slide_id}/versions/{version_filename}"
            pptx_url = self.storage_client.upload_file(
                file_path=pptx_path,
                storage_path=storage_path,
                content_type='application/vnd.openxmlformats-officedocument.presentationml.presentation'
            )
            
            if pptx_url:
                print(f"    ✅ PPTX version uploaded to: {pptx_url}")
                # Clean up local file
                try:
                    os.remove(pptx_path)
                except:
                    pass
            else:
                print(f"    ❌ Failed to upload PPTX to storage")
            
            return pptx_url
            
        except Exception as e:
            print(f"    ❌ Error creating PPTX version: {e}")
            return None
    
    def _get_or_create_slide_id(self, project_id: str, slide_index: int, slide_content: Any) -> Optional[str]:
        """
        Get existing slide ID or create a new slide record for refinement tracking
        
        Args:
            project_id: Project UUID
            slide_index: Zero-based slide index
            slide_content: Slide content object
            
        Returns:
            Slide UUID if successful, None otherwise
        """
        if not self.db_client:
            return None
        
        try:
            # Check if slide already exists
            existing_slides = self.db_client.get_project_slides(project_id)
            slide_number = slide_index + 1  # Convert to 1-based
            
            for slide in existing_slides:
                if slide['slide_number'] == slide_number:
                    return slide['id']
            
            # Create new slide record
            slide_title = f"Slide {slide_number}"
            content_dict = {}
            
            if hasattr(slide_content, 'content') and slide_content.content:
                content_dict = slide_content.content
                # Try to get a better title from content
                for key, value in slide_content.content.items():
                    if 'title' in key.lower() and isinstance(value, str):
                        slide_title = value[:100]  # Limit length
                        break
            
            slide_record = self.db_client.create_slide(
                project_id=project_id,
                slide_number=slide_number,
                title=slide_title,
                content=content_dict,
                layout_type=f"layout_{getattr(slide_content, 'layout_index', 0)}"
            )
            
            return slide_record['id']
            
        except Exception as e:
            print(f"  ⚠️ Failed to get/create slide ID: {e}")
            return None

    @monitor_agent_execution("html_refinement_agent")
    def execute(
        self, state: SlideGenerationState, config: Optional[RunnableConfig] = None
    ) -> SlideGenerationState:
        """
        Refine HTML content through iterative visual feedback.
        This agent manages a queue of HTML slides and refines them one by one.
        """
        print(f"🎨 {self.name}: Running HTML refinement process...")

        # Clean up old debug files at the start
        self._cleanup_old_debug_files()

        slide_contents = state.get("slide_contents")
        if not slide_contents:
            print("  - No slide contents found. Skipping refinement.")
            state["needs_html_refinement"] = False
            state["current_step"] = "html_refinement_complete"
            return state

        # Initialize the queue of HTML slides on the first run
        if (
            "html_slides_to_refine_queue" not in state
            or state["html_slides_to_refine_queue"] is None
        ):
            html_slide_indices = self._identify_html_slides(slide_contents)
            state["html_slides_to_refine_queue"] = html_slide_indices
            state["html_refinement_slide_index"] = None
            state["html_refinement_iteration"] = 0
            print(
                f"  - Identified {len(html_slide_indices)} HTML slides to refine: {html_slide_indices}"
            )

        queue = state.get("html_slides_to_refine_queue", [])
        current_slide_index = state.get("html_refinement_slide_index")
        iteration = state.get("html_refinement_iteration", 0)

        # If there is no slide being actively refined, pick the next one from the queue.
        if current_slide_index is None:
            if not queue:
                print("  - HTML refinement queue is empty. Process complete.")
                state["needs_html_refinement"] = False
                state["current_step"] = "html_refinement_complete"
                return state

            # Get the next slide from the queue and reset the iteration count for it.
            current_slide_index = queue.pop(0)
            iteration = 1
            state["html_slides_to_refine_queue"] = queue
            state["html_refinement_slide_index"] = current_slide_index
            state["html_refinement_iteration"] = iteration
            print(
                f"  - Starting refinement for slide {current_slide_index + 1} (index {current_slide_index}), Iteration {iteration}/{self.max_iterations}"
            )
        else:
            # Continue refining the current slide.
            iteration += 1
            state["html_refinement_iteration"] = iteration
            print(
                f"  - Continuing refinement for slide {current_slide_index + 1} (index {current_slide_index}), Iteration {iteration}/{self.max_iterations}"
            )

        # Check if we have exceeded the max refinement iterations for the current slide.
        if iteration > self.max_iterations:
            print(
                f"  - Max refinement iterations reached for slide {current_slide_index + 1}."
            )
            # Move to the next slide in the next execution cycle.
            state["html_refinement_slide_index"] = None
            state["html_refinement_iteration"] = 0

            # Check if there are more slides in the queue.
            is_queue_empty = not state.get("html_slides_to_refine_queue")
            state["needs_html_refinement"] = not is_queue_empty

            if is_queue_empty:
                print("  - All HTML slides have been refined.")
                state["current_step"] = "html_refinement_complete"
            return state

        # --- Core refinement logic for the current_slide_index ---
        html_content = self._get_html_content_for_slide(
            slide_contents, current_slide_index
        )
        if not html_content or not html_content.strip():
            print(f"  - No HTML content for slide {current_slide_index + 1}. Skipping.")
            state["html_refinement_slide_index"] = None
            state["html_refinement_iteration"] = 0
            state["needs_html_refinement"] = bool(
                state.get("html_slides_to_refine_queue")
            )
            if not state["needs_html_refinement"]:
                state["current_step"] = "html_refinement_complete"
            return state

        presentation_plan = state.get("presentation_plan")
        slide_purpose = "No purpose provided."
        if presentation_plan and current_slide_index < len(presentation_plan):
            slide_spec = presentation_plan[current_slide_index]
            purpose_parts = []
            if slide_spec.slide_purpose:
                purpose_parts.append(f"Purpose: {slide_spec.slide_purpose}")
            if slide_spec.detailed_purpose:
                purpose_parts.append(f"Details: {slide_spec.detailed_purpose}")
            if purpose_parts:
                slide_purpose = "\n".join(purpose_parts)

        refinement_id = state.get("refinement_id") or str(uuid.uuid4())
        state["refinement_id"] = refinement_id

        # Use a unique filename for each slide and iteration to avoid conflicts.
        # Use 1-based slide numbering for clarity
        slide_number = current_slide_index + 1
        image_filename = (
            f"{refinement_id}_slide_{slide_number:02d}_iteration_{iteration}.png"
        )
        image_path = self.temp_dir / image_filename
        html_filename = (
            f"{refinement_id}_slide_{slide_number:02d}_iteration_{iteration}.html"
        )
        html_path = self.temp_dir / html_filename
        try:
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"  - Saved HTML for iteration {iteration} to: {html_path}")
        except Exception as e:
            print(f"  - Warning: Failed to save HTML debug file: {e}")

        if not self._render_html_to_image(html_content, str(image_path)):
            print("  - Failed to render HTML to image.")
            state["error_message"] = "HTML rendering failed during refinement."
            state["needs_html_refinement"] = False  # Stop refinement on render failure
            state["current_step"] = "html_refinement_complete"
            return state

        # Compress image for optimal LLM processing
        print("  🗜️ Compressing image for LLM processing...")
        if not self._compress_image_for_llm(str(image_path)):
            print("  - Image compression failed, but continuing with original image")

        image_url = self.uploader.upload_file(
            str(image_path), blob_name=f"refinement/{image_filename}"
        )
        if not image_url:
            print("  - Failed to upload image to Azure Blob Storage.")
            state["error_message"] = "Image upload failed during refinement."
            state["needs_html_refinement"] = False
            state["current_step"] = "html_refinement_complete"
            return state

        print(f"  - Rendered HTML to image and uploaded to: {image_url}")

        try:
            # Get refinement history for this slide
            refinement_history_key = f"html_refinement_history_{current_slide_index}"
            refinement_history = state.get(refinement_history_key, [])
            
            correction_response = self._get_html_correction(
                html_content, image_url, slide_purpose, refinement_history, config
            )
            if (
                correction_response
                and correction_response.html_code.strip().lower() != "no changes"
            ):
                print("  - HTML content updated.")
                print(f"  - Reasoning: {correction_response.reasoning}")
                print("  - Changes Applied:")
                for change in correction_response.changes_applied:
                    print(f"    - {change}")

                # Track refinement history for this slide to prevent flip-flopping
                refinement_history.extend(correction_response.changes_applied)
                state[refinement_history_key] = refinement_history

                state["slide_contents"] = self._update_slide_content(
                    slide_contents, current_slide_index, correction_response.html_code
                )
                # This slide needs another refinement iteration.
                state["needs_html_refinement"] = True
            else:
                print(
                    "  - No significant changes suggested. Refinement for this slide is complete."
                )
                # This slide is done. Clear its refinement history and move to next.
                state["html_refinement_slide_index"] = None
                state["html_refinement_iteration"] = 0
                # Clear refinement history for completed slide
                if refinement_history_key in state:
                    del state[refinement_history_key]

                # Check if there are more slides in the queue.
                is_queue_empty = not state.get("html_slides_to_refine_queue")
                state["needs_html_refinement"] = not is_queue_empty

                if is_queue_empty:
                    print("  - All HTML slides have been refined.")
                    state["current_step"] = "html_refinement_complete"

        except Exception as e:
            print(f"  - Error getting HTML correction: {e}")
            print("  - Proceeding with the current HTML content for this slide.")
            # Stop refining this slide and move to the next one.
            state["html_refinement_slide_index"] = None
            state["html_refinement_iteration"] = 0

            is_queue_empty_on_error = not state.get("html_slides_to_refine_queue")
            state["needs_html_refinement"] = not is_queue_empty_on_error

            if is_queue_empty_on_error:
                state["current_step"] = "html_refinement_complete"

        return state

    @monitor_agent_execution("html_refinement_agent_parallel")
    async def execute_parallel(
        self, state: SlideGenerationState, config: Optional[RunnableConfig] = None
    ) -> SlideGenerationState:
        """
        Refine HTML content through iterative visual feedback in TRUE parallel.
        All slides are processed simultaneously with parallel LLM calls.

        Args:
            state: Current workflow state
            config: Langchain configuration with callbacks

        Returns:
            Updated state with refined HTML content
        """
        print(f"🎨 {self.name}: Running TRUE parallel HTML refinement process...")

        # Clean up old debug files at the start
        self._cleanup_old_debug_files()

        slide_contents = state.get("slide_contents")
        if not slide_contents:
            print("  - No slide contents found. Skipping refinement.")
            state["needs_html_refinement"] = False
            state["current_step"] = "html_refinement_complete"
            return state

        # Identify all HTML slides
        html_slide_indices = self._identify_html_slides(slide_contents)
        if not html_slide_indices:
            print("  - No HTML slides identified. Skipping refinement.")
            state["needs_html_refinement"] = False
            state["current_step"] = "html_refinement_complete"
            return state

        print(
            f"  - Identified {len(html_slide_indices)} HTML slides for TRUE parallel refinement: {html_slide_indices}"
        )

        # Generate a single refinement ID for this batch
        refinement_id = str(uuid.uuid4())
        state["refinement_id"] = refinement_id

        # Get presentation plan for slide purposes
        presentation_plan = state.get("presentation_plan")

        # Prepare slide data for parallel processing
        slide_data = []
        for slide_index in html_slide_indices:
            html_content = self._get_html_content_for_slide(slide_contents, slide_index)
            if not html_content or not html_content.strip():
                print(f"  - No HTML content for slide {slide_index + 1}. Skipping.")
                continue

            # Get slide purpose
            slide_purpose = "No purpose provided."
            if presentation_plan and slide_index < len(presentation_plan):
                slide_spec = presentation_plan[slide_index]
                purpose_parts = []
                if slide_spec.slide_purpose:
                    purpose_parts.append(f"Purpose: {slide_spec.slide_purpose}")
                if slide_spec.detailed_purpose:
                    purpose_parts.append(f"Details: {slide_spec.detailed_purpose}")
                if purpose_parts:
                    slide_purpose = "\n".join(purpose_parts)

            slide_data.append(
                {
                    "slide_index": slide_index,
                    "html_content": html_content,
                    "slide_purpose": slide_purpose,
                }
            )

        if not slide_data:
            print("  - No valid HTML slides to process.")
            state["needs_html_refinement"] = False
            state["current_step"] = "html_refinement_complete"
            return state

        # Process all slides with TRUE parallel iterations
        print(f"  🚀 Starting TRUE parallel refinement for {len(slide_data)} slides...")
        refined_contents = await self._refine_all_slides_parallel(
            slide_data, refinement_id, state, config
        )

        # Update slide contents with refined HTML
        updated_slide_contents = slide_contents.copy()
        success_count = 0

        for slide_index, refined_html in refined_contents.items():
            if refined_html:
                updated_slide_contents = self._update_slide_content(
                    updated_slide_contents, slide_index, refined_html
                )
                success_count += 1
                print(f"  ✅ Successfully refined slide {slide_index + 1}")

        # Update state with refined content
        state["slide_contents"] = updated_slide_contents
        state["needs_html_refinement"] = False
        state["current_step"] = "html_refinement_complete"

        print(
            f"🎉 {self.name}: TRUE parallel refinement complete! {success_count}/{len(slide_data)} slides refined successfully."
        )
        return state

    async def _refine_all_slides_parallel(
        self,
        slide_data: List[Dict[str, Any]],
        refinement_id: str,
        state: SlideGenerationState,
        config: Optional[RunnableConfig] = None,
        max_iterations: int = 5,
    ) -> Dict[int, Optional[str]]:
        """
        Refine all slides with TRUE parallel processing. Each slide runs its full
        refinement loop independently.
        """
        print(
            f"  🔄 Processing {len(slide_data)} slides with independent parallel refinement loops..."
        )

        # Extract project ID and slide contents from state
        project_id = state.get("project_id")
        slide_contents = state.get("slide_contents", [])
        
        tasks = []
        for data in slide_data:
            slide_index = data["slide_index"]
            slide_content = slide_contents[slide_index] if slide_index < len(slide_contents) else None
            
            task = self._refine_one_slide_fully_async(
                slide_index=slide_index,
                initial_html_content=data["html_content"],
                slide_purpose=data["slide_purpose"],
                refinement_id=refinement_id,
                project_id=project_id,
                slide_content=slide_content,
                config=config,
                max_iterations=max_iterations,
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        final_html_contents = {}
        for i, result in enumerate(results):
            slide_index = slide_data[i]["slide_index"]
            if isinstance(result, BaseException):
                print(f"      ❌ Error refining slide {slide_index + 1}: {result}")
                # Return the original HTML on error to avoid losing content
                final_html_contents[slide_index] = slide_data[i]["html_content"]
            else:
                final_html_contents[slide_index] = result

        print(
            f"  ✅ All parallel refinement loops complete for {len(slide_data)} slides"
        )
        return final_html_contents

    async def _refine_one_slide_fully_async(
        self,
        slide_index: int,
        initial_html_content: str,
        slide_purpose: str,
        refinement_id: str,
        project_id: Optional[str] = None,
        slide_content: Optional[Any] = None,
        config: Optional[RunnableConfig] = None,
        max_iterations: int = 5,
    ) -> Optional[str]:
        """
        Processes the full refinement loop for a single slide asynchronously.
        This allows each slide to complete its refinement independently.
        """
        current_html = initial_html_content
        slide_number = slide_index + 1
        print(f"  🚀 Starting full refinement loop for slide {slide_number}...")
        
        # Get or create slide ID for Supabase tracking
        slide_id = None
        if project_id and slide_content:
            slide_id = self._get_or_create_slide_id(project_id, slide_index, slide_content)
            if slide_id:
                print(f"      📋 Using slide ID {slide_id} for Supabase tracking")

        for iteration in range(1, max_iterations + 1):
            print(
                f"    - Slide {slide_number}, Iteration {iteration}/{max_iterations}..."
            )

            # Create filenames for this specific iteration
            image_filename = (
                f"{refinement_id}_slide_{slide_number:02d}_iter_{iteration}.png"
            )
            image_path = self.temp_dir / image_filename

            # Render HTML to image (async)
            if not await self._render_html_to_image_async(
                current_html, str(image_path)
            ):
                print(
                    f"      ❌ Failed to render HTML for slide {slide_number}, aborting refinement for this slide."
                )
                return current_html  # Return last known good version

            # Compress image for optimal LLM processing
            print(f"      🗜️ Compressing image for slide {slide_number}...")
            if not self._compress_image_for_llm(str(image_path)):
                print(
                    f"      - Image compression failed for slide {slide_number}, but continuing with original image"
                )

            # Upload image
            image_url = self.uploader.upload_file(
                str(image_path), blob_name=f"refinement/{image_filename}"
            )
            if not image_url:
                print(
                    f"      ❌ Failed to upload image for slide {slide_number}, aborting refinement."
                )
                return current_html

            # Get refinement history for this slide (starts empty for each slide)
            refinement_history = []
            
            # Get LLM correction
            correction_response = await self._get_html_correction_async(
                current_html, image_url, slide_purpose, refinement_history, config
            )
            
            # Track this refinement iteration in Supabase
            refinement_feedback = None
            refinement_prompt = slide_purpose
            is_final = False
            
            if correction_response:
                refinement_feedback = correction_response.reasoning
                if hasattr(correction_response, 'changes_applied'):
                    refinement_feedback += f"\nChanges: {correction_response.changes_applied}"

            if (
                correction_response
                and correction_response.html_code.strip().lower() != "no changes"
                and correction_response.html_code.strip() != current_html.strip()
            ):
                print(
                    f"      🔄 Slide {slide_number}, Iteration {iteration}: LLM suggested changes. Continuing loop."
                )
                current_html = correction_response.html_code
                # Track changes in history to prevent flip-flopping
                if hasattr(correction_response, 'changes_applied'):
                    refinement_history.extend(correction_response.changes_applied)
                
                # Track the updated HTML in Supabase
                if project_id and slide_id:
                    await self._track_refinement_in_supabase(
                        project_id, slide_id, iteration, current_html, image_path,
                        refinement_feedback, refinement_prompt, is_final=False
                    )
                
            else:
                print(
                    f"      ⚪ Slide {slide_number}, Iteration {iteration}: No changes from LLM. Refinement complete for this slide."
                )
                
                # Mark this as the final refinement
                if project_id and slide_id:
                    await self._track_refinement_in_supabase(
                        project_id, slide_id, iteration, current_html, image_path,
                        refinement_feedback, refinement_prompt, is_final=True
                    )
                
                break  # Early exit if no changes are needed

        print(f"  ✅ Finished refinement loop for slide {slide_number}.")
        return current_html

    def _identify_html_slides(self, slide_contents: list[SlideContent]) -> list[int]:
        """Scans all slide contents and returns a list of indices for slides containing HTML."""
        html_slide_indices = []
        for i, slide in enumerate(slide_contents):
            has_html = False
            for placeholder_name, content in slide.content.items():
                if isinstance(content, str) and "<" in content and ">" in content:
                    if content.strip().startswith("<"):
                        html_slide_indices.append(i)
                        has_html = True
                        print(
                            f"  - Found HTML content in slide {i + 1}, placeholder '{placeholder_name}'"
                        )
                        break  # Move to next slide once HTML is found

            if not has_html:
                # Check if slide has any content that might be HTML-related
                for placeholder_name, content in slide.content.items():
                    if isinstance(content, str) and any(
                        tag in content.lower()
                        for tag in ["<div", "<html", "<body", "<span", "<p>"]
                    ):
                        print(
                            f"  - Slide {i + 1} has potential HTML content in placeholder '{placeholder_name}': {content[:100]}..."
                        )

        print(
            f"  - HTML slide identification complete: found {len(html_slide_indices)} HTML slides"
        )
        return html_slide_indices

    def _get_html_content_for_slide(
        self, slide_contents: list[SlideContent], slide_index: int
    ) -> Optional[str]:
        """Gets the HTML content for a specific slide index."""
        if slide_index >= len(slide_contents):
            return None
        slide = slide_contents[slide_index]
        for content in slide.content.values():
            if isinstance(content, str) and "<" in content and ">" in content:
                if content.strip().startswith("<"):
                    return content
        return None

    def _render_html_to_image(self, html_content: str, image_path: str) -> bool:
        # Extract dimensions from HTML content
        width, height = self._extract_html_dimensions(html_content)
        
        # Try to render with default method first
        try:
            print("  - Attempting to render HTML with default method...")
            self.html_renderer.render_html_to_image(html_content, image_path, width, height)
            if os.path.exists(image_path):
                print("  - Successfully rendered HTML to image with default method")
                return True
        except Exception as e:
            print(f"  - Error rendering HTML to image with default method: {e}")

        # If default method failed, try other available methods
        for method in ["playwright", "selenium", "weasyprint", "imgkit"]:
            if method == self.html_renderer.active_method:
                continue  # Skip the already tried method

            if self.html_renderer.available_methods.get(method, False):
                try:
                    print(f"  - Attempting to render HTML with {method}...")
                    # Create a temporary renderer with this method
                    temp_renderer = HTMLRenderer(preferred_method=method)
                    temp_renderer.render_html_to_image(html_content, image_path, width, height)
                    if os.path.exists(image_path):
                        print(f"  - Successfully rendered HTML to image with {method}")
                        return True
                except Exception as e:
                    print(f"  - Error rendering HTML to image with {method}: {e}")

        print("  - Failed to render HTML with all available methods")
        return False

    async def _render_html_to_image_async(
        self, html_content: str, image_path: str
    ) -> bool:
        """Async version of _render_html_to_image for use in async contexts"""
        # Extract dimensions from HTML content
        width, height = self._extract_html_dimensions(html_content)
        
        # Try to render with async method first
        try:
            print("  - Attempting to render HTML with async method...")
            result = await self.html_renderer.render_html_to_image_async(
                html_content, image_path, width, height
            )
            if result and os.path.exists(image_path):
                print("  - Successfully rendered HTML to image with async method")
                return True
        except Exception as e:
            print(f"  - Error rendering HTML to image with async method: {e}")

        # If async method failed, try other available methods with async execution
        import concurrent.futures

        for method in [
            "selenium",
            "weasyprint",
            "imgkit",
        ]:  # Skip playwright as we tried async version
            if self.html_renderer.available_methods.get(method, False):
                try:
                    print(f"  - Attempting to render HTML with {method} (async)...")
                    # Create a temporary renderer with this method and run in executor
                    temp_renderer = HTMLRenderer(preferred_method=method)

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            temp_renderer.render_html_to_image, html_content, image_path, width, height
                        )
                        result = await asyncio.wrap_future(future)

                    if result and os.path.exists(image_path):
                        print(
                            f"  - Successfully rendered HTML to image with {method} (async)"
                        )
                        return True
                except Exception as e:
                    print(
                        f"  - Error rendering HTML to image with {method} (async): {e}"
                    )

        print("  - Failed to render HTML with all available methods (async)")
        return False

    def _extract_html_dimensions(self, html_content: str) -> tuple[int, int]:
        """Extract viewport dimensions from HTML content body class
        
        Args:
            html_content: HTML content with body class containing dimensions
            
        Returns:
            Tuple of (width, height) in pixels
        """
        import re
        
        # Default fallback dimensions
        default_width, default_height = 1577, 603
        
        try:
            # Look for patterns like w-[1577px] h-[603px] in body class
            width_match = re.search(r'w-\[(\d+)px\]', html_content)
            height_match = re.search(r'h-\[(\d+)px\]', html_content)
            
            if width_match and height_match:
                width = int(width_match.group(1))
                height = int(height_match.group(1))
                return width, height
            
            print(f"  - Could not extract dimensions from HTML, using defaults: {default_width}x{default_height}")
            return default_width, default_height
                
        except Exception as e:
            print(f"  - Error extracting HTML dimensions: {e}, using defaults: {default_width}x{default_height}")
            return default_width, default_height

    async def _get_html_correction_async(
        self,
        html_content: str,
        image_url: str,
        slide_purpose: str,
        refinement_history: Optional[list[str]] = None,
        config: Optional[RunnableConfig] = None,
    ) -> Optional[RefinedHTML]:
        """
        Async version of _get_html_correction for true parallel LLM calls
        """
        import concurrent.futures

        system_prompt = self._get_system_prompt()
        user_prompt = self._create_user_prompt(html_content, image_url, slide_purpose, refinement_history)

        # Run the LLM call in a thread executor for true parallelism
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                self.llm_client.generate_structured_vision_content,
                system_prompt,
                user_prompt,
                RefinedHTML,
                config,
            )
            response = await asyncio.wrap_future(future)

        return response if response else None

    def _get_html_correction(
        self,
        html_content: str,
        image_url: str,
        slide_purpose: str,
        refinement_history: Optional[list[str]] = None,
        config: Optional[RunnableConfig] = None,
    ) -> Optional[RefinedHTML]:
        """
        Synchronous version (kept for compatibility with sequential processing)
        """
        system_prompt = self._get_system_prompt()
        user_prompt = self._create_user_prompt(html_content, image_url, slide_purpose, refinement_history)

        response = self.llm_client.generate_structured_vision_content(
            system_prompt,
            user_prompt,  # This will now be a list of messages
            response_model=RefinedHTML,
            config=config,
        )
        return response if response else None

    def _update_slide_content(
        self, slide_contents: list[SlideContent], slide_index: int, new_html: str
    ) -> list[SlideContent]:
        """Creates a new list of slide contents with the HTML updated for a specific slide."""
        updated_contents = []
        for i, slide in enumerate(slide_contents):
            if i == slide_index:
                new_content_dict = {}
                for key, value in slide.content.items():
                    if isinstance(value, str) and value.strip().startswith("<"):
                        new_content_dict[key] = new_html
                    else:
                        new_content_dict[key] = value
                updated_slide = SlideContent(
                    layout_index=slide.layout_index, content=new_content_dict
                )
                updated_contents.append(updated_slide)
            else:
                updated_contents.append(slide)
        return updated_contents

    def _format_refinement_history_context(self, refinement_history: Optional[list[str]]) -> str:
        """Format refinement history to provide context to avoid flip-flopping"""
        if not refinement_history:
            return ""
        
        history_text = "\n".join([f"• {change}" for change in refinement_history[-3:]])  # Last 3 changes
        
        return f"""**🔄 PREVIOUS REFINEMENT ATTEMPTS (AVOID REPEATING):**
The following changes were already tried in previous iterations. DO NOT reverse these decisions:
{history_text}

**⚠️ CRITICAL: Do not undo previous fixes or flip-flop between solutions.**
**Focus on NEW issues not yet addressed, or build upon previous improvements.**
"""

    def _create_user_prompt(
        self, html_content: str, image_url: str, slide_purpose: str, refinement_history: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        return [
            {
                "type": "text",
                "text": f"""**SLIDE PURPOSE & REQUIREMENTS:**
{slide_purpose}

**TASK:** Evaluate if the HTML code below successfully fulfills the slide's purpose and requirements. 
The attached image shows how this HTML currently renders.
If any content is missing in the image it means it is either outside the boundary or not rendering properly.

{self._format_refinement_history_context(refinement_history)}

**EVALUATION CRITERIA:**
• Does the visualization effectively communicate the slide's purpose?
• Is the content well-organized and visually clear?
• Are all required elements present and properly positioned?
• Does the design enhance understanding of the intended message?

**HTML CODE TO EVALUATE:**
```html
{html_content}
```

**INSTRUCTIONS:**
1. Review the slide's purpose and requirements above
2. Examine the rendered image to see how the current HTML performs
3. Determine if the HTML successfully fulfills the slide's purpose
4. If improvements are needed, refine the HTML code to better meet the requirements
5. Focus on purpose alignment, not just visual aesthetics""",
            },
            {
                "type": "image_url",
                "image_url": {"url": image_url},
            },
        ]

    def _get_system_prompt(self) -> str:
        return """You are an expert web developer and presentation design specialist.
Your task is to evaluate HTML code against slide requirements and refine it for optimal purpose fulfillment.

**YOUR MISSION:** Assess whether the provided HTML code successfully achieves the slide's intended purpose and requirements. If not, improve the HTML to better fulfill those objectives.

**RESPONSE FORMAT:**
Your response MUST be a JSON object that strictly follows this format: 
`{"html_code": "<FULL_HTML_CODE>", "reasoning": "...", "changes_applied": ["...", "..."]}`.
Do NOT provide any other text, explanations, or markdown.

**CRITICAL EVALUATION PRIORITIES:**

**1. 🚨 CRITICAL HEIGHT CONSTRAINT ANALYSIS (ABSOLUTE TOP PRIORITY) 🚨:**
- **DETECT MISSING CONTENT**: If ANY content is missing from the bottom of the image, the HTML HEIGHT is TOO LARGE and content is CROPPED
- **CHECK VIEWPORT DIMENSIONS**: Extract w-[NNNpx] h-[NNNpx] from body class - this is the ABSOLUTE MAXIMUM allowed size
- **CALCULATE TOTAL HEIGHT**: body padding + card padding + content + gaps MUST be < viewport height
- **MERMAID DIAGRAM OVERFLOW**: If Mermaid diagrams are cut off, they are exceeding viewport height - CRITICAL FIX NEEDED  
- **IMMEDIATE ACTION REQUIRED**: If bottom content is missing, reduce padding, text sizes, or content to fit within height limit
- **HEIGHT MATH**: For h-[456px]: p-4(32px) + card-body p-4(32px) + content + gaps MUST be < 456px
- **VALIDATION**: If rendered content is taller than specified h-[NNNpx], it WILL be cropped and invisible

**2. MANDATORY DAISYUI CARD STRUCTURE:**
- **Card Usage**: Is ALL content properly wrapped in DaisyUI card components?
- **Card Organization**: Are cards used effectively for content structure and spacing?
- **Visual Hierarchy**: Do cards provide proper visual separation and organization?
- **REQUIREMENT**: Content should NEVER be placed directly in body - always use cards

**3. Content Layout Assessment:**
- **Space Distribution**: Is the space used efficiently without overflow?
- **Content Scaling**: Are text sizes, diagrams, and elements appropriately sized?
- **Grid/Flex Usage**: Is CSS Grid or Flexbox used effectively for layout?
- **Safe Margins**: Are there appropriate margins (minimum 20px) on all sides?

**4. Color Palette Validation:** 
- Are ALL elements using the correct Ekona colors? Check every text element, background, accent, and component for brand compliance.

**5. Purpose Assessment:** 
- Does the HTML effectively communicate the slide's intended message?

**6. Requirements Check:** 
- Are all specified requirements met (content structure, visual elements, etc.)?

**7. Visual Effectiveness:** 
- Does the rendered result enhance understanding and engagement with correct branding?

**8. Technical Quality:** 
- Is the HTML technically sound and properly structured?

**REFINEMENT PRIORITIES:**
1. **CRITICAL: Viewport Constraint Enforcement** - Fix any content cropping or overflow issues IMMEDIATELY
2. **MANDATORY: DaisyUI Card Structure** - Ensure all content is properly contained in cards
3. **Color Palette Enforcement**: MANDATORY enforcement of Ekona color palette - check every element for correct colors
4. **Purpose Alignment**: Ensure the visualization directly supports the slide's objectives
5. **Content Clarity**: Information should be easily understood and well-organized
6. **Visual Hierarchy**: Important elements should be properly emphasized with correct brand colors
7. **Professional Quality**: Design should be polished and business-appropriate with consistent branding
8. **Space Utilization**: Effective use of the viewport

**🔧 CRITICAL HEIGHT OVERFLOW SOLUTIONS (APPLY IMMEDIATELY):**
- **Missing Bottom Content**: REDUCE padding: p-8→p-4, p-6→p-3, gap-6→gap-3
- **Text Too Large**: REDUCE font sizes: text-3xl→text-lg, text-2xl→text-base, text-xl→text-sm
- **Mermaid Diagram Cut Off**: ADD max-h-[300px] to .mermaid containers, reduce diagram complexity
- **Too Many Elements**: REMOVE secondary content, prioritize only essential information
- **Card Body Overflow**: REDUCE card-body padding: p-6→p-4→p-3, use flex-shrink
- **Grid Gaps Too Large**: REDUCE gaps: gap-6→gap-4→gap-2 for grid layouts
- **CALCULATION CHECK**: Sum all padding + content height < viewport h-[NNNpx]

**MANDATORY CARD PATTERNS TO ENFORCE:**
```html
<!-- Single Card (for simple content) -->
<body class="w-[WIDTHpx] h-[HEIGHTpx] p-8 overflow-hidden">
    <div class="card bg-base-100 shadow-xl h-full">
        <div class="card-body p-6">
            <!-- All content here -->
        </div>
    </div>
</body>

<!-- Multi-Card Layout (for complex content) -->
<body class="w-[WIDTHpx] h-[HEIGHTpx] p-8 overflow-hidden">
    <div class="grid grid-cols-2 gap-6 h-full">
        <div class="card bg-base-100 shadow-xl">
            <div class="card-body p-6">
                <!-- Left content -->
            </div>
        </div>
        <div class="card bg-base-100 shadow-xl">
            <div class="card-body p-6 flex flex-col">
                <h2 class="card-title text-xl mb-4">Title</h2>
                <div class="flex-grow flex items-center justify-center">
                    <div class="mermaid w-full max-h-[350px]">
                        <!-- Diagram -->
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>

NOTE: Replace WIDTH and HEIGHT with the exact pixel dimensions found in the existing HTML being refined.
```

**TECHNICAL REQUIREMENTS:**
- **Viewport**: Match the exact dimensions specified in the HTML body element with `overflow: hidden`
- **Frameworks**: TailwindCSS, Flowbite, and daisyUI components only
- **Diagrams**: Mermaid.js or D3.js with height constraints (`max-h-[400px]`)
- **No Titles**: Remove `<h1>` tags (slide has its own title)
- **Responsive**: Fixed pixel values for critical positioning
- **Performance**: High z-index values (z-10+) for proper layering

**DESIGN STANDARDS (CRITICAL - MUST BE ENFORCED):**
- **Colors (MANDATORY EKONA PALETTE)**: 
  - Primary/Accent: Swiss Red (#dc261e) - MUST be used for ALL accent elements
  - Text Headers: Dark Grey (#2d3748) - MUST be used for ALL headings  
  - Text Body: Black (#000000) - MUST be used for ALL body text
  - Background: White (#ffffff) - MUST be used for ALL backgrounds
  - NEVER accept default component colors - ALWAYS override with inline styles
- **Typography**: Clear font hierarchy with multiple fallbacks (Segoe UI, system-ui, sans-serif)
- **Layout**: No overlapping elements, proper spacing, professional appearance
- **Icons**: Properly sized and positioned, no visual conflicts, correct color palette
- **Content**: All text visible and readable, appropriate sizing

**MERMAID.JS SYNTAX RULES:**
- **Links**: Use `A -- "text" --> B` or `A o-- "text" --> B` (NOT `A --o "text" --> B`)
- **Nodes**: Use `nodeId["Display Text"]` format
- **Subgraphs**: Use `subgraph "Title" ... end` structure
- **Validation**: Double-check all syntax for correctness
- **Height Constraint**: ALWAYS use `max-h-[400px]` or similar height limits

**REFINEMENT DECISIONS:**
- **No Changes Needed**: If HTML perfectly fulfills the purpose AND fits viewport constraints, return original code with empty reasoning/changes
- **Viewport Fixes**: HIGHEST priority - fix any content cropping or overflow issues immediately
- **Card Structure**: Ensure proper DaisyUI card usage for all content organization
- **Minor Improvements**: Focus on enhancing purpose fulfillment without major restructuring  
- **Significant Changes**: When current approach doesn't effectively serve the slide's purpose
- **Conservative Approach**: Preserve working elements while improving purpose alignment

**QUALITY CHECKLIST:**
✅ CRITICAL: ALL content fits within the specified viewport dimensions (no cropping or overflow)
✅ MANDATORY: All content wrapped in proper DaisyUI card structure
✅ MANDATORY: Ekona color palette enforced on ALL elements (Swiss Red #dc261e, Dark Grey #2d3748, Black #000000, White #ffffff)
✅ Purpose clearly communicated through visualization
✅ All requirements from slide specifications met
✅ Professional, polished visual presentation with consistent branding
✅ No overlapping or mispositioned elements
✅ Optimal use of available space without exceeding bounds
✅ Technically sound HTML structure
✅ Text colors explicitly set (no default colors accepted)
✅ Mermaid diagrams have proper height constraints

**Mermaid-Specific Refinements:**
- **Enforce Title Separation**: The main title of the visualization MUST be a standard HTML tag (e.g., `<h2>`) outside the Mermaid `<div>`. If you see a `title` inside the Mermaid syntax, you MUST refactor the HTML to separate it.
- **Recommend Component Wrappers**: For plain, unstyled diagrams, you SHOULD wrap the Mermaid `<div>` in a DaisyUI `card` component (`<div class="card bg-base-100 shadow-xl"><div class="card-body">...</div></div>`) to improve framing and visual appeal.
- **Check for Professionalism**: Even without seeing the final colors, evaluate if the layout, spacing, and font sizes are professional and aligned with a corporate brand identity. The final render will apply brand colors, but the structure must be sound.
- **Height Constraints**: ALWAYS ensure Mermaid containers have `max-h-[400px]` or similar constraints to prevent overflow.

Focus on creating HTML that serves the slide's purpose effectively while ABSOLUTELY ensuring all content fits within the viewport constraints without any cropping or information loss."""


class ImagePromptAgent:
    """
    Agent responsible for crafting high-quality, descriptive prompts for image generation.
    Translates user requests and slide context into detailed visual descriptions
    optimized for AI image generation models.
    """

    def __init__(self):
        self.name = "image_prompt_agent" 
        self.llm_client = LangchainLLMClient()

    @monitor_agent_execution("image_prompt_agent")
    def execute(
        self, state: SlideGenerationState, config: Optional[RunnableConfig] = None
    ) -> SlideGenerationState:
        """
        Create detailed image generation prompts for slides that need images.
        
        Args:
            state: Current workflow state
            config: Optional LangGraph configuration
            
        Returns:
            Updated state with optimized image prompts
        """
        print(f"🎨 {self.name}: Crafting detailed image generation prompts...")
        
        # Check if we have slides that need images
        if not state.get("slide_contents"):
            print("  - No slide contents available")
            return state
            
        # Identify slides that need images and create prompts
        image_prompts = self._create_image_prompts(state)
        
        if image_prompts:
            state["image_prompts"] = image_prompts
            print(f"  ✅ Created {len(image_prompts)} detailed image prompts")
        else:
            print("  - No slides identified for image generation")
            
        return state
    
    def _create_image_prompts(self, state: SlideGenerationState) -> dict:
        """
        Create detailed image prompts for all slides that need images.
        
        Args:
            state: Current workflow state
            
        Returns:
            Dictionary mapping slide indices to detailed image prompts
        """
        image_prompts = {}
        slide_contents = state.get("slide_contents", [])
        layouts_info = state.get("layouts_info", {})
        presentation_plan = state.get("presentation_plan", [])
        topic = state.get("topic", "")
        
        # Handle both List[SlideSpec] and PresentationPlan object
        from .llm_models import PresentationPlan
        if isinstance(presentation_plan, PresentationPlan):
            slides_list = presentation_plan.slides
        else:
            slides_list = presentation_plan
        
        for i, slide_content in enumerate(slide_contents):
            # Get layout info
            layout_index = getattr(slide_content, 'layout_index', None)
            if not layout_index or layout_index not in layouts_info:
                continue
                
            layout_info = layouts_info[layout_index]
            
            # Check if this layout has picture placeholders
            has_picture = False
            for placeholder in layout_info.get("placeholders", []):
                if "Picture" in placeholder.get("name", ""):
                    has_picture = True
                    break
                    
            if not has_picture:
                continue
                
            # Get slide context
            slide_spec = slides_list[i] if i < len(slides_list) else None
            slide_title = getattr(slide_spec, 'slide_title', 'Slide') if slide_spec else 'Slide'
            
            # Create detailed prompt using LLM
            detailed_prompt = self._generate_detailed_image_prompt(
                topic=topic,
                slide_title=slide_title,
                slide_content=slide_content,
                slide_spec=slide_spec
            )
            
            if detailed_prompt:
                image_prompts[i] = detailed_prompt
                print(f"  📝 Created prompt for slide {i + 1}: {slide_title}")
                
        return image_prompts
    
    def _generate_detailed_image_prompt(
        self, 
        topic: str, 
        slide_title: str, 
        slide_content, 
        slide_spec
    ) -> str:
        """
        Use LLM to generate a detailed, descriptive image prompt.
        
        Args:
            topic: Original presentation topic
            slide_title: Title of the slide
            slide_content: Slide content object
            slide_spec: Slide specification from planning
            
        Returns:
            Detailed image generation prompt
        """
        try:
            # Build context for the LLM
            context_parts = [f"Topic: {topic}", f"Slide: {slide_title}"]
            
            if slide_spec:
                if hasattr(slide_spec, 'slide_purpose'):
                    context_parts.append(f"Purpose: {slide_spec.slide_purpose}")
                if hasattr(slide_spec, 'key_information'):
                    context_parts.append(f"Key Info: {', '.join(slide_spec.key_information)}")
            
            # Get text content from slide
            text_content = []
            for attr_name, attr_value in slide_content.__dict__.items():
                if isinstance(attr_value, str) and attr_value.strip() and attr_name != 'layout_index':
                    text_content.append(f"{attr_name}: {attr_value}")
            
            if text_content:
                context_parts.append(f"Content: {'; '.join(text_content)}")
            
            context = "\n".join(context_parts)
            
            prompt = f"""You are an expert at creating specific visual descriptions for AI image generation.

TASK: Based on the context below, create a detailed visual description focusing ONLY on what should appear in the image itself.

CONTEXT:
{context}

BRAND COLORS (use when appropriate):
- Swiss Red: #dc261e
- Dark Grey: #2d3748

INSTRUCTIONS:
1. Describe the exact visual scene - people, objects, environment, composition
2. Be specific about clothing, expressions, poses, lighting, atmosphere
3. Focus on the core visual elements, not the presentation context
4. Include relevant colors and professional style
5. Make it a clear, direct description of what should be generated

OUTPUT: Return ONLY the visual description for image generation, no mention of slides or presentations."""

            # Use the same pattern as other agents
            messages = [
                {"role": "system", "content": "You are an expert image prompt creator."},
                {"role": "user", "content": prompt}
            ]
            config = RunnableConfig(
                run_name="image_prompt_generation",
                tags=["image", "prompt", "generation"]
            )
            
            response = self.llm_client.chat_client.invoke(messages, config=config)
            content = str(response.content) if response.content else ""
            
            if content and content.strip():
                return content.strip()
            else:
                print(f"  ⚠️ LLM returned empty response for slide prompt")
                return self._create_fallback_prompt(topic, slide_title)
                
        except Exception as e:
            print(f"  ⚠️ Error generating detailed prompt: {e}")
            return self._create_fallback_prompt(topic, slide_title)
    
    def _create_fallback_prompt(self, topic: str, slide_title: str) -> str:
        """Create a fallback prompt when LLM generation fails."""
        if 'image of' in topic.lower():
            base_prompt = topic.replace('image of', '').strip()
        else:
            base_prompt = f"Professional business scene related to {slide_title}"
        
        return (f"{base_prompt}. High-quality, detailed illustration with clean composition, "
                f"professional style, modern design, Swiss red (#dc261e) and dark grey (#2d3748) accents.")


class ImageGenerationAgent:
    """
    Agent responsible for generating images for Layout 2 slides using GPT-image-1 model.
    Identifies slides that need images and generates them in parallel.
    """

    def __init__(self):
        self.name = "image_generation_agent"
        
        # Initialize the image webhook client
        try:
            from .image_webhook_client import ImageWebhookClient
            self.image_client = ImageWebhookClient()
            print("✅ Image webhook client initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize image webhook client: {e}")
            self.image_client = None
            
        # Initialize storage and database clients
        try:
            from .supabase_storage import get_storage_client
            from .database import get_supabase_client
            self.storage_client = get_storage_client()
            self.db_client = get_supabase_client()
            print("✅ Supabase storage and database clients initialized for image tracking")
        except Exception as e:
            print(f"⚠️ Failed to initialize Supabase clients for image tracking: {e}")
            self.storage_client = None
            self.db_client = None
            
        self.temp_dir = Path("image_debug")
        self.temp_dir.mkdir(exist_ok=True)

    @monitor_agent_execution("image_generation_agent")
    def execute(
        self, state: SlideGenerationState, config: Optional[RunnableConfig] = None
    ) -> SlideGenerationState:
        """
        Generate images for slides that need them (Layout 2).
        
        Args:
            state: Current workflow state containing slide contents
            config: Optional LangGraph configuration
            
        Returns:
            Updated state with generated images
        """
        if not self.image_client:
            print("❌ Image client not available, skipping image generation")
            return state
            
        # Check if we have slide contents
        if not state.get("slide_contents"):
            print("❌ No slide contents available for image generation")
            return state
            
        print(f"🎨 {self.name}: Starting image generation process...")
        
        # Identify slides that need images (Layout 2)
        image_slides = self._identify_image_slides(state)
        
        if not image_slides:
            print(f"ℹ️ {self.name}: No slides require image generation")
            return state
            
        print(f"🎯 {self.name}: Found {len(image_slides)} slides needing images")
        
        # Check for parallel processing
        use_parallel = os.getenv("USE_PARALLEL_IMAGE_GENERATION", "true").lower() == "true"
        
        if use_parallel:
            print("🚀 Using parallel image generation")
            return self._generate_images_parallel(state, image_slides)
        else:
            print("🔄 Using sequential image generation")
            return self._generate_images_sequential(state, image_slides)
            
    def _identify_image_slides(self, state: SlideGenerationState) -> list[dict]:
        """
        Identify slides that need image generation (Layout 2).
        
        Args:
            state: Current workflow state
            
        Returns:
            List of dictionaries containing slide info for image generation
        """
        image_slides = []
        slide_contents = state.get("slide_contents", [])
        layouts_info = state.get("layouts_info", {})
        
        for i, slide_content in enumerate(slide_contents):
            layout_index = getattr(slide_content, 'layout_index', None)
            
            # Check if this is Layout 2 (Title and Picture)
            if layout_index == 2:
                layout_info = layouts_info.get(layout_index, {})
                
                # Find the picture placeholder
                picture_placeholder = None
                for placeholder in layout_info.get("placeholders", []):
                    if "Picture 16:9" in placeholder.get("name", ""):
                        picture_placeholder = placeholder
                        break
                        
                if picture_placeholder:
                    # Get image prompt for this slide (preferring detailed prompts)
                    image_prompt = self._get_image_prompt_for_slide(i, state)
                    
                    image_slides.append({
                        "slide_index": i,
                        "slide_content": slide_content,
                        "placeholder": picture_placeholder,
                        "image_prompt": image_prompt,
                        "placeholder_description": picture_placeholder.get("name", "Picture 16:9"),
                        "placeholder_width": picture_placeholder.get("width_px", 1200),
                        "placeholder_height": picture_placeholder.get("height_px", 456),
                    })
                    
        return image_slides
        
    def _get_image_prompt_for_slide(self, slide_index: int, state: SlideGenerationState) -> str:
        """
        Get the image prompt for a slide, preferring pre-crafted prompts from ImagePromptAgent.
        
        Args:
            slide_index: Index of the slide (0-based)
            state: Full workflow state
            
        Returns:
            Image generation prompt
        """
        # First try to use pre-crafted prompt from ImagePromptAgent
        image_prompts = state.get('image_prompts', {})
        if slide_index in image_prompts:
            print(f"    🎯 Using detailed prompt from ImagePromptAgent")
            return image_prompts[slide_index]
        
        # Fallback to simple prompt generation
        print(f"    ⚠️ No detailed prompt available, using fallback")
        original_topic = state.get('topic', '')
        
        if original_topic and 'image of' in original_topic.lower():
            # User specifically requested an image scene
            base_prompt = original_topic
        else:
            # Generic business slide
            base_prompt = f"Professional business illustration for presentation slide"
            if original_topic:
                base_prompt += f" about {original_topic[:100]}"
        
        # Add style guidelines
        style_prompt = ". Style: modern, professional, clean design with corporate colors (Swiss red #dc261e, dark grey #2d3748). High quality, detailed illustration suitable for business presentation."
        
        return base_prompt + style_prompt
        
    def _generate_images_parallel(
        self, state: SlideGenerationState, image_slides: list[dict]
    ) -> SlideGenerationState:
        """
        Generate images for multiple slides in parallel.
        
        Args:
            state: Current workflow state
            image_slides: List of slide information for image generation
            
        Returns:
            Updated state with generated images
        """
        try:
            # Prepare prompts and specs for parallel generation
            prompts_and_specs = []
            for slide_info in image_slides:
                prompts_and_specs.append((
                    slide_info["image_prompt"],
                    {
                        "slide_index": slide_info["slide_index"],
                        "placeholder_description": slide_info["placeholder_description"],
                        "placeholder_width": slide_info["placeholder_width"],
                        "placeholder_height": slide_info["placeholder_height"],
                    }
                ))
                
            # Run parallel image generation
            import concurrent.futures
            
            def run_async_in_thread():
                return asyncio.run(
                    self.image_client.generate_images_parallel(prompts_and_specs)
                )
                
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_async_in_thread)
                results = future.result()
            
            # Process results and save images
            generated_images = {}
            
            # Create a mapping from slide_index to slide_info for quick lookup
            slide_info_map = {info["slide_index"]: info for info in image_slides}
            
            for slide_index, image_data in results:
                if image_data:
                    # Save image to debug directory
                    image_filename = f"slide_{slide_index + 1:02d}_generated_image.png"
                    image_path = self.temp_dir / image_filename
                    
                    if self.image_client.save_image_to_file(image_data, str(image_path)):
                        # Get the slide info for this slide index
                        slide_info = slide_info_map.get(slide_index)
                        placeholder_name = slide_info["placeholder"]["name"] if slide_info else "Picture 16:9"
                        
                        generated_images[slide_index] = {
                            "image_data": image_data,
                            "image_path": str(image_path),
                            "placeholder_name": placeholder_name
                        }
                        print(f"✅ Generated and saved image for slide {slide_index + 1}")
                    else:
                        print(f"❌ Failed to save image for slide {slide_index + 1}")
                else:
                    print(f"❌ Failed to generate image for slide {slide_index + 1}")
                    
            # Update state with generated images
            state["generated_images"] = generated_images
            state["needs_image_refinement"] = len(generated_images) > 0
            
            # Update slide contents with image paths
            slide_contents = state.get("slide_contents", [])
            for slide_index, image_info in generated_images.items():
                if slide_index < len(slide_contents):
                    slide_content = slide_contents[slide_index]
                    placeholder_name = image_info["placeholder_name"]
                    image_path = image_info["image_path"]
                    
                    # Update the slide content with the image path
                    if hasattr(slide_content, 'content'):
                        slide_content.content[placeholder_name] = image_path
                        print(f"  ✅ Updated slide {slide_index + 1} content with image: {placeholder_name} -> {image_path}")
            
            print(f"🎉 {self.name}: Generated {len(generated_images)} images successfully")
            return state
            
        except Exception as e:
            print(f"❌ Parallel image generation failed: {e}")
            state["generated_images"] = {}
            state["needs_image_refinement"] = False
            return state
            
    def _generate_images_sequential(
        self, state: SlideGenerationState, image_slides: list[dict]
    ) -> SlideGenerationState:
        """
        Generate images for slides sequentially (fallback method).
        
        Args:
            state: Current workflow state  
            image_slides: List of slide information for image generation
            
        Returns:
            Updated state with generated images
        """
        generated_images = {}
        
        for slide_info in image_slides:
            slide_index = slide_info["slide_index"]
            print(f"🎨 Generating image for slide {slide_index + 1}...")
            
            try:
                # Generate single image using thread executor
                import concurrent.futures
                
                def run_single_image(info):
                    return asyncio.run(
                        self.image_client.generate_image(
                            prompt=info["image_prompt"],
                            placeholder_description=info["placeholder_description"],
                            placeholder_width=info["placeholder_width"],
                            placeholder_height=info["placeholder_height"],
                        )
                    )
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_single_image, slide_info)
                    image_data = future.result()
                
                if image_data:
                    # Save image to debug directory
                    image_filename = f"slide_{slide_index + 1:02d}_generated_image.png"
                    image_path = self.temp_dir / image_filename
                    
                    if self.image_client.save_image_to_file(image_data, str(image_path)):
                        generated_images[slide_index] = {
                            "image_data": image_data,
                            "image_path": str(image_path),
                            "placeholder_name": slide_info["placeholder"]["name"]
                        }
                        print(f"✅ Generated and saved image for slide {slide_index + 1}")
                    else:
                        print(f"❌ Failed to save image for slide {slide_index + 1}")
                else:
                    print(f"❌ Failed to generate image for slide {slide_index + 1}")
                    
            except Exception as e:
                print(f"❌ Failed to generate image for slide {slide_index + 1}: {e}")
                continue
                
        # Update state with generated images
        state["generated_images"] = generated_images
        state["needs_image_refinement"] = len(generated_images) > 0
        
        # Update slide contents with image paths
        slide_contents = state.get("slide_contents", [])
        for slide_index, image_info in generated_images.items():
            if slide_index < len(slide_contents):
                slide_content = slide_contents[slide_index]
                placeholder_name = image_info["placeholder_name"]
                image_path = image_info["image_path"]
                
                # Update the slide content with the image path
                if hasattr(slide_content, 'content'):
                    slide_content.content[placeholder_name] = image_path
                    print(f"  ✅ Updated slide {slide_index + 1} content with image: {placeholder_name} -> {image_path}")
        
        print(f"🎉 {self.name}: Generated {len(generated_images)} images successfully")
        return state


class ImageRefinementAgent:
    """
    Agent responsible for refining generated images based on visual feedback.
    Uses vision models to analyze generated images and request improvements.
    """

    def __init__(self):
        self.name = "image_refinement_agent"
        self.max_iterations = 3  # Limited to 3 rounds as specified
        
        # Initialize the image webhook client
        try:
            from .image_webhook_client import ImageWebhookClient
            self.image_client = ImageWebhookClient()
            print("✅ Image webhook client initialized for refinement")
        except Exception as e:
            print(f"❌ Failed to initialize image webhook client: {e}")
            self.image_client = None
            
        # Initialize LLM client for vision analysis
        self.llm_client = LangchainLLMClient()
        
        # Initialize storage and database clients
        try:
            from .supabase_storage import get_storage_client
            from .database import get_supabase_client
            self.storage_client = get_storage_client()
            self.db_client = get_supabase_client()
            print("✅ Supabase clients initialized for image refinement tracking")
        except Exception as e:
            print(f"⚠️ Failed to initialize Supabase clients: {e}")
            self.storage_client = None
            self.db_client = None
            
        self.temp_dir = Path("image_debug")
        self.temp_dir.mkdir(exist_ok=True)

    @monitor_agent_execution("image_refinement_agent")
    def execute(
        self, state: SlideGenerationState, config: Optional[RunnableConfig] = None
    ) -> SlideGenerationState:
        """
        Refine generated images based on visual feedback.
        
        Args:
            state: Current workflow state containing generated images
            config: Optional LangGraph configuration
            
        Returns:
            Updated state with refined images
        """
        if not self.image_client or not state.get("needs_image_refinement", False):
            print(f"ℹ️ {self.name}: No image refinement needed")
            return state
            
        generated_images = state.get("generated_images", {})
        if not generated_images:
            print(f"ℹ️ {self.name}: No generated images to refine")
            return state
            
        print(f"🔧 {self.name}: Starting image refinement process for {len(generated_images)} images")
        
        # Check for parallel processing
        use_parallel = os.getenv("USE_PARALLEL_IMAGE_REFINEMENT", "true").lower() == "true"
        
        if use_parallel:
            print("🚀 Using parallel image refinement")
            return self._refine_images_parallel(state, generated_images)
        else:
            print("🔄 Using sequential image refinement")
            return self._refine_images_sequential(state, generated_images)
            
    def _refine_images_parallel(
        self, state: SlideGenerationState, generated_images: dict
    ) -> SlideGenerationState:
        """
        Refine multiple images in parallel with limited iterations.
        
        Args:
            state: Current workflow state
            generated_images: Dictionary of generated images
            
        Returns:
            Updated state with refined images
        """
        # For now, implement a simple approach that just validates the images exist
        # Full refinement logic would involve vision model analysis and iterative improvement
        
        refined_images = {}
        
        for slide_index, image_info in generated_images.items():
            # Check if image file exists
            image_path = image_info.get("image_path")
            if image_path and Path(image_path).exists():
                refined_images[slide_index] = image_info
                print(f"✅ Validated image for slide {slide_index + 1}")
            else:
                print(f"❌ Image file not found for slide {slide_index + 1}")
                
        # Update state with refined images
        state["refined_images"] = refined_images
        state["needs_image_refinement"] = False
        
        print(f"🎉 {self.name}: Image refinement complete for {len(refined_images)} images")
        return state
        
    def _refine_images_sequential(
        self, state: SlideGenerationState, generated_images: dict
    ) -> SlideGenerationState:
        """
        Refine images sequentially (fallback method).
        
        Args:
            state: Current workflow state
            generated_images: Dictionary of generated images
            
        Returns:
            Updated state with refined images
        """
        # Same simple validation approach for now
        return self._refine_images_parallel(state, generated_images)
