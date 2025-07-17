# 🤖 Auto Slides Generator

An AI-powered PowerPoint presentation generator that automatically creates professional slides based on any topic you provide. Using OpenAI's GPT models, it intelligently selects appropriate slide layouts and generates engaging content.

## ✨ Features

- **AI-Powered Content Generation**: Uses OpenAI GPT models to create relevant, engaging slide content
- **Smart Layout Selection**: Automatically chooses the best slide layouts for your topic
- **Template-Based**: Works with your existing PowerPoint templates
- **Font & Style Preservation**: Maintains original template formatting, font sizes, and theme styles
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

### How It Works

- **Theme Inheritance**: Generated content inherits font sizes, colors, and styles from your template's theme
- **Placeholder Respect**: Different placeholder types (title, content, subtitle) maintain their distinct formatting
- **No Override**: The system doesn't impose uniform font sizes - your template's design rules apply
- **Professional Output**: Maintains visual hierarchy and brand consistency

### What This Means

✅ **Title placeholders** use your template's title formatting (typically larger, bold)  
✅ **Content placeholders** use body text formatting (smaller, readable)  
✅ **Bullet point levels** maintain proper hierarchy with different sizes  
✅ **Colors and fonts** match your template's theme exactly  
✅ **Brand consistency** is automatically maintained  

### Before vs After

**Before (Fixed Sizing):** All text at 12pt or 18pt regardless of placeholder type  
**After (Theme Preservation):** Title = 28pt, Body = 18pt, Sub-bullets = 16pt, etc. (as defined in your template)

This ensures your generated presentations look professionally designed and maintain your organization's visual standards.

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