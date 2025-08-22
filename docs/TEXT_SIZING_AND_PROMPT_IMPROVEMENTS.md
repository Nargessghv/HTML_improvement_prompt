# Text Sizing and Prompt Improvements Summary

## Overview

This document summarizes all the improvements made to fix the HTML-to-PowerPoint image size mismatch issue, specifically focusing on text sizing, prompt enhancements, and iteration control.

## Problem Identified

The HTML generation system was correctly getting placeholder dimensions but the generated HTML content was not respecting viewport constraints, causing:
- Content overflow and cropping
- Text too large for available space
- Poor visual presentation in PowerPoint slides

## Solution Implemented

### 1. Dynamic Font Size Calculation System

**New Method Added: `_calculate_dynamic_font_sizes()` in `src/html_prompt_manager.py`**

```python
def _calculate_dynamic_font_sizes(self, viewport_width: int, viewport_height: int) -> str:
    """
    Calculate appropriate font sizes based on viewport dimensions.
    Ensures text fits within the available space.
    """
    # Calculate available space for content (accounting for padding)
    available_width = viewport_width - 16  # 8px padding on each side
    available_height = viewport_height - 16  # 8px padding on each side
    
    # Calculate area and determine font size strategy
    area = available_width * available_height
    
    if area < 50000:  # Very small placeholders (< 50k pixels)
        return "text-xs (12px) for headings, text-[10px] for body, text-[8px] for small text"
    elif area < 100000:  # Small placeholders (< 100k pixels)
        return "text-sm (14px) for headings, text-xs (12px) for body, text-[10px] for small text"
    elif area < 200000:  # Medium placeholders (< 200k pixels)
        return "text-base (16px) for headings, text-sm (14px) for body, text-xs (12px) for small text"
    elif area < 400000:  # Large placeholders (< 400k pixels)
        return "text-lg (18px) for headings, text-base (16px) for body, text-sm (14px) for small text"
    else:  # Very large placeholders
        return "text-xl (20px) for headings, text-lg (18px) for body, text-base (16px) for small text"
```

**Font Size Strategy by Placeholder Area:**
- **Very small** (< 50k pixels): `text-xs (12px)` headings, `text-[10px]` body, `text-[8px]` small text
- **Small** (< 100k pixels): `text-sm (14px)` headings, `text-xs (12px)` body, `text-[10px]` small text
- **Medium** (< 200k pixels): `text-base (16px)` headings, `text-sm (14px)` body, `text-xs (12px)` small text
- **Large** (< 400k pixels): `text-lg (18px)` headings, `text-base (16px)` body, `text-sm (14px)` small text
- **Very large**: `text-xl (20px)` headings, `text-lg (18px)` body, `text-base (16px)` small text

### 2. Enhanced HTML Generation Template

**File Modified: `html_prompts/templates/html_generation_template.txt`**

**Key Improvements:**
- ✅ Added critical viewport constraint requirements
- ✅ Added mandatory Ekona/Swiss red color enforcement
- ✅ Added strict content sizing rules
- ✅ Added content fitting strategy

**New Sections Added:**

```markdown
🚨 CRITICAL VIEWPORT CONSTRAINT REQUIREMENTS:
- Exact dimensions: {viewport_width}x{viewport_height} pixels
- Body element MUST have: class="w-[{viewport_width}px] h-[{viewport_height}px] overflow-hidden"
- Body background MUST be: style="background-color: transparent;"
- ALL content MUST fit within these dimensions - NO EXCEPTIONS
- If content is too large, REDUCE text sizes, padding, and spacing IMMEDIATELY

🎨 MANDATORY EKONA/SWISS RED COLOR ENFORCEMENT:
- ALL text elements: text-[#dc261e] (Ekona red)
- ALL borders: border-[#dc261e] (Ekona red)
- ALL accent elements: text-[#ff0000] (Swiss red)
- ALL lines in diagrams: stroke="#dc261e" (Ekona red)
- ALL connection lines: stroke="#dc261e" (Ekona red)
- NO default colors - always override with brand colors

📏 STRICT CONTENT SIZING RULES:
- Text sizes: Use text-xs (12px) for body, text-sm (14px) for headings
- For small placeholders: Use text-[10px] for body, text-[8px] for small text
- Padding: Use p-1 (4px) or p-2 (8px) maximum
- Margins: Use m-1 (4px) maximum
- Gaps: Use gap-1 (4px) or gap-2 (8px) maximum
- Card padding: Use p-2 (8px) maximum
- Diagram height: Use max-h-[{viewport_height//3}px] maximum
- If text doesn't fit: REDUCE font sizes immediately (text-[8px], text-[6px])

📏 CONTENT FITTING STRATEGY:
1. Start with smallest fonts: text-[8px] for body, text-[10px] for headings
2. Use minimal spacing: p-1, m-1, gap-1
3. If still doesn't fit: Use text-[6px] for body, text-[8px] for headings
4. Prioritize content over aesthetics - readability is secondary to fitting
5. Use single-line layouts where possible
6. Remove decorative elements if space is limited
```

### 3. Enhanced HTML Requirements Templates

**Files Modified:**
- `templates/ekona_slides_template_new/html_prompts/templates/html_requirements.txt`
- `templates/html_prompts_default/templates/html_requirements.txt`

**Key Improvements:**

#### A. Critical Viewport Constraint Requirements
```markdown
🚨 CRITICAL VIEWPORT CONSTRAINT REQUIREMENTS:
1. **Overall Container**: The `<body>` of the HTML MUST be exactly `{viewport_width}x{viewport_height}` pixels. Use Tailwind classes `w-[{viewport_width}px] h-[{viewport_height}px] overflow-hidden`. The root element should be a flex container (`flex`, `w-full`, `h-full`) to manage layout.

2. **STRICT CONTENT SIZING**: ALL content MUST fit within viewport with NO overflow.
   - Text sizes: Use text-xs (12px) for body, text-sm (14px) for headings
   - For small placeholders: Use text-[10px] for body, text-[8px] for small text
   - For very small placeholders: Use text-[8px] for body, text-[6px] for small text
   - Padding: Use p-1 (4px) or p-2 (8px) maximum
   - Margins: Use m-1 (4px) maximum
   - Gaps: Use gap-1 (4px) or gap-2 (8px) maximum
   - Card padding: Use p-2 (8px) maximum
   - Diagram height: Use max-h-[{viewport_height//3}px] maximum
   - If text doesn't fit: REDUCE font sizes immediately (text-[8px], text-[6px])
```

#### B. Mandatory Color Enforcement
```markdown
🎨 MANDATORY EKONA/SWISS RED COLOR ENFORCEMENT:
- Color Palette (NO EXCEPTIONS):
  - ALL Borders: Ekona Red (#dc261e) - REQUIRED for ALL borders and lines
  - ALL Accent Elements: Swiss Red (#ff0000) - REQUIRED for ALL accents and highlights
  - ALL Lines in Diagrams: Ekona Red (#dc261e) - REQUIRED for ALL connection lines
  - Background: TRANSPARENT - REQUIRED for PowerPoint integration
  - Component Backgrounds: White (#ffffff) - REQUIRED for cards and panels
  - ⚠️ CRITICAL: Use inline style attributes to override component defaults
  - ⚠️ CRITICAL: NEVER rely on Tailwind color classes alone - always specify exact hex values

- Color Implementation Examples:
  - ALL Headers: style="color: #dc261e;" 
  - ALL Borders: style="border-color: #dc261e;"
  - ALL Lines: stroke="#dc261e" (for SVG/diagrams)
  - ALL Accent elements: style="color: #ff0000;"
  - Card backgrounds: style="background-color: #ffffff;"
  - Body background: style="background-color: transparent;"
```

#### C. Enhanced Typography
```markdown
- Typography:
  - Font: 'Segoe UI', system-ui, sans-serif (MANDATORY)
  - Base Size: 12px (text-xs) - SMALLER for viewport constraints
  - Headers: 14px (text-sm, font-bold) with Ekona Red (#dc261e)
  - Body Text: 12px (text-xs) or smaller if needed
  - Small Text: 10px (text-[10px]) or 8px (text-[8px]) for very small placeholders
  - If text doesn't fit: Use text-[6px] for body, text-[8px] for headings
```

#### D. Updated Example Layouts
```html
<body class="w-[{viewport_width}px] h-[{viewport_height}px] flex flex-col p-2 overflow-hidden" style="background-color: transparent;">
  <h1 class="text-xs font-bold mb-1" style="color: #dc261e;">Diagram Title</h1>
  <div class="mermaid flex-grow max-h-[{viewport_height//3}px]">
    ... Mermaid diagram ...
  </div>
</body>
```

### 4. Enhanced HTML Prompt Manager

**File Modified: `src/html_prompt_manager.py`**

**Key Improvements:**

#### A. Dynamic Font Size Integration
```python
# Calculate dynamic font sizes based on viewport dimensions
dynamic_font_sizes = self._calculate_dynamic_font_sizes(viewport_width, viewport_height)

# ALWAYS add strict sizing rules regardless of viewport size
strict_sizing_rules = f"""
🚨 CRITICAL VIEWPORT CONSTRAINT ENFORCEMENT:
- Viewport: {viewport_width}x{viewport_height}px - ALL content MUST fit
- Dynamic Font Sizing: {dynamic_font_sizes}
- Padding: Use p-1 (4px) or p-2 (8px) maximum
- Margins: Use m-1 (4px) maximum
- Gaps: Use gap-1 (4px) or gap-2 (8px) maximum
- Card padding: Use p-2 (8px) maximum
- Diagram height: Use max-h-[{viewport_height//3}px] maximum
- NO OVERFLOW: If content doesn't fit, REDUCE sizes immediately

🎨 MANDATORY COLOR ENFORCEMENT:
- ALL borders: border-[#dc261e] (Ekona red)
- ALL lines: stroke="#dc261e" (Ekona red)
- NO default colors - always override with brand colors"""
```

#### B. Always Enforce Strict Sizing
```python
# Always add strict sizing rules
base_prompt += "\n\n" + strict_sizing_rules
```

### 5. Enhanced Iteration Control

**File Modified: `src/agents.py`**

**Key Improvements:**

#### A. Enhanced System Prompt (`_get_system_prompt_legacy`)
```markdown
🎯 FINAL VERSION DECISION CRITERIA (CRITICAL FOR ITERATION CONTROL):
**ONLY mark as "no changes" and finalize iteration when ALL criteria are met:**
1. **NO CONTENT CROPPING**: All content is fully visible within viewport boundaries
2. **PROPER SIZING**: Content fits perfectly within specified dimensions without overflow
3. **EKONA/SWISS RED COMPLIANCE**: all secondary elements, use correct brand colors (#dc261e for Ekona red, #ff0000 for Swiss red) - like connection lines, 
4. **MEANINGFUL CONTENT**: Content effectively communicates the slide's purpose
5. **VISUAL QUALITY**: Professional appearance with proper hierarchy and spacing
```

#### B. Enhanced User Prompt (`_create_user_prompt`)
```markdown
🎯 FINAL VERSION DECISION CRITERIA (CRITICAL):
**ONLY mark as "no changes" when ALL criteria are met:**
1. **NO CONTENT CROPPING**: All content is fully visible within viewport boundaries
2. **PROPER SIZING**: Content fits perfectly within specified dimensions without overflow
3. **EKONA/SWISS RED COMPLIANCE**: all secondary elements use correct brand colors (#dc261e for Ekona red, #ff0000 for Swiss red)
4. **MEANINGFUL CONTENT**: Content effectively communicates the slide's purpose
5. **VISUAL QUALITY**: Professional appearance with proper hierarchy and spacing

EVALUATION CRITERIA:
• Does the visualization effectively communicate the slide's purpose?
• Is the content well-organized and visually clear?
• Are all required elements present and properly positioned?
• Does the design enhance understanding of the intended message?
• **CRITICAL**: Is ALL content visible without cropping or overflow?
• **CRITICAL**: Are all secondary elements using correct Ekona/Swiss red brand colors?

INSTRUCTIONS:
1. Review the slide's purpose and requirements above
2. Examine the rendered image to see how the current HTML performs
3. **CRITICAL CHECK**: Verify NO content is cropped or overflowing
4. **CRITICAL CHECK**: Verify all secondary elements use correct brand colors
5. Determine if the HTML successfully fulfills the slide's purpose
6. If improvements are needed, refine the HTML code to better meet the requirements
7. **FINAL DECISION**: Only mark as "no changes" when ALL criteria are met

🚨 FINAL DECISION RULE: Only mark as "no changes" when ALL criteria are met - no cropping, proper colors, meaningful content.
```

#### C. Final Content Validation
```python
async def _validate_final_content(
    self, html_content: str, slide_purpose: str, slide_number: int, 
    project_id: str = None, slide_id: str = None
) -> Optional[dict]:
    """
    Advanced final content validation after iteration is complete.
    Checks if content is meaningful, properly sized, and brand compliant.
    """
    # Validation criteria:
    # 1. CONTENT MEANINGFULNESS: Does the content effectively communicate the slide's purpose?
    # 2. NO CROPPING: Is ALL content visible within viewport boundaries?
    # 3. BRAND COMPLIANCE: Are all secondary elements using correct Ekona/Swiss red colors?
    # 4. PROFESSIONAL QUALITY: Is the design polished and business-appropriate?
    # 5. PURPOSE ALIGNMENT: Does the visualization support the slide's objectives?
```

### 6. Complete Iteration Flow with Final Validation

```
HTML Refinement Loop:
1. Generate HTML → Render to Image → Send to LLM
2. LLM evaluates using Enhanced System + User prompts
3. Decision Point:
   ├─ IF LLM suggests changes → Continue to next iteration
   └─ IF LLM says "no changes" → Proceed to Final Validation
4. Final Content Validation:
   ├─ IF validation passes → Mark as FINAL and complete
   └─ IF validation fails → Continue with additional iteration
5. Max iterations (3) reached → Force mark as FINAL
```

## Summary of Changes

### Files Modified:
1. **`src/html_prompt_manager.py`**
   - Added `_calculate_dynamic_font_sizes()` method
   - Enhanced system prompt generation with dynamic font sizing
   - Always enforce strict sizing rules

2. **`html_prompts/templates/html_generation_template.txt`**
   - Added critical viewport constraint requirements
   - Added mandatory color enforcement
   - Added strict content sizing rules
   - Added content fitting strategy

3. **`templates/ekona_slides_template_new/html_prompts/templates/html_requirements.txt`**
   - Enhanced viewport constraint requirements
   - Updated color enforcement for secondary elements
   - Added aggressive font sizing rules
   - Updated example layouts with smaller fonts

4. **`templates/html_prompts_default/templates/html_requirements.txt`**
   - Enhanced viewport constraint requirements
   - Updated color enforcement for secondary elements
   - Added aggressive font sizing rules
   - Updated example layouts with smaller fonts

5. **`src/agents.py`**
   - Enhanced system prompt with final version decision criteria
   - Enhanced user prompt with critical checks
   - Added final content validation method
   - Improved iteration control logic

### Key Improvements:
1. **Dynamic Font Sizing**: Automatically calculates appropriate font sizes based on placeholder dimensions
2. **Aggressive Spacing**: Reduced padding, margins, and gaps to maximize content space
3. **Color Enforcement**: Ensures all secondary elements (lines, borders) use Ekona/Swiss red
4. **Content Fitting Strategy**: Prioritizes content fitting over aesthetics
5. **Final Validation**: Additional LLM check after iteration completes
6. **Strict Iteration Control**: Only marks as final when ALL criteria are met

### Expected Results:
1. **HTML content will respect placeholder dimensions** - no more cropping
2. **Text will be appropriately sized** for the available space
3. **All secondary elements will be red** (Ekona/Swiss red)
4. **Content will fit perfectly** within viewport constraints
5. **Professional appearance** with consistent brand colors
6. **Better iteration control** with final validation

## Testing Recommendations

1. **Test with various placeholder sizes** to verify dynamic font sizing
2. **Verify color compliance** for all secondary elements
3. **Check content fitting** within different viewport dimensions
4. **Validate iteration control** with final content validation
5. **Test edge cases** with very small placeholders

## Future Enhancements

1. **Machine Learning**: Train models to predict optimal font sizes
2. **A/B Testing**: Compare different font sizing strategies
3. **User Feedback**: Incorporate user preferences for font sizes
4. **Performance Optimization**: Cache font size calculations
5. **Accessibility**: Ensure minimum readable font sizes
