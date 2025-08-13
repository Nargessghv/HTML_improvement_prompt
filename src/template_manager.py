"""
Template Manager Module

Manages PowerPoint templates for the slide generation system.
Provides functionality to list, validate, and select templates from the templates directory.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import logging
from pptx import Presentation

logger = logging.getLogger(__name__)


@dataclass
class TemplateInfo:
    """Information about a PowerPoint template"""
    
    filename: str
    path: str
    name: str
    size_mb: float
    slide_count: int
    is_valid: bool
    error_message: Optional[str] = None
    
    @property
    def display_name(self) -> str:
        """Get a user-friendly display name"""
        return self.name.replace("_", " ").replace("-", " ").title()


class TemplateManager:
    """Manages PowerPoint templates in the templates directory"""
    
    def __init__(self, templates_dir: str = "templates"):
        self.templates_dir = Path(templates_dir)
        self._ensure_templates_dir()
    
    def _ensure_templates_dir(self):
        """Ensure the templates directory exists"""
        self.templates_dir.mkdir(exist_ok=True)
        logger.info(f"Templates directory: {self.templates_dir.absolute()}")
    
    def list_templates(self) -> List[TemplateInfo]:
        """
        List all PowerPoint templates in the templates directory
        
        Returns:
            List of TemplateInfo objects for valid templates
        """
        templates = []
        
        if not self.templates_dir.exists():
            logger.warning(f"Templates directory does not exist: {self.templates_dir}")
            return templates
        
        # Look for .pptx files
        for template_file in self.templates_dir.glob("*.pptx"):
            template_info = self._analyze_template(template_file)
            templates.append(template_info)
        
        # Sort by name
        templates.sort(key=lambda t: t.name.lower())
        
        logger.info(f"Found {len(templates)} templates")
        return templates
    
    def _analyze_template(self, template_path: Path) -> TemplateInfo:
        """
        Analyze a template file to extract information
        
        Args:
            template_path: Path to the template file
            
        Returns:
            TemplateInfo object with template details
        """
        filename = template_path.name
        name = template_path.stem
        size_mb = template_path.stat().st_size / (1024 * 1024)
        
        try:
            # Try to open the presentation to validate it
            presentation = Presentation(str(template_path))
            slide_count = len(presentation.slides)
            is_valid = True
            error_message = None
            
            logger.debug(f"Template {filename}: {slide_count} slides, {size_mb:.1f}MB")
            
        except Exception as e:
            logger.error(f"Failed to analyze template {filename}: {e}")
            slide_count = 0
            is_valid = False
            error_message = str(e)
        
        return TemplateInfo(
            filename=filename,
            path=str(template_path),
            name=name,
            size_mb=size_mb,
            slide_count=slide_count,
            is_valid=is_valid,
            error_message=error_message
        )
    
    def get_template_path(self, template_name: str) -> Optional[str]:
        """
        Get the full path for a template by name
        
        Args:
            template_name: Name of the template (with or without .pptx extension)
            
        Returns:
            Full path to the template file, or None if not found
        """
        if not template_name.endswith('.pptx'):
            template_name += '.pptx'
        
        template_path = self.templates_dir / template_name
        
        if template_path.exists():
            return str(template_path)
        
        logger.warning(f"Template not found: {template_name}")
        return None
    
    def get_default_template(self) -> Optional[str]:
        """
        Get the default template (first valid template found)
        
        Returns:
            Path to default template, or None if no templates available
        """
        templates = self.list_templates()
        valid_templates = [t for t in templates if t.is_valid]
        
        if valid_templates:
            default = valid_templates[0]
            logger.info(f"Using default template: {default.filename}")
            return default.path
        
        logger.error("No valid templates found")
        return None
    
    def validate_template(self, template_path: str) -> bool:
        """
        Validate that a template file is usable
        
        Args:
            template_path: Path to the template file
            
        Returns:
            True if template is valid, False otherwise
        """
        try:
            presentation = Presentation(template_path)
            return len(presentation.slides) > 0
        except Exception as e:
            logger.error(f"Template validation failed for {template_path}: {e}")
            return False


def get_template_manager() -> TemplateManager:
    """Get a configured template manager instance"""
    return TemplateManager()


def list_available_templates() -> List[TemplateInfo]:
    """Convenience function to list all available templates"""
    manager = get_template_manager()
    return manager.list_templates()


def resolve_template_path(template_name: Optional[str] = None) -> str:
    """
    Resolve template name to full path, with fallback to default
    
    Args:
        template_name: Optional template name/filename
        
    Returns:
        Full path to template file
        
    Raises:
        FileNotFoundError: If no valid template can be found
    """
    manager = get_template_manager()
    
    # Try to use specified template
    if template_name:
        template_path = manager.get_template_path(template_name)
        if template_path:
            return template_path
        logger.warning(f"Specified template not found: {template_name}")
    
    # Fall back to default template
    default_path = manager.get_default_template()
    if default_path:
        return default_path
    
    raise FileNotFoundError(
        "No valid PowerPoint templates found in templates directory. "
        "Please add .pptx files to the templates/ folder."
    )


if __name__ == "__main__":
    # CLI for testing template manager
    import sys
    
    manager = get_template_manager()
    templates = manager.list_templates()
    
    print(f"Found {len(templates)} template(s):")
    print("=" * 60)
    
    for template in templates:
        status = "✅ Valid" if template.is_valid else "❌ Invalid"
        print(f"{status} {template.filename}")
        print(f"   Name: {template.display_name}")
        print(f"   Size: {template.size_mb:.1f} MB")
        print(f"   Slides: {template.slide_count}")
        
        if template.error_message:
            print(f"   Error: {template.error_message}")
        print()
    
    if len(sys.argv) > 1:
        # Test template resolution
        template_name = sys.argv[1]
        try:
            resolved_path = resolve_template_path(template_name)
            print(f"Resolved '{template_name}' to: {resolved_path}")
        except FileNotFoundError as e:
            print(f"Error: {e}")