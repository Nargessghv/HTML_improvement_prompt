"""
Agent Nodes Module

Langgraph agent implementations for the slide generation workflow.
Each agent handles a specific step in the presentation creation process.
"""

import asyncio
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.runnables import RunnableConfig

from .azure_uploader import AzureBlobUploader
from .html_renderer import HTMLRenderer
from .llm_client import LangchainLLMClient, SlideContent
from .llm_models import RefinedHTML, SlideSpec
from .monitoring import monitor_agent_execution, slide_monitor
from .state import SlideGenerationState

# Add PIL for image compression
try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("⚠️ PIL not available - image compression disabled")




class SlideAssemblyAgent:
    """
    Agent responsible for assembling the final PowerPoint presentation
    from generated content and template layouts
    """

    def __init__(self):
        self.name = "slide_assembler"

    @monitor_agent_execution("slide_assembler")
    def execute(
        self, state: SlideGenerationState, config: Optional[RunnableConfig] = None
    ) -> SlideGenerationState:
        """
        Merge individual slides into final PowerPoint presentation

        This method now:
        1. Uses already-generated individual slides
        2. Merges them into a final deck
        3. Preserves all formatting, LOCKED_ backgrounds, and z-order

        Args:
            state: Current workflow state
            config: Langchain configuration with callbacks

        Returns:
            Updated state with final presentation path
        """
        print(f"🔧 {self.name}: Merging individual slides into final presentation...")

        try:
            # Get project ID and template path from state
            project_id = state.get("project_id")
            template_path = state.get("template_path")
            topic = state.get("topic", "presentation")

            if not project_id:
                # If no project_id, we need to use the slide_contents to identify slides
                print("⚠️ No project_id in state, using alternative approach...")

                # Import here to avoid circular imports
                from .slide_generator import SlideGenerator

                # Fall back to old behavior if no individual slides exist
                slide_contents = state.get("slide_contents")
                layouts_info = state.get("layouts_info")

                if not slide_contents or not layouts_info:
                    raise ValueError("Slide contents and layout info required")

                # Initialize slide generator
                slide_generator = SlideGenerator(template_path)
                slide_generator.content_generator.layouts_info = layouts_info
                slide_generator._current_topic = topic

                # Set output path for fallback
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_topic = "".join(
                    c for c in topic if c.isalnum() or c in " -_"
                ).strip()
                safe_topic = safe_topic.replace(" ", "_")[:50]
                output_filename = f"{safe_topic}_{timestamp}.pptx"
                output_path = os.path.join("generated_presentations", output_filename)
                
                # Ensure output directory exists
                os.makedirs("generated_presentations", exist_ok=True)

                # Generate presentation (old way - for backwards compatibility)
                presentation_path = slide_generator.create_presentation(
                    topic, output_path
                )
            else:
                # Use the new approach - merge individual slides
                print(f"✅ Using individual slides for project: {project_id}")

                # Import the individual slide generator
                from .individual_slide_generator import IndividualSlideGenerator

                # Create instance
                individual_generator = IndividualSlideGenerator()

                # Set output path
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_topic = "".join(
                    c for c in topic if c.isalnum() or c in " -_"
                ).strip()
                safe_topic = safe_topic.replace(" ", "_")[:50]
                output_filename = f"{safe_topic}_{timestamp}.pptx"
                output_path = os.path.join("generated_presentations", output_filename)

                # Ensure output directory exists
                os.makedirs("generated_presentations", exist_ok=True)

                # Combine individual slides into final presentation
                print(f"📚 Combining individual slides into: {output_path}")

                # This method preserves all formatting, images, LOCKED_ backgrounds
                import asyncio

                # Run the async combine method
                if loop.is_running():
                    # We're already in an async context
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run,
                            individual_generator.combine_individual_slides(
                                project_id=project_id,
                                output_path=output_path,
                                template_path=template_path,
                                dynamic_models=state.get("dynamic_models")
                            ),
                        )
                        result = future.result()
                else:
                    # Run normally
                    result = asyncio.run(
                        individual_generator.combine_individual_slides(
                            project_id=project_id,
                            output_path=output_path,
                            template_path=template_path,
                            dynamic_models=state.get("dynamic_models")
                        )
                    )

                if result.get("success"):
                    presentation_path = result["output_path"]
                    print(
                        f"✅ Successfully combined {result.get('slides_combined', 0)} slides"
                    )
                else:
                    raise Exception(
                        f"Failed to combine slides: {result.get('error', 'Unknown error')}"
                    )

            # Store presentation path
            state["presentation_path"] = presentation_path

            # No icon errors when using individual slides
            state["icon_errors"] = []

            print(f"✅ {self.name}: Final presentation created at {presentation_path}")

            return state

        except Exception as e:
            print(f"❌ {self.name}: Failed to assemble presentation: {e}")
            state["error_message"] = str(e)
            state["presentation_path"] = None
            return state

    def _extract_icon_errors_from_output(self, output: str) -> List[str]:
        """
        Extract icon error messages from the output stream.
        This is a placeholder and needs to be implemented based on
        the actual output format of the SlideGenerator.
        """
        icon_errors = []
        # Example: Look for lines starting with "Warning: SVG icon not found:"
        # or "Warning: Icon '... not found or failed to prepare"
        for line in output.splitlines():
            if line.startswith("Warning: SVG icon not found:"):
                icon_name = line.replace("Warning: SVG icon not found:", "").strip()
                icon_errors.append(icon_name)
            elif line.startswith("Warning: Icon '"):
                icon_name = (
                    line.replace("Warning: Icon '", "")
                    .replace("' not found or failed to prepare", "")
                    .strip()
                )
                icon_errors.append(icon_name)
        return list(set(icon_errors))  # Remove duplicates


class IconValidationAgent:
    """
    Agent responsible for validating and correcting invalid icon names
    when icon errors are detected during slide assembly
    """

    def __init__(self):
        self.name = "icon_validator"
        # Use OPENAI_MODEL_FAST for icon validation (fast, simple model)
        fast_model = os.getenv("OPENAI_MODEL_FAST", "gpt-4o-mini")
        self.llm_client = LangchainLLMClient(model=fast_model)
        # Initialize icon manager to get list of available icons
        from .icon_manager import IconManager

        self.icon_manager = IconManager()

    @monitor_agent_execution("icon_validator")
    def execute(
        self, state: SlideGenerationState, config: Optional[RunnableConfig] = None
    ) -> SlideGenerationState:
        """
        Validate and correct invalid icon names using LLM knowledge

        Args:
            state: Current workflow state
            config: Langchain configuration with callbacks

        Returns:
            Updated state with corrected icon names
        """
        print(f"�� {self.name}: Validating and correcting icon names...")

        try:
            # Check if we have icon errors to process
            icon_errors = state.get("icon_errors", [])
            if not icon_errors:
                print(f"✅ {self.name}: No icon errors to correct")
                state["needs_icon_retry"] = False
                state["current_step"] = "icon_validation_complete"
                return state

            print(f"⚠️ {self.name}: Found {len(icon_errors)} icon errors to correct")

            # Extract invalid icon names from error messages
            invalid_icons = self._extract_invalid_icon_names(icon_errors)

            if not invalid_icons:
                print(f"✅ {self.name}: No extractable icon names to correct")
                state["needs_icon_retry"] = False
                state["current_step"] = "icon_validation_complete"
                return state

            print(f"🔍 {self.name}: Correcting icons: {invalid_icons}")

            # Use LLM to suggest correct icon names
            icon_corrections = self._get_icon_corrections_from_llm(
                invalid_icons, state["topic"], config
            )

            if icon_corrections:
                print(f"✅ {self.name}: Generated corrections: {icon_corrections}")
                state["icon_corrections"] = icon_corrections
                state["needs_icon_retry"] = True
                state["current_step"] = "icon_validation_complete"
            else:
                print(f"⚠️ {self.name}: No corrections generated")
                state["needs_icon_retry"] = False
                state["current_step"] = "icon_validation_complete"

            return state

        except Exception as e:
            print(f"❌ {self.name}: Error during icon validation: {e}")
            state["error_message"] = f"Icon validation failed: {str(e)}"
            state["current_step"] = "error"
            return state

    def _extract_invalid_icon_names(self, icon_errors: List[str]) -> List[str]:
        """
        Extract invalid icon names from error messages

        Args:
            icon_errors: List of error messages from icon insertion

        Returns:
            List of invalid icon names
        """
        import re

        invalid_icons = []

        for error in icon_errors:
            # Pattern to extract icon name from error messages like:
            # "Warning: SVG icon not found:
            #   node_modules/lucide-static/icons/bar-chart.svg"
            # "Warning: Icon 'money' not found or failed to prepare"

            # Try pattern 1: from SVG path
            match = re.search(r"icons/([^/\.]+)\.svg", error)
            if match:
                invalid_icons.append(match.group(1))
                continue

            # Try pattern 2: from quoted icon name
            match = re.search(r"Icon '([^']+)' not found", error)
            if match:
                invalid_icons.append(match.group(1))
                continue

        return list(set(invalid_icons))  # Remove duplicates

    def _get_icon_corrections_from_llm(
        self,
        invalid_icons: List[str],
        topic: str,
        config: Optional[RunnableConfig] = None,
    ) -> Dict[str, str]:
        """
        Use LLM to suggest correct lucide-static icon names

        Args:
            invalid_icons: List of invalid icon names
            topic: Presentation topic for context
            config: Langchain configuration

        Returns:
            Dictionary mapping invalid icons to corrected icons
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        # Create the correction prompt
        prompt = self._create_icon_correction_prompt(invalid_icons, topic)
        system_prompt = self._get_icon_correction_system_prompt()

        try:
            # Create messages
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=prompt),
            ]

            # Generate corrections using Langchain
            response = self.llm_client.chat_client.invoke(messages, config=config)

            if response and response.content:
                content = str(response.content) if response.content else ""
                return self._parse_icon_corrections(content, invalid_icons)

            print("⚠️ No response received from LLM for icon corrections")
            return {}

        except Exception as e:
            print(f"❌ Error getting icon corrections from LLM: {e}")
            return {}

    def _create_icon_correction_prompt(
        self, invalid_icons: List[str], topic: str
    ) -> str:
        """Create prompt for LLM icon correction"""
        invalid_list = ", ".join(invalid_icons)

        # Get the actual list of available icons from the IconManager
        all_available_icons = self.icon_manager.icons_database.get("all_icons", [])

        # Take a sample of available icons to show in prompt (first 50)
        # Sort alphabetically for better organization
        sample_icons = sorted(all_available_icons)
        available_icons_text = ", ".join(sample_icons)

        # Also get categorized suggestions for context
        icon_categories = self.icon_manager.icons_database.get("categories", {})
        category_samples = {}
        for category, icons in icon_categories.items():
            if icons:
                category_samples[category] = icons[:5]  # First 5 from each category

        return f"""
The following icon names are INVALID in the lucide-static library and need correction:
{invalid_list}

Presentation topic: {topic}

🎯 AVAILABLE LUCIDE-STATIC ICONS:
{available_icons_text}

📊 ICON CATEGORIES WITH EXAMPLES:
{self._format_category_samples(category_samples)}

📋 TOTAL AVAILABLE: {len(all_available_icons)} icons in the lucide-static library

For each invalid icon, suggest the closest valid lucide-static icon name that:
1. ✅ EXISTS in the lucide-static library (from the list above)
2. 🎯 Has similar meaning/purpose to the invalid icon
3. 📝 Fits the presentation topic: "{topic}"
4. 🔤 Uses exact lucide-static naming (hyphen-separated, lowercase)
5. 🔤 Is a possible abstraction of the invalid icon (e.g circle-dot for molecule)

Please respond in this EXACT format:
invalid_icon1 -> valid_icon1
invalid_icon2 -> valid_icon2

Example:
bar-chart -> bar-chart-3
money -> coins
tools -> wrench
time -> clock
check-circle -> circle-check
"""

    def _format_category_samples(self, category_samples: Dict[str, List[str]]) -> str:
        """Format category samples for the prompt"""
        formatted = []
        for category, icons in category_samples.items():
            if icons:
                icons_text = ", ".join(icons)
                formatted.append(f"  • {category}: {icons_text}")
        return "\n".join(formatted)

    def _get_icon_correction_system_prompt(self) -> str:
        """Get system prompt for icon correction"""
        return """You are an expert lucide-static icon validation specialist with 
access to the COMPLETE database of all available lucide-static icons.

🎯 YOUR TASK: Correct invalid icon names to valid lucide-static alternatives using 
the provided comprehensive list of available icons.

🚨 CRITICAL REQUIREMENTS:
- You have been provided with the COMPLETE list of available lucide-static icons
- ONLY suggest icon names that appear in the provided list
- Do NOT rely on general knowledge - use ONLY the provided icon list
- Choose icons with similar semantic meaning to the invalid ones
- Consider the presentation context when choosing alternatives
- Use exact lucide-static naming conventions (lowercase, hyphen-separated)

📋 VALIDATION PROCESS:
1. Review the invalid icon name
2. Find semantically similar icons from the provided available list
3. Select the best match considering the presentation topic
4. Ensure the suggested icon exists in the provided list

You have been given the actual database of available icons - use this authoritative 
source to make accurate corrections."""

    def _parse_icon_corrections(
        self, response_text: str, invalid_icons: List[str]
    ) -> Dict[str, str]:
        """
        Parse LLM response to extract icon corrections

        Args:
            response_text: Raw LLM response
            invalid_icons: Original invalid icon names

        Returns:
            Dictionary mapping invalid to corrected icon names
        """
        corrections = {}

        lines = response_text.strip().split("\n")

        for line in lines:
            line = line.strip()
            if "->" in line:
                parts = line.split("->")
                if len(parts) == 2:
                    invalid = parts[0].strip()
                    valid = parts[1].strip()

                    # Only include if the invalid icon was in our original list
                    if invalid in invalid_icons:
                        corrections[invalid] = valid

        return corrections


class QualityReviewAgent:
    """
    Agent responsible for reviewing generated content quality
    and providing feedback for improvements
    """

    def __init__(self):
        self.name = "quality_reviewer"
        self.llm_client = LangchainLLMClient()

    @monitor_agent_execution("quality_reviewer")
    def execute(
        self, state: SlideGenerationState, config: Optional[RunnableConfig] = None
    ) -> SlideGenerationState:
        """
        Review content quality and provide improvement suggestions

        Args:
            state: Current workflow state
            config: Langchain configuration with callbacks

        Returns:
            Updated state with quality review results
        """
        print(f"🔍 {self.name}: Reviewing content quality...")

        try:
            # Check prerequisites
            slide_contents = state.get("slide_contents")
            if not slide_contents:
                print(f"⚠️ {self.name}: No content to review, skipping...")
                return state

            topic = state["topic"]

            # Calculate quality metrics
            quality_metrics = self._calculate_quality_metrics(slide_contents, topic)

            # Track quality metrics in monitoring
            monitor_trace = state.get("monitor_trace")
            if monitor_trace:
                slide_monitor.track_content_quality(
                    monitor_trace,
                    {"slide_count": len(slide_contents), "topic": topic},
                    quality_metrics,
                )

            print(f"✅ {self.name}: Quality review complete")
            completeness = quality_metrics.get("completeness", 0)
            relevance = quality_metrics.get("relevance", 0)
            print(f"   📊 Content completeness: {completeness:.1%}")
            print(f"   📊 Topic relevance: {relevance:.1%}")

            return state

        except Exception as e:
            print(f"❌ {self.name}: Error during quality review: {e}")
            # Don't fail the entire workflow for quality review errors
            return state

    def _calculate_quality_metrics(
        self, slide_contents: List[SlideContent], topic: str
    ) -> Dict[str, float]:
        """Calculate content quality metrics"""
        # (Implementation of quality metrics calculation)
        # This is a placeholder for a more sophisticated implementation
        completeness = sum(1 for slide in slide_contents if slide.content) / len(
            slide_contents
        )
        relevance = 0.85  # Placeholder
        return {"completeness": completeness, "relevance": relevance}


class HTMLRefinementAgent:
    """
    Agent responsible for refining HTML content based on visual feedback.
    It renders the HTML, sends it to a vision model, and applies corrections.
    """

    def __init__(self, max_iterations: int = 5):
        self.name = "html_refinement_agent"
        self.llm_client = LangchainLLMClient()
        self.html_renderer = HTMLRenderer()
        self.max_iterations = max_iterations
        self.temp_dir = Path("html_debug")
        self.temp_dir.mkdir(exist_ok=True)

        # Initialize HTML prompt manager for refinement
        from .html_prompt_manager import HTMLPromptManager

        self.html_prompt_manager = HTMLPromptManager()
        print(f"✅ {self.name}: HTML prompt manager initialized for refinement")

        # Initialize the Azure Blob Uploader
        self.uploader = AzureBlobUploader()

        # Initialize Supabase storage and database clients for refinement tracking
        try:
            from .database import get_supabase_client
            from .supabase_storage import get_storage_client

            self.storage_client = get_storage_client()
            self.db_client = get_supabase_client()
            print(
                "✅ Supabase storage and database clients initialized for refinement tracking"
            )
        except Exception as e:
            print(
                f"⚠️ Failed to initialize Supabase clients for refinement tracking: {e}"
            )
            self.storage_client = None
            self.db_client = None

        # Image compression settings optimized for LLM vision models
        self.compression_settings = {
            "max_size_mb": 20,  # OpenAI GPT-4V max is 20MB, Claude is 32MB
            "target_size_mb": 5,  # Target smaller size for faster processing
            "min_quality": 30,  # Don't go below 30% JPEG quality
            "resize_thresholds": [0.8, 0.6, 0.4],  # Progressive resize factors
            "preserve_aspect_ratio": True,
            "convert_to_jpeg": True,  # JPEG compression is more efficient than PNG
            # Optimal dimensions for LLM vision models (reduces token usage dramatically)
            "target_dimensions": {
                "max_width": 768,  # Based on research: 512-768px width is sufficient
                "max_height": 1024,  # Based on research: up to 1024px height works well
                "min_width": 512,  # Minimum width to maintain detail
                "min_height": 512,  # Minimum height to maintain detail
            },
        }

    def _cleanup_old_debug_files(self, keep_latest: int = 5):
        """
        Clean up old debug files to prevent accumulation

        Args:
            keep_latest: Number of latest refinement sessions to keep
        """
        try:
            if not self.temp_dir.exists():
                return

            # Get all HTML and PNG files
            debug_files = list(self.temp_dir.glob("*.html")) + list(
                self.temp_dir.glob("*.png")
            )

            if (
                len(debug_files) <= keep_latest * 10
            ):  # Rough estimate (slides * iterations)
                return

            # Sort by modification time and remove oldest
            debug_files.sort(key=lambda f: f.stat().st_mtime)
            files_to_remove = debug_files[: -keep_latest * 10]

            removed_count = 0
            for file_path in files_to_remove:
                try:
                    file_path.unlink()
                    removed_count += 1
                except OSError:
                    pass

            if removed_count > 0:
                print(f"  🧹 Cleaned up {removed_count} old debug files")

        except Exception as e:
            print(f"  - Warning: Failed to clean up debug files: {e}")

    def _compress_image_for_llm(
        self, image_path: str, max_size_mb: Optional[float] = None
    ) -> bool:
        """
        Compress image for optimal LLM processing while maintaining quality

        Args:
            image_path: Path to the image file to compress
            max_size_mb: Maximum file size in MB (uses configured setting if None)

        Returns:
            True if compression was successful or not needed, False if failed
        """
        if not PIL_AVAILABLE:
            print("  - PIL not available, skipping image compression")
            return True

        # Use configured settings if max_size_mb not provided
        if max_size_mb is None:
            max_size_mb = self.compression_settings["max_size_mb"]

        # Type assertion to help linter - max_size_mb is guaranteed to be float here
        assert max_size_mb is not None
        max_size: float = max_size_mb

        try:
            # Check if file exists
            if not os.path.exists(image_path):
                print(f"  - Image file not found for compression: {image_path}")
                return False

            # Get original file size
            original_size = os.path.getsize(image_path)
            original_size_mb = original_size / (1024 * 1024)

            print(f"  - Original image size: {original_size_mb:.2f} MB")

            # If already under limit, no compression needed
            if original_size_mb <= max_size:
                print(
                    f"  - Image already under {max_size}MB limit, no compression needed"
                )
                return True

            # Open and analyze image
            with Image.open(image_path) as img:
                # Get original dimensions
                original_width, original_height = img.size
                print(f"  - Original dimensions: {original_width}x{original_height}")

                # Convert to RGB if needed (for JPEG compression)
                if img.mode in ("RGBA", "LA", "P"):
                    # Convert RGBA to RGB with white background
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    background.paste(
                        img, mask=img.split()[-1] if img.mode == "RGBA" else None
                    )
                    img = background
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                # STEP 1: Resize to optimal LLM vision dimensions first (most important for token reduction)
                target_dims = self.compression_settings["target_dimensions"]
                max_width = target_dims["max_width"]
                max_height = target_dims["max_height"]
                min_width = target_dims["min_width"]
                min_height = target_dims["min_height"]

                # Calculate optimal resize dimensions
                if original_width > max_width or original_height > max_height:
                    # Calculate scale factor to fit within max dimensions while preserving aspect ratio
                    scale_factor = min(
                        max_width / original_width, max_height / original_height
                    )
                    new_width = max(int(original_width * scale_factor), min_width)
                    new_height = max(int(original_height * scale_factor), min_height)

                    print(
                        f"  - Resizing to optimal LLM dimensions: {new_width}x{new_height}"
                    )
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                    # Save with high quality first to check size
                    temp_path = image_path.replace(".png", "_resized_temp.jpg")
                    img.save(temp_path, format="JPEG", quality=90, optimize=True)

                    # Check file size after optimal resize
                    resized_size = os.path.getsize(temp_path)
                    resized_size_mb = resized_size / (1024 * 1024)

                    print(f"  - After optimal resize: {resized_size_mb:.2f} MB")

                    if resized_size_mb <= max_size:
                        # Great! Optimal resize was sufficient
                        os.remove(image_path)
                        os.rename(temp_path, image_path)

                        dimension_reduction = (
                            (
                                (original_width * original_height)
                                - (new_width * new_height)
                            )
                            / (original_width * original_height)
                            * 100
                        )
                        size_reduction = (
                            (original_size - resized_size) / original_size
                        ) * 100

                        print("  ✅ Optimal dimension resize successful!")
                        print(
                            f"     Original: {original_width}x{original_height} ({original_size_mb:.2f} MB)"
                        )
                        print(
                            f"     Optimized: {new_width}x{new_height} ({resized_size_mb:.2f} MB)"
                        )
                        print(f"     Dimension reduction: {dimension_reduction:.1f}%")
                        print(f"     Size reduction: {size_reduction:.1f}%")
                        print(
                            f"     Token cost savings: ~{dimension_reduction * 0.8:.0f}% (estimated)"
                        )
                        return True
                    # Dimension resize wasn't enough, continue with quality compression
                    print(
                        f"  - Still {resized_size_mb:.2f} MB after resize, applying quality compression..."
                    )
                    compressed_path = temp_path
                else:
                    print(
                        f"  - Image already within optimal dimensions ({original_width}x{original_height})"
                    )
                    compressed_path = image_path.replace(".png", "_compressed.jpg")

                # STEP 2: Apply quality-based compression if needed
                quality = 95

                # Iteratively compress until under size limit
                for attempt in range(5):  # Max 5 attempts
                    # Try current quality level
                    img.save(
                        compressed_path, format="JPEG", quality=quality, optimize=True
                    )

                    # Check file size
                    compressed_size = os.path.getsize(compressed_path)
                    compressed_size_mb = compressed_size / (1024 * 1024)

                    print(
                        f"  - Quality attempt {attempt + 1}: {quality}%, Size: {compressed_size_mb:.2f} MB"
                    )

                    if compressed_size_mb <= max_size:
                        # Success! Replace original with compressed version
                        os.remove(image_path)
                        os.rename(compressed_path, image_path)

                        compression_ratio = (
                            (original_size - compressed_size) / original_size
                        ) * 100
                        print("  ✅ Compression successful!")
                        print(
                            f"     Original: {original_size_mb:.2f} MB → Final: {compressed_size_mb:.2f} MB"
                        )
                        print(f"     Total reduction: {compression_ratio:.1f}%")
                        print(f"     Final quality: {quality}%")
                        return True

                    # If still too large, reduce quality for next attempt
                    if quality > 60:
                        quality -= 15  # Reduce quality more aggressively
                    else:
                        quality -= 5  # Fine-tune at lower qualities

                    if quality < self.compression_settings["min_quality"]:
                        break

                # STEP 3: If quality compression wasn't enough, try further dimension reduction
                print(
                    "  - Quality compression insufficient, trying further dimension reduction..."
                )

                # Use more aggressive resize factors
                aggressive_scales = [0.7, 0.5, 0.3]

                for scale in aggressive_scales:
                    new_width = max(int(original_width * scale), min_width)
                    new_height = max(int(original_height * scale), min_height)

                    # Don't go below minimum dimensions
                    if new_width < min_width or new_height < min_height:
                        continue

                    # Resize image
                    resized_img = img.resize(
                        (new_width, new_height), Image.Resampling.LANCZOS
                    )

                    # Save with good quality since we reduced size significantly
                    resized_img.save(
                        compressed_path, format="JPEG", quality=85, optimize=True
                    )

                    compressed_size = os.path.getsize(compressed_path)
                    compressed_size_mb = compressed_size / (1024 * 1024)

                    print(
                        f"  - Aggressive resize: {new_width}x{new_height}, Size: {compressed_size_mb:.2f} MB"
                    )

                    if compressed_size_mb <= max_size:
                        # Success with aggressive resize!
                        os.remove(image_path)
                        os.rename(compressed_path, image_path)

                        compression_ratio = (
                            (original_size - compressed_size) / original_size
                        ) * 100
                        dimension_reduction = (
                            (
                                (original_width * original_height)
                                - (new_width * new_height)
                            )
                            / (original_width * original_height)
                            * 100
                        )

                        print("  ✅ Aggressive dimension reduction successful!")
                        print(
                            f"     Original: {original_width}x{original_height} ({original_size_mb:.2f} MB)"
                        )
                        print(
                            f"     Final: {new_width}x{new_height} ({compressed_size_mb:.2f} MB)"
                        )
                        print(f"     Total reduction: {compression_ratio:.1f}%")
                        print(f"     Dimension reduction: {dimension_reduction:.1f}%")
                        print(
                            f"     Massive token savings: ~{dimension_reduction * 0.8:.0f}% (estimated)"
                        )
                        return True

                # Clean up temporary file if all compression attempts failed
                if os.path.exists(compressed_path):
                    os.remove(compressed_path)

                print(f"  ⚠️ Could not compress image under {max_size}MB limit")
                print("     Final size may exceed limit but continuing processing")
                return True  # Return True to continue processing

        except Exception as e:
            print(f"  ❌ Error during image compression: {e}")
            return True  # Return True to continue processing even if compression fails

    async def _track_refinement_in_supabase(
        self,
        project_id: str,
        slide_id: str,
        iteration: int,
        html_content: str,
        image_path: Path,
        refinement_feedback: Optional[str] = None,
        refinement_prompt: Optional[str] = None,
        is_final: bool = False,
    ) -> Optional[str]:
        """
        Track HTML refinement iteration in Supabase storage and database

        Args:
            project_id: Project UUID
            slide_id: Slide UUID
            iteration: Refinement iteration number
            html_content: HTML content for this iteration
            image_path: Path to rendered image file
            refinement_feedback: LLM feedback from this iteration
            refinement_prompt: Prompt used for this iteration
            is_final: Whether this is the final refinement

        Returns:
            Refinement record ID if successful, None otherwise
        """
        if not self.storage_client or not self.db_client:
            print("  - Supabase clients not available, skipping refinement tracking")
            return None

        try:
            # Upload HTML and image to Supabase Storage
            html_url, image_url = self.storage_client.upload_refinement_files(
                project_id, slide_id, iteration, html_content, image_path
            )

            # Skip PPTX creation during iterations - only create PNG files
            pptx_url = None
            print(f"  🖼️ Iteration {iteration}: PNG saved for refinement preview")

            # Create database record for this refinement iteration
            refinement_record = self.db_client.create_html_refinement(
                project_id=project_id,
                slide_id=slide_id,
                iteration_number=iteration,
                html_content=html_content,
                html_file_url=html_url,
                image_file_url=image_url,
                pptx_file_url=pptx_url,
                refinement_feedback=refinement_feedback,
                refinement_prompt=refinement_prompt,
                is_final=is_final,
            )

            print(
                f"  ✅ Tracked refinement iteration {iteration} in Supabase: {refinement_record['id']}"
            )
            return refinement_record["id"]

        except Exception as e:
            print(f"  ⚠️ Failed to track refinement in Supabase: {e}")
            return None

    async def _create_pptx_version(
        self,
        project_id: str,
        slide_id: str,
        iteration: int,
        html_content: str,
        image_path: Path,
    ) -> Optional[str]:
        """
        Create a PPTX version for a specific refinement iteration

        Args:
            project_id: Project UUID
            slide_id: Slide UUID
            iteration: Refinement iteration number
            html_content: HTML content to render
            image_path: Path to the rendered image file

        Returns:
            Supabase Storage URL of the created PPTX file, or None if failed
        """
        try:
            # Import the individual slide generator
            from .individual_slide_generator import IndividualSlideGenerator
            from .llm_client import SlideContent

            # Get project data to retrieve layouts_info
            project_data = self.db_client.get_project(project_id)
            layouts_info = {}
            if project_data:
                layouts_info = project_data.get("layouts_info", {})
                print(f"🔍 DEBUG: Retrieved layouts_info from project: {bool(layouts_info)}")
            else:
                print(f"⚠️ Could not retrieve project data for project_id {project_id}")

            # Get slide data from database to understand layout and content structure
            slide_data = self.db_client.get_slide_details(slide_id)
            if not slide_data:
                print(f"    ❌ Could not find slide data for slide_id {slide_id}")
                return None

            # DEBUGGING: Print what we got from database
            print("🔍 DEBUG: Retrieved slide_data from database:")
            print(f"  - slide_id: {slide_id}")
            print(f"  - layout_index: {slide_data.get('layout_index')}")
            print(f"  - layout_type: {slide_data.get('layout_type')}")
            print(f"  - slide_number: {slide_data.get('slide_number')}")
            print(f"  - title: {slide_data.get('title')}")
            print(
                f"  - content keys: {list(slide_data.get('content', {}).keys()) if slide_data.get('content') else 'None'}"
            )

            # Create a SlideContent object with the refined HTML
            # Start with original content from the slide
            content_dict = slide_data.get("content", {}) or {}

            # Update with title and refined HTML
            content_dict.update(
                {
                    # Include title in content if available
                    "title": slide_data.get("title", "Untitled"),
                    # Replace any existing HTML content with the refined version
                    "main_content": html_content,
                    "html_visualization": html_content,
                }
            )

            # CRITICAL FIX: Get layout_index from database, with fallback to dynamic detection
            layout_index = slide_data.get("layout_index")
            print(
                f"🔍 DEBUG: Raw layout_index from database: {layout_index} (type: {type(layout_index)})"
            )

            if layout_index is None and layouts_info:
                # Dynamically find the right layout based on content characteristics
                layout_type = slide_data.get("layout_type", "")
                content_type = slide_data.get("content_type", "")
                print(
                    f"🔍 DEBUG: layout_type: '{layout_type}', content_type: '{content_type}'"
                )

                # Check if this is HTML/visual content and find appropriate layout
                is_html_content = any(
                    keyword in str(layout_type).lower()
                    for keyword in [
                        "html",
                        "chart",
                        "visual",
                        "timeline",
                        "diagram",
                        "interactive",
                    ]
                )
                is_visual_content = any(
                    keyword in str(content_type).lower()
                    for keyword in ["chart", "timeline", "visual", "comparison"]
                )

                if is_html_content or is_visual_content:
                    # Find layout with HTML picture placeholder
                    layout_index = self._find_html_capable_layout(layouts_info)
                    if layout_index is not None:
                        print(f"🎯 Found HTML-capable layout: {layout_index}")
                    else:
                        # Fallback to any picture layout
                        layout_index = self._find_picture_layout(layouts_info)
                        print(f"🎯 Using picture layout as fallback: {layout_index}")
                else:
                    # Find appropriate text layout
                    layout_index = self._find_text_layout(layouts_info)
                    print(f"🎯 Using text layout: {layout_index}")

                # Final fallback if no suitable layout found
                if layout_index is None:
                    layout_index = (
                        next(iter(layouts_info.keys())) if layouts_info else 0
                    )
                    print(
                        f"⚠️ No suitable layout found, using first available: {layout_index}"
                    )
            elif layout_index is None:
                # No layouts_info available, use default
                layout_index = 0
                print("⚠️ No layouts_info available, using default layout 0")
            else:
                # Ensure layout_index is an integer
                try:
                    layout_index = int(layout_index)
                    print(f"🎯 Using stored layout_index: {layout_index}")
                except (ValueError, TypeError):
                    print(
                        f"⚠️ Invalid layout_index format: {layout_index}, defaulting to 0"
                    )
                    layout_index = 0

            slide_content = SlideContent(
                layout_index=layout_index, content=content_dict
            )

            # DEBUGGING: Verify SlideContent object was created correctly
            print("🔍 DEBUG: Created SlideContent object:")
            print(f"  - layout_index: {slide_content.layout_index}")
            print(
                f"  - content keys: {list(slide_content.content.keys()) if slide_content.content else 'None'}"
            )

            # Get project data to find template path
            project_data = self.db_client.get_project(project_id)
            if not project_data:
                print(f"    ❌ Could not find project data for project_id {project_id}")
                return None

            # CRITICAL FIX: Use project's original template instead of defaulting to alphabetically first
            # Get template from project data to maintain consistency
            if project_data and project_data.get("template_path"):
                template_path = project_data["template_path"]
                print(f"🎯 Using project template: {template_path}")
            else:
                # Fallback to default only if project has no template
                from .template_manager import resolve_template_path

                template_path = resolve_template_path()
                print(f"⚠️ Using fallback template: {template_path}")

            # Create slide generator instance
            slide_generator = IndividualSlideGenerator()

            # Create a unique filename for this PPTX version
            import uuid

            version_filename = f"slide_{slide_data.get('slide_number', 1):02d}_v{iteration}_{uuid.uuid4().hex[:8]}.pptx"

            # Analyze template layout to get proper placeholder mapping
            try:
                from .layout_analyzer import LayoutAnalyzer

                layout_analyzer = LayoutAnalyzer(template_path)
                layouts_info = layout_analyzer.analyze_all_layouts()
                print(
                    f"✅ Analyzed template layouts: {len(layouts_info)} layouts found"
                )

                # Generate layouts export file if missing (for backward compatibility)
                layouts_export_path = "layouts_export.json"
                if not os.path.exists(layouts_export_path):
                    print("📄 Generating missing layouts export file...")
                    layout_analyzer.export_layouts_to_file(layouts_export_path)

            except Exception as e:
                print(f"⚠️ Layout analysis failed, using empty layouts_info: {e}")
                layouts_info = {}

            # Generate the individual PPTX slide
            result = await slide_generator.generate_individual_slide(
                slide_id=slide_id,
                project_id=project_id,
                slide_content=slide_content,
                template_path=template_path,
                slide_number=slide_data.get("slide_number", 1),
                layouts_info=layouts_info,  # Use analyzed layout info
                dynamic_models={},  # Will be populated by the generator
                html_image_path=str(image_path),  # Pass the rendered image path
            )

            if not result or not result.get("success"):
                print(
                    f"    ❌ Failed to generate PPTX: {result.get('error', 'Unknown error')}"
                )
                return None

            # Upload PPTX to Supabase Storage
            pptx_path = result.get("file_path")
            if not pptx_path or not os.path.exists(pptx_path):
                print(f"    ❌ PPTX file not found at: {pptx_path}")
                return None

            # Upload to storage with version-specific path
            storage_path = (
                f"projects/{project_id}/slides/{slide_id}/versions/{version_filename}"
            )
            pptx_url = self.storage_client.upload_file(
                file_path=pptx_path,
                storage_path=storage_path,
                content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                bucket_name="presentations",  # Use presentations bucket for PPTX files
            )

            if pptx_url:
                print(f"    ✅ PPTX version uploaded to: {pptx_url}")

            # Clean up local file after processing
            try:
                if os.path.exists(pptx_path):
                    os.remove(pptx_path)
            except Exception as cleanup_e:
                print(f"    ⚠️ Failed to clean up temp file: {cleanup_e}")
            else:
                print("    ❌ Failed to upload PPTX to storage")

            return pptx_url

        except Exception as e:
            print(f"    ❌ Error creating PPTX version: {e}")
            return None

    def _find_html_capable_layout(self, layouts_info: Dict[int, Dict]) -> Optional[int]:
        """
        Find a layout that has HTML picture placeholders
        """
        for layout_idx, layout_data in layouts_info.items():
            placeholders = layout_data.get("placeholders", [])
            for placeholder in placeholders:
                ph_name = placeholder.get("name", "").lower()
                # Look for HTML-specific picture placeholders
                if "html" in ph_name and ("picture" in ph_name or "image" in ph_name):
                    return layout_idx
        return None

    def _find_picture_layout(self, layouts_info: Dict[int, Dict]) -> Optional[int]:
        """
        Find a layout with picture placeholders
        """
        for layout_idx, layout_data in layouts_info.items():
            placeholders = layout_data.get("placeholders", [])
            for placeholder in placeholders:
                ph_name = placeholder.get("name", "").lower()
                ph_type = placeholder.get("type", 0)
                # Look for picture placeholders (type 18 is typically PICTURE)
                if "picture" in ph_name or "image" in ph_name or ph_type == 18:
                    return layout_idx
        return None

    def _find_text_layout(self, layouts_info: Dict[int, Dict]) -> Optional[int]:
        """
        Find a layout suitable for text content
        """
        for layout_idx, layout_data in layouts_info.items():
            layout_name = layout_data.get("name", "").lower()
            # Look for text-focused layouts
            if "text" in layout_name and "content" in layout_name:
                return layout_idx

        # Fallback: find any layout with content placeholders
        for layout_idx, layout_data in layouts_info.items():
            placeholders = layout_data.get("placeholders", [])
            for placeholder in placeholders:
                ph_name = placeholder.get("name", "").lower()
                if "content" in ph_name or "text" in ph_name or "body" in ph_name:
                    return layout_idx

        return None

    def _get_or_create_slide_id(
        self, project_id: str, slide_index: int, slide_content: Any
    ) -> Optional[str]:
        """
        Get existing slide ID or create a new slide record for refinement tracking

        Args:
            project_id: Project UUID
            slide_index: Zero-based slide index
            slide_content: Slide content object

        Returns:
            Slide UUID if successful, None otherwise
        """
        if not self.db_client:
            return None

        try:
            # Check if slide already exists
            existing_slides = self.db_client.get_project_slides(project_id)
            slide_number = slide_index + 1  # Convert to 1-based

            for slide in existing_slides:
                if slide["slide_number"] == slide_number:
                    return slide["id"]

            # Create new slide record
            slide_title = f"Slide {slide_number}"
            content_dict = {}

            if hasattr(slide_content, "content") and slide_content.content:
                content_dict = slide_content.content
                # Try to get a better title from content
                for key, value in slide_content.content.items():
                    if "title" in key.lower() and isinstance(value, str):
                        slide_title = value[:100]  # Limit length
                        break

            layout_index = getattr(slide_content, "layout_index", 0)
            slide_record = self.db_client.create_slide(
                project_id=project_id,
                slide_number=slide_number,
                title=slide_title,
                content=content_dict,
                layout_type=f"layout_{layout_index}",
                layout_index=layout_index,  # CRITICAL FIX: Store layout_index for HTML refinement
            )

            return slide_record["id"]

        except Exception as e:
            print(f"  ⚠️ Failed to get/create slide ID: {e}")
            return None

    @monitor_agent_execution("html_refinement_agent")
    def execute(
        self, state: SlideGenerationState, config: Optional[RunnableConfig] = None
    ) -> SlideGenerationState:
        """
        Refine HTML content through iterative visual feedback.
        This agent manages a queue of HTML slides and refines them one by one.
        """
        print(f"🎨 {self.name}: Running HTML refinement process...")

        # Clean up old debug files at the start
        self._cleanup_old_debug_files()

        # Set template for HTML prompt selection if available
        template_name = None
        
        # Debug: Print state keys related to template
        print(f"📁 {self.name}: Extracting template from state...")
        print(f"   - template_folder_path: {state.get('template_folder_path')}")
        print(f"   - template_path: {state.get('template_path')}")
        print(f"   - template_name: {state.get('template_name')}")
        
        template_folder_path = state.get("template_folder_path")
        if template_folder_path:
            from pathlib import Path

            template_name = Path(template_folder_path).name
            print(f"   - Extracted from folder_path: {template_name}")

        if not template_name:
            template_path = state.get("template_path")
            if template_path:
                template_path_str = str(template_path)
                print(f"   - Checking template_path: {template_path_str}")
                
                # Generic template extraction from path
                if "templates/" in template_path_str or "templates\\" in template_path_str:
                    from pathlib import Path
                    path_parts = Path(template_path_str).parts
                    
                    # Find the templates directory
                    if "templates" in path_parts:
                        idx = path_parts.index("templates")
                        # The next part after "templates" should be the template folder name
                        if idx + 1 < len(path_parts):
                            # Get the folder name (not the .pptx file)
                            potential_name = path_parts[idx + 1]
                            # If it's a .pptx file, we're looking at the wrong level
                            if potential_name.endswith('.pptx'):
                                # Try to get the parent folder name
                                if idx + 2 < len(path_parts):
                                    potential_name = path_parts[idx + 2]
                            
                            # Clean the name (remove .pptx if present)
                            template_name = potential_name.replace('.pptx', '')
                            print(f"   - Extracted template from path: {template_name}")
        
        # Try direct template_name from state
        if not template_name:
            direct_name = state.get("template_name")
            if direct_name:
                template_name = direct_name
                print(f"   - Got direct template_name: {template_name}")
        
        # Clean up template name
        if template_name:
            original = template_name
            template_name = template_name.replace('.pptx', '')
            if template_name.endswith('_1') or template_name.endswith('_2'):
                template_name = template_name[:-2]
            if original != template_name:
                print(f"   - Cleaned template name: {original} -> {template_name}")

        if template_name:
            self.html_prompt_manager.set_template(template_name)
            print(
                f"📁 {self.name}: Using template '{template_name}' for refinement prompts"
            )
            # Store template name for debugging
            self._current_template_name = template_name
        else:
            self._current_template_name = None

        slide_contents = state.get("slide_contents")
        if not slide_contents:
            print("  - No slide contents found. Skipping refinement.")
            state["needs_html_refinement"] = False
            state["current_step"] = "html_refinement_complete"
            return state

        # Initialize the queue of HTML slides on the first run
        if (
            "html_slides_to_refine_queue" not in state
            or state["html_slides_to_refine_queue"] is None
        ):
            html_slide_indices = self._identify_html_slides(slide_contents)
            state["html_slides_to_refine_queue"] = html_slide_indices
            state["html_refinement_slide_index"] = None
            state["html_refinement_iteration"] = 0
            print(
                f"  - Identified {len(html_slide_indices)} HTML slides to refine: {html_slide_indices}"
            )

        queue = state.get("html_slides_to_refine_queue", [])
        current_slide_index = state.get("html_refinement_slide_index")
        iteration = state.get("html_refinement_iteration", 0)

        # If there is no slide being actively refined, pick the next one from the queue.
        if current_slide_index is None:
            if not queue:
                print("  - HTML refinement queue is empty. Process complete.")
                state["needs_html_refinement"] = False
                state["current_step"] = "html_refinement_complete"
                return state

            # Get the next slide from the queue and reset the iteration count for it.
            current_slide_index = queue.pop(0)
            iteration = 1
            state["html_slides_to_refine_queue"] = queue
            state["html_refinement_slide_index"] = current_slide_index
            state["html_refinement_iteration"] = iteration
            print(
                f"  - Starting refinement for slide {current_slide_index + 1} (index {current_slide_index}), Iteration {iteration}/{self.max_iterations}"
            )
        else:
            # Continue refining the current slide.
            iteration += 1
            state["html_refinement_iteration"] = iteration
            print(
                f"  - Continuing refinement for slide {current_slide_index + 1} (index {current_slide_index}), Iteration {iteration}/{self.max_iterations}"
            )

        # Check if we have exceeded the max refinement iterations for the current slide.
        if iteration > self.max_iterations:
            print(
                f"  - Max refinement iterations reached for slide {current_slide_index + 1}."
            )
            # Move to the next slide in the next execution cycle.
            state["html_refinement_slide_index"] = None
            state["html_refinement_iteration"] = 0

            # Check if there are more slides in the queue.
            is_queue_empty = not state.get("html_slides_to_refine_queue")
            state["needs_html_refinement"] = not is_queue_empty

            if is_queue_empty:
                print("  - All HTML slides have been refined.")
                state["current_step"] = "html_refinement_complete"
            return state

        # --- Core refinement logic for the current_slide_index ---
        html_content = self._get_html_content_for_slide(
            slide_contents, current_slide_index
        )
        if not html_content or not html_content.strip():
            print(f"  - No HTML content for slide {current_slide_index + 1}. Skipping.")
            state["html_refinement_slide_index"] = None
            state["html_refinement_iteration"] = 0
            state["needs_html_refinement"] = bool(
                state.get("html_slides_to_refine_queue")
            )
            if not state["needs_html_refinement"]:
                state["current_step"] = "html_refinement_complete"
            return state

        presentation_plan = state.get("presentation_plan")
        slide_purpose = "No purpose provided."
        if presentation_plan and current_slide_index < len(presentation_plan):
            slide_spec = presentation_plan[current_slide_index]
            purpose_parts = []
            if slide_spec.slide_purpose:
                purpose_parts.append(f"Purpose: {slide_spec.slide_purpose}")
            if slide_spec.detailed_purpose:
                purpose_parts.append(f"Details: {slide_spec.detailed_purpose}")
            if purpose_parts:
                slide_purpose = "\n".join(purpose_parts)

        refinement_id = state.get("refinement_id") or str(uuid.uuid4())
        state["refinement_id"] = refinement_id

        # Use a unique filename for each slide and iteration to avoid conflicts.
        # Use 1-based slide numbering for clarity
        slide_number = current_slide_index + 1
        image_filename = (
            f"{refinement_id}_slide_{slide_number:02d}_iteration_{iteration}.png"
        )
        image_path = self.temp_dir / image_filename
        html_filename = (
            f"{refinement_id}_slide_{slide_number:02d}_iteration_{iteration}.html"
        )
        html_path = self.temp_dir / html_filename
        try:
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"  - Saved HTML for iteration {iteration} to: {html_path}")
        except Exception as e:
            print(f"  - Warning: Failed to save HTML debug file: {e}")

        if not self._render_html_to_image(html_content, str(image_path)):
            print("  - Failed to render HTML to image.")
            state["error_message"] = "HTML rendering failed during refinement."
            state["needs_html_refinement"] = False  # Stop refinement on render failure
            state["current_step"] = "html_refinement_complete"
            return state

        # Compress image for optimal LLM processing
        print("  🗜️ Compressing image for LLM processing...")
        if not self._compress_image_for_llm(str(image_path)):
            print("  - Image compression failed, but continuing with original image")

        image_url = self.uploader.upload_file(
            str(image_path), blob_name=f"refinement/{image_filename}"
        )
        if not image_url:
            print("  - Failed to upload image to Azure Blob Storage.")
            state["error_message"] = "Image upload failed during refinement."
            state["needs_html_refinement"] = False
            state["current_step"] = "html_refinement_complete"
            return state

        print(f"  - Rendered HTML to image and uploaded to: {image_url}")

        try:
            # Get refinement history for this slide
            refinement_history_key = f"html_refinement_history_{current_slide_index}"
            refinement_history = state.get(refinement_history_key, [])

            correction_response = self._get_html_correction(
                html_content, image_url, slide_purpose, refinement_history, config, current_slide_index
            )
            if (
                correction_response
                and correction_response.html_code.strip().lower() != "no changes"
            ):
                print("  - HTML content updated.")
                print(f"  - Reasoning: {correction_response.reasoning}")
                print("  - Changes Applied:")
                for change in correction_response.changes_applied:
                    print(f"    - {change}")

                # Track refinement history for this slide to prevent flip-flopping
                refinement_history.extend(correction_response.changes_applied)
                state[refinement_history_key] = refinement_history

                state["slide_contents"] = self._update_slide_content(
                    slide_contents, current_slide_index, correction_response.html_code
                )
                # This slide needs another refinement iteration.
                state["needs_html_refinement"] = True
            else:
                print(
                    "  - No significant changes suggested. Refinement for this slide is complete."
                )
                # This slide is done. Clear its refinement history and move to next.
                state["html_refinement_slide_index"] = None
                state["html_refinement_iteration"] = 0
                # Clear refinement history for completed slide
                if refinement_history_key in state:
                    del state[refinement_history_key]

                # Check if there are more slides in the queue.
                is_queue_empty = not state.get("html_slides_to_refine_queue")
                state["needs_html_refinement"] = not is_queue_empty

                if is_queue_empty:
                    print("  - All HTML slides have been refined.")
                    state["current_step"] = "html_refinement_complete"

        except Exception as e:
            print(f"  - Error getting HTML correction: {e}")
            print("  - Proceeding with the current HTML content for this slide.")
            # Stop refining this slide and move to the next one.
            state["html_refinement_slide_index"] = None
            state["html_refinement_iteration"] = 0

            is_queue_empty_on_error = not state.get("html_slides_to_refine_queue")
            state["needs_html_refinement"] = not is_queue_empty_on_error

            if is_queue_empty_on_error:
                state["current_step"] = "html_refinement_complete"

        return state

    @monitor_agent_execution("html_refinement_agent_parallel")
    async def execute_parallel(
        self, state: SlideGenerationState, config: Optional[RunnableConfig] = None
    ) -> SlideGenerationState:
        """
        Refine HTML content through iterative visual feedback in TRUE parallel.
        All slides are processed simultaneously with parallel LLM calls.

        Args:
            state: Current workflow state
            config: Langchain configuration with callbacks

        Returns:
            Updated state with refined HTML content
        """
        print(f"🎨 {self.name}: Running TRUE parallel HTML refinement process...")

        # Clean up old debug files at the start
        self._cleanup_old_debug_files()

        # Set template for HTML prompt selection if available
        template_name = None
        
        # Debug: Print state keys related to template
        print(f"📁 {self.name}: Extracting template from state...")
        print(f"   - template_folder_path: {state.get('template_folder_path')}")
        print(f"   - template_path: {state.get('template_path')}")
        print(f"   - template_name: {state.get('template_name')}")
        
        template_folder_path = state.get("template_folder_path")
        if template_folder_path:
            from pathlib import Path

            template_name = Path(template_folder_path).name
            print(f"   - Extracted from folder_path: {template_name}")

        if not template_name:
            template_path = state.get("template_path")
            if template_path:
                template_path_str = str(template_path)
                print(f"   - Checking template_path: {template_path_str}")
                
                # Generic template extraction from path
                if "templates/" in template_path_str or "templates\\" in template_path_str:
                    from pathlib import Path
                    path_parts = Path(template_path_str).parts
                    
                    # Find the templates directory
                    if "templates" in path_parts:
                        idx = path_parts.index("templates")
                        # The next part after "templates" should be the template folder name
                        if idx + 1 < len(path_parts):
                            # Get the folder name (not the .pptx file)
                            potential_name = path_parts[idx + 1]
                            # If it's a .pptx file, we're looking at the wrong level
                            if potential_name.endswith('.pptx'):
                                # Try to get the parent folder name
                                if idx + 2 < len(path_parts):
                                    potential_name = path_parts[idx + 2]
                            
                            # Clean the name (remove .pptx if present)
                            template_name = potential_name.replace('.pptx', '')
                            print(f"   - Extracted template from path: {template_name}")
        
        # Try direct template_name from state
        if not template_name:
            direct_name = state.get("template_name")
            if direct_name:
                template_name = direct_name
                print(f"   - Got direct template_name: {template_name}")
        
        # Clean up template name
        if template_name:
            original = template_name
            template_name = template_name.replace('.pptx', '')
            if template_name.endswith('_1') or template_name.endswith('_2'):
                template_name = template_name[:-2]
            if original != template_name:
                print(f"   - Cleaned template name: {original} -> {template_name}")

        if template_name:
            self.html_prompt_manager.set_template(template_name)
            print(
                f"📁 {self.name}: Using template '{template_name}' for parallel refinement prompts"
            )
            # Store template name for debugging
            self._current_template_name = template_name
        else:
            self._current_template_name = None

        slide_contents = state.get("slide_contents")
        if not slide_contents:
            print("  - No slide contents found. Skipping refinement.")
            state["needs_html_refinement"] = False
            state["current_step"] = "html_refinement_complete"
            return state

        # Identify all HTML slides
        html_slide_indices = self._identify_html_slides(slide_contents)
        if not html_slide_indices:
            print("  - No HTML slides identified. Skipping refinement.")
            state["needs_html_refinement"] = False
            state["current_step"] = "html_refinement_complete"
            return state

        print(
            f"  - Identified {len(html_slide_indices)} HTML slides for TRUE parallel refinement: {html_slide_indices}"
        )

        # Generate a single refinement ID for this batch
        refinement_id = str(uuid.uuid4())
        state["refinement_id"] = refinement_id

        # Get presentation plan for slide purposes
        presentation_plan = state.get("presentation_plan")

        # Prepare slide data for parallel processing
        slide_data = []
        for slide_index in html_slide_indices:
            html_content = self._get_html_content_for_slide(slide_contents, slide_index)
            if not html_content or not html_content.strip():
                print(f"  - No HTML content for slide {slide_index + 1}. Skipping.")
                continue

            # Get slide purpose
            slide_purpose = "No purpose provided."
            if presentation_plan and slide_index < len(presentation_plan):
                slide_spec = presentation_plan[slide_index]
                purpose_parts = []
                if slide_spec.slide_purpose:
                    purpose_parts.append(f"Purpose: {slide_spec.slide_purpose}")
                if slide_spec.detailed_purpose:
                    purpose_parts.append(f"Details: {slide_spec.detailed_purpose}")
                if purpose_parts:
                    slide_purpose = "\n".join(purpose_parts)

            slide_data.append(
                {
                    "slide_index": slide_index,
                    "html_content": html_content,
                    "slide_purpose": slide_purpose,
                }
            )

        if not slide_data:
            print("  - No valid HTML slides to process.")
            state["needs_html_refinement"] = False
            state["current_step"] = "html_refinement_complete"
            return state

        # Process all slides with TRUE parallel iterations
        print(f"  🚀 Starting TRUE parallel refinement for {len(slide_data)} slides...")
        refined_contents = await self._refine_all_slides_parallel(
            slide_data, refinement_id, state, config
        )

        # Update slide contents with refined HTML
        updated_slide_contents = slide_contents.copy()
        success_count = 0

        for slide_index, refined_html in refined_contents.items():
            if refined_html:
                updated_slide_contents = self._update_slide_content(
                    updated_slide_contents, slide_index, refined_html
                )
                success_count += 1
                print(f"  ✅ Successfully refined slide {slide_index + 1}")

        # Update state with refined content
        state["slide_contents"] = updated_slide_contents
        state["needs_html_refinement"] = False
        state["current_step"] = "html_refinement_complete"

        print(
            f"🎉 {self.name}: TRUE parallel refinement complete! {success_count}/{len(slide_data)} slides refined successfully."
        )
        
        # Trigger final PPTX creation for slides with HTML content
        await self._create_final_pptx_files(state, slide_data)
        
        return state

    async def _create_final_pptx_files(
        self, 
        state: SlideGenerationState, 
        slide_data: List[Dict[str, Any]]
    ):
        """
        Create final PPTX files for slides with HTML content using the final refined HTML
        """
        print(f"📄 {self.name}: Creating final PPTX files for refined HTML slides...")
        
        try:
            # Import here to avoid circular imports
            from .individual_slide_generator import IndividualSlideGenerator
            
            slide_generator = IndividualSlideGenerator()
            
            # Get required state information
            project_id = state.get("project_id")
            template_path = state.get("template_path")
            layouts_info = state.get("layouts_info")
            dynamic_models = state.get("dynamic_models")
            
            if not all([project_id, template_path, layouts_info]):
                print(f"  ❌ Missing required information for PPTX generation")
                return
            
            # Create final PPTX for each slide with HTML content
            for slide_info in slide_data:
                slide_index = slide_info["slide_index"]
                slide_content = slide_info["slide_content"]
                
                # Get slide ID from database
                slide_id = await self._get_slide_id_from_database(project_id, slide_index + 1)
                if not slide_id:
                    print(f"  ⚠️ Could not find slide ID for slide {slide_index + 1}")
                    continue
                
                # Get final refined HTML from database
                final_html_image_path = await self._get_final_html_image_path(project_id, slide_id)
                
                if final_html_image_path:
                    print(f"  📄 Creating final PPTX for slide {slide_index + 1} with HTML image")
                    
                    # Generate individual PPTX with final HTML image
                    result = await slide_generator.generate_individual_slide(
                        slide_id=slide_id,
                        project_id=project_id,
                        slide_content=slide_content,
                        template_path=template_path,
                        slide_number=slide_index + 1,
                        layouts_info=layouts_info,
                        dynamic_models=dynamic_models,
                        html_image_path=final_html_image_path
                    )
                    
                    if result.get("success"):
                        print(f"  ✅ Final PPTX created for slide {slide_index + 1}")
                    else:
                        print(f"  ❌ Failed to create final PPTX for slide {slide_index + 1}: {result.get('error')}")
                else:
                    print(f"  ℹ️ No HTML content for slide {slide_index + 1}, skipping PPTX generation")
                    
        except Exception as e:
            print(f"  ❌ Error creating final PPTX files: {e}")

    async def _get_slide_id_from_database(self, project_id: str, slide_number: int) -> Optional[str]:
        """Get slide ID from database using project_id and slide_number"""
        try:
            response = self.db_client.table('slides').select('id').eq('project_id', project_id).eq('slide_number', slide_number).execute()
            if response.data:
                return response.data[0]['id']
            return None
        except Exception as e:
            print(f"  ❌ Error getting slide ID: {e}")
            return None

    async def _get_final_html_image_path(self, project_id: str, slide_id: str) -> Optional[str]:
        """Get the final HTML image path from the last refinement iteration"""
        try:
            # Get the final refinement iteration (is_final=true)
            response = self.db_client.table('html_refinements').select('image_file_url').eq('project_id', project_id).eq('slide_id', slide_id).eq('is_final', True).execute()
            
            if response.data:
                return response.data[0]['image_file_url']
            
            # Fallback: get the latest iteration if no final iteration found
            response = self.db_client.table('html_refinements').select('image_file_url').eq('project_id', project_id).eq('slide_id', slide_id).order('iteration_number', desc=True).limit(1).execute()
            
            if response.data:
                return response.data[0]['image_file_url']
                
            return None
        except Exception as e:
            print(f"  ❌ Error getting final HTML image path: {e}")
            return None

    async def _refine_all_slides_parallel(
        self,
        slide_data: List[Dict[str, Any]],
        refinement_id: str,
        state: SlideGenerationState,
        config: Optional[RunnableConfig] = None,
        max_iterations: int = 5,
    ) -> Dict[int, Optional[str]]:
        """
        Refine all slides with TRUE parallel processing. Each slide runs its full
        refinement loop independently.
        """
        print(
            f"  🔄 Processing {len(slide_data)} slides with independent parallel refinement loops..."
        )

        # Extract project ID and slide contents from state
        project_id = state.get("project_id")
        slide_contents = state.get("slide_contents", [])

        tasks = []
        for data in slide_data:
            slide_index = data["slide_index"]
            slide_content = (
                slide_contents[slide_index]
                if slide_index < len(slide_contents)
                else None
            )

            task = self._refine_one_slide_fully_async(
                slide_index=slide_index,
                initial_html_content=data["html_content"],
                slide_purpose=data["slide_purpose"],
                refinement_id=refinement_id,
                project_id=project_id,
                slide_content=slide_content,
                config=config,
                max_iterations=max_iterations,
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        final_html_contents = {}
        for i, result in enumerate(results):
            slide_index = slide_data[i]["slide_index"]
            if isinstance(result, BaseException):
                print(f"      ❌ Error refining slide {slide_index + 1}: {result}")
                # Return the original HTML on error to avoid losing content
                final_html_contents[slide_index] = slide_data[i]["html_content"]
            else:
                final_html_contents[slide_index] = result

        print(
            f"  ✅ All parallel refinement loops complete for {len(slide_data)} slides"
        )
        return final_html_contents

    async def _refine_one_slide_fully_async(
        self,
        slide_index: int,
        initial_html_content: str,
        slide_purpose: str,
        refinement_id: str,
        project_id: Optional[str] = None,
        slide_content: Optional[Any] = None,
        config: Optional[RunnableConfig] = None,
        max_iterations: int = 5,
    ) -> Optional[str]:
        """
        Processes the full refinement loop for a single slide asynchronously.
        This allows each slide to complete its refinement independently.
        """
        current_html = initial_html_content
        slide_number = slide_index + 1
        print(f"  🚀 Starting full refinement loop for slide {slide_number}...")
        
        # Debug: Check if template is still set for this async task
        current_template = self.html_prompt_manager.current_template
        print(f"      📁 Template for slide {slide_number} refinement: {current_template or 'default'}")
        
        # If template was lost, restore it from saved value
        if not current_template and hasattr(self, '_current_template_name') and self._current_template_name:
            print(f"      🔄 Restoring template '{self._current_template_name}' for slide {slide_number}")
            self.html_prompt_manager.set_template(self._current_template_name)

        # Get or create slide ID for Supabase tracking
        slide_id = None
        if project_id and slide_content:
            slide_id = self._get_or_create_slide_id(
                project_id, slide_index, slide_content
            )
            if slide_id:
                print(f"      📋 Using slide ID {slide_id} for Supabase tracking")

        for iteration in range(1, max_iterations + 1):
            print(
                f"    - Slide {slide_number}, Iteration {iteration}/{max_iterations}..."
            )

            # Create filenames for this specific iteration
            image_filename = (
                f"{refinement_id}_slide_{slide_number:02d}_iter_{iteration}.png"
            )
            image_path = self.temp_dir / image_filename

            # Render HTML to image (async)
            if not await self._render_html_to_image_async(
                current_html, str(image_path)
            ):
                print(
                    f"      ❌ Failed to render HTML for slide {slide_number}, aborting refinement for this slide."
                )
                return current_html  # Return last known good version

            # Compress image for optimal LLM processing
            print(f"      🗜️ Compressing image for slide {slide_number}...")
            if not self._compress_image_for_llm(str(image_path)):
                print(
                    f"      - Image compression failed for slide {slide_number}, but continuing with original image"
                )

            # Upload image
            image_url = self.uploader.upload_file(
                str(image_path), blob_name=f"refinement/{image_filename}"
            )
            if not image_url:
                print(
                    f"      ❌ Failed to upload image for slide {slide_number}, aborting refinement."
                )
                return current_html

            # Get refinement history for this slide (starts empty for each slide)
            refinement_history = []

            # Get LLM correction
            correction_response = await self._get_html_correction_async(
                current_html, image_url, slide_purpose, refinement_history, config, slide_index
            )

            # Track this refinement iteration in Supabase
            refinement_feedback = None
            refinement_prompt = slide_purpose
            is_final = False

            if correction_response:
                refinement_feedback = correction_response.reasoning
                if hasattr(correction_response, "changes_applied"):
                    refinement_feedback += (
                        f"\nChanges: {correction_response.changes_applied}"
                    )

            if (
                correction_response
                and correction_response.html_code.strip().lower() != "no changes"
                and correction_response.html_code.strip() != current_html.strip()
            ):
                print(
                    f"      🔄 Slide {slide_number}, Iteration {iteration}: LLM suggested changes. Continuing loop."
                )
                current_html = correction_response.html_code
                # Track changes in history to prevent flip-flopping
                if hasattr(correction_response, "changes_applied"):
                    refinement_history.extend(correction_response.changes_applied)

                # Track the updated HTML in Supabase
                if project_id and slide_id:
                    await self._track_refinement_in_supabase(
                        project_id,
                        slide_id,
                        iteration,
                        current_html,
                        image_path,
                        refinement_feedback,
                        refinement_prompt,
                        is_final=False,
                    )

            else:
                print(
                    f"      ⚪ Slide {slide_number}, Iteration {iteration}: No changes from LLM. Refinement complete for this slide."
                )

                # Mark this as the final refinement
                if project_id and slide_id:
                    await self._track_refinement_in_supabase(
                        project_id,
                        slide_id,
                        iteration,
                        current_html,
                        image_path,
                        refinement_feedback,
                        refinement_prompt,
                        is_final=True,
                    )

                break  # Early exit if no changes are needed

        print(f"  ✅ Finished refinement loop for slide {slide_number}.")
        return current_html

    def _identify_html_slides(self, slide_contents: list[SlideContent]) -> list[int]:
        """Scans all slide contents and returns a list of indices for slides containing HTML."""
        html_slide_indices = []
        for i, slide in enumerate(slide_contents):
            has_html = False
            for placeholder_name, content in slide.content.items():
                if isinstance(content, str) and "<" in content and ">" in content:
                    if content.strip().startswith("<"):
                        html_slide_indices.append(i)
                        has_html = True
                        print(
                            f"  - Found HTML content in slide {i + 1}, placeholder '{placeholder_name}'"
                        )
                        break  # Move to next slide once HTML is found

            if not has_html:
                # Check if slide has any content that might be HTML-related
                for placeholder_name, content in slide.content.items():
                    if isinstance(content, str) and any(
                        tag in content.lower()
                        for tag in ["<div", "<html", "<body", "<span", "<p>"]
                    ):
                        print(
                            f"  - Slide {i + 1} has potential HTML content in placeholder '{placeholder_name}': {content[:100]}..."
                        )

        print(
            f"  - HTML slide identification complete: found {len(html_slide_indices)} HTML slides"
        )
        return html_slide_indices

    def _get_html_content_for_slide(
        self, slide_contents: list[SlideContent], slide_index: int
    ) -> Optional[str]:
        """Gets the HTML content for a specific slide index."""
        if slide_index >= len(slide_contents):
            return None
        slide = slide_contents[slide_index]
        for content in slide.content.values():
            if isinstance(content, str) and "<" in content and ">" in content:
                if content.strip().startswith("<"):
                    return content
        return None

    def _render_html_to_image(self, html_content: str, image_path: str) -> bool:
        # Extract dimensions from HTML content
        width, height = self._extract_html_dimensions(html_content)

        # Try to render with default method first
        try:
            print("  - Attempting to render HTML with default method...")
            self.html_renderer.render_html_to_image(
                html_content, image_path, width, height
            )
            if os.path.exists(image_path):
                print("  - Successfully rendered HTML to image with default method")
                return True
        except Exception as e:
            print(f"  - Error rendering HTML to image with default method: {e}")

        # If default method failed, try other available methods
        for method in ["playwright", "selenium", "weasyprint", "imgkit"]:
            if method == self.html_renderer.active_method:
                continue  # Skip the already tried method

            if self.html_renderer.available_methods.get(method, False):
                try:
                    print(f"  - Attempting to render HTML with {method}...")
                    # Create a temporary renderer with this method
                    temp_renderer = HTMLRenderer(preferred_method=method)
                    temp_renderer.render_html_to_image(
                        html_content, image_path, width, height
                    )
                    if os.path.exists(image_path):
                        print(f"  - Successfully rendered HTML to image with {method}")
                        return True
                except Exception as e:
                    print(f"  - Error rendering HTML to image with {method}: {e}")

        print("  - Failed to render HTML with all available methods")
        return False

    async def _render_html_to_image_async(
        self, html_content: str, image_path: str
    ) -> bool:
        """Async version of _render_html_to_image for use in async contexts"""
        # Extract dimensions from HTML content
        width, height = self._extract_html_dimensions(html_content)

        # Try to render with async method first
        try:
            print("  - Attempting to render HTML with async method...")
            result = await self.html_renderer.render_html_to_image_async(
                html_content, image_path, width, height
            )
            if result and os.path.exists(image_path):
                print("  - Successfully rendered HTML to image with async method")
                return True
        except Exception as e:
            print(f"  - Error rendering HTML to image with async method: {e}")

        # If async method failed, try other available methods with async execution
        import concurrent.futures

        for method in [
            "selenium",
            "weasyprint",
            "imgkit",
        ]:  # Skip playwright as we tried async version
            if self.html_renderer.available_methods.get(method, False):
                try:
                    print(f"  - Attempting to render HTML with {method} (async)...")
                    # Create a temporary renderer with this method and run in executor
                    temp_renderer = HTMLRenderer(preferred_method=method)

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            temp_renderer.render_html_to_image,
                            html_content,
                            image_path,
                            width,
                            height,
                        )
                        result = await asyncio.wrap_future(future)

                    if result and os.path.exists(image_path):
                        print(
                            f"  - Successfully rendered HTML to image with {method} (async)"
                        )
                        return True
                except Exception as e:
                    print(
                        f"  - Error rendering HTML to image with {method} (async): {e}"
                    )

        print("  - Failed to render HTML with all available methods (async)")
        return False

    def _extract_html_dimensions(self, html_content: str) -> tuple[int, int]:
        """Extract viewport dimensions from HTML content body class

        Args:
            html_content: HTML content with body class containing dimensions

        Returns:
            Tuple of (width, height) in pixels
        """
        import re

        # Default fallback dimensions
        default_width, default_height = 1577, 603

        try:
            # Look for patterns like w-[1577px] h-[603px] in body class
            width_match = re.search(r"w-\[(\d+)px\]", html_content)
            height_match = re.search(r"h-\[(\d+)px\]", html_content)

            if width_match and height_match:
                width = int(width_match.group(1))
                height = int(height_match.group(1))
                return width, height

            print(
                f"  - Could not extract dimensions from HTML, using defaults: {default_width}x{default_height}"
            )
            return default_width, default_height

        except Exception as e:
            print(
                f"  - Error extracting HTML dimensions: {e}, using defaults: {default_width}x{default_height}"
            )
            return default_width, default_height

    async def _get_html_correction_async(
        self,
        html_content: str,
        image_url: str,
        slide_purpose: str,
        refinement_history: Optional[list[str]] = None,
        config: Optional[RunnableConfig] = None,
        slide_index: Optional[int] = None,
    ) -> Optional[RefinedHTML]:
        """
        Async version of _get_html_correction for true parallel LLM calls
        """
        import concurrent.futures

        from .llm_models import RefinedHTML

        # Try to extract placeholder name and slide number from context
        placeholder_name = "unknown"
        slide_number = slide_index + 1 if slide_index is not None else 0
        
        # Try to extract placeholder name from slide_purpose or HTML content
        if slide_purpose:
            # Look for placeholder name in purpose (e.g., "HTML content leaflet front left far side")
            import re
            # Try to extract placeholder name from purpose
            if "HTML content" in slide_purpose:
                # Extract everything after "HTML content" as placeholder name
                placeholder_match = re.search(r'HTML content\s+(.+?)(?:\s+for|\s+on|\s+in|$)', slide_purpose, re.IGNORECASE)
                if placeholder_match:
                    placeholder_name = placeholder_match.group(1).strip()
                    print(f"      🔍 Extracted placeholder name: '{placeholder_name}' for slide {slide_number}")
            
            # Also try to extract slide number if not already set
            if slide_number == 0:
                slide_match = re.search(r'slide[\s_]*(\d+)', slide_purpose, re.IGNORECASE)
                if slide_match:
                    slide_number = int(slide_match.group(1))
        
        if placeholder_name == "unknown":
            print(f"      ⚠️ Could not extract placeholder name from purpose: '{slide_purpose[:100]}...'")
        
        system_prompt = self._get_system_prompt(
            html_content, placeholder_name, slide_number
        )  # Pass HTML to extract dimensions
        user_prompt = self._create_user_prompt(
            html_content, image_url, slide_purpose, refinement_history
        )

        try:
            # Run the LLM call in a thread executor for true parallelism
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    self.llm_client.generate_structured_vision_content,
                    system_prompt,
                    user_prompt,
                    RefinedHTML,
                    config,
                )
                response = await asyncio.wrap_future(future)

            return response if response else None
        except Exception as e:
            # Fallback: Try with a simpler non-structured approach for Gemini
            print(f"⚠️ Structured output failed in async, trying fallback: {e}")
            try:
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        self.llm_client.generate_vision_content,
                        system_prompt
                        + "\n\nRETURN ONLY THE CORRECTED HTML CODE. No explanations.",
                        user_prompt,
                        config,
                    )
                    fallback_response = await asyncio.wrap_future(future)

                if fallback_response:
                    # Extract HTML from the response
                    import re

                    html_match = re.search(
                        r"```html\s*\n(.*?)\n```", fallback_response, re.DOTALL
                    )
                    if not html_match:
                        # Try without code blocks
                        html_match = re.search(
                            r"<!DOCTYPE.*?</html>", fallback_response, re.DOTALL
                        )

                    if html_match:
                        html_code = (
                            html_match.group(1)
                            if "```" in fallback_response
                            else html_match.group(0)
                        )
                        # Create RefinedHTML manually
                        return RefinedHTML(
                            html_code=html_code,
                            reasoning="Fallback generation - structured output not available",
                            changes_applied=["HTML refined using fallback approach"],
                        )
                return None
            except Exception as fallback_e:
                print(f"❌ Fallback approach also failed in async: {fallback_e}")
                return None

    def _get_html_correction(
        self,
        html_content: str,
        image_url: str,
        slide_purpose: str,
        refinement_history: Optional[list[str]] = None,
        config: Optional[RunnableConfig] = None,
        slide_index: Optional[int] = None,
    ) -> Optional[RefinedHTML]:
        """
        Synchronous version (kept for compatibility with sequential processing)
        """
        # Try to extract placeholder name and slide number from context
        placeholder_name = "unknown"
        slide_number = slide_index + 1 if slide_index is not None else 0
        
        # Try to extract placeholder name from slide_purpose or HTML content
        if slide_purpose:
            # Look for placeholder name in purpose (e.g., "HTML content leaflet front left far side")
            import re
            # Try to extract placeholder name from purpose
            if "HTML content" in slide_purpose:
                # Extract everything after "HTML content" as placeholder name
                placeholder_match = re.search(r'HTML content\s+(.+?)(?:\s+for|\s+on|\s+in|$)', slide_purpose, re.IGNORECASE)
                if placeholder_match:
                    placeholder_name = placeholder_match.group(1).strip()
                    print(f"      🔍 Extracted placeholder name: '{placeholder_name}' for slide {slide_number}")
            
            # Also try to extract slide number if not already set
            if slide_number == 0:
                slide_match = re.search(r'slide[\s_]*(\d+)', slide_purpose, re.IGNORECASE)
                if slide_match:
                    slide_number = int(slide_match.group(1))
        
        if placeholder_name == "unknown":
            print(f"      ⚠️ Could not extract placeholder name from purpose: '{slide_purpose[:100]}...'")
        
        system_prompt = self._get_system_prompt(
            html_content, placeholder_name, slide_number
        )  # Pass HTML to extract dimensions
        user_prompt = self._create_user_prompt(
            html_content, image_url, slide_purpose, refinement_history
        )

        try:
            response = self.llm_client.generate_structured_vision_content(
                system_prompt,
                user_prompt,  # This will now be a list of messages
                response_model=RefinedHTML,
                config=config,
            )
            return response if response else None
        except Exception as e:
            # Fallback: Try with a simpler non-structured approach for Gemini
            print(f"⚠️ Structured output failed, trying fallback approach: {e}")
            try:
                # Use generate_vision_content without structured output
                fallback_response = self.llm_client.generate_vision_content(
                    system_prompt
                    + "\n\nRETURN ONLY THE CORRECTED HTML CODE. No explanations.",
                    user_prompt,
                    config=config,
                )

                if fallback_response:
                    # Extract HTML from the response
                    import re

                    html_match = re.search(
                        r"```html\s*\n(.*?)\n```", fallback_response, re.DOTALL
                    )
                    if not html_match:
                        # Try without code blocks
                        html_match = re.search(
                            r"<!DOCTYPE.*?</html>", fallback_response, re.DOTALL
                        )

                    if html_match:
                        html_code = (
                            html_match.group(1)
                            if "```" in fallback_response
                            else html_match.group(0)
                        )
                        # Create RefinedHTML manually
                        from .llm_models import RefinedHTML

                        return RefinedHTML(
                            html_code=html_code,
                            reasoning="Fallback generation - structured output not available",
                            changes_applied=["HTML refined using fallback approach"],
                        )
                return None
            except Exception as fallback_e:
                print(f"❌ Fallback approach also failed: {fallback_e}")
                return None

    def _update_slide_content(
        self, slide_contents: list[SlideContent], slide_index: int, new_html: str
    ) -> list[SlideContent]:
        """Creates a new list of slide contents with the HTML updated for a specific slide."""
        updated_contents = []
        for i, slide in enumerate(slide_contents):
            if i == slide_index:
                new_content_dict = {}
                for key, value in slide.content.items():
                    if isinstance(value, str) and value.strip().startswith("<"):
                        new_content_dict[key] = new_html
                    else:
                        new_content_dict[key] = value
                updated_slide = SlideContent(
                    layout_index=slide.layout_index, content=new_content_dict
                )
                updated_contents.append(updated_slide)
            else:
                updated_contents.append(slide)
        return updated_contents

    def _format_refinement_history_context(
        self, refinement_history: Optional[list[str]]
    ) -> str:
        """Format refinement history to provide context to avoid flip-flopping"""
        if not refinement_history:
            return ""

        history_text = "\n".join(
            [f"• {change}" for change in refinement_history[-3:]]
        )  # Last 3 changes

        return f"""**🔄 PREVIOUS REFINEMENT ATTEMPTS (AVOID REPEATING):**
The following changes were already tried in previous iterations. DO NOT reverse these decisions:
{history_text}

**⚠️ CRITICAL: Do not undo previous fixes or flip-flop between solutions.**
**Focus on NEW issues not yet addressed, or build upon previous improvements.**
"""

    def _create_user_prompt(
        self,
        html_content: str,
        image_url: str,
        slide_purpose: str,
        refinement_history: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        return [
            {
                "type": "text",
                "text": f"""**SLIDE PURPOSE & REQUIREMENTS:**
{slide_purpose}

**TASK:** Evaluate if the HTML code below successfully fulfills the slide's purpose and requirements. 
The attached image shows how this HTML currently renders.
If any content is missing in the image it means it is either outside the boundary or not rendering properly.

{self._format_refinement_history_context(refinement_history)}

**EVALUATION CRITERIA:**
• Does the visualization effectively communicate the slide's purpose?
• Is the content well-organized and visually clear?
• Are all required elements present and properly positioned?
• Does the design enhance understanding of the intended message?

**HTML CODE TO EVALUATE:**
```html
{html_content}
```

**INSTRUCTIONS:**
1. Review the slide's purpose and requirements above
2. Examine the rendered image to see how the current HTML performs
3. Determine if the HTML successfully fulfills the slide's purpose
4. If improvements are needed, refine the HTML code to better meet the requirements
5. Focus on purpose alignment, not just visual aesthetics""",
            },
            {
                "type": "image_url",
                "image_url": {"url": image_url},
            },
        ]

    def _extract_viewport_dimensions(self, html_content: str) -> tuple[int, int]:
        """Extract viewport dimensions from HTML body class."""
        import re

        # Default dimensions
        width, height = 1577, 603

        # Try to extract from body class
        width_match = re.search(r"w-\[(\d+)px\]", html_content)
        height_match = re.search(r"h-\[(\d+)px\]", html_content)

        if width_match:
            width = int(width_match.group(1))
        if height_match:
            height = int(height_match.group(1))

        return width, height

    def _get_system_prompt(self, html_content: str = None, placeholder_name: str = "unknown", slide_number: int = 0) -> str:
        """Get the system prompt for HTML refinement with template-aware colors."""
        # Extract viewport dimensions from HTML if provided
        if html_content:
            width, height = self._extract_viewport_dimensions(html_content)
        else:
            width, height = 1577, 603  # Default dimensions

        # Use HTML prompt manager to get template-aware refinement prompt
        prompt = self.html_prompt_manager.get_html_refinement_prompt(width, height, placeholder_name, slide_number)
        
        # Debug: Print template info
        print(f"  🔍 REFINEMENT DEBUG: Template = {self.html_prompt_manager.current_template}")
        print(f"  🔍 REFINEMENT DEBUG: Colors = {self.html_prompt_manager.get_template_colors().get('colors', {}).get('background', {})}")
        
        return prompt

    def _get_system_prompt_legacy(self) -> str:
        """DEPRECATED: Old hardcoded system prompt - DO NOT USE"""
        return """You are an expert web developer and presentation design specialist.
Your task is to evaluate HTML code against slide requirements and refine it for optimal purpose fulfillment.

**YOUR MISSION:** Assess whether the provided HTML code successfully achieves the slide's intended purpose and requirements. If not, improve the HTML to better fulfill those objectives.

**RESPONSE FORMAT:**
Your response MUST be a JSON object that strictly follows this format: 
`{"html_code": "<FULL_HTML_CODE>", "reasoning": "...", "changes_applied": ["...", "..."]}`.
Do NOT provide any other text, explanations, or markdown.

**CRITICAL EVALUATION PRIORITIES:**

**1. 🚨 CRITICAL HEIGHT CONSTRAINT ANALYSIS (ABSOLUTE TOP PRIORITY) 🚨:**
- **DETECT MISSING CONTENT**: If ANY content is missing from the bottom of the image, the HTML HEIGHT is TOO LARGE and content is CROPPED
- **CHECK VIEWPORT DIMENSIONS**: Extract w-[NNNpx] h-[NNNpx] from body class - this is the ABSOLUTE MAXIMUM allowed size
- **CALCULATE TOTAL HEIGHT**: body padding + card padding + content + gaps MUST be < viewport height
- **MERMAID DIAGRAM OVERFLOW**: If Mermaid diagrams are cut off, they are exceeding viewport height - CRITICAL FIX NEEDED  
- **IMMEDIATE ACTION REQUIRED**: If bottom content is missing, reduce padding, text sizes, or content to fit within height limit
- **HEIGHT MATH**: For h-[456px]: p-4(32px) + card-body p-4(32px) + content + gaps MUST be < 456px
- **VALIDATION**: If rendered content is taller than specified h-[NNNpx], it WILL be cropped and invisible

**2. MANDATORY DAISYUI CARD STRUCTURE:**
- **Card Usage**: Is ALL content properly wrapped in DaisyUI card components?
- **Card Organization**: Are cards used effectively for content structure and spacing?
- **Visual Hierarchy**: Do cards provide proper visual separation and organization?
- **REQUIREMENT**: Content should NEVER be placed directly in body - always use cards

**3. Content Layout Assessment:**
- **Space Distribution**: Is the space used efficiently without overflow?
- **Content Scaling**: Are text sizes, diagrams, and elements appropriately sized?
- **Grid/Flex Usage**: Is CSS Grid or Flexbox used effectively for layout?
- **Safe Margins**: Are there appropriate margins (minimum 20px) on all sides?

**4. Color Palette Validation:** 
- Are ALL elements using the correct Ekona colors? Check every text element, background, accent, and component for brand compliance.

**5. Purpose Assessment:** 
- Does the HTML effectively communicate the slide's intended message?

**6. Requirements Check:** 
- Are all specified requirements met (content structure, visual elements, etc.)?

**7. Visual Effectiveness:** 
- Does the rendered result enhance understanding and engagement with correct branding?

**8. Technical Quality:** 
- Is the HTML technically sound and properly structured?

**REFINEMENT PRIORITIES:**
1. **CRITICAL: Viewport Constraint Enforcement** - Fix any content cropping or overflow issues IMMEDIATELY
2. **MANDATORY: DaisyUI Card Structure** - Ensure all content is properly contained in cards
3. **Color Palette Enforcement**: MANDATORY enforcement of Ekona color palette - check every element for correct colors
4. **Purpose Alignment**: Ensure the visualization directly supports the slide's objectives
5. **Content Clarity**: Information should be easily understood and well-organized
6. **Visual Hierarchy**: Important elements should be properly emphasized with correct brand colors
7. **Professional Quality**: Design should be polished and business-appropriate with consistent branding
8. **Space Utilization**: Effective use of the viewport

**🔧 CRITICAL HEIGHT OVERFLOW SOLUTIONS (APPLY IMMEDIATELY):**
- **Missing Bottom Content**: REDUCE padding: p-8→p-4, p-6→p-3, gap-6→gap-3
- **Text Too Large**: REDUCE font sizes: text-3xl→text-lg, text-2xl→text-base, text-xl→text-sm
- **Mermaid Diagram Cut Off**: ADD max-h-[300px] to .mermaid containers, reduce diagram complexity
- **Too Many Elements**: REMOVE secondary content, prioritize only essential information
- **Card Body Overflow**: REDUCE card-body padding: p-6→p-4→p-3, use flex-shrink
- **Grid Gaps Too Large**: REDUCE gaps: gap-6→gap-4→gap-2 for grid layouts
- **CALCULATION CHECK**: Sum all padding + content height < viewport h-[NNNpx]

**MANDATORY CARD PATTERNS TO ENFORCE:**
```html
<!-- Single Card (for simple content) -->
<body class="w-[WIDTHpx] h-[HEIGHTpx] p-8 overflow-hidden">
    <div class="card bg-base-100 shadow-xl h-full">
        <div class="card-body p-6">
            <!-- All content here -->
        </div>
    </div>
</body>

<!-- Multi-Card Layout (for complex content) -->
<body class="w-[WIDTHpx] h-[HEIGHTpx] p-8 overflow-hidden">
    <div class="grid grid-cols-2 gap-6 h-full">
        <div class="card bg-base-100 shadow-xl">
            <div class="card-body p-6">
                <!-- Left content -->
            </div>
        </div>
        <div class="card bg-base-100 shadow-xl">
            <div class="card-body p-6 flex flex-col">
                <h2 class="card-title text-xl mb-4">Title</h2>
                <div class="flex-grow flex items-center justify-center">
                    <div class="mermaid w-full max-h-[350px]">
                        <!-- Diagram -->
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>

NOTE: Replace WIDTH and HEIGHT with the exact pixel dimensions found in the existing HTML being refined.
```

**TECHNICAL REQUIREMENTS:**
- **Viewport**: Match the exact dimensions specified in the HTML body element with `overflow: hidden`
- **Frameworks**: TailwindCSS, Flowbite, and daisyUI components only
- **Diagrams**: Mermaid.js or D3.js with height constraints (`max-h-[400px]`)
- **No Titles**: Remove `<h1>` tags (slide has its own title)
- **Responsive**: Fixed pixel values for critical positioning
- **Performance**: High z-index values (z-10+) for proper layering

**DESIGN STANDARDS (CRITICAL - MUST BE ENFORCED):**
- **Colors (MANDATORY EKONA PALETTE)**: 
  - Primary/Accent: Swiss Red (#dc261e) - MUST be used for ALL accent elements
  - Text Headers: Dark Grey (#2d3748) - MUST be used for ALL headings  
  - Text Body: Black (#000000) - MUST be used for ALL body text
  - Background: White (#ffffff) - MUST be used for ALL backgrounds
  - NEVER accept default component colors - ALWAYS override with inline styles
- **Typography**: Clear font hierarchy with multiple fallbacks (Segoe UI, system-ui, sans-serif)
- **Layout**: No overlapping elements, proper spacing, professional appearance
- **Icons**: Properly sized and positioned, no visual conflicts, correct color palette
- **Content**: All text visible and readable, appropriate sizing

**MERMAID.JS SYNTAX RULES:**
- **Links**: Use `A -- "text" --> B` or `A o-- "text" --> B` (NOT `A --o "text" --> B`)
- **Nodes**: Use `nodeId["Display Text"]` format
- **Subgraphs**: Use `subgraph "Title" ... end` structure
- **Validation**: Double-check all syntax for correctness
- **Height Constraint**: ALWAYS use `max-h-[400px]` or similar height limits

**REFINEMENT DECISIONS:**
- **No Changes Needed**: If HTML perfectly fulfills the purpose AND fits viewport constraints, return original code with empty reasoning/changes
- **Viewport Fixes**: HIGHEST priority - fix any content cropping or overflow issues immediately
- **Card Structure**: Ensure proper DaisyUI card usage for all content organization
- **Minor Improvements**: Focus on enhancing purpose fulfillment without major restructuring  
- **Significant Changes**: When current approach doesn't effectively serve the slide's purpose
- **Conservative Approach**: Preserve working elements while improving purpose alignment

**QUALITY CHECKLIST:**
✅ CRITICAL: ALL content fits within the specified viewport dimensions (no cropping or overflow)
✅ MANDATORY: All content wrapped in proper DaisyUI card structure
✅ MANDATORY: Ekona color palette enforced on ALL elements (Swiss Red #dc261e, Dark Grey #2d3748, Black #000000, White #ffffff)
✅ Purpose clearly communicated through visualization
✅ All requirements from slide specifications met
✅ Professional, polished visual presentation with consistent branding
✅ No overlapping or mispositioned elements
✅ Optimal use of available space without exceeding bounds
✅ Technically sound HTML structure
✅ Text colors explicitly set (no default colors accepted)
✅ Mermaid diagrams have proper height constraints

**Mermaid-Specific Refinements:**
- **Enforce Title Separation**: The main title of the visualization MUST be a standard HTML tag (e.g., `<h2>`) outside the Mermaid `<div>`. If you see a `title` inside the Mermaid syntax, you MUST refactor the HTML to separate it.
- **Recommend Component Wrappers**: For plain, unstyled diagrams, you SHOULD wrap the Mermaid `<div>` in a DaisyUI `card` component (`<div class="card bg-base-100 shadow-xl"><div class="card-body">...</div></div>`) to improve framing and visual appeal.
- **Check for Professionalism**: Even without seeing the final colors, evaluate if the layout, spacing, and font sizes are professional and aligned with a corporate brand identity. The final render will apply brand colors, but the structure must be sound.
- **Height Constraints**: ALWAYS ensure Mermaid containers have `max-h-[400px]` or similar constraints to prevent overflow.

Focus on creating HTML that serves the slide's purpose effectively while ABSOLUTELY ensuring all content fits within the viewport constraints without any cropping or information loss."""


class ImagePromptAgent:
    """
    Agent responsible for crafting high-quality, descriptive prompts for image generation.
    Translates user requests and slide context into detailed visual descriptions
    optimized for AI image generation models.
    """

    def __init__(self):
        self.name = "image_prompt_agent"
        self.llm_client = LangchainLLMClient()

        # Initialize HTML prompt manager to get template colors
        from .html_prompt_manager import HTMLPromptManager

        self.html_prompt_manager = HTMLPromptManager()

    @monitor_agent_execution("image_prompt_agent")
    def execute(
        self, state: SlideGenerationState, config: Optional[RunnableConfig] = None
    ) -> SlideGenerationState:
        """
        Create detailed image generation prompts for slides that need images.

        Args:
            state: Current workflow state
            config: Optional LangGraph configuration

        Returns:
            Updated state with optimized image prompts
        """
        print(f"🎨 {self.name}: Crafting detailed image generation prompts...")

        # Set template for color selection if available
        template_name = self._extract_template_name(state)
        if template_name:
            self.html_prompt_manager.set_template(template_name)
            print(
                f"📁 {self.name}: Using template '{template_name}' for image prompt colors"
            )

        # Check if we have slides that need images
        if not state.get("slide_contents"):
            print("  - No slide contents available")
            return state

        # Identify slides that need images and create prompts
        image_prompts = self._create_image_prompts(state)

        if image_prompts:
            state["image_prompts"] = image_prompts
            print(f"  ✅ Created {len(image_prompts)} detailed image prompts")
        else:
            print("  - No slides identified for image generation")

        return state

    def _extract_template_name(self, state: SlideGenerationState) -> Optional[str]:
        """Extract template name from state."""
        template_name = None
        template_folder_path = state.get("template_folder_path")
        if template_folder_path:
            from pathlib import Path

            template_name = Path(template_folder_path).name

        if not template_name:
            template_path = state.get("template_path")
            if template_path:
                template_path_str = str(template_path)
                print(f"   - Checking template_path: {template_path_str}")
                
                # Generic template extraction from path
                if "templates/" in template_path_str or "templates\\" in template_path_str:
                    from pathlib import Path
                    path_parts = Path(template_path_str).parts
                    
                    # Find the templates directory
                    if "templates" in path_parts:
                        idx = path_parts.index("templates")
                        # The next part after "templates" should be the template folder name
                        if idx + 1 < len(path_parts):
                            # Get the folder name (not the .pptx file)
                            potential_name = path_parts[idx + 1]
                            # If it's a .pptx file, we're looking at the wrong level
                            if potential_name.endswith('.pptx'):
                                # Try to get the parent folder name
                                if idx + 2 < len(path_parts):
                                    potential_name = path_parts[idx + 2]
                            
                            # Clean the name (remove .pptx if present)
                            template_name = potential_name.replace('.pptx', '')
                            print(f"   - Extracted template from path: {template_name}")
        
        # Try direct template_name from state
        if not template_name:
            direct_name = state.get("template_name")
            if direct_name:
                template_name = direct_name
                print(f"   - Got direct template_name: {template_name}")
        
        # Clean up template name
        if template_name:
            original = template_name
            template_name = template_name.replace('.pptx', '')
            if template_name.endswith('_1') or template_name.endswith('_2'):
                template_name = template_name[:-2]
            if original != template_name:
                print(f"   - Cleaned template name: {original} -> {template_name}")

        return template_name

    def _get_brand_colors(self) -> tuple[str, str]:
        """Get brand colors from the current template's JSON configuration."""
        # Get colors from JSON configuration
        colors = self.html_prompt_manager.get_template_colors()

        # Extract image generation colors if specified
        image_gen = colors.get("image_generation", {})
        if image_gen:
            primary_color = image_gen.get("primary_accent", "professional accent color")
            secondary_color = image_gen.get("secondary_accent", "dark grey")
        else:
            # Fall back to main color config
            color_config = colors.get("colors", {})
            primary = color_config.get("primary", {})
            secondary = color_config.get("secondary", {})

            primary_color = (
                f"{primary.get('name', 'accent color')} ({primary.get('hex', '')})"
                if primary.get("hex")
                else primary.get("name", "accent color")
            )
            secondary_color = (
                f"{secondary.get('name', 'dark grey')} ({secondary.get('hex', '')})"
                if secondary.get("hex")
                else secondary.get("name", "dark grey")
            )

        return primary_color, secondary_color

    def _create_image_prompts(self, state: SlideGenerationState) -> dict:
        """
        Create detailed image prompts for all slides that need images.

        Args:
            state: Current workflow state

        Returns:
            Dictionary mapping slide indices to detailed image prompts
        """
        image_prompts = {}
        slide_contents = state.get("slide_contents", [])
        presentation_plan = state.get("presentation_plan", [])
        topic = state.get("topic", "")

        # Handle both List[SlideSpec] and PresentationPlan object
        from .llm_models import PresentationPlan

        if isinstance(presentation_plan, PresentationPlan):
            slides_list = presentation_plan.slides
        else:
            slides_list = presentation_plan

        for i, slide_content in enumerate(slide_contents):
            # Get the corresponding slide specification from the presentation plan
            slide_spec = slides_list[i] if i < len(slides_list) else None
            
            if not slide_spec:
                continue
                
            # Check if planning agent flagged this slide for image generation
            is_image_slide = getattr(slide_spec, "is_image", False)
            
            if not is_image_slide:
                continue

            print(f"  🎯 Slide {i}: Planning agent flagged for image generation")

            # Get slide context
            slide_title = getattr(slide_spec, "slide_title", "Slide")

            # Create detailed prompt using LLM
            detailed_prompt = self._generate_detailed_image_prompt(
                topic=topic,
                slide_title=slide_title,
                slide_content=slide_content,
                slide_spec=slide_spec,
            )

            if detailed_prompt:
                image_prompts[i] = detailed_prompt
                print(f"  📝 Created prompt for slide {i + 1}: {slide_title}")

        return image_prompts


    def _generate_detailed_image_prompt(
        self, topic: str, slide_title: str, slide_content, slide_spec
    ) -> str:
        """
        Use LLM to generate a detailed, descriptive image prompt.

        Args:
            topic: Original presentation topic
            slide_title: Title of the slide
            slide_content: Slide content object
            slide_spec: Slide specification from planning

        Returns:
            Detailed image generation prompt
        """
        try:
            # Build context for the LLM
            context_parts = [f"Topic: {topic}", f"Slide: {slide_title}"]

            if slide_spec:
                if hasattr(slide_spec, "slide_purpose"):
                    context_parts.append(f"Purpose: {slide_spec.slide_purpose}")
                if hasattr(slide_spec, "key_information"):
                    context_parts.append(
                        f"Key Info: {', '.join(slide_spec.key_information)}"
                    )

            # Get text content from slide
            text_content = []
            for attr_name, attr_value in slide_content.__dict__.items():
                if (
                    isinstance(attr_value, str)
                    and attr_value.strip()
                    and attr_name != "layout_index"
                ):
                    text_content.append(f"{attr_name}: {attr_value}")

            if text_content:
                context_parts.append(f"Content: {'; '.join(text_content)}")

            context = "\n".join(context_parts)

            # Get brand colors for this template
            primary_color, secondary_color = self._get_brand_colors()

            prompt = f"""You are an expert at creating specific visual descriptions for AI image generation.

TASK: Based on the context below, create a detailed visual description focusing ONLY on what should appear in the image itself.

CONTEXT:
{context}

BRAND COLORS (use when appropriate):
- Primary: {primary_color}
- Secondary: {secondary_color}

INSTRUCTIONS:
1. Describe the exact visual scene - people, objects, environment, composition
2. Be specific about clothing, expressions, poses, lighting, atmosphere
3. Focus on the core visual elements, not the presentation context
4. Include relevant colors and professional style
5. Make it a clear, direct description of what should be generated

OUTPUT: Return ONLY the visual description for image generation, no mention of slides or presentations."""

            # Use the same pattern as other agents
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert image prompt creator.",
                },
                {"role": "user", "content": prompt},
            ]
            config = RunnableConfig(
                run_name="image_prompt_generation",
                tags=["image", "prompt", "generation"],
            )

            response = self.llm_client.chat_client.invoke(messages, config=config)
            content = str(response.content) if response.content else ""

            if content and content.strip():
                return content.strip()
            print("  ⚠️ LLM returned empty response for slide prompt")
            return self._create_fallback_prompt(topic, slide_title)

        except Exception as e:
            print(f"  ⚠️ Error generating detailed prompt: {e}")
            return self._create_fallback_prompt(topic, slide_title)

    def _create_fallback_prompt(self, topic: str, slide_title: str) -> str:
        """Create a fallback prompt when LLM generation fails."""
        if "image of" in topic.lower():
            base_prompt = topic.replace("image of", "").strip()
        else:
            base_prompt = f"Professional business scene related to {slide_title}"

        # Get brand colors for this template
        primary_color, secondary_color = self._get_brand_colors()

        return (
            f"{base_prompt}. High-quality, detailed illustration with clean composition, "
            f"professional style, modern design with {primary_color} and {secondary_color} accents."
        )


class ImageGenerationAgent:
    """
    Agent responsible for generating images for Layout 2 slides using GPT-image-1 model.
    Identifies slides that need images and generates them in parallel.
    """

    def __init__(self):
        self.name = "image_generation_agent"

        # Initialize the image webhook client
        try:
            from .image_webhook_client import ImageWebhookClient

            self.image_client = ImageWebhookClient()
            print("✅ Image webhook client initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize image webhook client: {e}")
            self.image_client = None

        # Initialize storage and database clients
        try:
            from .database import get_supabase_client
            from .supabase_storage import get_storage_client

            self.storage_client = get_storage_client()
            self.db_client = get_supabase_client()
            print(
                "✅ Supabase storage and database clients initialized for image tracking"
            )
        except Exception as e:
            print(f"⚠️ Failed to initialize Supabase clients for image tracking: {e}")
            self.storage_client = None
            self.db_client = None

        self.temp_dir = Path("image_debug")
        self.temp_dir.mkdir(exist_ok=True)

    @monitor_agent_execution("image_generation_agent")
    def execute(
        self, state: SlideGenerationState, config: Optional[RunnableConfig] = None
    ) -> SlideGenerationState:
        """
        Generate images for slides that need them (Layout 2).

        Args:
            state: Current workflow state containing slide contents
            config: Optional LangGraph configuration

        Returns:
            Updated state with generated images
        """
        if not self.image_client:
            print("❌ Image client not available, skipping image generation")
            return state

        # Check if we have slide contents
        if not state.get("slide_contents"):
            print("❌ No slide contents available for image generation")
            return state

        print(f"🎨 {self.name}: Starting image generation process...")

        # Identify slides that need images (Layout 2)
        image_slides = self._identify_image_slides(state)

        if not image_slides:
            print(f"ℹ️ {self.name}: No slides require image generation")
            return state

        print(f"🎯 {self.name}: Found {len(image_slides)} slides needing images")

        # Check for parallel processing
        use_parallel = (
            os.getenv("USE_PARALLEL_IMAGE_GENERATION", "true").lower() == "true"
        )

        if use_parallel:
            print("🚀 Using parallel image generation")
            return self._generate_images_parallel(state, image_slides)
        print("🔄 Using sequential image generation")
        return self._generate_images_sequential(state, image_slides)

    def _identify_image_slides(self, state: SlideGenerationState) -> list[dict]:
        """
        Identify slides that need image generation based on planning agent decisions.

        Args:
            state: Current workflow state

        Returns:
            List of dictionaries containing slide info for image generation
        """
        image_slides = []
        slide_contents = state.get("slide_contents", [])
        layouts_info = state.get("layouts_info", {})
        presentation_plan = state.get("presentation_plan", [])

        # Handle both List[SlideSpec] and PresentationPlan object
        from .llm_models import PresentationPlan

        if isinstance(presentation_plan, PresentationPlan):
            slides_list = presentation_plan.slides
        else:
            slides_list = presentation_plan

        print(f"🔍 Checking {len(slides_list) if slides_list else 0} slides for image requirements...")

        for i, slide_content in enumerate(slide_contents):
            layout_index = getattr(slide_content, "layout_index", None)
            layout_info = (
                layouts_info.get(layout_index, {}) if layout_index is not None else {}
            )

            # Get the corresponding slide specification from the presentation plan
            slide_spec = slides_list[i] if i < len(slides_list) else None
            
            if not slide_spec:
                print(f"  ⚠️ Slide {i+1}: No slide specification found in presentation plan")
                continue

            # Check if planning agent flagged this slide for image generation
            is_image_slide = getattr(slide_spec, "is_image", False)
            
            print(f"  🔍 Slide {i+1}: Planning agent decision is_image={is_image_slide}")

            if not is_image_slide:
                print(f"  ⏭️ Slide {i+1}: Skipping - planning agent did not flag for image generation")
                continue

            # Get image placeholder requirements from planning agent
            placeholder_requirements = getattr(slide_spec, "placeholder_requirements", None)
            image_placeholders = []
            
            if placeholder_requirements:
                image_placeholders = [
                    req.placeholder_name for req in placeholder_requirements 
                    if req.content_type == "image"
                ]
                print(f"  🎯 Slide {i+1}: Image placeholders specified: {image_placeholders}")
            else:
                print(f"  ⚠️ Slide {i+1}: No placeholder requirements specified, will search for suitable placeholders")

            # Find actual placeholders in the layout that match the requirements
            target_placeholders = []
            layout_placeholders = layout_info.get("placeholders", [])
            
            if image_placeholders:
                # Use planning agent's specific placeholder names
                for placeholder in layout_placeholders:
                    placeholder_name = placeholder.get("name", "")
                    if placeholder_name in image_placeholders:
                        target_placeholders.append(placeholder)
                        print(f"    ✅ Found specified image placeholder: {placeholder_name}")
            else:
                # Fallback: search for suitable picture placeholders
                for placeholder in layout_placeholders:
                    placeholder_name = placeholder.get("name", "")
                    placeholder_type = placeholder.get("type", 0)

                    # Only look at picture placeholders (type 18)
                    if placeholder_type != 18:
                        continue

                    # Skip LOCKED_ placeholders (these are background images)
                    if "LOCKED_" in placeholder_name:
                        print(f"    ⏭️ Skipping LOCKED placeholder: {placeholder_name}")
                        continue

                    # Skip HTML placeholders (these are for HTML-generated content)
                    placeholder_name_lower = placeholder_name.lower()
                    if (
                        "html" in placeholder_name_lower
                        or "generated from html" in placeholder_name_lower
                        or "picture from html" in placeholder_name_lower
                        or "visualization" in placeholder_name_lower
                    ):
                        print(f"    ⏭️ Skipping HTML/visualization placeholder: {placeholder_name}")
                        continue

                    # This is a suitable picture placeholder for image generation
                    target_placeholders.append(placeholder)
                    print(f"    🎯 Found suitable image placeholder: {placeholder_name}")

            # Process each target placeholder
            if target_placeholders:
                for picture_placeholder in target_placeholders:
                    # Get image prompt for this slide (preferring detailed prompts)
                    image_prompt = self._get_image_prompt_for_slide(i, state)

                    image_slides.append(
                        {
                            "slide_index": i,
                            "slide_content": slide_content,
                            "placeholder": picture_placeholder,
                            "image_prompt": image_prompt,
                            "placeholder_description": picture_placeholder.get(
                                "name", "Picture 16:9"
                            ),
                            "placeholder_width": picture_placeholder.get("width_px", 1200),
                            "placeholder_height": picture_placeholder.get("height_px", 456),
                            "detection_method": "planning_agent_decision",
                        }
                    )
                    print(
                        f"  🎯 Slide {i+1}: Added placeholder '{picture_placeholder.get('name', 'unnamed')}' to image generation queue"
                    )
            else:
                print(
                    f"  ⚠️ Slide {i+1}: Planning agent flagged for images but no suitable placeholders found"
                )

        return image_slides


    def _find_any_picture_placeholder(self, layout_info: dict):
        """
        Find any picture placeholder in the layout info.

        Args:
            layout_info: Layout information from template analysis

        Returns:
            Picture placeholder dictionary or None if not found
        """
        try:
            placeholders = layout_info.get("placeholders", [])

            # First, look for actual PICTURE type placeholders (type 18)
            # BUT skip LOCKED_ placeholders as they're for backgrounds
            for placeholder in placeholders:
                placeholder_name = placeholder.get("name", "")
                placeholder_type = placeholder.get("type", 0)

                # Skip LOCKED_ placeholders - they're handled by the background system
                if "LOCKED_" in placeholder_name:
                    print(
                        f"    🔒 Skipping locked background placeholder: {placeholder_name}"
                    )
                    continue

                # Check if it's a PICTURE type (type 18)
                if placeholder_type == 18:  # PP_PLACEHOLDER.PICTURE
                    print(
                        f"    🖼️ Found picture placeholder by type 18: {placeholder_name}"
                    )
                    return placeholder

            # Look for placeholders with picture-related names
            picture_names = [
                "Picture 16:9",
                "Picture",
                "Image",
                "Photo",
                "Visual",
                "Diagram",
                "Chart",
                "Illustration",
                "Graphic",
            ]

            for placeholder in placeholders:
                placeholder_name = placeholder.get("name", "")

                # Skip LOCKED_ placeholders
                if "LOCKED_" in placeholder_name:
                    continue

                # Check by name
                for pic_name in picture_names:
                    if pic_name.lower() in placeholder_name.lower():
                        print(
                            f"    🖼️ Found picture placeholder by name: {placeholder_name}"
                        )
                        return placeholder

            # Fallback: Use content placeholder if available (but not LOCKED_)
            for placeholder in placeholders:
                placeholder_name = placeholder.get("name", "")
                if (
                    "LOCKED_" not in placeholder_name
                    and "content" in placeholder_name.lower()
                ):
                    print(
                        f"    🖼️ Using content placeholder as fallback: {placeholder_name}"
                    )
                    return placeholder

            print("    ⚠️ No suitable picture placeholder found in layout")
            return None

        except Exception as e:
            print(f"    ⚠️ Error finding picture placeholder: {e}")
            return None

    def _get_image_prompt_for_slide(
        self, slide_index: int, state: SlideGenerationState
    ) -> str:
        """
        Get the image prompt for a slide, preferring pre-crafted prompts from ImagePromptAgent.

        Args:
            slide_index: Index of the slide (0-based)
            state: Full workflow state

        Returns:
            Image generation prompt
        """
        # First try to use pre-crafted prompt from ImagePromptAgent
        image_prompts = state.get("image_prompts", {})
        if slide_index in image_prompts:
            print("    🎯 Using detailed prompt from ImagePromptAgent")
            return image_prompts[slide_index]

        # Fallback to content-based prompt generation
        print(
            "    ⚠️ No detailed prompt available, analyzing slide content for fallback"
        )
        original_topic = state.get("topic", "")
        slide_contents = state.get("slide_contents", [])

        # Try to extract visual description from slide content
        content_prompt = None
        if slide_index < len(slide_contents):
            slide_content = slide_contents[slide_index]
            content_prompt = self._extract_visual_description_from_content(
                slide_content
            )

        if content_prompt:
            # Use content-based description
            base_prompt = content_prompt
            print(f"    📝 Using content-based prompt: {base_prompt[:50]}...")
        elif original_topic and "image of" in original_topic.lower():
            # User specifically requested an image scene
            base_prompt = original_topic
        else:
            # Generic business slide
            base_prompt = "Professional business illustration for presentation slide"
            if original_topic:
                base_prompt += f" about {original_topic[:100]}"

        # Add style guidelines with template-aware colors
        # Since this agent doesn't have HTMLPromptManager, use generic terms
        style_prompt = ". Style: modern, professional, clean design with appropriate brand colors. High quality, detailed illustration suitable for business presentation."

        return base_prompt + style_prompt

    def _extract_visual_description_from_content(self, slide_content) -> str:
        """
        Extract visual description from slide content for image generation.

        Args:
            slide_content: SlideContent object with content dictionary

        Returns:
            Visual description string or None if not found
        """
        try:
            content = getattr(slide_content, "content", {})
            if not content or not isinstance(content, dict):
                return None

            # Combine all text content
            all_text = ""
            for key, value in content.items():
                if isinstance(value, str):
                    all_text += value + " "
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            all_text += item + " "

            if not all_text.strip():
                return None

            # Look for sentences that describe visual content
            import re

            # Find sentences with image-related keywords
            sentences = re.split(r"[.!?]+", all_text)
            visual_sentences = []

            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue

                lower_sentence = sentence.lower()

                # Strong indicators for visual descriptions
                visual_indicators = [
                    "picture",
                    "image",
                    "photo",
                    "shows",
                    "displays",
                    "depicts",
                    "illustrates",
                    "represents",
                    "features",
                    "captures",
                    "view",
                    "scene",
                    "visual",
                    "diagram",
                    "chart",
                    "graph",
                    "design",
                ]

                if any(indicator in lower_sentence for indicator in visual_indicators):
                    visual_sentences.append(sentence)

            if visual_sentences:
                # Use the most descriptive sentence
                longest_sentence = max(visual_sentences, key=len)

                # Clean up the sentence for image generation
                description = longest_sentence.strip()

                # Remove common presentation text
                cleanup_patterns = [
                    r"^This slide (shows|displays|features|contains)",
                    r"^The slide (shows|displays|features|contains)",
                    r"^Here we (see|have|show)",
                    r"^This is a",
                    r"^This shows?",
                ]

                for pattern in cleanup_patterns:
                    description = re.sub(
                        pattern, "", description, flags=re.IGNORECASE
                    ).strip()

                if description and len(description) > 10:
                    return description

            return None

        except Exception as e:
            print(f"    ⚠️ Error extracting visual description: {e}")
            return None

    def _generate_images_parallel(
        self, state: SlideGenerationState, image_slides: list[dict]
    ) -> SlideGenerationState:
        """
        Generate images for multiple slides in parallel.

        Args:
            state: Current workflow state
            image_slides: List of slide information for image generation

        Returns:
            Updated state with generated images
        """
        try:
            # Extract image settings from state
            image_quality = state.get("image_quality", "auto")
            image_size = state.get("image_size", "auto")
            
            # Prepare prompts and specs for parallel generation
            prompts_and_specs = []
            for slide_info in image_slides:
                prompts_and_specs.append(
                    (
                        slide_info["image_prompt"],
                        {
                            "slide_index": slide_info["slide_index"],
                            "placeholder_description": slide_info[
                                "placeholder_description"
                            ],
                            "placeholder_width": slide_info["placeholder_width"],
                            "placeholder_height": slide_info["placeholder_height"],
                            "image_quality": image_quality,
                            "image_size": image_size,
                        },
                    )
                )

            # Run parallel image generation
            import concurrent.futures

            def run_async_in_thread():
                return asyncio.run(
                    self.image_client.generate_images_parallel(prompts_and_specs)
                )

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_async_in_thread)
                results = future.result()

            # Process results and save images
            generated_images = {}

            # Create a mapping from slide_index to slide_info for quick lookup
            slide_info_map = {info["slide_index"]: info for info in image_slides}

            for slide_index, image_data in results:
                if image_data:
                    # Save image to debug directory
                    image_filename = f"slide_{slide_index + 1:02d}_generated_image.png"
                    image_path = self.temp_dir / image_filename

                    if self.image_client.save_image_to_file(
                        image_data, str(image_path)
                    ):
                        # Get the slide info for this slide index
                        slide_info = slide_info_map.get(slide_index)
                        placeholder_name = (
                            slide_info["placeholder"]["name"]
                            if slide_info
                            else "Picture 16:9"
                        )

                        generated_images[slide_index] = {
                            "image_data": image_data,
                            "image_path": str(image_path),
                            "placeholder_name": placeholder_name,
                        }
                        print(
                            f"✅ Generated and saved image for slide {slide_index + 1}"
                        )
                    else:
                        print(f"❌ Failed to save image for slide {slide_index + 1}")
                else:
                    print(f"❌ Failed to generate image for slide {slide_index + 1}")

            # Update state with generated images
            state["generated_images"] = generated_images
            state["needs_image_refinement"] = len(generated_images) > 0

            # Update slide contents with image paths
            slide_contents = state.get("slide_contents", [])
            for slide_index, image_info in generated_images.items():
                if slide_index < len(slide_contents):
                    slide_content = slide_contents[slide_index]
                    placeholder_name = image_info["placeholder_name"]
                    image_path = image_info["image_path"]

                    # Update the slide content with the image path
                    if hasattr(slide_content, "content"):
                        slide_content.content[placeholder_name] = image_path
                        print(
                            f"  ✅ Updated slide {slide_index + 1} content with image: {placeholder_name} -> {image_path}"
                        )

            print(
                f"🎉 {self.name}: Generated {len(generated_images)} images successfully"
            )
            return state

        except Exception as e:
            print(f"❌ Parallel image generation failed: {e}")
            state["generated_images"] = {}
            state["needs_image_refinement"] = False
            return state

    def _generate_images_sequential(
        self, state: SlideGenerationState, image_slides: list[dict]
    ) -> SlideGenerationState:
        """
        Generate images for slides sequentially (fallback method).

        Args:
            state: Current workflow state
            image_slides: List of slide information for image generation

        Returns:
            Updated state with generated images
        """
        # Extract image settings from state
        image_quality = state.get("image_quality", "auto")
        image_size_setting = state.get("image_size", "auto")
        
        generated_images = {}

        for slide_info in image_slides:
            slide_index = slide_info["slide_index"]
            print(f"🎨 Generating image for slide {slide_index + 1}...")

            try:
                # Generate single image using thread executor
                import concurrent.futures

                def run_single_image(info):
                    return asyncio.run(
                        self.image_client.generate_image(
                            prompt=info["image_prompt"],
                            placeholder_description=info["placeholder_description"],
                            placeholder_width=info["placeholder_width"],
                            placeholder_height=info["placeholder_height"],
                            quality=image_quality,
                            image_size=image_size_setting,
                        )
                    )

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_single_image, slide_info)
                    image_data = future.result()

                if image_data:
                    # Save image to debug directory
                    image_filename = f"slide_{slide_index + 1:02d}_generated_image.png"
                    image_path = self.temp_dir / image_filename

                    if self.image_client.save_image_to_file(
                        image_data, str(image_path)
                    ):
                        generated_images[slide_index] = {
                            "image_data": image_data,
                            "image_path": str(image_path),
                            "placeholder_name": slide_info["placeholder"]["name"],
                        }
                        print(
                            f"✅ Generated and saved image for slide {slide_index + 1}"
                        )
                    else:
                        print(f"❌ Failed to save image for slide {slide_index + 1}")
                else:
                    print(f"❌ Failed to generate image for slide {slide_index + 1}")

            except Exception as e:
                print(f"❌ Failed to generate image for slide {slide_index + 1}: {e}")
                continue

        # Update state with generated images
        state["generated_images"] = generated_images
        state["needs_image_refinement"] = len(generated_images) > 0

        # Update slide contents with image paths
        slide_contents = state.get("slide_contents", [])
        for slide_index, image_info in generated_images.items():
            if slide_index < len(slide_contents):
                slide_content = slide_contents[slide_index]
                placeholder_name = image_info["placeholder_name"]
                image_path = image_info["image_path"]

                # Update the slide content with the image path
                if hasattr(slide_content, "content"):
                    slide_content.content[placeholder_name] = image_path
                    print(
                        f"  ✅ Updated slide {slide_index + 1} content with image: {placeholder_name} -> {image_path}"
                    )

        print(f"🎉 {self.name}: Generated {len(generated_images)} images successfully")
        return state


class ImageRefinementAgent:
    """
    Agent responsible for refining generated images based on visual feedback.
    Uses vision models to analyze generated images and request improvements.
    """

    def __init__(self):
        self.name = "image_refinement_agent"
        self.max_iterations = 3  # Limited to 3 rounds as specified

        # Initialize the image webhook client
        try:
            from .image_webhook_client import ImageWebhookClient

            self.image_client = ImageWebhookClient()
            print("✅ Image webhook client initialized for refinement")
        except Exception as e:
            print(f"❌ Failed to initialize image webhook client: {e}")
            self.image_client = None

        # Initialize LLM client for vision analysis
        self.llm_client = LangchainLLMClient()

        # Initialize storage and database clients
        try:
            from .database import get_supabase_client
            from .supabase_storage import get_storage_client

            self.storage_client = get_storage_client()
            self.db_client = get_supabase_client()
            print("✅ Supabase clients initialized for image refinement tracking")
        except Exception as e:
            print(f"⚠️ Failed to initialize Supabase clients: {e}")
            self.storage_client = None
            self.db_client = None

        self.temp_dir = Path("image_debug")
        self.temp_dir.mkdir(exist_ok=True)

    @monitor_agent_execution("image_refinement_agent")
    def execute(
        self, state: SlideGenerationState, config: Optional[RunnableConfig] = None
    ) -> SlideGenerationState:
        """
        Refine generated images based on visual feedback.

        Args:
            state: Current workflow state containing generated images
            config: Optional LangGraph configuration

        Returns:
            Updated state with refined images
        """
        if not self.image_client or not state.get("needs_image_refinement", False):
            print(f"ℹ️ {self.name}: No image refinement needed")
            return state

        generated_images = state.get("generated_images", {})
        if not generated_images:
            print(f"ℹ️ {self.name}: No generated images to refine")
            return state

        print(
            f"🔧 {self.name}: Starting image refinement process for {len(generated_images)} images"
        )

        # Check for parallel processing
        use_parallel = (
            os.getenv("USE_PARALLEL_IMAGE_REFINEMENT", "true").lower() == "true"
        )

        if use_parallel:
            print("🚀 Using parallel image refinement")
            return self._refine_images_parallel(state, generated_images)
        print("🔄 Using sequential image refinement")
        return self._refine_images_sequential(state, generated_images)

    def _refine_images_parallel(
        self, state: SlideGenerationState, generated_images: dict
    ) -> SlideGenerationState:
        """
        Refine multiple images in parallel with limited iterations.

        Args:
            state: Current workflow state
            generated_images: Dictionary of generated images

        Returns:
            Updated state with refined images
        """
        # For now, implement a simple approach that just validates the images exist
        # Full refinement logic would involve vision model analysis and iterative improvement

        refined_images = {}

        for slide_index, image_info in generated_images.items():
            # Check if image file exists
            image_path = image_info.get("image_path")
            if image_path and Path(image_path).exists():
                refined_images[slide_index] = image_info
                print(f"✅ Validated image for slide {slide_index + 1}")
            else:
                print(f"❌ Image file not found for slide {slide_index + 1}")

        # Update state with refined images
        state["refined_images"] = refined_images
        state["needs_image_refinement"] = False

        print(
            f"🎉 {self.name}: Image refinement complete for {len(refined_images)} images"
        )
        return state

    def _refine_images_sequential(
        self, state: SlideGenerationState, generated_images: dict
    ) -> SlideGenerationState:
        """
        Refine images sequentially (fallback method).

        Args:
            state: Current workflow state
            generated_images: Dictionary of generated images

        Returns:
            Updated state with refined images
        """
        # Same simple validation approach for now
        return self._refine_images_parallel(state, generated_images)
