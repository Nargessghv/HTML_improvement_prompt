"""
Layout Analyzer Module

This module analyzes PowerPoint slide layouts to understand their structure
and available placeholders for content generation.
"""

from typing import Any, Dict, List

from pptx import Presentation


class LayoutAnalyzer:
    """Analyzes PowerPoint slide layouts and their placeholders"""

    def __init__(self, template_path: str):
        """
        Initialize the layout analyzer with a template file

        Args:
            template_path: Path to the PowerPoint template file
        """
        self.template_path = template_path
        self.presentation = Presentation(template_path)
        self.layouts_info = {}

    def analyze_all_layouts(self) -> Dict[int, Dict[str, Any]]:
        """
        Analyze all slide layouts in the template

        Returns:
            Dictionary with layout index as key and layout info as value
        """
        for idx, layout in enumerate(self.presentation.slide_layouts):
            self.layouts_info[idx] = self._analyze_single_layout(idx, layout)

        return self.layouts_info

    def _analyze_single_layout(self, layout_index: int, layout) -> Dict[str, Any]:
        """
        Analyze a single slide layout

        Args:
            layout_index: Index of the layout
            layout: The slide layout object

        Returns:
            Dictionary containing layout information
        """
        layout_info = {
            "name": layout.name,
            "index": layout_index,
            "placeholders": [],
            "suitable_for": self._determine_layout_purpose(layout),
        }

        # Analyze placeholders directly from layout to preserve custom names and instructions
        for placeholder in layout.placeholders:
            # Use the custom name set in Selection Pane, fallback to generated name
            custom_name = (
                placeholder.name or f"Placeholder_{placeholder.placeholder_format.idx}"
            )

            # Extract instructional text from placeholder (if any)
            instructional_text = self._extract_placeholder_instructions(placeholder)

            # Calculate placeholder dimensions in pixels
            EMU_PER_INCH = 914400
            DPI = 96
            EMU_PER_PIXEL = EMU_PER_INCH / DPI
            
            width_px = int(placeholder.width.emu / EMU_PER_PIXEL)
            height_px = int(placeholder.height.emu / EMU_PER_PIXEL)

            placeholder_info = {
                "index": placeholder.placeholder_format.idx,
                "type": placeholder.placeholder_format.type,
                "name": custom_name,
                "shape_type": placeholder.shape_type,
                "instructions": instructional_text,  # Add instructional text
                "width_px": width_px,  # Add pixel width
                "height_px": height_px,  # Add pixel height
                "aspect_ratio": round(width_px / height_px, 2) if height_px > 0 else 1.0,
            }
            layout_info["placeholders"].append(placeholder_info)

        # Note: Using direct layout analysis preserves custom names and instructions

        return layout_info

    def _extract_placeholder_instructions(self, placeholder) -> str:
        """
        Extract instructional text from a placeholder in the slide master

        Args:
            placeholder: PowerPoint placeholder object

        Returns:
            Instructional text string, or empty string if none found
        """
        try:
            # Try to get text from the placeholder's text frame
            if hasattr(placeholder, "text_frame") and placeholder.text_frame:
                if placeholder.text_frame.text:
                    instruction_text = placeholder.text_frame.text.strip()

                    # Filter out generic PowerPoint defaults
                    generic_texts = [
                        "Click to edit Master title style",
                        "Click to edit Master text styles",
                        "",
                    ]

                    # Return instruction text if it's not a generic default
                    if instruction_text and instruction_text not in generic_texts:
                        return instruction_text

            elif hasattr(placeholder, "text") and placeholder.text:
                instruction_text = placeholder.text.strip()
                if instruction_text:
                    return instruction_text

        except Exception:
            # If we can't read the text, that's fine - just continue without instructions
            pass

        return ""  # Return empty string if no instructional text found

    def _determine_layout_purpose(self, layout) -> List[str]:
        """
        Determine what type of content this layout is suitable for

        Args:
            layout: The slide layout object

        Returns:
            List of strings describing layout purposes
        """
        purposes = []
        placeholder_types = []

        for placeholder in layout.placeholders:
            placeholder_types.append(placeholder.placeholder_format.type)

        # Determine purpose based on placeholder types
        if 1 in placeholder_types:  # Title placeholder
            purposes.append("title_slide")
        if 2 in placeholder_types:  # Body/content placeholder
            purposes.append("content")
        if 8 in placeholder_types:  # Picture placeholder
            purposes.append("image_content")
        if 14 in placeholder_types:  # Table placeholder
            purposes.append("data_presentation")

        # If no specific types found, mark as general content
        if not purposes:
            purposes.append("general")

        return purposes

    def get_layout_by_purpose(self, purpose: str) -> List[Dict[str, Any]]:
        """
        Get layouts suitable for a specific purpose

        Args:
            purpose: The purpose to filter by

        Returns:
            List of layout information dictionaries
        """
        if not self.layouts_info:
            self.analyze_all_layouts()

        suitable_layouts = []
        for layout_info in self.layouts_info.values():
            if purpose in layout_info["suitable_for"]:
                suitable_layouts.append(layout_info)

        return suitable_layouts

    def print_layout_summary(self) -> None:
        """Print a summary of all analyzed layouts"""
        if not self.layouts_info:
            self.analyze_all_layouts()

        print("=== SLIDE LAYOUT ANALYSIS ===")
        for idx, layout_info in self.layouts_info.items():
            print(f"\nLayout {idx}: {layout_info['name']}")
            print(f"  Suitable for: {', '.join(layout_info['suitable_for'])}")
            print(f"  Placeholders ({len(layout_info['placeholders'])}):")

            for placeholder in layout_info["placeholders"]:
                print(
                    f"    - Index: {placeholder['index']}, "
                    f"Type: {placeholder['type']}, "
                    f"Name: '{placeholder['name']}'"
                )
