"""
Image Generation Webhook Client

Handles communication with the image generation webhook API using GPT-image-1.
Supports image generation and refinement with proper error handling.
"""

import asyncio
import base64
import json
import os
from pathlib import Path
from typing import Optional

import aiohttp

from .monitoring import slide_monitor


class ImageGenerationError(Exception):
    """Exception raised when image generation fails"""


class ImageWebhookClient:
    """
    Client for communicating with the image generation webhook API

    Handles image generation requests using GPT-image-1 model with support for:
    - Different aspect ratios (16:9, 4:3)
    - Quality settings (high, medium, low)
    - Parallel generation
    - Error handling and retries
    """

    def __init__(self):
        self.webhook_url = os.getenv("IMAGE_GENERATION_WEBHOOK")
        self.image_model = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
        self.timeout = 120  # 2 minutes timeout for image generation (n8n takes ~1 min)
        self.max_retries = 3
        self.http_success = 200

        if not self.webhook_url:
            msg = "IMAGE_GENERATION_WEBHOOK environment variable is required"
            raise ValueError(msg)

    def _get_image_size_from_aspect_ratio(
        self, aspect_ratio: str, placeholder_width: int, placeholder_height: int
    ) -> str:
        """
        Determine optimal image size based on aspect ratio and placeholder dimensions

        Args:
            aspect_ratio: Target aspect ratio ("16:9", "4:3", etc.)
            placeholder_width: Width of PowerPoint placeholder in pixels
            placeholder_height: Height of PowerPoint placeholder in pixels

        Returns:
            Image size string (e.g., "1536x1024", "1024x1536")
        """
        # Map aspect ratios to optimal sizes for GPT-image-1
        if aspect_ratio == "16:9":
            # Landscape orientation
            return "1536x1024" if placeholder_width >= placeholder_height else "1024x1536"
        if aspect_ratio == "4:3":
            # Traditional presentation ratio
            return "1024x1024"  # Square works well for 4:3
        # Default to square for unknown ratios
        return "1024x1024"

    def _extract_aspect_ratio_from_description(self, description: str) -> str:
        """
        Extract aspect ratio from placeholder description

        Args:
            description: Placeholder description (e.g., "Picture 16:9")

        Returns:
            Aspect ratio string ("16:9", "4:3", or "auto")
        """
        description_lower = description.lower()
        if "16:9" in description_lower:
            return "16:9"
        if "4:3" in description_lower:
            return "4:3"
        return "auto"

    async def generate_image(
        self,
        prompt: str,
        placeholder_description: str = "",
        placeholder_width: int = 1200,
        placeholder_height: int = 456,
        quality: str = "high",
    ) -> Optional[bytes]:
        """
        Generate a single image using the webhook API

        Args:
            prompt: Text description of the desired image
            placeholder_description: Description of the placeholder (for aspect ratio detection)
            placeholder_width: Width of the placeholder in pixels
            placeholder_height: Height of the placeholder in pixels
            quality: Image quality ("high", "medium", "low")

        Returns:
            Image data as bytes, or None if generation failed
        """
        try:
            # Determine optimal image size
            aspect_ratio = self._extract_aspect_ratio_from_description(placeholder_description)
            image_size = self._get_image_size_from_aspect_ratio(
                aspect_ratio, placeholder_width, placeholder_height
            )

            # Prepare webhook payload according to GPT-image-1 API spec
            output_format = "png"  # Using PNG for PowerPoint compatibility
            
            # Clean and escape the prompt to prevent JSON issues
            cleaned_prompt = prompt.replace('\n', ' ').replace('\r', ' ').replace('"', '\\"').strip()
            
            payload = {
                "prompt": cleaned_prompt,
                "model": self.image_model,
                "size": image_size,
                "quality": quality,
                "n": 1,
                "output_format": output_format,
                "background": "auto",  # Must be one of: "transparent", "opaque", "auto"
                "moderation": "auto",  # Must be one of: "low", "auto"
                "stream": False,  # Generate in non-streaming mode
            }
            
            # Only add output_compression for webp/jpeg formats
            if output_format in ["webp", "jpeg"]:
                payload["output_compression"] = 90

            print(f"🎨 Generating image with size {image_size} for prompt: {prompt[:100]}...")
            
            # Debug: Log the payload being sent (excluding the full prompt for brevity)
            debug_payload = payload.copy()
            debug_payload["prompt"] = debug_payload["prompt"][:100] + "..." if len(debug_payload["prompt"]) > 100 else debug_payload["prompt"]
            print(f"🔍 Payload being sent: {json.dumps(debug_payload, indent=2)}")

            # Make webhook request with timeout
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession() as session, session.post(
                self.webhook_url, json=payload, timeout=timeout  # Send payload directly, not as array
            ) as response:

                if response.status != self.http_success:
                    error_text = await response.text()
                    msg = f"Webhook returned {response.status}: {error_text}"
                    raise ImageGenerationError(msg)

                # First read the raw response data once
                raw_data = await response.read()
                content_type = response.headers.get('content-type', '').lower()
                
                print(f"📄 Response content-type: {content_type}")
                print(f"📄 Response size: {len(raw_data)} bytes")
                
                # Priority 1: Check if response is binary PNG data (n8n returns this directly)
                if raw_data.startswith(b'\x89PNG'):
                    print("🎨 Response is direct PNG data from n8n webhook")
                    if len(raw_data) > 10000:  # Generated images should be at least 10KB
                        return raw_data
                    else:
                        raise ImageGenerationError(f"PNG data too small to be valid: {len(raw_data)} bytes")
                
                # Priority 2: Check content-type for image data
                if 'image/' in content_type and len(raw_data) > 10000:
                    print("🎨 Response is direct image data (via content-type)")
                    return raw_data
                
                # Priority 3: Check if it's a large binary response that might be image data
                if len(raw_data) > 50000:  # Large response likely to be image data
                    # Check for common image file signatures
                    if (raw_data.startswith(b'\xff\xd8\xff') or  # JPEG
                        raw_data.startswith(b'\x89PNG') or        # PNG  
                        raw_data.startswith(b'RIFF') and b'WEBP' in raw_data[:12]):  # WebP
                        print(f"🎨 Found large binary image data: {len(raw_data)} bytes")
                        return raw_data
                
                # Try to parse as JSON
                try:
                    result = json.loads(raw_data.decode('utf-8'))
                    print(f"📄 JSON response type: {type(result)}")
                    
                    # Handle null response
                    if result is None:
                        print("⚠️ Webhook returned null response")
                        raise ImageGenerationError("Webhook returned null response")
                    
                    # Extract base64 image from response (gpt-image-1 always returns base64)
                    if isinstance(result, list) and len(result) > 0:
                        image_data = result[0]
                        if "b64_json" in image_data:
                            print(f"✅ Found b64_json in list response, decoding...")
                            return base64.b64decode(image_data["b64_json"])
                        # Legacy support for URL responses (dall-e models)
                        if "url" in image_data:
                            print(f"✅ Found URL in response, fetching: {image_data['url']}")
                            async with session.get(image_data["url"]) as img_response:
                                if img_response.status == self.http_success:
                                    return await img_response.read()
                    
                    # Check if result is a direct dict with image data  
                    elif isinstance(result, dict):
                        if "b64_json" in result:
                            print(f"✅ Found b64_json in dict response, decoding...")
                            return base64.b64decode(result["b64_json"])
                        # Legacy support for URL responses (dall-e models)
                        if "url" in result:
                            print(f"✅ Found URL in response, fetching: {result['url']}")
                            async with session.get(result["url"]) as img_response:
                                if img_response.status == self.http_success:
                                    return await img_response.read()
                    
                    # Handle direct base64 string response (some webhooks might return this)
                    elif isinstance(result, str) and len(result) > 100:
                        try:
                            print(f"✅ Attempting to decode direct base64 string...")
                            return base64.b64decode(result)
                        except Exception as decode_err:
                            print(f"❌ Failed to decode direct string as base64: {decode_err}")
                    
                    # Log the response structure for debugging
                    print(f"🔍 Unexpected response structure: {result}")
                    raise ImageGenerationError("No valid image data in response")
                
                except (json.JSONDecodeError, UnicodeDecodeError) as json_err:
                    print(f"⚠️ JSON parsing failed: {json_err}")
                    print(f"🔍 Raw data starts with: {raw_data[:50]}")
                    
                    # Check if raw data is PNG
                    if raw_data.startswith(b'\x89PNG'):
                        print(f"🎨 Found PNG data in raw response: {len(raw_data)} bytes")
                        return raw_data
                    
                    raise ImageGenerationError(f"Failed to parse response: {json_err}")

        except asyncio.TimeoutError as e:
            msg = f"Image generation timed out after {self.timeout} seconds"
            raise ImageGenerationError(msg) from e
        except Exception as e:
            raise ImageGenerationError(f"Failed to generate image: {str(e)}") from e

    async def generate_images_parallel(
        self, prompts_and_specs: list[tuple[str, dict[str, any]]]
    ) -> list[tuple[int, Optional[bytes]]]:
        """
        Generate multiple images in parallel

        Args:
            prompts_and_specs: List of (prompt, spec_dict) tuples where spec_dict contains:
                - placeholder_description: str
                - placeholder_width: int
                - placeholder_height: int
                - slide_index: int

        Returns:
            List of (slide_index, image_bytes) tuples
        """
        tasks = []

        for prompt, spec in prompts_and_specs:
            task = self._generate_with_retry(
                prompt=prompt,
                placeholder_description=spec.get("placeholder_description", ""),
                placeholder_width=spec.get("placeholder_width", 1200),
                placeholder_height=spec.get("placeholder_height", 456),
                slide_index=spec.get("slide_index", 0),
            )
            tasks.append(task)

        print(f"🚀 Starting parallel image generation for {len(tasks)} images...")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"❌ Image generation failed for task {i}: {result}")
                slide_index = prompts_and_specs[i][1].get("slide_index", i)
                processed_results.append((slide_index, None))
            else:
                processed_results.append(result)

        return processed_results

    async def _generate_with_retry(
        self,
        prompt: str,
        placeholder_description: str,
        placeholder_width: int,
        placeholder_height: int,
        slide_index: int,
    ) -> tuple[int, Optional[bytes]]:
        """
        Generate image with retry logic

        Returns:
            Tuple of (slide_index, image_bytes)
        """
        for attempt in range(self.max_retries):
            try:
                with slide_monitor.trace_llm_call(
                    call_type="image_generation", model=self.image_model, prompt=prompt[:100]
                ):
                    image_data = await self.generate_image(
                        prompt=prompt,
                        placeholder_description=placeholder_description,
                        placeholder_width=placeholder_width,
                        placeholder_height=placeholder_height,
                    )

                    if image_data:
                        print(f"✅ Generated image for slide {slide_index} (attempt {attempt + 1})")
                        return (slide_index, image_data)

            except Exception as e:
                print(f"⚠️ Image generation attempt {attempt + 1} failed for slide {slide_index}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2**attempt)  # Exponential backoff

        print(f"❌ All attempts failed for slide {slide_index}")
        return (slide_index, None)

    def save_image_to_file(self, image_data: bytes, file_path: str) -> bool:
        """
        Save image data to file

        Args:
            image_data: Raw image bytes
            file_path: Path where to save the image

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "wb") as f:
                f.write(image_data)

            print(f"💾 Saved image to {file_path} ({len(image_data)} bytes)")
            return True

        except Exception as e:
            print(f"❌ Failed to save image to {file_path}: {e}")
            return False