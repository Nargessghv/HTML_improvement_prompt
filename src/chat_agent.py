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

from .database import get_supabase_client, DatabaseError
from .llm_models import PlaceholderRequirement


class SlideOutline(BaseModel):
    """Structure for individual slide outline"""
    slide_number: int
    title: str
    key_points: List[str]
    suggested_layout: Optional[str] = None
    notes: Optional[str] = None
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
    
    def __init__(self, model_name: str = "gpt-4o", temperature: float = 0.7):
        """
        Initialize the planning agent.
        
        Args:
            model_name: OpenAI model to use
            temperature: Model temperature for response generation
        """
        self.llm = ChatOpenAI(model=model_name, temperature=temperature)
        self.db = get_supabase_client()
        
        # System prompt for presentation planning
        self.system_prompt = """You are an expert presentation planning assistant. Your role is to help users create well-structured, engaging presentations through conversational planning.

Your responsibilities:
1. ALWAYS respect and incorporate the original project description/requirements provided by the user
2. Ask clarifying questions to understand the user's needs beyond the original description
3. Suggest presentation structures and content organization that align with the original requirements
4. Provide industry-specific insights and best practices
5. Create detailed slide outlines with intelligent content type selection
6. Recommend visual elements strategically for maximum impact

Key principles:
- Be conversational and friendly
- Ask one or two questions at a time
- Provide specific, actionable suggestions
- Consider the target audience and context
- Balance information density with visual appeal
- Suggest 8-15 slides for most presentations
- CRITICAL: If the original project description specifies certain content, slides, or requirements, ALWAYS include them in the final outline

Visual Content Strategy:
- Use HTML VISUALIZATION for: timelines, charts, comparisons, diagrams, infographics, visual representations
- Use HTML for: process flows, workflows, data visualizations, system architectures, conceptual diagrams
- Use AI-GENERATED IMAGES for: creative visuals, transformations, artistic representations
- Use TEXT ONLY for: simple introductions, conclusions, basic bullet points without visual elements

Content Type Selection Examples:
- "Project timeline" → HTML (timeline visualization)
- "Performance metrics" → HTML (chart visualization)
- "Before vs After results" → HTML (comparison visualization)
- "Process workflow" → HTML (process diagram)
- "AI agents overview" → HTML (conceptual diagram)
- "System architecture" → HTML (component diagram)
- "How it works" → HTML (infographic)
- "Transformation story" → AI-generated image
- "Company introduction" → Text only

When the user seems ready, generate a complete presentation outline with strategic content type selection that will enable powerful HTML visualizations where appropriate."""
    
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
            lc_messages = [SystemMessage(content=self.system_prompt)]
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
                    response_text += f"\n\nBased on our discussion, I've created a presentation outline with {len(outline.slides)} slides. You can review it and let me know if you'd like any changes!"
            
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
                "outline": outline.dict() if outline else None,
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
        
        lc_messages = [SystemMessage(content=self.system_prompt)]
        for msg in messages:
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            else:
                lc_messages.append(AIMessage(content=msg["content"]))
        
        outline = await self._generate_outline(session_id, lc_messages, force=True)
        await self._save_presentation_draft(session_id, outline)
        
        return {
            "response": result["response"],
            "outline": outline.dict()
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

IMPORTANT: This is a quickstart generation, so you must carefully analyze the project description above and create an outline that EXACTLY matches what was requested. If the description specifies a certain number of slides, specific content, or particular requirements, you MUST follow them precisely.

SPECIAL INSTRUCTIONS FOR USER REQUESTS:
- If user asks for "HTML" slide → Set is_html=true and create placeholder_requirements for HTML content
- If user asks for "image" slide or "picture" → Set is_image=true and create placeholder_requirements for AI image generation
- If user asks for "infographic" → Set is_html=true (infographics are best created as HTML visualizations)
- If user asks for "chart", "diagram", "visualization" → Set is_html=true
- If user specifies exact number of slides → Create EXACTLY that many slides
- If user specifies content types → Use those EXACT specifications

Create a detailed presentation outline using strategic presentation planning principles.

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

Return the outline in this exact JSON format:
        {{
            "title": "Presentation Title",
            "topic": "Main topic",
            "target_audience": "Target audience description",
            "objectives": ["Objective 1", "Objective 2"],
            "key_themes": ["Theme 1", "Theme 2"],
            "slides": [
                {{
                    "slide_number": 1,
                    "title": "Slide Title",
                    "key_points": ["Point 1", "Point 2"],
                    "suggested_layout": "layout name",
                    "notes": "Additional notes",
                    "is_html": false,
                    "is_image": false,
                    "placeholder_requirements": [
                        {{
                            "placeholder_name": "Picture 16:9",
                            "content_type": "image",
                            "description": "AI-generated image showing..."
                        }}
                    ]
                }}
            ],
            "estimated_duration": 30,
            "style_preferences": {{
                "tone": "professional|casual|academic",
                "visual_style": "modern|classic|minimal",
                "color_scheme": "suggestions"
            }}
        }}

CRITICAL: Always specify placeholder_requirements when is_html=true or is_image=true. For image slides, use placeholder_name "Picture 16:9". For HTML slides, use placeholder_name "Content Placeholder 1" or similar based on the slide layout.

REMINDER: Pay close attention to the original project description at the top and follow its requirements exactly."""
            
            # Create messages for the LLM
            messages = [
                SystemMessage(content="You are an expert presentation planning assistant specialized in quickstart generation."),
                HumanMessage(content=outline_prompt)
            ]
            
            # Generate response
            response = await self.llm.ainvoke(messages)
            
            # Parse JSON from response
            json_start = response.content.find('{')
            json_end = response.content.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                outline_data = json.loads(response.content[json_start:json_end])
                return PresentationOutline(**outline_data)
            
        except Exception as e:
            print(f"Error generating quickstart outline: {e}")
        
        return None
    
    # Private helper methods
    
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
            "presentation_outline": outline.dict(),
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
            "perfect"
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

IMPORTANT: The outline must respect and incorporate the specific requirements from the original project description above, while also considering our conversation. If the original description specifies certain slides or content, make sure to include them.

SPECIAL INSTRUCTIONS FOR USER REQUESTS:
- If user asks for "HTML" slide → Set is_html=true and create placeholder_requirements for HTML content
- If user asks for "image" slide or "picture" → Set is_image=true and create placeholder_requirements for AI image generation
- If user asks for "infographic" → Set is_html=true (infographics are best created as HTML visualizations)
- If user asks for "chart", "diagram", "visualization" → Set is_html=true
- If user specifies exact number of slides → Create EXACTLY that many slides
- If user specifies content types → Use those EXACT specifications

Based on our conversation and the original project requirements, create a detailed presentation outline using strategic presentation planning principles.

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

Return the outline in this exact JSON format with proper is_html, is_image, and placeholder_requirements fields:

CRITICAL: Always specify placeholder_requirements when is_html=true or is_image=true. For image slides, use placeholder_name "Picture 16:9". For HTML slides, use placeholder_name "Content Placeholder 1" or similar based on the slide layout."""
        
        messages_with_prompt = messages + [HumanMessage(content=outline_prompt)]
        
        try:
            response = await self.llm.ainvoke(messages_with_prompt)
            
            # Parse JSON from response
            json_start = response.content.find('{')
            json_end = response.content.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                outline_data = json.loads(response.content[json_start:json_end])
                return PresentationOutline(**outline_data)
            
        except Exception as e:
            print(f"Error generating outline: {e}")
        
        return None
    
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