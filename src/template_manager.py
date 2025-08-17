"""
Template Manager Module

Manages PowerPoint templates for the slide generation system.
Provides functionality to list, validate, and select templates from the templates directory.
"""

import os
import json
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
    layout_count: int = 0
    is_valid: bool = True
    error_message: Optional[str] = None
    folder_path: Optional[str] = None
    locked_backgrounds: int = 0
    
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
        
        # New folder structure: Look for .pptx files in subdirectories
        for template_folder in self.templates_dir.iterdir():
            if template_folder.is_dir():
                # Look for PPTX files in this template folder
                pptx_files = list(template_folder.glob("*.pptx"))
                if pptx_files:
                    # Use the first PPTX file found in the folder
                    template_file = pptx_files[0]
                    template_info = self._analyze_template(template_file, template_folder)
                    templates.append(template_info)
        
        # Fallback: Also check for legacy .pptx files directly in templates directory
        for template_file in self.templates_dir.glob("*.pptx"):
            template_info = self._analyze_template(template_file)
            templates.append(template_info)
        
        # Sort by name
        templates.sort(key=lambda t: t.name.lower())
        
        logger.info(f"Found {len(templates)} templates")
        return templates
    
    def _get_layout_count(self, template_name: str) -> int:
        """
        Get the number of layouts available for a template from layouts_export.json
        
        Args:
            template_name: Name of the template
            
        Returns:
            Number of layouts available, or 0 if not found
        """
        try:
            layouts_file = Path("layouts_export.json")
            if layouts_file.exists():
                with open(layouts_file, 'r') as f:
                    layouts_data = json.load(f)
                    count = len(layouts_data)
                    logger.debug(f"Found {count} layouts for template {template_name}")
                    return count
            else:
                logger.warning(f"layouts_export.json not found, cannot determine layout count for {template_name}")
                return 0
        except Exception as e:
            logger.error(f"Error reading layout count for {template_name}: {e}")
            return 0
    
    def _analyze_template(self, template_path: Path, template_folder: Optional[Path] = None) -> TemplateInfo:
        """
        Analyze a template file to extract information
        
        Args:
            template_path: Path to the template file
            template_folder: Path to the template folder (for new structure)
            
        Returns:
            TemplateInfo object with template details
        """
        filename = template_path.name
        
        # For new folder structure, use folder name as template name
        if template_folder and template_folder.parent.name == "templates":
            name = template_folder.name
        else:
            # Legacy: use file stem
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
        
        # Count locked background PNG files
        locked_backgrounds = 0
        folder_path_str = None
        
        if template_folder:
            folder_path_str = str(template_folder)
            locked_png_files = list(template_folder.glob("LOCKED_*.png"))
            locked_backgrounds = len(locked_png_files)
        
        # Get layout count from layouts_export.json
        layout_count = self._get_layout_count(name)
        if layout_count is None:
            layout_count = 0
        
        return TemplateInfo(
            filename=filename,
            path=str(template_path),
            name=name,
            size_mb=size_mb,
            slide_count=slide_count,
            layout_count=layout_count,
            is_valid=is_valid,
            error_message=error_message,
            folder_path=folder_path_str,
            locked_backgrounds=locked_backgrounds
        )
    
    def get_template_path(self, template_name: str) -> Optional[str]:
        """
        Get the full path for a template by name
        
        Args:
            template_name: Name of the template (folder name or filename)
            
        Returns:
            Full path to the template file, or None if not found
        """
        # New folder structure: Check if template_name is a folder name
        template_folder = self.templates_dir / template_name
        if template_folder.is_dir():
            # Look for PPTX files in the folder
            pptx_files = list(template_folder.glob("*.pptx"))
            if pptx_files:
                return str(pptx_files[0])
        
        # Legacy: Check if it's a direct PPTX filename
        if not template_name.endswith('.pptx'):
            template_name += '.pptx'
        
        template_path = self.templates_dir / template_name
        if template_path.exists():
            return str(template_path)
        
        logger.warning(f"Template not found: {template_name}")
        return None
    
    def get_default_template(self) -> Optional[str]:
        """
        Get the default template with preference for ekona template
        
        Returns:
            Path to default template, or None if no templates available
        """
        templates = self.list_templates()
        valid_templates = [t for t in templates if t.is_valid]
        
        if valid_templates:
            # CRITICAL FIX: Prefer ekona template over alphabetically first
            # This prevents Brochure template from being chosen when ekona is available
            ekona_template = next((t for t in valid_templates if 'ekona' in t.name.lower()), None)
            
            if ekona_template:
                default = ekona_template
                logger.info(f"Using preferred ekona template: {default.filename}")
            else:
                default = valid_templates[0]
                logger.info(f"Using default template: {default.filename}")
            
            return default.path
        
        logger.error("No valid templates found")
        return None
    
    def get_template_folder_path(self, template_name: str) -> Optional[str]:
        """
        Get the folder path for a template (for accessing SVG backgrounds)
        
        Args:
            template_name: Name of the template (folder name or filename)
            
        Returns:
            Full path to the template folder, or None if not found
        """
        # Check if template_name is a folder name
        template_folder = self.templates_dir / template_name
        if template_folder.is_dir():
            return str(template_folder)
        
        # If it's a filename, extract the folder name
        if template_name.endswith('.pptx'):
            folder_name = template_name[:-5]  # Remove .pptx
            template_folder = self.templates_dir / folder_name
            if template_folder.is_dir():
                return str(template_folder)
        
        # Legacy: For templates in root directory, return templates directory
        template_path = self.templates_dir / template_name
        if template_path.exists() and template_path.is_file():
            return str(self.templates_dir)
        
        logger.warning(f"Template folder not found for: {template_name}")
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