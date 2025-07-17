#!/usr/bin/env python3
"""
Auto Slides Generator

A command-line tool for automatically generating PowerPoint presentations
using AI-powered content generation with enhanced HTML visualizations.

Usage:
    python auto_slides.py "Your presentation topic" [options]
"""

import argparse
import os
import sys
from datetime import datetime

from src.workflow import SlideGenerationWorkflow


def main():
    """Main entry point for the auto-slides generator"""
    parser = argparse.ArgumentParser(
        description="Generate PowerPoint presentations automatically using AI agents "
        "with HTML visualizations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python auto_slides.py "Machine Learning Basics"
  python auto_slides.py "Climate Change Impact" --output climate_presentation
  python auto_slides.py "Product Launch Strategy" --layouts 0,1,2,5 --preview
  python auto_slides.py "Data Science Overview" --template custom_template.pptx
  
HTML Visualization Examples:
  python auto_slides.py "Product Development Timeline"     # HTML timelines
  python auto_slides.py "Software Development Process"    # HTML process flows  
  python auto_slides.py "Digital Transformation Journey"  # HTML roadmaps
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
        help="Show workflow plan without creating PowerPoint file",
    )

    parser.add_argument(
        "--analyze", "-a", action="store_true", help="Analyze template layouts and exit"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with detailed logging",
    )

    # Parse arguments
    args = parser.parse_args()

    # Validate template file exists
    if not os.path.exists(args.template):
        print(f"Error: Template file '{args.template}' not found.")
        print("Make sure you have a PowerPoint template file.")
        sys.exit(1)

    try:
        # Initialize the agent workflow
        workflow = SlideGenerationWorkflow()

        # Handle analyze mode
        if args.analyze:
            print("🔍 Analyzing template layouts using AI agents...")
            from src.agent_main import analyze_template_with_agents

            analyze_template_with_agents(args.template)
            return

        # Validate required arguments for generation
        if not args.topic and not args.analyze:
            parser.error("topic is required unless using --analyze mode")

        # Parse layout indices if provided
        layout_indices = None
        if args.layouts:
            try:
                layout_indices = [int(x.strip()) for x in args.layouts.split(",")]
                print(f"🎯 Using specific layouts: {layout_indices}")
            except ValueError:
                print("Error: Invalid layout indices. Use comma-separated integers.")
                sys.exit(1)

        # Handle preview mode
        if args.preview:
            print("📋 Generating workflow preview...")
            from src.agent_main import preview_workflow_plan

            preview_workflow_plan(workflow, args.topic, args.template)
            return

        # Generate output filename if not provided
        if args.output is None:
            # Create safe filename from topic
            safe_topic = "".join(
                c for c in args.topic if c.isalnum() or c in (" ", "-", "_")
            ).rstrip()
            safe_topic = safe_topic.replace(" ", "_")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            args.output = f"agent_generated_{safe_topic}_{timestamp}"

        # Create the presentation using AI agents with HTML generation
        print(f"🤖 Creating presentation with AI agents: '{args.topic}'")
        print(
            "✨ Enhanced with HTML visualizations for timelines, processes, "
            "and workflows"
        )

        result = workflow.run(
            topic=args.topic,
            template_path=args.template,
            output_path=args.output,
            layout_indices=layout_indices,
        )

        if result["success"]:
            print("\n✅ Presentation successfully created with AI agents!")
            print(f"📄 File: {result['presentation_path']}")
            print(f"🎯 Topic: {args.topic}")
            print(f"📊 Slides: {result['slide_count']}")
            print(f"🎨 Layouts used: {result['layouts_used']}")

            # Show agent results
            agent_results = result.get("agent_results", {})
            if agent_results.get("layout_analysis"):
                print("✅ Layout analysis completed")
            if agent_results.get("presentation_planning"):
                print("✅ Presentation planning completed")
            if agent_results.get("content_generation"):
                print("✅ Content generation completed")
            if agent_results.get("quality_review"):
                print("✅ Quality review completed")
            if agent_results.get("slide_assembly"):
                print("✅ Slide assembly completed")

            # Show HTML generation info
            print("🎨 HTML visualizations: Auto-generated for timeline/process content")

        else:
            error_msg = result.get("error", "Unknown error")
            print(f"\n❌ Presentation creation failed: {error_msg}")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args.debug:
            import traceback

            traceback.print_exc()
        sys.exit(1)


def show_help():
    """Show helpful information about using the tool"""
    help_text = """
🤖 Auto Slides Generator Help - Enhanced with AI Agents & HTML Visualizations

SETUP:
1. Make sure you have a PowerPoint template file (ekona_slides_template_new.pptx)
2. Set your OpenAI API key in environment:
   export OPENAI_API_KEY=your_api_key_here

BASIC USAGE:
  python auto_slides.py "Your Topic Here"

🎨 HTML VISUALIZATION TOPICS (Auto-Enhanced):
  python auto_slides.py "Product Development Timeline"
  python auto_slides.py "Software Development Process Flow"
  python auto_slides.py "Digital Transformation Journey"
  python auto_slides.py "Customer Onboarding Workflow"
  python auto_slides.py "Project Phases and Milestones"

ADVANCED OPTIONS:
  --output/-o     : Custom output filename
  --template/-t   : Use different template file  
  --layouts/-l    : Specify which layouts to use (e.g., "0,1,3")
  --preview/-p    : Preview workflow plan without creating slides
  --analyze/-a    : Analyze template layouts using AI agents

EXAMPLES:
  # Basic usage with auto HTML generation
  python auto_slides.py "Introduction to Python"
  
  # Timeline content (auto-generates HTML visualizations)
  python auto_slides.py "Company Growth Timeline" --output growth_presentation
  
  # Preview workflow plan first
  python auto_slides.py "Machine Learning Process" --preview
  
  # Use specific layouts
  python auto_slides.py "Business Strategy" --layouts 0,1,3,7
  
  # Analyze your template with AI
  python auto_slides.py --analyze

NEW FEATURES:
✨ AI Agent Workflow: 6-step process with layout analysis, planning, content generation, 
   HTML visualization, quality review, and assembly
🎨 HTML Visualizations: Auto-generated for timelines, processes, workflows, 
   and comparisons
🎯 Smart Planning: AI automatically selects Layout 3 for visual content
📊 Enhanced Monitoring: Full workflow tracing and performance metrics

TIPS:
- Use timeline/process topics for automatic HTML visualizations
- The AI planner will automatically select appropriate layouts
- Preview workflow plans with --preview to see the AI's strategy
- HTML visualizations are generated for Layout 3 content automatically
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
