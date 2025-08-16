"""
Agent-Based Main Module

New main entry point that uses Langgraph agents and Langfuse monitoring
for PowerPoint slide generation with enhanced orchestration and observability.
"""

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from .workflow import SlideGenerationWorkflow

# Load environment variables
load_dotenv()


def main():
    """
    Main entry point for agent-based slide generation

    Provides the same CLI interface as the original auto_slides.py
    but uses the new Langgraph agent workflow internally.
    """
    parser = argparse.ArgumentParser(
        description="Generate PowerPoint presentations using AI agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.agent_main "Machine Learning Basics"
  python -m src.agent_main "Climate Change Impact" --output climate_presentation
  python -m src.agent_main "Product Launch Strategy" --layouts 0,1,2,5 
  python -m src.agent_main "Data Science Overview" --template custom_template.pptx
        """,
    )

    # Required arguments
    parser.add_argument("topic", nargs="?", help="The topic for the presentation")

    # Optional arguments
    parser.add_argument(
        "--output", "-o", help="Output file path (without extension)", default=None
    )

    parser.add_argument(
        "--template",
        "-t",
        help="Path to PowerPoint template file (auto-selects from templates/ if not provided)",
        default=None,
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

    parser.add_argument(
        "--dual-path",
        action="store_true",
        help="Use enhanced dual-path generation (individual slides + final presentation)",
    )

    # Parse arguments
    args = parser.parse_args()

    # Validate required arguments
    if not args.analyze and not args.topic:
        parser.error("topic is required unless using --analyze mode")

    # Handle template selection
    if args.template is None:
        # Auto-select default template
        from src.template_manager import TemplateManager
        tm = TemplateManager()
        args.template = tm.get_default_template()
        if args.template is None:
            print("Error: No templates found in templates directory.")
            print("Make sure you have a PowerPoint template file.")
            sys.exit(1)
    
    # Validate template file exists
    if not os.path.exists(args.template):
        print(f"Error: Template file '{args.template}' not found.")
        print("Make sure you have a PowerPoint template file.")
        sys.exit(1)

    try:
        # Initialize workflow
        workflow = SlideGenerationWorkflow()

        # Handle analyze mode
        if args.analyze:
            print("🔍 Analyzing template layouts using AI agents...")
            return analyze_template_with_agents(args.template)

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
            return preview_workflow_plan(workflow, args.topic, args.template)

        # Generate output filename if not provided
        if args.output is None:
            # Create safe filename from topic
            safe_topic = "".join(
                c for c in args.topic if c.isalnum() or c in (" ", "-", "_")
            ).rstrip()
            safe_topic = safe_topic.replace(" ", "_")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Note: SlideGenerator will automatically place in generated_presentations/
            args.output = f"agent_generated_{safe_topic}_{timestamp}"

        # Create the presentation using agents
        if args.dual_path:
            print(f"🤖🔄 Creating presentation with ENHANCED DUAL-PATH agents: '{args.topic}'")
            print("📱 This will generate individual slides for preview AND final presentation")
            print("✨ Perfect formatting consistency guaranteed!")
        else:
            print(f"🤖 Creating presentation with AI agents: '{args.topic}'")

        # Create workflow with parallel HTML refinement enabled by default
        workflow = SlideGenerationWorkflow(use_parallel_html_refinement=True)

        results = workflow.run(
            topic=args.topic,
            template_path=args.template,
            output_path=args.output,
            layout_indices=layout_indices,
        )

        # Process results
        if results["success"]:
            if args.dual_path:
                print("\n🎉 ENHANCED DUAL-PATH presentation generation completed successfully!")
                print("✨ Perfect formatting consistency achieved!")
                
                # Show individual slides info if available
                individual_slides = results.get("individual_slides", [])
                if individual_slides:
                    successful_slides = [s for s in individual_slides if s.get("success")]
                    print(f"📱 Individual slides for preview: {len(successful_slides)}/{len(individual_slides)}")
                    for i, slide in enumerate(successful_slides[:3]):  # Show first 3
                        if slide.get("file_url"):
                            print(f"   • Slide {i+1}: {slide['file_url']}")
                    if len(successful_slides) > 3:
                        print(f"   • ... and {len(successful_slides) - 3} more slides")
                
                print(f"📄 Final presentation: {results['presentation_path']}")
                print("🔄 Future slide adjustments: Use regenerate_individual_slide API")
            else:
                print("\n🎉 Agent-based presentation generation completed successfully!")
            
            print(f"📄 File: {results['presentation_path']}")
            print(f"🎯 Topic: {args.topic}")
            print(f"📊 Slides generated: {results['slide_count']}")
            print(f"🎨 Layouts used: {results['layouts_used']}")
            
            if args.dual_path:
                print("🤖 Enhanced Agent workflow: Layout → Planning → Content → Quality → DUAL-PATH Assembly")
            else:
                print("🤖 Agent workflow: Layout → Planning → Content → Quality → Assembly")

            # Show monitoring info if available
            if os.getenv("LANGFUSE_PUBLIC_KEY"):
                print("📈 View detailed analytics at your Langfuse dashboard")

        else:
            print(f"\n❌ Agent workflow failed: {results['error']}")
            print(f"📍 Failed at step: {results['current_step']}")
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


def analyze_template_with_agents(template_path: str) -> None:
    """
    Analyze template using the layout analysis agent

    Args:
        template_path: Path to template file
    """
    from .agents import LayoutAnalysisAgent, SlideGenerationState

    print("🔍 Running layout analysis with AI agent...")

    # Create minimal state for analysis
    state: SlideGenerationState = {
        "topic": "analysis",
        "template_path": template_path,
        "output_path": "analysis",
        "layout_indices": None,
        "current_step": "starting",
        "error_message": None,
        "retry_count": 0,
        "layouts_info": None,
        "dynamic_models": None,
        "presentation_plan": None,
        "selected_layouts": None,
        "slide_contents": None,
        "presentation_path": None,
        "success": False,
        "monitor_trace": None,
    }

    # Run layout analysis agent
    agent = LayoutAnalysisAgent()
    result_state = agent.execute(state)

    layouts_info = result_state.get("layouts_info")
    if layouts_info:
        print(f"\n📊 Analysis Results: {len(layouts_info)} layouts found")

        for idx, info in layouts_info.items():
            print(f"\n🎨 Layout {idx}: {info['name']}")
            placeholders = info.get("placeholders", [])
            print(f"   📝 Placeholders: {len(placeholders)}")
            for placeholder in placeholders[:3]:  # Show first 3
                name = placeholder.get("name", "Unknown")
                ptype = placeholder.get("type", "Unknown")
                print(f"      • {name} ({ptype})")
            if len(placeholders) > 3:
                print(f"      ... and {len(placeholders) - 3} more")

        msg = "Layout analysis complete. Template is ready for agent-based generation."
        print(f"\n✅ {msg}")
    else:
        print("❌ Layout analysis failed")


def preview_workflow_plan(
    workflow: SlideGenerationWorkflow, topic: str, template_path: str
) -> None:
    """
    Preview the workflow plan without generating slides

    Args:
        workflow: Workflow instance
        topic: Presentation topic
        template_path: Template file path
    """
    print(f"📋 Workflow Preview for: '{topic}'")
    print("=" * 50)

    print("🔄 Agent Workflow Steps:")
    print("  1. 🔍 Layout Analysis Agent")
    print("     └── Analyze template and create dynamic models")
    print("  2. 📋 Presentation Planning Agent")
    print("     └── Create intelligent slide structure using LLM")
    print("  3. ✍️  Content Generation Agent")
    print("     └── Generate contextual content for each slide")
    print("  4. 🎯 Quality Review Agent")
    print("     └── Assess content quality and metrics")
    print("  5. 🔧 Slide Assembly Agent")
    print("     └── Create final PowerPoint presentation")

    print("\n📊 Monitoring & Observability:")
    if os.getenv("LANGFUSE_PUBLIC_KEY"):
        print("  ✅ Langfuse monitoring enabled")
        print("     └── Full workflow tracking and LLM call monitoring")
    else:
        print("  ⚠️  Langfuse monitoring disabled (no API keys)")
        print("     └── Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY to enable")

    print("\n🎯 Benefits of Agent-Based Approach:")
    print("  • Modular, fault-tolerant design")
    print("  • Comprehensive monitoring and analytics")
    print("  • Intelligent content planning and optimization")
    print("  • Quality assessment and feedback loops")
    print("  • Better error handling and recovery")

    print(f"\n🚀 Ready to generate presentation for: '{topic}'")
    print("   Remove --preview flag to start generation.")


async def generate_presentation_with_parallel_refinement(
    topic: str,
    template_path: Optional[str] = None,
    output_path: Optional[str] = None,
    layout_indices: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """
    Generate a presentation with parallel HTML refinement for better performance

    This function uses the async version of HTML refinement to process all
    HTML slides in parallel, which can significantly improve performance
    for presentations with multiple HTML visualizations.

    Args:
        topic: Presentation topic
        template_path: Path to PowerPoint template (defaults to standard template)
        output_path: Path to save generated presentation (defaults to generated_presentations/)
        layout_indices: Optional specific layouts to use

    Returns:
        Dictionary with workflow results and metadata
    """
    print("🚀 Starting slide generation with parallel HTML refinement...")
    print(f"📋 Topic: {topic}")

    # Resolve template if not specified
    if not template_path:
        from .template_manager import resolve_template_path
        template_path = resolve_template_path()
    print(f"📁 Template: {template_path}")

    # Generate output path if not specified
    if not output_path:
        # Create timestamped filename in the generated_presentations folder
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        safe_topic = "".join(c if c.isalnum() else "_" for c in topic[:30])
        output_dir = Path("generated_presentations")
        output_dir.mkdir(exist_ok=True)
        output_path = str(output_dir / f"{safe_topic}_{timestamp}.pptx")
    print(f"💾 Output: {output_path}")

    # Initialize workflow
    workflow = SlideGenerationWorkflow()

    # Execute workflow with parallel HTML refinement
    start_time = time.time()
    try:
        result = await workflow.run_with_parallel_refinement(
            topic=topic,
            template_path=template_path,
            output_path=output_path,
        )

        # Process results
        duration = time.time() - start_time
        print(f"✅ Presentation generated in {duration:.1f} seconds")

        # Convert SlideGenerationState to Dict
        result_dict = {
            "success": result.get("success", False),
            "presentation_path": result.get("presentation_path"),
            "execution_time": duration,
        }

        if result_dict["success"]:
            print(f"📊 Presentation saved to: {result_dict['presentation_path']}")
        else:
            print(
                f"❌ Generation failed: {result.get('error_message', 'Unknown error')}"
            )

        return result_dict

    except Exception as e:
        duration = time.time() - start_time
        print(f"❌ Error during generation: {e}")
        return {
            "success": False,
            "error": str(e),
            "presentation_path": None,
            "execution_time": duration,
        }


async def main_async():
    """
    Async entry point for parallel HTML refinement demo
    """
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.agent_main parallel_demo 'Your presentation topic'")
        return

    topic = sys.argv[2] if len(sys.argv) > 2 else "AI-powered Presentation Generation"
    result = await generate_presentation_with_parallel_refinement(topic)

    if result["success"]:
        print("\n✅ Parallel HTML refinement demo completed successfully!")
    else:
        print(
            f"\n❌ Parallel HTML refinement demo failed: {result.get('error', 'Unknown error')}"
        )


def show_agent_help():
    """Show detailed help for agent-based slide generation"""
    help_text = """
🤖 Agent-Based Slide Generator Help

WHAT'S NEW:
This new agent-based system uses Langgraph for workflow orchestration
and Langfuse for comprehensive monitoring and analytics.

SETUP:
1. Install dependencies: pip install -r requirements.txt
2. Set your OpenAI API key in .env file:
   OPENAI_API_KEY=your_api_key_here
3. Optional: Set Langfuse keys for monitoring:
   LANGFUSE_PUBLIC_KEY=your_public_key
   LANGFUSE_SECRET_KEY=your_secret_key

AGENT WORKFLOW:
1. 🔍 Layout Analysis: Analyzes template structure
2. 📋 Planning: Creates intelligent presentation plan
3. ✍️  Content Generation: Generates contextual content
4. 🎯 Quality Review: Assesses content quality
5. 🔧 Assembly: Creates final PowerPoint

USAGE:
  python -m src.agent_main "Your Topic Here"

OPTIONS:
  --output/-o     : Custom output filename
  --template/-t   : Use different template file  
  --layouts/-l    : Specify which layouts to use
  --preview/-p    : Preview workflow without creating slides
  --analyze/-a    : Analyze template layouts
  --debug         : Enable debug mode
  --parallel      : Use parallel HTML refinement (experimental)

EXAMPLES:
  # Basic usage with agents
  python -m src.agent_main "Introduction to AI"
  
  # Preview the workflow plan
  python -m src.agent_main "Data Science" --preview
  
  # Analyze template with agents
  python -m src.agent_main --analyze
  
  # Custom output and specific layouts
  python -m src.agent_main "Business Strategy" --output strategy --layouts 0,1,2
  
  # Use parallel HTML refinement
  python -m src.agent_main parallel_demo "AI Technologies"

MONITORING:
With Langfuse configured, you get:
- Complete workflow tracing
- LLM call monitoring and costs
- Content quality metrics
- Performance analytics
- Error tracking and debugging

Visit your Langfuse dashboard to see detailed analytics!
"""
    print(help_text)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "parallel_demo":
        import asyncio

        asyncio.run(main_async())
    # Check for help flags
    if len(sys.argv) == 1 or "--help" in sys.argv or "-h" in sys.argv:
        if "--help" in sys.argv or "-h" in sys.argv:
            main()  # Let argparse handle --help
        else:
            show_agent_help()
    else:
        main()
