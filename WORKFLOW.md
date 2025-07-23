# PowerPoint Slide Creator Workflow Documentation

## Overview

This document outlines the complete workflow of the PowerPoint Slide Creator, an AI-powered system that generates professional presentations using a sophisticated agent-based architecture. The system uses Langgraph for workflow orchestration and Langfuse for comprehensive monitoring and analytics.

## High-Level Architecture

The system follows a modular, agent-based architecture where each agent is responsible for a specific aspect of the presentation generation process. The workflow is orchestrated through the `SlideGenerationWorkflow` class, which coordinates the following agents:

1. Layout Analysis Agent
2. Presentation Planning Agent
3. Content Generation Agent
4. HTML Content Generation Agent
5. Quality Review Agent
6. Slide Assembly Agent
7. Icon Validation Agent

## Detailed Workflow Steps

### 1. Layout Analysis (LayoutAnalysisAgent)
- **Input**: PowerPoint template file
- **Process**:
  - Analyzes template layouts using `LayoutAnalyzer`
  - Creates dynamic Pydantic models for structured content generation
  - Maps placeholder types and capabilities
- **Output**: Layout information and dynamic models

### 2. Presentation Planning (PresentationPlanningAgent)
- **Input**: Topic, layout information
- **Process**:
  - Creates intelligent presentation structure
  - Determines optimal slide sequence
  - Selects appropriate layouts for content types
  - Identifies slides requiring HTML visualization
- **Output**: Detailed presentation plan with slide specifications

### 3. Content Generation (ContentGenerationAgent)
- **Input**: Presentation plan, topic
- **Process**:
  - Generates contextual content for each slide
  - Ensures content coherence across presentation
  - Uses dynamic models for structured generation
  - Considers full presentation context
- **Output**: Generated slide contents

### 4. HTML Content Generation (HTMLContentGenerationAgent)
- **Input**: Slide contents, presentation plan
- **Process**:
  - Identifies slides requiring HTML visualization
  - Generates HTML content for:
    - Timelines
    - Process flows
    - Comparisons
    - Data visualizations
    - Complex diagrams
  - Ensures proper viewport dimensions
  - Applies Ekona theme and styling
- **Output**: Enhanced slide contents with HTML visualizations

### 5. Quality Review (QualityReviewAgent)
- **Input**: Generated slide contents
- **Process**:
  - Reviews content quality
  - Calculates quality metrics:
    - Content completeness
    - Topic relevance
    - Slide count
    - Placeholder utilization
- **Output**: Quality assessment and metrics

### 6. Slide Assembly (SlideAssemblyAgent)
- **Input**: Final slide contents
- **Process**:
  - Creates PowerPoint presentation
  - Populates slides with content
  - Handles icon placement
  - Manages HTML rendering
- **Output**: Assembled PowerPoint file

### 7. Icon Validation (IconValidationAgent)
- **Input**: Assembled presentation with potential icon errors
- **Process**:
  - Validates icon names
  - Suggests corrections for invalid icons
  - Ensures icon compatibility
- **Output**: Icon corrections if needed

## Error Handling and Retry Logic

The workflow includes comprehensive error handling:
- Each agent has dedicated error recovery
- Icon validation includes retry mechanism
- HTML generation has fallback options
- Quality review provides non-blocking feedback

## Monitoring and Analytics

The system uses Langfuse for comprehensive monitoring:
- Complete workflow tracing
- LLM call monitoring
- Content quality metrics
- Performance analytics
- Error tracking

## File Structure

Key components and their locations:
```
src/
├── agent_main.py         # Main entry point
├── agents.py            # Core agent implementations
├── workflow.py          # Workflow orchestration
├── html_content_agent.py # HTML generation
├── layout_analyzer.py   # Template analysis
├── llm_client.py       # LLM interaction
├── html_renderer.py    # HTML rendering
├── icon_manager.py     # Icon handling
└── monitoring.py       # Analytics and monitoring
```

## Usage

Basic usage:
```python
python -m src.agent_main "Your Topic Here"
```

Options:
- `--output/-o`: Custom output filename
- `--template/-t`: Use different template file
- `--layouts/-l`: Specify which layouts to use
- `--preview/-p`: Preview workflow without creating slides
- `--analyze/-a`: Analyze template layouts
- `--debug`: Enable debug mode

## Environment Setup

Required environment variables:
```
OPENAI_API_KEY=your_api_key_here
LANGFUSE_PUBLIC_KEY=your_public_key  # Optional
LANGFUSE_SECRET_KEY=your_secret_key  # Optional
```

## Best Practices

1. **Template Design**:
   - Use consistent layout structure
   - Include HTML-capable placeholders
   - Maintain clear placeholder naming

2. **Content Generation**:
   - Provide detailed topic information
   - Use specific layout indices when needed
   - Enable monitoring for better insights

3. **HTML Visualization**:
   - Follow viewport requirements
   - Use provided theme colors
   - Implement static-friendly designs

4. **Icon Usage**:
   - Use valid Lucide icon names
   - Consider icon context
   - Plan for fallbacks

## Monitoring and Debugging

1. **Debug Mode**:
   - Enables detailed logging
   - Saves HTML debug files
   - Shows agent progress

2. **Langfuse Integration**:
   - Tracks LLM calls
   - Monitors execution time
   - Records quality metrics

3. **HTML Debug**:
   - Saves generated HTML
   - Shows rendering issues
   - Helps troubleshoot visualizations 

   