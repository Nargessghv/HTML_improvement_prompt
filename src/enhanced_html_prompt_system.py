"""
Enhanced HTML Prompt System

This module provides improvements to make template-specific HTML prompts
more influential in the generation process.
"""

import json
from pathlib import Path
from typing import Dict, Optional, Any


class EnhancedHTMLPromptManager:
    """
    Enhanced HTML prompt manager that gives more weight to template-specific
    prompts and placeholder instructions.
    """
    
    def __init__(self, html_prompt_manager):
        """
        Initialize enhanced manager as a wrapper around existing manager.
        
        Args:
            html_prompt_manager: Existing HTMLPromptManager instance
        """
        self.base_manager = html_prompt_manager
        self.template_prompts_cache = {}
        self.placeholder_instructions_cache = {}
    
    def set_placeholder_instructions(self, slide_number: int, placeholder_name: str, instructions: str):
        """
        Cache placeholder instructions for use in HTML generation.
        
        Args:
            slide_number: Slide number
            placeholder_name: Name of the placeholder
            instructions: Instructions from the placeholder text
        """
        key = f"{slide_number}_{placeholder_name}"
        self.placeholder_instructions_cache[key] = instructions
    
    def get_enhanced_html_user_prompt(
        self,
        placeholder_name: str,
        original_content: str,
        topic: str,
        slide_number: int,
        total_slides: int,
        viewport_width: int = 1577,
        viewport_height: int = 603,
        slide_spec: Optional[Any] = None,
        placeholder_instructions: Optional[str] = None,
    ) -> str:
        """
        Get enhanced HTML user prompt that prioritizes template-specific guidance.
        
        Args:
            placeholder_name: Name of the HTML placeholder
            original_content: Original text content to convert to HTML
            topic: Presentation topic
            slide_number: Current slide number
            total_slides: Total number of slides
            viewport_width: Width of HTML viewport
            viewport_height: Height of HTML viewport
            slide_spec: Optional slide specification
            placeholder_instructions: Instructions from placeholder text
            
        Returns:
            Enhanced HTML user prompt string
        """
        # Start with base prompt
        base_prompt = self.base_manager.get_html_user_prompt(
            placeholder_name=placeholder_name,
            original_content=original_content,
            topic=topic,
            slide_number=slide_number,
            total_slides=total_slides,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            slide_spec=slide_spec
        )
        
        # Check for cached placeholder instructions
        if not placeholder_instructions:
            key = f"{slide_number}_{placeholder_name}"
            placeholder_instructions = self.placeholder_instructions_cache.get(key)
        
        # Add placeholder instructions if available
        if placeholder_instructions:
            instructions_section = f"""
CRITICAL PLACEHOLDER INSTRUCTIONS:
The PowerPoint template placeholder contains the following instructions that MUST be followed:
"{placeholder_instructions}"

These instructions override any default guidelines. Your HTML must specifically implement these requirements.
"""
            # Insert at the beginning for maximum influence
            base_prompt = instructions_section + "\n\n" + base_prompt
        
        # Load and prioritize template-specific visual design
        if self.base_manager.current_template:
            template_design = self._load_template_visual_design()
            if template_design:
                # Replace the default design section with template-specific one
                base_prompt = self._replace_design_section(base_prompt, template_design)
        
        return base_prompt
    
    def _load_template_visual_design(self) -> Optional[str]:
        """
        Load template-specific visual design prompt with higher priority.
        
        Returns:
            Template-specific visual design prompt or None
        """
        if not self.base_manager.current_template:
            return None
        
        # Check cache first
        if self.base_manager.current_template in self.template_prompts_cache:
            return self.template_prompts_cache[self.base_manager.current_template]
        
        # Load from file
        design_file = (
            self.base_manager.templates_dir / 
            self.base_manager.current_template / 
            "html_prompts" / 
            "templates" / 
            "visual_design.txt"
        )
        
        if design_file.exists():
            design_content = design_file.read_text()
            # Cache for future use
            self.template_prompts_cache[self.base_manager.current_template] = design_content
            return design_content
        
        return None
    
    def _replace_design_section(self, prompt: str, template_design: str) -> str:
        """
        Replace the default design section with template-specific design.
        
        Args:
            prompt: Original prompt
            template_design: Template-specific design prompt
            
        Returns:
            Modified prompt with template design prioritized
        """
        # Look for the design specifications section
        design_markers = [
            "HTML VISUAL DESIGN SPECIFICATIONS:",
            "TEMPLATE COLOR PALETTE:",
            "BRAND COLORS"
        ]
        
        for marker in design_markers:
            if marker in prompt:
                # Find the start and end of the design section
                start_idx = prompt.find(marker)
                
                # Find the next major section (usually starts with uppercase)
                import re
                next_section = re.search(r'\n[A-Z]{4,}[^\n]*:', prompt[start_idx + len(marker):])
                
                if next_section:
                    end_idx = start_idx + len(marker) + next_section.start()
                else:
                    # No next section found, replace to the end
                    end_idx = len(prompt)
                
                # Replace with template-specific design
                prompt = (
                    prompt[:start_idx] + 
                    "\n" + template_design + "\n" +
                    prompt[end_idx:]
                )
                break
        else:
            # No design section found, prepend template design
            prompt = template_design + "\n\n" + prompt
        
        return prompt
    
    def get_enhanced_refinement_prompt(
        self, 
        width: int, 
        height: int,
        placeholder_instructions: Optional[str] = None
    ) -> str:
        """
        Get enhanced HTML refinement prompt with template-specific requirements.
        
        Args:
            width: Viewport width
            height: Viewport height
            placeholder_instructions: Instructions from placeholder
            
        Returns:
            Enhanced refinement prompt
        """
        base_prompt = self.base_manager.get_html_refinement_prompt(width, height)
        
        # Add placeholder instructions to refinement criteria
        if placeholder_instructions:
            instructions_section = f"""
PLACEHOLDER-SPECIFIC REQUIREMENTS:
The original placeholder contains these instructions that the HTML MUST fulfill:
"{placeholder_instructions}"

Add this to your evaluation criteria:
✅ HTML fulfills the specific placeholder instructions
✅ Visual design matches the template requirements exactly
"""
            base_prompt = instructions_section + "\n\n" + base_prompt
        
        # Add template-specific visual validation
        if self.base_manager.current_template:
            template_design = self._load_template_visual_design()
            if template_design:
                validation_section = f"""
TEMPLATE VISUAL VALIDATION:
Verify the HTML strictly follows this template's design system:

{template_design}

CRITICAL: If the HTML does not match these specifications exactly, it must be refined.
"""
                base_prompt = base_prompt + "\n\n" + validation_section
        
        return base_prompt


def integrate_enhanced_prompts(workflow_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Helper function to integrate enhanced prompts into the workflow.
    
    Args:
        workflow_state: Current workflow state
        
    Returns:
        Updated workflow state with enhanced prompt system
    """
    # Extract placeholder instructions from layout analysis
    layout_analysis = workflow_state.get("layout_analysis", {})
    placeholder_instructions = {}
    
    if layout_analysis and hasattr(layout_analysis, "layouts"):
        for layout in layout_analysis.layouts:
            for placeholder in layout.placeholders:
                if hasattr(placeholder, "instructions") and placeholder.instructions:
                    key = f"{layout.name}_{placeholder.name}"
                    placeholder_instructions[key] = placeholder.instructions
    
    # Store in state for use by HTML agents
    workflow_state["placeholder_instructions"] = placeholder_instructions
    
    return workflow_state


# Example integration code for html_content_agent.py
def example_integration():
    """
    Example of how to integrate the enhanced prompt system.
    """
    integration_code = '''
# In html_content_agent.py, modify the _generate_html_visualization_content method:

def _generate_html_visualization_content(
    self,
    placeholder_name: str,
    original_content: str,
    # ... other params
):
    # Get placeholder instructions from state
    placeholder_key = f"{slide_number}_{placeholder_name}"
    placeholder_instructions = self.state.get("placeholder_instructions", {}).get(
        placeholder_key, ""
    )
    
    # Use enhanced prompt manager
    if hasattr(self, "enhanced_prompt_manager"):
        user_prompt = self.enhanced_prompt_manager.get_enhanced_html_user_prompt(
            placeholder_name=placeholder_name,
            original_content=original_content,
            topic=topic,
            slide_number=slide_number,
            total_slides=total_slides,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            slide_spec=slide_spec,
            placeholder_instructions=placeholder_instructions
        )
    else:
        # Fallback to standard prompt manager
        user_prompt = self.html_prompt_manager.get_html_user_prompt(...)
'''
    return integration_code