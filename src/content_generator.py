"""
Content Generator Module

This module orchestrates the content generation process by combining
layout analysis with LLM-based content creation.
"""

from typing import Any, Dict, List, Optional

from .layout_analyzer import LayoutAnalyzer
from .llm_client import LLMClient, SlideContent


class ContentGenerator:
    """Orchestrates the content generation process"""

    def __init__(self, template_path: str, openai_api_key: Optional[str] = None):
        """
        Initialize the content generator

        Args:
            template_path: Path to the PowerPoint template file
            openai_api_key: OpenAI API key (optional, can use environment variable)
        """
        self.template_path = template_path
        self.layout_analyzer = LayoutAnalyzer(template_path)
        self.llm_client = LLMClient(api_key=openai_api_key)
        self.layouts_info = {}

    def analyze_template(self) -> Dict[int, Dict[str, Any]]:
        """
        Analyze the template to understand available layouts

        Returns:
            Dictionary of layout information
        """
        self.layouts_info = self.layout_analyzer.analyze_all_layouts()
        return self.layouts_info

    def generate_presentation_plan(self, topic: str) -> List[int]:
        """
        Generate a presentation plan by selecting appropriate layouts

        Args:
            topic: The presentation topic

        Returns:
            List of layout indices to use for the presentation
        """
        if not self.layouts_info:
            self.analyze_template()

        # Use LLM to select appropriate layouts
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
            layout_indices: Specific layout indices to use (if None, will auto-select)

        Returns:
            List of SlideContent objects
        """
        if not self.layouts_info:
            self.analyze_template()

        # Use provided layouts or generate a plan
        if layout_indices is None:
            layout_indices = self.generate_presentation_plan(topic)

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

            # Generate content for this slide
            slide_content = self.llm_client.generate_slide_content(
                layout_info, topic, i, total_slides
            )

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
