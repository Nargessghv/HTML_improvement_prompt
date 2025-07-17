"""
Slide Generator Module

This module creates actual PowerPoint slides using the generated content
and the template structure.
"""

import os
from typing import Any, Dict, List, Optional

from pptx import Presentation

from .content_generator import ContentGenerator
from .llm_client import SlideContent


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
        self.content_generator = ContentGenerator(template_path, openai_api_key)

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

        # Generate content for all slides
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

        # Fill in the placeholders
        self._populate_slide_placeholders(slide, slide_content.content)

    def _populate_slide_placeholders(self, slide, content: Dict[str, str]) -> None:
        """
        Populate slide placeholders with content

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

        # Try partial matches
        for name, placeholder in placeholder_map.items():
            if target_lower in name.lower() or name.lower() in target_lower:
                return placeholder

        return None

    def _set_placeholder_content(self, placeholder, content: str) -> None:
        """
        Set content for a placeholder while preserving original formatting

        Args:
            placeholder: PowerPoint placeholder object
            content: Text content to set
        """
        try:
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

    def _set_text_preserving_formatting(self, text_frame, content: str) -> None:
        """
        Set text content while preserving the original template formatting

        Args:
            text_frame: PowerPoint text frame object
            content: Text content to set
        """
        try:
            # Store original formatting from first paragraph/run before clearing
            original_format = self._capture_original_formatting(text_frame)

            # Clear existing text but preserve paragraph structure
            text_frame.clear()

            # Add our content with preserved formatting
            self._add_formatted_content(text_frame, content, original_format)

        except Exception as e:
            print(f"Error preserving formatting: {e}")
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
