"""
HTML Renderer Module

This module converts HTML content to images for insertion into PowerPoint slides.
Supports timeline generation, custom visualizations, and complex layouts with
enhanced Ekona branding and icon support.
"""

import os
import tempfile
from typing import Dict

# HTML-to-image rendering options (install one based on preference)
try:
    from playwright.sync_api import sync_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

try:
    import weasyprint

    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

try:
    import imgkit  # wkhtmltopdf wrapper

    IMGKIT_AVAILABLE = True
except ImportError:
    IMGKIT_AVAILABLE = False

# Fallback using selenium + chrome (most reliable)
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


class HTMLRenderer:
    """
    Converts HTML content to images for PowerPoint slide insertion
    with enhanced quality and Ekona branding
    """

    def __init__(self, preferred_method: str = "auto"):
        """
        Initialize HTML renderer

        Args:
            preferred_method: Rendering method
                ('playwright', 'weasyprint', 'selenium', 'auto')
        """
        self.preferred_method = preferred_method
        self.available_methods = self._check_available_methods()
        self.active_method = self._select_method()

        print(f"HTML Renderer initialized with method: {self.active_method}")

    def _check_available_methods(self) -> Dict[str, bool]:
        """Check which rendering methods are available"""
        return {
            "playwright": PLAYWRIGHT_AVAILABLE,
            "weasyprint": WEASYPRINT_AVAILABLE,
            "selenium": SELENIUM_AVAILABLE,
            "imgkit": IMGKIT_AVAILABLE,
        }

    def _select_method(self) -> str:
        """Select the best available rendering method"""
        if self.preferred_method != "auto" and self.available_methods.get(
            self.preferred_method
        ):
            return self.preferred_method

        # Priority order: playwright > selenium > weasyprint > imgkit
        for method in ["playwright", "selenium", "weasyprint", "imgkit"]:
            if self.available_methods.get(method):
                return method

        raise RuntimeError(
            "No HTML rendering method available. "
            "Please install playwright, selenium, weasyprint, or imgkit."
        )

    def render_html_to_image(
        self,
        html_content: str,
        output_path: str,
        width: int = 3154,  # 2x resolution for crisp images (1577*2)
        height: int = 1206,  # 2x resolution for crisp images (603*2)
        **kwargs,
    ) -> bool:
        """
        Render HTML content to an image file with high quality settings

        Args:
            html_content: HTML content string to render
            output_path: Path where the image should be saved
            width: Image width in pixels (default: 3154 for 2x crisp rendering)
            height: Image height in pixels (default: 1206 for 2x crisp rendering)
            **kwargs: Additional rendering options

        Returns:
            True if rendering was successful, False otherwise
        """
        try:
            # Try rendering with the active method
            if self.active_method == "playwright":
                return self._render_with_playwright(
                    html_content, output_path, width, height, **kwargs
                )
            if self.active_method == "selenium":
                return self._render_with_selenium(
                    html_content, output_path, width, height, **kwargs
                )
            if self.active_method == "weasyprint":
                return self._render_with_weasyprint(
                    html_content, output_path, width, height, **kwargs
                )
            if self.active_method == "imgkit":
                return self._render_with_imgkit(
                    html_content, output_path, width, height, **kwargs
                )

        except Exception as e:
            print(f"❌ Error rendering HTML with {self.active_method}: {e}")

        return False

    def _render_with_playwright(
        self, html_content: str, output_path: str, width: int, height: int, **kwargs
    ) -> bool:
        """Render using Playwright for highest quality"""
        try:
            with sync_playwright() as p:
                # Launch browser with high DPI settings
                browser = p.chromium.launch(
                    args=[
                        "--force-device-scale-factor=2",  # High DPI
                        "--disable-web-security",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                    ]
                )

                page = browser.new_page(
                    viewport={
                        "width": width // 2,
                        "height": height // 2,
                    },  # Actual viewport
                    device_scale_factor=2,  # High DPI rendering
                )

                # Set content and wait for rendering
                page.set_content(html_content, wait_until="networkidle")

                # Take screenshot with high quality settings
                page.screenshot(
                    path=output_path,
                    type="png",
                    full_page=False,
                    clip={"x": 0, "y": 0, "width": width // 2, "height": height // 2},
                )

                browser.close()
                return os.path.exists(output_path)

        except Exception as e:
            print(f"Playwright rendering error: {e}")
            return False

    def _render_with_selenium(
        self, html_content: str, output_path: str, width: int, height: int, **kwargs
    ) -> bool:
        """Render using Selenium with Chrome for reliability"""
        try:
            # Chrome options for high quality rendering
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument(f"--window-size={width//2},{height//2}")
            chrome_options.add_argument("--force-device-scale-factor=2")  # High DPI
            chrome_options.add_argument("--high-dpi-support=1")
            chrome_options.add_argument("--device-scale-factor=2")

            # Create temporary HTML file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".html", delete=False
            ) as f:
                f.write(html_content)
                temp_html_path = f.name

            try:
                # Initialize Chrome driver
                driver = webdriver.Chrome(options=chrome_options)
                driver.set_window_size(width // 2, height // 2)

                # Load HTML file
                driver.get(f"file://{temp_html_path}")

                # Wait for page to load completely
                driver.implicitly_wait(2)

                # Take screenshot
                driver.save_screenshot(output_path)
                driver.quit()

                return os.path.exists(output_path)

            finally:
                # Clean up temporary file
                if os.path.exists(temp_html_path):
                    os.unlink(temp_html_path)

        except Exception as e:
            print(f"Selenium rendering error: {e}")
            return False

    def _render_with_weasyprint(
        self, html_content: str, output_path: str, width: int, height: int, **kwargs
    ) -> bool:
        """Render using WeasyPrint (CSS to PNG)"""
        try:
            # WeasyPrint needs CSS dimensions
            css_content = f"""
            @page {{
                size: {width}px {height}px;
                margin: 0;
            }}
            body {{
                margin: 0;
                padding: 20px;
                width: {width-40}px;
                height: {height-40}px;
                overflow: hidden;
            }}
            """

            # Add CSS to HTML
            html_with_css = f"""
            <html>
            <head>
                <style>{css_content}</style>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """

            # Create document and render to PNG
            html_doc = weasyprint.HTML(string=html_with_css)

            # Render to PNG with high resolution
            html_doc.write_png(target=output_path, resolution=width // 8)  # High DPI

            return os.path.exists(output_path)

        except Exception as e:
            print(f"WeasyPrint rendering error: {e}")
            return False

    def _render_with_imgkit(
        self, html_content: str, output_path: str, width: int, height: int, **kwargs
    ) -> bool:
        """Render using imgkit (wkhtmltopdf wrapper)"""
        options = {
            "width": width,
            "height": height,
            "format": "png",
            "quality": 100,
            # High DPI settings
            "enable-smart-shrinking": "",
            "zoom": 2.0,  # 2x zoom for crisp images
        }

        try:
            imgkit.from_string(html_content, output_path, options=options)
            return os.path.exists(output_path)
        except Exception as e:
            print(f"imgkit rendering error: {e}")
            return False

    def create_timeline_html(
        self, events: list, title: str = "Timeline", theme: str = "ekona"
    ) -> str:
        """
        Generate HTML for a timeline visualization optimized for 1577x603 space

        Args:
            events: List of event dictionaries with 'date', 'title', 'description'
            title: Timeline title
            theme: Color theme ('ekona', 'modern', 'minimal')

        Returns:
            HTML string for the timeline optimized for PowerPoint slide space
        """
        # Ekona brand colors optimized for space
        if theme == "ekona":
            primary_color = "#dc261e"  # Ekona red
            secondary_color = "#404040"  # Ekona dark grey
            background_color = "#ffffff"  # Pure white
            text_color = "#2d3748"  # Dark text for readability
            accent_color = "#f7fafc"  # Very light accent
            gradient_bg = "linear-gradient(135deg, #ffffff 0%, #f8fafc 100%)"
        elif theme == "modern":
            primary_color = "#2563eb"
            secondary_color = "#64748b"
            background_color = "#ffffff"
            text_color = "#1e293b"
            accent_color = "#f8fafc"
            gradient_bg = "linear-gradient(135deg, #ffffff 0%, #f8fafc 100%)"
        else:  # minimal
            primary_color = "#000000"
            secondary_color = "#333333"
            background_color = "#ffffff"
            text_color = "#333333"
            accent_color = "#f9f9f9"
            gradient_bg = "#ffffff"

        # Generate calendar/clock SVG icon
        calendar_icon = f"""
        <svg class="timeline-icon" viewBox="0 0 24 24" fill="none" stroke="{primary_color}" stroke-width="2">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
            <line x1="16" y1="2" x2="16" y2="6"></line>
            <line x1="8" y1="2" x2="8" y2="6"></line>
            <line x1="3" y1="10" x2="21" y2="10"></line>
        </svg>
        """

        # Generate horizontal timeline events HTML for space optimization
        events_html = ""
        for i, event in enumerate(events):
            # Add connecting line for all but last event
            connector = (
                "" if i == len(events) - 1 else '<div class="timeline-connector"></div>'
            )

            events_html += f"""
            <div class="timeline-item">
                <div class="timeline-content">
                    <div class="timeline-marker">
                        {calendar_icon}
                    </div>
                    <div class="event-details">
                        <div class="date">{event.get('date', '')}</div>
                        <h3>{event.get('title', '')}</h3>
                        <p>{event.get('description', '')}</p>
                    </div>
                </div>
                {connector}
            </div>
            """

        html_template = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            <style>
                html, body {{
                    margin: 0;
                    padding: 0;
                    width: 1577px;
                    height: 603px;
                    overflow: hidden;
                    font-family: 'Segoe UI', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
                    background: {gradient_bg};
                    color: {text_color};
                    box-sizing: border-box;
                }}
                
                .timeline-container {{
                    width: 100%;
                    height: 100%;
                    display: flex;
                    flex-direction: column;
                    padding: 25px 40px;
                    box-sizing: border-box;
                }}
                
                .timeline-title {{
                    text-align: center;
                    font-size: 36px;
                    font-weight: 700;
                    margin: 0 0 30px 0;
                    color: {primary_color};
                    line-height: 1.2;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }}
                
                .timeline {{
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    flex: 1;
                    position: relative;
                    padding: 0 20px;
                }}
                
                .timeline::before {{
                    content: '';
                    position: absolute;
                    left: 20px;
                    right: 20px;
                    top: 50%;
                    height: 4px;
                    background: linear-gradient(90deg, {primary_color} 0%, {secondary_color} 50%, {primary_color} 100%);
                    border-radius: 2px;
                    z-index: 1;
                }}
                
                .timeline-item {{
                    position: relative;
                    flex: 1;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    z-index: 3;
                    max-width: calc(100% / {len(events) if events else 1});
                }}
                
                .timeline-content {{
                    background: {background_color};
                    border-radius: 16px;
                    padding: 25px 20px;
                    box-shadow: 0 8px 25px rgba(220, 38, 30, 0.15);
                    border: 2px solid {accent_color};
                    border-top: 6px solid {primary_color};
                    text-align: center;
                    width: 100%;
                    box-sizing: border-box;
                    min-height: 220px;
                    display: flex;
                    flex-direction: column;
                    justify-content: space-between;
                    position: relative;
                    transform: translateY(-20px);
                }}
                
                .timeline-marker {{
                    width: 60px;
                    height: 60px;
                    background: {primary_color};
                    border: 6px solid {background_color};
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    box-shadow: 0 4px 12px rgba(220, 38, 30, 0.3);
                    position: absolute;
                    bottom: -50px;
                    left: 50%;
                    transform: translateX(-50%);
                    z-index: 4;
                }}
                
                .timeline-icon {{
                    width: 28px;
                    height: 28px;
                    stroke: {background_color};
                    stroke-width: 2.5;
                }}
                
                .date {{
                    font-size: 16px;
                    color: {primary_color};
                    font-weight: 700;
                    margin-bottom: 12px;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }}
                
                .event-details h3 {{
                    margin: 0 0 15px 0;
                    font-size: 20px;
                    color: {secondary_color};
                    font-weight: 600;
                    line-height: 1.3;
                    min-height: 50px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }}
                
                .event-details p {{
                    margin: 0;
                    font-size: 15px;
                    color: {text_color};
                    line-height: 1.5;
                    text-align: center;
                    opacity: 0.85;
                }}
                
                .timeline-connector {{
                    position: absolute;
                    right: -15px;
                    top: 50%;
                    transform: translateY(-50%);
                    width: 30px;
                    height: 6px;
                    background: linear-gradient(90deg, transparent 0%, {primary_color} 50%, transparent 100%);
                    z-index: 2;
                }}
            </style>
        </head>
        <body>
            <div class="timeline-container">
                <div class="timeline-title">{title}</div>
                <div class="timeline">
                    {events_html}
                </div>
            </div>
        </body>
        </html>
        """

        return html_template

    def create_process_flow_html(
        self, steps: list, title: str = "Process Flow", theme: str = "ekona"
    ) -> str:
        """
        Generate HTML for a process flow visualization optimized for 1577x603 space

        Args:
            steps: List of step dictionaries with 'title', 'description', 'icon'
            title: Flow title
            theme: Color theme

        Returns:
            HTML string for the process flow optimized for PowerPoint slide space
        """
        if theme == "ekona":
            primary_color = "#dc261e"
            secondary_color = "#404040"
            background_color = "#ffffff"
            text_color = "#2d3748"
            accent_color = "#f7fafc"
            gradient_bg = "linear-gradient(135deg, #ffffff 0%, #f8fafc 100%)"
        else:
            primary_color = "#2563eb"
            secondary_color = "#64748b"
            background_color = "#ffffff"
            text_color = "#1e293b"
            accent_color = "#f8fafc"
            gradient_bg = "linear-gradient(135deg, #ffffff 0%, #f8fafc 100%)"

        # Calculate optimal grid layout based on number of steps
        num_steps = len(steps) if steps else 1
        if num_steps <= 3:
            columns = num_steps
            rows = 1
        elif num_steps <= 6:
            columns = 3
            rows = 2
        elif num_steps <= 8:
            columns = 4
            rows = 2
        else:
            columns = 4
            rows = 3

        # Generate step icons (customizable SVG)
        def get_step_icon(step_num):
            return f"""
            <svg class="step-icon" viewBox="0 0 24 24" fill="none" stroke="{background_color}" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <polyline points="12,6 12,12 16,14"></polyline>
            </svg>
            """

        steps_html = ""
        for i, step in enumerate(steps):
            # Add arrow connector for all but last step
            arrow = (
                ""
                if i == len(steps) - 1
                else f"""
            <div class="step-arrow">
                <svg viewBox="0 0 24 24" fill="none" stroke="{primary_color}" stroke-width="3">
                    <line x1="5" y1="12" x2="19" y2="12"></line>
                    <polyline points="12,5 19,12 12,19"></polyline>
                </svg>
            </div>
            """
            )

            steps_html += f"""
            <div class="process-step">
                <div class="step-header">
                    <div class="step-number">
                        <span>{i + 1}</span>
                        {get_step_icon(i + 1)}
                    </div>
                    <h3>{step.get('title', f'Step {i + 1}')}</h3>
                </div>
                <div class="step-content">
                    <p>{step.get('description', '')}</p>
                </div>
                {arrow}
            </div>
            """

        html_template = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            <style>
                html, body {{
                    margin: 0;
                    padding: 0;
                    width: 1577px;
                    height: 603px;
                    overflow: hidden;
                    font-family: 'Segoe UI', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
                    background: {gradient_bg};
                    color: {text_color};
                    box-sizing: border-box;
                }}
                
                .process-container {{
                    width: 100%;
                    height: 100%;
                    display: flex;
                    flex-direction: column;
                    padding: 25px 40px;
                    box-sizing: border-box;
                }}
                
                .process-title {{
                    text-align: center;
                    font-size: 36px;
                    font-weight: 700;
                    margin: 0 0 35px 0;
                    color: {primary_color};
                    line-height: 1.2;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }}
                
                .process-flow {{
                    display: grid;
                    grid-template-columns: repeat({columns}, 1fr);
                    grid-template-rows: repeat({rows}, 1fr);
                    gap: 25px;
                    flex: 1;
                    align-items: center;
                }}
                
                .process-step {{
                    background: {background_color};
                    border-radius: 20px;
                    padding: 30px 25px;
                    box-shadow: 0 10px 30px rgba(220, 38, 30, 0.15);
                    border: 2px solid {accent_color};
                    border-top: 6px solid {primary_color};
                    text-align: center;
                    display: flex;
                    flex-direction: column;
                    justify-content: space-between;
                    align-items: center;
                    position: relative;
                    transition: transform 0.3s ease, box-shadow 0.3s ease;
                    min-height: 180px;
                }}
                
                .step-header {{
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    margin-bottom: 20px;
                }}
                
                .step-number {{
                    width: 70px;
                    height: 70px;
                    background: {primary_color};
                    color: {background_color};
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 24px;
                    font-weight: 700;
                    margin-bottom: 15px;
                    box-shadow: 0 6px 20px rgba(220, 38, 30, 0.3);
                    position: relative;
                }}
                
                .step-number span {{
                    position: absolute;
                    z-index: 2;
                }}
                
                .step-icon {{
                    width: 35px;
                    height: 35px;
                    opacity: 0.2;
                    position: absolute;
                }}
                
                .step-header h3 {{
                    margin: 0;
                    color: {secondary_color};
                    font-size: 20px;
                    font-weight: 600;
                    line-height: 1.3;
                    text-align: center;
                    min-height: 45px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }}
                
                .step-content p {{
                    margin: 0;
                    color: {text_color};
                    font-size: 15px;
                    line-height: 1.5;
                    text-align: center;
                    opacity: 0.85;
                }}
                
                .step-arrow {{
                    position: absolute;
                    right: -35px;
                    top: 50%;
                    transform: translateY(-50%);
                    width: 30px;
                    height: 30px;
                    z-index: 10;
                }}
                
                .step-arrow svg {{
                    width: 100%;
                    height: 100%;
                }}
            </style>
        </head>
        <body>
            <div class="process-container">
                <div class="process-title">{title}</div>
                <div class="process-flow">
                    {steps_html}
                </div>
            </div>
        </body>
        </html>
        """

        return html_template
