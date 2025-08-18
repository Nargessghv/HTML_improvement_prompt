# HTML Prompt Template System Guide

## Overview
The HTML generation system now fully supports template-specific prompts that override default behavior. Each PowerPoint template can have its own HTML generation rules, visual design specifications, and refinement criteria.

## Template Folder Structure
Each template should have the following structure:
```
templates/
├── [template_name]/
│   ├── [template_name].pptx
│   ├── colors.json                    # Color configuration
│   ├── html_prompts/                  # HTML prompt customizations
│   │   ├── system/                    # System prompts
│   │   │   ├── html_generation.txt    # HTML generation system prompt
│   │   │   └── html_refinement.txt    # HTML refinement system prompt
│   │   ├── templates/                 # User prompt templates
│   │   │   ├── html_generation_template.txt  # User prompt template
│   │   │   ├── visual_design.txt      # Visual design specifications
│   │   │   └── html_requirements.txt  # Technical requirements (NEW)
│   │   └── generated/                 # Auto-generated prompts (for debugging)
```

## Key Files and Their Purpose

### 1. `html_requirements.txt` (NEW - HIGHEST PRIORITY)
This file contains the technical requirements for HTML generation specific to your template:
- Viewport specifications
- Layout requirements
- Component structure rules
- Visualization guidelines
- Template-specific constraints

**Variables Available:**
- `{viewport_width}` - Replaced with actual width
- `{viewport_height}` - Replaced with actual height

### 2. `visual_design.txt`
Visual design specifications for the template:
- Color palette requirements
- Typography rules
- Component styling
- Brand guidelines

### 3. `html_refinement.txt`
System prompt for the HTML refinement agent:
- Evaluation criteria specific to the template
- Quality checkpoints
- Refinement priorities
- Template-specific validation rules

### 4. `colors.json`
JSON configuration for template colors:
```json
{
  "colors": {
    "primary": {"name": "Swiss Red", "hex": "#dc261e"},
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
```

## How Prompts Are Prioritized

1. **Placeholder Instructions** (HIGHEST)
   - Text from the actual PowerPoint placeholder
   - Appears at the very beginning of prompts
   - Marked as "CRITICAL TEMPLATE INSTRUCTIONS"

2. **Template-Specific Requirements** (`html_requirements.txt`)
   - Technical requirements for the template
   - Marked as "TEMPLATE-SPECIFIC REQUIREMENTS (HIGHEST PRIORITY)"

3. **Template Visual Design** (`visual_design.txt`)
   - Visual specifications for the template
   - Marked as "TEMPLATE-SPECIFIC DESIGN REQUIREMENTS"

4. **Default Prompts** (FALLBACK)
   - Used only when template-specific files don't exist
   - Located in `html_prompts/` or `templates/html_prompts_default/`

## Example: Brochure Template Customization

### Brochure-Specific Requirements
The brochure template has unique requirements:
- White text on transparent backgrounds
- Large fonts for readability (min 14px)
- Print-optimized layout
- High visual impact design

These are specified in:
- `templates/Brochure_template_leaflet_4sides/html_prompts/templates/html_requirements.txt`
- `templates/Brochure_template_leaflet_4sides/html_prompts/templates/visual_design.txt`
- `templates/Brochure_template_leaflet_4sides/html_prompts/system/html_refinement.txt`

## Example: Ekona Template Customization

### Ekona Brand Requirements
The Ekona template enforces strict brand compliance:
- Swiss Red (#dc261e) for accents
- Dark Grey (#2d3748) for headings
- Black (#000000) for body text
- Mandatory DaisyUI card structure
- D3.js for timelines

These are specified in:
- `templates/ekona_slides_template_new/html_prompts/templates/html_requirements.txt`
- `templates/ekona_slides_template_new/html_prompts/templates/visual_design.txt`
- `templates/ekona_slides_template_new/html_prompts/system/html_refinement.txt`

## Creating a New Template

1. **Create the folder structure:**
   ```bash
   mkdir -p templates/my_template/html_prompts/{system,templates,generated}
   ```

2. **Add your requirements file:**
   Create `templates/my_template/html_prompts/templates/html_requirements.txt`
   with your specific technical requirements.

3. **Add your visual design:**
   Create `templates/my_template/html_prompts/templates/visual_design.txt`
   with your visual specifications.

4. **Add refinement criteria:**
   Create `templates/my_template/html_prompts/system/html_refinement.txt`
   with your quality evaluation criteria.

5. **Configure colors:**
   Create `templates/my_template/colors.json`
   with your color palette.

## Testing Your Template Prompts

1. The system will automatically use your template's prompts when that template is selected
2. Generated prompts are saved to the `generated/` folder for review
3. Check that your specifications appear with "HIGHEST PRIORITY" designation
4. Verify that placeholder instructions are being captured and used

## Benefits of This System

1. **Template Independence**: Each template has complete control over HTML generation
2. **No Code Changes Required**: Add new templates without modifying Python code
3. **Clear Priority**: Template-specific prompts always override defaults
4. **Placeholder Awareness**: Instructions from PowerPoint placeholders are preserved
5. **Easy Maintenance**: All template-specific content in one location
6. **Version Control**: Template prompts can be versioned with the template

## Troubleshooting

If your template prompts aren't being used:
1. Check that the folder structure matches exactly
2. Verify file names are correct (case-sensitive)
3. Ensure the template name in the folder matches the template selection
4. Check the `generated/` folder to see what prompts are actually being used
5. Look for "Using template-specific prompts" message in console output