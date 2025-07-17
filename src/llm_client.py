"""
LLM Client Module

This module handles communication with OpenAI's API for content generation.
"""

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

from .llm_models import LayoutSelection, PresentationPlan, SlideSpec

# Load environment variables
load_dotenv()


@dataclass
class SlideContent:
    """Data class for slide content"""

    layout_index: int
    content: Dict[str, str]  # placeholder_name -> content


class LLMClient:
    """Client for OpenAI API communication"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Initialize the LLM client

        Args:
            api_key: OpenAI API key (if None, will try to get from environment)
            model: OpenAI model to use
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "2000"))

        if not self.api_key:
            raise ValueError(
                "OpenAI API key not found. "
                "Set OPENAI_API_KEY in .env file or pass as parameter"
            )

        self.client = OpenAI(api_key=self.api_key)

    def analyze_layouts_for_topic(
        self, layouts_info: Dict[int, Dict[str, Any]], topic: str
    ) -> List[int]:
        """
        Ask LLM to select appropriate layouts for the given topic

        Args:
            layouts_info: Dictionary of layout information
            topic: The presentation topic

        Returns:
            List of layout indices to use
        """
        prompt = self._create_layout_selection_prompt(layouts_info, topic)

        try:
            # Try structured output first (for compatible OpenAI endpoints)
            try:
                response = self.client.chat.completions.parse(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self._get_layout_system_prompt()},
                        {"role": "user", "content": prompt},
                    ],
                    response_format=LayoutSelection,
                    max_tokens=self.max_tokens,
                    temperature=0.7,
                )

                # Extract layout indices from structured response
                if response.choices[0].message.parsed:
                    selection = response.choices[0].message.parsed
                    print(f"Layout selection reasoning: {selection.reasoning}")
                    return selection.selected_layouts
                print("Warning: No structured response received")
                return list(layouts_info.keys())[:3]  # Fallback

            except Exception:
                print("Structured output not supported, falling back to JSON mode")

                # Fallback to JSON mode for Azure OpenAI or older endpoints
                json_prompt = (
                    prompt + "\n\nRespond in valid JSON format: "
                    '{"selected_layouts": [0,1,2], "reasoning": "explanation"}'
                )

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self._get_layout_system_prompt()},
                        {"role": "user", "content": json_prompt},
                    ],
                    max_tokens=self.max_tokens,
                    temperature=0.7,
                )

                content = response.choices[0].message.content
                if content:
                    return self._parse_layout_selection(content)
                return list(layouts_info.keys())[:3]

        except Exception as e:
            print(f"Error in layout selection: {e}")
            # Fallback: return first few layouts
            return list(layouts_info.keys())[:3]

    def generate_slide_content(
        self,
        layout_info: Dict[str, Any],
        topic: str,
        slide_number: int,
        total_slides: int,
        dynamic_model: Optional[Any] = None,
    ) -> Optional[SlideContent]:
        """
        Generate content for a single slide using dynamic models for perfect matching

        Args:
            layout_info: Information about the slide layout
            topic: The presentation topic
            slide_number: Current slide number (1-indexed)
            total_slides: Total number of slides in presentation
            dynamic_model: Dynamic Pydantic model for this layout (optional)

        Returns:
            SlideContent object or None if generation fails
        """
        prompt = self._create_content_generation_prompt(
            layout_info, topic, slide_number, total_slides
        )

        try:
            # Use dynamic model if provided for perfect placeholder matching
            if dynamic_model:
                return self._generate_with_dynamic_model(
                    prompt, dynamic_model, layout_info, topic
                )
            # Fallback to original method
            return self._generate_with_original_method(
                prompt, layout_info, topic, slide_number
            )

        except Exception as e:
            print(f"Error generating content for slide {slide_number}: {e}")
            return self._create_fallback_content(layout_info, topic)

    def _generate_with_dynamic_model(
        self, prompt: str, dynamic_model: Any, layout_info: Dict[str, Any], topic: str
    ) -> Optional[SlideContent]:
        """
        Generate content using dynamic Pydantic model for exact placeholder matching

        Args:
            prompt: Content generation prompt
            dynamic_model: Dynamic Pydantic model class
            layout_info: Layout information
            topic: Presentation topic

        Returns:
            SlideContent object or None
        """
        try:
            # Try structured output with dynamic model
            response = self.client.chat.completions.parse(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_dynamic_content_system_prompt(),
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format=dynamic_model,
                max_tokens=self.max_tokens,
                temperature=0.8,
            )

            if response.choices[0].message.parsed:
                parsed_data = response.choices[0].message.parsed

                # Convert dynamic model instance to dictionary
                content_dict = {}
                for field_name in dynamic_model.model_fields.keys():
                    content_dict[field_name] = getattr(parsed_data, field_name, "")

                print(
                    f"  ✅ Dynamic model generated content for: {list(content_dict.keys())}"
                )

                return SlideContent(
                    layout_index=layout_info["index"],
                    content=content_dict,
                )
            print("Warning: No structured response from dynamic model")
            return None

        except Exception as e:
            print(f"Dynamic model generation failed: {e}")
            return None

    def _generate_with_original_method(
        self, prompt: str, layout_info: Dict[str, Any], topic: str, slide_number: int
    ) -> Optional[SlideContent]:
        """
        Fallback to original generation method

        Args:
            prompt: Content generation prompt
            layout_info: Layout information
            topic: Presentation topic
            slide_number: Slide number

        Returns:
            SlideContent object or None
        """
        # This is the original implementation
        try:
            # Try structured output first (for compatible OpenAI endpoints)
            try:
                from .llm_models import SlideContentData

                response = self.client.chat.completions.parse(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": self._get_content_system_prompt(),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    response_format=SlideContentData,
                    max_tokens=self.max_tokens,
                    temperature=0.8,
                )

                # Extract content from structured response
                if response.choices[0].message.parsed:
                    slide_data = response.choices[0].message.parsed
                    return SlideContent(
                        layout_index=layout_info["index"],
                        content=slide_data.placeholder_content,
                    )
                print(f"Warning: No structured response for slide {slide_number}")
                return self._create_fallback_content(layout_info, topic)

            except Exception:
                print(f"Structured output not supported for slide {slide_number}")
                print("Falling back to JSON mode")

                # Fallback to JSON mode
                json_prompt = (
                    prompt + "\n\nRespond in valid JSON format with placeholder "
                    "names as keys and content as values."
                )

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": self._get_content_system_prompt(),
                        },
                        {"role": "user", "content": json_prompt},
                    ],
                    max_tokens=self.max_tokens,
                    temperature=0.8,
                )

                content = response.choices[0].message.content
                if content:
                    parsed_content = self._parse_slide_content(content, layout_info)
                    return SlideContent(
                        layout_index=layout_info["index"],
                        content=parsed_content,
                    )
                return self._create_fallback_content(layout_info, topic)

        except Exception as e:
            print(f"Error in original method for slide {slide_number}: {e}")
            return self._create_fallback_content(layout_info, topic)

    def generate_contextual_slide_content(
        self,
        layout_info: Dict[str, Any],
        topic: str,
        slide_spec: SlideSpec,
        slide_number: int,
        total_slides: int,
        dynamic_model: Optional[Any] = None,
    ) -> Optional[SlideContent]:
        """
        Generate content for a specific slide with contextual awareness using dynamic models

        Args:
            layout_info: Information about the slide layout
            topic: The overall presentation topic
            slide_spec: Specification for this particular slide
            slide_number: Current slide number (1-indexed)
            total_slides: Total number of slides in presentation
            dynamic_model: Dynamic Pydantic model for exact placeholder matching

        Returns:
            SlideContent object or None if generation fails
        """
        prompt = self._create_contextual_content_prompt(
            layout_info, topic, slide_spec, slide_number, total_slides
        )

        try:
            # Use dynamic model if provided for perfect placeholder matching
            if dynamic_model:
                return self._generate_with_dynamic_model(
                    prompt, dynamic_model, layout_info, topic
                )
            # Fallback to original contextual method
            return self._generate_contextual_with_original_method(
                prompt, layout_info, topic, slide_spec, slide_number, total_slides
            )

        except Exception as e:
            print(f"Error generating contextual content for slide {slide_number}: {e}")
            return self._create_fallback_content(layout_info, topic)

    def _generate_contextual_with_original_method(
        self,
        prompt: str,
        layout_info: Dict[str, Any],
        topic: str,
        slide_spec: SlideSpec,
        slide_number: int,
        total_slides: int,
    ) -> Optional[SlideContent]:
        """
        Original contextual generation method as fallback

        Args:
            prompt: Content generation prompt
            layout_info: Layout information
            topic: Presentation topic
            slide_spec: Slide specification
            slide_number: Slide number
            total_slides: Total slides

        Returns:
            SlideContent object or None
        """
        try:
            # Try structured output first
            try:
                from .llm_models import SlideContentData

                response = self.client.chat.completions.parse(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": self._get_content_system_prompt(),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    response_format=SlideContentData,
                    max_tokens=self.max_tokens,
                    temperature=0.7,
                )

                if response.choices[0].message.parsed:
                    content_data = response.choices[0].message.parsed
                    return SlideContent(
                        layout_index=slide_spec.layout_index,
                        content=content_data.placeholder_content,
                    )

            except Exception:
                print(
                    f"Structured output not supported for slide {slide_number}, "
                    "using JSON mode"
                )

                # Fallback to JSON mode
                json_prompt = (
                    prompt + "\n\nRespond in valid JSON format:\n"
                    '{"placeholder_content": {"Title": "content", '
                    '"Content": "content"}}'
                )

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": self._get_content_system_prompt(),
                        },
                        {"role": "user", "content": json_prompt},
                    ],
                    max_tokens=self.max_tokens,
                    temperature=0.7,
                )

                # Parse JSON response
                content = response.choices[0].message.content
                if content:
                    try:
                        # Clean up response and parse JSON
                        content = self._clean_json_response(content)
                        content_data = json.loads(content)

                        return SlideContent(
                            layout_index=slide_spec.layout_index,
                            content=content_data.get("placeholder_content", {}),
                        )

                    except json.JSONDecodeError as e:
                        print(f"Failed to parse content JSON: {e}")
                        return self._create_fallback_content(layout_info, topic)
                else:
                    return self._create_fallback_content(layout_info, topic)

        except Exception as e:
            print(f"Error in contextual original method for slide {slide_number}: {e}")
            return self._create_fallback_content(layout_info, topic)

    def _clean_json_response(self, response: str) -> str:
        """Clean JSON response by removing markdown code blocks"""
        cleaned_response = response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
        return cleaned_response.strip()

    def _create_contextual_content_prompt(
        self,
        layout_info: Dict[str, Any],
        topic: str,
        slide_spec: SlideSpec,
        slide_number: int,
        total_slides: int,
    ) -> str:
        """Create contextual prompt for slide content generation"""
        placeholders = layout_info.get("placeholders", [])
        layout_name = layout_info.get("name", "Unknown")

        # Extract placeholder names from the list of dictionaries
        placeholder_names = []
        for placeholder in placeholders:
            if isinstance(placeholder, dict):
                placeholder_names.append(placeholder.get("name", "Unknown"))
            else:
                placeholder_names.append(str(placeholder))

        return f"""Generate content for slide {slide_number} of {total_slides} 
in a presentation about "{topic}".

Slide Specification:
- Title: {slide_spec.slide_title}
- Purpose: {slide_spec.slide_purpose}
- Layout: {layout_name}

Available placeholders: {', '.join(placeholder_names)}

Content Requirements:
1. Create content that specifically serves the slide's purpose: 
   {slide_spec.slide_purpose}
2. Ensure content aligns with the slide title: {slide_spec.slide_title}
3. Consider this slide's position ({slide_number}/{total_slides}) in overall flow
4. Fill all available placeholders with relevant, engaging content
5. Make content coherent with the overall topic while focusing on 
   this slide's specific purpose

Generate professional, informative content that advances the presentation 
narrative."""

    def plan_presentation(
        self, layouts_info: Dict[int, Dict[str, Any]], topic: str
    ) -> List[SlideSpec]:
        """
        Ask LLM to create an intelligent presentation plan

        Args:
            layouts_info: Dictionary of layout information
            topic: The presentation topic

        Returns:
            List of SlideSpec objects defining the presentation structure
        """
        prompt = self._create_presentation_planning_prompt(layouts_info, topic)

        try:
            # Try structured output first
            try:
                response = self.client.chat.completions.parse(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": self._get_planning_system_prompt(),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    response_format=PresentationPlan,
                    max_tokens=self.max_tokens,
                    temperature=0.7,
                )

                if response.choices[0].message.parsed:
                    plan = response.choices[0].message.parsed
                    print(f"Presentation plan created: {plan.total_slides} slides")
                    print(f"Flow: {plan.presentation_flow}")
                    print(f"Reasoning: {plan.reasoning}")
                    return plan.slides
                print("Warning: No structured response received")
                return self._create_default_plan(layouts_info)

            except Exception as e:
                print(f"Structured output failed: {e}")
                print("Falling back to JSON mode for presentation planning")

                # Fallback to JSON mode
                json_prompt = (
                    prompt + "\n\nRespond in valid JSON format with this structure:\n"
                    '{"total_slides": 3, "slides": [{"layout_index": 0, '
                    '"slide_title": "Title", "slide_purpose": "Purpose"}], '
                    '"presentation_flow": "Flow description", '
                    '"reasoning": "Why this structure"}'
                )

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": self._get_planning_system_prompt(),
                        },
                        {"role": "user", "content": json_prompt},
                    ],
                    max_tokens=self.max_tokens,
                    temperature=0.7,
                )

                # Parse JSON response
                content = response.choices[0].message.content
                if content:
                    try:
                        plan_data = json.loads(content)
                        slides = []
                        for slide_data in plan_data.get("slides", []):
                            slides.append(
                                SlideSpec(
                                    layout_index=slide_data["layout_index"],
                                    slide_title=slide_data["slide_title"],
                                    slide_purpose=slide_data["slide_purpose"],
                                )
                            )
                        print(f"Presentation plan: {len(slides)} slides")
                        return slides
                    except json.JSONDecodeError as e:
                        print(f"Failed to parse JSON: {e}")
                        # Ultimate fallback
                        return self._create_default_plan(layouts_info)
                else:
                    return self._create_default_plan(layouts_info)

        except Exception as e:
            print(f"Error in presentation planning: {e}")
            return self._create_default_plan(layouts_info)

    def _create_default_plan(
        self, layouts_info: Dict[int, Dict[str, Any]]
    ) -> List[SlideSpec]:
        """Create a default presentation plan as fallback"""
        available_layouts = list(layouts_info.keys())
        default_slides = [
            SlideSpec(
                layout_index=available_layouts[0] if available_layouts else 0,
                slide_title="Introduction",
                slide_purpose="Introduce the topic",
            ),
            SlideSpec(
                layout_index=(
                    available_layouts[1]
                    if len(available_layouts) > 1
                    else available_layouts[0]
                ),
                slide_title="Main Content",
                slide_purpose="Present key information",
            ),
            SlideSpec(
                layout_index=(
                    available_layouts[2]
                    if len(available_layouts) > 2
                    else available_layouts[0]
                ),
                slide_title="Conclusion",
                slide_purpose="Summarize and conclude",
            ),
        ]
        return default_slides

    def _create_presentation_planning_prompt(
        self, layouts_info: Dict[int, Dict[str, Any]], topic: str
    ) -> str:
        """Create prompt for presentation planning"""
        layouts_text = ""
        for idx, info in layouts_info.items():
            # Extract placeholder names from dictionaries
            placeholders = info.get("placeholders", [])
            placeholder_names = []
            for placeholder in placeholders:
                if isinstance(placeholder, dict):
                    placeholder_names.append(placeholder.get("name", "Unknown"))
                else:
                    placeholder_names.append(str(placeholder))

            layouts_text += f"Layout {idx}: {info['name']}\n"
            layouts_text += f"  - Placeholders: {', '.join(placeholder_names)}\n"
            layouts_text += (
                f"  - Best for: {info.get('description', 'General content')}\n\n"
            )

        return f"""Plan a comprehensive presentation for the topic: "{topic}"

Available layouts:
{layouts_text}

Create an intelligent presentation plan that:
1. Determines the optimal number of slides (typically 3-8 slides)
2. Selects appropriate layouts for each slide (can reuse layouts)
3. Defines clear purpose for each slide
4. Creates logical flow and structure

Consider:
- Topic complexity and scope
- Audience engagement 
- Information hierarchy
- Visual variety
- Logical progression

You can use the same layout multiple times if appropriate for the content."""

    def _get_planning_system_prompt(self) -> str:
        """Get system prompt for presentation planning"""
        return """You are an expert presentation designer and content strategist. 
        
Your role is to create intelligent presentation plans that:
- Determine optimal number of slides for comprehensive coverage
- Select appropriate layouts based on content type and purpose
- Create logical flow and narrative structure
- Balance information density with visual appeal
- Ensure engaging and professional presentations

Consider the topic's complexity, target audience, and educational value 
when planning."""

    def _create_layout_selection_prompt(
        self, layouts_info: Dict[int, Dict[str, Any]], topic: str
    ) -> str:
        """Create prompt for layout selection"""
        layouts_description = ""
        for idx, info in layouts_info.items():
            layouts_description += f"""
Layout {idx}: {info['name']}
- Suitable for: {', '.join(info['suitable_for'])}
- Placeholders: {len(info['placeholders'])} 
  ({', '.join([p['name'] for p in info['placeholders']])})
"""

        return f"""
Topic: {topic}

Available slide layouts:
{layouts_description}

Based on the topic "{topic}", please select slide layouts that would work best for 
best for creating a comprehensive presentation. Consider the flow of information 
and variety of content types.

Provide your selection as structured data with the layout indices and reasoning.
"""

    def _create_content_generation_prompt(
        self,
        layout_info: Dict[str, Any],
        topic: str,
        slide_number: int,
        total_slides: int,
    ) -> str:
        """Create prompt for content generation"""
        placeholders_desc = ""
        for p in layout_info["placeholders"]:
            placeholders_desc += f"- {p['name']} (Type: {p['type']})\n"

        return f"""
Topic: {topic}
Slide: {slide_number} of {total_slides}
Layout: {layout_info['name']}

CRITICAL: This slide has EXACTLY these placeholders (use EXACT names as keys):
{placeholders_desc}

Generate content for ALL and ONLY these placeholders. Do not create content for 
placeholders that don't exist. Use the exact placeholder names as shown above.

Generate appropriate content that fits the overall topic and slide position in 
the presentation. Ensure content is engaging, informative, and appropriate for 
the placeholder types.
"""

    def _get_layout_system_prompt(self) -> str:
        """Get system prompt for layout selection"""
        return """You are an expert presentation designer. Your task is to select 
the most appropriate slide layouts for a given topic. Consider:
- Flow of information (title slide first, conclusion last)
- Variety of content types
- Audience engagement
- Professional presentation structure

Always respond with only the layout indices as requested."""

    def _get_content_system_prompt(self) -> str:
        """Get system prompt for content generation"""
        return """You are an expert content creator specializing in presentations. 
Your task is to generate engaging, informative, and well-structured content 
for PowerPoint slides.

FORMATTING REQUIREMENTS:
- Use MARKDOWN formatting in all your content responses
- Use **bold** for emphasis and key points
- Use *italic* for terminology and subtle emphasis  
- Use # ## ### for headers of different levels
- Use - or * for bullet points
- Use 1. 2. 3. for numbered lists
- Structure content with clear headings and organized lists

Content should be:
- Clear and concise with professional markdown formatting
- Appropriate for business/professional audiences
- Properly formatted for the placeholder type
- Coherent with the overall topic
- Visually appealing when converted to PowerPoint format

Always respond in the requested JSON format with markdown-formatted content."""

    def _get_dynamic_content_system_prompt(self) -> str:
        """Get system prompt for dynamic model content generation"""
        return """You are an expert content creator specializing in presentations. 
Your task is to generate engaging, informative, and well-structured content 
for PowerPoint slides using the EXACT field names provided.

CRITICAL FORMATTING REQUIREMENTS:
- Use MARKDOWN formatting in your content responses
- Use **bold** for emphasis and important points
- Use *italic* for subtle emphasis or terminology
- Use # for main headers, ## for subheaders, ### for smaller headers
- Use - or * for bullet points
- Use 1. 2. 3. for numbered lists
- Structure content with proper headings and lists for visual appeal

FIELD NAME REQUIREMENT:
- Use the EXACT field names as they appear in the response format
- Do NOT shorten, abbreviate, or modify the field names in any way

Content should be:
- Clear and concise with proper markdown formatting
- Appropriate for business/professional audiences
- Properly structured with headers, lists, and emphasis
- Coherent with the overall topic

Follow the structured response format exactly and use markdown formatting throughout."""

    def _parse_layout_selection(self, response: str) -> List[int]:
        """Parse layout indices from LLM response"""
        try:
            # Extract numbers from response
            import re

            numbers = re.findall(r"\d+", response)
            return [int(n) for n in numbers]
        except Exception:
            # Fallback to first 3 layouts
            return [0, 1, 2]

    def _parse_slide_content(
        self, response: str, layout_info: Dict[str, Any]
    ) -> Dict[str, str]:
        """Parse slide content from LLM response"""
        try:
            # Clean the response - remove markdown code blocks if present
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()

            # Try to parse as JSON
            content_dict = json.loads(cleaned_response)

            # Validate that we only have placeholders that exist in the layout
            valid_placeholder_names = {p["name"] for p in layout_info["placeholders"]}
            filtered_content = {}

            for key, value in content_dict.items():
                if key in valid_placeholder_names:
                    filtered_content[key] = str(value)
                else:
                    print(
                        f"Warning: Ignoring invalid placeholder '{key}' "
                        f"for layout {layout_info['name']}"
                    )

            return filtered_content

        except json.JSONDecodeError as e:
            print(f"JSON parsing failed: {e}")
            # Fallback: create simple content mapping
            return self._create_simple_content_mapping(response, layout_info)

    def _create_simple_content_mapping(
        self, response: str, layout_info: Dict[str, Any]
    ) -> Dict[str, str]:
        """Create simple content mapping when JSON parsing fails"""
        content = {}
        lines = response.split("\n")

        for i, placeholder in enumerate(layout_info["placeholders"]):
            if i < len(lines):
                content[placeholder["name"]] = lines[i].strip()
            else:
                content[placeholder["name"]] = f"Content for {placeholder['name']}"

        return content

    def _create_fallback_content(
        self, layout_info: Dict[str, Any], topic: str
    ) -> SlideContent:
        """Create fallback content when LLM fails"""
        content = {}
        for placeholder in layout_info["placeholders"]:
            if "title" in placeholder["name"].lower():
                content[placeholder["name"]] = f"{topic} - Slide Content"
            else:
                content[placeholder["name"]] = f"Content about {topic}"

        return SlideContent(layout_index=layout_info["index"], content=content)
