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

from .llm_models import LayoutSelection, SlideContentData

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
                response = self.client.beta.chat.completions.parse(
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
    ) -> SlideContent:
        """
        Generate content for a specific slide layout

        Args:
            layout_info: Information about the layout
            topic: The presentation topic
            slide_number: Current slide number (1-indexed)
            total_slides: Total number of slides

        Returns:
            SlideContent object with generated content
        """
        prompt = self._create_content_generation_prompt(
            layout_info, topic, slide_number, total_slides
        )

        try:
            # Try structured output first (for compatible OpenAI endpoints)
            try:
                response = self.client.beta.chat.completions.parse(
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
                print(
                    f"Structured output not supported for slide {slide_number}, "
                    "using JSON mode"
                )

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
            print(f"Error generating content for slide {slide_number}: {e}")
            # Fallback content
            return self._create_fallback_content(layout_info, topic)

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

Based on the topic "{topic}", please select 3-5 slide layouts that would work 
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
for PowerPoint slides. Ensure content is:
- Clear and concise
- Appropriate for business/professional audiences
- Properly formatted for the placeholder type
- Coherent with the overall topic

Always respond in the requested JSON format."""

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
