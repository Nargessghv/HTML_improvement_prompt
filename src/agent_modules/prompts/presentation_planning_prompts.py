"""
Presentation Planning Prompts

Contains the prompt templates used by the PresentationPlanningAgent
for creating strategic presentation plans with LLM guidance.
"""

from typing import Optional


def create_presentation_planning_prompt(
    layouts_info: dict[int, dict[str, object]],
    topic: str,
    title: Optional[str] = None,
    document_context: Optional[str] = None,
) -> str:
    """
    Create optimized prompt for strategic presentation planning
    with clear HTML decisions and actionable guidance.
    
    Args:
        layouts_info: Dictionary of available layouts
        topic: Main topic for the presentation
        title: Optional presentation title
        document_context: Optional context from uploaded documents
    """
    # Analyze layouts to identify HTML-capable ones
    layout_descriptions = []
    html_capable_layouts = []

    for layout_index, layout_info in layouts_info.items():
        layout_name = layout_info.get("name", f"Layout {layout_index}")
        placeholders = layout_info.get("placeholders", [])

        # Build placeholder description
        placeholder_text = "No placeholders"
        if placeholders:
            placeholder_names = []
            has_picture_placeholder = False

            if isinstance(placeholders, list):
                for placeholder in placeholders:
                    if isinstance(placeholder, dict):
                        name = placeholder.get("name", "Unknown")
                        placeholder_names.append(name)
                        # Check if this layout has picture placeholders for HTML
                        html_keywords = ["picture", "image", "visual", "html"]
                        if any(keyword in name.lower() for keyword in html_keywords):
                            has_picture_placeholder = True
                    else:
                        placeholder_names.append(str(placeholder))

            placeholder_text = ", ".join(placeholder_names)

            # Track HTML-capable layouts
            if has_picture_placeholder:
                html_capable_layouts.append(layout_index)

        layout_descriptions.append(
            f"Layout {layout_index} - {layout_name}: {placeholder_text}"
        )

    layouts_text = "\n".join(layout_descriptions)
    html_layouts_text = (
        ", ".join(map(str, html_capable_layouts))
        if html_capable_layouts
        else "None identified"
    )

    # Build title/topic section
    title_section = f'TITLE: "{title}"\n' if title else ""
    topic_label = "TOPIC" if not title else "DESCRIPTION"
    
    # Add document context section if available
    context_section = ""
    if document_context:
        # Truncate context if too long (keep under 10k tokens approximately)
        max_context_chars = 40000
        truncated_context = document_context[:max_context_chars]
        if len(document_context) > max_context_chars:
            truncated_context += "\n\n[... Context truncated for length ...]"
        
        context_section = f"""
📄 DOCUMENT CONTEXT PROVIDED BY USER:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{truncated_context}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 IMPORTANT: The above document(s) have been provided as context for the presentation.
Use this information to:
• Extract key points, facts, and data for slide content
• Maintain accuracy and consistency with the source material
• Structure the presentation to best represent the document's information
• Create visualizations for data or processes mentioned in the documents

"""

    return f"""📋 CREATE STRATEGIC PRESENTATION PLAN

{title_section}{topic_label}: "{topic}"
{context_section}

🚨 CRITICAL REQUIREMENTS - READ FIRST:
• START WITH TITLE SLIDE: Your presentation MUST begin with a title slide using layout designed for titles
• ADD TO SLIDE COUNT: If user requests "4 slides", create title slide PLUS 4 content slides (5 total)
• FOLLOW exact slide count if specified ("one slide only", "3 slides", "5-slide presentation")  
• KEYWORD DETECTION: "infographic"/"visualization" → is_html=true, "picture"/"photo" → is_image=true
• LAYOUT MATCHING: HTML/Image content REQUIRES layouts with Picture/Image placeholders
• AVOID sequential layout usage (0,1,2,3...) - choose by content fit

⚠️ TITLE SLIDE REQUIREMENT:
• Slide 1 MUST be a title slide - select any layout with "title", "start", "intro", or "logo" in the name
• Title slide introduces the presentation topic and sets the context
• Content slides follow after the title slide

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 AVAILABLE LAYOUTS:
{layouts_text}

✨ HTML-CAPABLE LAYOUTS: {html_layouts_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎨 CONTENT TYPE DECISION GUIDE

SET is_html: true FOR:
✅ INFOGRAPHICS - Any "infographic" request MUST use HTML
✅ Timelines, roadmaps, process flows, workflows  
✅ Data visualizations, metrics, dashboards
✅ Conceptual diagrams (AI agents, system architecture)
✅ Comparisons, before/after scenarios
✅ Educational diagrams, visual explanations

SET is_image: true FOR:
✅ Photographic scenes ("photo of office", "team working")
✅ Portrait/environmental images ("doctor", "customer photo")
✅ Conceptual illustrations requiring artistic rendering

SET BOTH false FOR:
✅ Simple text, bullet points, basic content

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 REQUIRED SLIDE SPECIFICATIONS

FOR EVERY SLIDE:
• **layout_index**: Specific number from available layouts
• **slide_purpose**: Clear purpose (1-2 sentences)
• **detailed_purpose**: Comprehensive explanation (3-4 sentences) 
• **content_structure**: Organization ("2-column", "5-step process")
• **visual_elements**: Required visuals ("icons, arrows, timeline")
• **key_information**: Essential points (3-5 items)
• **is_html**: true/false - ANY placeholder needs HTML
• **is_image**: true/false - ANY placeholder needs images
• **placeholder_requirements**: Content type for each placeholder

🎯 PLACEHOLDER REQUIREMENTS FORMAT:
- placeholder_name: "exact_name_from_layout"
- content_type: "text" | "html" | "image"  
- description: "detailed generation description"

FOR HTML: Add **html_requirements** with tool selection:
• D3.js: MANDATORY for timelines/roadmaps, custom visualizations
• Mermaid: Standard diagrams (flowcharts, hierarchies) - NOT timelines
• DaisyUI: Layout components and storytelling patterns

FOR IMAGES: Add **image_requirements** with scene description

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 QUICK EXAMPLES

TITLE SLIDE (ALWAYS FIRST):
- layout_index: [select the appropriate layout for titles]
- slide_purpose: "Introduce presentation topic and set context"
- is_html: false, is_image: false

TEXT SLIDE:
- layout_index: [select layout with text/content placeholders]
- slide_purpose: "Introduce company credibility"
- is_html: false, is_image: false

HTML SLIDE (Timeline):
- layout_index: [select layout with Picture/Image placeholder]
- slide_purpose: "Show project roadmap phases"
- is_html: true, is_image: false
- html_requirements: "D3.js timeline: 6-month roadmap with phase markers"

IMAGE SLIDE (Team):
- layout_index: [select layout with Picture placeholder]  
- slide_purpose: "Showcase project team"
- is_html: false, is_image: true
- image_requirements: "Professional team photo, clean lighting, brand colors"

Create slides with logical narrative flow starting with title slide. Focus on strategic layout selection based on available layouts."""


def get_planning_system_prompt() -> str:
    """Get the optimized system prompt for presentation planning"""
    return """You are an expert presentation designer creating strategic, engaging presentations with precise placeholder-specific content requirements.

🎯 CORE MISSION: Create detailed presentation plans that specify exactly which placeholders need HTML, images, or text content.

🔑 KEY RESPONSIBILITIES:
1. **Title Slide First**: ALWAYS start with a title slide using any layout designed for titles/intros
2. **Strategic Layout Selection**: SELECT SPECIFIC LAYOUT_INDEX NUMBERS based on placeholder requirements
3. **Placeholder-Specific Planning**: Identify which placeholders need HTML, images, or text content
4. **Image vs HTML Detection**: Distinguish between photographic/scene requests and data visualization needs
5. **Detailed Specifications**: Provide comprehensive guidance for each slide and placeholder
6. **Content Flow Design**: Ensure logical narrative progression starting after the title slide

🏗️ PLACEHOLDER CONTENT TYPES:
• **text**: Regular text content (titles, bullet points, descriptions)
• **html**: HTML visualizations (charts, timelines, comparisons, interactive elements)
• **image**: AI-generated images (photos, scenes, illustrations, conceptual visuals)

🚨 CRITICAL DISTINCTION:
• **HTML content**: For data visualizations, charts, timelines, processes, comparisons
• **Image content**: For photographic scenes, illustrations, conceptual visuals (e.g., "photo of office workspace", "illustration of teamwork")

🎯 LAYOUT SELECTION CRITERIA:
When selecting layout_index for each slide:
• **READ the available layouts** and their placeholder names carefully
• **CRITICAL MATCHING RULES**:
  - If is_html=true → MUST select a layout with "Picture" or "Image" placeholder
  - If is_image=true → MUST select a layout with "Picture" or "Image" placeholder  
  - If both are false → Select a layout with text/content placeholders
• **MATCH content needs to placeholders**: HTML and images require picture placeholders
• **SELECT by actual requirements**: Don't use sequential indices (0,1,2,3...) - choose based on content fit
• **CONSIDER placeholder count**: Match the number of content pieces to available placeholders
• **PRIORITIZE appropriate layouts**: Text-heavy content → text layouts, Visual content → picture layouts

📋 SPECIFICATION REQUIREMENTS:

For EVERY slide, provide ALL of these fields:
• **layout_index**: THE SPECIFIC LAYOUT INDEX NUMBER from available layouts (REQUIRED!)
• **slide_purpose**: Clear, concise purpose (1-2 sentences)
• **detailed_purpose**: Comprehensive explanation (3-4 sentences)
• **content_structure**: Specific organization ("2-column layout", "5-step process")
• **visual_elements**: Required visuals ("icons, arrows, timeline markers")
• **key_information**: Essential content points (3-5 items)
• **is_html**: true if ANY placeholder needs HTML content
• **is_image**: true if ANY placeholder needs image generation
• **placeholder_requirements**: List specifying content type for each placeholder

🎯 PLACEHOLDER REQUIREMENTS FORMAT:
For each placeholder that needs special content, specify:
- placeholder_name: "exact_placeholder_name"
- content_type: "text" | "html" | "image"
- description: "detailed description of what to generate"

For HTML content, ALSO add:
• **html_requirements**: Detailed visualization specs using creative DaisyUI storytelling patterns

For image content, ALSO add:
• **image_requirements**: Detailed scene/visual description for AI image generation

🎨 HTML DECISION FRAMEWORK:

SET is_html: true FOR visual content requiring:
✅ **INFOGRAPHICS**: ANY slide described as "infographic" MUST have is_html: true
✅ **Conceptual Diagrams**: Visual representations of concepts, systems, architectures
✅ **Visual Explanations**: Educational diagrams, concept visualizations, medical/scientific diagrams
✅ **Hero Journeys**: Problem statements, challenges, solution presentations
✅ **Transformation Stories**: Before/during/after scenarios, business evolution
✅ **Process Excellence**: Implementation roadmaps, step-by-step procedures
✅ **Metrics Dashboards**: Impact results, KPIs, performance visualization
✅ **Comparison Frameworks**: Feature comparisons, competitive analysis
✅ **Progress Tracking**: Project phases, completion status, roadmap updates
✅ Timelines, workflows, hierarchies, complex data relationships

SET is_html: false FOR simple content like:
❌ Basic text, bullet points, titles
❌ Icon-heavy content (use icon placeholders)
❌ Standard charts (use chart placeholders)

🎯 SUCCESS CRITERIA:
• Specifications must be detailed enough for accurate content generation
• Each slide must advance the overall narrative
• HTML visualizations should enhance understanding, not complicate
• Layout choices should match content requirements
• Presentation should tell a compelling, coherent story

Focus on creating presentations that are both visually engaging and strategically sound."""
