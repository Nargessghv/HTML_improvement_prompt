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
from typing import Dict, List, Optional

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
        Process slide contents to detect and generate HTML visualizations

        Args:
            state: Current workflow state with generated slide contents
            config: Langchain configuration with callbacks

        Returns:
            Updated state with HTML visualizations processed
        """
        print(f"🎨 {self.name}: Processing content for HTML visualizations...")

        try:
            # Check prerequisites
            slide_contents = state.get("slide_contents")
            if not slide_contents:
                print(f"⚠️ {self.name}: No slide contents to process")
                return state

            if not self.html_available:
                print(f"⚠️ {self.name}: HTML rendering not available, skipping...")
                return state

            # Process each slide for HTML visualization opportunities
            processed_slides = self._process_slides_for_html_content(
                slide_contents, state.get("topic", ""), config
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

                # Generate enhanced HTML content
                html_content = self._generate_html_visualization_content(
                    placeholder_name=placeholder_name,
                    original_content=content_text,
                    topic=topic,
                    slide_number=slide_number,
                    total_slides=total_slides,
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
                placeholder_name, original_content, topic, slide_number, total_slides
            )

            system_prompt = self._get_html_generation_system_prompt()

            # Generate HTML content using LLM
            html_content = self.llm_client.generate_content(
                system_prompt=system_prompt, user_prompt=prompt, config=config
            )

            # Clean the LLM response to remove markdown formatting
            html_content = self._clean_llm_response(html_content)

            # Debug: Show what was generated (summary)
            if html_content:
                print(f"    🔍 Generated {len(html_content)} chars of content")

            if html_content and self._validate_html_content(html_content):
                # Save HTML to debug folder if enabled
                if self.debug_enabled and html_content:
                    self._save_html_debug_file(
                        html_content,
                        placeholder_name,
                        topic,
                        slide_number,
                        original_content,
                    )

                return html_content

            # Fallback: Try to create basic HTML wrapper if content looks like HTML
            if html_content and ("<" in html_content and ">" in html_content):
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
    {html_content}
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

            # Final fallback: Convert text content to basic HTML timeline
            if html_content and len(html_content) > 10:
                print(
                    f"    🔧 Converting text to basic HTML timeline for '{placeholder_name}'"
                )
                basic_html = self._create_basic_html_timeline(original_content, topic)
                if basic_html and self._validate_html_content(basic_html):
                    # Save basic HTML to debug folder
                    if self.debug_enabled:
                        self._save_html_debug_file(
                            basic_html,
                            placeholder_name,
                            topic,
                            slide_number,
                            original_content,
                            suffix="_basic",
                        )
                    return basic_html

            print(f"    ⚠️ Generated content not valid HTML for '{placeholder_name}'")
            if html_content:
                print(f"    🔍 Generated content was: {html_content[:500]}...")
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
    ) -> str:
        """Create prompt for HTML visualization generation"""
        return f"""
Generate an HTML visualization for a PowerPoint slide placeholder.

CONTEXT:
- Presentation Topic: {topic}
- Slide: {slide_number} of {total_slides}
- Placeholder: {placeholder_name}
- Original Content: {original_content}

TASK:
Create a complete, self-contained HTML document that visualizes the 
original content in an engaging, professional way suitable for 
business presentations.

VISUALIZATION TYPES TO CONSIDER:
- Timeline: For chronological events, project phases, roadmaps
- Process Flow: For step-by-step processes, workflows
- Comparison Chart: For comparing options, before/after scenarios
- Infographic: For statistics, metrics, key points
- Diagram: For relationships, hierarchies, structures

🎯 CRITICAL SPACE OPTIMIZATION REQUIREMENTS:
- Exact dimensions: 1577x603 pixels (fixed container size)
- MAXIMIZE content density - use every pixel effectively
- NO white empty space or large margins
- NO grey background colors (#f5f5f5, #eeeeee, #cccccc, etc.)
- Compact, information-dense layouts
- Full-width utilization of the 1577x603 space

🎨 VISUAL DESIGN REQUIREMENTS:
- Complete HTML document with <!DOCTYPE html>, <head>, and <body>
- Professional styling using CSS (embedded in <style> tags)
- Container: width: 1577px; height: 603px; overflow: hidden;
- Background: Pure white (#ffffff) or rich brand colors only
- Primary color: #dc261e (Ekona red) for accents and highlights
- Secondary color: #404040 (dark grey) for text and structure
- Text color: #2d3748 for maximum readability
- Use modern web fonts (Segoe UI, Inter, or system fonts)
- NO external dependencies (no external CSS/JS files)
- NO interactive elements (this will be converted to static image)

📏 LAYOUT OPTIMIZATION RULES:
1. Set body and html to exact dimensions: 1577x603px
2. Use margin: 0; padding: 0; on body and html
3. Create a main container with full dimensions
4. Distribute content evenly across the full width and height
5. Use CSS Grid or Flexbox for optimal space distribution
6. Minimize whitespace between elements
7. Scale fonts and elements to fit the space perfectly
8. Use compact layouts with multiple columns when appropriate

🎯 CONTENT DENSITY GUIDELINES:
- For timelines: Use horizontal layouts to maximize width usage
- For processes: Arrange in efficient grids (2x2, 3x2, etc.)
- For comparisons: Use side-by-side layouts filling full width
- For infographics: Create dense, information-rich displays
- Add visual elements (icons, borders, gradients) to fill space
- Use larger fonts and generous padding within constraints

💡 COLOR SCHEME ENHANCEMENTS:
- Primary backgrounds: #ffffff (pure white) or #dc261e (Ekona red)
- Accent colors: #f7fafc (very light blue-grey), #e2e8f0 (light grey)
- Gradient backgrounds are encouraged for visual interest
- Card backgrounds: subtle shadows with #ffffff
- Border colors: #e2e8f0 for structure, #dc261e for emphasis

OUTPUT:
Return ONLY the complete HTML code with optimized 1577x603 layout, 
no explanations or markdown formatting.
"""

    def _get_html_generation_system_prompt(self) -> str:
        """Get system prompt for HTML generation"""
        return """You are an expert web developer and data visualization specialist 
specializing in creating high-density, space-optimized HTML visualizations 
for PowerPoint presentations.

🎯 PRIMARY MISSION: Create visually compelling HTML that MAXIMIZES the 
1577x603 pixel space with zero wasted area.

DESIGN PRINCIPLES:
- **Space Efficiency First**: Every pixel serves a purpose
- **Visual Density**: Pack maximum information in minimum space
- **Professional Appearance**: Clean, modern, business-appropriate
- **Brand Consistency**: Ekona colors and professional typography
- **Zero Waste Policy**: No large margins, excessive padding, or empty areas

CRITICAL TECHNICAL REQUIREMENTS:
- Self-contained HTML (no external resources)
- CSS embedded in <style> tags within <head>
- Exact container dimensions: 1577px × 603px
- No JavaScript or interactive elements
- Valid HTML5 structure optimized for image conversion

🚫 ABSOLUTE PROHIBITIONS:
- Large empty spaces or excessive margins
- Grey background colors (#f5f5f5, #eeeeee, #cccccc, etc.)
- Wasted vertical or horizontal space
- Default browser styling (always reset margins/padding)
- Sparse layouts with poor space utilization

✅ MANDATORY OPTIMIZATIONS:
1. **Container Setup**: 
   - html, body { margin: 0; padding: 0; width: 1577px; height: 603px; }
   - Main container: full dimensions with overflow: hidden
   
2. **Layout Strategy**:
   - Use CSS Grid or Flexbox for perfect space distribution
   - Multiple columns for horizontal content (2-4 columns optimal)
   - Vertical stacking for timeline/process flows
   - Compact card layouts with minimal gaps
   
3. **Typography Scaling**:
   - Scale font sizes to fill space appropriately
   - Titles: 28-36px for impact
   - Subtitles: 20-24px for hierarchy
   - Body text: 16-18px for readability
   - Adjust based on content density
   
4. **Visual Enhancement**:
   - Subtle gradients for background interest
   - Strategic use of Ekona red (#dc261e) for highlights
   - Box shadows for depth without consuming space
   - Border accents for structure and visual appeal

🎨 LAYOUT PATTERNS FOR DIFFERENT CONTENT:
- **Timeline**: Horizontal flow using full width (1577px)
- **Process Flow**: Grid layout (3×2 or 4×2) maximizing space
- **Comparison**: Side-by-side columns with full height usage
- **Infographic**: Multi-section layout with visual hierarchy
- **Data Display**: Chart-like layouts with dense information

Generate complete, production-ready HTML that creates compelling, 
space-optimized visual representations of the provided content."""

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

    def _create_basic_html_timeline(self, content: str, topic: str) -> str:
        """Create a basic HTML timeline from text content"""
        return f"""<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; padding: 20px; 
                background: #f8f9fa; }}
        .timeline {{ max-width: 1200px; margin: 0 auto; }}
        .timeline-item {{ background: white; margin: 10px 0; padding: 15px; 
                         border-left: 4px solid #dc261e; 
                         box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .timeline-title {{ color: #dc261e; font-weight: bold; font-size: 18px; margin-bottom: 8px; }}
        .timeline-content {{ color: #404040; line-height: 1.6; }}
        h1 {{ color: #dc261e; text-align: center; margin-bottom: 30px; }}
    </style>
</head>
<body>
    <div class="timeline">
        <h1>{topic}</h1>
        <div class="timeline-item">
            <div class="timeline-title">Timeline Overview</div>
            <div class="timeline-content">{content}</div>
        </div>
    </div>
</body>
</html>"""

    def get_supported_visualization_types(self) -> List[str]:
        """
        Get list of supported visualization types

        Returns:
            List of supported visualization type names
        """
        return [
            "timeline",
            "process_flow",
            "comparison_chart",
            "infographic",
            "diagram",
            "metrics_dashboard",
            "roadmap",
            "workflow",
            "hierarchy",
            "before_after",
        ]

    def create_sample_visualizations(
        self, output_dir: str = "html_samples"
    ) -> Dict[str, str]:
        """
        Create sample HTML visualizations for testing

        Args:
            output_dir: Directory to save sample files

        Returns:
            Dictionary mapping visualization types to file paths
        """
        if not self.html_available:
            print("HTML renderer not available for sample generation")
            return {}

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        samples = {}

        # Timeline sample
        timeline_html = self.html_renderer.create_timeline_html(
            events=[
                {
                    "date": "2024 Q1",
                    "title": "Project Kickoff",
                    "description": "Requirements gathering and team formation",
                },
                {
                    "date": "2024 Q2",
                    "title": "Development Phase",
                    "description": "Core feature implementation",
                },
                {
                    "date": "2024 Q3",
                    "title": "Testing & QA",
                    "description": "Quality assurance and bug fixes",
                },
                {
                    "date": "2024 Q4",
                    "title": "Launch",
                    "description": "Product release and go-to-market",
                },
            ],
            title="Product Development Timeline",
            theme="ekona",
        )

        timeline_path = os.path.join(output_dir, "timeline_sample.html")
        with open(timeline_path, "w", encoding="utf-8") as f:
            f.write(timeline_html)
        samples["timeline"] = timeline_path

        # Process flow sample
        process_html = self.html_renderer.create_process_flow_html(
            steps=[
                {"title": "Analyze", "description": "Understand requirements"},
                {"title": "Design", "description": "Create solution architecture"},
                {"title": "Develop", "description": "Implement features"},
                {"title": "Test", "description": "Quality assurance"},
                {"title": "Deploy", "description": "Release to production"},
            ],
            title="Development Process",
            theme="ekona",
        )

        process_path = os.path.join(output_dir, "process_sample.html")
        with open(process_path, "w", encoding="utf-8") as f:
            f.write(process_html)
        samples["process_flow"] = process_path

        print(f"✅ Created {len(samples)} sample visualizations in {output_dir}")
        return samples

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
        Save HTML content to debug folder for inspection

        Args:
            html_content: The generated HTML content
            placeholder_name: Name of the placeholder
            topic: Presentation topic
            slide_number: Slide number
            original_content: Original text content
            suffix: Optional suffix for filename
        """
        try:
            timestamp = datetime.now().strftime("%H%M%S")
            safe_topic = "".join(
                c for c in topic if c.isalnum() or c in (" ", "-", "_")
            ).rstrip()
            safe_topic = safe_topic.replace(" ", "_")[:20]
            safe_placeholder = "".join(
                c for c in placeholder_name if c.isalnum() or c in ("-", "_")
            )[:30]

            filename = (
                f"slide_{slide_number:02d}_{safe_placeholder}_{timestamp}{suffix}.html"
            )
            filepath = self.debug_folder / filename

            # Create metadata for the HTML file
            metadata = {
                "timestamp": datetime.now().isoformat(),
                "slide_number": slide_number,
                "placeholder_name": placeholder_name,
                "topic": topic,
                "original_content": (
                    original_content[:500] + "..."
                    if len(original_content) > 500
                    else original_content
                ),
                "html_length": len(html_content),
                "file_type": "html_visualization",
            }

            # Save HTML file
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html_content)

            # Save metadata file
            metadata_filepath = filepath.with_suffix(".json")
            with open(metadata_filepath, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)

            print(f"    💾 Saved HTML debug file: {filename}")

        except Exception as e:
            print(f"    ⚠️ Failed to save HTML debug file: {e}")
