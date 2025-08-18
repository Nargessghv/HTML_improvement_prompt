#!/usr/bin/env python
"""
Debug runner for slide generation workflow
Allows direct execution with predefined parameters for debugging with breakpoints
"""

import os
import sys
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path to handle relative imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Now import from src as a package
from src.workflow import SlideGenerationWorkflow
from src.template_manager import resolve_template_path, get_template_manager
from src.database import get_supabase_client


class DebugRunner:
    """Debug runner for slide generation with predefined parameters"""
    
    def __init__(self):
        """Initialize the debug runner"""
        self.db = get_supabase_client()
        self.workflow = SlideGenerationWorkflow()
        
    def create_debug_project(self, topic: str, description: str, template_name: str) -> Dict[str, Any]:
        """Create a debug project in the database"""
        project_id = str(uuid.uuid4())
        
        # Create project record
        project_data = {
            "id": project_id,
            "title": f"Debug: {topic}",
            "topic": description,  # Store the full description as topic
            "status": "processing",
            "metadata": {
                "template_name": template_name,
                "debug_mode": True
            }
        }
        
        # If you want to persist in database (optional for debugging)
        # Uncomment the following lines to save to database:
        # result = self.db.client.table("projects").insert(project_data).execute()
        # if result.data:
        #     print(f"✅ Created debug project: {project_id}")
        
        return project_data
    
    def create_simple_outline(self, topic: str, description: str) -> Dict[str, Any]:
        """Create a simple 2-slide outline based on the description"""
        return {
            "title": topic,
            "topic": description,
            "slides": [
                {
                    "slide_number": 1,
                    "title": "What is an AI Agent?",
                    "content_type": "text",
                    "key_points": [
                        "Definition of AI agents",
                        "Key characteristics",
                        "How they differ from traditional software",
                        "Examples in practice"
                    ],
                    "layout_type": "content",
                    "notes": "Text-based slide explaining AI agents conceptually"
                },
                {
                    "slide_number": 2,
                    "title": "AI Agent Architecture",
                    "content_type": "html",
                    "key_points": [
                        "Core components of an AI agent",
                        "Input processing",
                        "Decision making",
                        "Action execution"
                    ],
                    "layout_type": "content",
                    "notes": "Simple HTML visualization showing AI agent components",
                    "html_content_suggestion": "Create a simple text-based diagram showing the flow: Input → Processing → Decision → Action"
                }
            ]
        }
    
    async def run_workflow(
        self,
        topic: str = "Training Deck",
        description: str = "Two slides, one text and one html on what is an AI agent. The HTML should be very simple text only",
        template_name: str = "ekona_slides_template_new"
    ):
        """Run the slide generation workflow with predefined parameters"""
        
        print("=" * 80)
        print("🚀 Starting Debug Slide Generation")
        print("=" * 80)
        print(f"Topic: {topic}")
        print(f"Description: {description}")
        print(f"Template: {template_name}")
        print("=" * 80)
        
        # Create debug project
        project = self.create_debug_project(topic, description, template_name)
        project_id = project["id"]
        
        # Create simple outline
        approved_outline = self.create_simple_outline(topic, description)
        print(f"\n📋 Created outline with {len(approved_outline['slides'])} slides")
        
        # Resolve template paths
        template_path = resolve_template_path(template_name)
        print(f"\n📁 Template path: {template_path}")
        
        # Get template folder path for locked backgrounds
        manager = get_template_manager()
        template_folder_path = manager.get_template_folder_path(template_name)
        print(f"📁 Template folder: {template_folder_path}")
        
        # Set output path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"debug_{topic.lower().replace(' ', '_')}_{timestamp}.pptx"
        output_path = os.path.join("generated_presentations", output_filename)
        
        # Ensure output directory exists
        os.makedirs("generated_presentations", exist_ok=True)
        
        print(f"\n📂 Output will be saved to: {output_path}")
        
        # Set up a simple callback for progress tracking
        def progress_callback(project_id: str, agent_name: str, status: str, **kwargs):
            """Simple progress callback for debugging"""
            timestamp = datetime.now().strftime("%H:%M:%S")
            if status == "started":
                print(f"\n[{timestamp}] ▶️  {agent_name}: Starting...")
            elif status == "completed":
                print(f"[{timestamp}] ✅ {agent_name}: Completed")
            elif status == "failed":
                error = kwargs.get("error_message", "Unknown error")
                print(f"[{timestamp}] ❌ {agent_name}: Failed - {error}")
            else:
                print(f"[{timestamp}] ℹ️  {agent_name}: {status}")
        
        # Set the callback on workflow
        self.workflow.set_database_callback(progress_callback, project_id)
        
        print("\n" + "=" * 80)
        print("🔄 Starting Workflow Execution")
        print("=" * 80)
        
        # Check if parallel processing is enabled
        use_parallel = os.getenv("USE_PARALLEL_SLIDE_PROCESSING", "false").lower() == "true"
        
        if use_parallel:
            print("\n🚀 Using PARALLEL workflow")
            # Run parallel workflow
            result = await self.workflow.run_parallel_for_approved_outline(
                topic=description,  # Use full description as topic
                template_path=template_path,
                output_path=output_path,
                approved_outline=approved_outline,
                title=topic,
                template_folder_path=template_folder_path
            )
        else:
            print("\n🔄 Using SEQUENTIAL workflow")
            # Run standard sequential workflow
            result = self.workflow.run(
                topic=description,  # Use full description as topic
                template_path=template_path,
                template_folder_path=template_folder_path,
                output_path=output_path,
                title=topic,
                approved_outline=approved_outline
            )
        
        print("\n" + "=" * 80)
        print("📊 Workflow Results")
        print("=" * 80)
        
        if result.get("success"):
            print(f"✅ SUCCESS: Presentation created!")
            print(f"📁 Output: {result.get('presentation_path')}")
            print(f"📊 Slides: {result.get('slide_count', 0)}")
            
            # Print slide details if available
            slide_contents = result.get("slide_contents", [])
            if slide_contents:
                print("\n📑 Slide Details:")
                for i, slide in enumerate(slide_contents, 1):
                    print(f"  Slide {i}: {slide.get('title', 'Untitled')}")
                    if slide.get("html_content"):
                        print(f"    - Has HTML content")
                    if slide.get("refined_html"):
                        print(f"    - Has refined HTML")
        else:
            print(f"❌ FAILED: {result.get('error', 'Unknown error')}")
        
        return result


async def main():
    """Main entry point for debug runner"""
    
    # You can modify these parameters for different test scenarios
    TOPIC = "Training Deck"
    DESCRIPTION = "Two slides, one text and one html on what is an AI agent. The HTML should be very simple text only"
    TEMPLATE = "ekona_slides_template_new"
    
    # Create and run debug runner
    runner = DebugRunner()
    
    try:
        result = await runner.run_workflow(
            topic=TOPIC,
            description=DESCRIPTION,
            template_name=TEMPLATE
        )
        
        print("\n" + "=" * 80)
        print("🎉 Debug run completed!")
        print("=" * 80)
        
        # Set breakpoint here to inspect final result
        return result
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
        return None
    except Exception as e:
        print(f"\n\n❌ Error during execution: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # Run the async main function
    result = asyncio.run(main())
    
    # Keep console open to review output
    if result:
        print("\n✅ Presentation generated successfully!")
        print(f"📁 Check: {result.get('presentation_path', 'generated_presentations/')}")
    else:
        print("\n⚠️ Generation did not complete successfully")
    
    print("\nPress Enter to exit...")
    input()