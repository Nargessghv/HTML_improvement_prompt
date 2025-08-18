"""
Debug Variables Tracker

This module provides comprehensive variable tracking for the slide generation workflow.
It captures all key variables and saves them to variables.json for debugging purposes.
The file is automatically cleared on each run to provide fresh tracking data.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path


class VariableTracker:
    """Tracks all major variables during the slide creation workflow"""
    
    def __init__(self, output_file: str = "variables.json"):
        """
        Initialize the variable tracker
        
        Args:
            output_file: Path to the JSON file where variables will be saved
        """
        self.output_file = output_file
        self.variables = {
            "tracking_metadata": {
                "session_start": datetime.now().isoformat(),
                "workflow_type": None,
                "total_slides": 0,
                "completed_slides": 0,
                "failed_slides": 0
            },
            "workflow_state": {},
            "layout_analysis": {},
            "presentation_planning": {},
            "content_generation": {},
            "html_content": {},
            "html_refinement": {},
            "image_generation": {},
            "slide_assembly": {},
            "individual_slides": [],
            "final_presentation": {},
            "errors": [],
            "performance_metrics": {}
        }
        
        # Clear the file at the start of each run
        self._clear_variables_file()
    
    def _clear_variables_file(self):
        """Clear the variables.json file and initialize with session metadata"""
        try:
            with open(self.output_file, 'w') as f:
                json.dump(self.variables, f, indent=2)
            print(f"🗑️ Cleared variables.json for new debugging session")
        except Exception as e:
            print(f"⚠️ Warning: Could not clear variables file: {e}")
    
    def set_workflow_type(self, workflow_type: str):
        """Set the type of workflow being executed"""
        self.variables["tracking_metadata"]["workflow_type"] = workflow_type
        self._save_variables()
    
    def track_workflow_state(self, state: Dict[str, Any]):
        """Track the main workflow state variables"""
        # Filter out sensitive or large data, keep key identifiers
        tracked_state = {
            "topic": state.get("topic"),
            "template_path": state.get("template_path"),
            "output_path": state.get("output_path"),
            "project_id": state.get("project_id"),
            "current_step": state.get("current_step"),
            "title": state.get("title"),
            "retry_count": state.get("retry_count"),
            "error_message": state.get("error_message"),
            "success": state.get("success"),
            "needs_html_refinement": state.get("needs_html_refinement"),
            "needs_icon_retry": state.get("needs_icon_retry"),
            "html_refinement_iteration": state.get("html_refinement_iteration"),
            "layout_indices": state.get("layout_indices"),
            "slide_count": len(state.get("slide_contents", [])) if state.get("slide_contents") else 0,
            "selected_layouts_count": len(state.get("selected_layouts", [])) if state.get("selected_layouts") else 0,
            "presentation_path": state.get("presentation_path"),
            "last_updated": datetime.now().isoformat()
        }
        
        self.variables["workflow_state"] = tracked_state
        self._save_variables()
    
    def track_layout_analysis(self, layouts_info: Dict[str, Any], dynamic_models: Optional[Dict] = None):
        """Track layout analysis results"""
        analysis_data = {
            "total_layouts": len(layouts_info) if layouts_info else 0,
            "layout_indices": list(layouts_info.keys()) if layouts_info else [],
            "has_dynamic_models": dynamic_models is not None,
            "dynamic_models_count": len(dynamic_models) if dynamic_models else 0,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add sample layout info for debugging
        if layouts_info:
            first_layout_key = list(layouts_info.keys())[0]
            first_layout = layouts_info[first_layout_key]
            analysis_data["sample_layout"] = {
                "index": first_layout_key,
                "placeholder_count": len(first_layout.get("placeholders", [])),
                "placeholder_names": [ph.get("name") for ph in first_layout.get("placeholders", [])],
            }
        
        self.variables["layout_analysis"] = analysis_data
        self._save_variables()
    
    def track_presentation_planning(self, presentation_plan: List[Any], selected_layouts: List[int]):
        """Track presentation planning results"""
        planning_data = {
            "total_slides_planned": len(presentation_plan) if presentation_plan else 0,
            "selected_layouts": selected_layouts,
            "unique_layouts_used": len(set(selected_layouts)) if selected_layouts else 0,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add sample slide plan for debugging
        if presentation_plan:
            first_slide = presentation_plan[0]
            if hasattr(first_slide, '__dict__'):
                planning_data["sample_slide_plan"] = {
                    "slide_type": type(first_slide).__name__,
                    "attributes": list(first_slide.__dict__.keys()),
                }
                # Add specific content if available
                if hasattr(first_slide, 'title'):
                    planning_data["sample_slide_plan"]["title"] = first_slide.title
                if hasattr(first_slide, 'slide_number'):
                    planning_data["sample_slide_plan"]["slide_number"] = first_slide.slide_number
        
        self.variables["presentation_planning"] = planning_data
        self._save_variables()
    
    def track_content_generation(self, slide_contents: List[Any]):
        """Track content generation results"""
        content_data = {
            "total_slides_generated": len(slide_contents) if slide_contents else 0,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add sample content for debugging
        if slide_contents:
            first_slide = slide_contents[0]
            content_data["sample_slide_content"] = {
                "slide_type": type(first_slide).__name__,
                "has_content": hasattr(first_slide, 'content'),
                "has_layout_index": hasattr(first_slide, 'layout_index'),
            }
            
            if hasattr(first_slide, 'content') and first_slide.content:
                content_data["sample_slide_content"]["content_keys"] = list(first_slide.content.keys())
                content_data["sample_slide_content"]["content_size"] = len(str(first_slide.content))
            
            if hasattr(first_slide, 'layout_index'):
                content_data["sample_slide_content"]["layout_index"] = first_slide.layout_index
        
        self.variables["content_generation"] = content_data
        self._save_variables()
    
    def track_html_content_generation(self, state: Dict[str, Any]):
        """Track HTML content generation"""
        html_data = {
            "html_content_generated": state.get("needs_html_refinement", False),
            "refinement_needed": state.get("needs_html_refinement", False),
            "slides_with_html": 0,
            "timestamp": datetime.now().isoformat()
        }
        
        # Count slides with HTML content
        slide_contents = state.get("slide_contents", [])
        for slide in slide_contents:
            if hasattr(slide, 'content') and slide.content:
                if any('html' in key.lower() for key in slide.content.keys()):
                    html_data["slides_with_html"] += 1
        
        self.variables["html_content"] = html_data
        self._save_variables()
    
    def track_html_refinement(self, iteration: int, slide_index: Optional[int], refinement_id: Optional[str]):
        """Track HTML refinement progress"""
        refinement_data = {
            "current_iteration": iteration,
            "current_slide_index": slide_index,
            "refinement_id": refinement_id,
            "timestamp": datetime.now().isoformat()
        }
        
        # Keep history of refinement iterations
        if "refinement_history" not in self.variables["html_refinement"]:
            self.variables["html_refinement"]["refinement_history"] = []
        
        self.variables["html_refinement"]["refinement_history"].append({
            "iteration": iteration,
            "slide_index": slide_index,
            "refinement_id": refinement_id,
            "timestamp": datetime.now().isoformat()
        })
        
        self.variables["html_refinement"].update(refinement_data)
        self._save_variables()
    
    def track_image_generation(self, state: Dict[str, Any]):
        """Track image generation progress"""
        image_data = {
            "image_prompts_generated": False,
            "images_generated": False,
            "images_refined": False,
            "timestamp": datetime.now().isoformat()
        }
        
        # Check for image-related content in slides
        slide_contents = state.get("slide_contents", [])
        for slide in slide_contents:
            if hasattr(slide, 'content') and slide.content:
                content_keys = slide.content.keys()
                if any('image' in key.lower() for key in content_keys):
                    image_data["image_prompts_generated"] = True
                if any('generated_image' in key.lower() for key in content_keys):
                    image_data["images_generated"] = True
        
        self.variables["image_generation"] = image_data
        self._save_variables()
    
    def track_slide_assembly(self, presentation_path: Optional[str], icon_errors: List[Any]):
        """Track slide assembly results"""
        assembly_data = {
            "presentation_created": presentation_path is not None,
            "presentation_path": presentation_path,
            "icon_errors_count": len(icon_errors) if icon_errors else 0,
            "has_icon_errors": bool(icon_errors),
            "timestamp": datetime.now().isoformat()
        }
        
        if presentation_path and os.path.exists(presentation_path):
            try:
                assembly_data["file_size_bytes"] = os.path.getsize(presentation_path)
                assembly_data["file_exists"] = True
            except:
                assembly_data["file_exists"] = False
        
        self.variables["slide_assembly"] = assembly_data
        self._save_variables()
    
    def track_individual_slide(self, slide_id: str, slide_number: int, status: str, **kwargs):
        """Track individual slide generation progress"""
        slide_data = {
            "slide_id": slide_id,
            "slide_number": slide_number,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }
        
        # Update or add slide data
        existing_slide_index = None
        for i, existing_slide in enumerate(self.variables["individual_slides"]):
            if existing_slide.get("slide_id") == slide_id:
                existing_slide_index = i
                break
        
        if existing_slide_index is not None:
            self.variables["individual_slides"][existing_slide_index].update(slide_data)
        else:
            self.variables["individual_slides"].append(slide_data)
        
        # Update summary counts
        statuses = [s.get("status") for s in self.variables["individual_slides"]]
        self.variables["tracking_metadata"]["total_slides"] = len(self.variables["individual_slides"])
        self.variables["tracking_metadata"]["completed_slides"] = statuses.count("completed")
        self.variables["tracking_metadata"]["failed_slides"] = statuses.count("failed")
        
        self._save_variables()
    
    def track_final_presentation(self, result: Dict[str, Any]):
        """Track final presentation assembly results"""
        final_data = {
            "success": result.get("success", False),
            "output_path": result.get("output_path"),
            "slides_combined": result.get("slides_combined", 0),
            "total_slides": result.get("total_slides", 0),
            "file_size": result.get("file_size", 0),
            "error": result.get("error"),
            "timestamp": datetime.now().isoformat()
        }
        
        self.variables["final_presentation"] = final_data
        self._save_variables()
    
    def track_error(self, error_type: str, error_message: str, context: Optional[Dict] = None):
        """Track errors that occur during the workflow"""
        error_data = {
            "error_type": error_type,
            "error_message": error_message,
            "context": context or {},
            "timestamp": datetime.now().isoformat()
        }
        
        self.variables["errors"].append(error_data)
        self._save_variables()
    
    def track_performance_metric(self, metric_name: str, value: Any, unit: Optional[str] = None):
        """Track performance metrics"""
        self.variables["performance_metrics"][metric_name] = {
            "value": value,
            "unit": unit,
            "timestamp": datetime.now().isoformat()
        }
        self._save_variables()
    
    def _save_variables(self):
        """Save current variables to JSON file"""
        try:
            # Update session metadata
            self.variables["tracking_metadata"]["last_updated"] = datetime.now().isoformat()
            
            with open(self.output_file, 'w') as f:
                json.dump(self.variables, f, indent=2, default=str)
            
        except Exception as e:
            print(f"⚠️ Warning: Could not save variables to {self.output_file}: {e}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of tracked variables"""
        return {
            "session_duration": self._calculate_session_duration(),
            "total_slides": self.variables["tracking_metadata"]["total_slides"],
            "completed_slides": self.variables["tracking_metadata"]["completed_slides"],
            "failed_slides": self.variables["tracking_metadata"]["failed_slides"],
            "errors_count": len(self.variables["errors"]),
            "workflow_steps_completed": self._count_completed_steps(),
            "final_presentation_success": self.variables["final_presentation"].get("success", False)
        }
    
    def _calculate_session_duration(self) -> str:
        """Calculate session duration"""
        try:
            start = datetime.fromisoformat(self.variables["tracking_metadata"]["session_start"])
            duration = datetime.now() - start
            return str(duration)
        except:
            return "Unknown"
    
    def _count_completed_steps(self) -> int:
        """Count how many workflow steps have been completed"""
        completed_steps = 0
        steps = [
            "layout_analysis", "presentation_planning", "content_generation",
            "html_content", "slide_assembly"
        ]
        
        for step in steps:
            if self.variables[step]:
                completed_steps += 1
        
        return completed_steps


# Global tracker instance
_global_tracker: Optional[VariableTracker] = None


def get_variable_tracker() -> VariableTracker:
    """Get the global variable tracker instance"""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = VariableTracker()
    return _global_tracker


def init_variable_tracking(output_file: str = "variables.json") -> VariableTracker:
    """Initialize variable tracking with a specific output file"""
    global _global_tracker
    _global_tracker = VariableTracker(output_file)
    return _global_tracker


def clear_variable_tracking():
    """Clear the global variable tracker"""
    global _global_tracker
    _global_tracker = None