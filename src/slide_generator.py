"""
Slide Generator Module

This module creates actual PowerPoint slides using the generated content
and the template structure.
"""

import os
from typing import Any, Dict, List, Optional

from pptx import Presentation
from pptx.enum.shapes import PP_PLACEHOLDER

from .chart_generator import ChartGenerator
from .content_generator import ContentGenerator
from .llm_client import SlideContent
from .markdown_formatter import MarkdownFormatter


class SlideGenerator:
    """Creates PowerPoint slides from generated content"""

    def __init__(self, template_path: str, openai_api_key: Optional[str] = None):
        """
        Initialize the slide generator

        Args:
            template_path: Path to the PowerPoint template file
            openai_api_key: OpenAI API key (optional, can use environment variable)
        """
        self.template_path = template_path
        self.content_generator = ContentGenerator(template_path)
        self.chart_generator = ChartGenerator()
        self.markdown_formatter = MarkdownFormatter()  # Initialize markdown formatter

    def create_presentation(
        self, topic: str, output_path: str, layout_indices: Optional[List[int]] = None
    ) -> str:
        """
        Create a complete PowerPoint presentation

        Args:
            topic: The presentation topic
            output_path: Path where to save the generated presentation
            layout_indices: Specific layout indices to use (optional)

        Returns:
            Path to the created presentation file
        """
        print(f"Creating presentation for topic: '{topic}'")

        # Generate content for all slides using the proven approach
        # The mapping fix handles custom placeholder names correctly
        slide_contents = self.content_generator.generate_slide_contents(
            topic, layout_indices
        )

        if not slide_contents:
            raise ValueError("No slide contents generated")

        # Create the presentation
        presentation = self._create_powerpoint_presentation(slide_contents)

        # Save the presentation
        full_output_path = self._ensure_output_path(output_path)
        presentation.save(full_output_path)

        print(f"Presentation saved to: {full_output_path}")

        # Print summary
        self.content_generator.print_generation_summary(topic, slide_contents)

        return full_output_path

    def create_slide_with_dynamic_content(
        self,
        presentation: Presentation,
        layout_index: int,
        topic: str,
        slide_spec: Optional[Any] = None,
        slide_number: int = 1,
        total_slides: int = 1,
    ) -> None:
        """
        Create a slide and generate content based on its actual placeholder names

        Args:
            presentation: PowerPoint presentation object
            layout_index: Index of the layout to use
            topic: The presentation topic
            slide_spec: Optional slide specification with title/purpose
            slide_number: Current slide number
            total_slides: Total number of slides
        """
        # Get the layout and create the slide
        layout = presentation.slide_layouts[layout_index]
        slide = presentation.slides.add_slide(layout)

        # Get the actual placeholder names from the created slide
        actual_placeholders = self._get_actual_placeholder_info(slide)

        if not actual_placeholders:
            print(
                f"  → Slide {slide_number} has no placeholders, skipping content generation"
            )
            return

        # Extract just the placeholder names for content generation
        placeholder_names = list(actual_placeholders.keys())
        print(f"  → Found actual placeholders: {placeholder_names}")

        # Generate content based on actual placeholder names
        if hasattr(self, "content_generator") and self.content_generator:
            content = self._generate_content_for_actual_placeholders(
                placeholder_names, topic, slide_spec, slide_number, total_slides
            )

            if content:
                # Populate placeholders with generated content
                self._populate_slide_with_actual_names(
                    slide, content, actual_placeholders
                )
            else:
                print(f"  → Warning: No content generated for slide {slide_number}")
        else:
            print(
                f"  → Warning: No content generator available for slide {slide_number}"
            )

    def _generate_content_for_actual_placeholders(
        self,
        placeholder_names: List[str],
        topic: str,
        slide_spec: Optional[Any],
        slide_number: int,
        total_slides: int,
    ) -> Optional[Dict[str, str]]:
        """
        Generate content specifically for the actual placeholder names found on a slide

        Args:
            placeholder_names: List of actual placeholder names from the slide
            topic: The presentation topic
            slide_spec: Optional slide specification
            slide_number: Current slide number
            total_slides: Total number of slides

        Returns:
            Dictionary mapping placeholder names to content
        """
        try:
            # Import here to avoid circular imports
            from .llm_client import LLMClient

            # Create a simple layout info structure for the LLM
            layout_info = {
                "name": f"Dynamic Layout {slide_number}",
                "placeholders": [{"name": name} for name in placeholder_names],
            }

            # Use LLM client to generate content
            llm_client = LLMClient()

            if slide_spec:
                slide_content = llm_client.generate_contextual_slide_content(
                    layout_info, topic, slide_spec, slide_number, total_slides
                )
            else:
                slide_content = llm_client.generate_slide_content(
                    layout_info, topic, slide_number, total_slides
                )

            return slide_content.content if slide_content else None

        except Exception as e:
            print(f"  → Error generating content: {e}")
            return None

    def _populate_slide_with_actual_names(
        self,
        slide,
        content: Dict[str, str],
        actual_placeholders: Dict[str, Dict[str, Any]],
    ) -> None:
        """
        Populate slide using actual placeholder objects (no name matching needed)

        Args:
            slide: PowerPoint slide object
            content: Dictionary mapping placeholder names to content
            actual_placeholders: Dictionary of actual placeholder info
        """
        for placeholder_name, text_content in content.items():
            if placeholder_name in actual_placeholders:
                placeholder_obj = actual_placeholders[placeholder_name]["placeholder"]
                self._set_placeholder_content(placeholder_obj, text_content)
                print(f"  ✓ Set content for '{placeholder_name}'")
            else:
                print(
                    f"  ✗ Warning: Placeholder '{placeholder_name}' not found in actual placeholders"
                )

    def _create_powerpoint_presentation(
        self, slide_contents: List[SlideContent]
    ) -> Presentation:
        """
        Create the actual PowerPoint presentation

        Args:
            slide_contents: List of slide content objects

        Returns:
            PowerPoint presentation object
        """
        # Load template
        presentation = Presentation(self.template_path)

        # Create slides for each content without clearing existing slides
        # This avoids XML manipulation issues
        for slide_content in slide_contents:
            self._add_slide_to_presentation(presentation, slide_content)

        return presentation

    def _add_slide_to_presentation(
        self, presentation: Presentation, slide_content: SlideContent
    ) -> None:
        """
        Add a single slide to the presentation

        Args:
            presentation: PowerPoint presentation object
            slide_content: Content for this slide
        """
        # Get the layout
        layout = presentation.slide_layouts[slide_content.layout_index]

        # Add slide with the specified layout
        slide = presentation.slides.add_slide(layout)

        # Get the actual placeholder names from the created slide
        actual_placeholders = self._get_actual_placeholder_info(slide)

        # If we have content to place, use it directly
        # If not, we might need to generate content based on actual placeholders
        if slide_content.content:
            # Use existing content with improved matching
            self._populate_slide_placeholders(slide, slide_content.content)
        elif actual_placeholders:
            # No content provided but slide has placeholders
            # This could happen if content generation was skipped
            print(
                f"  → Slide created with {len(actual_placeholders)} placeholders, "
                "no content"
            )

    def _get_actual_placeholder_info(self, slide) -> Dict[str, Dict[str, Any]]:
        """
        Get information about actual placeholders on a created slide

        Args:
            slide: PowerPoint slide object

        Returns:
            Dictionary mapping placeholder names to their info
        """
        placeholder_info = {}
        for placeholder in slide.placeholders:
            name = (
                placeholder.name or f"Placeholder_{placeholder.placeholder_format.idx}"
            )
            placeholder_info[name] = {
                "placeholder": placeholder,
                "type": placeholder.placeholder_format.type,
                "index": placeholder.placeholder_format.idx,
                "shape_type": placeholder.shape_type,
            }
        return placeholder_info

    def _populate_slide_placeholders(self, slide, content: Dict[str, str]) -> None:
        """
        Populate slide placeholders with content using intelligent mapping

        Args:
            slide: PowerPoint slide object
            content: Dictionary mapping placeholder names to content
        """
        # Get layout information for this slide to access custom placeholder mapping
        slide_layout_index = None
        for i, layout in enumerate(slide.slide_layout.slide_master.slide_layouts):
            if layout == slide.slide_layout:
                slide_layout_index = i
                break

        if slide_layout_index is not None and hasattr(self, "content_generator"):
            # Get layout info which has the custom name to index mapping
            layout_info = self.content_generator.layouts_info.get(slide_layout_index)
            if layout_info:
                self._populate_with_layout_mapping(slide, content, layout_info)
                return

        # Fallback to original method if no layout mapping available
        self._populate_with_name_matching(slide, content)

    def _populate_with_layout_mapping(
        self, slide, content: Dict[str, str], layout_info: Dict
    ) -> None:
        """
        Populate placeholders using layout analysis mapping (handles custom names)

        Args:
            slide: PowerPoint slide object
            content: Dictionary mapping custom placeholder names to content
            layout_info: Layout information with custom name to index mapping
        """
        # Create mapping from placeholder indices to placeholder objects
        placeholder_by_index = {}
        for placeholder in slide.placeholders:
            idx = placeholder.placeholder_format.idx
            placeholder_by_index[idx] = placeholder

        print("  → Mapping content using layout analysis:")

        # Map content using layout analysis custom name -> index mapping
        for layout_placeholder in layout_info.get("placeholders", []):
            custom_name = layout_placeholder["name"]
            placeholder_index = layout_placeholder["index"]

            if custom_name in content:
                if placeholder_index in placeholder_by_index:
                    placeholder_obj = placeholder_by_index[placeholder_index]
                    text_content = content[custom_name]
                    self._set_placeholder_content(placeholder_obj, text_content)
                    print(f"    ✓ '{custom_name}' → Index {placeholder_index}")
                else:
                    print(
                        f"    ✗ Index {placeholder_index} not found in slide for '{custom_name}'"
                    )
            else:
                print(f"    - No content for '{custom_name}'")

    def _populate_with_name_matching(self, slide, content: Dict[str, str]) -> None:
        """
        Fallback method using name matching (original approach)

        Args:
            slide: PowerPoint slide object
            content: Dictionary mapping placeholder names to content
        """
        # Create a mapping from placeholder names to placeholder objects
        placeholder_map = {}
        for placeholder in slide.placeholders:
            name = (
                placeholder.name or f"Placeholder_{placeholder.placeholder_format.idx}"
            )
            placeholder_map[name] = placeholder

        # Fill placeholders with content
        for placeholder_name, text_content in content.items():
            if placeholder_name in placeholder_map:
                placeholder = placeholder_map[placeholder_name]
                self._set_placeholder_content(placeholder, text_content)
            else:
                # Try to find placeholder by partial name match
                matched_placeholder = self._find_placeholder_by_partial_match(
                    placeholder_map, placeholder_name
                )
                if matched_placeholder:
                    self._set_placeholder_content(matched_placeholder, text_content)
                else:
                    print(f"Warning: Placeholder '{placeholder_name}' not found")

    def _find_placeholder_by_partial_match(
        self, placeholder_map: Dict[str, Any], target_name: str
    ) -> Optional[Any]:
        """
        Find placeholder by partial name matching

        Args:
            placeholder_map: Dictionary of placeholder names to objects
            target_name: Target placeholder name to find

        Returns:
            Placeholder object if found, None otherwise
        """
        target_lower = target_name.lower()

        # Try exact match first
        if target_name in placeholder_map:
            return placeholder_map[target_name]

        # Try case-insensitive match
        for name, placeholder in placeholder_map.items():
            if name.lower() == target_lower:
                return placeholder

        # Enhanced matching for common placeholder name patterns
        # Handle PowerPoint's automatic naming patterns
        for name, placeholder in placeholder_map.items():
            name_lower = name.lower()

            # Handle "Title" matching "Title 1"
            if target_lower == "title" and name_lower.startswith("title"):
                return placeholder

            # Handle "Subtitle" matching "Text Placeholder 2" (common for subtitle)
            if target_lower == "subtitle" and "text placeholder" in name_lower:
                return placeholder

            # Handle "Presenter" matching remaining text placeholders
            if target_lower == "presenter" and "text placeholder" in name_lower:
                # Try to find the last text placeholder for presenter
                continue

            # Handle content placeholders
            if (
                "content placeholder" in target_lower
                and "content placeholder" in name_lower
            ):
                return placeholder

            # Handle "Text Content" matching "Content Placeholder"
            if target_lower == "text content" and "content placeholder" in name_lower:
                return placeholder

            # Handle chart placeholders
            if (
                "chart placeholder" in target_lower
                and "chart placeholder" in name_lower
            ):
                return placeholder

            # Handle picture placeholders
            if "picture" in target_lower and "picture" in name_lower:
                return placeholder

            # Generic partial matching for other cases
            if target_lower in name_lower or name_lower in target_lower:
                return placeholder

        # Special handling for "Presenter" - use the last available text placeholder
        if target_lower == "presenter":
            text_placeholders = [
                (name, placeholder)
                for name, placeholder in placeholder_map.items()
                if "text placeholder" in name.lower()
            ]
            if text_placeholders:
                # Sort by name and take the last one (highest number)
                text_placeholders.sort(key=lambda x: x[0])
                return text_placeholders[-1][1]

        return None

    def _set_placeholder_content(self, placeholder, content: str) -> None:
        """
        Set content for a placeholder while preserving original formatting

        Args:
            placeholder: PowerPoint placeholder object
            content: Text content to set or chart data
        """
        try:
            # Check if this is a chart placeholder
            if (
                hasattr(placeholder, "placeholder_format")
                and placeholder.placeholder_format.type == PP_PLACEHOLDER.CHART
            ):

                # Try to create chart from content
                if self._create_chart_from_content(placeholder, content):
                    return  # Chart created successfully
                # If chart creation fails, fall through to text insertion

            if hasattr(placeholder, "text_frame"):
                # Text placeholder - preserve original formatting
                self._set_text_preserving_formatting(placeholder.text_frame, content)
            elif hasattr(placeholder, "text"):
                # Simple text placeholder
                placeholder.text = content
            else:
                print(
                    f"Warning: Unknown placeholder type for content: {content[:50]}..."
                )
        except Exception as e:
            print(f"Error setting placeholder content: {e}")

    def _create_chart_from_content(self, placeholder, content: str) -> bool:
        """
        Attempt to create a chart from content string

        Args:
            placeholder: Chart placeholder object
            content: Content string that might contain chart instructions

        Returns:
            True if chart was created successfully, False otherwise
        """
        try:
            # For now, create a sample chart based on content keywords
            # TODO: Parse actual chart data from LLM in future enhancement
            chart_data = self._parse_chart_content(content)
            return self.chart_generator.create_chart(placeholder, chart_data)

        except Exception as e:
            print(f"Error creating chart: {e}")
            return False

    def _parse_chart_content(self, content: str) -> Dict[str, Any]:
        """
        Parse chart content and create appropriate chart data

        Args:
            content: Text content describing the chart

        Returns:
            Dictionary with chart data structure
        """
        # Simple parsing logic - can be enhanced with LLM chart data generation
        content_lower = content.lower()

        # Determine chart type from content
        chart_type = "column"  # default
        if any(word in content_lower for word in ["pie", "distribution", "percentage"]):
            chart_type = "pie"
        elif any(word in content_lower for word in ["line", "trend", "over time"]):
            chart_type = "line"
        elif any(word in content_lower for word in ["bar", "horizontal"]):
            chart_type = "bar"

        # Create sample data based on content context
        if "growth" in content_lower or "increase" in content_lower:
            return {
                "type": chart_type,
                "title": "Growth Metrics",
                "categories": ["Q1", "Q2", "Q3", "Q4"],
                "series": [
                    {"name": "Actual", "values": [15, 25, 40, 55]},
                    {"name": "Target", "values": [20, 30, 45, 60]},
                ],
            }
        if "market" in content_lower or "share" in content_lower:
            return {
                "type": "pie",
                "title": "Market Distribution",
                "categories": ["Company A", "Company B", "Company C", "Others"],
                "series": [{"name": "Market Share", "values": [35, 25, 20, 20]}],
            }
        if "performance" in content_lower or "metrics" in content_lower:
            return {
                "type": chart_type,
                "title": "Performance Metrics",
                "categories": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
                "series": [{"name": "Performance", "values": [78, 82, 85, 88, 91, 95]}],
            }
        # Generic data
        return {
            "type": chart_type,
            "title": "Data Visualization",
            "categories": ["Category 1", "Category 2", "Category 3", "Category 4"],
            "series": [
                {"name": "Series 1", "values": [10, 20, 30, 40]},
                {"name": "Series 2", "values": [15, 25, 35, 45]},
            ],
        }

    def _set_text_preserving_formatting(self, text_frame, content: str) -> None:
        """
        Set text content with markdown formatting while preserving template styling

        Args:
            text_frame: PowerPoint text frame object
            content: Markdown-formatted text content to set
        """
        try:
            # Use markdown formatter to apply proper formatting
            self.markdown_formatter.format_text_frame(text_frame, content)
            print("  ✓ Applied markdown formatting to content")

        except Exception as e:
            print(f"Error applying markdown formatting: {e}")
            # Fallback to simple text setting
            text_frame.text = content

    def _capture_original_formatting(self, text_frame) -> dict:
        """
        Capture original formatting properties from the text frame

        Args:
            text_frame: PowerPoint text frame object

        Returns:
            Dictionary containing original formatting properties
        """
        original_format: Dict[str, Any] = {
            "font_name": None,
            "font_size": None,
            "bold": None,
            "italic": None,
            "color": None,
            "paragraph_format": None,
        }

        try:
            if text_frame.paragraphs:
                # Get formatting from first paragraph
                paragraph = text_frame.paragraphs[0]
                original_format["paragraph_format"] = {
                    "level": paragraph.level,
                    "alignment": (
                        paragraph.alignment if hasattr(paragraph, "alignment") else None
                    ),
                }

                # Get formatting from paragraph font
                if hasattr(paragraph, "font"):
                    para_font = paragraph.font
                    original_format["font_name"] = para_font.name
                    original_format["font_size"] = para_font.size
                    original_format["bold"] = para_font.bold
                    original_format["italic"] = para_font.italic
                    original_format["color"] = para_font.color

                # If paragraph font is None, try first run
                if paragraph.runs:
                    run = paragraph.runs[0]
                    if hasattr(run, "font"):
                        run_font = run.font
                        # Only override None values from paragraph
                        if original_format["font_name"] is None:
                            original_format["font_name"] = run_font.name
                        if original_format["font_size"] is None:
                            original_format["font_size"] = run_font.size
                        if original_format["bold"] is None:
                            original_format["bold"] = run_font.bold
                        if original_format["italic"] is None:
                            original_format["italic"] = run_font.italic
                        if original_format["color"] is None:
                            original_format["color"] = run_font.color

        except Exception:
            # If we can't capture formatting, return defaults
            pass

        return original_format

    def _add_formatted_content(
        self, text_frame, content: str, original_format: dict
    ) -> None:
        """
        Add content to text frame while applying original formatting

        Args:
            text_frame: PowerPoint text frame object
            content: Text content to add
            original_format: Original formatting properties to preserve
        """
        try:
            # Add a paragraph
            paragraph = (
                text_frame.paragraphs[0]
                if text_frame.paragraphs
                else text_frame.add_paragraph()
            )

            # Apply original paragraph formatting
            if original_format.get("paragraph_format"):
                para_format = original_format["paragraph_format"]
                if para_format.get("level") is not None:
                    paragraph.level = para_format["level"]
                if para_format.get("alignment") is not None:
                    paragraph.alignment = para_format["alignment"]

            # Set the text content
            paragraph.text = content

            # Apply original font formatting to runs if we have them
            if paragraph.runs and any(
                v is not None
                for v in [
                    original_format.get("font_name"),
                    original_format.get("font_size"),
                    original_format.get("bold"),
                    original_format.get("italic"),
                ]
            ):
                for run in paragraph.runs:
                    if hasattr(run, "font"):
                        font = run.font

                        # Apply captured formatting only if it was explicitly set
                        if original_format.get("font_name") is not None:
                            font.name = original_format["font_name"]
                        if original_format.get("font_size") is not None:
                            font.size = original_format["font_size"]
                        if original_format.get("bold") is not None:
                            font.bold = original_format["bold"]
                        if original_format.get("italic") is not None:
                            font.italic = original_format["italic"]
                        # Note: Color formatting is more complex and often theme-based
                        # so we'll let PowerPoint handle it via the template

        except Exception as e:
            print(f"Error applying formatting: {e}")
            # Fallback: just set the text
            if text_frame.paragraphs:
                text_frame.paragraphs[0].text = content
            else:
                text_frame.add_paragraph().text = content

    def _format_text_frame(self, text_frame) -> None:
        """
        Apply basic formatting to text frame (DEPRECATED - now preserved from template)

        Args:
            text_frame: PowerPoint text frame object
        """
        # This method is now deprecated as we preserve original formatting
        # Keeping it for backward compatibility but it does nothing
        pass

    def _ensure_output_path(self, output_path: str) -> str:
        """
        Ensure the output path has the correct extension and directory exists

        Args:
            output_path: Requested output path

        Returns:
            Full output path with proper extension
        """
        # Ensure .pptx extension
        if not output_path.lower().endswith(".pptx"):
            output_path += ".pptx"

        # Ensure directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        return output_path

    def preview_content(self, topic: str) -> str:
        """
        Generate and return a text preview of the presentation content

        Args:
            topic: The presentation topic

        Returns:
            String preview of the presentation
        """
        return self.content_generator.create_content_preview(topic)

    def get_available_layouts(self) -> Dict[int, Dict[str, Any]]:
        """
        Get information about available layouts in the template

        Returns:
            Dictionary of layout information
        """
        return self.content_generator.analyze_template()

    def print_template_analysis(self) -> None:
        """Print analysis of the template layouts"""
        self.content_generator.layout_analyzer.print_layout_summary()
