# PowerPoint Slide Creator

An AI-powered tool that generates professional PowerPoint presentations from text prompts using intelligent layout selection and content generation.

## 🆕 NEW: Icon Integration (Layout 8)

The system now supports **automatic icon selection and insertion** for Layout 8 ("Slide with icons and short text as a list of items"). 

### How Icon Integration Works

1. **Intelligent Icon Selection**: The LLM analyzes your slide content and automatically selects appropriate icons from 1600+ Lucide icons
2. **Swiss Red Styling**: All icons are automatically converted to Swiss red color to match your brand
3. **High Resolution**: Icons are converted to PNG format at optimal resolution for presentations
4. **Content-Aware**: Icons are chosen based on the semantic meaning of the accompanying text

### Layout 8 Structure

Layout 8 provides:
- 1 title placeholder: "Conclusion Title" 
- 3 icon placeholders: "Icon 1", "Icon 2", "Icon 3"
- 3 text placeholders: "Text Beside Icon 1", "Text Beside Icon 2", "Text Beside Icon 3"

Example usage:
```bash
python3 auto_slides.py "AI Business Solutions" --layouts "8"
```

This will generate a slide with:
- A title about AI Business Solutions
- 3 automatically selected icons (e.g., trending-up, users, lightbulb)
- 3 corresponding text descriptions (max 10 words each)
- All icons rendered in Swiss red

## Features

- **Intelligent Layout Selection**: AI automatically chooses the best slide layouts for your content
- **Dynamic Content Generation**: Creates engaging, contextually relevant slide content
- **Template-Based**: Works with your existing PowerPoint templates
- **Icon Integration**: Automatically selects and inserts relevant icons (Layout 8)
- **Chart Support**: Generates charts and data visualizations when appropriate
- **Markdown Formatting**: Supports rich text formatting in slide content

## Requirements

- Python 3.8+
- OpenAI API key
- PowerPoint template file

### Dependencies

```bash
pip install -r requirements.txt
```

For icon conversion (optional but recommended):
```bash
# macOS with Homebrew
brew install cairo

# Ubuntu/Debian
sudo apt-get install libcairo2-dev

# Windows
# Download and install Cairo libraries
```

## Quick Start

1. **Set up your environment**:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

2. **Generate a presentation**:
   ```bash
   python3 auto_slides.py "Your presentation topic"
   ```

3. **Use specific layouts** (including icon-enabled Layout 8):
   ```bash
   python3 auto_slides.py "Digital Transformation" --layouts "1,5,8,9"
   ```

## Available Layouts

- **Layout 0**: Main Logo Start Slide
- **Layout 1**: Title Slide with subtitle and presenter
- **Layout 2**: Why Ekona slide 
- **Layout 3**: Why Ekona slide 2
- **Layout 4**: Title and Picture
- **Layout 5**: Title and Text Content
- **Layout 6**: Single Chart Slide
- **Layout 7**: Title and Two Column Content
- **🆕 Layout 8**: Slide with icons and short text (NEW!)
- **Layout 9**: Conclusion Slide

## Icon Integration Details

### Icon Categories Available

- **Business**: briefcase, building, chart, graph, presentation, target, trending, users, team, office
- **Technology**: cpu, database, server, code, robot, computer, settings, gear, tool, wrench, monitor  
- **Communication**: message, mail, phone, chat, speak, voice, megaphone, bell, notification
- **Data**: bar-chart, pie-chart, analytics, stats, graph, trend, file, folder, document
- **UI Elements**: check, x, plus, minus, star, heart, thumb, eye, edit, trash, download
- **Arrows**: arrow, chevron, triangle, move, corner, expand
- **Social**: share, link, globe, network, users, person
- **Finance**: dollar, euro, pound, credit-card, bank, coin, wallet, payment
- **General**: Various other icons for flexibility

### Icon Selection Algorithm

The system uses a multi-step process:
1. **Content Analysis**: Extracts keywords from slide text
2. **Semantic Matching**: Maps content concepts to appropriate icons
3. **LLM Enhancement**: Uses AI to select the most contextually relevant icons
4. **Validation**: Ensures selected icons exist in the icon database
5. **Fallback**: Provides sensible defaults if selection fails

## Usage Examples

### Basic Usage
```bash
# Generate presentation with automatic layout selection
python3 auto_slides.py "Machine Learning in Healthcare"

# Use specific layouts including icons
python3 auto_slides.py "Customer Success Strategy" --layouts "1,5,8"

# Preview content before generating
python3 auto_slides.py "Product Roadmap" --preview
```

### Advanced Usage
```bash
# Analyze template layouts
python3 auto_slides.py --analyze

# Generate with custom output name
python3 auto_slides.py "Q4 Results" --output "quarterly_presentation"
```

## File Structure

```
src/
├── __init__.py
├── main.py                 # Main slide generation logic
├── content_generator.py    # LLM content generation
├── slide_generator.py      # PowerPoint slide creation
├── layout_analyzer.py      # Template layout analysis
├── llm_client.py          # OpenAI API integration
├── llm_models.py          # Pydantic models
├── dynamic_models.py      # Dynamic model generation
├── chart_generator.py     # Chart creation
├── markdown_formatter.py  # Text formatting
├── icon_manager.py        # Icon management and conversion (NEW!)
└── icon_selector.py       # AI-powered icon selection (NEW!)
```

## Testing Icon Integration

Run the icon integration test:
```bash
python3 test_icon_integration.py
```

This will test:
- Icon database creation
- Icon suggestion algorithm  
- Icon selection for sample content
- Template layout analysis
- Icon conversion (if Cairo libraries available)

## Configuration

### Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `OPENAI_MODEL`: Model to use (default: gpt-4o)

### Template Requirements

- Template must be a valid PowerPoint (.pptx) file
- Layout 8 should have picture placeholders for icons
- Placeholder names should match expected format

## Troubleshooting

### Icon Conversion Issues

If you see "Icon conversion not available":
1. Install Cairo libraries for your system
2. Install cairosvg: `pip install cairosvg`
3. Restart your terminal session

### Common Issues

- **"Layout 8 not found"**: Check your template file has the correct layout
- **"No icons selected"**: Verify your content has descriptive text
- **"OpenAI API error"**: Check your API key and quota

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly (including icon integration)
5. Submit a pull request

## License

This project is licensed under the MIT License. 