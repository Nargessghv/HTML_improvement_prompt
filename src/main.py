"""
Main script for generating PowerPoint presentations from a custom layout file.
"""

import argparse
import io
import json
import logging
import os
from pathlib import Path

import cairosvg
import openai
from dotenv import load_dotenv
from pptx import Presentation
from pptx.util import Inches

# Load environment variables at the very top
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Slide configuration from python-pptx defaults (for a 16:9 slide)
SLIDE_WIDTH = Inches(10)
SLIDE_HEIGHT = Inches(7.5)


def generate_content_for_layout(topic: str, layout: dict) -> dict:
    """
    Generates content using an LLM to fill a predefined layout structure.
    """
    logging.info(f"Generating content for topic '{topic}' based on layout file...")
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set.")

    model_name = os.getenv("OPENAI_MODEL", "gpt-4o")
    logging.info(f"Using model: {model_name}")

    # Create a simplified structure for the LLM prompt
    prompt_layout = {"slides": []}
    for slide_layout in layout["slides"]:
        slide_prompt = {"content_blocks": [], "icons": []}
        for block in slide_layout.get("content_blocks", []):
            slide_prompt["content_blocks"].append(
                {"id": block["id"], "type": block["type"]}
            )
        for icon in slide_layout.get("icons", []):
            slide_prompt["icons"].append({"id": icon["id"]})
        prompt_layout["slides"].append(slide_prompt)

    system_prompt = f"""
    You are a content creator for a presentation on '{topic}'.
    Your task is to fill in the content for a predefined slide layout.
    You will be given a JSON structure with "content_blocks" and "icons",
    each with a unique "id".

    Your response must be a single JSON object where the keys are the "id"s
    from the layout and the values are the content you generate.

    - For "content_blocks", provide a string for titles/subtitles, or a list
      of strings for body text (bullet points).
    - For "icons", provide a single, relevant icon name from the valid list.

    VALID LUCIDE ICONS:
    brain, lightbulb, target, users, shield, globe, rocket, chart-bar, 
    settings, heart, star, check-circle, arrow-right, trending-up, cpu, 
    database, cloud, lock, eye, camera, phone.

    EXAMPLE REQUEST LAYOUT:
    {{
        "slides": [
            {{
                "content_blocks": [{{"id": "title_1", "type": "title"}}],
                "icons": []
            }},
            {{
                "content_blocks": [
                    {{"id": "body_2", "type": "body"}},
                    {{"id": "title_2", "type": "title"}}
                ],
                "icons": [{{"id": "icon_2"}}]
            }}
        ]
    }}

    EXAMPLE JSON RESPONSE:
    {{
      "title_1": "The Main Topic",
      "title_2": "A Sub-Topic",
      "body_2": [
        "First bullet point about the sub-topic.",
        "Second bullet point with more details."
      ],
      "icon_2": "lightbulb"
    }}
    """

    try:
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        "Please generate content for the following layout:\n"
                        f"{json.dumps(prompt_layout, indent=2)}\n"
                        "Respond with a single JSON object."
                    ),
                },
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        if content:
            return json.loads(content)
        raise ValueError("OpenAI response content is empty.")
    except Exception as e:
        logging.error(f"Error generating content with OpenAI: {e}")
        raise


def create_presentation_from_layout(
    layout: dict, content: dict, template_path: str, output_path: str
):
    """
    Creates a PowerPoint presentation from a layout file and generated content.
    """
    prs = Presentation(template_path)

    # Find the "Blank" layout
    blank_layout = None
    for item in prs.slide_layouts:
        if item.name == "Blank":
            blank_layout = item
            break
    if not blank_layout:
        logging.warning("No 'Blank' layout found; using the first available layout.")
        blank_layout = prs.slide_layouts[0]

    for i, slide_layout in enumerate(layout["slides"]):
        slide = prs.slides.add_slide(blank_layout)
        logging.info(f"=== CREATING SLIDE {i+1} ===")

        # Create Content Blocks
        for block in slide_layout.get("content_blocks", []):
            content_id = block["id"]
            text_content = content.get(content_id)

            if not text_content:
                logging.warning(f"No content found for block id: {content_id}")
                continue

            try:
                # Calculate position and size from layout
                pos = block["position"]
                left = Inches(SLIDE_WIDTH.inches * pos["x"] / 100)
                top = Inches(SLIDE_HEIGHT.inches * pos["y"] / 100)
                width = Inches(SLIDE_WIDTH.inches * block["width"] / 100)
                height = Inches(2)  # Default height, will auto-adjust

                text_box = slide.shapes.add_textbox(left, top, width, height)
                tf = text_box.text_frame
                tf.clear()

                # Add text content
                if isinstance(text_content, list):
                    for j, point in enumerate(text_content):
                        p = tf.add_paragraph() if j > 0 else tf.paragraphs[0]
                        p.text = point
                        p.level = 1 if block["type"] == "body" else 0
                else:
                    tf.paragraphs[0].text = text_content

                # Apply basic formatting
                for p in tf.paragraphs:
                    font = p.font
                    if block["type"] == "title":
                        font.size = Inches(0.5)
                        font.bold = True
                    elif block["type"] == "subtitle":
                        font.size = Inches(0.3)
                        font.bold = False
                    elif block["type"] == "highlight":
                        font.size = Inches(0.4)
                        font.bold = True
                    else:  # body
                        font.size = Inches(0.2)
                logging.info(f"Added content block '{content_id}'")
            except Exception as e:
                logging.error(f"Error creating content block '{content_id}': {e}")

        # Add Icons
        for icon in slide_layout.get("icons", []):
            icon_id = icon["id"]
            icon_name = content.get(icon_id)

            if not icon_name:
                logging.warning(f"No icon name found for icon id: {icon_id}")
                continue

            try:
                svg_path = Path(f"node_modules/lucide-static/icons/{icon_name}.svg")
                if not svg_path.exists():
                    logging.warning(f"Icon '{icon_name}' not found at {svg_path}")
                    continue

                png_io = io.BytesIO()
                cairosvg.svg2png(
                    url=str(svg_path),
                    write_to=png_io,
                    dpi=300,
                    output_width=600,
                    output_height=600,
                )
                png_io.seek(0)

                # Determine icon size and position from layout
                size_map = {
                    "small": Inches(1),
                    "medium": Inches(1.5),
                    "large": Inches(2),
                }
                icon_size = size_map.get(icon.get("size", "medium"))
                pos = icon["position"]
                icon_x = Inches(SLIDE_WIDTH.inches * pos["x"] / 100)
                icon_y = Inches(SLIDE_HEIGHT.inches * pos["y"] / 100)

                slide.shapes.add_picture(png_io, icon_x, icon_y, icon_size, icon_size)
                logging.info(f"Added icon '{icon_name}' from id '{icon_id}'")
            except Exception as e:
                logging.error(f"Error adding icon '{icon_name}': {e}")

    prs.save(output_path)
    logging.info(f"Presentation saved to {output_path}")


def main():
    """
    Main function to orchestrate the presentation generation.
    """

    parser = argparse.ArgumentParser(
        description="Generate a PowerPoint from a layout file."
    )
    parser.add_argument("topic", type=str, help="The topic of the presentation.")
    parser.add_argument(
        "--layout",
        type=str,
        default="src/layout.json",
        help="Path to the layout JSON file.",
    )
    args = parser.parse_args()

    # 1. Load layout file
    try:
        with open(args.layout) as f:
            layout_definition = json.load(f)
    except FileNotFoundError:
        logging.error(f"Layout file not found at: {args.layout}")
        return
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON in layout file: {args.layout}")
        return

    # 2. Generate content based on layout
    presentation_content = generate_content_for_layout(args.topic, layout_definition)

    # 3. Create presentation
    output_dir = Path("generated_presentations")
    output_dir.mkdir(exist_ok=True)
    create_presentation_from_layout(
        layout_definition,
        presentation_content,
        "ekona_slides_template_new.pptx",
        str(output_dir / "custom_layout_presentation.pptx"),
    )

    logging.info("Presentation generated successfully!")


if __name__ == "__main__":
    main()
