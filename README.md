# PowerPoint Slide Creator

An AI-powered slide generation system using **agent-based architecture** with **unified Langfuse tracing** for comprehensive monitoring and analytics.

## 🌟 Key Features

### **🤖 Agent-Based Architecture**
- **5 Specialized Agents**: Layout Analysis → Planning → Content Generation → Quality Review → Assembly
- **LangGraph Orchestration**: Coordinated workflow with error handling and retry logic
- **Unified Generation**: Single workflow system - eliminates duplicate content generation
- **Modular Design**: Each agent handles specific aspects of presentation creation

### **📊 Unified Langfuse Tracing** ✨ **NEW**
- **Single Comprehensive Trace**: Complete workflow visibility in one unified trace
- **End-to-End Monitoring**: Track all 5 agents and LLM calls in sequence
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

## 🚀 Quick Start

### Using the Agent-Based Workflow (Recommended)

```bash
# Preview the agent workflow
python -m src.agent_main "Your Topic" --preview

# Generate presentation with unified tracing
python -m src.agent_main "Your Topic" --template template.pptx --output result.pptx
```

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