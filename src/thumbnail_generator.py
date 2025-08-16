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

# Try to import Spire.Presentation for direct PPTX to image conversion
try:
    from spire.presentation import Presentation as SpirePresentation
    from spire.presentation import FileFormat, ImageFormat
    HAS_SPIRE_PRESENTATION = True
except ImportError:
    HAS_SPIRE_PRESENTATION = False

# Try to import Aspose Slides for direct PPTX to image conversion (fallback)
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
        # Use Microsoft Graph API for PPTX to PDF conversion (cloud-native)
        if os.environ.get('AZURE_CLIENT_ID') and os.environ.get('AZURE_CLIENT_SECRET'):
            return "microsoft_graph"
        
        # Fallback to PDF2Image with LibreOffice for local development
        if HAS_PDF2IMAGE:
            return "pdf2image"
        
        # Final fallback to shape extraction
        return "export_shapes"
    
    def generate_thumbnail(
        self,
        pptx_path: str,
        output_path: Optional[str] = None,
        size: Tuple[int, int] = (400, 300),
        slide_number: int = 0,
        user_access_token: Optional[str] = None
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
            
            # Use appropriate conversion method based on environment
            if self.conversion_method == "microsoft_graph":
                return self._generate_with_microsoft_graph(pptx_path, output_path, size, slide_number)
            elif self.conversion_method == "pdf2image":
                return self._generate_with_pdf2image(pptx_path, output_path, size, slide_number)
            else:
                return self._generate_with_export_shapes(pptx_path, output_path, size, slide_number)
                
        except Exception as e:
            logger.error(f"Error generating thumbnail: {e}")
            return None
    
    def _generate_with_microsoft_graph(
        self,
        pptx_path: str,
        output_path: str,
        size: tuple[int, int],
        slide_number: int,
        user_access_token: Optional[str] = None
    ) -> Optional[str]:
        """Generate thumbnail using Microsoft Graph API for PPTX to PDF conversion"""
        import requests
        import tempfile
        from pdf2image import convert_from_path
        
        try:
            # Get access token for Microsoft Graph
            access_token = self._get_graph_access_token(user_access_token)
            if not access_token:
                logger.error("Failed to get Microsoft Graph access token")
                return None
            
            # Create temporary PDF file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
                temp_pdf_path = temp_pdf.name
            
            try:
                # Upload PPTX file to OneDrive and convert to PDF
                pdf_content = self._convert_pptx_to_pdf_via_graph(pptx_path, access_token)
                if not pdf_content:
                    logger.error("Failed to convert PPTX to PDF via Microsoft Graph")
                    return None
                
                # Save PDF content to temp file
                with open(temp_pdf_path, 'wb') as f:
                    f.write(pdf_content)
                
                # Convert PDF to image using pdf2image
                logger.info(f"Converting PDF to image for slide {slide_number}")
                images = convert_from_path(
                    temp_pdf_path,
                    first_page=slide_number + 1,  # pdf2image uses 1-based indexing
                    last_page=slide_number + 1,
                    dpi=200  # High quality
                )
                
                if not images:
                    logger.error("No images generated from PDF")
                    return None
                
                # Resize and save the image
                image = images[0]
                image = image.resize(size, Image.Resampling.LANCZOS)
                image.save(output_path, 'PNG', optimize=True)
                
                logger.info(f"Generated thumbnail with Microsoft Graph: {output_path}")
                return str(output_path)
                
            finally:
                # Clean up temp PDF file
                try:
                    if Path(temp_pdf_path).exists():
                        Path(temp_pdf_path).unlink()
                except Exception:
                    pass
                    
        except Exception as e:
            logger.error(f"Microsoft Graph conversion failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _get_graph_access_token(self, user_access_token: Optional[str] = None) -> Optional[str]:
        """Get access token for Microsoft Graph API"""
        
        # If user access token is provided (from authenticated session), use it directly
        if user_access_token:
            logger.info("Using provided user access token for Graph API")
            return user_access_token
        
        # Fallback: Try to get from environment (for testing)
        user_token_env = os.environ.get('AZURE_USER_ACCESS_TOKEN')
        if user_token_env:
            logger.info("Using user access token from environment")
            return user_token_env
        
        # Final fallback: client credentials (won't work for /me endpoints)
        import requests
        
        try:
            client_id = os.environ.get('AZURE_CLIENT_ID')
            client_secret = os.environ.get('AZURE_CLIENT_SECRET')
            tenant_id = os.environ.get('AZURE_TENANT_ID', 'common')
            
            if not client_id or not client_secret:
                logger.error("Azure credentials not configured")
                return None
            
            logger.warning("Using client credentials - this won't work for user OneDrive access")
            
            # Get access token using client credentials flow
            token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
            token_data = {
                'grant_type': 'client_credentials',
                'client_id': client_id,
                'client_secret': client_secret,
                'scope': 'https://graph.microsoft.com/.default'
            }
            
            response = requests.post(token_url, data=token_data)
            response.raise_for_status()
            
            token_result = response.json()
            access_token = token_result.get('access_token')
            
            if access_token:
                logger.info("Successfully obtained Graph API access token (client credentials)")
            else:
                logger.error("No access token in response")
                
            return access_token
            
        except Exception as e:
            logger.error(f"Failed to get Graph access token: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _convert_pptx_to_pdf_via_graph(self, pptx_path: str, access_token: str) -> Optional[bytes]:
        """Convert PPTX to PDF using Microsoft Graph API"""
        import requests
        import uuid
        
        try:
            # For client credentials flow, we need to use a different approach
            # We'll use the conversion service directly rather than uploading to OneDrive
            
            # Read PPTX file
            with open(pptx_path, 'rb') as f:
                pptx_content = f.read()
            
            # Use Microsoft Graph conversion service
            # This is a direct conversion without needing OneDrive storage
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
            }
            
            # Try using the conversion API directly
            # Note: This might require different permissions or approach
            convert_url = "https://graph.microsoft.com/v1.0/me/drive/root/microsoft.graph.convertTo(format='pdf')"
            
            # First attempt: direct conversion API
            try:
                response = requests.post(convert_url, headers=headers, data=pptx_content)
                if response.status_code == 200:
                    return response.content
            except Exception as e:
                logger.warning(f"Direct conversion failed: {e}")
            
            # Fallback: Upload to temp location and convert
            temp_filename = f"temp_presentation_{uuid.uuid4().hex[:8]}.pptx"
            upload_url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{temp_filename}:/content"
            
            upload_headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/octet-stream'
            }
            
            # Upload file
            upload_response = requests.put(upload_url, headers=upload_headers, data=pptx_content)
            upload_response.raise_for_status()
            
            # Get file ID from upload response
            file_info = upload_response.json()
            file_id = file_info.get('id')
            
            if not file_id:
                logger.error("Failed to get file ID from upload")
                return None
            
            # Convert to PDF using Graph API
            convert_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/content?format=pdf"
            headers_get = {'Authorization': f'Bearer {access_token}'}
            
            convert_response = requests.get(convert_url, headers=headers_get)
            convert_response.raise_for_status()
            
            # Clean up uploaded file
            delete_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}"
            requests.delete(delete_url, headers=headers_get)
            
            return convert_response.content
            
        except Exception as e:
            logger.error(f"Graph API conversion failed: {e}")
            return None
    
    def _generate_with_spire(
        self,
        pptx_path: str,
        output_path: str,
        size: Tuple[int, int],
        slide_number: int
    ) -> Optional[str]:
        """Generate thumbnail using Spire.Presentation"""
        try:
            # Load the presentation
            presentation = SpirePresentation()
            presentation.load_from_file(pptx_path)
            
            if slide_number >= presentation.slides.count:
                logger.error(f"Slide number {slide_number} exceeds available slides ({presentation.slides.count})")
                return None
            
            # Get the specific slide
            slide = presentation.slides[slide_number]
            
            # Calculate scale based on desired size
            # Standard slide size is typically 960x720, scale accordingly
            scale_x = size[0] / 960.0
            scale_y = size[1] / 720.0
            scale = min(scale_x, scale_y)  # Maintain aspect ratio
            
            # Generate thumbnail
            thumbnail = slide.save_as_image(scale, scale)
            
            # Save as PNG
            thumbnail.save(str(output_path), ImageFormat.PNG)
            
            # Clean up
            presentation.dispose()
            thumbnail.dispose()
            
            logger.info(f"Generated thumbnail with Spire.Presentation: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Spire.Presentation conversion failed: {e}")
            import traceback
            traceback.print_exc()
        
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
        size: tuple[int, int],
        slide_number: int
    ) -> Optional[str]:
        """Generate thumbnail by first converting PPTX to PDF then to image"""
        import subprocess
        import tempfile
        from pdf2image import convert_from_path
        
        try:
            # Create temporary PDF file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
                temp_pdf_path = temp_pdf.name
            
            try:
                # Convert PPTX to PDF using LibreOffice
                cmd = [
                    'libreoffice',
                    '--headless',
                    '--convert-to', 'pdf',
                    '--outdir', str(Path(temp_pdf_path).parent),
                    pptx_path
                ]
                
                logger.info(f"Converting PPTX to PDF: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode != 0:
                    logger.error(f"LibreOffice conversion failed: {result.stderr}")
                    return None
                
                # LibreOffice creates PDF with same name as PPTX
                expected_pdf = Path(temp_pdf_path).parent / (Path(pptx_path).stem + '.pdf')
                if not expected_pdf.exists():
                    logger.error(f"Expected PDF not found: {expected_pdf}")
                    return None
                
                # Convert PDF to image using pdf2image
                logger.info(f"Converting PDF to image: {expected_pdf}")
                images = convert_from_path(
                    str(expected_pdf),
                    first_page=slide_number + 1,  # pdf2image uses 1-based indexing
                    last_page=slide_number + 1,
                    dpi=200  # High quality
                )
                
                if not images:
                    logger.error("No images generated from PDF")
                    return None
                
                # Resize and save the image
                image = images[0]
                image = image.resize(size, Image.Resampling.LANCZOS)
                image.save(output_path, 'PNG', optimize=True)
                
                logger.info(f"Generated thumbnail with PDF2Image: {output_path}")
                return str(output_path)
                
            finally:
                # Clean up temp files
                try:
                    if Path(temp_pdf_path).exists():
                        Path(temp_pdf_path).unlink()
                    expected_pdf = Path(temp_pdf_path).parent / (Path(pptx_path).stem + '.pdf')
                    if expected_pdf.exists():
                        expected_pdf.unlink()
                except Exception:
                    pass
                    
        except subprocess.TimeoutExpired:
            logger.error("LibreOffice conversion timed out")
            return None
        except Exception as e:
            logger.error(f"PDF conversion failed: {e}")
            import traceback
            traceback.print_exc()
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