"""
Slide Generation State Module

Contains the state object that flows through the agent workflow.
Tracks all data needed for slide generation across different agent steps.
"""

from typing import Any, Dict, List, Optional, TypedDict

from .llm_client import SlideContent
from .llm_models import SlideSpec


class SlideGenerationState(TypedDict):
    """
    State object that flows through the agent workflow

    Tracks all data needed for slide generation across different agent steps
    """

    # Input parameters
    topic: str
    template_path: str
    template_folder_path: Optional[
        str
    ]  # Path to template folder for locked backgrounds
    output_path: str
    layout_indices: Optional[List[int]]
    title: Optional[str]
    approved_outline: Optional[Dict[str, Any]]  # Interactive planning outline

    # Workflow state
    current_step: str
    error_message: Optional[str]
    retry_count: int
    html_refinement_iteration: int
    html_refinement_slide_index: Optional[int]
    html_slides_to_refine_queue: Optional[list[int]]
    refinement_id: Optional[str]  # Add this line

    # Analysis results
    layouts_info: Optional[Dict[int, Dict[str, Any]]]
    dynamic_models: Optional[Dict[int, Any]]

    # Planning results
    presentation_plan: Optional[List[SlideSpec]]
    selected_layouts: Optional[List[int]]

    # Content generation results
    slide_contents: Optional[List[SlideContent]]

    # Icon validation results
    icon_errors: Optional[List[str]]
    icon_corrections: Optional[Dict[str, str]]
    needs_icon_retry: bool
    needs_html_refinement: bool

    # Image generation results
    image_prompts: Optional[Dict[int, str]]  # Detailed prompts for each slide
    generated_images: Optional[Dict[int, Dict[str, Any]]]
    refined_images: Optional[Dict[int, Dict[str, Any]]]
    needs_image_refinement: bool

    # Final output
    presentation_path: Optional[str]
    success: bool

    # Monitoring context
    monitor_trace: Optional[Any]

    # Project tracking for Supabase integration
    project_id: Optional[str]