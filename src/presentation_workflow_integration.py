"""
Integration example showing how to use DirectPresentationGenerator
instead of creating individual slides and merging them.
"""

from typing import List, Dict, Any, Optional
from .direct_presentation_generator import DirectPresentationGenerator
from .llm_client import SlideContent


class ImprovedPresentationWorkflow:
    """
    Example of how to integrate the direct presentation generation approach
    into your existing workflow to avoid formatting issues.
    """
    
    def __init__(self, template_path: str):
        self.template_path = template_path
        self.direct_generator = DirectPresentationGenerator(template_path)
    
    async def generate_presentation_with_perfect_formatting(
        self,
        project_id: str,
        output_path: str,
        slide_specifications: List[Dict[str, Any]],
        layouts_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a complete presentation with perfect formatting preservation
        
        This replaces the workflow of:
        1. Creating individual PPTX files
        2. Merging them (which loses formatting)
        
        With:
        1. Generate all slide content
        2. Create all slides directly in final presentation
        
        Args:
            project_id: Project identifier
            output_path: Final presentation path
            slide_specifications: List of slide specs (from your existing system)
            layouts_info: Layout analysis from your LayoutAnalysisAgent
            
        Returns:
            Result with success status and presentation info
        """
        try:
            # Step 1: Generate content for all slides
            # (Use your existing content generation agents)
            slide_contents = await self._generate_all_slide_contents(
                slide_specifications, layouts_info
            )
            
            # Step 2: Create complete presentation directly
            # This preserves ALL formatting because no copying occurs
            result = await self.direct_generator.generate_complete_presentation(
                project_id=project_id,
                output_path=output_path,
                slide_contents=slide_contents,
                layouts_info=layouts_info
            )
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Workflow failed: {str(e)}",
                "slides_added": 0
            }
    
    async def _generate_all_slide_contents(
        self,
        slide_specifications: List[Dict[str, Any]],
        layouts_info: Optional[Dict[str, Any]] = None
    ) -> List[SlideContent]:
        """
        Generate content for all slides using your existing content generation system
        
        This integrates with your existing:
        - ContentGenerationAgent
        - HTMLContentGenerationAgent
        - Any other content generation agents
        """
        slide_contents = []
        
        for i, slide_spec in enumerate(slide_specifications):
            try:
                # Use your existing content generation logic here
                # This is just an example structure
                slide_content = await self._generate_single_slide_content(
                    slide_spec, i + 1, layouts_info
                )
                
                if slide_content:
                    slide_contents.append(slide_content)
                    
            except Exception as e:
                print(f"Failed to generate content for slide {i + 1}: {e}")
                continue
        
        return slide_contents
    
    async def _generate_single_slide_content(
        self,
        slide_spec: Dict[str, Any],
        slide_number: int,
        layouts_info: Optional[Dict[str, Any]] = None
    ) -> Optional[SlideContent]:
        """
        Generate content for a single slide using your existing system
        
        Replace this with calls to your actual content generation agents:
        - Use your ContentGenerationAgent
        - Use your HTMLContentGenerationAgent if needed
        - Apply any refinements
        """
        # Example - replace with your actual content generation
        from .llm_client import SlideContent
        
        # This would use your existing content generation logic
        content = {
            "Title": slide_spec.get("title", f"Slide {slide_number}"),
            "Content": slide_spec.get("content", "Generated content"),
            # Add other placeholder content based on your system
        }
        
        layout_index = slide_spec.get("layout_index", 1)
        
        return SlideContent(
            layout_index=layout_index,
            content=content
        )


# Example of how to modify your existing workflow
async def example_integration_with_existing_system():
    """
    Example showing how to integrate this with your existing agent system
    """
    from pathlib import Path
    
    # Your existing template path
    template_path = "templates/ekona_slides_template_new/ekona_slides_template_new.pptx"
    
    # Initialize the improved workflow
    workflow = ImprovedPresentationWorkflow(template_path)
    
    # Example slide specifications (from your planning agent)
    slide_specs = [
        {
            "title": "Introduction",
            "content": "Welcome to our presentation",
            "layout_index": 0,  # Title slide
            "slide_type": "title"
        },
        {
            "title": "Key Points",
            "content": "Our main discussion topics",
            "layout_index": 1,  # Content slide
            "slide_type": "content"
        },
        {
            "title": "Timeline",
            "content": "timeline: Project milestones over time",
            "layout_index": 2,  # Layout with picture placeholder for timeline
            "slide_type": "timeline_visualization"
        }
    ]
    
    # Generate the complete presentation with perfect formatting
    result = await workflow.generate_presentation_with_perfect_formatting(
        project_id="example_project_123",
        output_path="generated_presentations/perfect_formatting_example.pptx",
        slide_specifications=slide_specs,
        layouts_info=None  # Your layout analysis results
    )
    
    if result["success"]:
        print(f"✅ Generated presentation with {result['slides_added']} slides")
        print(f"📁 Saved to: {result['output_path']}")
        print(f"📊 File size: {result['file_size']} bytes")
    else:
        print(f"❌ Failed: {result['error']}")


# Integration with your agent workflow
class AgentWorkflowIntegration:
    """
    Shows how to integrate with your existing 6-agent LangGraph workflow
    """
    
    async def run_improved_workflow(
        self,
        topic: str,
        project_id: str,
        template_path: str,
        output_path: str
    ):
        """
        Run your existing 6-agent workflow but generate presentation directly
        instead of creating individual files and merging
        """
        # Step 1: Layout Analysis Agent (your existing)
        layouts_info = await self.run_layout_analysis_agent(template_path)
        
        # Step 2: Presentation Planning Agent (your existing)
        slide_plan = await self.run_presentation_planning_agent(topic)
        
        # Step 3: Content Generation Agent (your existing)
        slide_contents = []
        for slide_spec in slide_plan:
            content = await self.run_content_generation_agent(slide_spec, layouts_info)
            
            # Step 4: HTML Content Generation Agent (your existing, if needed)
            if self.needs_html_visualization(slide_spec):
                html_content = await self.run_html_content_agent(content)
                content.update({"html_visualization": html_content})
            
            # Step 5: HTML Refinement Agent (your existing, if needed)
            if "html_visualization" in content:
                refined_html = await self.run_html_refinement_agent(content["html_visualization"])
                content["html_visualization"] = refined_html
            
            slide_contents.append(content)
        
        # Step 6: Direct Slide Assembly (NEW - replaces merging individual files)
        workflow = ImprovedPresentationWorkflow(template_path)
        result = await workflow.generate_presentation_with_perfect_formatting(
            project_id=project_id,
            output_path=output_path,
            slide_specifications=slide_contents,
            layouts_info=layouts_info
        )
        
        return result
    
    # Your existing agent methods would go here
    async def run_layout_analysis_agent(self, template_path):
        # Your existing layout analysis logic
        pass
    
    async def run_presentation_planning_agent(self, topic):
        # Your existing presentation planning logic
        pass
    
    async def run_content_generation_agent(self, slide_spec, layouts_info):
        # Your existing content generation logic
        pass
    
    async def run_html_content_agent(self, content):
        # Your existing HTML content generation logic
        pass
    
    async def run_html_refinement_agent(self, html_content):
        # Your existing HTML refinement logic
        pass
    
    def needs_html_visualization(self, slide_spec):
        # Your logic to determine if HTML visualization is needed
        return False