# PowerPoint Slide Creator

An AI-powered slide generation system using **agent-based architecture** with **unified Langfuse tracing** for comprehensive monitoring and analytics.

## 🌟 Key Features

### **🤖 Agent-Based Architecture**
- **6 Specialized Agents**: Layout Analysis → Planning → Content Generation → **HTML Visualization** → Quality Review → Assembly
- **LangGraph Orchestration**: Coordinated workflow with error handling and retry logic
- **Unified Generation**: Single workflow system - eliminates duplicate content generation
- **Modular Design**: Each agent handles specific aspects of presentation creation

### **📊 Unified Langfuse Tracing** ✨ **NEW**
- **Single Comprehensive Trace**: Complete workflow visibility in one unified trace
- **End-to-End Monitoring**: Track all 6 agents and LLM calls in sequence
- **Enhanced Analytics**: Better insights into workflow performance and costs
- **Langchain Integration**: Uses `CallbackHandler` for proper trace unification

### **🧠 Enhanced Content Generation**
- **🆕 Unified Generation**: All slides generated in one LLM call with full presentation context for maximum coherence
- **Contextual Awareness**: Each slide generated with full presentation context
- **Presentation Outline**: Shows complete slide structure before generation
- **Dynamic Models**: Perfect placeholder matching using Pydantic models
- **Quality Assessment**: Content completeness and relevance metrics

### **🎨 Advanced Slide Creation**
- **Layout Analysis**: Automatic template analysis and dynamic model creation
- **Intelligent Planning**: LLM-powered slide structure optimization
- **Icon Integration**: Automatic icon insertion with visual elements
- **Chart Generation**: Data visualization with branded styling
- **🆕 HTML Visualizations**: Intelligent detection and generation of custom visualizations

## 🎯 Enhanced Detailed Purpose Specifications ✨ **NEW**

During presentation planning, content generation, and HTML content generation, the system now uses **comprehensive detailed purpose specifications** to ensure crystal-clear alignment throughout the entire pipeline.

### **Detailed Specification Framework**
For every slide, the presentation planner generates:

- **🎯 Basic Purpose**: Clear 1-2 sentence slide objective
- **📋 Detailed Purpose**: Comprehensive 3-4 sentence explanation of what should be represented
- **🏗️ Content Structure**: Specific organization requirements (e.g., "two-column comparison", "numbered list of 5 steps")
- **🎨 Visual Elements**: Required visual components (e.g., "icons showing growth, timeline markers, comparison arrows")
- **📝 Key Information**: 3-5 essential information points that must be included
- **🖼️ HTML Requirements** *(for HTML slides)*: Specific visualization requirements (e.g., "horizontal timeline with 4 milestones, each with date, title, and description")

### **Enhanced Pipeline Flow**
```python
# Presentation Planning → Detailed Specifications Generated
slide_spec = SlideSpec(
    layout_index=3,
    slide_title="Project Timeline Overview",
    slide_purpose="Present project phases and key milestones",
    is_html=True,
    detailed_purpose="Provide comprehensive project roadmap that demonstrates structured approach...",
    content_structure="Title explaining timeline scope, horizontal timeline with clear phases",
    html_requirements="Horizontal timeline with 5 major milestones spanning 6 months...",
    visual_elements="Timeline markers, phase icons, progress indicators",
    key_information=["Discovery & Planning (Month 1)", "Development Phase (Months 2-4)", ...]
)

# Content Generation → Uses All Specifications
content_agent.generate_content(slide_spec)  # Considers all detailed specs

# HTML Generation → Implements Exact Requirements  
html_agent.generate_visualization(slide_spec)  # Follows HTML requirements precisely
```

### **Benefits of Detailed Specifications**
- **🎯 Precise Content**: Content generation follows exact requirements rather than generic instructions
- **🎨 Targeted HTML**: HTML visualizations implement specific layout and content requirements
- **🔄 Perfect Alignment**: All agents work from the same detailed plan, ensuring consistency
- **📊 Better Results**: More relevant, brand-aligned content that serves the presentation's purpose

## 🎨 HTML Content Generation Agent ✨ **NEW**

The **HTML Content Generation Agent** automatically detects when slide content would benefit from visual representation and generates stunning HTML visualizations that are rendered as ultra-high-resolution images (2560x1440 with 2x scaling) and inserted into picture placeholders.

### **Automatic Detection**
The agent intelligently identifies content that should be visualized based on:
- **Picture Placeholders**: Only processes actual picture/image placeholders (not icons)
- **Content Keywords**: Detects timelines, processes, workflows, comparisons, metrics
- **Structured Data**: Recognizes dates, sequential steps, and multi-item lists

### **Supported Visualization Types**
- **📅 Timelines**: Project phases, roadmaps, chronological events
- **🔄 Process Flows**: Step-by-step workflows, methodologies  
- **📊 Comparison Charts**: Before/after, traditional vs modern
- **📈 Infographics**: Metrics, statistics, key performance indicators
- **🗺️ Diagrams**: Relationships, hierarchies, system architecture

### **Agent Integration**
```python
# The HTML agent runs automatically in the workflow
workflow = SlideGenerationWorkflow()
results = workflow.run(
    topic="Product Development Timeline",
    template_path="template.pptx",
    output_path="presentation"
)

# Agent workflow sequence:
# 1. Layout Analysis → 2. Planning → 3. Content Generation 
# 4. HTML Visualization → 5. Quality Review → 6. Assembly
```

### **Content Examples That Trigger HTML Generation**

**Timeline Content:**
```
Our development follows this timeline:
- Q1 2024: Requirements gathering and team formation
- Q2 2024: Design phase with user experience focus  
- Q3 2024: Development sprint with agile methodology
- Q4 2024: Testing, quality assurance, and launch prep
```

**Process Flow Content:**
```
Our development process includes these steps:
1. Discovery and planning
2. Design and prototyping
3. Development and testing
4. Quality assurance
5. Deployment and monitoring
```

**Comparison Content:**
```
Performance comparison:
- Traditional approach: 73% efficiency
- Our innovative approach: 96% efficiency
- Cost reduction: 40% compared to industry standard
```

### **Professional Styling**
All HTML visualizations use:
- **Ekona Branding**: Primary color #dc261e, secondary #404040
- **Modern Design**: Clean layouts, professional typography
- **High Resolution**: Ultra-crisp 2560x1440 rendering
- **Responsive Layout**: Optimized for PowerPoint integration

## 🎨 HTML Visualizations Feature

Create beautiful timelines, process flows, and custom visualizations that are automatically rendered as **ultra-high-resolution images** (2560x1440 with 2x device scaling) and inserted into slides:

### **Timeline Example**
```python
# Content that gets detected and rendered as a timeline
timeline_content = """timeline: Product Development Roadmap
2024 Q1 - Project Kickoff
2024 Q2 - Design Phase  
2024 Q3 - Development Sprint
2024 Q4 - Launch Preparation"""

# Use in picture placeholders - automatically rendered as image
slide_content = SlideContent(
    layout_index=4,  # Title and Picture layout
    content={
        "Title 1": "Development Timeline",
        "Picture Placeholder 2": timeline_content
    }
)
```

### **Process Flow Example**
```python
process_content = """process: Customer Onboarding
Welcome & Registration
Account Setup  
Product Training
First Success Milestone"""
```

### **Custom HTML**
```python
# Full custom HTML with CSS styling
custom_html = """
<div style="text-align: center; padding: 40px;">
    <h1 style="color: #dc261e;">Custom Visualization</h1>
    <div style="display: flex; justify-content: space-around;">
        <div style="background: #f8f8f8; padding: 20px; border-radius: 10px;">
            <h3>Before</h3><p>Manual Process</p>
        </div>
        <div style="background: #dc261e; color: white; padding: 20px; border-radius: 10px;">
            <h3>After</h3><p>AI-Powered</p>
        </div>
    </div>
</div>
"""
```

### **High-Resolution Image Quality**
- **Default Resolution**: 2560x1440 (QHD) with 16:9 aspect ratio
- **Device Scaling**: 2x pixel ratio for ultra-crisp rendering  
- **Professional Quality**: Perfect for presentations and large displays
- **Multiple Options**: HD (1920x1080), Standard (1280x720) also available

### **Installation for HTML Rendering**
```bash
# Option 1: Playwright (recommended for best quality)
pip install playwright
playwright install chromium

# Option 2: Selenium (reliable fallback) 
pip install selenium
# Requires Chrome browser installed

# Option 3: WeasyPrint (lightweight)
pip install weasyprint
```

See `example_html_timeline.py` for complete working examples.

## 📁 Project Structure

```
Powerpoint Slide Creator/
├── src/                          # Core application code
│   ├── agents.py                 # AI agent implementations
│   ├── workflow.py               # LangGraph workflow orchestration
│   ├── html_content_agent.py     # HTML visualization agent
│   ├── llm_client.py            # OpenAI/LLM integration
│   └── ...                      # Other core modules
├── generated_presentations/      # Generated PPTX files (git-ignored)
│   ├── agent_generated_*.pptx   # Auto-generated presentations
│   └── tests/                   # Test outputs
├── html_debug/                  # HTML debug files (git-ignored)
├── icon_cache/                  # Cached icon assets
├── ekona_slides_template_new.pptx # PowerPoint template (tracked)
├── auto_slides.py              # Main CLI entry point
├── .gitignore                  # Excludes generated files
└── README.md                   # This file
```

**Key Folders:**
- **`generated_presentations/`** - All output PPTX files (automatically created, git-ignored)
- **`src/`** - Core application logic and AI agents
- **`html_debug/`** - HTML visualization debug files (git-ignored)
- **`icon_cache/`** - Lucide icon assets for presentations

## 🚀 Quick Start

### Using the Agent-Based Workflow (Recommended)

```bash
# Preview the agent workflow
python -m src.agent_main "Your Topic" --preview

# Generate presentation with unified tracing
python -m src.agent_main "Your Topic" --template template.pptx --output result
```

**📁 Output Organization**: Generated presentations are automatically saved in the `generated_presentations/` folder, which is excluded from git tracking for clean repository management.

## 📈 Monitoring & Analytics

### **Langfuse Dashboard Integration**
- **Unified Traces**: See complete workflow in single trace view
- **Agent Performance**: Track each agent's execution time and success rate
- **LLM Usage**: Comprehensive token usage and cost tracking
- **Quality Metrics**: Content completeness and relevance scores

### **What You'll See in Langfuse:**

**Before (Individual Traces):**
```
❌ OpenAI-generation (slide 1)
❌ OpenAI-generation (slide 2) 
❌ OpenAI-generation (slide 3)
```

**Now (Unified Trace):**
```
✅ slide_generation_workflow
   ├── Layout Analysis Agent
   ├── Presentation Planning Agent  
   ├── Content Generation Agent
   ├── Quality Review Agent
   └── Slide Assembly Agent
```

## 🔧 Agent Workflow Details

### **1. 🔍 Layout Analysis Agent**
- Analyzes PowerPoint template layouts
- Creates dynamic Pydantic models for exact placeholder matching
- Identifies suitable layouts for different content types

### **2. 📋 Presentation Planning Agent** 
- Uses LLM to create intelligent slide structure
- Selects optimal layouts for each slide's purpose
- Ensures logical flow and narrative coherence

### **3. ✍️ Content Generation Agent**
- Generates contextual content with full presentation awareness
- Shows complete presentation outline before generation
- Uses dynamic models for perfect placeholder alignment

### **4. 🎯 Quality Review Agent**
- Assesses content completeness and topic relevance
- Provides quality metrics and improvement suggestions
- Ensures professional presentation standards

### **5. 🔧 Slide Assembly Agent**
- Creates final PowerPoint presentation
- Applies formatting, icons, and visual elements
- Handles template mapping and content placement

## 🛠️ Requirements

```bash
pip install -r requirements.txt
```

### Environment Setup

Create a `.env` file:
```env
OPENAI_API_KEY=your_openai_api_key
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com
```

## 📊 Example Output

```
🚀 Starting AI-powered slide generation workflow...
✅ Unified Langfuse tracing enabled for workflow
⚡ Executing agent workflow...

🔍 layout_analyzer: Analyzed 10 layouts
📋 presentation_planner: Created plan with 5 slides
✍️ content_generator: Generated content for 5 slides
🎯 quality_reviewer: Quality review complete (100% completeness)
🔧 slide_assembler: Presentation saved to output.pptx

🎉 Agent-based presentation generation completed successfully!
📈 View detailed analytics at your Langfuse dashboard
```

## 🎯 Benefits

- **🔄 Complete Workflow Visibility**: Unified traces show entire agent flow
- **📈 Better Analytics**: Comprehensive metrics across all agents  
- **🐛 Improved Debugging**: Full context when issues occur
- **💰 Cost Tracking**: Complete token usage across workflow
- **⚡ Performance Insights**: End-to-end workflow timing
- **🤖 Agent Performance**: Individual agent success rates and bottlenecks

## 🔬 Technical Architecture

- **Framework**: LangGraph for agent orchestration
- **LLM Integration**: Langchain with OpenAI ChatGPT
- **Monitoring**: Langfuse with unified callback tracing
- **Template Processing**: python-pptx for PowerPoint manipulation
- **Content Models**: Dynamic Pydantic models for structured output

## 📝 Recent Updates

### ✨ Version 2.0 - Unified Tracing & Enhanced Agents
- **🎯 Unified Langfuse Tracing**: Complete workflow in single trace
- **🤖 Agent-Based Architecture**: 5 specialized agents with LangGraph
- **📊 Enhanced Monitoring**: Comprehensive analytics and performance tracking
- **🧠 Contextual Content**: Presentation-aware slide generation
- **🎨 Quality Assessment**: Content completeness and relevance metrics

---

**🚀 Ready to create intelligent presentations with unified tracing!** 