# 🤖 Auto Slides Generator

An AI-powered PowerPoint presentation generator that automatically creates professional slides based on any topic you provide. Using OpenAI's GPT models, it intelligently selects appropriate slide layouts and generates engaging content.

## ✨ Features

- **AI-Powered Content Generation**: Uses OpenAI GPT models to create relevant, engaging slide content
- **Intelligent Presentation Planning**: LLM decides optimal number of slides and strategically reuses layouts
- **Smart Layout Selection**: Automatically chooses the best slide layouts for your topic
- **Advanced Markdown Formatting**: LLM generates markdown content that's automatically converted to professional PowerPoint formatting
- **Custom Placeholder Support**: Works with any custom placeholder names and instructional text from slide master
- **Chart Creation with ekona Branding**: Automatically creates professional charts using python-pptx with ekona brand colors
- **Template-Based**: Works with your existing PowerPoint templates
- **Font & Style Preservation**: Maintains original template formatting while applying markdown styling
- **Dynamic Model Generation**: Creates Pydantic models based on your template for perfect placeholder matching
- **Modular Architecture**: Clean, maintainable code with separate modules for different functions
- **Command-Line Interface**: Easy-to-use CLI with multiple options
- **Content Preview**: Preview generated content before creating slides
- **Layout Analysis**: Understand your template's available layouts

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.8+
- OpenAI API key
- PowerPoint template file

### 2. Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

### 3. Setup

1. **Create a `.env` file** in the project root:
```bash
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS=2000
```

2. **Ensure you have a PowerPoint template** named `template.pptx` in the project root, or specify a different template with the `--template` option.

### 4. Basic Usage

Generate a presentation on any topic:

```bash
python auto_slides.py "Introduction to Machine Learning"
```

## 📖 Usage Examples

### Basic Generation
```bash
# Generate slides on a topic
python auto_slides.py "Climate Change Solutions"

# Specify custom output name
python auto_slides.py "Data Science Basics" --output data_science_intro

# Use a different template
python auto_slides.py "Product Strategy" --template custom_template.pptx
```

### Advanced Options
```bash
# Preview content without creating slides
python auto_slides.py "Artificial Intelligence" --preview

# Use specific slide layouts
python auto_slides.py "Marketing Strategy" --layouts 0,1,3,5

# Analyze your template layouts
python auto_slides.py --analyze
```

### Full Example
```bash
python auto_slides.py "Python Programming for Beginners" \
  --output python_course \
  --template educational_template.pptx \
  --layouts 0,1,2,4,6 \
  --preview
```

## 🏗️ Project Structure

```
Powerpoint Slide Creator/
├── src/                          # Core modules
│   ├── __init__.py
│   ├── layout_analyzer.py        # Analyzes PowerPoint layouts
│   ├── llm_client.py            # OpenAI API integration
│   ├── content_generator.py     # Orchestrates content generation
│   └── slide_generator.py       # Creates actual PowerPoint slides
├── auto_slides.py               # Main CLI entry point
├── slide_creator.py             # Template analysis utility
├── template.pptx                # Default PowerPoint template
├── requirements.txt             # Python dependencies
├── .env                        # Environment variables (create this)
└── README.md                   # This file
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file with the following variables:

```bash
# Required
OPENAI_API_KEY=your_api_key_here

# Optional (with defaults)
OPENAI_MODEL=gpt-4o-mini          # AI model to use
OPENAI_MAX_TOKENS=2000            # Maximum tokens per request
```

### Command-Line Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--output` | `-o` | Output file path (without extension) | Auto-generated |
| `--template` | `-t` | PowerPoint template file | `template.pptx` |
| `--layouts` | `-l` | Specific layout indices to use | Auto-selected |
| `--preview` | `-p` | Show content preview only | False |
| `--analyze` | `-a` | Analyze template layouts | False |
| `--api-key` | | OpenAI API key (alternative to .env) | From environment |

## 🎨 How It Works

1. **Template Analysis**: The system analyzes your PowerPoint template to understand available slide layouts and their placeholders.

2. **Layout Selection**: Using AI, it selects the most appropriate layouts for your topic, considering factors like content flow and presentation structure.

3. **Content Generation**: For each selected layout, the AI generates relevant, engaging content that fits the placeholder types and overall topic.

4. **Slide Creation**: The system creates the PowerPoint presentation by filling the selected layouts with generated content.

## 📋 Modules Overview

### `layout_analyzer.py`
- Analyzes PowerPoint template layouts
- Identifies placeholders and their types
- Categorizes layouts by purpose (title, content, etc.)

### `llm_client.py`
- Handles OpenAI API communication
- Manages prompt engineering for layout selection and content generation
- Includes error handling and fallback strategies

### `content_generator.py`
- Orchestrates the content generation process
- Combines layout analysis with LLM content creation
- Provides presentation planning and content preview

### `slide_generator.py`
- Creates actual PowerPoint presentations
- Handles slide creation and placeholder population
- Manages file output and formatting

## 🧪 Testing

Test the layout analysis:
```bash
python slide_creator.py
```

Analyze your template:
```bash
python auto_slides.py --analyze
```

Preview content generation:
```bash
python auto_slides.py "Your Topic" --preview
```

## 🔍 Troubleshooting

### Common Issues

**"Template file not found"**
- Ensure `template.pptx` exists in the project root
- Or specify a different template with `--template`

**"OpenAI API key not found"**
- Create a `.env` file with your API key
- Or pass the key with `--api-key`

**"No slide contents generated"**
- Check your internet connection
- Verify your OpenAI API key is valid
- Try a more specific or descriptive topic

**Layout-related errors**
- Run `--analyze` to understand your template's layouts
- Use `--layouts` to specify valid layout indices

### Debug Mode

Add `--debug` to any command for detailed error information:
```bash
python auto_slides.py "Your Topic" --debug
```

## 🎨 Formatting & Style Preservation

The Auto Slides Generator **automatically preserves** your PowerPoint template's original formatting, ensuring professional, consistent presentations.

### 🆕 NEW: Template-First Formatting Approach

**FIXED ISSUE**: Previously, content was capped at 20pt font size regardless of template design. Now the system **preserves your template's exact font sizes and styles**.

- **Your Template Rules**: If your title placeholder is Calibri Bold 60pt, content will be Calibri Bold 60pt
- **No Font Size Caps**: Removes the previous 20pt maximum limitation
- **Smart Preservation**: Captures template formatting before applying markdown
- **Graceful Fallbacks**: Handles theme-controlled properties safely

### How It Works

- **Template Capture**: System reads your template's font sizes, styles, and colors BEFORE generating content
- **Markdown Enhancement**: Applies **bold**, *italic*, headers, and bullets while preserving base formatting
- **Theme Inheritance**: Generated content inherits font sizes, colors, and styles from your template's theme
- **Placeholder Respect**: Different placeholder types (title, content, subtitle) maintain their distinct formatting
- **No Override**: The system doesn't impose uniform font sizes - your template's design rules apply
- **Professional Output**: Maintains visual hierarchy and brand consistency

### What This Means

✅ **Title placeholders** use your template's title formatting (e.g., Calibri Bold 60pt)  
✅ **Content placeholders** use body text formatting (e.g., Calibri Regular 18pt)  
✅ **Bullet point levels** maintain proper hierarchy with different sizes  
✅ **Colors and fonts** match your template's theme exactly  
✅ **Markdown formatting** (bold, italic) enhances content without overriding font sizes
✅ **Brand consistency** is automatically maintained  

### Before vs After

**Before (Fixed Sizing):** All text at 12pt or 18pt regardless of placeholder type  
**After (Theme Preservation):** Title = 28pt, Body = 18pt, Sub-bullets = 16pt, etc. (as defined in your template)

This ensures your generated presentations look professionally designed and maintain your organization's visual standards.

## 🧠 Intelligent Presentation Planning

The Auto Slides Generator now features **intelligent presentation planning** that revolutionizes how presentations are created.

### How It Works

Instead of being limited to one slide per layout, the LLM now:

1. **Analyzes your topic** to determine optimal presentation structure
2. **Decides slide count** based on content complexity (typically 3-8 slides)
3. **Strategically reuses layouts** when appropriate for the content
4. **Creates logical flow** with purpose-driven slide sequence

### Example: "Machine Learning Basics"

The LLM generated a 7-slide presentation:
```
Slide 1: Introduction (Title Slide)
Slide 2: What is ML? (Title and Text Content) ← Layout reuse
Slide 3: Types of ML (Title and Text Content) ← Layout reuse  
Slide 4: ML Process (Single Chart Slide)
Slide 5: Applications (Title and Text Content) ← Layout reuse
Slide 6: Challenges (Title and Text Content) ← Layout reuse
Slide 7: Conclusion (Title Slide) ← Layout reuse
```

### Benefits

✅ **Optimal Coverage**: LLM determines ideal slide count for comprehensive coverage  
✅ **Strategic Reuse**: Same layout used multiple times when content type matches  
✅ **Professional Flow**: Logical progression from introduction to conclusion  
✅ **Contextual Content**: Each slide serves a specific purpose in the narrative  
✅ **Flexible Structure**: Not constrained by template layout count  

This intelligent approach creates more comprehensive, engaging presentations that adapt to your topic's specific needs.

## 📊 Chart Creation with ekona Branding

The Auto Slides Generator now **automatically creates professional charts** when chart placeholders are detected in your template.

### How It Works

When the system encounters a chart placeholder (Type: CHART), it:

1. **Detects Chart Placeholders**: Automatically identifies chart placeholders in your template
2. **Analyzes Content Context**: Determines appropriate chart type based on content keywords
3. **Creates Actual Charts**: Uses python-pptx library to generate real charts (not just text)
4. **Applies ekona Brand Colors**: Charts use your brand color palette consistently

### ekona Brand Color Palette

Charts are automatically styled with ekona's brand colors:

- **Primary Red**: RGB(220, 38, 30) - Main brand color
- **Dark Grey**: RGB(64, 64, 64) - Professional accent
- **Medium Red**: RGB(230, 69, 62) - Secondary brand color  
- **Light Grey**: RGB(128, 128, 128) - Supporting color
- **Black & White**: For contrast and clarity

### Supported Chart Types

The system intelligently selects chart types based on content:

- **Column Charts**: For comparisons and metrics
- **Bar Charts**: For horizontal data presentation
- **Line Charts**: For trends and time-series data
- **Pie Charts**: For distributions and percentages
- **Area Charts**: For cumulative data visualization

### Example: Financial Dashboard

When generating a "Financial Performance Dashboard" presentation:
```
✅ Successfully created pie chart: Growth Metrics
✅ Chart uses ekona brand colors automatically
✅ Professional styling with proper fonts and sizing
```

### Technical Implementation

- **Chart Detection**: Uses `PP_PLACEHOLDER.CHART` type detection
- **Chart Creation**: `python-pptx` CategoryChartData and chart insertion
- **Brand Styling**: Automatic color application, font styling, and axis formatting
- **Error Handling**: Graceful fallback to text if chart creation fails

This ensures your presentations maintain consistent visual branding while providing rich data visualization capabilities.

## 🎨 Advanced Markdown Formatting

The system now features **intelligent markdown processing** that automatically converts AI-generated markdown content into professional PowerPoint formatting.

### Supported Markdown Elements

#### **Headers**
- `# Main Header` → Large bold title (24pt)
- `## Section Header` → Medium bold header (20pt)  
- `### Subsection` → Small bold header (18pt)

#### **Text Emphasis**
- `**Bold Text**` → **Bold formatting** in PowerPoint
- `*Italic Text*` → *Italic formatting* in PowerPoint
- Combined: `**Bold and *italic* text**` → Proper mixed formatting

#### **Lists**
- `- Bullet point` → Properly indented bullet lists
- `* Alternative bullets` → Also creates bullet lists
- `1. Numbered item` → Numbered lists with proper indentation
- `2. Second item` → Sequential numbering

#### **Complex Content**
```markdown
# Implementation Strategy
Here are the **key steps** for success:

## Phase 1: Planning
- **Define objectives** clearly
- *Identify stakeholders* and requirements
- Create detailed project timeline

## Phase 2: Development  
1. **Setup infrastructure** and tools
2. *Implement core features* systematically
3. **Test thoroughly** before deployment
```

### How It Works

1. **LLM Generation**: AI creates content in markdown format with proper structure
2. **Intelligent Parsing**: System analyzes markdown syntax and identifies elements
3. **PowerPoint Conversion**: Converts to native PowerPoint formatting (bold, italic, headers, lists)
4. **Template Integration**: Applies formatting while preserving your template's styling

### Benefits

✅ **Professional Formatting**: Automatic bold, italic, headers, and lists  
✅ **Consistent Structure**: Well-organized content with proper hierarchy  
✅ **Visual Appeal**: Enhanced readability with varied font sizes and emphasis  
✅ **Time Saving**: No manual formatting required  
✅ **Template Compatibility**: Works with any PowerPoint template

## 📝 Best Practices

### Topic Selection
- Use clear, specific topics: ✅ "Introduction to Machine Learning" vs ❌ "ML"
- Include context when helpful: ✅ "Marketing Strategy for SaaS Startups"
- Avoid overly broad topics: ✅ "Python Data Structures" vs ❌ "Programming"

### Template Design
- Use consistent placeholder naming
- Include variety in layout types (title, content, comparison, etc.)
- Test layouts with `--analyze` before generating

### Workflow
1. First, analyze your template: `--analyze`
2. Preview content: `--preview`
3. Generate with specific layouts if needed: `--layouts`
4. Iterate and refine

## 🔧 Troubleshooting

### Placeholder Warnings

If you see warnings like `Warning: Placeholder 'Subtitle' not found`, this typically means:

**Issue**: PowerPoint assigns different names to placeholders when creating slides vs. analyzing layouts.

**Root Cause**: 
- **Template analysis** finds: `"Title", "Subtitle", "Random Animal Name here"`
- **Actual slide creation** assigns: `"Title 1", "Text Placeholder 2", "Text Placeholder 4"`

**Solution**: The system includes enhanced placeholder matching that automatically handles:
- `"Title"` → `"Title 1"`
- `"Subtitle"` → `"Text Placeholder 2"`
- `"Text Content Placeholder"` → `"Content Placeholder 2"`
- `"Large Chart Placeholder"` → `"Chart Placeholder 2"`
- **Custom names** → Automatically mapped using intelligent pattern matching

**For Custom Placeholder Names**: 
The system can handle ANY custom placeholder names (like "Random number to be inserted here") through:
1. **Dynamic Placeholder Detection**: Creates slides first, then generates content for actual placeholder names
2. **Smart Pattern Matching**: Maps content using placeholder types and positions
3. **Zero-configuration**: Works automatically without manual mapping

**Prevention**:
- Use the template layout inspector: `python template_layout_inspector.py`
- Verify placeholder names match expected patterns
- Test with `--preview` before generating full presentations

### Empty Slides

If slides appear empty:
- Check that your template layouts have placeholders
- Some layouts (like logo slides) intentionally have no placeholders
- Use `--analyze` to see which layouts have content placeholders

### Content Generation Issues

If content seems inappropriate:
- Make your topic more specific
- Use `--preview` to review content before generating slides
- Try different layout selections with `--layouts`

## 🤝 Contributing

This project follows clean, modular architecture principles:

- Keep files small and focused (<200 lines)
- Write comprehensive comments and documentation
- Use clear, descriptive naming
- Implement error handling with graceful fallbacks
- Test functionality after changes

## 📄 License

This project is for internal use. Please ensure you comply with OpenAI's usage policies when using their API.

## 🆘 Support

For issues or questions:
1. Check this README for common solutions
2. Use `--analyze` to understand your template
3. Try `--preview` to debug content generation
4. Use `--debug` for detailed error information 