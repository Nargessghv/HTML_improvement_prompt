"""
Markdown Formatter Module

This module converts markdown-formatted content to PowerPoint text formatting,
handling headers, bold, italic, bullets, numbered lists, etc.
PRESERVES TEMPLATE FORMATTING - Uses template's font sizes and styles.
"""

import re
from typing import Any, Dict, List, Tuple

from pptx.dml.color import RGBColor
from pptx.text.text import TextFrame


class MarkdownFormatter:
    """
    Converts markdown content to PowerPoint formatted text while preserving
    template formatting

    New Approach:
    - Captures template's original font sizes, styles, and formatting
    - Applies markdown formatting (bold, italic, bullets) while preserving
      template design
    - No hardcoded font size caps - uses your template's exact specifications
    """

    def format_text_frame(self, text_frame: TextFrame, markdown_content: str, layout_formatting: Dict[str, Any] = None) -> None:
        """
        Format a PowerPoint text frame with markdown content while preserving
        template styling

        Args:
            text_frame: PowerPoint text frame object
            markdown_content: Markdown-formatted content string
            layout_formatting: Optional pre-extracted layout formatting
        """
        # STEP 1: Capture original template formatting BEFORE clearing
        original_formatting = self._capture_template_formatting(text_frame)
        
        # Merge with provided layout formatting if available
        if layout_formatting:
            original_formatting.update(layout_formatting)

        # STEP 2: Clear existing content carefully to preserve formatting
        # Instead of text_frame.clear(), we'll keep the first paragraph and clear its text
        if text_frame.paragraphs:
            # Keep first paragraph to preserve its formatting
            first_para = text_frame.paragraphs[0]
            first_para.text = ""  # Clear text but keep paragraph
            
            # Remove additional paragraphs if any
            while len(text_frame.paragraphs) > 1:
                # Access the internal element to remove extra paragraphs
                p_elem = text_frame.paragraphs[-1]._element
                text_frame._element.remove(p_elem)
        else:
            # No paragraphs, need to add one
            text_frame.add_paragraph()

        # STEP 3: Parse markdown into structured elements
        elements = self._parse_markdown(markdown_content)

        # STEP 4: Apply formatting to text frame while preserving template styling
        self._apply_formatting_preserving_template(
            text_frame, elements, original_formatting
        )

    def _capture_template_formatting(self, text_frame: TextFrame) -> Dict[str, Any]:
        """
        Capture the template's original formatting before we modify the text frame

        Args:
            text_frame: PowerPoint text frame object

        Returns:
            Dictionary containing original template formatting
        """
        template_format: Dict[str, Any] = {
            "font_name": None,
            "font_size": None,
            "bold": None,
            "italic": None,
            "color": None,
            "paragraph_alignment": None,
            "paragraph_level": None,
        }

        try:
            if text_frame.paragraphs:
                # Get formatting from first paragraph (template default)
                paragraph = text_frame.paragraphs[0]

                # Capture paragraph-level formatting
                template_format["paragraph_level"] = getattr(paragraph, "level", 0)
                template_format["paragraph_alignment"] = getattr(
                    paragraph, "alignment", None
                )

                # Capture font formatting from paragraph
                if hasattr(paragraph, "font") and paragraph.font:
                    para_font = paragraph.font
                    template_format["font_name"] = para_font.name
                    template_format["font_size"] = para_font.size
                    template_format["bold"] = para_font.bold
                    template_format["italic"] = para_font.italic
                    template_format["color"] = para_font.color

                # If paragraph font is None, try first run
                if paragraph.runs:
                    run = paragraph.runs[0]
                    if hasattr(run, "font") and run.font:
                        run_font = run.font
                        # Only use run values if paragraph values are None
                        if template_format["font_name"] is None:
                            template_format["font_name"] = run_font.name
                        if template_format["font_size"] is None:
                            template_format["font_size"] = run_font.size
                        if template_format["bold"] is None:
                            template_format["bold"] = run_font.bold
                        if template_format["italic"] is None:
                            template_format["italic"] = run_font.italic
                        if template_format["color"] is None:
                            template_format["color"] = run_font.color

        except Exception as e:
            print(f"  → Warning: Could not capture template formatting: {e}")
            # Continue with empty formatting - PowerPoint will use defaults

        return template_format

    def _parse_markdown(self, content: str) -> List[Tuple[str, str, dict]]:
        """
        Parse markdown content into structured elements

        Args:
            content: Markdown content string

        Returns:
            List of tuples: (element_type, text_content, formatting_options)
        """
        elements = []
        lines = content.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for different markdown elements
            if line.startswith("# "):
                # Header 1 - NO hardcoded font size, preserve template
                text = line[2:].strip()
                elements.append(("header1", text, {"level": 0, "markdown_bold": True}))

            elif line.startswith("## "):
                # Header 2 - NO hardcoded font size, preserve template
                text = line[3:].strip()
                elements.append(("header2", text, {"level": 0, "markdown_bold": True}))

            elif line.startswith("### "):
                # Header 3 - NO hardcoded font size, preserve template
                text = line[4:].strip()
                elements.append(("header3", text, {"level": 0, "markdown_bold": True}))

            elif line.startswith("- ") or line.startswith("* "):
                # Bullet point - check for indentation to determine level
                stripped = line.lstrip()
                indent_count = len(line) - len(stripped)
                level = min(indent_count // 2, 4)  # Support up to 5 levels (0-4)
                
                text = stripped[2:].strip() if stripped.startswith(("- ", "* ")) else stripped
                formatted_text = self._process_inline_formatting(text)
                
                # If template has bullets defined, use level 0 for main bullets
                # Otherwise use level 1 (PowerPoint default)
                bullet_level = level if level > 0 else 0
                elements.append(("bullet", formatted_text, {"level": bullet_level}))

            elif re.match(r"^\d+\.\s", line):
                # Numbered list
                text = re.sub(r"^\d+\.\s", "", line).strip()
                formatted_text = self._process_inline_formatting(text)
                elements.append(("numbered", formatted_text, {"level": 1}))

            else:
                # Regular paragraph
                formatted_text = self._process_inline_formatting(line)
                elements.append(("paragraph", formatted_text, {"level": 0}))

        return elements

    def _process_inline_formatting(self, text: str) -> List[Tuple[str, dict]]:
        """
        Process inline markdown formatting (bold, italic, etc.)

        Args:
            text: Text with inline markdown

        Returns:
            List of (text_segment, formatting_dict) tuples
        """
        segments = []
        remaining_text = text

        # Process **bold** text
        while "**" in remaining_text:
            start = remaining_text.find("**")
            if start == -1:
                break

            # Add text before bold
            if start > 0:
                segments.append((remaining_text[:start], {}))

            # Find end of bold
            end = remaining_text.find("**", start + 2)
            if end == -1:
                # No closing **, treat as regular text
                segments.append((remaining_text[start:], {}))
                break

            # Add bold text
            bold_text = remaining_text[start + 2 : end]
            segments.append((bold_text, {"markdown_bold": True}))

            # Continue with remaining text
            remaining_text = remaining_text[end + 2 :]

        # Add any remaining text
        if remaining_text:
            segments.append((remaining_text, {}))

        # If no segments were created, add the original text
        if not segments:
            segments.append((text, {}))

        # Process *italic* text in each segment
        final_segments = []
        for segment_text, segment_format in segments:
            if "*" in segment_text and "markdown_bold" not in segment_format:
                # Process italic formatting
                final_segments.extend(
                    self._process_italic_formatting(segment_text, segment_format)
                )
            else:
                final_segments.append((segment_text, segment_format))

        return final_segments

    def _process_italic_formatting(
        self, text: str, base_format: dict
    ) -> List[Tuple[str, dict]]:
        """
        Process *italic* formatting in text

        Args:
            text: Text that may contain italic formatting
            base_format: Base formatting to apply

        Returns:
            List of (text_segment, formatting_dict) tuples
        """
        segments = []
        remaining_text = text

        while "*" in remaining_text:
            start = remaining_text.find("*")
            if start == -1:
                break

            # Add text before italic
            if start > 0:
                segments.append((remaining_text[:start], base_format.copy()))

            # Find end of italic
            end = remaining_text.find("*", start + 1)
            if end == -1:
                # No closing *, treat as regular text
                segments.append((remaining_text[start:], base_format.copy()))
                break

            # Add italic text
            italic_text = remaining_text[start + 1 : end]
            italic_format = base_format.copy()
            italic_format["markdown_italic"] = True
            segments.append((italic_text, italic_format))

            # Continue with remaining text
            remaining_text = remaining_text[end + 1 :]

        # Add any remaining text
        if remaining_text:
            segments.append((remaining_text, base_format.copy()))

        return segments if segments else [(text, base_format)]

    def _apply_formatting_preserving_template(
        self,
        text_frame: TextFrame,
        elements: List[Tuple[str, str, dict]],
        template_formatting: Dict[str, Any],
    ) -> None:
        """
        Apply parsed markdown elements to a PowerPoint text frame while preserving
        template formatting

        Args:
            text_frame: PowerPoint text frame
            elements: Parsed markdown elements
            template_formatting: Original template formatting to preserve
        """
        for i, (element_type, content, options) in enumerate(elements):
            # Add paragraph (first one already exists)
            if i == 0:
                paragraph = text_frame.paragraphs[0]
            else:
                paragraph = text_frame.add_paragraph()

            # Set paragraph level for bullets/numbering
            paragraph.level = options.get(
                "level", template_formatting.get("paragraph_level", 0)
            )
            
            # Apply paragraph-level formatting from template
            self._apply_paragraph_formatting(paragraph, template_formatting)

            # Handle different element types
            if element_type in ["bullet", "numbered"]:
                # For lists, set the text and formatting
                if isinstance(content, list):
                    # Multiple formatted segments
                    for j, (text_segment, segment_format) in enumerate(content):
                        if j == 0:
                            run = (
                                paragraph.runs[0]
                                if paragraph.runs
                                else paragraph.add_run()
                            )
                        else:
                            run = paragraph.add_run()

                        run.text = text_segment
                        self._apply_run_formatting_preserving_template(
                            run,
                            segment_format if isinstance(segment_format, dict) else {},
                            template_formatting,
                        )
                else:
                    # Single text string
                    paragraph.text = str(content)
                    # Apply template formatting to the paragraph's run
                    if paragraph.runs:
                        self._apply_run_formatting_preserving_template(
                            paragraph.runs[0], {}, template_formatting
                        )

            elif element_type in ["header1", "header2", "header3", "paragraph"]:
                # For headers and paragraphs
                if isinstance(content, list):
                    # Multiple formatted segments
                    for j, (text_segment, segment_format) in enumerate(content):
                        if j == 0:
                            run = (
                                paragraph.runs[0]
                                if paragraph.runs
                                else paragraph.add_run()
                            )
                        else:
                            run = paragraph.add_run()

                        run.text = text_segment

                        # Combine element formatting with segment formatting
                        combined_format = options.copy()
                        if isinstance(segment_format, dict):
                            combined_format.update(segment_format)
                        self._apply_run_formatting_preserving_template(
                            run, combined_format, template_formatting
                        )
                else:
                    # Single text string
                    paragraph.text = str(content)
                    # Apply formatting to the paragraph's run
                    if paragraph.runs:
                        combined_format = options.copy()
                        self._apply_run_formatting_preserving_template(
                            paragraph.runs[0], combined_format, template_formatting
                        )

    def _apply_paragraph_formatting(self, paragraph, template_formatting: Dict[str, Any]) -> None:
        """
        Apply paragraph-level formatting from template
        
        Args:
            paragraph: PowerPoint paragraph object
            template_formatting: Template formatting to apply
        """
        from pptx.enum.text import PP_ALIGN
        
        # Apply alignment
        if 'alignment' in template_formatting:
            alignment_map = {
                'l': PP_ALIGN.LEFT,
                'ctr': PP_ALIGN.CENTER,
                'r': PP_ALIGN.RIGHT,
                'just': PP_ALIGN.JUSTIFY
            }
            if template_formatting['alignment'] in alignment_map:
                try:
                    paragraph.alignment = alignment_map[template_formatting['alignment']]
                except:
                    pass
        
        # Note: Bullet formatting in python-pptx is controlled by paragraph level
        # The template defines whether bullets appear at each level
        # We can't directly set bullet properties through python-pptx
        # but the level will trigger the template's bullet settings
        
        # Apply indentation
        if 'margin_left' in template_formatting:
            try:
                from pptx.util import Emu
                paragraph.left_indent = Emu(template_formatting['margin_left'])
            except:
                pass
        
        if 'indent' in template_formatting:
            try:
                from pptx.util import Emu
                paragraph.first_line_indent = Emu(template_formatting['indent'])
            except:
                pass
        
        # Apply spacing
        if 'line_spacing' in template_formatting:
            try:
                paragraph.line_spacing = template_formatting['line_spacing']
            except:
                pass
        
        if 'space_before' in template_formatting:
            try:
                from pptx.util import Pt
                paragraph.space_before = Pt(template_formatting['space_before'] / 100)
            except:
                pass
        
        if 'space_after' in template_formatting:
            try:
                from pptx.util import Pt
                paragraph.space_after = Pt(template_formatting['space_after'] / 100)
            except:
                pass
    
    def _apply_run_formatting_preserving_template(
        self, run, markdown_formatting: dict, template_formatting: Dict[str, Any]
    ) -> None:
        """
        Apply formatting options to a text run while preserving template formatting

        Args:
            run: PowerPoint text run object
            markdown_formatting: Markdown-specific formatting to apply
            template_formatting: Original template formatting to preserve
        """
        font = run.font

        # PRESERVE TEMPLATE FONT NAME (safely)
        try:
            if template_formatting.get("font_name") is not None:
                font.name = template_formatting["font_name"]
        except (AttributeError, TypeError):
            # Font name might be theme-controlled, skip silently
            pass

        # PRESERVE TEMPLATE FONT SIZE (safely, NO CAPS!)
        try:
            if template_formatting.get("font_size") is not None:
                font.size = template_formatting["font_size"]
                print(
                    f"  ✓ Preserved template font size: {template_formatting['font_size']}"
                )
        except (AttributeError, TypeError):
            # Font size might be theme-controlled, skip silently
            print("  → Font size is theme-controlled, keeping template default")

        # APPLY TEMPLATE BOLD/ITALIC AS BASE, THEN MARKDOWN OVERRIDES (safely)
        # Start with template's base bold/italic settings
        base_bold = template_formatting.get("bold", False)
        base_italic = template_formatting.get("italic", False)

        # Apply markdown bold (if specified, override template)
        try:
            if markdown_formatting.get("markdown_bold"):
                font.bold = True
            elif base_bold is not None:
                font.bold = base_bold
        except (AttributeError, TypeError):
            # Bold might be theme-controlled, skip silently
            pass

        # Apply markdown italic (if specified, override template)
        try:
            if markdown_formatting.get("markdown_italic"):
                font.italic = True
            elif base_italic is not None:
                font.italic = base_italic
        except (AttributeError, TypeError):
            # Italic might be theme-controlled, skip silently
            pass

        # PRESERVE TEMPLATE COLOR (safely)
        try:
            # Only apply color if we have a valid RGB color
            if template_formatting.get("font_color_rgb") is not None:
                font.color.rgb = template_formatting["font_color_rgb"]
            elif template_formatting.get("color") is not None and hasattr(template_formatting["color"], "rgb"):
                # This is a color object with RGB, apply it directly
                font.color = template_formatting["color"]
            # Skip theme colors - they can cause corruption if not handled properly
        except (AttributeError, TypeError):
            # Color might be theme-controlled, skip silently
            pass

        # Handle any custom color from markdown (rare, but supported)
        try:
            if "color" in markdown_formatting:
                if isinstance(markdown_formatting["color"], str):
                    # Handle hex color
                    color_hex = markdown_formatting["color"].lstrip("#")
                    r, g, b = tuple(int(color_hex[i : i + 2], 16) for i in (0, 2, 4))
                    font.color.rgb = RGBColor(r, g, b)
        except (AttributeError, TypeError, ValueError):
            # Color setting failed, skip silently
            pass
