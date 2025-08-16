"""
Workflow Integration Guide

This module shows how to integrate the DualPathGenerator into your existing
6-agent LangGraph workflow to achieve perfect formatting consistency between
individual slide previews and the final presentation.
"""

from typing import List, Dict, Any, Optional
from .dual_path_generator import DualPathGenerator, UnifiedPresentationWorkflow
from .llm_client import SlideContent


class EnhancedAgentWorkflow:
    """
    Enhanced version of your existing 6-agent workflow that generates both
    individual slides (for preview) and complete presentations (final)
    with 100% formatting consistency.
    """
    
    def __init__(self, template_path: str):
        self.template_path = template_path
        self.unified_workflow = UnifiedPresentationWorkflow(template_path)
        
        # Your existing agents would be initialized here
        # self.layout_analysis_agent = LayoutAnalysisAgent()
        # self.presentation_planning_agent = PresentationPlanningAgent()
        # self.content_generation_agent = ContentGenerationAgent()
        # self.html_content_agent = HTMLContentGenerationAgent()
        # self.html_refinement_agent = HTMLRefinementAgent()
        # NOTE: Slide Assembly Agent is replaced by DualPathGenerator

    async def run_complete_workflow(
        self,
        topic: str,
        project_id: str,
        output_path: str,
        generate_previews: bool = True
    ) -> Dict[str, Any]:
        """
        Run the complete 6-agent workflow with dual-path generation
        
        This maintains your existing agent workflow but ensures perfect
        formatting consistency between previews and final presentation.
        """
        try:
            print(f"🚀 Starting enhanced workflow for topic: '{topic}'")
            
            # Step 1: Layout Analysis Agent (unchanged)
            print("📊 Running Layout Analysis Agent...")
            layouts_info = await self._run_layout_analysis_agent()
            
            # Step 2: Presentation Planning Agent (unchanged)
            print("🎯 Running Presentation Planning Agent...")
            slide_specifications = await self._run_presentation_planning_agent(topic)
            
            # Step 3: Content Generation Agent (unchanged)
            print("✍️ Running Content Generation Agent...")
            slide_contents = []
            for i, slide_spec in enumerate(slide_specifications):
                content = await self._run_content_generation_agent(
                    slide_spec, layouts_info, i + 1, len(slide_specifications)
                )
                slide_contents.append(content)
            
            # Step 4: HTML Content Generation Agent (unchanged, but per slide)
            print("🎨 Running HTML Content Generation Agent...")
            for slide_content in slide_contents:
                if self._needs_html_visualization(slide_content):
                    html_content = await self._run_html_content_agent(slide_content)
                    if html_content:
                        # Add HTML content to slide
                        self._add_html_content_to_slide(slide_content, html_content)
            
            # Step 5: HTML Refinement Agent (unchanged, but per slide)
            print("🔧 Running HTML Refinement Agent...")
            for slide_content in slide_contents:
                if self._has_html_content(slide_content):
                    refined_html = await self._run_html_refinement_agent(slide_content)
                    if refined_html:
                        self._update_html_content_in_slide(slide_content, refined_html)
            
            # Step 6: ENHANCED Slide Assembly (NEW - dual path generation)
            print("🔄 Running Enhanced Slide Assembly (Dual Path)...")
            result = await self.unified_workflow.generate_presentation_with_previews(
                project_id=project_id,
                slide_contents=slide_contents,
                output_path=output_path,
                layouts_info=layouts_info,
                generate_previews=generate_previews
            )
            
            if result["success"]:
                print(f"✅ Workflow completed successfully!")
                print(f"📱 Individual slides: {len(result['individual_slides'])} generated")
                print(f"📄 Final presentation: {result['final_presentation']['slides_added']} slides")
                print(f"💾 File size: {result['final_presentation']['file_size']} bytes")
            else:
                print(f"❌ Workflow failed: {result.get('error', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            print(f"❌ Enhanced workflow failed: {e}")
            return {"success": False, "error": str(e)}

    # Your existing agent methods (unchanged)
    async def _run_layout_analysis_agent(self) -> Dict[str, Any]:
        """Run your existing Layout Analysis Agent"""
        # Your existing implementation
        # from .agents import LayoutAnalysisAgent
        # return await self.layout_analysis_agent.execute(self.template_path)
        
        # Placeholder for example
        return {
            0: {"name": "Title Slide", "placeholders": [{"name": "Title", "index": 0}]},
            1: {"name": "Content Slide", "placeholders": [{"name": "Title", "index": 0}, {"name": "Content", "index": 1}]}
        }

    async def _run_presentation_planning_agent(self, topic: str) -> List[Dict[str, Any]]:
        """Run your existing Presentation Planning Agent"""
        # Your existing implementation
        # return await self.presentation_planning_agent.execute(topic)
        
        # Placeholder for example
        return [
            {"title": f"Introduction to {topic}", "layout_index": 0, "slide_type": "title"},
            {"title": "Key Points", "layout_index": 1, "slide_type": "content"},
            {"title": "Conclusion", "layout_index": 1, "slide_type": "content"}
        ]

    async def _run_content_generation_agent(
        self, 
        slide_spec: Dict[str, Any], 
        layouts_info: Dict[str, Any],
        slide_number: int,
        total_slides: int
    ) -> SlideContent:
        """Run your existing Content Generation Agent"""
        # Your existing implementation
        # return await self.content_generation_agent.execute(slide_spec, layouts_info, slide_number, total_slides)
        
        # Placeholder for example
        from .llm_client import SlideContent
        content = {
            "Title": slide_spec.get("title", f"Slide {slide_number}"),
            "Content": f"Generated content for {slide_spec.get('title', 'slide')}"
        }
        
        return SlideContent(
            layout_index=slide_spec.get("layout_index", 1),
            content=content
        )

    async def _run_html_content_agent(self, slide_content: SlideContent) -> Optional[str]:
        """Run your existing HTML Content Generation Agent"""
        # Your existing implementation
        # return await self.html_content_agent.execute(slide_content)
        
        # Placeholder - return HTML content if visualization is needed
        return None

    async def _run_html_refinement_agent(self, slide_content: SlideContent) -> Optional[str]:
        """Run your existing HTML Refinement Agent"""
        # Your existing implementation
        # return await self.html_refinement_agent.execute(slide_content.html_content)
        
        # Placeholder
        return None

    def _needs_html_visualization(self, slide_content: SlideContent) -> bool:
        """Determine if slide needs HTML visualization"""
        # Your logic to determine if HTML visualization is needed
        # Check for keywords like "timeline", "process", "chart", etc.
        if hasattr(slide_content, 'content'):
            content_text = str(slide_content.content).lower()
            return any(keyword in content_text for keyword in [
                "timeline", "process", "flowchart", "diagram", "chart"
            ])
        return False

    def _has_html_content(self, slide_content: SlideContent) -> bool:
        """Check if slide has HTML content that needs refinement"""
        return hasattr(slide_content, 'html_content') and slide_content.html_content

    def _add_html_content_to_slide(self, slide_content: SlideContent, html_content: str):
        """Add HTML content to slide"""
        slide_content.html_content = html_content

    def _update_html_content_in_slide(self, slide_content: SlideContent, refined_html: str):
        """Update HTML content in slide after refinement"""
        slide_content.html_content = refined_html

    # Slide adjustment and regeneration methods
    async def regenerate_slide_after_adjustment(
        self,
        project_id: str,
        slide_id: str,
        slide_number: int,
        user_adjustments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Regenerate a specific slide after user requests adjustments
        
        This allows users to request changes to individual slides and
        regenerate only that slide while maintaining consistency.
        """
        try:
            print(f"🔄 Regenerating slide {slide_number} after user adjustments...")
            
            # Get original slide specification (you'd retrieve this from database)
            original_slide_spec = await self._get_slide_specification(slide_id)
            
            # Apply user adjustments to the specification
            adjusted_slide_spec = self._apply_user_adjustments(original_slide_spec, user_adjustments)
            
            # Regenerate content with adjustments
            layouts_info = await self._run_layout_analysis_agent()
            updated_slide_content = await self._run_content_generation_agent(
                adjusted_slide_spec, layouts_info, slide_number, 1
            )
            
            # Handle HTML content if needed
            if self._needs_html_visualization(updated_slide_content):
                html_content = await self._run_html_content_agent(updated_slide_content)
                if html_content:
                    self._add_html_content_to_slide(updated_slide_content, html_content)
                    
                    # Refine HTML if needed
                    refined_html = await self._run_html_refinement_agent(updated_slide_content)
                    if refined_html:
                        self._update_html_content_in_slide(updated_slide_content, refined_html)
            
            # Regenerate individual slide using dual path generator
            dual_generator = DualPathGenerator(self.template_path)
            result = await dual_generator.regenerate_individual_slide(
                slide_id=slide_id,
                project_id=project_id,
                updated_slide_content=updated_slide_content,
                slide_number=slide_number,
                layouts_info=layouts_info
            )
            
            if result["success"]:
                print(f"✅ Successfully regenerated slide {slide_number}")
            else:
                print(f"❌ Failed to regenerate slide {slide_number}: {result['error']}")
            
            return result
            
        except Exception as e:
            print(f"❌ Slide regeneration failed: {e}")
            return {"success": False, "error": str(e)}

    async def _get_slide_specification(self, slide_id: str) -> Dict[str, Any]:
        """Get original slide specification from database"""
        # Implement database retrieval of slide specification
        # This would contain the original slide spec used for generation
        pass

    def _apply_user_adjustments(
        self, 
        original_spec: Dict[str, Any], 
        adjustments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply user adjustments to slide specification"""
        # Merge user adjustments with original specification
        adjusted_spec = original_spec.copy()
        adjusted_spec.update(adjustments)
        return adjusted_spec


# Example usage and integration
async def example_enhanced_workflow():
    """
    Example showing how to use the enhanced workflow
    """
    # Initialize enhanced workflow
    template_path = "templates/ekona_slides_template_new/ekona_slides_template_new.pptx"
    enhanced_workflow = EnhancedAgentWorkflow(template_path)
    
    # Run complete workflow with dual-path generation
    result = await enhanced_workflow.run_complete_workflow(
        topic="AI in Business Applications",
        project_id="project_123",
        output_path="generated_presentations/ai_business_presentation.pptx",
        generate_previews=True  # Generate individual slides for preview
    )
    
    if result["success"]:
        print("🎉 Enhanced workflow completed successfully!")
        
        # Individual slides are available for preview
        for i, slide_result in enumerate(result["individual_slides"]):
            if slide_result["success"]:
                print(f"📱 Slide {i+1} preview: {slide_result['file_url']}")
        
        # Final presentation is ready
        final_info = result["final_presentation"]
        print(f"📄 Final presentation: {final_info['output_path']}")
        print(f"📊 Slides in final: {final_info['slides_added']}")
        
        # Later, if user wants to adjust slide 2...
        adjustment_result = await enhanced_workflow.regenerate_slide_after_adjustment(
            project_id="project_123",
            slide_id="slide_project_123_2",
            slide_number=2,
            user_adjustments={
                "title": "Updated Key Points",
                "content": "Updated content based on user feedback"
            }
        )
        
        if adjustment_result["success"]:
            print(f"🔄 Slide 2 regenerated: {adjustment_result['file_url']}")


# Integration with your existing API endpoints
class APIIntegration:
    """
    Shows how to integrate with your existing API endpoints
    """
    
    @staticmethod
    async def generate_presentation_endpoint(
        topic: str,
        project_id: str,
        template_name: str = "ekona_slides_template_new"
    ):
        """
        API endpoint for generating presentations with dual-path approach
        """
        template_path = f"templates/{template_name}/{template_name}.pptx"
        workflow = EnhancedAgentWorkflow(template_path)
        
        output_path = f"generated_presentations/{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pptx"
        
        result = await workflow.run_complete_workflow(
            topic=topic,
            project_id=project_id,
            output_path=output_path,
            generate_previews=True
        )
        
        return {
            "success": result["success"],
            "individual_slides": result.get("individual_slides", []),
            "final_presentation": result.get("final_presentation", {}),
            "error": result.get("error")
        }
    
    @staticmethod
    async def regenerate_slide_endpoint(
        project_id: str,
        slide_id: str,
        slide_number: int,
        adjustments: Dict[str, Any]
    ):
        """
        API endpoint for regenerating individual slides after adjustments
        """
        template_path = "templates/ekona_slides_template_new/ekona_slides_template_new.pptx"
        workflow = EnhancedAgentWorkflow(template_path)
        
        result = await workflow.regenerate_slide_after_adjustment(
            project_id=project_id,
            slide_id=slide_id,
            slide_number=slide_number,
            user_adjustments=adjustments
        )
        
        return result