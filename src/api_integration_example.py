"""
API Integration Example for Enhanced Dual-Path Workflow

This module shows how to integrate the enhanced dual-path slide generation
into your existing API endpoints and frontend integration.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List

from .workflow import SlideGenerationWorkflow
from .template_manager import resolve_template_path


class EnhancedPresentationAPI:
    """
    Enhanced API class that provides dual-path presentation generation
    with individual slide previews and perfect formatting consistency.
    """

    def __init__(self):
        self.workflow = SlideGenerationWorkflow(use_parallel_html_refinement=True)

    async def generate_presentation_with_previews(
        self,
        topic: str,
        project_id: str,
        template_name: str = "ekona_slides_template_new",
        layout_indices: Optional[List[int]] = None,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a complete presentation with individual slide previews
        
        This API endpoint creates both:
        1. Individual PPTX files for each slide (for preview modal)
        2. Complete final presentation (for download)
        
        Both use the exact same slide creation process ensuring perfect consistency.
        
        Args:
            topic: Presentation topic
            project_id: Project identifier for tracking
            template_name: Template name (defaults to ekona template)
            layout_indices: Optional specific layouts to use
            title: Optional presentation title
            
        Returns:
            API response with both individual slides and final presentation
        """
        try:
            print(f"🚀 API: Generating presentation with dual-path approach")
            print(f"📋 Topic: {topic}")
            print(f"🆔 Project ID: {project_id}")
            
            # Resolve template path
            template_path = f"templates/{template_name}/{template_name}.pptx"
            if not template_path:
                template_path = resolve_template_path()
            
            # Generate output path with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"generated_presentations/{project_id}_{timestamp}.pptx"
            
            # Execute the enhanced workflow
            result = self.workflow.run(
                topic=topic,
                template_path=template_path,
                output_path=output_path,
                layout_indices=layout_indices,
                title=title
            )
            
            # Format API response
            if result["success"]:
                # The enhanced assembly agent now provides both individual and final
                individual_slides = result.get("individual_slides", [])
                
                api_response = {
                    "success": True,
                    "project_id": project_id,
                    "topic": topic,
                    "presentation": {
                        "final_file_path": result["presentation_path"],
                        "slide_count": result["slide_count"],
                        "layouts_used": result.get("layouts_used", [])
                    },
                    "individual_slides": [
                        {
                            "slide_number": i + 1,
                            "preview_url": slide_result.get("file_url") if slide_result.get("success") else None,
                            "thumbnail_url": slide_result.get("thumbnail_url") if slide_result.get("success") else None,
                            "slide_id": slide_result.get("slide_id"),
                            "status": "success" if slide_result.get("success") else "failed"
                        }
                        for i, slide_result in enumerate(individual_slides)
                    ],
                    "generation_info": {
                        "timestamp": timestamp,
                        "execution_time": result.get("execution_time", 0),
                        "total_tokens": result.get("total_tokens", 0),
                        "cost_estimate": result.get("cost_estimate", 0.0)
                    },
                    "message": "Presentation generated with perfect formatting consistency"
                }
                
                print(f"✅ API: Generation completed successfully")
                print(f"📄 Final presentation: {result['presentation_path']}")
                print(f"📱 Individual slides: {len(individual_slides)} for preview")
                
                return api_response
            else:
                return {
                    "success": False,
                    "project_id": project_id,
                    "error": result.get("error", "Unknown error"),
                    "error_details": {
                        "current_step": result.get("current_step"),
                        "error_message": result.get("error_message")
                    }
                }
                
        except Exception as e:
            print(f"❌ API: Generation failed: {e}")
            return {
                "success": False,
                "project_id": project_id,
                "error": str(e),
                "error_type": "api_error"
            }

    async def regenerate_individual_slide(
        self,
        project_id: str,
        slide_id: str,
        slide_number: int,
        user_adjustments: Dict[str, Any],
        template_name: str = "ekona_slides_template_new"
    ) -> Dict[str, Any]:
        """
        Regenerate a specific individual slide after user adjustments
        
        This API endpoint allows users to request changes to specific slides
        in the preview modal and regenerate only that slide.
        
        Args:
            project_id: Project identifier
            slide_id: Unique slide identifier
            slide_number: Slide number (1-indexed)
            user_adjustments: Dictionary of user-requested changes
            template_name: Template name
            
        Returns:
            API response with regenerated slide information
        """
        try:
            print(f"🔄 API: Regenerating slide {slide_number} with user adjustments")
            print(f"🆔 Project ID: {project_id}")
            print(f"📝 Adjustments: {list(user_adjustments.keys())}")
            
            # Resolve template path
            template_path = f"templates/{template_name}/{template_name}.pptx"
            
            # Use workflow's regeneration method
            regeneration_result = self.workflow.regenerate_individual_slide(
                template_path=template_path,
                slide_id=slide_id,
                project_id=project_id,
                user_adjustments=user_adjustments,
                slide_number=slide_number
            )
            
            if regeneration_result["success"]:
                api_response = {
                    "success": True,
                    "project_id": project_id,
                    "slide_id": slide_id,
                    "slide_number": slide_number,
                    "regenerated_slide": {
                        "preview_url": regeneration_result.get("file_url"),
                        "thumbnail_url": regeneration_result.get("thumbnail_url"),
                        "updated_at": datetime.now().isoformat()
                    },
                    "adjustments_applied": user_adjustments,
                    "message": f"Slide {slide_number} regenerated successfully"
                }
                
                print(f"✅ API: Slide {slide_number} regenerated successfully")
                return api_response
            else:
                return {
                    "success": False,
                    "project_id": project_id,
                    "slide_id": slide_id,
                    "slide_number": slide_number,
                    "error": regeneration_result.get("error", "Unknown regeneration error")
                }
                
        except Exception as e:
            print(f"❌ API: Slide regeneration failed: {e}")
            return {
                "success": False,
                "project_id": project_id,
                "slide_id": slide_id,
                "slide_number": slide_number,
                "error": str(e),
                "error_type": "regeneration_error"
            }

    async def regenerate_final_presentation(
        self,
        project_id: str,
        template_name: str = "ekona_slides_template_new"
    ) -> Dict[str, Any]:
        """
        Regenerate the final presentation using the latest individual slides
        
        This is useful when users have made adjustments to multiple individual slides
        and want to generate a new final presentation with all the latest changes.
        
        Args:
            project_id: Project identifier
            template_name: Template name
            
        Returns:
            API response with new final presentation
        """
        try:
            print(f"🔄 API: Regenerating final presentation for project {project_id}")
            
            # This would integrate with your database to:
            # 1. Get all the latest individual slides for the project
            # 2. Combine them into a new final presentation
            # 3. Use the dual-path generator's combine method
            
            # Example implementation (you'd integrate with your actual database)
            from .dual_path_generator import DualPathGenerator
            
            template_path = f"templates/{template_name}/{template_name}.pptx"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"generated_presentations/{project_id}_updated_{timestamp}.pptx"
            
            dual_generator = DualPathGenerator(template_path)
            
            # This would use your database to get the latest slide contents
            # For now, this is a placeholder
            # Note: In a real implementation, you should also pass dynamic_models for optimal accuracy
            combine_result = await dual_generator.combine_individual_slides(
                project_id=project_id,
                output_path=output_path,
                template_path=template_path
                # dynamic_models=dynamic_models  # <- Add this in real implementation
            )
            
            if combine_result["success"]:
                return {
                    "success": True,
                    "project_id": project_id,
                    "updated_presentation": {
                        "file_path": combine_result["output_path"],
                        "slides_combined": combine_result["slides_combined"],
                        "total_slides": combine_result["total_slides"],
                        "file_size": combine_result["file_size"]
                    },
                    "message": combine_result["message"]
                }
            else:
                return {
                    "success": False,
                    "project_id": project_id,
                    "error": combine_result["error"]
                }
                
        except Exception as e:
            print(f"❌ API: Final presentation regeneration failed: {e}")
            return {
                "success": False,
                "project_id": project_id,
                "error": str(e),
                "error_type": "final_regeneration_error"
            }


# FastAPI integration example
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

app = FastAPI()
enhanced_api = EnhancedPresentationAPI()

class PresentationRequest(BaseModel):
    topic: str
    project_id: str
    template_name: Optional[str] = "ekona_slides_template_new"
    layout_indices: Optional[List[int]] = None
    title: Optional[str] = None

class SlideRegenerationRequest(BaseModel):
    project_id: str
    slide_id: str
    slide_number: int
    user_adjustments: Dict[str, Any]
    template_name: Optional[str] = "ekona_slides_template_new"

@app.post("/api/presentations/generate")
async def generate_presentation_endpoint(request: PresentationRequest):
    \"\"\"Generate presentation with individual slide previews\"\"\"
    result = await enhanced_api.generate_presentation_with_previews(
        topic=request.topic,
        project_id=request.project_id,
        template_name=request.template_name,
        layout_indices=request.layout_indices,
        title=request.title
    )
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result

@app.post("/api/slides/regenerate")
async def regenerate_slide_endpoint(request: SlideRegenerationRequest):
    \"\"\"Regenerate individual slide after user adjustments\"\"\"
    result = await enhanced_api.regenerate_individual_slide(
        project_id=request.project_id,
        slide_id=request.slide_id,
        slide_number=request.slide_number,
        user_adjustments=request.user_adjustments,
        template_name=request.template_name
    )
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result

@app.post("/api/presentations/{project_id}/regenerate-final")
async def regenerate_final_presentation_endpoint(
    project_id: str,
    template_name: Optional[str] = "ekona_slides_template_new"
):
    \"\"\"Regenerate final presentation with latest individual slides\"\"\"
    result = await enhanced_api.regenerate_final_presentation(
        project_id=project_id,
        template_name=template_name
    )
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result
"""


# Example usage
async def example_usage():
    """Example of how to use the enhanced API"""
    
    api = EnhancedPresentationAPI()
    
    # Generate presentation with previews
    print("🚀 Generating presentation with dual-path approach...")
    result = await api.generate_presentation_with_previews(
        topic="AI-Powered Business Transformation",
        project_id="demo_project_123",
        title="AI in Business"
    )
    
    if result["success"]:
        print(f"✅ Generation successful!")
        print(f"📄 Final presentation: {result['presentation']['final_file_path']}")
        print(f"📱 Individual slides: {len(result['individual_slides'])} for preview")
        
        # Example: User wants to adjust slide 2
        print("\n🔄 User requesting adjustment to slide 2...")
        adjustment_result = await api.regenerate_individual_slide(
            project_id="demo_project_123",
            slide_id="slide_demo_project_123_2",
            slide_number=2,
            user_adjustments={
                "title": "Enhanced Key Benefits",
                "content": {
                    "Title": "Enhanced Key Benefits",
                    "Content": "Updated content based on user feedback and requirements"
                },
                "tone": "enthusiastic"
            }
        )
        
        if adjustment_result["success"]:
            print(f"✅ Slide 2 regenerated successfully!")
            print(f"🔗 New preview URL: {adjustment_result['regenerated_slide']['preview_url']}")
        
    else:
        print(f"❌ Generation failed: {result['error']}")


if __name__ == "__main__":
    asyncio.run(example_usage())