# PowerPoint Generation Workflow - Step by Step Guide

This document explains how individual slides are created and how the final deck is assembled in the ekona PowerPoint Slide Creator system.

## Overview: 6-Agent LangGraph Workflow

The system uses a **6-agent LangGraph workflow** that creates PowerPoint presentations through sequential processing. Here's the high-level flow:

```
Layout Analysis → Presentation Planning → Content Generation → HTML Content Generation → HTML Refinement → Image Processing → Quality Review → Slide Assembly → Icon Validation
```

The workflow supports three execution modes:
- **Full workflow**: Complete generation from topic to final presentation
- **Streamlined workflow**: For approved outlines (skips planning)  
- **Parallel workflow**: Processes slides concurrently for faster generation

---

## Step 1: Layout Analysis Agent (`src/agents.py:LayoutAnalysisAgent`)

**What happens:** The Layout Analysis Agent analyzes the PowerPoint template to understand available slide layouts and their placeholder structure.

**Key operations:**
- Reads the PowerPoint template file (`.pptx`)
- Extracts all slide layouts and their placeholders
- Creates **dynamic Pydantic models** for each layout based on placeholder names
- Converts placeholder dimensions from EMU to pixels: `int(placeholder.width.emu / 9525)`
- Stores layout information including placeholder positions, sizes, and types

**Outputs:**
- `layouts_info`: Complete layout analysis with placeholder details
- `dynamic_models`: Pydantic models for type-safe content generation
- Template validation and compatibility checks

**Database tracking:** Real-time updates to `workflow_states` table with execution time and status.

This creates the foundation for all subsequent agents by understanding exactly what content placeholders are available in each layout.

---

## Step 2: Presentation Planning Agent (`src/agents.py:PresentationPlanningAgent`)

**What happens:** The Presentation Planning Agent creates an intelligent slide structure and determines the optimal flow for the presentation.

**Key operations:**
- **Two modes of operation:**
  1. **LLM-generated planning**: Uses GPT-4o to create a presentation plan from scratch based on the topic
  2. **Approved outline conversion**: Converts user-approved outlines from interactive planning into executable slide specifications

- **Layout selection strategy**: Intelligently matches content types to appropriate layouts:
  - Text content → Text-based layouts
  - Timelines/processes → Timeline layouts  
  - Data/metrics → Chart layouts
  - Comparisons → Comparison layouts

- **Anti-sequential detection**: Monitors for lazy sequential layout assignment (1,2,3,4...) and warns if detected

- **Content type analysis**: Determines optimal visual content types:
  - `TIMELINE`: chronological sequences, process flows, roadmaps
  - `CHART`: data visualizations, metrics, hierarchies  
  - `COMPARISON`: before/after, pros/cons, feature comparisons
  - `VISUAL`: creative storytelling, transformations
  - `TEXT`: introductions, conclusions, bullet points

**Outputs:**
- `presentation_plan`: List of `SlideSpec` objects with detailed slide specifications
- `selected_layouts`: Array of layout indices strategically chosen for each slide
- Title, content type, and structural flow for each slide

**Database tracking:** Execution time and planning metrics stored in workflow states.

---

## Step 3: Content Generation Agent (`src/agents.py:ContentGenerationAgent`)

**What happens:** The Content Generation Agent creates the actual content for each slide based on the presentation plan, using full presentation context for coherent messaging.

**Key operations:**

- **Unified generation approach**: Generates ALL slide content in a single LLM call for better coherence and flow between slides
- **HTML-awareness**: Recognizes which slides are designated for HTML visualizations and prepares content accordingly  
- **Contextual understanding**: Each slide is generated with full awareness of the entire presentation structure
- **Dynamic model usage**: Uses the Pydantic models created by Layout Analysis to ensure content fits exactly into placeholder fields

**Generation process:**
1. **Primary method**: `generate_unified_presentation_content()` - Single LLM call for all slides
2. **Fallback method**: Individual slide generation if unified approach fails
3. **Content matching**: Ensures generated content maps precisely to template placeholder names

**Content types handled:**
- **Text content**: Titles, bullet points, descriptions
- **HTML-flagged content**: Special content designed for visualization (timelines, charts, comparisons)
- **Structured data**: Content that matches dynamic Pydantic models from layout analysis

**Outputs:**
- `slide_contents`: List of `SlideContent` objects with content mapped to placeholder fields
- Content is ready for either direct insertion or HTML visualization processing

**Database tracking:** Performance metrics and content generation statistics stored in workflow states.

---

## Step 4: HTML Content Generation Agent (`src/html_content_agent.py:HTMLContentGenerationAgent`)

**What happens:** The HTML Content Generation Agent automatically detects slide content that needs visual enhancement and converts descriptive text into interactive HTML visualizations.

**Key operations:**

- **Smart detection**: Analyzes slide content to identify opportunities for HTML visualizations (timelines, process flows, charts, comparisons)
- **Template-aware prompting**: Uses template-specific HTML prompts for consistent visual styling
- **Parallel processing**: Can process multiple slides concurrently for performance (configurable via `USE_PARALLEL_HTML_CONTENT`)
- **Dimension extraction**: Gets exact placeholder dimensions from layout analysis to create perfectly-sized visualizations

**HTML generation process:**
1. **Content analysis**: Examines each slide's descriptive content
2. **Opportunity detection**: Identifies content suitable for visualization (process steps, timelines, data)
3. **HTML conversion**: Transforms descriptive text into structured HTML with CSS styling
4. **Dimension matching**: Creates HTML with viewport classes matching placeholder dimensions: `class="w-[1577px] h-[603px]"`

**Supported visualization types:**
- **Timelines**: Sequential processes, roadmaps, chronological events
- **Process flows**: Step-by-step workflows with visual connections
- **Comparison charts**: Side-by-side feature comparisons, before/after
- **Custom diagrams**: Data visualizations, organizational charts

**Technical details:**
- Uses `HTMLPromptManager` for template-specific styling prompts
- Integrates with `HTMLRenderer` for image generation
- Stores debug HTML files in `html_debug/` folder when enabled
- Sets `needs_html_refinement` flag if HTML content is generated

**Outputs:**
- Enhanced `slide_contents` with HTML visualizations embedded
- `needs_html_refinement` flag to trigger refinement process
- Generated HTML count and processing summary

---

## Step 5: HTML Refinement Agent (`src/agents.py:HTMLRefinementAgent`)

**What happens:** The HTML Refinement Agent uses visual AI to improve HTML visualizations through iterative feedback loops. It renders HTML to images, analyzes them with vision models, and applies improvements.

**Key operations:**

- **Visual feedback loop**: Renders HTML → Screenshots image → Vision model analysis → Refinement suggestions → Updated HTML
- **Queue-based processing**: Manages a queue of HTML slides, refining them systematically one by one
- **Parallel processing**: Supports true parallel refinement with `execute_parallel()` for concurrent slide processing
- **Iterative improvement**: Up to 5 refinement iterations per slide for optimal visual quality

**Refinement process:**
1. **HTML detection**: Identifies slides containing HTML visualizations
2. **Image rendering**: Converts HTML to high-resolution screenshots using `HTMLRenderer`
3. **Vision analysis**: Sends screenshots to GPT-4o Vision for quality assessment
4. **Improvement generation**: LLM suggests specific CSS, layout, and content improvements
5. **Implementation**: Applies suggested changes and re-renders for verification

**Technical features:**
- **Image compression**: Optimizes screenshots for LLM vision models (768x1024px max, JPEG compression)
- **Template-aware prompts**: Uses template-specific styling guidelines for consistent refinements
- **Supabase integration**: Tracks refinement iterations and stores debug images in cloud storage
- **Debug mode**: Saves all iteration files to `html_debug/` folder for analysis

**Queue management:**
- Processes one slide at a time in sequential mode
- Tracks current slide index and iteration count
- Automatically moves to next slide when max iterations reached
- Sets `needs_html_refinement = false` when queue is empty

**Outputs:**
- Refined `slide_contents` with improved HTML visualizations
- Updated queue state for progressive refinement
- Quality assessment scores and improvement metrics
- Cloud-stored refinement iterations for review

---

## Step 6: Slide Assembly Agent

*[To be documented as we proceed through each step]*

---

## Final PPTX Creation Process

**What happens:** After HTML refinement is complete, final individual PPTX slides are created using the refined HTML images in correct layouts.

**Key process:**
1. **HTML Refinement Complete**: When all iterations are done, system triggers final PPTX creation
2. **Final Image Retrieval**: Gets the final HTML PNG from the last refinement iteration (`is_final=true`)
3. **Layout-Aware PPTX Creation**: Uses `IndividualSlideGenerator.generate_individual_slide()` with:
   - Correct template layout and placeholder positioning
   - Final HTML image inserted into appropriate placeholder
   - Proper z-order and LOCKED_ background preservation

**Frontend Transition:**
- **During iterations**: Refinement modal shows PNG carousel as iterations are created
- **After completion**: Slide status changes to `completed` → Frontend automatically switches to PowerPoint online viewer
- **User experience**: Seamless transition from watching iterations to viewing final presentation

**Technical implementation:**
- `HTMLRefinementAgent._create_final_pptx_files()` triggered after refinement completion
- Individual slides get `status: "completed"` when PPTX file is successfully created
- Frontend real-time subscriptions detect status change and update UI automatically

---

**Generated:** 2025-01-16 by Claude Code  
**Source:** Workflow analysis of `/src/workflow.py` and related agent files  
**Updated:** Fixed iteration vs final PPTX creation flow