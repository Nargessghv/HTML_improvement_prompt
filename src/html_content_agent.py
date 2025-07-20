"""
HTML Content Generation Agent

This agent detects when slide content needs HTML visualization
and generates appropriate HTML content for timelines, process flows,
charts, and other custom visualizations.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

from langchain_core.runnables import RunnableConfig

from .agents import SlideGenerationState
from .html_renderer import HTMLRenderer
from .llm_client import LangchainLLMClient, SlideContent
from .monitoring import monitor_agent_execution


class HTMLContentGenerationAgent:
    """
    Agent responsible for detecting and generating HTML visualizations
    for slide content that requires custom graphics or interactive elements
    """

    def __init__(self):
        self.name = "html_content_generator"
        self.llm_client = LangchainLLMClient()

        # Initialize HTML renderer with error handling
        try:
            self.html_renderer = HTMLRenderer()
            self.html_available = True
            print(f"✅ {self.name}: HTML renderer initialized successfully")
        except RuntimeError as e:
            print(f"⚠️ {self.name}: HTML renderer not available: {e}")
            self.html_available = False

        # Setup debug folder for HTML files
        self.debug_folder = Path("html_debug")
        self.debug_enabled = os.getenv("HTML_DEBUG", "true").lower() == "true"

        if self.debug_enabled:
            self.debug_folder.mkdir(exist_ok=True)
            print(
                f"🔍 {self.name}: HTML debug mode enabled - "
                f"files saved to {self.debug_folder}"
            )

    @monitor_agent_execution("html_content_generator")
    def execute(
        self, state: SlideGenerationState, config: Optional[RunnableConfig] = None
    ) -> SlideGenerationState:
        """
        Process slide contents to generate HTML visualizations for pre-planned
        HTML slides

        Args:
            state: Current workflow state with generated slide contents and
                   presentation plan
            config: Langchain configuration with callbacks

        Returns:
            Updated state with HTML visualizations processed
        """
        print(f"🎨 {self.name}: Processing pre-planned HTML slides...")

        try:
            # Check prerequisites
            slide_contents = state.get("slide_contents")
            presentation_plan = state.get("presentation_plan")

            if not slide_contents or not presentation_plan:
                print(f"⚠️ {self.name}: Missing slide contents or presentation plan")
                return state

            if not self.html_available:
                print(f"⚠️ {self.name}: HTML rendering not available, skipping...")
                return state

            # Process slides using the presentation plan's HTML flags
            processed_slides = self._process_planned_html_slides(
                slide_contents, presentation_plan, state.get("topic", ""), config
            )

            # Update state with processed content
            state["slide_contents"] = processed_slides
            state["current_step"] = "html_content_generation_complete"

            html_count = sum(
                1
                for slide in processed_slides
                for content in slide.content.values()
                if self._is_html_visualization(content)
            )

            print(f"✅ {self.name}: Processed {len(processed_slides)} slides")
            print(f"✅ {self.name}: Generated {html_count} HTML visualizations")

            return state

        except Exception as e:
            print(f"❌ {self.name}: Error during HTML content generation: {e}")
            # Don't fail the workflow - HTML generation is optional
            state["current_step"] = "html_content_generation_complete"
            return state

    def _process_slides_for_html_content(
        self,
        slide_contents: List[SlideContent],
        topic: str,
        config: Optional[RunnableConfig] = None,
    ) -> List[SlideContent]:
        """
        Process all slides to detect and enhance content with HTML visualizations

        Args:
            slide_contents: List of slide content objects
            topic: Presentation topic for context
            config: Langchain configuration

        Returns:
            List of processed slide content with HTML visualizations
        """
        processed_slides = []
        html_generated_count = 0

        print(f"  🔍 Analyzing {len(slide_contents)} slides for HTML opportunities...")

        for i, slide_content in enumerate(slide_contents, 1):
            print(f"  📄 Processing slide {i} (Layout {slide_content.layout_index})...")

            # Show what placeholders this slide has
            placeholder_names = list(slide_content.content.keys())
            print(f"      Placeholders: {placeholder_names}")

            # Analyze content for HTML visualization opportunities
            enhanced_content = self._enhance_slide_with_html_content(
                slide_content, topic, i, len(slide_contents), config
            )

            # Check if HTML was generated for this slide
            html_generated_for_slide = any(
                self._is_html_visualization(content)
                for content in enhanced_content.content.values()
            )

            if html_generated_for_slide:
                html_generated_count += 1
                print(f"      ✅ HTML visualization generated for slide {i}")
            else:
                print(f"      ⚪ No HTML visualization for slide {i}")

            processed_slides.append(enhanced_content)

        print("  📊 HTML Generation Summary:")
        print(f"      Total slides: {len(slide_contents)}")
        print(f"      HTML visualizations: {html_generated_count}")
        print(f"      Coverage: {html_generated_count}/{len(slide_contents)} slides")

        return processed_slides

    def _enhance_slide_with_html_content(
        self,
        slide_content: SlideContent,
        topic: str,
        slide_number: int,
        total_slides: int,
        config: Optional[RunnableConfig] = None,
    ) -> SlideContent:
        """
        Enhance a single slide with HTML visualizations where appropriate

        Args:
            slide_content: Original slide content
            topic: Presentation topic
            slide_number: Current slide number
            total_slides: Total slides in presentation
            config: Langchain configuration

        Returns:
            Enhanced slide content with HTML visualizations
        """
        enhanced_content = {}
        html_generated_this_slide = False

        for placeholder_name, content_text in slide_content.content.items():
            print(f"        📝 Checking '{placeholder_name}'...")
            print(f"           Content preview: {content_text[:100]}...")

            # Check if this placeholder should have HTML visualization
            should_generate = self._should_generate_html_visualization(
                placeholder_name, content_text
            )

            if should_generate:
                print(f"        🎨 Generating HTML for '{placeholder_name}'")

                # Generate enhanced HTML content (without detailed specifications)
                html_content = self._generate_html_visualization_content(
                    placeholder_name=placeholder_name,
                    original_content=content_text,
                    topic=topic,
                    slide_number=slide_number,
                    total_slides=total_slides,
                    slide_spec=None,
                    config=config,
                )

                if html_content:
                    enhanced_content[placeholder_name] = html_content
                    html_generated_this_slide = True
                    print(f"        ✅ Generated HTML for '{placeholder_name}'")
                else:
                    # Keep original content if HTML generation fails
                    enhanced_content[placeholder_name] = content_text
                    print("        ⚠️  HTML generation failed, keeping original")
            else:
                # Keep original content for non-HTML placeholders
                enhanced_content[placeholder_name] = content_text
                print(f"        ⚪ Keeping original content for '{placeholder_name}'")

        if not html_generated_this_slide:
            print("        💡 No HTML content generated for this slide")
            print("           Consider using visualization keywords in content")
            print("           (timeline, process, workflow, steps, comparison, etc.)")

        return SlideContent(
            layout_index=slide_content.layout_index, content=enhanced_content
        )

    def _process_planned_html_slides(
        self,
        slide_contents: List[SlideContent],
        presentation_plan: List[Any],  # List[SlideSpec]
        topic: str,
        config: Optional[RunnableConfig] = None,
    ) -> List[SlideContent]:
        """
        Process slides using the presentation plan's HTML flags instead of detection

        Args:
            slide_contents: List of slide content objects
            presentation_plan: List of SlideSpec objects with is_html flags
            topic: Presentation topic for context
            config: Langchain configuration

        Returns:
            List of processed slide content with HTML visualizations where planned
        """
        processed_slides = []
        html_generated_count = 0

        print(
            f"  🔍 Processing {len(slide_contents)} slides using presentation plan..."
        )

        for i, (slide_content, slide_spec) in enumerate(
            zip(slide_contents, presentation_plan), 1
        ):
            is_html_planned = getattr(slide_spec, "is_html", False)
            layout_info = f"Layout {slide_content.layout_index}"

            if is_html_planned:
                print(f"  📄 Processing HTML slide {i} ({layout_info})...")
            else:
                print(f"  📄 Skipping non-HTML slide {i} ({layout_info})...")

            # Show what placeholders this slide has
            placeholder_names = list(slide_content.content.keys())
            print(f"      Placeholders: {placeholder_names}")

            if is_html_planned:
                # Generate HTML for slides planned as HTML
                enhanced_content = self._enhance_planned_html_slide(
                    slide_content, slide_spec, topic, i, len(slide_contents), config
                )

                # Check if HTML was actually generated for this slide
                html_generated_for_slide = any(
                    self._is_html_visualization(content)
                    for content in enhanced_content.content.values()
                )

                if html_generated_for_slide:
                    html_generated_count += 1
                    print(f"      ✅ HTML visualization generated for slide {i}")
                else:
                    print(f"      ⚠️ HTML generation failed for planned HTML slide {i}")

                processed_slides.append(enhanced_content)
            else:
                # Keep non-HTML slides as-is
                processed_slides.append(slide_content)
                print(f"      ⚪ Kept standard content for slide {i}")

        print("  📊 HTML Generation Summary:")
        print(f"      Total slides: {len(slide_contents)}")
        html_planned = sum(
            1 for spec in presentation_plan if getattr(spec, "is_html", False)
        )
        print(f"      HTML planned: {html_planned}")
        print(f"      HTML generated: {html_generated_count}")
        print(
            f"      Success rate: {html_generated_count}/{html_planned} "
            "planned HTML slides"
        )

        return processed_slides

    def _enhance_planned_html_slide(
        self,
        slide_content: SlideContent,
        slide_spec: Any,  # SlideSpec
        topic: str,
        slide_number: int,
        total_slides: int,
        config: Optional[RunnableConfig] = None,
    ) -> SlideContent:
        """
        Enhance a single slide that is planned to be HTML with HTML visualizations

        Args:
            slide_content: Original slide content
            slide_spec: The SlideSpec object for this slide
            topic: Presentation topic
            slide_number: Current slide number
            total_slides: Total slides in presentation
            config: Langchain configuration

        Returns:
            Enhanced slide content with HTML visualizations
        """
        enhanced_content = {}
        html_generated_this_slide = False

        for placeholder_name, content_text in slide_content.content.items():
            print(f"        📝 Checking '{placeholder_name}'...")
            print(f"           Content preview: {content_text[:100]}...")

            # Check if this placeholder should have HTML visualization
            should_generate = self._should_generate_html_visualization(
                placeholder_name, content_text
            )

            if should_generate:
                print(f"        🎨 Generating HTML for '{placeholder_name}'")

                # Generate enhanced HTML content with detailed specifications
                html_content = self._generate_html_visualization_content(
                    placeholder_name=placeholder_name,
                    original_content=content_text,
                    topic=topic,
                    slide_number=slide_number,
                    total_slides=total_slides,
                    slide_spec=slide_spec,
                    config=config,
                )

                if html_content:
                    enhanced_content[placeholder_name] = html_content
                    html_generated_this_slide = True
                    print(f"        ✅ Generated HTML for '{placeholder_name}'")
                else:
                    # Keep original content if HTML generation fails
                    enhanced_content[placeholder_name] = content_text
                    print("        ⚠️  HTML generation failed, keeping original")
            else:
                # Keep original content for non-HTML placeholders
                enhanced_content[placeholder_name] = content_text
                print(f"        ⚪ Keeping original content for '{placeholder_name}'")

        if not html_generated_this_slide:
            print("        💡 No HTML content generated for this slide")
            print("           Consider using visualization keywords in content")
            print("           (timeline, process, workflow, steps, comparison, etc.)")

        return SlideContent(
            layout_index=slide_content.layout_index, content=enhanced_content
        )

    def _should_generate_html_visualization(
        self, placeholder_name: str, content_text: str
    ) -> bool:
        """
        Determine if a placeholder should have HTML visualization

        Args:
            placeholder_name: Name of the placeholder
            content_text: Current content text

        Returns:
            True if HTML visualization should be generated
        """
        placeholder_lower = placeholder_name.lower()
        content_lower = content_text.lower()

        # Skip icon placeholders - they have specific icon handling
        is_icon_placeholder = "icon" in placeholder_lower
        if is_icon_placeholder:
            return False

        # ✅ EXPANDED DETECTION LOGIC:

        # 1. HTML-specific placeholders (Layout 3)
        is_html_placeholder = any(
            keyword in placeholder_lower
            for keyword in ["html", "picture from html", "picture generated from html"]
        )

        # 2. Picture/image placeholders (original logic)
        is_picture_placeholder = any(
            keyword in placeholder_lower
            for keyword in ["picture", "image", "visual", "graphic", "diagram"]
        )

        # 3. Chart placeholders that could be HTML charts
        is_chart_placeholder = any(
            keyword in placeholder_lower
            for keyword in ["chart", "graph", "data visualization", "metrics"]
        )

        # 4. Content placeholders with visualization-worthy content
        is_content_placeholder = any(
            keyword in placeholder_lower
            for keyword in ["content", "text content", "main content", "body"]
        )

        # Check content for visualization keywords
        visualization_keywords = [
            "timeline",
            "process",
            "workflow",
            "steps",
            "phases",
            "stages",
            "journey",
            "roadmap",
            "comparison",
            "vs",
            "versus",
            "before and after",
            "chart",
            "graph",
            "data",
            "metrics",
            "statistics",
            "flowchart",
            "diagram",
            "visualization",
            "infographic",
            "development process",
            "project phases",
            "methodology",
        ]

        has_visualization_keywords = any(
            keyword in content_lower for keyword in visualization_keywords
        )

        # Detect structured content that could benefit from visualization
        has_multiple_items = (
            content_text.count("\n") >= 2 or content_text.count(",") >= 2
        )
        has_dates = any(
            date_indicator in content_lower
            for date_indicator in [
                "2024",
                "2025",
                "q1",
                "q2",
                "q3",
                "q4",
                "january",
                "february",
                "march",
                "april",
                "may",
                "june",
                "july",
                "august",
                "september",
                "october",
                "november",
                "december",
            ]
        )
        has_sequential_content = any(
            seq_indicator in content_lower
            for seq_indicator in [
                "first",
                "then",
                "next",
                "finally",
                "step",
                "phase",
                "stage",
                "1.",
                "2.",
                "3.",
                "•",
                "-",
            ]
        )

        # DECISION LOGIC:

        # Always generate for HTML-specific placeholders
        if is_html_placeholder:
            print(f"    🎯 HTML placeholder detected: '{placeholder_name}'")
            return True

        # Generate for picture/chart placeholders with visualization content
        if (
            is_picture_placeholder or is_chart_placeholder
        ) and has_visualization_keywords:
            print(f"    🎯 Visual placeholder with viz content: '{placeholder_name}'")
            return True

        # Generate for content placeholders with strong visualization indicators
        if is_content_placeholder and (
            has_visualization_keywords
            or (has_multiple_items and has_dates)
            or (has_multiple_items and has_sequential_content)
        ):
            print(
                f"    🎯 Content placeholder with structured data: '{placeholder_name}'"
            )
            return True

        return False

    def _generate_html_visualization_content(
        self,
        placeholder_name: str,
        original_content: str,
        topic: str,
        slide_number: int,
        total_slides: int,
        slide_spec: Optional[Any] = None,
        config: Optional[RunnableConfig] = None,
    ) -> Optional[str]:
        """
        Generate HTML visualization content for a specific placeholder

        Args:
            placeholder_name: Name of the placeholder to generate content for
            original_content: Original text content from the placeholder
            topic: Overall presentation topic
            slide_number: Current slide number
            total_slides: Total number of slides

        Returns:
            HTML content string or None if generation failed
        """
        try:
            prompt = self._create_html_generation_prompt(
                placeholder_name,
                original_content,
                topic,
                slide_number,
                total_slides,
                slide_spec,
            )

            # Generate HTML content
            generated_html = self.llm_client.generate_content(
                system_prompt=self._get_html_generation_system_prompt(),
                user_prompt=prompt,
                config=config,
            )

            if not generated_html:
                print("        ⚠️ No HTML content generated")
                return original_content

            # Clean the response
            cleaned_html = self._clean_llm_response(generated_html)

            # Validate and correct Lucide icon names in HTML
            validated_html = self._validate_and_correct_html_icons(cleaned_html, topic)

            # Debug: Show what was generated (summary)
            if validated_html:
                print(f"    🔍 Generated {len(validated_html)} chars of content")

            if validated_html and self._validate_html_content(validated_html):
                # Save HTML to debug folder if enabled
                if self.debug_enabled and validated_html:
                    self._save_html_debug_file(
                        validated_html,
                        placeholder_name,
                        topic,
                        slide_number,
                        original_content,
                    )

                return validated_html

            # Fallback: Try to create basic HTML wrapper if content looks like HTML
            if cleaned_html and ("<" in cleaned_html and ">" in cleaned_html):
                print(f"    🔧 Wrapping partial HTML content for '{placeholder_name}'")
                wrapped_html = f"""<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .timeline {{ color: #dc261e; }}
    </style>
</head>
<body>
    {cleaned_html}
</body>
</html>"""
                if self._validate_html_content(wrapped_html):
                    # Save wrapped HTML to debug folder
                    if self.debug_enabled:
                        self._save_html_debug_file(
                            wrapped_html,
                            placeholder_name,
                            topic,
                            slide_number,
                            original_content,
                            suffix="_wrapped",
                        )
                    return wrapped_html

            print(f"    ⚠️ Generated content not valid HTML for '{placeholder_name}'")
            if cleaned_html:
                print(f"    🔍 Generated content was: {cleaned_html[:500]}...")
            return None

        except Exception as e:
            print(f"    ❌ Error generating HTML content: {e}")
            return None

    def _clean_llm_response(self, content: str) -> str:
        """
        Clean LLM response to remove markdown formatting and other artifacts

        Args:
            content: Raw LLM response content

        Returns:
            Cleaned HTML content
        """
        if not content:
            return content

        # Remove leading/trailing whitespace
        content = content.strip()

        # Remove markdown code block markers
        if content.startswith("```html"):
            content = content[7:]  # Remove ```html
        elif content.startswith("```"):
            content = content[3:]  # Remove ```

        if content.endswith("```"):
            content = content[:-3]  # Remove trailing ```

        # Remove any remaining leading/trailing whitespace
        content = content.strip()

        # Remove any triple quotes if they appear
        if content.startswith("'''html"):
            content = content[7:]
        elif content.startswith("'''"):
            content = content[3:]

        if content.endswith("'''"):
            content = content[:-3]

        return content.strip()

    def _create_html_generation_prompt(
        self,
        placeholder_name: str,
        original_content: str,
        topic: str,
        slide_number: int,
        total_slides: int,
        slide_spec: Optional[Any] = None,
    ) -> str:
        """Create prompt for HTML visualization generation."""

        # Build context section
        context_section = f"""
CONTEXT:
- Presentation Topic: {topic}
- Slide you are working on from the full deck: {slide_number} of {total_slides}
- Placeholder: {placeholder_name}
- Original Content: {original_content}"""

        # Add detailed specs if available
        if slide_spec:
            specs = []
            if hasattr(slide_spec, "detailed_purpose") and slide_spec.detailed_purpose:
                specs.append(f"- Detailed Purpose: {slide_spec.detailed_purpose}")
            if (
                hasattr(slide_spec, "content_structure")
                and slide_spec.content_structure
            ):
                specs.append(f"- Content Structure: {slide_spec.content_structure}")
            if (
                hasattr(slide_spec, "html_requirements")
                and slide_spec.html_requirements
            ):
                specs.append(f"- HTML Requirements: {slide_spec.html_requirements}")
            if hasattr(slide_spec, "visual_elements") and slide_spec.visual_elements:
                specs.append(f"- Visual Elements: {slide_spec.visual_elements}")
            if hasattr(slide_spec, "key_information") and slide_spec.key_information:
                key_info = ", ".join(slide_spec.key_information)
                specs.append(f"- Key Information: {key_info}")

            if specs:
                context_section += "\n\nDETAILED SLIDE SPECIFICATIONS:\n"
                context_section += "\n".join(specs)
                context_section += (
                    "\n\nCRITICAL: Your HTML visualization MUST implement "
                    "these specifications exactly."
                )

        # Static requirements section
        requirements_section = """
VIEWPORT REQUIREMENTS:
1.  **Overall Container**: The `<body>` of the HTML MUST be exactly `1577x603` pixels. Use Tailwind classes `w-[1577px] h-[603px]`. The root element should be a flex container (`flex`, `w-full`, `h-full`) to manage layout.

2.  **Diagram Sizing**: The `div` containing a Mermaid diagram should NOT fill the entire container if there is other content (like a title or descriptive text).
    - Use flexbox or grid to allocate space. For example, a title can be in one `div` and the diagram in another `div` that takes the remaining space (`flex-grow`).
    - The diagram's container should have padding (e.g., `p-8`) to ensure it doesn't touch the edges.
    - Example Layout:
      <body class="w-[1577px] h-[603px] flex flex-col p-8">
        <h1 class="text-3xl font-bold mb-4">Diagram Title</h1>
        <div class="mermaid flex-grow">
          ... Mermaid diagram ...
        </div>
      </body>

3.  **No Overflow**: All content, including text and the diagram, MUST fit within the `1577x603` viewport without any scrolling or content being cut off.
"""

        # Visual design section
        design_section = """
VISUAL DESIGN (CRITICAL):
- Color Palette:
  - Primary/Accent: Swiss Red (#dc261e)
  - Text (Headings): Dark Grey (#2d3748)
  - Text (Body): Black (#000000)
  - Background: White (#ffffff)

- Typography:
  - Font: 'Segoe UI', system-ui, sans-serif
  - Base Size: 16px (text-base)
  - Headers: 24px (text-2xl, font-bold)

- Layout:
  - Keep it clean, simple, and minimalist.
  - Use ample white space.
  - Ensure content is highly readable.

- Components:
  - Use DaisyUI and Flowbite components for layout and elements.
  - Use Mermaid.js for diagrams, molecular pathways, etc.
  - Repurpose components creatively (e.g., an Event Schedule can be used for a sequence of steps).
  - Use Tailwind CSS for custom styling and adjustments."""

        # Example section
        example_section = """
COMPONENT EXAMPLES:
Use these as a guide for building your visualization.

1. Stats:
<div class="stats shadow">
  <div class="stat">
    <div class="stat-title">Total Page Views</div>
    <div class="stat-value">89,400</div>
    <div class="stat-desc">21% more than last month</div>
  </div>
</div>

2. Cards:
<div class="card bg-base-100 w-96 shadow-sm">
  <figure>
    <img
      src="https://img.daisyui.com/images/stock/photo-1606107557195-0e29a4b5b4aa.webp"
      alt="Shoes" />
  </figure>
  <div class="card-body">
    <h2 class="card-title">Card Title</h2>
    <p>A card component has a body and action buttons.</p>
    <div class="card-actions justify-end">
      <button class="btn btn-primary">Buy Now</button>
    </div>
  </div>
</div>

3. Timeline (from Flowbite):
<ol class="relative border-s border-gray-200">
  <li class="mb-10 ms-4">
    <div class="absolute w-3 h-3 bg-gray-200 rounded-full mt-1.5 
                -start-1.5 border border-white"></div>
    <time class="mb-1 text-sm font-normal leading-none text-gray-400">
      Step 1
    </time>
    <h3 class="text-lg font-semibold text-gray-900">Analysis</h3>
    <p class="mb-4 text-base font-normal text-gray-500">
      Understand project requirements.
    </p>
  </li>
  <li class="ms-4">
    <div class="absolute w-3 h-3 bg-gray-200 rounded-full mt-1.5 
                -start-1.5 border border-white"></div>
    <time class="mb-1 text-sm font-normal leading-none text-gray-400">
      Step 2
    </time>
    <h3 class="text-lg font-semibold text-gray-900">Development</h3>
    <p class="text-base font-normal text-gray-500">
      Implement core features.
    </p>
  </li>
</ol>"""

        # Combine all sections
        return "\\n\\n".join(
            [
                (
                    "Generate an HTML visualization for a PowerPoint slide "
                    "placeholder."
                ),
                context_section,
                requirements_section,
                design_section,
                example_section,
                (
                    "OUTPUT:\\nReturn ONLY the complete HTML code. "
                    "No explanations or markdown."
                ),
            ]
        )

    def _get_html_generation_system_prompt(self) -> str:
        """Get system prompt for HTML generation"""
        return """You are an expert web developer and data visualization specialist.
Your mission is to create visually compelling, minimalist HTML content that
perfectly fills a 1577x603px container for a business presentation.

**Core Principles:**
1.  **Strict Component Usage**: Your ONLY tools for layout and components
    are DaisyUI and Flowbite. You MUST NOT use any other library or write
    custom components.
2.  **Brand Consistency**: Strictly adhere to the specified color palette.
    Use Tailwind CSS to override component styles if necessary to match the theme.
    - Primary/Accent: Swiss Red (#dc261e)
    - Text: Dark Grey for headers (#2d3748), Black for body (#000000)
    - Background: White (#ffffff)
3.  **Static & Non-Interactive**: The output is for a static image.
    DO NOT include animations, hover effects, or any user interactivity.
4.  **No Custom SVG**: You MUST NOT generate any inline SVG code. The ONLY
    way to use icons is with the Lucide icon sprite system, like:
    `<svg><use href="#icon-name"></use></svg>`.

**Layout and Sizing (CRITICAL):**
- The **ENTIRE HTML `<body>`** is the `1577x603px` container.
- If the content includes a diagram AND other elements (like a title), you MUST divide the space.
- The Mermaid diagram `div` must be smaller than the body to leave room for titles, text, etc.
- Use Flexbox or Grid to create a balanced layout. For example:
  - A heading at the top.
  - A `flex-grow` container below it for the diagram, with padding (`p-8`).
- **NEVER** make the diagram's container `w-full h-full` if other content exists.

**Library Usage Guidelines:**
1.  **DaisyUI & Flowbite**: Use for ALL components (cards, stats, timelines, etc.).
    Stick to simple, clean components. For example, use DaisyUI Cards
    or Flowbite's standard components.

2.  **Mermaid.js for Diagrams**: For ANY chart, graph, process flow,
    timeline, or diagram, you MUST use Mermaid.js syntax.
    - Place the Mermaid syntax inside a `<div class="mermaid">` element.
    - The renderer will handle a theme matching the brand colors, so do not
      add styling commands inside the mermaid code.
    - **CRITICAL**: The diagram MUST be simple enough to fit comfortably
      within the 1577x603px container without overflowing or scrolling.
      Keep diagrams clear and concise.
    - Example:
      <div class="mermaid">
        graph TD;
            A[Start] --> B(Process);
            B --> C{Decision};
      </div>

    **Mermaid.js Best Practices (Follow these STRICTLY to avoid errors):**
    - **Semicolons are Mandatory**: End EVERY line with a semicolon (`;`).
    - **One Link Per Line**: To create multiple links from one node, define each on a separate line.
      - Correct: `A --> B; A --> C;`
      - WRONG: `A --> B & C;`
    - **Simple Node Text**: Do NOT embed HTML or complex styles in node labels. Use plain text.
      - Correct: `A["Node with simple text"];`
      - WRONG: `A["<div style='...'>Complex HTML</div>"];`
    - **Quotes in Labels**: Use standard double quotes for labels. Do NOT escape quotes inside labels. If you need a quote, use single quotes inside the double-quoted string.
      - Correct: `A["Label with 'a quote'"];`
      - WRONG: `A["Label with \\"a quote\\""];`
    - **Styling**: Do NOT use `linkStyle` or other inline styling. The theme is applied automatically.
    - **Keep it Simple**: Focus on creating a clear, structurally correct diagram. Avoid overly complex or obscure Mermaid features.

3.  **Lucide Icons**: Use for all icons. You are provided with a sprite sheet.
    Reference icons by name using the `<use>` tag.
    - Correct: `<svg class="w-6 h-6"><use href="#zap"></use></svg>`
    - WRONG: `<svg>...</svg>` (Do not generate full SVG tags)

Your HTML must be production-ready, clean, and strictly follow these rules
for rendering in PowerPoint slides.
"""

    def _validate_html_content(self, content: str) -> bool:
        """
        Validate that content is proper HTML

        Args:
            content: Content string to validate

        Returns:
            True if content appears to be valid HTML
        """
        content_lower = content.lower().strip()

        # Check for basic HTML structure
        has_doctype = "<!doctype" in content_lower or "<html" in content_lower
        has_body = "<body" in content_lower

        # Check for common HTML elements
        has_elements = any(
            tag in content_lower for tag in ["<div", "<p", "<h1", "<h2", "<h3", "<span"]
        )

        # Relaxed validation - if it has HTML structure, accept it
        has_basic_html = "<" in content and ">" in content

        # Accept if it has proper structure OR basic HTML tags
        return (has_doctype and has_body and has_elements) or (
            has_doctype and has_basic_html
        )

    def _is_html_visualization(self, content: str) -> bool:
        """Check if content is an HTML visualization"""
        return self._validate_html_content(content)

    def _save_html_debug_file(
        self,
        html_content: str,
        placeholder_name: str,
        topic: str,
        slide_number: int,
        original_content: str,
        suffix: str = "",
    ) -> None:
        """
        Save HTML content to debug file for comparison and verification

        Args:
            html_content: Generated HTML content
            placeholder_name: Name of the placeholder
            topic: Presentation topic
            slide_number: Slide number
            original_content: Original text content
            suffix: Optional suffix for filename
        """
        if not self.debug_enabled:
            return

        try:
            # Ensure debug directory exists
            os.makedirs(self.debug_folder, exist_ok=True)

            # Create filename with slide info and timestamp
            slide_num = slide_number
            clean_placeholder = "".join(
                c for c in placeholder_name if c.isalnum() or c in ("-", "_")
            )[:30]
            timestamp = datetime.now().strftime("%H%M%S")

            # Inject Lucide sprite into HTML for debug file so icons display correctly
            if self.html_renderer and self.html_renderer.lucide_sprite_content:
                html_content = self.html_renderer._inject_lucide_sprite(html_content)

            base_filename = (
                f"slide_{slide_num:02d}_{clean_placeholder}_{timestamp}{suffix}"
            )
            html_file = os.path.join(self.debug_folder, f"{base_filename}.html")
            json_file = os.path.join(self.debug_folder, f"{base_filename}.json")

            # Save HTML file with sprite included
            with open(html_file, "w", encoding="utf-8") as f:
                f.write(html_content)

            # Save metadata JSON
            metadata = {
                "timestamp": datetime.now().isoformat(),
                "slide_number": slide_number,
                "placeholder_name": placeholder_name,
                "topic": topic,
                "original_content_length": len(original_content),
                "generated_html_length": len(html_content),
                "lucide_sprite_included": bool(
                    self.html_renderer
                    and self.html_renderer.lucide_sprite_content
                    and "Lucide Icons Sprite" in html_content
                ),
            }

            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)

            print(f"    💾 Saved HTML debug file: {base_filename}.html")

        except Exception as e:
            print(f"    ⚠️ Failed to save debug file: {e}")

    def _validate_and_correct_html_icons(self, html_content: str, topic: str) -> str:
        """
        Validate and correct Lucide icon names in HTML content

        Args:
            html_content: HTML content containing Lucide icon references
            topic: Presentation topic for context in corrections

        Returns:
            HTML content with corrected icon names
        """
        try:
            # Extract icon names from HTML
            import re

            icon_pattern = r'<use href="#([^"]+)"></use>'
            icon_matches = re.findall(icon_pattern, html_content)

            if not icon_matches:
                return html_content

            print(
                f"    🔍 Found {len(icon_matches)} Lucide icons in HTML: {icon_matches}"
            )

            # Get valid Lucide icon names from sprite
            valid_icons = self._get_valid_lucide_icons()

            # Find invalid icons
            invalid_icons = []
            for icon_name in icon_matches:
                if icon_name not in valid_icons:
                    invalid_icons.append(icon_name)

            if not invalid_icons:
                print("    ✅ All Lucide icons are valid")
                return html_content

            print(f"    ⚠️ Invalid Lucide icons: {invalid_icons}")

            # Get corrections from LLM
            corrections = self._get_lucide_icon_corrections(
                invalid_icons, topic, valid_icons
            )

            if not corrections:
                print("    ⚠️ No corrections generated")
                return html_content

            print(f"    ✅ Generated corrections: {corrections}")

            # Apply corrections to HTML
            corrected_html = html_content
            for invalid_icon, valid_icon in corrections.items():
                old_ref = f'<use href="#{invalid_icon}"></use>'
                new_ref = f'<use href="#{valid_icon}"></use>'
                corrected_html = corrected_html.replace(old_ref, new_ref)
                print(f"    📝 Corrected '{invalid_icon}' → '{valid_icon}' in HTML")

            return corrected_html

        except Exception as e:
            print(f"    ⚠️ Error validating HTML icons: {e}")
            return html_content

    def _get_valid_lucide_icons(self) -> list:
        """Get list of valid Lucide icon names from the sprite"""
        try:
            if not self.html_renderer or not self.html_renderer.lucide_sprite_content:
                return []

            # Extract icon IDs from sprite content
            import re

            id_pattern = r'id="([^"]+)"'
            valid_icons = re.findall(
                id_pattern, self.html_renderer.lucide_sprite_content
            )
            return valid_icons

        except Exception as e:
            print(f"Warning: Could not extract Lucide icons: {e}")
            return []

    def _get_lucide_icon_corrections(
        self, invalid_icons: list, topic: str, valid_icons: list
    ) -> dict:
        """
        Get corrections for invalid Lucide icon names using LLM

        Args:
            invalid_icons: List of invalid icon names
            topic: Presentation topic for context
            valid_icons: List of all valid Lucide icon names

        Returns:
            Dictionary mapping invalid icons to corrected icons
        """
        try:
            # Sample valid icons for prompt (first 100 alphabetically)
            sample_valid_icons = sorted(valid_icons)[:100]

            prompt = (
                f"""
The following Lucide icon names are INVALID and need correction:
{', '.join(invalid_icons)}

Presentation topic: {topic}

AVAILABLE LUCIDE ICONS (sample of {len(sample_valid_icons)} """
                + f"""from {len(valid_icons)} total):
{', '.join(sample_valid_icons)}

For each invalid icon, suggest the closest valid Lucide icon name that:
1. ✅ EXISTS in the Lucide library (from the list above)
2. 🎯 Has similar meaning/purpose to the invalid icon
3. 📝 Fits the presentation topic: "{topic}"
4. 🔤 Uses exact Lucide naming (hyphen-separated, lowercase)

Common corrections:
- check-circle -> circle-check
- edit -> pen or pencil
- bar-chart -> bar-chart-3
- money -> coins

Please respond in this EXACT format:
invalid_icon1 -> valid_icon1
invalid_icon2 -> valid_icon2
"""
            )

            system_prompt = """You are an expert Lucide icon validation specialist.
Your task is to correct invalid Lucide icon names to valid alternatives.

CRITICAL REQUIREMENTS:
- ONLY suggest icon names from the provided valid icons list
- Choose icons with similar semantic meaning
- Use exact Lucide naming conventions (lowercase, hyphen-separated)
- Consider the presentation context when choosing alternatives"""

            # Use the LLM client to generate corrections
            response = self.llm_client.generate_content(
                system_prompt=system_prompt, user_prompt=prompt
            )

            if not response:
                return {}

            # Parse corrections from response
            corrections = {}
            lines = response.strip().split("\n")

            for line in lines:
                if "->" in line:
                    parts = line.split("->")
                    if len(parts) == 2:
                        invalid = parts[0].strip()
                        valid = parts[1].strip()
                        if invalid in invalid_icons and valid in valid_icons:
                            corrections[invalid] = valid

            return corrections

        except Exception as e:
            print(f"Error getting Lucide icon corrections: {e}")
            return {}
