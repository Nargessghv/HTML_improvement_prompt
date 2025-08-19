"""
HTML Prompt Management System

This module manages HTML generation prompts with support for template-specific
customizations, allowing each PowerPoint template to have its own HTML prompt variants.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any, Union
from .simple_debug import save_prompt_debug


class HTMLPromptManager:
    """
    Manages HTML content generation prompts with template-specific overrides.
    
    Supports a two-tier system:
    1. Default HTML prompts - always available as fallback
    2. Template-specific HTML prompts - override defaults when a template is selected
    """

    def __init__(self, default_prompts_dir: str = "html_prompts", templates_dir: str = "templates"):
        """
        Initialize the HTML prompt manager.
        
        Args:
            default_prompts_dir: Directory for default HTML prompts
            templates_dir: Directory containing PowerPoint templates and their HTML prompts
        """
        self.default_prompts_dir = Path(default_prompts_dir)
        self.templates_dir = Path(templates_dir)
        
        # Create default prompts directory structure
        self.default_prompts_dir.mkdir(exist_ok=True)
        
        # Subdirectories for default prompts
        self.default_system_dir = self.default_prompts_dir / "system"
        self.default_templates_dir = self.default_prompts_dir / "templates"
        self.default_generated_dir = self.default_prompts_dir / "generated"
        
        for dir_path in [self.default_system_dir, self.default_templates_dir, self.default_generated_dir]:
            dir_path.mkdir(exist_ok=True)
        
        # Initialize default HTML prompts if they don't exist
        self._initialize_default_html_prompts()
        
        # Current template selection (None means use defaults)
        self.current_template = None
        self.current_colors = None  # Cache for current template colors
    
    def set_template(self, template_name: Optional[str]):
        """
        Set the current template for HTML prompt selection.
        
        Args:
            template_name: Name of the template folder, or None to use defaults
        """
        if template_name:
            template_path = self.templates_dir / template_name
            if template_path.exists():
                self.current_template = template_name
                self.current_colors = self._load_template_colors(template_name)
                print(f"✅ HTML Prompt Manager: Using template-specific prompts for '{template_name}'")
            else:
                print(f"⚠️ HTML Prompt Manager: Template '{template_name}' not found, using defaults")
                self.current_template = None
                self.current_colors = self._load_default_colors()
        else:
            self.current_template = None
            self.current_colors = self._load_default_colors()
            print("✅ HTML Prompt Manager: Using default HTML prompts")
    
    def _load_template_colors(self, template_name: str) -> Dict:
        """
        Load color configuration from template's colors.json file.
        
        Args:
            template_name: Name of the template folder
            
        Returns:
            Dictionary containing color configuration
        """
        colors_file = self.templates_dir / template_name / "colors.json"
        
        if colors_file.exists():
            try:
                with open(colors_file, 'r') as f:
                    colors = json.load(f)
                print(f"  📎 Loaded color configuration for '{template_name}'")
                return colors
            except Exception as e:
                print(f"  ⚠️ Error loading colors.json: {e}")
        
        # Fallback to default colors
        return self._load_default_colors()
    
    def _load_default_colors(self) -> Dict:
        """
        Load default color configuration.
        
        Returns:
            Dictionary containing default color configuration
        """
        default_colors_file = self.templates_dir / "default_colors.json"
        
        if default_colors_file.exists():
            try:
                with open(default_colors_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"  ⚠️ Error loading default colors: {e}")
        
        # Ultimate fallback
        return {
            "colors": {
                "primary": {"name": "Professional Blue", "hex": "#0052cc"},
                "secondary": {"name": "Dark Grey", "hex": "#2d3748"},
                "text": {
                    "body": {"hex": "#000000"},
                    "heading": {"hex": "#2d3748"}
                },
                "background": {
                    "body": {"value": "transparent"},
                    "components": {"hex": "#ffffff"}
                }
            }
        }
    
    def get_template_colors(self) -> Dict:
        """
        Get the current template's color configuration.
        
        Returns:
            Dictionary containing color configuration
        """
        if self.current_colors is None:
            self.current_colors = self._load_default_colors()
        return self.current_colors
    
    def _generate_color_aware_design_prompt(self, colors: Dict) -> str:
        """
        Generate HTML design prompt with colors from JSON configuration.
        
        Args:
            colors: Dictionary containing color configuration
            
        Returns:
            HTML design prompt string with template colors
        """
        color_config = colors.get("colors", {})
        typography = colors.get("typography", {})
        
        # Extract colors with safe defaults
        primary = color_config.get("primary", {})
        secondary = color_config.get("secondary", {})
        text = color_config.get("text", {})
        background = color_config.get("background", {})
        
        # Handle transparent backgrounds properly
        component_bg = background.get('components', {})
        component_bg_value = component_bg.get('value', component_bg.get('hex', '#ffffff'))
        
        prompt = f"""HTML VISUAL DESIGN SPECIFICATIONS:

TEMPLATE COLOR PALETTE:
- Primary/Accent: {primary.get('name', 'Accent')} ({primary.get('hex', '#0052cc')}) - {primary.get('usage', 'Key elements, highlights')}
- Secondary: {secondary.get('name', 'Secondary')} ({secondary.get('hex', '#2d3748')}) - {secondary.get('usage', 'Headings, secondary info')}
- Body Text: {text.get('body', {}).get('name', 'Black')} ({text.get('body', {}).get('hex', '#000000')}) - Body text and descriptions
- Heading Text: {text.get('heading', {}).get('name', 'Dark Grey')} ({text.get('heading', {}).get('hex', '#2d3748')}) - All headings
- HTML Body Background: {background.get('body', {}).get('value', 'transparent')} - CRITICAL for PowerPoint integration
- Component Backgrounds: {component_bg.get('name', 'White')} ({component_bg_value}) - Cards, panels

HTML TYPOGRAPHY:
- Font Stack: {typography.get('font_family', "'Segoe UI', system-ui, sans-serif")}
- H1 Size: {typography.get('sizes', {}).get('h1', '24px')}
- H2 Size: {typography.get('sizes', {}).get('h2', '20px')}
- Body Size: {typography.get('sizes', {}).get('body', '16px')}

HTML COMPONENT GUIDELINES:
- Use DaisyUI components: cards, stats, badges, alerts, timeline
- Override ALL component default colors with template colors using inline styles
- Ensure high contrast between text and backgrounds

HTML VISUALIZATION RULES:
- Mermaid.js: Use for process flows and organizational charts ONLY
- D3.js: REQUIRED for all timelines and roadmaps
- Icons: Use Lucide icons via <use href="#icon-name"> references only
- Background: Body MUST have transparent background

CRITICAL COLOR IMPLEMENTATION:
- Use inline styles with exact hex values from above
- Example: style="color: {primary.get('hex', '#0052cc')};" for primary accent
- Example: style="background-color: {component_bg_value};" for component backgrounds
- NEVER rely on default component colors - always override"""
        
        return prompt
    
    def _get_prompt_path(self, prompt_type: str, filename: str, use_default_fallback: bool = True) -> Path:
        """
        Get the path to a prompt file, checking template-specific first, then defaults.
        
        Args:
            prompt_type: Type of prompt ('system' or 'templates')
            filename: Name of the prompt file
            
        Returns:
            Path to the prompt file
        """
        # Check template-specific prompts first if a template is selected
        if self.current_template:
            template_prompt_dir = self.templates_dir / self.current_template / "html_prompts"
            
            if prompt_type == "system":
                template_file = template_prompt_dir / "system" / filename
            else:
                template_file = template_prompt_dir / "templates" / filename
            
            if template_file.exists():
                return template_file
        
        # Fall back to default prompts
        if use_default_fallback:
            if prompt_type == "system":
                default_file = self.default_system_dir / filename
            else:
                default_file = self.default_templates_dir / filename
            
            # If default doesn't exist, try html_prompts_default folder
            if not default_file.exists():
                default_folder = Path("templates/html_prompts_default")
                if prompt_type == "system":
                    fallback_file = default_folder / "system" / filename
                else:
                    fallback_file = default_folder / "templates" / filename
                if fallback_file.exists():
                    return fallback_file
            return default_file
        
        # Return non-existent path if no fallback requested
        if prompt_type == "system":
            return self.default_system_dir / filename
        else:
            return self.default_templates_dir / filename
    
    def _initialize_default_html_prompts(self):
        """Initialize default HTML prompts if they don't exist."""
        # Check if system prompt exists
        system_prompt_file = self.default_system_dir / "html_generation.txt"
        if not system_prompt_file.exists():
            self._create_default_html_system_prompt(system_prompt_file)
        
        # Check if user prompt template exists
        user_template_file = self.default_templates_dir / "html_generation_template.txt"
        if not user_template_file.exists():
            self._create_default_html_user_template(user_template_file)
        
        # Check if visual design prompt exists
        design_prompt_file = self.default_templates_dir / "visual_design.txt"
        if not design_prompt_file.exists():
            self._create_default_html_design_prompt(design_prompt_file)
        
        # Check if D3 timeline template exists
        d3_template_file = self.default_templates_dir / "d3_timeline.html"
        if not d3_template_file.exists():
            self._create_default_html_d3_template(d3_template_file)
        
        # Check if Mermaid examples exist
        mermaid_examples_file = self.default_templates_dir / "mermaid_examples.txt"
        if not mermaid_examples_file.exists():
            self._create_default_mermaid_examples(mermaid_examples_file)
        
        # Check if HTML refinement system prompt exists
        refinement_prompt_file = self.default_system_dir / "html_refinement.txt"
        if not refinement_prompt_file.exists():
            self._create_default_html_refinement_prompt(refinement_prompt_file)
    
    def _create_default_html_system_prompt(self, file_path: Path):
        """Create the default HTML system prompt."""
        system_prompt = """You are an expert HTML content generator specializing in creating visualizations for PowerPoint presentations.
Your task is to convert descriptive content into visually appealing HTML that will be rendered as images for PowerPoint slides.

CRITICAL HTML REQUIREMENTS:
1. Generate ONLY valid HTML content - no markdown, no code blocks
2. Use provided viewport dimensions exactly as specified
3. Apply brand colors consistently using inline styles
4. Ensure ALL content fits within viewport without any overflow or scrolling
5. Create clean, professional, corporate-quality visualizations
6. NO EMOJIS - Never use emoji characters in the HTML
7. ICONS ONLY - Use Lucide icons exclusively via <svg><use href="#icon-name"></use></svg>

HTML TRANSPARENCY REQUIREMENT:
- The main <body> background MUST be transparent: background-color: transparent;
- Individual components (cards, panels, divs) should have white backgrounds (#ffffff)
- This transparency allows the HTML to blend seamlessly with PowerPoint slide backgrounds

HTML OUTPUT FORMAT:
- Return ONLY the HTML code itself
- Start with <!DOCTYPE html>
- Include all necessary CSS and JavaScript inline
- No explanations, no markdown formatting, no code blocks
- The response should be pure HTML that can be directly rendered"""
        
        file_path.write_text(system_prompt)
        print(f"✅ Created default HTML system prompt at: {file_path}")
    
    def _create_default_html_user_template(self, file_path: Path):
        """Create the default HTML user prompt template."""
        user_template = """HTML VISUALIZATION CONTEXT:
- Presentation Topic: {topic}
- Current Slide: {slide_number} of {total_slides}
- HTML Placeholder: {placeholder_name}
- Content to Visualize: {original_content}

{detailed_specs}

HTML VIEWPORT REQUIREMENTS:
- Exact dimensions: {viewport_width}x{viewport_height} pixels
- Body element MUST have: class="w-[{viewport_width}px] h-[{viewport_height}px]"
- Body background MUST be: style="background-color: transparent;"
- ALL content MUST fit within these dimensions without scrolling
- Use responsive layouts (grid, flexbox) to ensure proper fit

HTML GENERATION TASK:
Create a professional HTML visualization for the above content that:
1. Converts the descriptive content into compelling visual elements
2. Uses appropriate components (cards, charts, diagrams, timelines)
3. Maintains strict brand compliance
4. Fits perfectly within the specified viewport
5. Has a transparent background with solid component backgrounds
6. Uses ONLY Lucide icons - NO emoji characters allowed"""
        
        file_path.write_text(user_template)
        print(f"✅ Created default HTML user template at: {file_path}")
    
    def _create_default_html_design_prompt(self, file_path: Path):
        """Create the default HTML visual design prompt."""
        design_prompt = """HTML VISUAL DESIGN SPECIFICATIONS:

BRAND COLORS (MANDATORY FOR ALL HTML):
- Primary/Accent: Swiss Red (#dc261e) - Use for highlights, key metrics, CTAs
- Headings: Dark Grey (#2d3748) - All H1, H2, H3 tags
- Body Text: Black (#000000) - All paragraph and description text
- HTML Body Background: TRANSPARENT - Required for PowerPoint integration
- Component Backgrounds: White (#ffffff) - Cards, panels, containers

HTML TYPOGRAPHY:
- Font Stack: 'Segoe UI', system-ui, -apple-system, sans-serif
- Base Size: 16px (text-base in Tailwind)
- Headings: 24px (text-2xl), bold, Dark Grey
- Body: 16px (text-base), regular, Black

HTML COMPONENT GUIDELINES:
- Use DaisyUI components: cards, stats, badges, alerts, timeline
- Use Flowbite for additional components if needed
- Override ALL component default colors with brand colors using inline styles
- Ensure high contrast between text and backgrounds

HTML VISUALIZATION RULES:
- Mermaid.js: Use for process flows and organizational charts ONLY
- D3.js: REQUIRED for all timelines and roadmaps (superior styling control)
- DaisyUI Timeline: Alternative for simple timelines
- Icons: Use Lucide icons via <use href="#icon-name"> references ONLY
- NO EMOJIS: Never use emoji characters (❌ ✅ 🎯 etc.) - use Lucide icons instead
- NEVER create custom SVG sprites or symbol definitions

HTML LAYOUT PRINCIPLES:
- Clean, minimalist design with ample white space
- Use CSS Grid or Flexbox for responsive layouts
- Maintain consistent spacing (use Tailwind spacing utilities)
- Ensure all interactive elements are visually distinct
- Group related information in cards or panels"""
        
        file_path.write_text(design_prompt)
        print(f"✅ Created default HTML design prompt at: {file_path}")
    
    def _create_default_html_d3_template(self, file_path: Path):
        """Create the default D3.js HTML template."""
        d3_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { 
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; 
            background-color: transparent;
            margin: 0;
            padding: 0;
        }
    </style>
</head>
<body class="w-[{viewport_width}px] h-[{viewport_height}px] flex items-center justify-center p-8" style="background-color: transparent;">
    <div class="card w-full h-full bg-white shadow-xl">
        <div class="card-body flex flex-col p-6">
            <h1 class="text-2xl font-bold text-center mb-4 shrink-0" style="color: #2d3748;">{title}</h1>
            <div id="d3-container" class="flex-grow w-full h-full"></div>
        </div>
    </div>
    <script>
        // Data for visualization
        const visualizationData = {data};
        
        // D3.js visualization implementation
        const container = d3.select("#d3-container");
        const width = container.node().getBoundingClientRect().width;
        const height = container.node().getBoundingClientRect().height;
        
        const svg = container
            .append("svg")
            .attr("width", width)
            .attr("height", height);
        
        // Add your D3.js visualization code here
        // Use brand colors: #dc261e (red), #2d3748 (dark grey), #000000 (black)
    </script>
</body>
</html>"""
        
        file_path.write_text(d3_template)
        print(f"✅ Created default HTML D3 template at: {file_path}")
    
    def _create_default_mermaid_examples(self, file_path: Path):
        """Create default Mermaid.js HTML examples."""
        mermaid_examples = """MERMAID.JS HTML EXAMPLES FOR POWERPOINT:

1. PROCESS FLOW HTML:
<div class="mermaid max-h-[400px] w-full">
flowchart LR
    A["Start"] --> B["Process Data"]
    B --> C{"Decision"}
    C -->|Yes| D["Action 1"]
    C -->|No| E["Action 2"]
    D --> F["End"]
    E --> F
</div>

2. ORGANIZATIONAL CHART HTML:
<div class="mermaid max-h-[400px] w-full">
graph TD
    CEO["CEO"]
    CEO --> CTO["CTO"]
    CEO --> CFO["CFO"]
    CEO --> CMO["CMO"]
    CTO --> Dev1["Dev Team"]
    CTO --> Dev2["QA Team"]
    CFO --> Fin["Finance"]
    CMO --> Mark["Marketing"]
</div>

3. DECISION TREE HTML:
<div class="mermaid max-h-[400px] w-full">
graph TD
    Start["Analyze Problem"] --> Q1{"Is it urgent?"}
    Q1 -->|Yes| Q2{"High impact?"}
    Q1 -->|No| Q3{"Strategic value?"}
    Q2 -->|Yes| A1["Priority 1"]
    Q2 -->|No| A2["Priority 2"]
    Q3 -->|Yes| A3["Priority 3"]
    Q3 -->|No| A4["Priority 4"]
</div>

IMPORTANT HTML NOTES:
- Always wrap Mermaid in a constrained div: max-h-[400px]
- Use simple text in nodes, avoid HTML tags
- Use quotes for node text: A["Text"]
- Keep diagrams simple for better rendering"""
        
        file_path.write_text(mermaid_examples)
        print(f"✅ Created default Mermaid HTML examples at: {file_path}")
    
    def get_html_system_prompt(self, viewport_width: int = 1577, viewport_height: int = 603, placeholder_name: str = "unknown", slide_number: int = 0) -> str:
        """
        Get the HTML system prompt for content generation.
        
        Args:
            viewport_width: Width of the HTML viewport
            viewport_height: Height of the HTML viewport
            
        Returns:
            HTML system prompt string
        """
        system_prompt_file = self._get_prompt_path("system", "html_generation.txt")
        
        if not system_prompt_file.exists() and not self.current_template:
            # Create default if it doesn't exist
            self._create_default_html_system_prompt(system_prompt_file)
        
        if system_prompt_file.exists():
            base_prompt = system_prompt_file.read_text()
        else:
            # Fallback to a minimal prompt if file not found
            base_prompt = "Generate valid HTML content for PowerPoint slides."
        
        # Add adaptive layout guidance for unusual viewport sizes
        aspect_ratio = viewport_width / viewport_height if viewport_height > 0 else 1.0
        is_short_placeholder = viewport_height < 500
        
        if is_short_placeholder and aspect_ratio > 2.5:
            layout_addon = f"""
HTML LAYOUT ADAPTATION - SHORT & WIDE VIEWPORT:
- Height is LIMITED ({viewport_height}px) - use horizontal layouts
- Use compact spacing: gap-2, p-2, mb-2
- Reduce text sizes: text-sm for body, text-base for headings
- Prioritize key information only
- Use single-row layouts where possible"""
            base_prompt += "\n\n" + layout_addon
        
        # Save system prompt for debugging
        if placeholder_name != "unknown":
            self._save_generated_html_prompt(base_prompt, placeholder_name, slide_number, "system")
            
            # Also save debug info
            debug_info = f"\n\n[DEBUG INFO]\nTemplate: {self.current_template or 'default'}\n"
            debug_info += f"System Prompt File: {system_prompt_file}\n"
            debug_prompt = base_prompt + debug_info
            self._save_generated_html_prompt(debug_prompt, placeholder_name, slide_number, "system_with_debug")
            
            # Also use simple debug
            try:
                save_prompt_debug("system", base_prompt, self.current_template, f"slide_{slide_number}_{placeholder_name}")
            except:
                pass
        
        return base_prompt
    
    def get_html_user_prompt(
        self,
        placeholder_name: str,
        original_content: str,
        topic: str,
        slide_number: int,
        total_slides: int,
        viewport_width: int = 1577,
        viewport_height: int = 603,
        slide_spec: Optional[Any] = None,
        placeholder_instructions: Optional[str] = None,
    ) -> str:
        """
        Get the HTML user prompt for content generation.
        
        Args:
            placeholder_name: Name of the HTML placeholder
            original_content: Original text content to convert to HTML
            topic: Presentation topic
            slide_number: Current slide number
            total_slides: Total number of slides
            viewport_width: Width of HTML viewport
            viewport_height: Height of HTML viewport
            slide_spec: Optional slide specification with additional requirements
            
        Returns:
            HTML user prompt string
        """
        # Add placeholder instructions to the beginning if provided
        instructions_section = ""
        if placeholder_instructions:
            instructions_section = f"""CRITICAL TEMPLATE INSTRUCTIONS FROM PLACEHOLDER:
The PowerPoint template placeholder contains these specific instructions that MUST be followed:
"{placeholder_instructions}"

These instructions are the PRIMARY requirements for this HTML visualization.

"""
        
        # Load HTML templates
        user_template_file = self._get_prompt_path("templates", "html_generation_template.txt")
        design_prompt_file = self._get_prompt_path("templates", "visual_design.txt")
        requirements_file = self._get_prompt_path("templates", "html_requirements.txt")
        
        # Read templates with fallback
        if user_template_file.exists():
            user_template = user_template_file.read_text()
        else:
            user_template = "Generate HTML for: {original_content}"
        
        if design_prompt_file.exists():
            design_prompt = design_prompt_file.read_text()
        else:
            design_prompt = ""
        
        # Build detailed HTML specifications if available
        detailed_specs = ""
        if slide_spec:
            specs = []
            if hasattr(slide_spec, "detailed_purpose") and slide_spec.detailed_purpose:
                specs.append(f"- HTML Purpose: {slide_spec.detailed_purpose}")
            if hasattr(slide_spec, "content_structure") and slide_spec.content_structure:
                specs.append(f"- HTML Structure: {slide_spec.content_structure}")
            if hasattr(slide_spec, "html_requirements") and slide_spec.html_requirements:
                specs.append(f"- HTML Requirements: {slide_spec.html_requirements}")
            if hasattr(slide_spec, "visual_elements") and slide_spec.visual_elements:
                specs.append(f"- HTML Visual Elements: {slide_spec.visual_elements}")
            
            if specs:
                detailed_specs = "DETAILED HTML SPECIFICATIONS:\n" + "\n".join(specs)
                detailed_specs += "\n\nCRITICAL: Your HTML must implement these specifications exactly."
        
        # Format the HTML prompt with instructions at the beginning
        prompt = instructions_section + user_template.format(
            topic=topic,
            slide_number=slide_number,
            total_slides=total_slides,
            placeholder_name=placeholder_name,
            original_content=original_content,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            detailed_specs=detailed_specs
        )
        
        # Add HTML requirements if available (highest priority for template-specific)
        if requirements_file.exists():
            requirements = requirements_file.read_text()
            # Replace viewport placeholders
            requirements = requirements.replace("{viewport_width}", str(viewport_width))
            requirements = requirements.replace("{viewport_height}", str(viewport_height))
            prompt += "\n\nTEMPLATE-SPECIFIC REQUIREMENTS (HIGHEST PRIORITY):\n" + requirements
        
        # Add HTML design specifications - prioritize template-specific over defaults
        if design_prompt and self.current_template:
            # For template-specific prompts, use the visual_design.txt directly
            # as it contains template-specific requirements
            prompt += "\n\nTEMPLATE-SPECIFIC DESIGN REQUIREMENTS:\n" + design_prompt
        elif design_prompt:
            # Only use color-aware design for default templates
            colors = self.get_template_colors()
            color_aware_design = self._generate_color_aware_design_prompt(colors)
            prompt += "\n\n" + color_aware_design
        else:
            # Fallback to color-aware design if no design prompt exists
            colors = self.get_template_colors()
            color_aware_design = self._generate_color_aware_design_prompt(colors)
            prompt += "\n\n" + color_aware_design
        
        # Save the generated HTML prompt for debugging/review
        self._save_generated_html_prompt(prompt, placeholder_name, slide_number, "user")
        
        # Also log which template is being used
        template_info = f"\n\n[DEBUG INFO]\nTemplate: {self.current_template or 'default'}\n"
        template_info += f"Visual Design File: {design_prompt_file}\n"
        template_info += f"Requirements File: {requirements_file}\n"
        template_info += f"Colors: {self.get_template_colors().get('colors', {}).get('background', {})}\n"
        
        debug_prompt = prompt + template_info
        self._save_generated_html_prompt(debug_prompt, placeholder_name, slide_number, "user_with_debug")
        
        # Also use simple debug
        try:
            full_debug = prompt + template_info
            save_prompt_debug("user", full_debug, self.current_template, f"slide_{slide_number}_{placeholder_name}")
        except:
            pass
        
        return prompt
    
    def _save_generated_html_prompt(self, prompt: str, placeholder_name: str, slide_number: int, prompt_type: str = "user"):
        """
        Save generated HTML prompts for review and debugging.
        
        Args:
            prompt: The generated HTML prompt
            placeholder_name: Name of the HTML placeholder
            slide_number: Slide number
        """
        # Determine where to save based on current template
        if self.current_template:
            generated_dir = self.templates_dir / self.current_template / "html_prompts" / "generated"
        else:
            generated_dir = self.default_generated_dir
        
        generated_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prompt_type}_prompt_slide_{slide_number}_{placeholder_name}_{timestamp}.txt"
        
        file_path = generated_dir / filename
        file_path.write_text(prompt)
        
        # Keep only the last 50 generated HTML prompts to avoid clutter
        self._cleanup_old_html_prompts(generated_dir, keep_last=50)
    
    def _cleanup_old_html_prompts(self, directory: Path, keep_last: int = 50):
        """
        Clean up old generated HTML prompts.
        
        Args:
            directory: Directory containing HTML prompts
            keep_last: Number of recent prompts to keep
        """
        if not directory.exists():
            return
            
        prompt_files = sorted(directory.glob("*.txt"), key=lambda p: p.stat().st_mtime)
        
        if len(prompt_files) > keep_last:
            for file_path in prompt_files[:-keep_last]:
                file_path.unlink()
    
    def list_html_prompts(self) -> Dict[str, Dict[str, list]]:
        """
        List all available HTML prompts (default and template-specific).
        
        Returns:
            Dictionary of HTML prompt categories and their files
        """
        result = {
            "default": {
                "system": list(self.default_system_dir.glob("*.txt")) if self.default_system_dir.exists() else [],
                "templates": list(self.default_templates_dir.glob("*")) if self.default_templates_dir.exists() else [],
                "generated": list(self.default_generated_dir.glob("*.txt")) if self.default_generated_dir.exists() else []
            }
        }
        
        # Add template-specific HTML prompts
        if self.templates_dir.exists():
            for template_dir in self.templates_dir.iterdir():
                if template_dir.is_dir():
                    html_prompts_dir = template_dir / "html_prompts"
                    if html_prompts_dir.exists():
                        result[template_dir.name] = {
                            "system": list((html_prompts_dir / "system").glob("*.txt")) 
                                     if (html_prompts_dir / "system").exists() else [],
                            "templates": list((html_prompts_dir / "templates").glob("*"))
                                        if (html_prompts_dir / "templates").exists() else [],
                            "generated": list((html_prompts_dir / "generated").glob("*.txt"))
                                        if (html_prompts_dir / "generated").exists() else []
                        }
        
        # Convert paths to strings for readability
        for category in result:
            for subcategory in result[category]:
                result[category][subcategory] = [str(p.name) for p in result[category][subcategory]]
        
        return result
    
    def _create_default_html_refinement_prompt(self, file_path: Path):
        """Create the default HTML refinement system prompt."""
        refinement_prompt = """You are an expert web developer and presentation design specialist.
Your task is to evaluate HTML code against slide requirements and refine it for optimal purpose fulfillment.

YOUR MISSION: Assess whether the provided HTML code successfully achieves the slide's intended purpose and requirements. If not, improve the HTML to better fulfill those objectives.

RESPONSE FORMAT:
Your response MUST be a JSON object that strictly follows this format: 
`{"html_code": "<FULL_HTML_CODE>", "reasoning": "...", "changes_applied": ["...", "..."]}`
Do NOT provide any other text, explanations, or markdown.

CRITICAL EVALUATION PRIORITIES:

1. VIEWPORT DIMENSION COMPLIANCE (ABSOLUTE TOP PRIORITY):
- DETECT MISSING CONTENT: If ANY content is missing from the image, the HTML dimensions are incorrect
- CHECK VIEWPORT DIMENSIONS: Extract w-[NNNpx] h-[NNNpx] from body class - this is the ABSOLUTE MAXIMUM allowed size
- ENSURE EXACT COMPLIANCE: Body dimensions MUST match exactly w-[{width}px] h-[{height}px]
- CALCULATE TOTAL HEIGHT: body padding + card padding + content + gaps MUST be < viewport height
- VALIDATION: If rendered content exceeds specified dimensions, it WILL be cropped

2. MANDATORY DAISYUI CARD STRUCTURE:
- Card Usage: Is ALL content properly wrapped in DaisyUI card components?
- Card Organization: Are cards used effectively for content structure and spacing?
- Visual Hierarchy: Do cards provide proper visual separation and organization?
- REQUIREMENT: Content should NEVER be placed directly in body - always use cards

3. Content Layout Assessment:
- Space Distribution: Is the space used efficiently without overflow?
- Content Scaling: Are text sizes, diagrams, and elements appropriately sized?
- Grid/Flex Usage: Is CSS Grid or Flexbox used effectively for layout?
- Safe Margins: Are there appropriate margins on all sides?

4. Color Palette Validation:
- Are ALL elements using the correct template-specific colors?
- Check every text element, background, accent, and component for brand compliance
- Note: Colors should match the template's visual design specifications

5. Purpose Assessment:
- Does the HTML effectively communicate the slide's intended message?
- Are all specified requirements met?
- Does the rendered result enhance understanding and engagement?

TECHNICAL REQUIREMENTS:
- Viewport: Match the exact dimensions specified in the HTML body element
- Frameworks: TailwindCSS, Flowbite, and daisyUI components only
- Diagrams: Mermaid.js or D3.js with height constraints (max-h-[400px])
- Background: Transparent body background for PowerPoint integration
- Typography: Clear font hierarchy with appropriate fallbacks

QUALITY CHECKLIST:
- ALL content fits within the specified viewport dimensions
- All content wrapped in proper DaisyUI card structure
- Template color palette enforced on ALL elements
- Purpose clearly communicated through visualization
- Professional, polished visual presentation
- No overlapping or mispositioned elements
- Optimal use of available space
- NO emoji characters - only Lucide icons used
- Clean, professional appearance"""
        
        file_path.write_text(refinement_prompt)
        print(f"✅ Created default HTML refinement prompt at: {file_path}")
    
    def get_html_refinement_prompt(self, width: int, height: int, placeholder_name: str = "unknown", slide_number: int = 0) -> str:
        """
        Get the HTML refinement system prompt with viewport dimensions.
        
        Args:
            width: Width of the HTML viewport in pixels
            height: Height of the HTML viewport in pixels
            
        Returns:
            HTML refinement system prompt string
        """
        refinement_prompt_file = self._get_prompt_path("system", "html_refinement.txt")
        
        if not refinement_prompt_file.exists() and not self.current_template:
            # Create default if it doesn't exist
            self._create_default_html_refinement_prompt(refinement_prompt_file)
        
        if refinement_prompt_file.exists():
            base_prompt = refinement_prompt_file.read_text()
        else:
            # Minimal fallback
            base_prompt = "Evaluate and refine HTML code for PowerPoint slides."
        
        # Replace viewport placeholders if they exist
        base_prompt = base_prompt.replace("{width}", str(width))
        base_prompt = base_prompt.replace("{height}", str(height))
        
        # Get color specifications from JSON
        colors = self.get_template_colors()
        color_config = colors.get("colors", {})
        
        if color_config:
            primary = color_config.get("primary", {})
            secondary = color_config.get("secondary", {})
            text = color_config.get("text", {})
            
            color_section = f"""
TEMPLATE-SPECIFIC COLOR REQUIREMENTS:
- Primary: {primary.get('name', 'Accent')} ({primary.get('hex', '#0052cc')}) - ALL accent elements
- Secondary: {secondary.get('name', 'Secondary')} ({secondary.get('hex', '#2d3748')}) - ALL secondary elements
- Body Text: {text.get('body', {}).get('hex', '#000000')} - ALL body text
- Heading Text: {text.get('heading', {}).get('hex', '#2d3748')} - ALL headings
- Transparent background for body - CRITICAL for PowerPoint integration"""
            
            base_prompt += color_section
        
        # Save refinement prompt for debugging
        if placeholder_name != "unknown":
            self._save_generated_html_prompt(base_prompt, placeholder_name, slide_number, "refinement")
            
            # Also save debug info
            debug_info = f"\n\n[DEBUG INFO]\nTemplate: {self.current_template or 'default'}\n"
            debug_info += f"Refinement Prompt File: {refinement_prompt_file}\n"
            debug_info += f"Width: {width}, Height: {height}\n"
            debug_prompt = base_prompt + debug_info
            self._save_generated_html_prompt(debug_prompt, placeholder_name, slide_number, "refinement_with_debug")
            
            # Also use simple debug
            try:
                full_debug = base_prompt + debug_info
                save_prompt_debug("refinement", full_debug, self.current_template, f"slide_{slide_number}_{placeholder_name}_w{width}_h{height}")
            except:
                pass
        
        return base_prompt