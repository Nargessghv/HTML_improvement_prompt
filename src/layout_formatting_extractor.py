"""
Layout Formatting Extractor

Extracts text formatting from PowerPoint layout XML files to preserve
template styling when programmatically setting text content.
"""

import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional
import re
from pptx.util import Pt
from pptx.dml.color import RGBColor


class LayoutFormattingExtractor:
    """Extract and preserve text formatting from PowerPoint layout XML"""
    
    # XML namespaces
    NAMESPACES = {
        'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
        'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
        'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    }
    
    def __init__(self):
        self.placeholder_formats: Dict[int, Dict[str, Any]] = {}
    
    def extract_from_layout(self, layout):
        """
        Extract formatting from a slide layout
        
        Args:
            layout: python-pptx slide layout object
            
        Returns:
            Dictionary mapping placeholder idx to formatting properties
        """
        try:
            # Access the layout's XML part
            layout_part = layout.part
            layout_xml = layout_part.blob
            
            # Parse the XML
            root = ET.fromstring(layout_xml)
            
            # Find all shape elements with placeholders
            shapes = root.findall('.//p:sp', self.NAMESPACES)
            
            for shape in shapes:
                # Get placeholder index
                ph_elem = shape.find('.//p:ph', self.NAMESPACES)
                if ph_elem is None:
                    continue
                    
                idx = ph_elem.get('idx')
                if idx is None:
                    continue
                    
                idx = int(idx)
                
                # Get placeholder name
                name_elem = shape.find('.//p:cNvPr', self.NAMESPACES)
                name = name_elem.get('name', '') if name_elem is not None else ''
                
                # Extract text formatting
                formatting = self._extract_text_formatting(shape)
                if formatting:
                    formatting['name'] = name
                    self.placeholder_formats[idx] = formatting
                    
            return self.placeholder_formats
            
        except Exception as e:
            print(f"Error extracting layout formatting: {e}")
            return {}
    
    def _extract_text_formatting(self, shape_elem) -> Dict[str, Any]:
        """
        Extract text formatting from a shape element
        
        Args:
            shape_elem: XML element for a shape
            
        Returns:
            Dictionary of formatting properties
        """
        formatting = {}
        
        try:
            # Find the default run properties
            defRPr = shape_elem.find('.//a:defRPr', self.NAMESPACES)
            if defRPr is None:
                # Try lvl1pPr for list styles
                defRPr = shape_elem.find('.//a:lvl1pPr/a:defRPr', self.NAMESPACES)
            
            if defRPr is not None:
                # Extract font size (in 100ths of points)
                sz = defRPr.get('sz')
                if sz:
                    formatting['font_size'] = Pt(int(sz) / 100)
                
                # Extract bold
                bold = defRPr.get('b')
                if bold:
                    formatting['bold'] = bold == '1'
                
                # Extract italic
                italic = defRPr.get('i')
                if italic:
                    formatting['italic'] = italic == '1'
                
                # Extract font name
                latin = defRPr.find('a:latin', self.NAMESPACES)
                if latin is not None:
                    typeface = latin.get('typeface')
                    if typeface:
                        formatting['font_name'] = typeface
                
                # Extract color
                color_elem = None
                
                # Check for solid fill color
                solidFill = defRPr.find('a:solidFill', self.NAMESPACES)
                if solidFill is not None:
                    # RGB color
                    srgbClr = solidFill.find('a:srgbClr', self.NAMESPACES)
                    if srgbClr is not None:
                        val = srgbClr.get('val')
                        if val:
                            formatting['font_color'] = val
                            # Convert hex to RGB tuple for python-pptx
                            formatting['font_color_rgb'] = self._hex_to_rgb(val)
                    
                    # Theme color
                    schemeClr = solidFill.find('a:schemeClr', self.NAMESPACES)
                    if schemeClr is not None:
                        val = schemeClr.get('val')
                        if val:
                            formatting['font_color_theme'] = val
                
                # Extract paragraph properties
                lvl1pPr = shape_elem.find('.//a:lvl1pPr', self.NAMESPACES)
                if lvl1pPr is not None:
                    # Paragraph alignment (left, center, right, justify)
                    algn = lvl1pPr.get('algn')
                    if algn:
                        formatting['alignment'] = algn  # 'l', 'ctr', 'r', 'just'
                    
                    # Margin left
                    marL = lvl1pPr.get('marL')
                    if marL:
                        formatting['margin_left'] = int(marL)
                    
                    # Margin right
                    marR = lvl1pPr.get('marR')
                    if marR:
                        formatting['margin_right'] = int(marR)
                    
                    # Indent (first line or hanging indent)
                    indent = lvl1pPr.get('indent')
                    if indent:
                        formatting['indent'] = int(indent)
                    
                    # Line spacing
                    lnSpc = lvl1pPr.find('a:lnSpc', self.NAMESPACES)
                    if lnSpc is not None:
                        spcPct = lnSpc.find('a:spcPct', self.NAMESPACES)
                        if spcPct is not None:
                            val = spcPct.get('val')
                            if val:
                                formatting['line_spacing'] = int(val) / 1000  # Convert to percentage
                    
                    # Space before paragraph
                    spcBef = lvl1pPr.find('a:spcBef', self.NAMESPACES)
                    if spcBef is not None:
                        spcPts = spcBef.find('a:spcPts', self.NAMESPACES)
                        if spcPts is not None:
                            val = spcPts.get('val')
                            if val:
                                formatting['space_before'] = int(val)
                    
                    # Space after paragraph
                    spcAft = lvl1pPr.find('a:spcAft', self.NAMESPACES)
                    if spcAft is not None:
                        spcPts = spcAft.find('a:spcPts', self.NAMESPACES)
                        if spcPts is not None:
                            val = spcPts.get('val')
                            if val:
                                formatting['space_after'] = int(val)
                    
                    # Bullet properties
                    buNone = lvl1pPr.find('a:buNone', self.NAMESPACES)
                    if buNone is not None:
                        formatting['bullet'] = False
                    else:
                        formatting['bullet'] = True
                        
                        # Bullet character
                        buChar = lvl1pPr.find('a:buChar', self.NAMESPACES)
                        if buChar is not None:
                            char = buChar.get('char')
                            if char:
                                formatting['bullet_char'] = char
                        
                        # Bullet font
                        buFont = lvl1pPr.find('a:buFont', self.NAMESPACES)
                        if buFont is not None:
                            typeface = buFont.get('typeface')
                            if typeface:
                                formatting['bullet_font'] = typeface
                        
                        # Bullet color
                        buClr = lvl1pPr.find('a:buClr', self.NAMESPACES)
                        if buClr is not None:
                            srgbClr = buClr.find('a:srgbClr', self.NAMESPACES)
                            if srgbClr is not None:
                                val = srgbClr.get('val')
                                if val:
                                    formatting['bullet_color'] = val
                                    formatting['bullet_color_rgb'] = self._hex_to_rgb(val)
                        
                        # Bullet size (percentage of text)
                        buSzPct = lvl1pPr.find('a:buSzPct', self.NAMESPACES)
                        if buSzPct is not None:
                            val = buSzPct.get('val')
                            if val:
                                formatting['bullet_size_pct'] = int(val) / 1000  # Convert to percentage
        
        except Exception as e:
            print(f"Error extracting text formatting: {e}")
        
        return formatting
    
    def _hex_to_rgb(self, hex_color: str) -> RGBColor:
        """
        Convert hex color string to RGBColor object
        
        Args:
            hex_color: Hex color string (e.g., '002060')
            
        Returns:
            RGBColor object
        """
        # Remove # if present
        hex_color = hex_color.lstrip('#')
        
        # Convert to RGB
        try:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return RGBColor(r, g, b)
        except:
            return None
    
    def get_placeholder_formatting(self, idx: int) -> Dict[str, Any]:
        """
        Get formatting for a specific placeholder by index
        
        Args:
            idx: Placeholder index
            
        Returns:
            Dictionary of formatting properties
        """
        return self.placeholder_formats.get(idx, {})
    
    def apply_formatting_to_run(self, run, idx: int):
        """
        Apply extracted formatting to a text run
        
        Args:
            run: python-pptx text run object
            idx: Placeholder index
        """
        formatting = self.get_placeholder_formatting(idx)
        if not formatting:
            return
        
        font = run.font
        
        # Apply font name
        if 'font_name' in formatting:
            try:
                font.name = formatting['font_name']
            except:
                pass
        
        # Apply font size
        if 'font_size' in formatting:
            try:
                font.size = formatting['font_size']
            except:
                pass
        
        # Apply bold
        if 'bold' in formatting:
            try:
                font.bold = formatting['bold']
            except:
                pass
        
        # Apply italic
        if 'italic' in formatting:
            try:
                font.italic = formatting['italic']
            except:
                pass
        
        # Apply color - only RGB colors, not theme colors
        if 'font_color_rgb' in formatting and formatting['font_color_rgb']:
            try:
                font.color.rgb = formatting['font_color_rgb']
            except:
                pass
        # Note: We skip theme colors (font_color_theme) as they can cause corruption
        # if not properly handled by python-pptx
    
    def apply_paragraph_formatting(self, paragraph, idx: int):
        """
        Apply extracted paragraph formatting
        
        Args:
            paragraph: python-pptx paragraph object
            idx: Placeholder index
        """
        formatting = self.get_placeholder_formatting(idx)
        if not formatting:
            return
        
        # Apply alignment
        if 'alignment' in formatting:
            from pptx.enum.text import PP_ALIGN
            alignment_map = {
                'l': PP_ALIGN.LEFT,
                'ctr': PP_ALIGN.CENTER,
                'r': PP_ALIGN.RIGHT,
                'just': PP_ALIGN.JUSTIFY
            }
            if formatting['alignment'] in alignment_map:
                try:
                    paragraph.alignment = alignment_map[formatting['alignment']]
                except:
                    pass
        
        # Apply margins and indentation
        if 'margin_left' in formatting:
            try:
                paragraph.level = 0  # Reset level first
                # Convert EMU to Pt (1 inch = 914400 EMU = 72 Pt)
                from pptx.util import Emu
                paragraph.left_indent = Emu(formatting['margin_left'])
            except:
                pass
        
        if 'indent' in formatting:
            try:
                from pptx.util import Emu
                paragraph.first_line_indent = Emu(formatting['indent'])
            except:
                pass
        
        # Apply spacing
        if 'line_spacing' in formatting:
            try:
                paragraph.line_spacing = formatting['line_spacing']
            except:
                pass
        
        if 'space_before' in formatting:
            try:
                from pptx.util import Pt
                paragraph.space_before = Pt(formatting['space_before'] / 100)
            except:
                pass
        
        if 'space_after' in formatting:
            try:
                from pptx.util import Pt
                paragraph.space_after = Pt(formatting['space_after'] / 100)
            except:
                pass
    
    def apply_bullet_formatting(self, paragraph, idx: int):
        """
        Apply extracted bullet formatting
        
        Args:
            paragraph: python-pptx paragraph object
            idx: Placeholder index
        """
        formatting = self.get_placeholder_formatting(idx)
        if not formatting:
            return
        
        # Apply bullet settings
        if 'bullet' in formatting:
            if formatting['bullet']:
                # Enable bullets
                try:
                    from pptx.enum.text import PP_BULLET
                    
                    # Set bullet character if specified
                    if 'bullet_char' in formatting:
                        paragraph.bullet.char = formatting['bullet_char']
                    else:
                        paragraph.bullet.char = '•'  # Default bullet
                    
                    # Set bullet font if specified
                    if 'bullet_font' in formatting:
                        paragraph.bullet.font.name = formatting['bullet_font']
                    
                    # Set bullet color if specified
                    if 'bullet_color_rgb' in formatting:
                        paragraph.bullet.font.color.rgb = formatting['bullet_color_rgb']
                    
                    # Set bullet size if specified
                    if 'bullet_size_pct' in formatting:
                        paragraph.bullet.relative_size = formatting['bullet_size_pct']
                    
                    paragraph.bullet.visible = True
                except Exception as e:
                    print(f"Could not apply bullet formatting: {e}")
            else:
                # Disable bullets
                try:
                    paragraph.bullet.visible = False
                except:
                    pass