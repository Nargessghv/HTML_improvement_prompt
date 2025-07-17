"""
LLM Models Module

Pydantic models for structured output from OpenAI API calls.
This ensures reliable, type-safe parsing of LLM responses.
"""

from typing import Dict, List

from pydantic import BaseModel


class LayoutSelection(BaseModel):
    """Model for layout selection response from LLM"""

    selected_layouts: List[int]
    reasoning: str


class SlideContentData(BaseModel):
    """Model for individual slide content"""

    placeholder_content: Dict[str, str]


class PresentationContent(BaseModel):
    """Model for complete presentation content generation"""

    slide_contents: List[SlideContentData]
    presentation_summary: str
    key_points: List[str]
