# PowerPoint Template Creation Guide for AI Agents

This guide explains how to create and configure PowerPoint templates that work optimally with the AI agent-based slide generation system.

## Table of Contents
1. [Overview](#overview)
2. [Layout Naming Best Practices](#layout-naming-best-practices)
3. [Placeholder Configuration](#placeholder-configuration)
4. [Testing Your Template](#testing-your-template)
5. [Common Issues and Solutions](#common-issues-and-solutions)
6. [Advanced Tips](#advanced-tips)

## Overview

The AI agents analyze PowerPoint templates using the **Layout Analysis Agent** which extracts:
- Layout names and purposes
- Placeholder names, types, and dimensions
- Instructional text for content generation
- Placeholder positioning and relationships

This information is used to create **dynamic Pydantic models** that ensure content fits perfectly into your template's design.

## Layout Naming Best Practices

### 1. Access Layout Names
1. **Open PowerPoint** and go to **View → Slide Master**
2. **Right-click on each layout** in the thumbnail pane
3. **Select "Rename Layout"**

### 2. Naming Convention

Use **descriptive, purpose-driven names** that help the AI understand when to use each layout:

#### ✅ **Good Layout Names:**
```
✓ "Main Logo Start Slide - Should always be used as the first slide before any content"
✓ "Title Slide with subtitle and presenter name"
✓ "Title and Text Content"
✓ "Title and Picture"
✓ "Title and Picture generated from HTML"
✓ "Single Chart Slide"
✓ "Title and Two Column Content"
✓ "Slide with 6 icons and short text as a list of items"
✓ "Conclusion Slide"
✓ "Branding Slide should always be added at the end of the deck"
```

#### ❌ **Avoid Generic Names:**
```
✗ "Layout 1"
✗ "Content Slide"
✗ "Title and Content"
✗ "Section Header"
```

### 3. Layout Purpose Keywords

Include these keywords to help the **Layout Analysis Agent** categorize layouts:

- **`"Should always be used as the first slide"`** - For opening slides
- **`"Should always be added at the end"`** - For closing slides
- **`"Picture generated from HTML"`** - For HTML visualization slots
- **`"Chart"`** - For data visualization layouts
- **`"Two Column"`** - For side-by-side content
- **`"icons and short text"`** - For bullet-point style layouts

## Placeholder Configuration

### 1. Access Selection Pane

For each layout that has placeholders:
1. **Go to Home → Arrange → Selection Pane**
2. This shows all objects on the slide with their current names

### 2. Placeholder Naming Strategy

#### ✅ **Descriptive Placeholder Names:**
```
✓ "Title of the presentation"
✓ "Short Subtitle"
✓ "Presenter"
✓ "Text Content taking all the slide horizontally"
✓ "Picture from HTML"
✓ "Large Chart horizontal"
✓ "Text Content first column (half the slide)"
✓ "Text Content second column (half the slide)"
✓ "Icon 1", "Icon 2", etc.
✓ "Text Beside Icon 1", "Text Beside Icon 2", etc.
```

#### ❌ **Avoid Default Names:**
```
✗ "Content Placeholder 2"
✗ "Text Placeholder 3"
✗ "Picture 1"
✗ "Rectangle 4"
```

### 3. Font and Style Decision Process

#### **How AI Agents Handle Text Formatting**

The AI agents use a **template-first approach** for all text formatting decisions:

1. **Layout Analysis Agent** extracts existing formatting from placeholder instructional text
2. **Content Generation Agent** creates content that fits the extracted specifications
3. **Slide Assembly Agent** applies content while **preserving template formatting**

#### **Agent Responsibilities:**

| Agent | Font Decisions | How It Works |
|-------|---------------|--------------|
| **Layout Analysis Agent** | Extracts template font specifications | Reads placeholder text formatting and stores as layout metadata |
| **Content Generation Agent** | Determines content length and structure | Uses font size info to calculate appropriate content length |
| **Slide Assembly Agent** | Applies final formatting | Uses PowerPoint's `_set_placeholder_content()` which **preserves template formatting** |

⚠️ **Critical**: AI agents **DO NOT** set fonts directly. They rely entirely on your template's formatting.

### 4. Instructional Text Guidelines

Each placeholder should contain **sample instructional text** that demonstrates:

#### **For Text Placeholders:**
- **Font size** you want in the final output (CRITICAL for AI content length calculation)
- **Font style** and formatting (bold, italic, color, etc.)
- **Content type** and length expectations
- **Tone** and style guidelines

#### **Font Configuration Process:**

1. **In PowerPoint Slide Master Mode:**
   - Select each placeholder
   - Set the **exact font, size, color, and style** you want in final slides
   - Type instructional text using these formatting settings
   - The AI will generate content to fit these specifications

2. **Template Formatting Preservation:**
   - When AI agents populate placeholders, PowerPoint automatically applies the template's formatting
   - Content length is adjusted based on font size analysis
   - **No manual font setting required** in the agent code

##### **Formatting Examples:**

```
Title Placeholder (48pt, Bold, Ekona Red):
"A short title with maximum 6-8 words"

Subtitle Placeholder (24pt, Regular, Dark Gray):
"A short subtitle with maximum 5 words"

Content Placeholder (18pt, Regular, Black):
"• First key point with specific details and examples
• Second important point that provides value  
• Third point that concludes the main argument
• Keep each bullet point concise but informative"

Presenter Placeholder (16pt, Italic, Gray):
"Presenter name and title"
```

#### **Font Size Impact on Content Generation:**

The **Content Generation Agent** uses font size information to:

| Font Size Range | Content Strategy | Example Usage |
|----------------|------------------|---------------|
| **36pt+** | Very short titles (3-6 words) | Main slide titles |
| **24-32pt** | Short phrases (5-8 words) | Subtitles, section headers |
| **18-22pt** | Standard content (2-4 bullet points) | Main slide content |
| **14-16pt** | Detailed text (4-6 bullet points) | Supporting information |
| **12pt or less** | Fine print (disclaimers, notes) | Footer text, citations |

#### **For Image/HTML Placeholders:**
```
HTML Picture Placeholder:
"HTML-generated visualization will appear here"

Regular Picture Placeholder:
"Relevant image supporting the slide content"

Chart Placeholder:
"Data visualization chart showing key metrics"
```

#### **For Icon Placeholders:**
```
Icon Placeholder:
"[Icon representing the concept]"

Icon Text Placeholder:
"Brief description of the icon concept (2-3 words)"
```

### 4. Placeholder Sizing Considerations

The **Layout Analysis Agent** extracts pixel dimensions, so ensure:

- **Text placeholders** have appropriate width for content
- **Image placeholders** maintain proper aspect ratios (16:9 for landscape images)
- **Icon placeholders** are sized consistently across the layout
- **Multi-column layouts** have balanced spacing

## Testing Your Template

### 1. Run Layout Analysis

Use the test script to verify your template structure:

```bash
cd "/path/to/project"
python test_layout_export.py
```

This generates:
- **`layouts_export_[timestamp].json`** - Machine-readable layout data
- **`layout_summary_[timestamp].txt`** - Human-readable report

### 2. Verify Layout Analysis Output

Check that your template produces:

#### ✅ **Expected Output:**
```
🎨 Layout 4: Title and Text Content
   📝 Placeholders: 2
   🎯 Suitable for: title_slide
   📋 Placeholder details:
      1. Title (TITLE (1)) - 1200x139px
      2. Text Content taking all the slide horizontally (OBJECT (7)) - 1100x396px
```

#### ❌ **Problematic Output:**
```
🎨 Layout 2: Layout 2
   📝 Placeholders: 2
   🎯 Suitable for: general
   📋 Placeholder details:
      1. Content Placeholder 2 (BODY (2)) - 800x400px
      2. Text Placeholder 3 (BODY (2)) - 800x200px
```

### 3. Test Content Generation

Run a simple slide generation to verify placeholder mapping:

```bash
cd src
python -m agent_main "Test Topic" --output test_template_check
```

Verify that:
- All placeholders receive appropriate content
- Text formatting matches your specifications
- Layout selection makes sense for the content

## Common Issues and Solutions

### Issue 1: "Placeholder not found" Errors

**Symptoms:**
```
Warning: Placeholder 'Content Placeholder 2' not found
```

**Solutions:**
- ✅ Use descriptive names instead of default PowerPoint names
- ✅ Ensure all placeholders are named in Selection Pane
- ✅ Avoid special characters in placeholder names

### Issue 2: Content Doesn't Fit Properly

**Symptoms:**
- Text overflows placeholder boundaries
- Font sizes don't match template design

**Solutions:**
- ✅ Set instructional text with target font size
- ✅ Adjust placeholder dimensions to accommodate content
- ✅ Include length guidelines in instructional text

### Issue 3: Wrong Layout Selection

**Symptoms:**
- AI chooses inappropriate layouts for content

**Solutions:**
- ✅ Use specific, descriptive layout names
- ✅ Include purpose keywords in layout names
- ✅ Create layouts for specific content types (charts, images, etc.)

### Issue 4: HTML Content Not Rendering

**Symptoms:**
- HTML visualizations don't appear in slides

**Solutions:**
- ✅ Create layouts specifically for HTML content
- ✅ Include "Picture generated from HTML" in layout names
- ✅ Set appropriate aspect ratios for HTML placeholders

### Issue 5: Font Formatting Problems

**Symptoms:**
- Generated content doesn't match template font style
- Text appears with wrong font size or color
- Inconsistent formatting across slides

**Solutions:**
- ✅ **Set placeholder formatting in Slide Master mode** (not in normal view)
- ✅ **Use the exact fonts** you want in the final output when creating instructional text
- ✅ **Verify font availability** - use system fonts or embed custom fonts in template
- ✅ **Test formatting preservation** by running content generation and checking output

**Font Troubleshooting Steps:**
1. **Check Slide Master**: Ensure instructional text uses correct formatting
2. **Verify Font Installation**: Confirm fonts are available on generation system
3. **Test Template**: Run `test_layout_export.py` and verify font information
4. **Check Agent Logic**: Verify `_set_placeholder_content()` preserves formatting

### Issue 6: Content Length Mismatches

**Symptoms:**
- Content overflows placeholder boundaries
- Too little content for large placeholders
- Inconsistent content density

**Solutions:**
- ✅ **Set appropriate font sizes** in template to guide content length
- ✅ **Include length guidelines** in instructional text
- ✅ **Use placeholder dimensions** to indicate expected content volume
- ✅ **Test with actual content** to verify fit

## Advanced Tips

### 1. Layout Hierarchy

Structure layouts from **most specific** to **most general**:

1. **Specialized layouts** (charts, HTML, multi-column)
2. **Content-specific layouts** (title + text, title + image)
3. **Generic layouts** (basic title and content)

### 2. Consistent Naming Patterns

Use consistent naming patterns across layouts:

```
"Title Slide with [specific features]"
"[Content Type] Slide"
"[Layout Type] with [additional elements]"
```

### 3. Placeholder Relationships

For complex layouts, use naming that shows relationships:

```
"Icon 1" → "Text Beside Icon 1"
"Icon 2" → "Text Beside Icon 2"
"Left Column Content" → "Right Column Content"
"Main Chart" → "Chart Description"
```

### 4. Template Versioning

When updating templates:

1. **Test with layout analysis script** before deployment
2. **Regenerate layout cache** if structure changes significantly
3. **Document changes** in layout names or placeholder structure
4. **Verify backward compatibility** with existing content

### 5. Multi-Language Support

For international templates:

- Use **English placeholder names** (the AI works best with English)
- Include **language-specific formatting** in instructional text
- Set appropriate **text direction** and **font choices**

### 6. Font Strategy Best Practices

#### **Font Selection for AI Compatibility:**

1. **Use System Fonts** for maximum compatibility:
   ```
   ✅ Arial, Helvetica, Times New Roman, Calibri
   ✅ Open Sans, Roboto (if widely available)
   ❌ Custom or proprietary fonts (may not render on all systems)
   ```

2. **Font Hierarchy for Content Types:**
   ```
   Title Fonts: Bold, Sans-serif (Arial Black, Helvetica Bold)
   Content Fonts: Regular, Sans-serif (Arial, Calibri)
   Accent Fonts: Italic or Light weights for emphasis
   ```

3. **Brand Font Integration:**
   - **Embed custom fonts** in PowerPoint template if using brand fonts
   - **Test font availability** on the system running AI agents
   - **Provide fallback fonts** in template design

#### **Font Size Strategy for AI Content:**

The AI agents analyze font sizes to determine appropriate content length. Use this strategically:

```
Font Size Planning:
- 42pt+ : Major titles (2-4 words max)
- 32-36pt: Section headers (4-6 words)
- 24-28pt: Slide titles (6-8 words)  
- 18-20pt: Main content (3-5 bullet points)
- 14-16pt: Supporting text (5-7 bullet points)
- 12pt-  : Fine print, citations
```

#### **Color and Contrast Considerations:**

1. **High Contrast Text**: Ensures readability in generated slides
2. **Brand Color Usage**: Apply brand colors through template, not agent code
3. **Consistent Color Scheme**: Use template's color palette for text elements

#### **Font Formatting Examples by Content Type:**

```
Executive Summary Slide:
- Title: 36pt, Bold, Brand Color
- Bullets: 20pt, Regular, Dark Gray
- Max 3 bullet points for readability

Technical Detail Slide:
- Title: 28pt, Bold, Brand Color  
- Bullets: 16pt, Regular, Black
- Max 5 bullet points for completeness

Conclusion Slide:
- Title: 42pt, Bold, Brand Color
- Content: 24pt, Semi-bold, Dark Gray
- 1-2 key takeaway statements
```

## Template Validation Checklist

Before deploying a new template, verify:

### **Basic Structure:**
- [ ] All layouts have **descriptive, purpose-driven names**
- [ ] All placeholders have **meaningful names** (not defaults)
- [ ] All placeholders contain **instructional text** with proper formatting
- [ ] **Layout analysis** produces expected output structure
- [ ] **Test generation** works without placeholder mapping errors

### **Font and Formatting:**
- [ ] **Font families** are system fonts or properly embedded
- [ ] **Font sizes** are appropriate for content density (see font size strategy)
- [ ] **Font colors** provide sufficient contrast for readability
- [ ] **Font weights** (bold, italic) are used consistently across layouts
- [ ] **Instructional text** uses exact target formatting for each placeholder
- [ ] **Brand fonts** are embedded or have appropriate fallbacks

### **Layout Design:**
- [ ] **Aspect ratios** are appropriate for content types
- [ ] **Special layouts** (HTML, charts) are properly identified
- [ ] **Placeholder dimensions** accommodate expected content volume
- [ ] **Spacing** and alignment support content readability

### **Agent Integration:**
- [ ] **Content Generation Agent** produces appropriate content length for font sizes
- [ ] **Slide Assembly Agent** preserves template formatting during content insertion
- [ ] **Layout Analysis Agent** correctly extracts font information
- [ ] **Template changes** don't break existing agent functionality

## File Locations

- **Template file**: `ekona_slides_template_new.pptx`
- **Layout analysis script**: `test_layout_export.py`
- **Generated layout data**: `layouts_export_[timestamp].json`
- **Layout summary**: `layout_summary_[timestamp].txt`

---

**Remember**: The AI agents rely entirely on the template analysis to understand your design. Well-configured templates with clear naming and instructions result in better content generation and fewer formatting issues.