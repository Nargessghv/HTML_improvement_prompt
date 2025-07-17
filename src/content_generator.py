"""
Content Generator Module

This module orchestrates the content generation process by combining
layout analysis with LLM-based content creation.
"""

from typing import Any, Dict, List, Optional

from .dynamic_models import create_presentation_models
from .layout_analyzer import LayoutAnalyzer
from .llm_client import LLMClient, SlideContent
from .llm_models import SlideSpec


class ContentGenerator:
    """Orchestrates the content generation process"""

    def __init__(self, template_path: str):
        """
        Initialize ContentGenerator with template path

        Args:
            template_path: Path to PowerPoint template file
        """
        self.layout_analyzer = LayoutAnalyzer(template_path)
        self.llm_client = LLMClient()
        self.layouts_info = {}
        self.dynamic_models = {}  # Store dynamic Pydantic models for each layout

    def analyze_template(self) -> Dict[int, Dict[str, Any]]:
        """
        Analyze template layouts and create dynamic models

        Returns:
            Dictionary containing layout information
        """
        self.layouts_info = self.layout_analyzer.analyze_all_layouts()

        # Create dynamic Pydantic models for each layout
        self.dynamic_models = create_presentation_models(self.layouts_info)

        print(f"✅ Analyzed template: {len(self.layouts_info)} layouts")
        print("✅ Created dynamic models for perfect placeholder matching")

        return self.layouts_info

    def generate_intelligent_presentation_plan(self, topic: str) -> List[SlideSpec]:
        """
        Generate an intelligent presentation plan using LLM

        Args:
            topic: The presentation topic

        Returns:
            List of SlideSpec objects defining the presentation structure
        """
        if not self.layouts_info:
            self.analyze_template()

        # Use LLM to create intelligent presentation plan
        presentation_plan = self.llm_client.plan_presentation(self.layouts_info, topic)

        print(f"Presentation plan created: {len(presentation_plan)} slides")
        for i, slide_spec in enumerate(presentation_plan, 1):
            layout_name = self.layouts_info.get(slide_spec.layout_index, {}).get(
                "name", "Unknown"
            )
            print(f"  Slide {i}: {slide_spec.slide_title} (Layout: {layout_name})")

        return presentation_plan

    def generate_presentation_plan(self, topic: str) -> List[int]:
        """
        Generate a presentation plan by selecting appropriate layouts (DEPRECATED)

        This method is kept for backward compatibility.
        Use generate_intelligent_presentation_plan() for better results.

        Args:
            topic: The presentation topic

        Returns:
            List of layout indices to use for the presentation
        """
        if not self.layouts_info:
            self.analyze_template()

        # Use LLM to select appropriate layouts (old method)
        selected_layouts = self.llm_client.analyze_layouts_for_topic(
            self.layouts_info, topic
        )

        print(f"Selected layouts for '{topic}': {selected_layouts}")
        return selected_layouts

    def generate_slide_contents(
        self, topic: str, layout_indices: Optional[List[int]] = None
    ) -> List[SlideContent]:
        """
        Generate content for all slides in the presentation

        Args:
            topic: The presentation topic
            layout_indices: Specific layout indices to use
                           (if None, will use intelligent planning)

        Returns:
            List of SlideContent objects
        """
        if not self.layouts_info:
            self.analyze_template()

        # Use intelligent planning or provided layouts
        if layout_indices is None:
            print("🧠 Using intelligent LLM-based layout planning")
            # Use intelligent presentation planning
            presentation_plan = self.generate_intelligent_presentation_plan(topic)
            slide_contents = self._generate_contents_from_plan(topic, presentation_plan)
        else:
            print(f"📋 Using provided layout indices: {layout_indices}")
            if len(layout_indices) >= 5:
                max_check = min(5, len(layout_indices))
                is_sequential = all(
                    layout_indices[i] == layout_indices[i - 1] + 1
                    for i in range(1, max_check)
                )
                if is_sequential:
                    print("⚠️ WARNING: Sequential layout assignment detected!")
                    print("   Consider using intelligent planning instead")
                    print("   (set layout_indices=None)")

            # Use provided layout indices (backward compatibility)
            slide_contents = self._generate_contents_from_layouts(topic, layout_indices)

        return slide_contents

    def generate_slide_contents_with_dynamic_placeholders(
        self, topic: str, layout_indices: Optional[List[int]] = None
    ) -> List[SlideContent]:
        """
        Generate content using dynamic placeholder detection (recommended approach)

        This method creates slides first, then generates content based on the
        actual placeholder names found on each slide. This eliminates mapping
        issues with custom placeholder names.

        Args:
            topic: The presentation topic
            layout_indices: Specific layout indices to use
                           (if None, will use intelligent planning)

        Returns:
            List of SlideContent objects with actual placeholder names
        """
        if not self.layouts_info:
            self.analyze_template()

        # Use intelligent planning or provided layouts
        if layout_indices is None:
            # Use intelligent presentation planning
            presentation_plan = self.generate_intelligent_presentation_plan(topic)
            return self._generate_dynamic_contents_from_plan(topic, presentation_plan)
        # Use provided layout indices with dynamic placeholder detection
        return self._generate_dynamic_contents_from_layouts(topic, layout_indices)

    def _generate_contents_from_plan(
        self, topic: str, presentation_plan: List[SlideSpec]
    ) -> List[SlideContent]:
        """
        Generate content based on intelligent presentation plan using dynamic models

        Args:
            topic: The presentation topic
            presentation_plan: List of SlideSpec objects

        Returns:
            List of SlideContent objects
        """
        slide_contents = []
        total_slides = len(presentation_plan)

        print(f"Generating content for {total_slides} slides...")

        for i, slide_spec in enumerate(presentation_plan, 1):
            # Validate layout index
            if slide_spec.layout_index not in self.layouts_info:
                print(
                    f"Warning: Layout {slide_spec.layout_index} not found. Skipping..."
                )
                continue

            layout_info = self.layouts_info[slide_spec.layout_index]
            print(
                f"Generating slide {i}/{total_slides}: {slide_spec.slide_title} "
                f"(Layout: {layout_info['name']})..."
            )

            # Check if layout has any placeholders
            placeholders = layout_info.get("placeholders", [])
            if not placeholders:
                print("  → Layout has no placeholders, skipping content generation")
                # Create empty content for layouts with no placeholders
                slide_content = SlideContent(
                    layout_index=slide_spec.layout_index,
                    content={},  # Empty content dictionary
                )
                slide_contents.append(slide_content)
                continue

            # Get dynamic model for this layout
            dynamic_model = self.dynamic_models.get(slide_spec.layout_index)

            if dynamic_model:
                print("  → Using dynamic model for exact placeholder matching")
                # Generate content using dynamic model for perfect matching
                slide_content = self.llm_client.generate_contextual_slide_content(
                    layout_info, topic, slide_spec, i, total_slides, dynamic_model
                )
            else:
                print("  → No dynamic model found, using fallback method")
                # Generate content for this specific slide with its purpose
                slide_content = self.llm_client.generate_contextual_slide_content(
                    layout_info, topic, slide_spec, i, total_slides
                )

            if slide_content:
                slide_contents.append(slide_content)

        return slide_contents

    def _generate_dynamic_contents_from_plan(
        self, topic: str, presentation_plan: List[SlideSpec]
    ) -> List[SlideContent]:
        """
        Generate content using dynamic placeholder detection from presentation plan

        Args:
            topic: The presentation topic
            presentation_plan: List of SlideSpec objects

        Returns:
            List of SlideContent objects
        """
        from pptx import Presentation

        # Load template to inspect actual slide placeholders
        temp_presentation = Presentation(self.layout_analyzer.template_path)
        slide_contents = []
        total_slides = len(presentation_plan)

        print(
            f"Generating content using dynamic placeholder detection for "
            f"{total_slides} slides..."
        )

        for i, slide_spec in enumerate(presentation_plan, 1):
            # Validate layout index
            if slide_spec.layout_index not in self.layouts_info:
                print(
                    f"Warning: Layout {slide_spec.layout_index} not found. Skipping..."
                )
                continue

            layout_info = self.layouts_info[slide_spec.layout_index]
            print(
                f"Generating slide {i}/{total_slides}: {slide_spec.slide_title} "
                f"(Layout: {layout_info['name']})..."
            )

            # Create a temporary slide to inspect actual placeholder names
            layout = temp_presentation.slide_layouts[slide_spec.layout_index]
            temp_slide = temp_presentation.slides.add_slide(layout)

            # Get actual placeholder names
            actual_placeholder_names = []
            for placeholder in temp_slide.placeholders:
                name = (
                    placeholder.name
                    or f"Placeholder_{placeholder.placeholder_format.idx}"
                )
                actual_placeholder_names.append(name)

            if not actual_placeholder_names:
                print("  → Layout has no placeholders, creating empty content")
                slide_content = SlideContent(
                    layout_index=slide_spec.layout_index, content={}
                )
                slide_contents.append(slide_content)
                continue

            print(f"  → Actual placeholders: {actual_placeholder_names}")

            # Generate content using actual placeholder names
            content = self._generate_content_for_actual_names(
                actual_placeholder_names, topic, slide_spec, i, total_slides
            )

            if content:
                slide_content = SlideContent(
                    layout_index=slide_spec.layout_index, content=content
                )
                slide_contents.append(slide_content)

        return slide_contents

    def _generate_content_for_actual_names(
        self,
        placeholder_names: List[str],
        topic: str,
        slide_spec: SlideSpec,
        slide_number: int,
        total_slides: int,
    ) -> Optional[Dict[str, str]]:
        """
        Generate content for actual placeholder names (no mapping needed)

        Args:
            placeholder_names: List of actual placeholder names from slide
            topic: The presentation topic
            slide_spec: Slide specification with title/purpose
            slide_number: Current slide number
            total_slides: Total number of slides

        Returns:
            Dictionary mapping actual placeholder names to content
        """
        # Create layout info using actual placeholder names
        layout_info = {
            "name": f"Dynamic Layout for Slide {slide_number}",
            "placeholders": [{"name": name} for name in placeholder_names],
        }

        # Generate content using actual names
        slide_content = self.llm_client.generate_contextual_slide_content(
            layout_info, topic, slide_spec, slide_number, total_slides
        )

        return slide_content.content if slide_content else None

    def _generate_contents_from_layouts(
        self, topic: str, layout_indices: List[int]
    ) -> List[SlideContent]:
        """
        Generate content from layout indices using
        dynamic models (backward compatibility)

        Args:
            topic: The presentation topic
            layout_indices: List of layout indices

        Returns:
            List of SlideContent objects
        """
        slide_contents = []
        total_slides = len(layout_indices)

        print(f"Generating content for {total_slides} slides...")

        for i, layout_index in enumerate(layout_indices, 1):
            # Validate layout index
            if layout_index not in self.layouts_info:
                print(f"Warning: Layout {layout_index} not found. Skipping...")
                continue

            layout_info = self.layouts_info[layout_index]
            print(
                f"Generating slide {i}/{total_slides} "
                f"(Layout: {layout_info['name']})..."
            )

            # Check if layout has any placeholders
            placeholders = layout_info.get("placeholders", [])
            if not placeholders:
                print("  → Layout has no placeholders, skipping content generation")
                # Create empty content for layouts with no placeholders
                slide_content = SlideContent(
                    layout_index=layout_index, content={}  # Empty content dictionary
                )
                slide_contents.append(slide_content)
                continue

            # Get dynamic model for this layout
            dynamic_model = self.dynamic_models.get(layout_index)

            if dynamic_model:
                print("  → Using dynamic model for exact placeholder matching")
                # Generate content using dynamic model
                slide_content = self.llm_client.generate_slide_content(
                    layout_info, topic, i, total_slides, dynamic_model
                )
            else:
                print("  → No dynamic model found, using fallback method")
                # Generate content for this slide (old method)
                slide_content = self.llm_client.generate_slide_content(
                    layout_info, topic, i, total_slides
                )

            if slide_content:
                slide_contents.append(slide_content)

        return slide_contents

    def _generate_dynamic_contents_from_layouts(
        self, topic: str, layout_indices: List[int]
    ) -> List[SlideContent]:
        """
        Generate content using layout analysis custom names, then map to actual slides

        Args:
            topic: The presentation topic
            layout_indices: List of layout indices to use

        Returns:
            List of SlideContent objects
        """
        slide_contents = []
        total_slides = len(layout_indices)

        print(
            f"Generating content using custom placeholder names for {total_slides} slides..."
        )

        for i, layout_index in enumerate(layout_indices, 1):
            # Validate layout index
            if layout_index not in self.layouts_info:
                print(f"Warning: Layout {layout_index} not found. Skipping...")
                continue

            layout_info = self.layouts_info[layout_index]
            print(
                f"Generating slide {i}/{total_slides} "
                f"(Layout: {layout_info['name']})..."
            )

            placeholders = layout_info.get("placeholders", [])
            if not placeholders:
                print("  → Layout has no placeholders, creating empty content")
                slide_content = SlideContent(layout_index=layout_index, content={})
                slide_contents.append(slide_content)
                continue

            # Show the custom placeholder names from layout analysis
            custom_names = [p["name"] for p in placeholders]
            print(f"  → Layout placeholders (custom names): {custom_names}")

            # Generate content using the layout analysis (which has custom names)
            slide_content = self.llm_client.generate_slide_content(
                layout_info, topic, i, total_slides
            )

            if slide_content:
                slide_contents.append(slide_content)

        return slide_contents

    def get_layout_suggestions(self, topic: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get layout suggestions organized by purpose

        Args:
            topic: The presentation topic

        Returns:
            Dictionary of layouts organized by purpose
        """
        if not self.layouts_info:
            self.analyze_template()

        suggestions = {
            "title_slide": self.layout_analyzer.get_layout_by_purpose("title_slide"),
            "content": self.layout_analyzer.get_layout_by_purpose("content"),
            "image_content": self.layout_analyzer.get_layout_by_purpose(
                "image_content"
            ),
            "data_presentation": self.layout_analyzer.get_layout_by_purpose(
                "data_presentation"
            ),
            "general": self.layout_analyzer.get_layout_by_purpose("general"),
        }

        return suggestions

    def print_generation_summary(
        self, topic: str, slide_contents: List[SlideContent]
    ) -> None:
        """
        Print a summary of the generated content

        Args:
            topic: The presentation topic
            slide_contents: List of generated slide contents
        """
        print("\n=== PRESENTATION GENERATION SUMMARY ===")
        print(f"Topic: {topic}")
        print(f"Total slides: {len(slide_contents)}")
        print()

        for i, slide_content in enumerate(slide_contents, 1):
            layout_info = self.layouts_info[slide_content.layout_index]
            print(
                f"Slide {i}: {layout_info['name']} "
                f"(Layout {slide_content.layout_index})"
            )

            for placeholder_name, content in slide_content.content.items():
                # Truncate long content for summary
                display_content = content[:60] + "..." if len(content) > 60 else content
                print(f"  - {placeholder_name}: {display_content}")
            print()

    def create_content_preview(self, topic: str) -> str:
        """
        Create a text preview of the generated content

        Args:
            topic: The presentation topic

        Returns:
            String containing a preview of the presentation
        """
        slide_contents = self.generate_slide_contents(topic)

        preview = f"PRESENTATION PREVIEW: {topic}\n"
        preview += "=" * 50 + "\n\n"

        for i, slide_content in enumerate(slide_contents, 1):
            layout_info = self.layouts_info[slide_content.layout_index]
            preview += f"Slide {i}: {layout_info['name']}\n"
            preview += "-" * 30 + "\n"

            for placeholder_name, content in slide_content.content.items():
                preview += f"{placeholder_name}: {content}\n"

            preview += "\n"

        return preview
