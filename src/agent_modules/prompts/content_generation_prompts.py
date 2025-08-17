"""
Content Generation Prompts

Contains the prompt templates used by the ContentGenerationAgent
for creating unified presentation content with full context awareness.
"""

from typing import Any, Dict, List


def create_unified_presentation_prompt(
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

        # Add IMAGE requirements if available and is image slide
        is_image = getattr(slide_spec, "is_image", False)
        if (
            is_image
            and hasattr(slide_spec, "image_requirements")
            and slide_spec.image_requirements
        ):
            specifications.append(
                f"Image Requirements: {slide_spec.image_requirements}"
            )

        # Add key information if available
        if hasattr(slide_spec, "key_information") and slide_spec.key_information:
            key_info_text = ", ".join(slide_spec.key_information)
            specifications.append(f"Key Information: {key_info_text}")

        specifications_text = "\n".join(specifications)
        
        # Create visual indicators for different slide types
        visual_indicator = ""
        if is_html:
            visual_indicator = " (HTML VISUALIZATION)"
        elif is_image:
            visual_indicator = " (AI IMAGE GENERATION)"

        detailed_slides += f"""
Slide {i}: {slide_spec.slide_title}{visual_indicator}
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
10. For IMAGE slides, create descriptive content that guides AI image generation
11. Include ALL key information points specified for each slide

CONTENT STRATEGY:
- Follow the detailed purpose and content structure for each slide
- Incorporate all specified visual elements and key information
- Introduction slides should set the stage for detailed content
- Middle slides should develop key concepts with supporting details
- Conclusion slides should synthesize and reinforce main messages
- Use consistent examples and case studies throughout when appropriate
- Maintain professional tone and clear, concise language
- For HTML slides, structure content to support the specified visualizations
- For IMAGE slides, provide descriptive content that will guide AI image generation

Generate content that creates a unified, compelling presentation experience 
where each slide contributes to a coherent whole."""


def get_unified_generation_system_prompt() -> str:
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

AI IMAGE GENERATION SLIDES:
For slides marked as "AI IMAGE GENERATION", generate DESCRIPTIVE content that:
- Describes the visual scene, concept, or illustration needed
- Provides specific details about composition, style, and key elements
- Includes context about the business/professional setting if relevant
- Focuses on VISUAL DESCRIPTIONS that will guide AI image generation
- Considers the slide's purpose and how the image supports the message

🚫 DO NOT generate actual images - generate detailed descriptions instead
✅ Example: "Professional office setting showing diverse team collaborating around a digital dashboard, modern workspace with natural lighting, business casual attire, engaged expressions"
❌ Wrong: "[Image of people working]" or vague descriptions

The AI image generation agent will convert your descriptive content into actual images.

UNIFIED CONTENT STRATEGY:
- Consider the ENTIRE presentation narrative when creating each slide
- Ensure smooth transitions between slides
- Use consistent terminology and examples throughout
- Build arguments progressively across slides
- Create compelling opening, strong development, and memorable conclusion
- Maintain professional, engaging tone throughout
- For HTML slides, structure information to support effective visualization
- For IMAGE slides, provide rich visual descriptions for AI generation

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