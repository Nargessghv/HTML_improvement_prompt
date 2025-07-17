"""
Dynamic Pydantic Models Module

This module creates Pydantic models dynamically based on template layout analysis
to ensure LLM structured output matches exact placeholder names.
"""

from typing import Any, Dict, Type

from pydantic import BaseModel, Field, create_model


def create_placeholder_model(layout_info: Dict[str, Any]) -> Type[BaseModel]:
    """
    Create a dynamic Pydantic model based on layout placeholder names

    Args:
        layout_info: Layout information with placeholder details

    Returns:
        Dynamically created Pydantic model class
    """
    placeholders = layout_info.get("placeholders", [])

    if not placeholders:
        # Return empty model for layouts with no placeholders
        return create_model("EmptySlideContent", __base__=BaseModel)

    # Create field definitions for each placeholder
    field_definitions = {}

    for placeholder in placeholders:
        placeholder_name = placeholder["name"]
        placeholder_type = placeholder.get("type", 1)

        # Create field with exact placeholder name as key
        # Add description to help LLM understand what content to generate
        description = _generate_field_description(placeholder_name, placeholder_type)

        field_definitions[placeholder_name] = (str, Field(description=description))

    # Create the dynamic model with layout-specific name
    layout_name = layout_info.get("name", "Unknown").replace(" ", "_").replace("-", "_")
    model_name = f"SlideContent_{layout_name}_{layout_info.get('index', 0)}"

    # Create the model
    DynamicModel = create_model(model_name, __base__=BaseModel, **field_definitions)

    return DynamicModel


def create_presentation_models(
    layouts_info: Dict[int, Dict[str, Any]],
) -> Dict[int, Type[BaseModel]]:
    """
    Create dynamic Pydantic models for all layouts in a presentation template

    Args:
        layouts_info: Dictionary of layout information

    Returns:
        Dictionary mapping layout index to its dynamic Pydantic model
    """
    models = {}

    for layout_index, layout_info in layouts_info.items():
        model = create_placeholder_model(layout_info)
        models[layout_index] = model

    return models


def _generate_field_description(placeholder_name: str, placeholder_type: int) -> str:
    """
    Generate helpful description for LLM based on placeholder name and type

    Args:
        placeholder_name: Name of the placeholder
        placeholder_type: PowerPoint placeholder type (1=TITLE, 2=BODY, etc.)

    Returns:
        Description string for the field
    """
    # Map PowerPoint placeholder types to descriptions
    type_descriptions = {
        1: "slide title",
        2: "body text or subtitle",
        7: "text content",
        8: "chart description or data",
        18: "image description or caption",
    }

    base_description = type_descriptions.get(placeholder_type, "content")

    # Enhance description based on placeholder name
    name_lower = placeholder_name.lower()

    if "title" in name_lower:
        return f"Slide title for '{placeholder_name}'"
    if "subtitle" in name_lower:
        return f"Subtitle content for '{placeholder_name}'"
    if "presenter" in name_lower:
        return f"Presenter name and title for '{placeholder_name}'"
    if "chart" in name_lower:
        return f"Chart data and description for '{placeholder_name}'"
    if "picture" in name_lower or "image" in name_lower:
        return f"Image description and context for '{placeholder_name}'"
    if "animal" in name_lower:
        return f"Animal name for '{placeholder_name}'"
    if "text" in name_lower or "content" in name_lower:
        return f"Text content for '{placeholder_name}'"
    return f"Content for '{placeholder_name}' ({base_description})"


def get_model_for_layout(
    layout_index: int, models: Dict[int, Type[BaseModel]]
) -> Type[BaseModel]:
    """
    Get the appropriate Pydantic model for a specific layout

    Args:
        layout_index: Index of the layout
        models: Dictionary of layout models

    Returns:
        Pydantic model class for the layout
    """
    return models.get(layout_index, BaseModel)
