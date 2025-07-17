"""
LLM Models Module

Pydantic models for structured output from OpenAI API calls.
This ensures reliable, type-safe parsing of LLM responses.
"""

from typing import Dict, List, Union

from pydantic import BaseModel


class SlideSpec(BaseModel):
    """Specification for a single slide"""

    layout_index: int
    slide_title: str
    slide_purpose: str


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
