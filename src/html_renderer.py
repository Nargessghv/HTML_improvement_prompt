"""
HTML Renderer Module

This module converts HTML content to images for insertion into PowerPoint slides.
Supports timeline generation, custom visualizations, and complex layouts with
enhanced Ekona branding and icon support.
"""

import asyncio
import os
import tempfile
from typing import Dict

# HTML-to-image rendering options (install one based on preference)
try:
    from playwright.async_api import async_playwright
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
    with enhanced quality, Ekona branding, and Lucide icon support
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
        self.lucide_sprite_content = self._load_lucide_sprite()

        print(f"HTML Renderer initialized with method: {self.active_method}")
        if self.lucide_sprite_content:
            print("✅ Lucide icon sprite loaded successfully")
        else:
            print("⚠️ Lucide icon sprite not found - icons may not display")

    def _is_async_context(self) -> bool:
        """
        Check if we're running in an async context

        Returns:
            True if running in async context, False otherwise
        """
        try:
            loop = asyncio.get_running_loop()
            return True
        except RuntimeError:
            return False

    def _prepare_html_for_rendering(self, html_content: str) -> str:
        """
        Prepare HTML for rendering by injecting Lucide sprite and Mermaid.js

        Args:
            html_content: Original HTML content

        Returns:
            HTML content ready for rendering
        """
        # Check if HTML contains Lucide icon references but no sprite definitions
        has_icon_references = '<use href="#' in html_content
        has_sprite_definitions = "<symbol id=" in html_content

        # 1. Inject Lucide icon sprite if needed
        if (
            has_icon_references
            and not has_sprite_definitions
            and self.lucide_sprite_content
        ):
            print("🎯 Lucide icon references found, injecting sprite definitions...")
            body_start = html_content.find("<body")
            if body_start != -1:
                body_tag_end = html_content.find(">", body_start) + 1
                sprite_container = f"""
    <!-- Lucide Icons Sprite -->
    <svg width="0" height="0" style="position: absolute; visibility: hidden;">
        {self.lucide_sprite_content}
    </svg>
"""
                html_content = (
                    html_content[:body_tag_end]
                    + sprite_container
                    + html_content[body_tag_end:]
                )
                print("✅ Lucide sprite definitions injected successfully")
        elif has_sprite_definitions:
            print("✅ HTML already contains SVG sprite definitions, skipping injection")
        elif not has_icon_references:
            print("📝 No Lucide icon references found in HTML")
        elif not self.lucide_sprite_content:
            print("⚠️ Lucide sprite content not loaded - icons may not display")

        # 2. Check for and inject Mermaid.js if needed
        if '<div class="mermaid">' in html_content:
            print("🧜‍♀️ Mermaid diagram detected, injecting script...")
            head_end = html_content.find("</head>")
            if head_end != -1:
                mermaid_script = """
    <!-- Mermaid.js for diagrams -->
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <script>
      mermaid.initialize({
        startOnLoad: true,
        theme: 'base',
        themeVariables: {
          'primaryColor': '#ffffff',
          'primaryTextColor': '#000000',
          'primaryBorderColor': '#2d3748',
          'lineColor': '#2d3748',
          'secondaryColor': '#f3f4f6',
          'tertiaryColor': '#ffffff',
          'fontFamily': '"Segoe UI", system-ui, sans-serif',
          'fontSize': '16px',

          'gitGraph:': {
            'mainBranchName': 'main',
            'mainBranchOrder': 0
          },

          'pieBkgColor': '#ffffff',
          'pieBorderColor': '#2d3748',
          'pieTextColor': '#000000',

          'actorBkgColor': '#ffffff',
          'actorBorderColor': '#dc261e',
          'actorTextColor': '#000000',

          'taskBkgColor': '#ffffff',
          'taskBorderColor': '#dc261e',
          'taskTextColor': '#000000',
          
          'nodeBorder': '#2d3748',

          'messageTextColor': '#000000',
          'messageLineColor': '#2d3748',
        }
      });
    </script>
"""
                html_content = (
                    html_content[:head_end] + mermaid_script + html_content[head_end:]
                )

        # 3. Check for and inject D3.js if needed
        if "d3.select" in html_content or '<div id="d3-container">' in html_content:
            print("📊 D3.js visualization detected, injecting script...")
            head_end = html_content.find("</head>")
            if head_end != -1:
                d3_script = """
    <!-- D3.js for advanced visualizations -->
    <script src="https://d3js.org/d3.v7.min.js"></script>
"""
                html_content = (
                    html_content[:head_end] + d3_script + html_content[head_end:]
                )

        return html_content

    def _load_lucide_sprite(self) -> str:
        """Load the Lucide sprite SVG content for icon support"""
        sprite_path = os.path.join(os.path.dirname(__file__), "lucide-sprite.svg")
        try:
            with open(sprite_path, encoding="utf-8") as f:
                content = f.read()
                # Extract just the symbol definitions from the sprite
                # Find the <defs> section and extract symbols
                start_marker = "<defs>"
                end_marker = "</defs>"

                start_idx = content.find(start_marker)
                end_idx = content.find(end_marker)

                if start_idx != -1 and end_idx != -1:
                    # Extract the content between <defs> and </defs>
                    defs_content = content[start_idx + len(start_marker) : end_idx]
                    return defs_content.strip()

                print("Warning: Could not find <defs> section in Lucide sprite")
                return ""
        except (OSError, FileNotFoundError) as e:
            print(f"Warning: Could not load Lucide sprite: {e}")
            return ""

    def _inject_lucide_sprite(self, html_content: str) -> str:
        """
        Inject Lucide sprite definitions into HTML content for icon support

        Args:
            html_content: Original HTML content

        Returns:
            HTML content with embedded Lucide sprite definitions
        """
        # This method is now part of _prepare_html_for_rendering
        # but kept for compatibility or direct use if needed.
        return self._prepare_html_for_rendering(html_content)

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
        width: int,
        height: int,
        **kwargs,
    ) -> bool:
        """
        Render HTML content to an image file with high quality settings
        Automatically detects async context and uses appropriate method

        Args:
            html_content: HTML content string to render
            output_path: Path where the image should be saved
            width: Image width in pixels (should match placeholder width * 2 for crisp rendering)
            height: Image height in pixels (should match placeholder height * 2 for crisp rendering)
            **kwargs: Additional rendering options

        Returns:
            True if rendering was successful, False otherwise
        """
        try:
            # Prepare HTML by injecting necessary scripts and sprites
            prepared_html = self._prepare_html_for_rendering(html_content)

            # Check if we're in an async context
            if self._is_async_context():
                print("🔄 Async context detected, using async-compatible rendering...")
                # In async context, use async Playwright renderer
                if self.active_method == "playwright":
                    print("  - Using async Playwright renderer...")
                    import asyncio
                    try:
                        # Try to run in existing event loop
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # Create a new event loop in a thread for async operations
                            import concurrent.futures
                            import threading
                            
                            def run_async():
                                new_loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(new_loop)
                                try:
                                    return new_loop.run_until_complete(
                                        self._render_with_playwright_async(
                                            prepared_html, output_path, width, height, **kwargs
                                        )
                                    )
                                finally:
                                    new_loop.close()
                            
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(run_async)
                                return future.result()
                        else:
                            return asyncio.run(self._render_with_playwright_async(
                                prepared_html, output_path, width, height, **kwargs
                            ))
                    except Exception as e:
                        print(f"  - Async Playwright failed with error: {type(e).__name__}: {e}")
                        import traceback
                        print(f"  - Stack trace: {traceback.format_exc()}")
                        print(f"  - Falling back to enhanced Selenium renderer...")
                        return self._render_with_selenium(
                            prepared_html, output_path, width, height, **kwargs
                        )
                # For other methods, proceed normally as they're sync-safe
                if self.active_method == "selenium":
                    return self._render_with_selenium(
                        prepared_html, output_path, width, height, **kwargs
                    )
                if self.active_method == "weasyprint":
                    return self._render_with_weasyprint(
                        prepared_html, output_path, width, height, **kwargs
                    )
                if self.active_method == "imgkit":
                    return self._render_with_imgkit(
                        prepared_html, output_path, width, height, **kwargs
                    )
            # Not in async context, use normal methods
            elif self.active_method == "playwright":
                return self._render_with_playwright(
                    prepared_html, output_path, width, height, **kwargs
                )
            elif self.active_method == "selenium":
                return self._render_with_selenium(
                    prepared_html, output_path, width, height, **kwargs
                )
            elif self.active_method == "weasyprint":
                return self._render_with_weasyprint(
                    prepared_html, output_path, width, height, **kwargs
                )
            elif self.active_method == "imgkit":
                return self._render_with_imgkit(
                    prepared_html, output_path, width, height, **kwargs
                )

        except Exception as e:
            print(f"❌ Error rendering HTML with {self.active_method}: {e}")
            print("  - Attempting to render HTML with selenium...")
            # Fallback to selenium which is most reliable
            try:
                return self._render_with_selenium(
                    prepared_html, output_path, width, height, **kwargs
                )
            except Exception as selenium_e:
                print(f"❌ Selenium fallback also failed: {selenium_e}")

        return False

    async def render_html_to_image_async(
        self,
        html_content: str,
        output_path: str,
        width: int,
        height: int,
        **kwargs,
    ) -> bool:
        """
        Async version of render_html_to_image for use in async contexts

        Args:
            html_content: HTML content string to render
            output_path: Path where the image should be saved
            width: Image width in pixels (should match placeholder width * 2 for crisp rendering)
            height: Image height in pixels (should match placeholder height * 2 for crisp rendering)
            **kwargs: Additional rendering options

        Returns:
            True if rendering was successful, False otherwise
        """
        try:
            # Prepare HTML by injecting necessary scripts and sprites
            prepared_html = self._prepare_html_for_rendering(html_content)

            # Try async Playwright first, then fallback to sync methods
            if self.active_method == "playwright" and PLAYWRIGHT_AVAILABLE:
                return await self._render_with_playwright_async(
                    prepared_html, output_path, width, height, **kwargs
                )
            # Run sync methods in executor to avoid blocking
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                if self.active_method == "selenium":
                    future = executor.submit(
                        self._render_with_selenium,
                        prepared_html,
                        output_path,
                        width,
                        height,
                        **kwargs,
                    )
                elif self.active_method == "weasyprint":
                    future = executor.submit(
                        self._render_with_weasyprint,
                        prepared_html,
                        output_path,
                        width,
                        height,
                        **kwargs,
                    )
                elif self.active_method == "imgkit":
                    future = executor.submit(
                        self._render_with_imgkit,
                        prepared_html,
                        output_path,
                        width,
                        height,
                        **kwargs,
                    )
                else:
                    # Default to selenium
                    future = executor.submit(
                        self._render_with_selenium,
                        prepared_html,
                        output_path,
                        width,
                        height,
                        **kwargs,
                    )

                return await asyncio.wrap_future(future)

        except Exception as e:
            print(f"❌ Error in async HTML rendering: {e}")
            # Fallback to selenium in executor
            try:
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        self._render_with_selenium,
                        prepared_html,
                        output_path,
                        width,
                        height,
                        **kwargs,
                    )
                    return await asyncio.wrap_future(future)
            except Exception as selenium_e:
                print(f"❌ Async selenium fallback also failed: {selenium_e}")

        return False

    def _render_with_playwright(
        self, html_content: str, output_path: str, width: int, height: int, **kwargs
    ) -> bool:
        """Render using Playwright for highest quality with transparent background support"""
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

                # Check actual content dimensions to prevent cropping
                content_width = page.evaluate("document.body.scrollWidth")
                content_height = page.evaluate("document.body.scrollHeight")
                
                viewport_width = width // 2
                viewport_height = height // 2
                
                if content_height > viewport_height or content_width > viewport_width:
                    print(f"  - Content ({content_width}x{content_height}px) > Viewport ({viewport_width}x{viewport_height}px)")
                    print(f"  - Using full page screenshot to prevent cropping")
                    
                    # Use full page screenshot when content exceeds viewport
                    page.screenshot(
                        path=output_path,
                        type="png",
                        full_page=True,
                        omit_background=True,  # Enable transparency
                    )
                else:
                    print(f"  - Content fits in viewport, using clipped screenshot")
                    
                    # Use clipped screenshot when content fits
                    page.screenshot(
                        path=output_path,
                        type="png",
                        full_page=False,
                        clip={"x": 0, "y": 0, "width": viewport_width, "height": viewport_height},
                        omit_background=True,  # Enable transparency
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
                
                # Check actual content dimensions to prevent cropping
                content_width = driver.execute_script("return document.body.scrollWidth")
                content_height = driver.execute_script("return document.body.scrollHeight")
                
                viewport_width = width // 2
                viewport_height = height // 2
                
                if content_height > viewport_height or content_width > viewport_width:
                    print(f"  - Content ({content_width}x{content_height}px) > Viewport ({viewport_width}x{viewport_height}px)")
                    print(f"  - Resizing browser window to fit full content")
                    
                    # Resize window to accommodate full content
                    new_width = max(content_width, viewport_width)
                    new_height = max(content_height, viewport_height)
                    driver.set_window_size(new_width, new_height)
                    
                    # Wait a moment for resize
                    driver.implicitly_wait(1)
                    
                    print(f"  - Resized to: {new_width}x{new_height}px")
                else:
                    print(f"  - Content fits in viewport, using standard screenshot")

                # Take screenshot (full page to capture all content)
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
            html_doc.write_png(  # type: ignore
                target=output_path, resolution=width // 8
            )  # High DPI

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

    async def _render_with_playwright_async(
        self, html_content: str, output_path: str, width: int, height: int, **kwargs
    ) -> bool:
        """Async version of Playwright rendering with transparent background support"""
        try:
            async with async_playwright() as p:
                # Launch browser with high DPI settings
                browser = await p.chromium.launch(
                    args=[
                        "--force-device-scale-factor=2",  # High DPI
                        "--disable-web-security",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                    ]
                )

                page = await browser.new_page(
                    viewport={
                        "width": width // 2,
                        "height": height // 2,
                    },  # Actual viewport
                    device_scale_factor=2,  # High DPI rendering
                )

                # Set content and wait for rendering
                await page.set_content(html_content, wait_until="networkidle")

                # Check actual content dimensions to prevent cropping
                content_width = await page.evaluate("document.body.scrollWidth")
                content_height = await page.evaluate("document.body.scrollHeight")
                
                viewport_width = width // 2
                viewport_height = height // 2
                
                if content_height > viewport_height or content_width > viewport_width:
                    print(f"  - Content ({content_width}x{content_height}px) > Viewport ({viewport_width}x{viewport_height}px)")
                    print(f"  - Using full page screenshot to prevent cropping")
                    
                    # Use full page screenshot when content exceeds viewport
                    await page.screenshot(
                        path=output_path,
                        type="png",
                        full_page=True,
                        omit_background=True,  # Enable transparency
                    )
                else:
                    print(f"  - Content fits in viewport, using clipped screenshot")
                    
                    # Use clipped screenshot when content fits
                    await page.screenshot(
                        path=output_path,
                        type="png",
                        full_page=False,
                        clip={"x": 0, "y": 0, "width": viewport_width, "height": viewport_height},
                        omit_background=True,  # Enable transparency
                    )

                await browser.close()
                return os.path.exists(output_path)

        except Exception as e:
            print(f"Async Playwright rendering error: {e}")
            return False
