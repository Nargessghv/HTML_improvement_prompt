"""
Template Management Utilities

Handles template folder structure and path conversions for the new organized template system.
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any


class TemplateManager:
    """
    Manages template folders and provides utilities for the new folder-based template structure
    """
    
    def __init__(self, templates_root: str = "templates"):
        """
        Initialize template manager
        
        Args:
            templates_root: Root directory containing template folders
        """
        self.templates_root = Path(templates_root)
    
    def get_template_pptx_path(self, template_name: str) -> Optional[str]:
        """
        Get the PPTX file path for a template
        
        Args:
            template_name: Name of the template (e.g., "Brochure_template_1_1")
            
        Returns:
            Path to the PPTX file, or None if not found
        """
        template_folder = self.templates_root / template_name
        pptx_files = list(template_folder.glob("*.pptx"))
        
        if pptx_files:
            return str(pptx_files[0])  # Return first PPTX file found
        return None
    
    def get_template_folder_path(self, template_name: str) -> Optional[str]:
        """
        Get the folder path for a template
        
        Args:
            template_name: Name of the template
            
        Returns:
            Path to the template folder, or None if not found
        """
        template_folder = self.templates_root / template_name
        if template_folder.exists() and template_folder.is_dir():
            return str(template_folder)
        return None
    
    def get_available_templates(self) -> List[Dict[str, Any]]:
        """
        Get list of available templates with their details
        
        Returns:
            List of template info dictionaries
        """
        templates = []
        
        if not self.templates_root.exists():
            return templates
        
        for item in self.templates_root.iterdir():
            if item.is_dir():
                template_info = self._analyze_template_folder(item)
                if template_info:
                    templates.append(template_info)
        
        return templates
    
    def _analyze_template_folder(self, folder_path: Path) -> Optional[Dict[str, Any]]:
        """
        Analyze a template folder and extract information
        
        Args:
            folder_path: Path to the template folder
            
        Returns:
            Template information dictionary, or None if invalid
        """
        try:
            pptx_files = list(folder_path.glob("*.pptx"))
            png_files = list(folder_path.glob("*.png"))
            locked_backgrounds = [f for f in png_files if f.stem.startswith("LOCKED_")]
            
            if not pptx_files:
                return None  # No PPTX file found
            
            return {
                "name": folder_path.name,
                "display_name": folder_path.name.replace("_", " "),
                "folder_path": str(folder_path),
                "pptx_path": str(pptx_files[0]),
                "pptx_count": len(pptx_files),
                "png_count": len(png_files),
                "locked_backgrounds": len(locked_backgrounds),
                "locked_background_files": [f.stem for f in locked_backgrounds]
            }
        
        except Exception as e:
            print(f"Error analyzing template folder {folder_path}: {e}")
            return None
    
    def get_locked_background_files(self, template_name: str) -> List[str]:
        """
        Get list of locked background PNG files for a template
        
        Args:
            template_name: Name of the template
            
        Returns:
            List of PNG file paths for locked backgrounds
        """
        template_folder = self.templates_root / template_name
        if not template_folder.exists():
            return []
        
        locked_pngs = []
        for png_file in template_folder.glob("LOCKED_*.png"):
            locked_pngs.append(str(png_file))
        
        return locked_pngs
    
    def convert_old_template_path(self, old_path: str) -> str:
        """
        Convert old template path format to new folder-based format
        
        Args:
            old_path: Old template path (e.g., "templates/template.pptx")
            
        Returns:
            New template path (e.g., "templates/template_name/template.pptx")
        """
        path = Path(old_path)
        
        # If already in new format (has intermediate folder), return as-is
        if path.parent.name != "templates":
            return old_path
        
        # Convert from old format
        template_name = path.stem
        new_path = self.templates_root / template_name / path.name
        
        if new_path.exists():
            return str(new_path)
        
        # Fallback: return original path
        return old_path
    
    def ensure_template_structure(self) -> bool:
        """
        Ensure all templates follow the new folder structure
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.templates_root.exists():
                self.templates_root.mkdir(parents=True)
                return True
            
            # Check for old-format templates and move them
            old_templates = list(self.templates_root.glob("*.pptx"))
            
            for old_template in old_templates:
                template_name = old_template.stem
                new_folder = self.templates_root / template_name
                
                if not new_folder.exists():
                    new_folder.mkdir()
                    # Move the PPTX file
                    new_path = new_folder / old_template.name
                    old_template.rename(new_path)
                    print(f"✅ Moved {old_template.name} to new folder structure")
            
            return True
            
        except Exception as e:
            print(f"❌ Error ensuring template structure: {e}")
            return False


# Global template manager instance
template_manager = TemplateManager()


def get_template_pptx_path(template_name: str) -> Optional[str]:
    """
    Convenience function to get PPTX path for a template
    
    Args:
        template_name: Template name
        
    Returns:
        Path to PPTX file
    """
    return template_manager.get_template_pptx_path(template_name)


def get_template_folder_path(template_name: str) -> Optional[str]:
    """
    Convenience function to get folder path for a template
    
    Args:
        template_name: Template name
        
    Returns:
        Path to template folder
    """
    return template_manager.get_template_folder_path(template_name)


def convert_template_path(old_path: str) -> str:
    """
    Convenience function to convert old template paths to new format
    
    Args:
        old_path: Old template path
        
    Returns:
        New template path
    """
    return template_manager.convert_old_template_path(old_path)