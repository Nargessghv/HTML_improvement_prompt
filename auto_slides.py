#!/usr/bin/env python3
"""
Auto Slides Generator

A command-line tool for automatically generating PowerPoint presentations
using AI-powered content generation.

Usage:
    python auto_slides.py "Your presentation topic" [options]
"""

import argparse
import os
import sys
from datetime import datetime

from src.slide_generator import SlideGenerator


def main():
    """Main entry point for the auto-slides generator"""
    parser = argparse.ArgumentParser(
        description="Generate PowerPoint presentations automatically using AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python auto_slides.py "Machine Learning Basics"
  python auto_slides.py "Climate Change Impact" --output climate_presentation
  python auto_slides.py "Product Launch Strategy" --layouts 0,1,2,5 --preview
  python auto_slides.py "Data Science Overview" --template custom_template.pptx
        """,
    )

    # Required arguments
    parser.add_argument("topic", help="The topic for the presentation")

    # Optional arguments
    parser.add_argument(
        "--output", "-o", help="Output file path (without extension)", default=None
    )

    parser.add_argument(
        "--template",
        "-t",
        help="Path to PowerPoint template file",
        default="ekona_slides_template_new.pptx",
    )

    parser.add_argument(
        "--layouts",
        "-l",
        help="Comma-separated list of layout indices to use (e.g., '0,1,3')",
        default=None,
    )

    parser.add_argument(
        "--preview",
        "-p",
        action="store_true",
        help="Show content preview without creating PowerPoint file",
    )

    parser.add_argument(
        "--analyze", "-a", action="store_true", help="Analyze template layouts and exit"
    )

    parser.add_argument(
        "--api-key",
        help="OpenAI API key (can also use OPENAI_API_KEY environment variable)",
        default=None,
    )

    # Parse arguments
    args = parser.parse_args()

    # Validate template file exists
    if not os.path.exists(args.template):
        print(f"Error: Template file '{args.template}' not found.")
        print("Make sure you have a PowerPoint template file.")
        sys.exit(1)

    try:
        # Initialize slide generator
        generator = SlideGenerator(args.template, args.api_key)

        # Handle analyze mode
        if args.analyze:
            print("Analyzing template layouts...")
            generator.print_template_analysis()
            return

        # Parse layout indices if provided
        layout_indices = None
        if args.layouts:
            try:
                layout_indices = [int(x.strip()) for x in args.layouts.split(",")]
                print(f"Using specific layouts: {layout_indices}")
            except ValueError:
                print("Error: Invalid layout indices. Use comma-separated integers.")
                sys.exit(1)

        # Handle preview mode
        if args.preview:
            print("Generating content preview...")
            preview = generator.preview_content(args.topic)
            print("\n" + preview)
            return

        # Generate output filename if not provided
        if args.output is None:
            # Create safe filename from topic
            safe_topic = "".join(
                c for c in args.topic if c.isalnum() or c in (" ", "-", "_")
            ).rstrip()
            safe_topic = safe_topic.replace(" ", "_")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            args.output = f"{safe_topic}_{timestamp}"

        # Create the presentation
        print(f"Generating presentation: '{args.topic}'")
        output_path = generator.create_presentation(
            args.topic, args.output, layout_indices
        )

        print("\n✅ Presentation successfully created!")
        print(f"📄 File: {output_path}")
        print(f"🎯 Topic: {args.topic}")

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if "--debug" in sys.argv:
            import traceback

            traceback.print_exc()
        sys.exit(1)


def show_help():
    """Show helpful information about using the tool"""
    help_text = """
🤖 Auto Slides Generator Help

SETUP:
1. Make sure you have a PowerPoint template file (template.pptx)
2. Set your OpenAI API key in .env file:
   OPENAI_API_KEY=your_api_key_here

BASIC USAGE:
  python auto_slides.py "Your Topic Here"

ADVANCED OPTIONS:
  --output/-o     : Custom output filename
  --template/-t   : Use different template file  
  --layouts/-l    : Specify which layouts to use (e.g., "0,1,3")
  --preview/-p    : Preview content without creating slides
  --analyze/-a    : Analyze template layouts

EXAMPLES:
  # Basic usage
  python auto_slides.py "Introduction to Python"
  
  # Custom output name
  python auto_slides.py "Data Science" --output my_presentation
  
  # Preview content first
  python auto_slides.py "Machine Learning" --preview
  
  # Use specific layouts
  python auto_slides.py "Business Strategy" --layouts 0,1,2,5
  
  # Analyze your template
  python auto_slides.py --analyze

TIPS:
- Use descriptive, specific topics for better results
- Preview content first with --preview to see what will be generated
- Analyze your template with --analyze to understand available layouts
- The tool works best with clear, focused presentation topics
"""
    print(help_text)


if __name__ == "__main__":
    # Check for help flags
    if len(sys.argv) == 1 or "--help" in sys.argv or "-h" in sys.argv:
        if "--help" in sys.argv or "-h" in sys.argv:
            main()  # Let argparse handle --help
        else:
            show_help()
    else:
        main()
