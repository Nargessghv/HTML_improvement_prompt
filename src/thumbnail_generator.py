"""
Thumbnail Generator for PowerPoint Slides

Generates preview thumbnails from PPTX files for display in the UI.
"""

import os
import tempfile
import logging
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
import io

# Try to import Aspose Slides for direct PPTX to image conversion
try:
    import aspose.slides as slides
    HAS_ASPOSE_SLIDES = True
except ImportError:
    HAS_ASPOSE_SLIDES = False

# Try to import python-pptx2png for direct PPTX to image conversion
try:
    from pptx2png import convert
    HAS_PPTX2PNG = True
except ImportError:
    HAS_PPTX2PNG = False

# Alternative: Use pdf2image if available
try:
    from pdf2image import convert_from_path
    HAS_PDF2IMAGE = True
except ImportError:
    HAS_PDF2IMAGE = False

# For PPTX manipulation
from pptx import Presentation
from pptx.util import Inches

logger = logging.getLogger(__name__)


class ThumbnailGenerator:
    """
    Generates thumbnail images from PowerPoint slides
    """
    
    def __init__(self):
        """Initialize the thumbnail generator"""
        self.temp_dir = Path(tempfile.gettempdir()) / "slide_thumbnails"
        self.temp_dir.mkdir(exist_ok=True)
        
        # Check available conversion methods
        self.conversion_method = self._detect_conversion_method()
        logger.info(f"Thumbnail generator using method: {self.conversion_method}")
    
    def _detect_conversion_method(self) -> str:
        """Detect which conversion method is available"""
        if HAS_ASPOSE_SLIDES:
            return "aspose"
        elif HAS_PPTX2PNG:
            return "pptx2png"
        elif HAS_PDF2IMAGE:
            return "pdf2image"
        else:
            return "export_shapes"  # Fallback to exporting shapes as images
    
    def generate_thumbnail(
        self,
        pptx_path: str,
        output_path: Optional[str] = None,
        size: Tuple[int, int] = (400, 300),
        slide_number: int = 0
    ) -> Optional[str]:
        """
        Generate a thumbnail image from a PowerPoint slide
        
        Args:
            pptx_path: Path to the PPTX file
            output_path: Optional output path for the thumbnail
            size: Thumbnail size (width, height)
            slide_number: Which slide to create thumbnail from (0-indexed)
            
        Returns:
            Path to the generated thumbnail or None if failed
        """
        try:
            if not os.path.exists(pptx_path):
                logger.error(f"PPTX file not found: {pptx_path}")
                return None
            
            # Generate output path if not provided
            if not output_path:
                pptx_name = Path(pptx_path).stem
                output_path = self.temp_dir / f"{pptx_name}_thumbnail.png"
            
            # Use appropriate conversion method
            if self.conversion_method == "aspose":
                return self._generate_with_aspose(pptx_path, output_path, size, slide_number)
            elif self.conversion_method == "pptx2png":
                return self._generate_with_pptx2png(pptx_path, output_path, size, slide_number)
            elif self.conversion_method == "pdf2image":
                return self._generate_with_pdf2image(pptx_path, output_path, size, slide_number)
            else:
                return self._generate_with_export_shapes(pptx_path, output_path, size, slide_number)
                
        except Exception as e:
            logger.error(f"Error generating thumbnail: {e}")
            return None
    
    def _generate_with_pptx2png(
        self,
        pptx_path: str,
        output_path: str,
        size: Tuple[int, int],
        slide_number: int
    ) -> Optional[str]:
        """Generate thumbnail using pptx2png library"""
        try:
            # Convert PPTX to PNG
            images = convert(pptx_path, resolution=150)
            
            if slide_number < len(images):
                # Get the specified slide image
                image = images[slide_number]
                
                # Resize to thumbnail size
                image.thumbnail(size, Image.Resampling.LANCZOS)
                
                # Save thumbnail
                image.save(str(output_path), "PNG", optimize=True, quality=95)
                logger.info(f"Generated thumbnail with pptx2png: {output_path}")
                return str(output_path)
            
        except Exception as e:
            logger.error(f"pptx2png conversion failed: {e}")
        
        return None
    
    def _generate_with_aspose(
        self,
        pptx_path: str,
        output_path: str,
        size: Tuple[int, int],
        slide_number: int
    ) -> Optional[str]:
        """Generate thumbnail using Aspose Slides library"""
        try:
            # Load the presentation
            with slides.Presentation(pptx_path) as presentation:
                if slide_number >= len(presentation.slides):
                    logger.error(f"Slide {slide_number} not found in presentation")
                    return None
                
                # Get the specific slide
                slide = presentation.slides[slide_number]
                
                # Create thumbnail
                # Aspose uses a scale factor - calculate based on desired size
                # Standard slide size is typically 960x720, scale accordingly
                scale_x = size[0] / 960.0
                scale_y = size[1] / 720.0
                scale = min(scale_x, scale_y)  # Maintain aspect ratio
                
                # Generate thumbnail
                thumbnail = slide.get_thumbnail(scale, scale)
                
                # Save as PNG
                thumbnail.save(output_path, slides.ImageFormat.PNG)
                
                logger.info(f"Generated thumbnail with Aspose Slides: {output_path}")
                return str(output_path)
                
        except Exception as e:
            logger.error(f"Aspose Slides conversion failed: {e}")
            import traceback
            traceback.print_exc()
        
        return None
    
    def _generate_with_pdf2image(
        self,
        pptx_path: str,
        output_path: str,
        size: Tuple[int, int],
        slide_number: int
    ) -> Optional[str]:
        """Generate thumbnail by first converting to PDF then to image"""
        try:
            # This method requires LibreOffice or similar to convert PPTX to PDF
            # For now, return None as this requires external dependencies
            logger.warning("PDF conversion method not fully implemented")
            return None
            
        except Exception as e:
            logger.error(f"PDF conversion failed: {e}")
            return None
    
    def _generate_with_export_shapes(
        self,
        pptx_path: str,
        output_path: str,
        size: Tuple[int, int],
        slide_number: int
    ) -> Optional[str]:
        """Generate thumbnail by exporting slide content as image (fallback method)"""
        try:
            # Open the presentation
            prs = Presentation(pptx_path)
            
            if slide_number >= len(prs.slides):
                logger.error(f"Slide {slide_number} not found in presentation")
                return None
            
            slide = prs.slides[slide_number]
            
            # Create a blank image with white background
            img = Image.new('RGB', size, color='white')
            
            # Add a placeholder thumbnail with slide information
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(img)
            
            # Try to get slide title
            title = "Slide Preview"
            if slide.shapes.title:
                title = slide.shapes.title.text or title
            
            # Draw basic slide representation
            margin = 20
            border_rect = [margin, margin, size[0] - margin, size[1] - margin]
            draw.rectangle(border_rect, outline='#cccccc', width=2)
            
            # Add slide number
            slide_num_text = f"Slide {slide_number + 1}"
            try:
                # Try to use a better font if available
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
            except:
                font = ImageFont.load_default()
            
            # Draw slide number
            draw.text((margin + 10, margin + 10), slide_num_text, fill='#666666', font=font)
            
            # Draw title
            try:
                title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
            except:
                title_font = ImageFont.load_default()
            
            # Wrap long titles
            title_lines = []
            words = title.split()
            current_line = ""
            for word in words:
                test_line = f"{current_line} {word}".strip()
                bbox = draw.textbbox((0, 0), test_line, font=title_font)
                if bbox[2] - bbox[0] > size[0] - 2 * margin - 20:
                    if current_line:
                        title_lines.append(current_line)
                    current_line = word
                else:
                    current_line = test_line
            if current_line:
                title_lines.append(current_line)
            
            # Draw title lines
            y_offset = margin + 50
            for line in title_lines[:3]:  # Max 3 lines
                draw.text((margin + 10, y_offset), line, fill='#333333', font=title_font)
                y_offset += 25
            
            # Add content preview indicator
            content_count = len([s for s in slide.shapes if s.has_text_frame])
            if content_count > 0:
                content_text = f"{content_count} text element{'s' if content_count > 1 else ''}"
                draw.text((margin + 10, size[1] - margin - 30), content_text, fill='#999999')
            
            # Add "Preview" watermark
            try:
                watermark_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
            except:
                watermark_font = ImageFont.load_default()
            
            draw.text(
                (size[0] - margin - 60, size[1] - margin - 20),
                "Preview",
                fill='#cccccc',
                font=watermark_font
            )
            
            # Save the image
            img.save(str(output_path), "PNG", optimize=True, quality=95)
            logger.info(f"Generated fallback thumbnail: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Export shapes method failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def generate_slide_thumbnails(
        self,
        pptx_path: str,
        output_dir: Optional[str] = None,
        size: Tuple[int, int] = (400, 300)
    ) -> dict:
        """
        Generate thumbnails for all slides in a presentation
        
        Args:
            pptx_path: Path to the PPTX file
            output_dir: Optional output directory for thumbnails
            size: Thumbnail size (width, height)
            
        Returns:
            Dictionary mapping slide numbers to thumbnail paths
        """
        thumbnails = {}
        
        try:
            prs = Presentation(pptx_path)
            num_slides = len(prs.slides)
            
            if not output_dir:
                output_dir = self.temp_dir
            else:
                output_dir = Path(output_dir)
                output_dir.mkdir(exist_ok=True)
            
            pptx_name = Path(pptx_path).stem
            
            for i in range(num_slides):
                thumbnail_path = output_dir / f"{pptx_name}_slide_{i+1}_thumb.png"
                result = self.generate_thumbnail(
                    pptx_path,
                    str(thumbnail_path),
                    size,
                    i
                )
                if result:
                    thumbnails[i + 1] = result
                    
        except Exception as e:
            logger.error(f"Error generating thumbnails: {e}")
        
        return thumbnails


# Test function
if __name__ == "__main__":
    # Test the thumbnail generator
    generator = ThumbnailGenerator()
    
    # Test with a sample PPTX file
    test_pptx = "test_presentation.pptx"
    if os.path.exists(test_pptx):
        thumbnail = generator.generate_thumbnail(test_pptx)
        if thumbnail:
            print(f"✅ Thumbnail generated: {thumbnail}")
        else:
            print("❌ Failed to generate thumbnail")
    else:
        print(f"Test file not found: {test_pptx}")