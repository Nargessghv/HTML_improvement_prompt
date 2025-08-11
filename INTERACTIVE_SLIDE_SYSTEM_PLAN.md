# Interactive Slide Generation System - Implementation Plan

## Overview
This document outlines a comprehensive plan to transform the current batch slide generation system into an interactive, real-time platform where users can view, edit, and refine slides as they are generated.

## 🎯 Key Features to Implement

### 1. Pre-Generation Chat Interface
- Conversational AI assistant to help draft presentation outline
- Interactive skeleton builder with topic refinement
- Context preservation for all downstream agents

### 2. Real-Time Slide Generation & Display
- Live slide preview as each slide is generated
- Per-slide modification requests
- HTML content re-rendering on demand

### 3. Asynchronous Feedback System
- Comment threads per slide
- Edit requests queue
- Real-time updates via WebSockets

### 4. Final Assembly Process
- Review all slides before final generation
- Batch apply any last-minute changes
- Export options (PPTX, PDF, etc.)

## 📐 System Architecture

### Database Schema Extensions

```sql
-- New tables for interactive features
CREATE TABLE presentation_drafts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    chat_history JSONB DEFAULT '[]',
    presentation_outline JSONB,
    skeleton_structure JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE slide_drafts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    slide_number INTEGER NOT NULL,
    title TEXT,
    content JSONB,
    html_content TEXT,
    refined_html TEXT,
    status TEXT DEFAULT 'pending', -- pending, generating, generated, editing, approved
    placeholder_info JSONB, -- stores dimensions and layout info
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(project_id, slide_number)
);

CREATE TABLE slide_comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slide_draft_id UUID REFERENCES slide_drafts(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id),
    comment_text TEXT NOT NULL,
    comment_type TEXT, -- 'feedback', 'edit_request', 'approval'
    resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE slide_edit_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slide_draft_id UUID REFERENCES slide_drafts(id) ON DELETE CASCADE,
    request_type TEXT, -- 'content', 'html', 'layout', 'style'
    request_details JSONB,
    status TEXT DEFAULT 'pending', -- pending, processing, completed, failed
    result JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP
);

CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    messages JSONB DEFAULT '[]',
    context JSONB, -- preserved context for agents
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_slide_drafts_project_status ON slide_drafts(project_id, status);
CREATE INDEX idx_slide_comments_slide_draft ON slide_comments(slide_draft_id);
CREATE INDEX idx_edit_requests_status ON slide_edit_requests(status);
```

### Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Next.js)                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │  Chat Interface │  │ Slide Editor │  │ Live Preview  │ │
│  │   Component     │  │   Component  │  │   Component   │ │
│  └────────┬────────┘  └──────┬───────┘  └───────┬───────┘ │
│           │                   │                   │         │
│  ┌────────┴───────────────────┴───────────────────┴──────┐ │
│  │              WebSocket Connection Manager              │ │
│  └────────────────────────┬──────────────────────────────┘ │
└───────────────────────────┼────────────────────────────────┘
                            │
┌───────────────────────────┼────────────────────────────────┐
│                    API Layer (FastAPI)                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │  Chat Endpoint  │  │ Slide CRUD   │  │  Edit Queue   │ │
│  │    /chat/*      │  │   /slides/*  │  │  Processor    │ │
│  └────────┬────────┘  └──────┬───────┘  └───────┬───────┘ │
│           │                   │                   │         │
│  ┌────────┴───────────────────┴───────────────────┴──────┐ │
│  │              Agent Orchestration Layer                 │ │
│  └────────────────────────┬──────────────────────────────┘ │
└───────────────────────────┼────────────────────────────────┘
                            │
┌───────────────────────────┼────────────────────────────────┐
│                   Agent System (LangGraph)                  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │  Chat Agent     │  │ Slide Gen    │  │ Edit/Refine   │ │
│  │  (with memory)  │  │   Agents     │  │   Agents      │ │
│  └─────────────────┘  └──────────────┘  └───────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 Implementation Phases

### Phase 1: Chat Interface & Presentation Planning (Week 1-2)

#### 1.1 Chat Agent Implementation
```python
# src/chat_agent.py
class PresentationPlanningAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
        self.memory = ConversationBufferMemory()
        
    async def chat(self, message: str, session_id: str) -> Dict:
        # Load chat history from Supabase
        history = await self.load_chat_history(session_id)
        
        # Generate response with context
        response = await self.llm.achat(message, history=history)
        
        # Extract presentation structure if discussed
        outline = self.extract_presentation_outline(response)
        
        # Save to Supabase
        await self.save_chat_state(session_id, message, response, outline)
        
        return {
            "response": response,
            "outline": outline,
            "suggestions": self.generate_suggestions(outline)
        }
```

#### 1.2 Frontend Chat Component
```typescript
// frontend/src/components/chat/PresentationPlanner.tsx
export function PresentationPlanner({ projectId }: Props) {
  const [messages, setMessages] = useState<Message[]>([])
  const [outline, setOutline] = useState<PresentationOutline>()
  
  const sendMessage = async (text: string) => {
    const response = await fetch('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ text, projectId })
    })
    
    const data = await response.json()
    setMessages([...messages, { role: 'user', text }, data.response])
    if (data.outline) setOutline(data.outline)
  }
  
  return (
    <div className="flex h-full">
      <ChatInterface messages={messages} onSend={sendMessage} />
      <OutlineBuilder outline={outline} onEdit={updateOutline} />
    </div>
  )
}
```

### Phase 2: Real-Time Slide Generation (Week 2-3)

#### 2.1 Modified Workflow with Streaming
```python
# src/interactive_workflow.py
class InteractiveSlideWorkflow:
    def __init__(self, project_id: str, chat_context: Dict):
        self.project_id = project_id
        self.chat_context = chat_context
        self.db = get_supabase_client()
        
    async def generate_slide_interactive(self, slide_number: int):
        # Create slide draft
        slide_draft = await self.db.create_slide_draft(
            project_id=self.project_id,
            slide_number=slide_number,
            status='generating'
        )
        
        # Generate with context from chat
        content = await self.content_agent.generate(
            slide_info=self.outline[slide_number],
            chat_context=self.chat_context
        )
        
        # Stream updates via WebSocket
        await self.send_update('slide_content_generated', {
            'slide_id': slide_draft['id'],
            'content': content
        })
        
        # Generate HTML if needed
        if self.needs_html_visualization(content):
            html = await self.html_agent.generate(content)
            await self.db.update_slide_draft(
                slide_draft['id'], 
                html_content=html
            )
            
            # Render and save preview
            preview_url = await self.render_html_preview(html)
            await self.send_update('slide_preview_ready', {
                'slide_id': slide_draft['id'],
                'preview_url': preview_url
            })
```

#### 2.2 WebSocket Handler
```python
# src/websocket_handlers.py
@app.websocket("/ws/project/{project_id}")
async def project_websocket(websocket: WebSocket, project_id: str):
    await manager.connect(websocket, project_id)
    
    # Send initial state
    slides = await db.get_slide_drafts(project_id)
    await websocket.send_json({
        "type": "initial_state",
        "slides": slides
    })
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data["type"] == "generate_slide":
                await workflow.generate_slide_interactive(
                    data["slide_number"]
                )
            elif data["type"] == "edit_request":
                await edit_queue.add_request(
                    slide_id=data["slide_id"],
                    request=data["request"]
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket, project_id)
```

### Phase 3: Interactive Editing System (Week 3-4)

#### 3.1 Edit Request Processor
```python
# src/edit_processor.py
class SlideEditProcessor:
    def __init__(self):
        self.agents = {
            'content': ContentEditAgent(),
            'html': HTMLEditAgent(),
            'style': StyleEditAgent()
        }
        
    async def process_edit_request(self, request_id: str):
        request = await db.get_edit_request(request_id)
        slide = await db.get_slide_draft(request['slide_draft_id'])
        
        # Get chat context for consistency
        chat_context = await db.get_chat_context(slide['project_id'])
        
        # Process based on request type
        agent = self.agents[request['request_type']]
        result = await agent.process(
            slide=slide,
            request=request,
            context=chat_context
        )
        
        # Update slide draft
        await db.update_slide_draft(slide['id'], **result['updates'])
        
        # Re-render if HTML changed
        if 'html_content' in result['updates']:
            preview_url = await self.render_html_preview(
                result['updates']['html_content']
            )
            result['preview_url'] = preview_url
        
        # Update request status
        await db.update_edit_request(
            request_id, 
            status='completed',
            result=result
        )
        
        # Notify via WebSocket
        await manager.send_update(slide['project_id'], {
            'type': 'edit_completed',
            'slide_id': slide['id'],
            'request_id': request_id,
            'result': result
        })
```

#### 3.2 Frontend Slide Editor
```typescript
// frontend/src/components/slides/SlideEditor.tsx
export function SlideEditor({ slide, onUpdate }: Props) {
  const [editMode, setEditMode] = useState<'view' | 'edit'>('view')
  const [editRequest, setEditRequest] = useState('')
  
  const submitEdit = async () => {
    const response = await fetch('/api/slides/edit', {
      method: 'POST',
      body: JSON.stringify({
        slideId: slide.id,
        requestType: detectRequestType(editRequest),
        request: editRequest
      })
    })
    
    // Request queued, will receive updates via WebSocket
    setEditMode('view')
  }
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>Slide {slide.slideNumber}: {slide.title}</CardTitle>
        <Badge>{slide.status}</Badge>
      </CardHeader>
      <CardContent>
        {slide.htmlContent ? (
          <HTMLPreview html={slide.htmlContent} />
        ) : (
          <TextContent content={slide.content} />
        )}
        
        {editMode === 'edit' ? (
          <EditInterface 
            onSubmit={submitEdit}
            onCancel={() => setEditMode('view')}
          />
        ) : (
          <Button onClick={() => setEditMode('edit')}>
            Request Changes
          </Button>
        )}
        
        <CommentThread slideId={slide.id} />
      </CardContent>
    </Card>
  )
}
```

### Phase 4: Final Assembly System (Week 4)

#### 4.1 Assembly Controller
```python
# src/assembly_controller.py
class PresentationAssemblyController:
    async def assemble_presentation(self, project_id: str):
        # Get all approved slides
        slides = await db.get_slide_drafts(
            project_id, 
            status='approved'
        )
        
        # Verify all slides are ready
        if not self.all_slides_ready(slides):
            raise ValueError("Not all slides are approved")
        
        # Create final presentation
        presentation = SlideGenerator(template_path)
        
        for slide in slides:
            if slide['html_content']:
                # Render final high-res version
                image_path = await self.render_final_image(
                    slide['html_content'],
                    slide['placeholder_info']
                )
                presentation.add_html_slide(
                    slide_number=slide['slide_number'],
                    image_path=image_path,
                    title=slide['title']
                )
            else:
                presentation.add_text_slide(
                    slide_number=slide['slide_number'],
                    content=slide['content'],
                    title=slide['title']
                )
        
        # Save and upload
        output_path = presentation.save()
        download_url = await self.upload_to_storage(output_path)
        
        # Update project status
        await db.update_project(
            project_id,
            status='completed',
            download_url=download_url
        )
        
        return download_url
```

#### 4.2 Frontend Assembly Interface
```typescript
// frontend/src/components/assembly/FinalReview.tsx
export function FinalReview({ projectId }: Props) {
  const [slides, setSlides] = useState<SlideDraft[]>([])
  const [assembling, setAssembling] = useState(false)
  
  const assemblePresentation = async () => {
    setAssembling(true)
    
    try {
      const response = await fetch(`/api/projects/${projectId}/assemble`, {
        method: 'POST'
      })
      
      const { downloadUrl } = await response.json()
      
      // Show success and download link
      toast.success('Presentation assembled successfully!')
      window.open(downloadUrl, '_blank')
    } finally {
      setAssembling(false)
    }
  }
  
  const allApproved = slides.every(s => s.status === 'approved')
  
  return (
    <div>
      <SlideGrid slides={slides} />
      
      <div className="mt-8 flex justify-end">
        <Button
          onClick={assemblePresentation}
          disabled={!allApproved || assembling}
          size="lg"
        >
          {assembling ? (
            <>
              <Loader2 className="animate-spin mr-2" />
              Assembling...
            </>
          ) : (
            <>
              <FileDown className="mr-2" />
              Create Final Presentation
            </>
          )}
        </Button>
      </div>
    </div>
  )
}
```

## 🔄 Real-Time Features Implementation

### WebSocket Event Types
```typescript
type WebSocketEvent = 
  | { type: 'slide_generating'; slideId: string; progress: number }
  | { type: 'slide_generated'; slideId: string; content: SlideContent }
  | { type: 'preview_ready'; slideId: string; previewUrl: string }
  | { type: 'edit_queued'; requestId: string; slideId: string }
  | { type: 'edit_processing'; requestId: string; progress: number }
  | { type: 'edit_completed'; requestId: string; result: EditResult }
  | { type: 'comment_added'; slideId: string; comment: Comment }
  | { type: 'slide_approved'; slideId: string; userId: string }
```

### State Management with Zustand
```typescript
// frontend/src/stores/interactiveSlideStore.ts
interface InteractiveSlideStore {
  slides: Map<string, SlideDraft>
  editRequests: Map<string, EditRequest>
  chatHistory: Message[]
  outline: PresentationOutline | null
  
  // Actions
  updateSlide: (slideId: string, updates: Partial<SlideDraft>) => void
  addEditRequest: (request: EditRequest) => void
  updateEditRequest: (requestId: string, updates: Partial<EditRequest>) => void
  addChatMessage: (message: Message) => void
  setOutline: (outline: PresentationOutline) => void
  
  // WebSocket handlers
  handleWebSocketMessage: (event: WebSocketEvent) => void
}
```

## 📋 API Endpoints

### Chat Endpoints
- `POST /api/chat/start` - Start new planning session
- `POST /api/chat/message` - Send message to planning agent
- `GET /api/chat/{session_id}/context` - Get chat context for agents

### Slide Management
- `POST /api/slides/generate` - Generate single slide
- `GET /api/slides/{slide_id}` - Get slide details
- `PUT /api/slides/{slide_id}/approve` - Approve slide
- `POST /api/slides/{slide_id}/edit` - Request edit

### Edit Requests
- `GET /api/edits/queue` - Get pending edit requests
- `GET /api/edits/{request_id}/status` - Get edit status
- `POST /api/edits/{request_id}/cancel` - Cancel edit

### Assembly
- `POST /api/projects/{project_id}/assemble` - Assemble final presentation
- `GET /api/projects/{project_id}/download` - Get download URL

## 🚀 Migration Strategy

### 1. Database Migration
```sql
-- Run migrations in order
-- 001_add_interactive_tables.sql
-- 002_add_indexes.sql
-- 003_add_rls_policies.sql
```

### 2. Gradual Feature Rollout
1. **Week 1**: Deploy chat interface (feature flag: `ENABLE_CHAT_PLANNING`)
2. **Week 2**: Enable real-time slide generation for new projects
3. **Week 3**: Add edit capabilities
4. **Week 4**: Full system with assembly

### 3. Backward Compatibility
- Keep existing batch generation as "Quick Mode"
- New interactive mode as "Interactive Mode"
- Shared agent codebase with mode detection

## 🔒 Security Considerations

### Row Level Security (RLS)
```sql
-- Ensure users can only access their own data
CREATE POLICY slide_draft_access ON slide_drafts
  FOR ALL USING (
    project_id IN (
      SELECT id FROM projects WHERE user_id = auth.uid()
    )
  );

CREATE POLICY edit_request_access ON slide_edit_requests
  FOR ALL USING (
    slide_draft_id IN (
      SELECT id FROM slide_drafts WHERE project_id IN (
        SELECT id FROM projects WHERE user_id = auth.uid()
      )
    )
  );
```

### Input Validation
- Sanitize all edit requests before processing
- Validate HTML content before rendering
- Rate limit edit requests per user

## 📊 Monitoring & Analytics

### Key Metrics
- Average time per slide generation
- Edit request completion rate
- User engagement with chat interface
- Slide approval rate
- Assembly success rate

### Logging Strategy
```python
# Structured logging for each operation
logger.info("slide_generated", {
    "project_id": project_id,
    "slide_number": slide_number,
    "generation_time": elapsed_time,
    "has_html": bool(html_content),
    "chat_context_used": bool(chat_context)
})
```

## 🔮 Future Enhancements

### Phase 5: Advanced Features
1. **Collaborative Editing**
   - Multiple users working on same presentation
   - Real-time cursor positions
   - Conflict resolution

2. **AI-Powered Suggestions**
   - Proactive design improvements
   - Content recommendations based on industry
   - Automatic accessibility checks

3. **Template Marketplace**
   - User-created templates
   - Industry-specific templates
   - Template customization API

4. **Version Control**
   - Slide version history
   - Branching for different versions
   - Diff visualization

## 📚 Technical Stack Summary

### Backend
- **FastAPI**: REST API + WebSocket support
- **LangGraph**: Agent orchestration
- **Supabase**: Database + Realtime + Storage
- **Celery**: Background task processing (optional)

### Frontend
- **Next.js 15**: React framework
- **Zustand**: State management
- **Socket.io-client**: WebSocket client
- **React Query**: API state management
- **Tailwind + shadcn/ui**: UI components

### Infrastructure
- **Docker**: Containerization
- **Redis**: Queue + caching (optional)
- **CloudFlare**: CDN for assets
- **Monitoring**: Sentry + Custom analytics

## 🎯 Success Criteria

1. **User Experience**
   - < 5s per slide generation
   - < 10s for edit application
   - Real-time updates with < 100ms latency

2. **Reliability**
   - 99.9% uptime for core features
   - Graceful degradation for AI services
   - Automatic retry for failed operations

3. **Scalability**
   - Support 100+ concurrent users
   - Handle presentations up to 100 slides
   - Process multiple edit requests in parallel

## 🗓️ Timeline

- **Month 1**: Core infrastructure + Chat interface
- **Month 2**: Real-time generation + Basic editing
- **Month 3**: Advanced editing + Assembly
- **Month 4**: Polish + Performance optimization
- **Month 5**: Beta testing + Bug fixes
- **Month 6**: Production release

This plan provides a comprehensive roadmap for transforming the slide generation system into an interactive, real-time platform that gives users full control over their presentation creation process.