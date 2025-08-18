"""
HTML Debug Logger

This module provides debugging functionality to track HTML generation
and refinement prompts and outputs.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class HTMLDebugLogger:
    """
    Logger for debugging HTML generation and refinement process.
    Saves prompts, generated HTML, and refinement history.
    """
    
    def __init__(self, debug_folder: str = "html_debug/prompts"):
        """
        Initialize the HTML debug logger.
        
        Args:
            debug_folder: Folder to save debug information
        """
        self.debug_folder = Path(debug_folder)
        self.debug_folder.mkdir(parents=True, exist_ok=True)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"📝 HTML Debug Logger initialized - Session: {self.session_id}")
    
    def log_generation(
        self,
        slide_number: int,
        placeholder_name: str,
        system_prompt: str,
        user_prompt: str,
        generated_html: str,
        template_name: Optional[str] = None,
        colors: Optional[Dict] = None,
    ):
        """
        Log HTML generation details.
        
        Args:
            slide_number: Slide number
            placeholder_name: Placeholder name
            system_prompt: System prompt used
            user_prompt: User prompt used
            generated_html: Generated HTML content
            template_name: Template name if available
            colors: Color configuration if available
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create a comprehensive log entry
        log_data = {
            "timestamp": timestamp,
            "session_id": self.session_id,
            "slide_number": slide_number,
            "placeholder_name": placeholder_name,
            "template_name": template_name or "default",
            "colors": colors,
            "prompts": {
                "system": system_prompt,
                "user": user_prompt
            },
            "generated_html": generated_html
        }
        
        # Save as JSON for structured analysis
        json_file = self.debug_folder / f"generation_slide_{slide_number}_{placeholder_name}_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        
        # Also save HTML separately for easy viewing
        html_file = self.debug_folder / f"generated_slide_{slide_number}_{placeholder_name}_{timestamp}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(generated_html)
        
        print(f"  📝 Saved generation debug info to {json_file.name}")
    
    def log_refinement(
        self,
        slide_number: int,
        placeholder_name: str,
        iteration: int,
        system_prompt: str,
        user_prompt: str,
        original_html: str,
        refined_html: str,
        reasoning: Optional[str] = None,
        changes: Optional[list] = None,
        template_name: Optional[str] = None,
    ):
        """
        Log HTML refinement details.
        
        Args:
            slide_number: Slide number
            placeholder_name: Placeholder name
            iteration: Refinement iteration number
            system_prompt: System prompt used
            user_prompt: User prompt used
            original_html: Original HTML before refinement
            refined_html: Refined HTML content
            reasoning: Refinement reasoning
            changes: List of changes applied
            template_name: Template name if available
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create a comprehensive refinement log
        log_data = {
            "timestamp": timestamp,
            "session_id": self.session_id,
            "slide_number": slide_number,
            "placeholder_name": placeholder_name,
            "iteration": iteration,
            "template_name": template_name or "default",
            "prompts": {
                "system": system_prompt,
                "user": user_prompt
            },
            "html": {
                "original": original_html,
                "refined": refined_html
            },
            "refinement": {
                "reasoning": reasoning,
                "changes": changes
            }
        }
        
        # Save as JSON for structured analysis
        json_file = self.debug_folder / f"refinement_slide_{slide_number}_{placeholder_name}_iter{iteration}_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        
        # Save refined HTML separately
        html_file = self.debug_folder / f"refined_slide_{slide_number}_{placeholder_name}_iter{iteration}_{timestamp}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(refined_html)
        
        print(f"  📝 Saved refinement debug info to {json_file.name}")
    
    def log_template_analysis(self, template_name: str, template_data: Dict[str, Any]):
        """
        Log template configuration analysis.
        
        Args:
            template_name: Name of the template
            template_data: Template configuration data
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        analysis_file = self.debug_folder / f"template_analysis_{template_name}_{timestamp}.json"
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": timestamp,
                "session_id": self.session_id,
                "template_name": template_name,
                "template_data": template_data
            }, f, indent=2, ensure_ascii=False)
        
        print(f"  📝 Saved template analysis to {analysis_file.name}")
    
    def create_summary_report(self):
        """
        Create a summary report of the debugging session.
        """
        summary_file = self.debug_folder / f"session_summary_{self.session_id}.md"
        
        # Collect all debug files from this session
        generation_files = list(self.debug_folder.glob(f"generation_*{self.session_id}*.json"))
        refinement_files = list(self.debug_folder.glob(f"refinement_*{self.session_id}*.json"))
        
        with open(summary_file, 'w') as f:
            f.write(f"# HTML Debug Session Summary\n\n")
            f.write(f"**Session ID:** {self.session_id}\n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write(f"## Generation Summary\n")
            f.write(f"- Total generations logged: {len(generation_files)}\n\n")
            
            f.write(f"## Refinement Summary\n")
            f.write(f"- Total refinements logged: {len(refinement_files)}\n\n")
            
            f.write(f"## Files Generated\n")
            for file in generation_files + refinement_files:
                f.write(f"- {file.name}\n")
        
        print(f"  📊 Created session summary: {summary_file.name}")


# Global instance for easy access
_debug_logger = None

def get_debug_logger() -> HTMLDebugLogger:
    """Get or create the global debug logger instance."""
    global _debug_logger
    if _debug_logger is None:
        _debug_logger = HTMLDebugLogger()
    return _debug_logger