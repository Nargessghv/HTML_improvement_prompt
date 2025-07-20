"""
LLM Client Module

This module handles communication with OpenAI's API for content generation.
Supports both direct OpenAI API calls and Langchain integration for unified tracing.
"""

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from openai import OpenAI

from .llm_models import LayoutSelection, PresentationPlan, SlideSpec

# Load environment variables
load_dotenv()


@dataclass
class SlideContent:
    """Data class for slide content"""

    layout_index: int
    content: Dict[str, str]  # placeholder_name -> content


class LangchainLLMClient:
    """
    Langchain-compatible LLM client for unified tracing with Langfuse
    Supports both OpenAI and Azure OpenAI endpoints via environment variables.
    """

    def __init__(
        self, model: Optional[str] = None, chat_client: Optional[ChatOpenAI] = None
    ):
        """
        Initialize the Langchain LLM client

        Args:
            model: OpenAI model to use (defaults to OPENAI_MODEL env var)
            chat_client: An optional pre-configured ChatOpenAI instance.
        """
        provider = os.getenv("LLM_PROVIDER", "openai").lower()
        if provider == "azure":
            # Azure OpenAI configuration using the dedicated AzureChatOpenAI class
            azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
            azure_api_version = os.getenv(
                "AZURE_OPENAI_API_VERSION", "2024-02-15-preview"
            )
            self.model = model or os.getenv("AZURE_OPENAI_MODEL") or azure_deployment
            self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "2000"))
            self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.1"))

            # Use the dedicated AzureChatOpenAI class for robust Azure support
            # It automatically uses AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY from env
            self.chat_client = AzureChatOpenAI(
                azure_deployment=azure_deployment,
                api_version=azure_api_version,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        elif chat_client:
            self.chat_client = chat_client
            self.model = chat_client.model_name
        else:
            # Standard OpenAI configuration
            self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o")
            self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "2000"))
            self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.1"))
            self.chat_client = ChatOpenAI(
                model=self.model,
                temperature=self.temperature,
                max_completion_tokens=self.max_tokens,
            )

    def generate_structured_content(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Any,
        config: Optional[RunnableConfig] = None,
    ) -> Any:
        """
        Generate structured content using Langchain with callback support

        Args:
            system_prompt: System instructions
            user_prompt: User input
            response_model: Pydantic model for structured output
            config: Langchain configuration with callbacks

        Returns:
            Generated content in the specified format
        """
        try:
            # Create structured chat client
            structured_client = self.chat_client.with_structured_output(response_model)

            # Create messages
            messages = [
                ("system", system_prompt),
                ("human", user_prompt),
            ]

            # Generate with callback support
            response = structured_client.invoke(messages, config=config)
            return response

        except Exception as e:
            print(f"❌ Error generating structured content: {e}")
            raise

    def generate_structured_vision_content(
        self,
        system_prompt: str,
        user_prompt: List[Dict[str, Any]],
        response_model: Any,
        config: Optional[RunnableConfig] = None,
    ) -> Any:
        """
        Generate structured content from multimodal input (text + image)
        using Langchain with callback support.

        Args:
            system_prompt: System instructions for the vision model.
            user_prompt: A list of dictionaries representing the multimodal
                         content (e.g., text and image URLs).
            response_model: Pydantic model for structured output.
            config: Langchain configuration with callbacks.

        Returns:
            Generated content in the specified Pydantic model format.
        """
        try:
            # Create a structured chat client with the specified response model
            structured_client = self.chat_client.with_structured_output(response_model)

            # Create messages with multimodal content
            messages = [
                ("system", system_prompt),
                ("human", user_prompt),
            ]

            # Invoke the client with the messages and configuration
            response = structured_client.invoke(messages, config=config)
            return response

        except Exception as e:
            print(f"❌ Error generating structured vision content: {e}")
            raise

    def generate_content(
        self,
        system_prompt: str,
        user_prompt: str,
        config: Optional[RunnableConfig] = None,
    ) -> str:
        """
        Generate text content using Langchain with callback support

        Args:
            system_prompt: System instructions
            user_prompt: User input
            config: Langchain configuration with callbacks

        Returns:
            Generated text content
        """
        try:
            # Create messages
            messages = [
                ("system", system_prompt),
                ("human", user_prompt),
            ]

            # Generate with callback support
            response = self.chat_client.invoke(messages, config=config)

            # Ensure we return a string
            if hasattr(response, "content"):
                return str(response.content)
            return str(response)

        except Exception as e:
            print(f"❌ Error generating content: {e}")
            raise

    def generate_contextual_slide_content(
        self,
        layout_info: Dict[str, Any],
        topic: str,
        slide_spec: Any,  # SlideSpec object
        slide_number: int,
        total_slides: int,
        dynamic_model: Optional[Any] = None,
        config: Optional[RunnableConfig] = None,
    ) -> Optional[Any]:  # SlideContent object
        """
        Generate content for a specific slide with contextual awareness using Langchain

        Args:
            layout_info: Information about the slide layout
            topic: The overall presentation topic
            slide_spec: Specification for this particular slide
            slide_number: Current slide number (1-indexed)
            total_slides: Total number of slides in presentation
            dynamic_model: Dynamic Pydantic model for exact placeholder matching
            config: Langchain configuration with callbacks

        Returns:
            SlideContent object or None if generation fails
        """
        prompt = self._create_contextual_content_prompt(
            layout_info, topic, slide_spec, slide_number, total_slides
        )

        try:
            # Use dynamic model if provided for perfect placeholder matching
            if dynamic_model:
                system_prompt = self._get_content_generation_system_prompt()
                response = self.generate_structured_content(
                    system_prompt=system_prompt,
                    user_prompt=prompt,
                    response_model=dynamic_model,
                    config=config,
                )

                if response:
                    # Convert dynamic model response to SlideContent
                    content_dict = {}
                    for field_name, field_value in response.__dict__.items():
                        if field_value is not None:
                            content_dict[field_name] = str(field_value)

                    return SlideContent(
                        layout_index=slide_spec.layout_index,
                        content=content_dict,
                    )

            # Fallback to text generation
            system_prompt = self._get_content_generation_system_prompt()
            response_text = self.generate_content(
                system_prompt=system_prompt,
                user_prompt=prompt,
                config=config,
            )

            # Parse response and create SlideContent
            placeholders = layout_info.get("placeholders", {})
            content_dict = {}

            # Handle placeholders list vs dict format
            if isinstance(placeholders, list):
                # Convert list of placeholder objects to names
                placeholder_names = [
                    p.get("name", f"placeholder_{i}") if isinstance(p, dict) else str(p)
                    for i, p in enumerate(placeholders)
                ]
            elif isinstance(placeholders, dict):
                placeholder_names = list(placeholders.keys())
            else:
                placeholder_names = []

            # Simple content extraction for fallback
            if placeholder_names:
                if len(placeholder_names) == 1:
                    # Single placeholder - use entire response
                    content_dict[placeholder_names[0]] = response_text
                else:
                    # Multiple placeholders - split content
                    lines = response_text.split("\n\n")
                    for i, placeholder in enumerate(placeholder_names):
                        if i < len(lines):
                            content_dict[placeholder] = lines[i].strip()
                        else:
                            content_dict[placeholder] = f"Content for {placeholder}"

            return SlideContent(
                layout_index=slide_spec.layout_index,
                content=content_dict,
            )

        except Exception as e:
            print(
                f"❌ Error generating contextual content for slide {slide_number}: {e}"
            )
            return self._create_fallback_content(
                layout_info, topic, slide_spec.layout_index
            )

    def _create_contextual_content_prompt(
        self,
        layout_info: Dict[str, Any],
        topic: str,
        slide_spec: Any,  # SlideSpec object
        slide_number: int,
        total_slides: int,
    ) -> str:
        """
        Create contextual content generation prompt with HTML awareness

        Args:
            layout_info: Information about the slide layout
            topic: The overall presentation topic
            slide_spec: Specification for this particular slide (includes is_html flag)
            slide_number: Current slide number (1-indexed)
            total_slides: Total number of slides in presentation

        Returns:
            Contextual prompt string with HTML guidance
        """
        # Get placeholder information
        placeholders = layout_info.get("placeholders", [])

        if isinstance(placeholders, list):
            placeholder_descriptions = []
            for placeholder in placeholders:
                if isinstance(placeholder, dict):
                    name = placeholder.get("name", "Unknown")
                    placeholder_type = placeholder.get("type", "text")
                    instructions = placeholder.get("instructions", "")

                    desc = f"- {name}"
                    if placeholder_type != "text":
                        desc += f" (type: {placeholder_type})"
                    if instructions:
                        desc += f" - {instructions}"
                    placeholder_descriptions.append(desc)
                else:
                    placeholder_descriptions.append(f"- {str(placeholder)}")

            placeholders_text = "\n".join(placeholder_descriptions)
        else:
            placeholders_text = "No specific placeholders defined"

        # Check if this slide is marked for HTML visualization
        is_html = getattr(slide_spec, "is_html", False)
        html_guidance = ""

        if is_html:
            html_guidance = """
🎨 HTML VISUALIZATION SLIDE:
This slide is specifically designated for HTML visualization. Generate DESCRIPTIVE content that:
- Describes what should be visualized (timeline, process, comparison, diagram)
- Provides structured data and information that can be turned into HTML
- Includes specific data points, steps, sequences, or comparative elements
- Focuses on the INFORMATION to be visualized, not the HTML code itself

IMPORTANT: Do NOT generate HTML code. Generate descriptions and structured information 
that the HTML generation agent will use to create actual visualizations.

CONTENT APPROACH FOR HTML SLIDES:
- For timelines: Provide dates, milestones, and sequential events with descriptions
- For processes: List clear steps with detailed descriptions and relationships
- For comparisons: Present contrasting elements with specific metrics and details
- For data viz: Include actual numbers, percentages, or measurable outcomes
- Structure content as information to be visualized, not as final HTML

EXAMPLES:
❌ WRONG: Generate HTML like "<div class='timeline'>..."
✅ CORRECT: "Timeline showing 4 key phases: Phase 1 (Jan 2024): Discovery and planning with stakeholder interviews..."

The HTML generation agent will convert your descriptive content into actual HTML visualizations.
"""
        else:
            html_guidance = """
📝 STANDARD CONTENT SLIDE:
This slide uses traditional text content. Generate:
- Clear, well-structured text content
- Professional bullet points or paragraphs as appropriate
- Content suitable for standard text placeholders
- Focus on clarity and readability
"""

        # Build detailed specifications from enhanced SlideSpec
        detailed_specs = []

        # Add detailed purpose if available
        if hasattr(slide_spec, "detailed_purpose") and slide_spec.detailed_purpose:
            detailed_specs.append(f"Detailed Purpose: {slide_spec.detailed_purpose}")

        # Add content structure if available
        if hasattr(slide_spec, "content_structure") and slide_spec.content_structure:
            detailed_specs.append(f"Content Structure: {slide_spec.content_structure}")

        # Add visual elements if available
        if hasattr(slide_spec, "visual_elements") and slide_spec.visual_elements:
            detailed_specs.append(f"Visual Elements: {slide_spec.visual_elements}")

        # Add HTML requirements if available and is HTML slide
        if (
            is_html
            and hasattr(slide_spec, "html_requirements")
            and slide_spec.html_requirements
        ):
            detailed_specs.append(f"HTML Requirements: {slide_spec.html_requirements}")

        # Add key information if available
        if hasattr(slide_spec, "key_information") and slide_spec.key_information:
            key_info_text = ", ".join(slide_spec.key_information)
            detailed_specs.append(f"Key Information: {key_info_text}")

        detailed_specs_text = (
            "\n- ".join(detailed_specs)
            if detailed_specs
            else "No additional specifications"
        )

        return f"""
Generate compelling content for slide {slide_number} of {total_slides} in a 
presentation about "{topic}".

🎯 SLIDE CONTEXT:
- Title: {slide_spec.slide_title}
- Basic Purpose: {slide_spec.slide_purpose}
- Layout: {layout_info.get('name', 'Unknown Layout')}

🎯 DETAILED SPECIFICATIONS:
- {detailed_specs_text}

📋 AVAILABLE PLACEHOLDERS:
{placeholders_text}

{html_guidance}

🎯 CONTENT REQUIREMENTS:
- Professional, engaging tone suitable for business presentations
- Content MUST align with ALL detailed specifications provided above
- Follow the specified content structure and include all key information
- Incorporate required visual elements in your content descriptions
- Ensure content fits the available placeholders appropriately
- Use Ekona branding context where relevant (professional services, innovation)
- Make content specific and actionable rather than generic

Generate content for each placeholder that supports the detailed specifications 
and fits the designated content approach (HTML visualization vs. standard text).
Use the detailed purpose, content structure, and key information to create 
precisely targeted content that aligns with the presentation plan.
"""

    def _get_content_generation_system_prompt(self) -> str:
        """Get system prompt for content generation"""
        return """You are an expert content creator for professional presentations. 
Create engaging, informative, and well-structured content that effectively 
communicates key messages to the audience."""

    def _create_fallback_content(
        self, layout_info: Dict[str, Any], topic: str, layout_index: int
    ) -> Any:
        """Create basic fallback content when generation fails"""
        placeholders = layout_info.get("placeholders", {})
        content_dict = {}

        # Handle placeholders list vs dict format
        if isinstance(placeholders, list):
            placeholder_names = [
                p.get("name", f"placeholder_{i}") if isinstance(p, dict) else str(p)
                for i, p in enumerate(placeholders)
            ]
        elif isinstance(placeholders, dict):
            placeholder_names = list(placeholders.keys())
        else:
            placeholder_names = []

        for placeholder_name in placeholder_names:
            content_dict[placeholder_name] = f"Content about {topic}"

        return SlideContent(
            layout_index=layout_index,
            content=content_dict,
        )

    def generate_unified_presentation_content(
        self,
        topic: str,
        presentation_plan: List[Any],  # List of SlideSpec objects
        layouts_info: Dict[int, Dict[str, Any]],
        config: Optional[RunnableConfig] = None,
    ) -> Optional[List[Any]]:  # List of SlideContent objects
        """
        Generate content for ALL slides in one unified LLM call with full
        presentation context for better coherence between slides.

        Args:
            topic: The presentation topic
            presentation_plan: Complete list of SlideSpec objects
            layouts_info: Layout information for all slides
            config: Langchain configuration with callbacks

        Returns:
            List of SlideContent objects with contextually aware content
        """
        prompt = self._create_unified_presentation_prompt(
            topic, presentation_plan, layouts_info
        )
        system_prompt = self._get_unified_generation_system_prompt()

        try:
            # Import here to avoid circular import
            from .llm_models import PresentationContent

            # Use structured output with full presentation context
            response = self.generate_structured_content(
                system_prompt=system_prompt,
                user_prompt=prompt,
                response_model=PresentationContent,
                config=config,
            )

            if response and hasattr(response, "slide_contents"):
                print(
                    f"✅ Generated unified content for "
                    f"{len(response.slide_contents)} slides"
                )
                print(f"📝 Presentation Summary: {response.presentation_summary}")

                # Convert to SlideContent objects
                slide_contents = []
                for i, slide_data in enumerate(response.slide_contents):
                    if i < len(presentation_plan):
                        slide_content = SlideContent(
                            layout_index=presentation_plan[i].layout_index,
                            content=slide_data.placeholder_content,
                        )
                        slide_contents.append(slide_content)

                return slide_contents

            return None

        except Exception as e:
            print(f"❌ Error in unified content generation: {e}")
            return None

    def _create_unified_presentation_prompt(
        self,
        topic: str,
        presentation_plan: List[Any],
        layouts_info: Dict[int, Dict[str, Any]],
    ) -> str:
        """Create comprehensive prompt for unified presentation generation"""

        # Build detailed presentation outline
        outline_text = ""
        detailed_slides = ""

        for i, slide_spec in enumerate(presentation_plan, 1):
            layout_info = layouts_info.get(slide_spec.layout_index, {})
            layout_name = layout_info.get("name", f"Layout {slide_spec.layout_index}")

            outline_text += f"{i}. {slide_spec.slide_title}\n"

            # Get placeholder details for this slide
            placeholders = layout_info.get("placeholders", [])
            placeholder_details = []

            for p in placeholders:
                if isinstance(p, dict):
                    name = p.get("name", "Placeholder")
                    instructions = p.get("instructions", "")
                    if instructions:
                        placeholder_details.append(f"  - {name}: {instructions}")
                    else:
                        placeholder_details.append(f"  - {name}")
                else:
                    placeholder_details.append(f"  - {str(p)}")

            placeholder_text = (
                "\n".join(placeholder_details)
                if placeholder_details
                else "  - No placeholders"
            )

            # Build detailed specifications section
            specifications = [f"Basic Purpose: {slide_spec.slide_purpose}"]

            # Add detailed purpose if available
            if hasattr(slide_spec, "detailed_purpose") and slide_spec.detailed_purpose:
                specifications.append(
                    f"Detailed Purpose: {slide_spec.detailed_purpose}"
                )

            # Add content structure if available
            if (
                hasattr(slide_spec, "content_structure")
                and slide_spec.content_structure
            ):
                specifications.append(
                    f"Content Structure: {slide_spec.content_structure}"
                )

            # Add visual elements if available
            if hasattr(slide_spec, "visual_elements") and slide_spec.visual_elements:
                specifications.append(f"Visual Elements: {slide_spec.visual_elements}")

            # Add HTML requirements if available and is HTML slide
            is_html = getattr(slide_spec, "is_html", False)
            if (
                is_html
                and hasattr(slide_spec, "html_requirements")
                and slide_spec.html_requirements
            ):
                specifications.append(
                    f"HTML Requirements: {slide_spec.html_requirements}"
                )

            # Add key information if available
            if hasattr(slide_spec, "key_information") and slide_spec.key_information:
                key_info_text = ", ".join(slide_spec.key_information)
                specifications.append(f"Key Information: {key_info_text}")

            specifications_text = "\n".join(specifications)
            html_indicator = " (HTML VISUALIZATION)" if is_html else ""

            detailed_slides += f"""
Slide {i}: {slide_spec.slide_title}{html_indicator}
{specifications_text}
Layout: {layout_name}
Placeholders:
{placeholder_text}
"""

        return f"""Create a comprehensive, coherent presentation about: "{topic}"

PRESENTATION STRUCTURE ({len(presentation_plan)} slides total):
{outline_text}

DETAILED SLIDE SPECIFICATIONS:
{detailed_slides}

CRITICAL REQUIREMENTS:
1. Generate content for ALL {len(presentation_plan)} slides in one unified response
2. STRICTLY FOLLOW all detailed specifications provided for each slide
3. Ensure content flows logically from slide to slide
4. Maintain consistent messaging and terminology throughout
5. Each slide should build upon previous slides and prepare for upcoming ones
6. Use the EXACT placeholder names as specified for each slide
7. Create engaging, professional content appropriate for business audiences
8. Ensure content coherence across the entire presentation narrative
9. For HTML slides, create content that supports the specified visualization 
   requirements
10. Include ALL key information points specified for each slide

CONTENT STRATEGY:
- Follow the detailed purpose and content structure for each slide
- Incorporate all specified visual elements and key information
- Introduction slides should set the stage for detailed content
- Middle slides should develop key concepts with supporting details
- Conclusion slides should synthesize and reinforce main messages
- Use consistent examples and case studies throughout when appropriate
- Maintain professional tone and clear, concise language
- For HTML slides, structure content to support the specified visualizations

Generate content that creates a unified, compelling presentation experience 
where each slide contributes to a coherent whole."""

    def _get_unified_generation_system_prompt(self) -> str:
        """Get system prompt for unified presentation generation"""
        return """You are an expert presentation content strategist specializing 
in creating coherent, engaging business presentations. 

Your task is to generate content for an ENTIRE presentation in one unified 
response, ensuring perfect flow and coherence between all slides.

CRITICAL FORMATTING REQUIREMENTS:
- Use MARKDOWN formatting in your content responses
- Use **bold** for emphasis and important points
- Use *italic* for subtle emphasis or terminology
- Use # for main headers, ## for subheaders, ### for smaller headers
- Use - or * for bullet points
- Use 1. 2. 3. for numbered lists
- Structure content with proper headings and lists for visual appeal

HTML VISUALIZATION SLIDES:
For slides marked as "HTML VISUALIZATION", generate DESCRIPTIVE content that:
- Describes what should be visualized (timeline, process, comparison, diagram)
- Provides structured data and information that can be turned into HTML
- Includes specific data points, steps, sequences, or comparative elements
- Focuses on the INFORMATION to be visualized, not HTML code itself

🚫 DO NOT generate HTML code for HTML slides - generate descriptions instead
✅ Example: "Timeline showing 4 key phases: Phase 1 (Jan 2024): Discovery..."
❌ Wrong: "<div class='timeline'>..." or any actual HTML

The HTML generation agent will convert your descriptive content into actual visualizations.

UNIFIED CONTENT STRATEGY:
- Consider the ENTIRE presentation narrative when creating each slide
- Ensure smooth transitions between slides
- Use consistent terminology and examples throughout
- Build arguments progressively across slides
- Create compelling opening, strong development, and memorable conclusion
- Maintain professional, engaging tone throughout
- For HTML slides, structure information to support effective visualization

ICON PLACEHOLDER HANDLING:
- For icon fields, provide ONLY the icon name 
  (e.g., "users", "trending-up", "lightbulb")
- Choose icons that reinforce the overall presentation theme
- Select contextually appropriate icons for each slide's purpose
- 🚨 CRITICAL: ONLY use lucide-static icon names that exist in the library
- You have knowledge of lucide-static - stick to valid icon names only
- INVALID examples: money, tools, time, exclamation (these don't exist)

Your content should create a presentation that flows like a well-structured 
story, where each slide serves the overall narrative while standing strong 
individually."""


class LLMClient:
    """LLM client for OpenAI or Azure OpenAI API"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        provider = os.getenv("LLM_PROVIDER", "openai").lower()
        if provider == "azure":
            self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
            self.model = model or os.getenv("AZURE_OPENAI_MODEL", "gpt-35-turbo")
            self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "2000"))
            self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.1"))
            self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
            self.api_version = os.getenv(
                "AZURE_OPENAI_API_VERSION", "2024-02-15-preview"
            )
            if not self.endpoint:
                raise ValueError(
                    "AZURE_OPENAI_ENDPOINT must be set for Azure OpenAI usage."
                )
            from openai import AzureOpenAI

            self.client = AzureOpenAI(
                api_key=self.api_key,
                api_version=self.api_version,
                azure_endpoint=self.endpoint,
            )
        else:
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o")
            self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "2000"))
            self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.1"))
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
                    temperature=self.temperature,
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
                    temperature=self.temperature,
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
                    f"  ✅ Dynamic model generated content for: "
                    f"{list(content_dict.keys())}"
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
        Generate content for a specific slide with contextual awareness
        using dynamic models

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
                    temperature=self.temperature,
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
                    temperature=self.temperature,
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
                    temperature=self.temperature,
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
                    temperature=self.temperature,
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
5. **PRIORITIZES HTML visualizations** for timeline, process, and workflow content

🎯 CRITICAL: Use Layout 3 ("Title and Picture generated from HTML") for:
- Timelines, roadmaps, chronological sequences
- Process flows, workflows, step-by-step procedures
- Comparisons, before/after scenarios  
- Complex data requiring custom visualization
- Any content that would benefit from interactive-style graphics

Consider:
- Topic complexity and scope
- Audience engagement through rich visuals
- Information hierarchy with HTML visualizations
- Visual storytelling opportunities
- Logical progression with strategic visual elements

You can and SHOULD use the same layout multiple times when appropriate. 
Prioritize HTML visualizations at the same level as icon usage."""

    def _get_planning_system_prompt(self) -> str:
        """Get system prompt for presentation planning"""
        return """You are an expert presentation designer and content strategist 
specialized in creating visually rich, engaging presentations.
        
Your role is to create intelligent presentation plans that:
- Determine optimal number of slides for comprehensive coverage
- PROACTIVELY identify content requiring HTML visualizations
- Select appropriate layouts based on content type and visual needs
- Create logical flow and narrative structure with rich visual elements
- Balance information density with compelling visual storytelling
- Ensure engaging and professional presentations with custom graphics

CRITICAL: Always consider if content would benefit from Layout 3 HTML 
visualizations (timelines, processes, workflows). Prioritize 
visual impact at the same level as textual content.

Consider the topic's complexity, target audience, and educational value 
when planning, with emphasis on visual engagement opportunities."""

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

ICON PLACEHOLDER HANDLING:
- For fields requesting icon selection, respond with ONLY the icon name
- Choose from the provided list of valid icon names
- DO NOT provide descriptive text like "Icon representing..." 
- Examples: "users", "trending-up", "lightbulb" (NOT "Icon showing growth")
- Select icons that match the slide content and context
- 🚨 CRITICAL: ONLY use lucide-static icon names that exist in the library
- You have knowledge of lucide-static - stick to valid icon names only
- INVALID examples: money, tools, time, exclamation (these don't exist)

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
