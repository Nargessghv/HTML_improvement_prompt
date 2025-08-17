"""
Presentation Planning Agent Module

Agent responsible for creating intelligent presentation plans
using LLM to determine optimal slide structure and flow.
"""

from typing import Any, Dict, List, Optional

from langchain_core.runnables import RunnableConfig

from ..llm_client import LangchainLLMClient
from ..llm_models import SlideSpec
from ..monitoring import monitor_agent_execution
from ..state import SlideGenerationState
from .prompts.presentation_planning_prompts import (
    create_presentation_planning_prompt,
    get_planning_system_prompt,
)


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
            print(
                f"📋 {self.name}: Approved outline present: {approved_outline is not None}"
            )
            if approved_outline:
                print(
                    f"📋 {self.name}: Approved outline slides count: {len(approved_outline.get('slides', []))}"
                )
                # Debug: Print slide details to verify is_html and is_image flags
                for i, slide in enumerate(approved_outline.get('slides', [])):
                    print(f"🔍 Approved slide {i+1}: {slide.get('title', 'No title')}")
                    print(f"   - is_html: {slide.get('is_html', False)}")
                    print(f"   - is_image: {slide.get('is_image', False)}")
                    print(f"   - content_type: {slide.get('content_type', 'N/A')}")

            # Check if we have an approved outline from interactive planning
            if approved_outline:
                print(
                    f"📋 {self.name}: Using approved outline from interactive planning"
                )
                presentation_plan = self._convert_approved_outline_to_plan(
                    approved_outline, layouts_info
                )
            else:
                print(f"📋 {self.name}: Generating new presentation plan with LLM")
                # Use LLM to create intelligent presentation plan with callback tracing
                presentation_plan = self._plan_presentation_with_tracing(
                    layouts_info, topic, title, config
                )
                print(f"✅ {self.name}: Presentation plan: {presentation_plan}")

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
            # Print each step of the presentation plan for debugging and transparency
            print("📋 Presentation Plan Steps:")
            for idx, slide_spec in enumerate(presentation_plan, 1):
                # Try to print key details for each slide step
                # SlideSpec may have attributes like title, layout_index, content_type, etc.
                # We'll print the most common ones, but use getattr for safety
                slide_title = getattr(slide_spec, "slide_title", "Untitled")
                layout_index = getattr(slide_spec, "layout_index", "N/A")
                is_html = getattr(slide_spec, "is_html", False)
                is_image = getattr(slide_spec, "is_image", False)
                
                # Determine content type from flags
                if is_html and is_image:
                    content_type = "html+image"
                elif is_html:
                    content_type = "html"
                elif is_image:
                    content_type = "image"
                else:
                    content_type = "text"
                    
                print(
                    f"  Step {idx}: Title='{slide_title}', "
                    f"Layout={layout_index}, ContentType={content_type}"
                )
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
        from ..llm_models import PresentationPlan

        # Create the planning prompt using the extracted prompt function
        prompt = create_presentation_planning_prompt(layouts_info, topic, title)
        system_prompt = get_planning_system_prompt()
        
        # Debug: Log the topic being processed
        print(f"🔍 Planning for topic: '{topic}'")

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
                # Debug logging for HTML/image decisions
                for idx, slide in enumerate(response.slides, 1):
                    print(f"  Slide {idx}: is_html={slide.is_html}, is_image={slide.is_image}, title='{slide.slide_title}'")
                return response.slides
            print("Warning: No structured response received")
            return self._create_default_plan(layouts_info)

        except Exception as e:
            print(f"Structured planning failed: {e}")
            return self._create_default_plan(layouts_info)

    def _convert_approved_outline_to_plan(
        self, approved_outline: Dict[str, Any], layouts_info: Dict[int, Dict[str, Any]]
    ) -> List[SlideSpec]:
        """
        Convert approved outline from interactive planning to SlideSpec format

        Args:
            approved_outline: The approved outline from interactive planning
            layouts_info: Available layout information for layout selection

        Returns:
            List of SlideSpec objects matching the approved outline
        """
        from ..llm_models import SlideSpec

        slides = approved_outline.get("slides", [])
        slide_specs = []


        for slide_data in slides:
            slide_number = slide_data.get("slide_number", len(slide_specs) + 1)
            title = slide_data.get("title", f"Slide {slide_number}")
            key_points = slide_data.get("key_points", [])

            # Get content flags from new structure (with fallback for old content_type)
            is_html = slide_data.get("is_html", False)
            is_image = slide_data.get("is_image", False)
            placeholder_requirements = slide_data.get("placeholder_requirements", [])
            
            # Fallback for old content_type format (for backward compatibility during transition)
            content_type = slide_data.get("content_type")
            if content_type and not (is_html or is_image):
                # Convert old format to new format
                is_html = content_type in ["chart", "timeline", "comparison"]
                is_image = content_type == "visual"

            # First try to use suggested_layout from approved outline
            suggested_layout = slide_data.get("suggested_layout")
            layout_index = None
            
            if suggested_layout:
                # Find layout index by name
                for idx, layout_info in layouts_info.items():
                    if layout_info.get("name", "").lower() == suggested_layout.lower():
                        layout_index = idx
                        print(f"    Using suggested layout '{suggested_layout}' -> index {idx}")
                        break
            
            # If no suggested layout or not found, use LLM to select based on content
            if layout_index is None:
                print(f"    Selecting layout with LLM for slide: {title}")
                layout_index = self._select_layout_with_llm(
                    layouts_info, 
                    title, 
                    key_points, 
                    is_html, 
                    is_image,
                    placeholder_requirements
                )
            
            # Convert placeholder requirements to PlaceholderRequirement objects
            from ..llm_models import PlaceholderRequirement
            placeholder_reqs = []
            if placeholder_requirements:
                for req in placeholder_requirements:
                    if isinstance(req, dict):
                        placeholder_reqs.append(PlaceholderRequirement(**req))
                    else:
                        placeholder_reqs.append(req)
            
            # If no placeholder requirements provided, create them based on flags
            if not placeholder_reqs:
                if is_image:
                    placeholder_reqs = [PlaceholderRequirement(
                        placeholder_name="Picture 16:9",
                        content_type="image",
                        description=f"AI-generated image for {title}"
                    )]
                elif is_html:
                    placeholder_reqs = [PlaceholderRequirement(
                        placeholder_name="Picture from HTML", 
                        content_type="html",
                        description=f"HTML visualization for {title}"
                    )]

            # Determine slide type for purpose description
            slide_type = "image" if is_image else "HTML" if is_html else "text"

            # Create slide specification
            slide_spec = SlideSpec(
                layout_index=layout_index,
                slide_title=title,
                slide_purpose=f"Create {slide_type} slide: {title}",
                is_html=is_html,
                is_image=is_image,
                detailed_purpose=f"Content from approved outline - slide {slide_number}",
                content_structure=f"Key points: {', '.join(key_points)}",
                html_requirements=(
                    f"Create visualization for {title}" if is_html else None
                ),
                image_requirements=(
                    f"Generate visual content for {title}" if is_image else None
                ),
                visual_elements=slide_type if is_html else None,
                key_information=key_points,
                placeholder_requirements=placeholder_reqs,
            )

            slide_specs.append(slide_spec)

        print(
            f"✅ Converted approved outline to {len(slide_specs)} slide specifications"
        )
        # Print out each SlideSpec for debugging and traceability
        for idx, spec in enumerate(slide_specs, 1):
            print(f"    Slide {idx}: {spec}")
        return slide_specs

    def _select_layout_with_llm(
        self, 
        layouts_info: Dict[int, Dict[str, Any]], 
        slide_title: str,
        key_points: List[str],
        is_html: bool,
        is_image: bool,
        placeholder_requirements: List[Any]
    ) -> int:
        """
        Use LLM to intelligently select the best layout based on slide content
        
        Args:
            layouts_info: Dictionary of all available layouts with their details
            slide_title: Title of the slide
            key_points: Key points for the slide
            is_html: Whether slide needs HTML visualization
            is_image: Whether slide needs AI-generated image
            placeholder_requirements: Specific placeholder requirements
            
        Returns:
            Layout index selected by LLM
        """
        # Build detailed layout descriptions for LLM
        layout_options = []
        for idx, layout_info in layouts_info.items():
            layout_name = layout_info.get("name", f"Layout {idx}")
            placeholders = layout_info.get("placeholders", [])
            
            # Build detailed placeholder info
            placeholder_details = []
            for p in placeholders:
                if isinstance(p, dict):
                    name = p.get("name", "Unknown")
                    p_type = p.get("type", "Unknown")
                    placeholder_details.append(f"{name} ({p_type})")
                else:
                    placeholder_details.append(str(p))
                    
            layout_options.append({
                "index": idx,
                "name": layout_name,
                "placeholders": placeholder_details
            })
        
        # Create prompt for layout selection
        prompt = f"""Select the BEST layout for this slide based on content requirements:

SLIDE CONTENT:
- Title: {slide_title}
- Key Points: {', '.join(key_points) if key_points else 'None'}
- Needs HTML visualization: {is_html}
- Needs AI-generated image: {is_image}
- Content Type: {'HTML/Visual' if is_html else 'Image' if is_image else 'Text'}

AVAILABLE LAYOUTS:
"""
        
        for layout in layout_options:
            prompt += f"\nLayout {layout['index']}: {layout['name']}\n"
            prompt += f"  Placeholders: {', '.join(layout['placeholders'])}\n"
        
        prompt += """\n
SELECTION CRITERIA:
1. For HTML content: Choose layouts with picture/image placeholders that can display rendered HTML
2. For AI images: Choose layouts with picture placeholders for generated images  
3. For text content: Choose layouts with content/text placeholders
4. Match the number and type of placeholders to the content needs
5. Consider the slide's purpose and how to best present the information

RETURN ONLY THE LAYOUT INDEX NUMBER (e.g., 3)
"""
        
        try:
            # Use LLM to select layout
            response = self.llm_client.generate_content(
                system_prompt="You are a presentation layout expert. Select the most appropriate layout index based on content requirements.",
                user_prompt=prompt
            )
            
            # Extract layout index from response
            import re
            match = re.search(r'\b(\d+)\b', response)
            if match:
                selected_index = int(match.group(1))
                if selected_index in layouts_info:
                    print(f"      LLM selected layout {selected_index}: {layouts_info[selected_index].get('name', 'Unknown')}")
                    return selected_index
                    
        except Exception as e:
            print(f"      Warning: LLM layout selection failed: {e}")
        
        # Fallback: Select first suitable layout based on content type
        print("      Falling back to default layout selection")
        if is_html or is_image:
            # Find first layout with picture placeholder
            for idx, layout_info in layouts_info.items():
                placeholders = layout_info.get("placeholders", [])
                for p in placeholders:
                    if isinstance(p, dict):
                        name = p.get("name", "").lower()
                        if any(word in name for word in ["picture", "image", "visual", "html"]):
                            return idx
        
        # Default to first non-logo layout
        for idx, layout_info in layouts_info.items():
            if "logo" not in layout_info.get("name", "").lower():
                return idx
                
        return list(layouts_info.keys())[0] if layouts_info else 0

    def _create_default_plan(
        self, layouts_info: Dict[int, Dict[str, Any]]
    ) -> List[SlideSpec]:
        """Create a basic default plan if LLM planning fails"""
        from ..llm_models import SlideSpec

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