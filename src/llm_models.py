"""
LLM Models Module

Pydantic models for structured output from OpenAI API calls.
This ensures reliable, type-safe parsing of LLM responses.
"""

from typing import Dict, List, Optional, Union

from pydantic import BaseModel


class SlideSpec(BaseModel):
    """
    Enhanced specification for a single slide with detailed purpose instructions

    This model now includes comprehensive instructions for content generation
    and HTML visualization to ensure alignment throughout the pipeline.
    """

    layout_index: int
    slide_title: str
    slide_purpose: str
    is_html: bool = False  # Track whether this slide should use HTML visualization

    # Enhanced detailed specifications
    detailed_purpose: Optional[str] = (
        None  # Detailed explanation of what should be represented
    )
    content_structure: Optional[str] = None  # Specific content structure requirements
    html_requirements: Optional[str] = (
        None  # Specific HTML visualization requirements (when is_html=True)
    )
    visual_elements: Optional[str] = (
        None  # Required visual elements (icons, charts, tables, etc.)
    )
    key_information: Optional[List[str]] = (
        None  # Key information points that must be included
    )

    def get_complete_purpose(self) -> str:
        """
        Get the complete purpose specification including all details

        Returns:
            Combined purpose specification for content generation
        """
        purpose_parts = [self.slide_purpose]

        if self.detailed_purpose:
            purpose_parts.append(f"Detailed requirements: {self.detailed_purpose}")

        if self.content_structure:
            purpose_parts.append(f"Content structure: {self.content_structure}")

        if self.html_requirements and self.is_html:
            purpose_parts.append(f"HTML visualization: {self.html_requirements}")

        if self.visual_elements:
            purpose_parts.append(f"Visual elements: {self.visual_elements}")

        if self.key_information:
            purpose_parts.append(f"Key information: {', '.join(self.key_information)}")

        return " | ".join(purpose_parts)


class PresentationPlan(BaseModel):
    """Model for presentation planning response from LLM"""

    total_slides: int
    slides: List[SlideSpec]
    presentation_flow: str
    reasoning: str


class LayoutSelection(BaseModel):
    """Model for layout selection response from LLM"""

    selected_layouts: List[int]
    reasoning: str


class ChartSeries(BaseModel):
    """Model for a single chart data series"""

    name: str
    values: List[Union[int, float]]


class ChartData(BaseModel):
    """Model for chart data structure"""

    type: str
    title: str
    categories: List[str]
    series: List[ChartSeries]


class PlaceholderItem(BaseModel):
    """Single placeholder name-content pair"""

    name: str
    content: str


class SlideContentData(BaseModel):
    """Model for individual slide content - structured to avoid additionalProperties"""

    placeholders: List[PlaceholderItem]

    @property
    def placeholder_content(self) -> Dict[str, str]:
        """Convert placeholders list to dict for backward compatibility"""
        return {item.name: item.content for item in self.placeholders}


class PresentationContent(BaseModel):
    """Model for complete presentation content generation"""

    slide_contents: List[SlideContentData]
    presentation_summary: str
    key_points: List[str]
