"""
Presentation Planning Chat Agent

This module provides an interactive chat agent that helps users plan and structure
their presentations through conversational AI. The agent maintains context and
generates presentation outlines that can be used by downstream slide generation agents.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from pydantic import BaseModel, Field
import instructor
from openai import AsyncOpenAI
import os

from .database import get_supabase_client, DatabaseError
from .llm_models import PlaceholderRequirement
from .agent_modules.layout_analysis_agent import LayoutAnalysisAgent
from .agent_modules.prompts.presentation_planning_prompts import get_planning_system_prompt
from .llm_client import LangchainLLMClient


class SlideOutline(BaseModel):
    """Structure for individual slide outline"""
    slide_number: int
    title: str
    key_points: List[str]
    suggested_layout: Optional[str] = None
    notes: Optional[str] = None
    # Layout intelligence from presentation planning agent
    layout_index: Optional[int] = None
    layout_name: Optional[str] = None
    # NEW: Use the same structure as SlideSpec for consistency
    is_html: bool = False
    is_image: bool = False
    placeholder_requirements: Optional[List[PlaceholderRequirement]] = None


class PresentationOutline(BaseModel):
    """Complete presentation outline structure"""
    title: str
    topic: str
    target_audience: Optional[str] = None
    objectives: List[str] = Field(default_factory=list)
    key_themes: List[str] = Field(default_factory=list)
    slides: List[SlideOutline] = Field(default_factory=list)
    estimated_duration: Optional[int] = None  # in minutes
    style_preferences: Dict[str, Any] = Field(default_factory=dict)


@dataclass
class ChatMessage:
    """Chat message structure"""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: str = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.metadata is None:
            self.metadata = {}


class PresentationPlanningAgent:
    """
    Interactive chat agent for presentation planning and structuring.
    Maintains conversation context and generates structured outlines.
    """
    
    def __init__(self, model_name: str = "gpt-4o", temperature: float = 0.7, template_path: Optional[str] = None):
        """
        Initialize the planning agent.
        
        Args:
            model_name: OpenAI model to use
            temperature: Model temperature for response generation
            template_path: Path to PowerPoint template for layout analysis
        """
        self.llm = ChatOpenAI(model=model_name, temperature=temperature)
        self.db = get_supabase_client()
        
        # Initialize instructor client for structured outputs
        openai_client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")  # Support custom base URLs like OpenRouter
        )
        self.instructor_client = instructor.from_openai(openai_client)
        self.model_name = model_name
        self.temperature = temperature
        
        # Layout intelligence for enhanced planning
        self.layout_analyzer = LayoutAnalysisAgent()
        self.layouts_info = {}
        self.template_path = template_path
        
        # LLM client for intelligent layout selection
        self.llm_client = LangchainLLMClient()
        
        # Initialize layouts if template provided
        if template_path:
            self._initialize_layouts(template_path)
            
    def _initialize_layouts(self, template_path: str):
        """Initialize layout analysis for the given template"""
        try:
            # Run layout analysis
            layout_state = self.layout_analyzer.execute({
                "template_path": template_path,
                "current_step": "layout_analysis"
            })
            
            self.layouts_info = layout_state.get("layouts_info", {})
            print(f"✅ Chat agent initialized with {len(self.layouts_info)} layouts")
            
        except Exception as e:
            print(f"⚠️ Failed to initialize layouts: {e}")
            self.layouts_info = {}
    
    def set_template(self, template_path: str):
        """Set template and initialize layouts"""
        self.template_path = template_path
        self._initialize_layouts(template_path)
        
        # Enhanced system prompt with layout awareness
        self.base_system_prompt = """You are an expert presentation planning assistant with advanced layout intelligence. Your role is to help users create well-structured, engaging presentations through conversational planning.

🎯 CORE MISSION: Create engaging presentation outlines with intelligent layout selection for optimal visual impact.

Your responsibilities:
1. ALWAYS respect and incorporate the original project description/requirements provided by the user
2. Ask clarifying questions to understand the user's needs beyond the original description  
3. Suggest presentation structures with smart layout selection that align with requirements
4. Provide industry-specific insights and best practices
5. Create detailed slide outlines with strategic layout and content type selection
6. Recommend visual elements and layouts for maximum impact

Key principles:
- Be conversational and friendly
- Ask one or two questions at a time
- Provide specific, actionable suggestions with layout reasoning
- Consider the target audience and context
- Balance information density with visual appeal through smart layout choices
- Suggest 8-15 slides for most presentations
- CRITICAL: If the original project description specifies certain content, slides, or requirements, ALWAYS include them in the final outline

🎨 VISUAL CONTENT & LAYOUT STRATEGY:

For HTML VISUALIZATIONS (use layouts with picture placeholders):
- Timelines, process flows, workflows → "Title and Picture generated from HTML" layouts
- Charts, comparisons, diagrams → "Title and Picture generated from HTML" layouts  
- Infographics, system architectures → "Title and Picture generated from HTML" layouts
- Data visualizations, conceptual diagrams → "Title and Picture generated from HTML" layouts

For AI-GENERATED IMAGES (use picture layouts):
- Creative visuals, transformations → "Title and Picture" layouts
- Artistic representations, scenes → "Title and Picture" layouts

For TEXT CONTENT (use text/content layouts):
- Simple introductions, conclusions → "Title and Text Content" layouts
- Bullet points, basic information → "Title and Text Content" layouts
- Two-column comparisons → "Title and Two Column Content" layouts

For TITLE SLIDES:
- Presentation opening → "Title Slide with subtitle and presenter name"
- Section introductions → Title-focused layouts

When the user seems ready, generate a complete presentation outline with:
- Strategic layout selection for each slide
- Proper is_html and is_image flags based on content
- Layout reasoning and visual impact considerations
- Structured output ready for slide generation"""
    
    async def start_session(self, project_id: str, initial_topic: str) -> Dict[str, Any]:
        """
        Start a new chat session for presentation planning.
        
        Args:
            project_id: Project ID to associate with the session
            initial_topic: Initial topic provided by the user
            
        Returns:
            Session info including session_id and initial response
        """
        try:
            # Create chat session in database
            session_data = {
                "project_id": project_id,
                "messages": [],
                "context": {
                    "initial_topic": initial_topic,
                    "started_at": datetime.now().isoformat()
                }
            }
            
            result = self.db.client.table("chat_sessions").insert(session_data).execute()
            session = result.data[0]
            session_id = session["id"]
            
            # Generate initial response
            initial_message = f"I'd be happy to help you create a presentation based on your project description:\n\n**'{initial_topic}'**\n\nI've noted your specific requirements and will make sure to include them in the final outline. To help me create the best possible presentation structure, could you tell me:\n\n1. Who is your target audience?\n2. What's the main goal or message you want to convey?\n3. How long do you expect the presentation to be (in minutes or number of slides)?\n4. Are there any additional points beyond your original description that you'd like to emphasize?"
            
            # Save messages
            messages = [
                ChatMessage(role="user", content=initial_topic),
                ChatMessage(role="assistant", content=initial_message)
            ]
            
            await self._save_messages(session_id, messages)
            
            return {
                "session_id": session_id,
                "response": initial_message,
                "suggestions": self._generate_initial_suggestions(initial_topic)
            }
            
        except DatabaseError as e:
            raise Exception(f"Failed to start chat session: {str(e)}")
    
    async def send_message(self, session_id: str, message: str) -> Dict[str, Any]:
        """
        Process a user message and generate a response.
        
        Args:
            session_id: Chat session ID
            message: User's message
            
        Returns:
            Response with agent's reply and any generated outline
        """
        try:
            # Load chat history
            session = await self._load_session(session_id)
            messages = session["messages"]
            
            # Convert to LangChain messages
            lc_messages = [SystemMessage(content=self.base_system_prompt)]
            for msg in messages:
                if msg["role"] == "user":
                    lc_messages.append(HumanMessage(content=msg["content"]))
                else:
                    lc_messages.append(AIMessage(content=msg["content"]))
            
            # Add new user message
            lc_messages.append(HumanMessage(content=message))
            
            # Generate response
            response = await self.llm.ainvoke(lc_messages)
            response_text = response.content
            
            # Check if we should generate an outline
            outline = None
            if self._should_generate_outline(message, response_text, len(messages)):
                outline = await self._generate_outline(session_id, lc_messages)
                if outline:
                    response_text += (
                        f"\n\n🎯 **Presentation Outline Created!**\n\n"
                        f"I've created a detailed presentation outline with {len(outline.slides)} slides "
                        f"based on our discussion. You can review it in the 'Presentation Outline' tab.\n\n"
                        f"**Next Steps:**\n"
                        f"1. Review the outline structure and slide titles\n"
                        f"2. If you're happy with it, click 'Approve & Generate' to start creating your presentation\n"
                        f"3. If you'd like changes, just let me know what to adjust!\n\n"
                        f"The outline includes strategic visual content recommendations for maximum impact. "
                        f"Ready to generate your presentation?"
                    )
            
            # Save new messages
            new_messages = [
                ChatMessage(role="user", content=message),
                ChatMessage(role="assistant", content=response_text)
            ]
            await self._save_messages(session_id, new_messages)
            
            # Update presentation draft if outline generated
            if outline:
                await self._save_presentation_draft(session_id, outline)
            
            return {
                "response": response_text,
                "outline": outline.model_dump() if outline else None,
                "suggestions": self._generate_suggestions(message, response_text)
            }
            
        except Exception as e:
            raise Exception(f"Failed to process message: {str(e)}")
    
    async def get_context(self, session_id: str) -> Dict[str, Any]:
        """
        Get the chat context for use by downstream agents.
        
        Args:
            session_id: Chat session ID
            
        Returns:
            Context dictionary with chat history and extracted information
        """
        try:
            session = await self._load_session(session_id)
            messages = session["messages"]
            
            # Extract key information from conversation
            context = {
                "chat_history": messages,
                "key_points": self._extract_key_points(messages),
                "style_preferences": self._extract_style_preferences(messages),
                "target_audience": self._extract_target_audience(messages),
                "objectives": self._extract_objectives(messages)
            }
            
            # Get presentation outline if available
            draft_result = self.db.client.table("presentation_drafts").select("*").eq(
                "chat_session_id", session_id
            ).execute()
            
            if draft_result.data:
                context["presentation_outline"] = draft_result.data[0]["presentation_outline"]
            
            return context
            
        except Exception as e:
            raise Exception(f"Failed to get context: {str(e)}")
    
    async def regenerate_outline(self, session_id: str, feedback: str) -> Dict[str, Any]:
        """
        Regenerate the presentation outline based on user feedback.
        
        Args:
            session_id: Chat session ID
            feedback: User's feedback on the current outline
            
        Returns:
            Updated outline
        """
        # First process the feedback as a regular message
        result = await self.send_message(session_id, f"Please update the outline: {feedback}")
        
        # Force outline regeneration
        session = await self._load_session(session_id)
        messages = session["messages"]
        
        lc_messages = [SystemMessage(content=self.base_system_prompt)]
        for msg in messages:
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            else:
                lc_messages.append(AIMessage(content=msg["content"]))
        
        outline = await self._generate_outline(session_id, lc_messages, force=True)
        await self._save_presentation_draft(session_id, outline)
        
        return {
            "response": result["response"],
            "outline": outline.model_dump()
        }

    async def generate_outline_for_quickstart(self, topic: str, project_id: Optional[str] = None) -> Optional[PresentationOutline]:
        """
        Generate presentation outline for quickstart workflow (without session context).
        
        Args:
            topic: The project topic/description
            project_id: Optional project ID to fetch additional context
            
        Returns:
            Generated outline or None if generation fails
        """
        try:
            # Create a comprehensive prompt that includes the original project description
            outline_prompt = f"""You are creating a presentation outline for quickstart generation.

ORIGINAL PROJECT DESCRIPTION:
{topic}

🚨 CRITICAL REQUIREMENTS - READ FIRST:
• START WITH TITLE SLIDE: Your presentation MUST begin with a title slide
• ADD TO SLIDE COUNT: If user requests "4 slides", create title slide PLUS 4 content slides (5 total)
• FOLLOW exact slide count if specified ("one slide only", "3 slides", "5-slide presentation")

IMPORTANT: This is a quickstart generation, so you must carefully analyze the project description above and create an outline that EXACTLY matches what was requested. If the description specifies a certain number of slides, specific content, or particular requirements, you MUST follow them precisely.

SPECIAL INSTRUCTIONS FOR USER REQUESTS:
- If user asks for "HTML" slide → Set is_html=true and create placeholder_requirements for HTML content
- If user asks for "image" slide or "picture" → Set is_image=true and create placeholder_requirements for AI image generation
- If user asks for "infographic" → Set is_html=true (infographics are best created as HTML visualizations)
- If user asks for "chart", "diagram", "visualization" → Set is_html=true
- If user specifies exact number of slides → Create EXACTLY that many slides
- If user specifies content types → Use those EXACT specifications

🎨 CONTENT TYPE DECISION GUIDE

SET is_html=true FOR:
✅ Timelines, roadmaps, chronological sequences  
✅ Process flows, workflows, step-by-step procedures
✅ Data visualizations, metrics, statistics  
✅ Complex diagrams, hierarchies, relationships
✅ Comparisons, before/after scenarios
✅ Feature comparisons, pros/cons analysis
✅ Conceptual diagrams, infographics, visual representations
✅ System architectures, component diagrams
✅ Any content that would benefit from visual structure/layout
✅ When user explicitly asks for "HTML" slide or "visual" representation

SET is_image=true FOR:
✅ Any content requiring AI-generated images
✅ When user explicitly asks for "image" slide
✅ Creative storytelling patterns requiring custom visuals

For slides requiring neither HTML nor images, use is_html=false and is_image=false.

🔑 KEY PRINCIPLES:
• STRICTLY follow the requirements in the project description
• If description says "one slide", create exactly one slide
• If description specifies content types, use those exact specifications
• Choose content flags based on CONTENT PURPOSE, not sequence
• Use visual content types strategically for maximum impact
• Ensure each slide advances the narrative
• Always specify placeholder_requirements when is_html=true or is_image=true

📋 CONTENT TYPE SELECTION EXAMPLES:
- Company introduction → is_html=false, is_image=false
- Project timeline → is_html=true (timeline visualization)
- Performance metrics → is_html=true (chart visualization)
- Before vs After results → is_html=true (comparison visualization)
- Process workflow → is_html=true (timeline visualization)
- Feature comparison → is_html=true (comparison visualization)
- Vision/mission statement → is_html=false, is_image=false
- Team introduction → is_html=false, is_image=false
- Data analysis → is_html=true (chart visualization)
- Transformation story → is_image=true (AI-generated visual)
- AI agents overview → is_html=true (conceptual diagram)
- System architecture → is_html=true (component diagram)
- Technology stack → is_html=true (visual infographic)
- How it works → is_html=true (process diagram)
- Key concepts visualization → is_html=true (infographic)

CRITICAL: Always specify placeholder_requirements when is_html=true or is_image=true. For image slides, use placeholder_name "Picture 16:9". For HTML slides, use placeholder_name "Content Placeholder 1" or similar based on the slide layout.

Please create a structured presentation outline that follows these guidelines and exactly matches the project requirements."""
            
            # Create messages for the LLM
            messages = [
                SystemMessage(content="You are an expert presentation planning assistant specialized in quickstart generation."),
                HumanMessage(content=outline_prompt)
            ]
            
            # Convert langchain messages to OpenAI format for instructor
            openai_messages = []
            for msg in messages:
                if isinstance(msg, SystemMessage):
                    openai_messages.append({"role": "system", "content": msg.content})
                elif isinstance(msg, HumanMessage):
                    openai_messages.append({"role": "user", "content": msg.content})
                elif isinstance(msg, AIMessage):
                    openai_messages.append({"role": "assistant", "content": msg.content})
            
            # Use instructor for guaranteed structured output
            outline = await self.instructor_client.chat.completions.create(
                model=self.model_name,
                response_model=PresentationOutline,
                messages=openai_messages,
                temperature=self.temperature
            )
            
            return outline
            
        except Exception as e:
            print(f"Error generating quickstart outline: {e}")
        
        return None
    
    # Private helper methods
    
    def _extract_json_from_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from LLM response that may contain extra text"""
        import re
        
        # Try to find JSON in code blocks first
        code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if code_block_match:
            try:
                return json.loads(code_block_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON object directly
        brace_count = 0
        start_pos = -1
        
        for i, char in enumerate(response_text):
            if char == '{':
                if brace_count == 0:
                    start_pos = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_pos >= 0:
                    try:
                        json_str = response_text[start_pos:i+1]
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        continue
        
        return None
    
    async def _load_session(self, session_id: str) -> Dict[str, Any]:
        """Load chat session from database"""
        result = self.db.client.table("chat_sessions").select("*").eq("id", session_id).execute()
        if not result.data:
            raise ValueError(f"Session {session_id} not found")
        return result.data[0]
    
    async def _save_messages(self, session_id: str, messages: List[ChatMessage]):
        """Save messages to the session"""
        # Load existing messages
        session = await self._load_session(session_id)
        existing_messages = session["messages"]
        
        # Append new messages
        for msg in messages:
            existing_messages.append(asdict(msg))
        
        # Update session
        self.db.client.table("chat_sessions").update({
            "messages": existing_messages
        }).eq("id", session_id).execute()
    
    async def _save_presentation_draft(self, session_id: str, outline: PresentationOutline):
        """Save or update presentation draft"""
        session = await self._load_session(session_id)
        project_id = session["project_id"]
        
        draft_data = {
            "project_id": project_id,
            "chat_session_id": session_id,
            "presentation_outline": outline.model_dump(),
            "skeleton_structure": self._generate_skeleton_structure(outline)
        }
        
        # Check if draft exists
        existing = self.db.client.table("presentation_drafts").select("id").eq(
            "project_id", project_id
        ).execute()
        
        if existing.data:
            # Update existing
            self.db.client.table("presentation_drafts").update(draft_data).eq(
                "id", existing.data[0]["id"]
            ).execute()
        else:
            # Create new
            self.db.client.table("presentation_drafts").insert(draft_data).execute()
    
    def _should_generate_outline(self, message: str, response: str, message_count: int) -> bool:
        """Determine if we should generate an outline"""
        # Triggers for outline generation
        triggers = [
            "create the outline",
            "generate the outline", 
            "show me the structure",
            "let's proceed",
            "that sounds good",
            "looks good",
            "perfect",
            "approve",
            "start generating",
            "begin generation",
            "generate the slides",
            "create the presentation"
        ]
        
        message_lower = message.lower()
        
        # Check explicit triggers
        if any(trigger in message_lower for trigger in triggers):
            return True
        
        # Check if we have enough context (usually after 4-6 exchanges)
        if message_count >= 8:
            confirmation_words = ["yes", "okay", "sure", "great", "sounds good"]
            if any(word in message_lower for word in confirmation_words):
                return True
        
        return False
    
    async def _generate_outline(self, session_id: str, messages: List, force: bool = False) -> Optional[PresentationOutline]:
        """Generate presentation outline based on conversation"""
        
        # Get project context to include original description
        session = await self._load_session(session_id)
        project_id = session["project_id"]
        
        # Get the original project information
        project_result = self.db.client.table("projects").select("*").eq("id", project_id).execute()
        project_topic = ""
        if project_result.data:
            project_topic = project_result.data[0].get("topic", "")
        
        outline_prompt = f"""Based on our conversation AND the original project description, create a detailed presentation outline using strategic presentation planning principles.

ORIGINAL PROJECT DESCRIPTION:
{project_topic}

🚨 CRITICAL REQUIREMENTS - READ FIRST:
• START WITH TITLE SLIDE: Your presentation MUST begin with a title slide
• ADD TO SLIDE COUNT: If user requests "4 slides", create title slide PLUS 4 content slides (5 total)
• FOLLOW exact slide count if specified ("one slide only", "3 slides", "5-slide presentation")

IMPORTANT: The outline must respect and incorporate the specific requirements from the original project description above, while also considering our conversation. If the original description specifies certain slides or content, make sure to include them.

SPECIAL INSTRUCTIONS FOR USER REQUESTS:
- If user asks for "HTML" slide → Set is_html=true and create placeholder_requirements for HTML content
- If user asks for "image" slide or "picture" → Set is_image=true and create placeholder_requirements for AI image generation
- If user asks for "infographic" → Set is_html=true (infographics are best created as HTML visualizations)
- If user asks for "chart", "diagram", "visualization" → Set is_html=true
- If user specifies exact number of slides → Create EXACTLY that many slides
- If user specifies content types → Use those EXACT specifications

🎨 CONTENT TYPE DECISION GUIDE

SET is_html=true FOR:
✅ Timelines, roadmaps, chronological sequences  
✅ Process flows, workflows, step-by-step procedures
✅ Data visualizations, metrics, statistics  
✅ Complex diagrams, hierarchies, relationships
✅ Comparisons, before/after scenarios
✅ Feature comparisons, pros/cons analysis
✅ Conceptual diagrams, infographics, visual representations
✅ System architectures, component diagrams
✅ Any content that would benefit from visual structure/layout
✅ When user explicitly asks for "HTML" slide or "visual" representation

SET is_image=true FOR:
✅ Any content requiring AI-generated images
✅ When user explicitly asks for "image" slide
✅ Creative storytelling patterns requiring custom visuals

For slides requiring neither HTML nor images, use is_html=false and is_image=false.

🔑 KEY PRINCIPLES:
• Create 8-15 slides with logical flow: introduction → content → conclusion
• Choose content flags based on CONTENT PURPOSE, not sequence
• Use visual content types strategically for maximum impact
• Ensure each slide advances the narrative
• Balance visual and text slides appropriately
• Always specify placeholder_requirements when is_html=true or is_image=true

📋 CONTENT TYPE SELECTION EXAMPLES:
- Company introduction → is_html=false, is_image=false
- Project timeline → is_html=true (timeline visualization)
- Performance metrics → is_html=true (chart visualization)
- Before vs After results → is_html=true (comparison visualization)
- Process workflow → is_html=true (timeline visualization)
- Feature comparison → is_html=true (comparison visualization)
- Vision/mission statement → is_html=false, is_image=false
- Team introduction → is_html=false, is_image=false
- Data analysis → is_html=true (chart visualization)
- Transformation story → is_image=true (AI-generated visual)
- AI agents overview → is_html=true (conceptual diagram)
- System architecture → is_html=true (component diagram)
- Technology stack → is_html=true (visual infographic)
- How it works → is_html=true (process diagram)
- Key concepts visualization → is_html=true (infographic)

CRITICAL: Always specify placeholder_requirements when is_html=true or is_image=true. For image slides, use placeholder_name "Picture 16:9". For HTML slides, use placeholder_name "Content Placeholder 1" or similar based on the slide layout.

Please create a structured presentation outline that follows these guidelines."""
        
        messages_with_prompt = messages + [HumanMessage(content=outline_prompt)]
        
        try:
            # Convert langchain messages to OpenAI format for instructor
            openai_messages = []
            for msg in messages_with_prompt:
                if isinstance(msg, SystemMessage):
                    openai_messages.append({"role": "system", "content": msg.content})
                elif isinstance(msg, HumanMessage):
                    openai_messages.append({"role": "user", "content": msg.content})
                elif isinstance(msg, AIMessage):
                    openai_messages.append({"role": "assistant", "content": msg.content})
            
            # Use instructor for guaranteed structured output
            outline = await self.instructor_client.chat.completions.create(
                model=self.model_name,
                response_model=PresentationOutline,
                messages=openai_messages,
                temperature=self.temperature
            )
            
            # Enhance outline with layout intelligence
            if self.layouts_info:
                outline = self._enhance_outline_with_layouts(outline)
            
            return outline
            
        except Exception as e:
            print(f"Error generating outline: {e}")
        
        return None
    
    def _enhance_outline_with_layouts(self, outline: PresentationOutline) -> PresentationOutline:
        """Enhance outline with intelligent layout selection"""
        try:
            print(f"🎨 Enhancing outline with layout intelligence for {len(outline.slides)} slides")
            
            for slide in outline.slides:
                layout_info = self._select_layout_for_slide(slide)
                slide.layout_index = layout_info["index"]
                slide.layout_name = layout_info["name"]
                
                # Update flags based on selected layout capabilities
                layout_details = self.layouts_info.get(layout_info["index"], {})
                slide = self._update_slide_flags_from_layout(slide, layout_details)
                
                print(f"  📋 Slide {slide.slide_number}: '{slide.title}' → Layout {slide.layout_index} ('{slide.layout_name}') - HTML:{slide.is_html}, Image:{slide.is_image}")
            
            return outline
            
        except Exception as e:
            print(f"⚠️ Error enhancing outline with layouts: {e}")
            return outline
    
    def _select_layout_for_slide(self, slide: SlideOutline) -> Dict[str, Any]:
        """Select best layout for a slide based on content and flags using LLM intelligence"""
        
        # Use LLM to intelligently select layout based on slide content
        if not self.layouts_info:
            return {"index": 0, "name": "Default Layout"}
            
        layout_index = self._select_layout_with_llm(
            self.layouts_info,
            slide.title,
            slide.key_points,
            slide.is_html,
            slide.is_image,
            slide.placeholder_requirements or []
        )
        
        # Get layout name from the selected index
        layout_info = self.layouts_info.get(layout_index, {})
        layout_name = layout_info.get("name", f"Layout {layout_index}")
        
        return {
            "index": layout_index,
            "name": layout_name
        }
    
    def _select_layout_with_llm(
        self, 
        layouts_info: Dict[int, Dict[str, Any]], 
        slide_title: str,
        key_points: List[str],
        is_html: bool,
        is_image: bool,
        placeholder_requirements: List[Any]
    ) -> int:
        """
        Use LLM to intelligently select the best layout based on slide content
        
        Args:
            layouts_info: Dictionary of all available layouts with their details
            slide_title: Title of the slide
            key_points: Key points for the slide
            is_html: Whether slide needs HTML visualization
            is_image: Whether slide needs AI-generated image
            placeholder_requirements: Specific placeholder requirements
            
        Returns:
            Layout index selected by LLM
        """
        # Build detailed layout descriptions for LLM
        layout_options = []
        for idx, layout_info in layouts_info.items():
            layout_name = layout_info.get("name", f"Layout {idx}")
            placeholders = layout_info.get("placeholders", [])
            
            # Build detailed placeholder info
            placeholder_details = []
            for p in placeholders:
                if isinstance(p, dict):
                    name = p.get("name", "Unknown")
                    p_type = p.get("type", "Unknown")
                    placeholder_details.append(f"{name} ({p_type})")
                else:
                    placeholder_details.append(str(p))
                    
            layout_options.append({
                "index": idx,
                "name": layout_name,
                "placeholders": placeholder_details
            })
        
        # Create prompt for layout selection
        prompt = f"""Select the BEST layout for this slide based on content requirements:

SLIDE CONTENT:
- Title: {slide_title}
- Key Points: {', '.join(key_points) if key_points else 'None'}
- Needs HTML visualization: {is_html}
- Needs AI-generated image: {is_image}
- Content Type: {'HTML/Visual' if is_html else 'Image' if is_image else 'Text'}

AVAILABLE LAYOUTS:
"""
        
        for layout in layout_options:
            prompt += f"\nLayout {layout['index']}: {layout['name']}\n"
            prompt += f"  Placeholders: {', '.join(layout['placeholders'])}\n"
        
        prompt += """\n
SELECTION CRITERIA:
1. For HTML content: Choose layouts with picture/image placeholders that can display rendered HTML
2. For AI images: Choose layouts with picture placeholders for generated images  
3. For text content: Choose layouts with content/text placeholders
4. Match the number and type of placeholders to the content needs
5. Consider the slide's purpose and how to best present the information

RETURN ONLY THE LAYOUT INDEX NUMBER (e.g., 3)
"""
        
        try:
            # Use LLM to select layout
            response = self.llm_client.generate_content(
                system_prompt="You are a presentation layout expert. Select the most appropriate layout index based on content requirements.",
                user_prompt=prompt
            )
            
            # Extract layout index from response
            import re
            match = re.search(r'\b(\d+)\b', response)
            if match:
                selected_index = int(match.group(1))
                if selected_index in layouts_info:
                    print(f"      LLM selected layout {selected_index}: {layouts_info[selected_index].get('name', 'Unknown')}")
                    return selected_index
                    
        except Exception as e:
            print(f"      Warning: LLM layout selection failed: {e}")
        
        # Fallback: Select first suitable layout based on content type
        print("      Falling back to default layout selection")
        if is_html or is_image:
            # Find first layout with picture placeholder
            for idx, layout_info in layouts_info.items():
                placeholders = layout_info.get("placeholders", [])
                for p in placeholders:
                    if isinstance(p, dict):
                        name = p.get("name", "").lower()
                        if any(word in name for word in ["picture", "image", "visual", "html"]):
                            return idx
        
        # Default to first non-logo layout
        for idx, layout_info in layouts_info.items():
            if "logo" not in layout_info.get("name", "").lower():
                return idx
                
        return list(layouts_info.keys())[0] if layouts_info else 0
    
    def _find_layout_by_type(self, layout_type: str) -> Optional[Dict[str, Any]]:
        """Find layout by type (title, html, picture, text)"""
        
        for layout_idx, layout_info in self.layouts_info.items():
            layout_name = layout_info.get("name", "").lower()
            
            if layout_type == "title":
                if "title" in layout_name and "subtitle" in layout_name:
                    return {"index": layout_idx, "name": layout_info.get("name")}
            
            elif layout_type == "html":
                if "html" in layout_name or ("picture" in layout_name and "html" in layout_name):
                    return {"index": layout_idx, "name": layout_info.get("name")}
            
            elif layout_type == "picture":
                if "picture" in layout_name and "html" not in layout_name:
                    return {"index": layout_idx, "name": layout_info.get("name")}
            
            elif layout_type == "text":
                # Prioritize layouts with "text content" in the name for text-only slides
                if ("text content" in layout_name) or ("content" in layout_name and "picture" not in layout_name and "html" not in layout_name):
                    return {"index": layout_idx, "name": layout_info.get("name")}
        
        return None
    
    def _update_slide_flags_from_layout(self, slide: SlideOutline, layout_details: Dict[str, Any]) -> SlideOutline:
        """Update slide flags based on layout capabilities"""
        
        # Check if layout has picture placeholders (can support HTML or images)
        placeholders = layout_details.get("placeholders", [])
        has_picture_placeholder = any(
            ph.get("type") == 18 or "picture" in ph.get("name", "").lower() or "image" in ph.get("name", "").lower()
            for ph in placeholders
        )
        
        # If slide is marked for HTML but layout doesn't support it, keep the flag but warn
        if slide.is_html and not has_picture_placeholder:
            print(f"  ⚠️ Slide {slide.slide_number} marked for HTML but selected layout may not fully support it")
        
        # If slide is marked for image but layout doesn't support it, keep the flag but warn  
        if slide.is_image and not has_picture_placeholder:
            print(f"  ⚠️ Slide {slide.slide_number} marked for image but selected layout may not fully support it")
        
        return slide
    
    def _generate_skeleton_structure(self, outline: PresentationOutline) -> Dict[str, Any]:
        """Generate skeleton structure for the presentation"""
        return {
            "total_slides": len(outline.slides),
            "sections": self._identify_sections(outline.slides),
            "visual_elements": self._count_visual_elements(outline.slides),
            "estimated_generation_time": len(outline.slides) * 30  # seconds
        }
    
    def _identify_sections(self, slides: List[SlideOutline]) -> List[Dict[str, Any]]:
        """Identify logical sections in the presentation"""
        sections = []
        current_section = {"start": 0, "end": 0, "theme": "Introduction"}
        
        for i, slide in enumerate(slides):
            # Simple section detection based on slide numbers and titles
            if i == 0:
                current_section["theme"] = "Introduction"
            elif i == len(slides) - 1:
                sections.append(current_section)
                current_section = {"start": i, "end": i, "theme": "Conclusion"}
            elif "overview" in slide.title.lower():
                if current_section["end"] > current_section["start"]:
                    sections.append(current_section)
                current_section = {"start": i, "end": i, "theme": "Overview"}
            elif any(word in slide.title.lower() for word in ["conclusion", "summary", "next steps"]):
                if current_section["end"] > current_section["start"]:
                    sections.append(current_section)
                current_section = {"start": i, "end": i, "theme": "Conclusion"}
            else:
                current_section["end"] = i
        
        sections.append(current_section)
        return sections
    
    def _count_visual_elements(self, slides: List[SlideOutline]) -> Dict[str, int]:
        """Count different types of visual elements"""
        counts = {
            "html_slides": 0,
            "image_slides": 0,
            "text_slides": 0
        }
        
        for slide in slides:
            if slide.is_html:
                counts["html_slides"] += 1
            if slide.is_image:
                counts["image_slides"] += 1
            if not slide.is_html and not slide.is_image:
                counts["text_slides"] += 1
        
        return counts
    
    def _extract_key_points(self, messages: List[Dict]) -> List[str]:
        """Extract key points from conversation"""
        key_points = []
        
        for msg in messages:
            if msg["role"] == "user":
                # Look for explicitly stated points
                content_lower = msg["content"].lower()
                if any(phrase in content_lower for phrase in ["important", "key point", "main", "focus"]):
                    key_points.append(msg["content"])
        
        return key_points[:5]  # Limit to top 5
    
    def _extract_style_preferences(self, messages: List[Dict]) -> Dict[str, Any]:
        """Extract style preferences from conversation"""
        preferences = {
            "formality": "professional",  # default
            "visual_density": "balanced",
            "color_preferences": []
        }
        
        # Analyze messages for style cues
        all_text = " ".join([msg["content"].lower() for msg in messages])
        
        if any(word in all_text for word in ["casual", "friendly", "informal"]):
            preferences["formality"] = "casual"
        elif any(word in all_text for word in ["academic", "scientific", "research"]):
            preferences["formality"] = "academic"
        
        if any(word in all_text for word in ["minimal", "simple", "clean"]):
            preferences["visual_density"] = "minimal"
        elif any(word in all_text for word in ["detailed", "comprehensive", "thorough"]):
            preferences["visual_density"] = "detailed"
        
        return preferences
    
    def _extract_target_audience(self, messages: List[Dict]) -> Optional[str]:
        """Extract target audience from conversation"""
        for msg in messages:
            content_lower = msg["content"].lower()
            if any(phrase in content_lower for phrase in ["audience", "presenting to", "for"]):
                # Simple extraction - can be made more sophisticated
                return msg["content"]
        return None
    
    def _extract_objectives(self, messages: List[Dict]) -> List[str]:
        """Extract presentation objectives from conversation"""
        objectives = []
        
        for msg in messages:
            content_lower = msg["content"].lower()
            if any(phrase in content_lower for phrase in ["goal", "objective", "aim", "purpose"]):
                objectives.append(msg["content"])
        
        return objectives[:3]  # Limit to top 3
    
    def _generate_initial_suggestions(self, topic: str) -> List[str]:
        """Generate initial suggestions based on topic"""
        return [
            f"Consider starting with a compelling story or statistic about {topic}",
            "Think about what your audience already knows and what they need to learn",
            "Aim for 8-15 slides with strategic use of timelines, charts, and comparisons",
            "Include visual elements where they add value - timelines for processes, charts for data"
        ]
    
    def _generate_suggestions(self, message: str, response: str) -> List[str]:
        """Generate contextual suggestions"""
        suggestions = []
        
        # Context-based suggestions with visual content strategy
        if "audience" in message.lower():
            suggestions.append("Consider tailoring examples to your audience's industry or experience")
        
        if "technical" in message.lower():
            suggestions.append("Balance technical details with clear explanations for non-experts")
        
        if any(word in message.lower() for word in ["visual", "chart", "graph", "diagram"]):
            suggestions.append("Use timelines for processes, charts for data, comparisons for before/after scenarios")
        
        if any(word in message.lower() for word in ["process", "workflow", "timeline", "roadmap"]):
            suggestions.append("Consider using timeline visualization to show process flow or chronological sequence")
        
        if any(word in message.lower() for word in ["data", "metrics", "statistics", "numbers"]):
            suggestions.append("Charts work well for data visualization and performance metrics")
        
        if any(word in message.lower() for word in ["compare", "versus", "before", "after", "difference"]):
            suggestions.append("Comparison slides are perfect for before/after scenarios and feature analysis")
        
        if any(word in message.lower() for word in ["story", "journey", "transformation", "change"]):
            suggestions.append("Visual storytelling patterns can make transformation narratives more engaging")
        
        return suggestions if suggestions else ["Let me know if you need any clarification or have specific requirements"]