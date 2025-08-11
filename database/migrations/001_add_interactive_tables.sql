-- Migration: Add tables for interactive slide generation system
-- Created: 2025-07-23

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table for storing presentation planning chat sessions
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    messages JSONB DEFAULT '[]'::jsonb NOT NULL,
    context JSONB DEFAULT '{}'::jsonb NOT NULL,
    presentation_outline JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table for presentation drafts with planning data
CREATE TABLE IF NOT EXISTS presentation_drafts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE UNIQUE,
    chat_session_id UUID REFERENCES chat_sessions(id),
    presentation_outline JSONB,
    skeleton_structure JSONB,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table for individual slide drafts
CREATE TABLE IF NOT EXISTS slide_drafts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    slide_number INTEGER NOT NULL,
    title TEXT,
    content JSONB,
    html_content TEXT,
    refined_html TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'generating', 'generated', 'editing', 'approved', 'failed')),
    placeholder_info JSONB,
    layout_type TEXT,
    generation_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(project_id, slide_number)
);

-- Table for slide comments and feedback
CREATE TABLE IF NOT EXISTS slide_comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slide_draft_id UUID REFERENCES slide_drafts(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id),
    comment_text TEXT NOT NULL,
    comment_type TEXT DEFAULT 'feedback' CHECK (comment_type IN ('feedback', 'edit_request', 'approval', 'rejection')),
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table for slide edit requests
CREATE TABLE IF NOT EXISTS slide_edit_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slide_draft_id UUID REFERENCES slide_drafts(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id),
    request_type TEXT NOT NULL CHECK (request_type IN ('content', 'html', 'layout', 'style', 'regenerate')),
    request_details JSONB NOT NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Table for slide preview images
CREATE TABLE IF NOT EXISTS slide_previews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slide_draft_id UUID REFERENCES slide_drafts(id) ON DELETE CASCADE,
    preview_url TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    width INTEGER,
    height INTEGER,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_chat_sessions_project_id ON chat_sessions(project_id);
CREATE INDEX idx_presentation_drafts_project_id ON presentation_drafts(project_id);
CREATE INDEX idx_slide_drafts_project_status ON slide_drafts(project_id, status);
CREATE INDEX idx_slide_drafts_project_number ON slide_drafts(project_id, slide_number);
CREATE INDEX idx_slide_comments_slide_draft ON slide_comments(slide_draft_id);
CREATE INDEX idx_slide_comments_user ON slide_comments(user_id);
CREATE INDEX idx_edit_requests_slide ON slide_edit_requests(slide_draft_id);
CREATE INDEX idx_edit_requests_status ON slide_edit_requests(status);
CREATE INDEX idx_edit_requests_user ON slide_edit_requests(user_id);
CREATE INDEX idx_slide_previews_slide ON slide_previews(slide_draft_id);

-- Add triggers for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_chat_sessions_updated_at BEFORE UPDATE ON chat_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_presentation_drafts_updated_at BEFORE UPDATE ON presentation_drafts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_slide_drafts_updated_at BEFORE UPDATE ON slide_drafts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE chat_sessions IS 'Stores chat conversations for presentation planning';
COMMENT ON TABLE presentation_drafts IS 'Stores presentation outlines and planning data';
COMMENT ON TABLE slide_drafts IS 'Stores individual slide content during generation';
COMMENT ON TABLE slide_comments IS 'User comments and feedback on slides';
COMMENT ON TABLE slide_edit_requests IS 'Edit requests for slide modifications';
COMMENT ON TABLE slide_previews IS 'Preview images for slides';