"""
Simple debugging for HTML prompt tracking
"""

import os
from datetime import datetime
from pathlib import Path


def save_prompt_debug(prompt_type: str, content: str, template_name: str = None, extra_info: str = None):
    """
    Simple function to save prompts for debugging.
    
    Args:
        prompt_type: Type of prompt (system, user, refinement)
        content: The prompt content
        template_name: Template name if available
        extra_info: Any extra information
    """
    debug_dir = Path("html_debug/simple_prompts")
    debug_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prompt_type}_{template_name or 'unknown'}_{timestamp}.txt"
    
    filepath = debug_dir / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"=== {prompt_type.upper()} PROMPT ===\n")
        f.write(f"Template: {template_name or 'unknown'}\n")
        f.write(f"Timestamp: {timestamp}\n")
        if extra_info:
            f.write(f"Extra Info: {extra_info}\n")
        f.write(f"\n{'='*50}\n\n")
        f.write(content)
    
    print(f"  📝 Saved {prompt_type} prompt to: {filename}")
    return filepath