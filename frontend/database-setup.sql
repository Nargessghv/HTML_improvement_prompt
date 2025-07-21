-- =====================================================
-- Ekona Slide Creator - Database Setup
-- =====================================================
-- This script creates all the required tables and policies
-- Run this in your Supabase SQL editor

-- =====================================================
-- PROJECTS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  title TEXT NOT NULL,
  topic TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft', -- draft, processing, completed, failed
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  completed_at TIMESTAMP WITH TIME ZONE,
  metadata JSONB DEFAULT '{}'::jsonb
);

-- Add check constraint for status
ALTER TABLE projects 
ADD CONSTRAINT projects_status_check 
CHECK (status IN ('draft', 'processing', 'completed', 'failed'));

-- =====================================================
-- WORKFLOW_STATES TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS workflow_states (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE NOT NULL,
  agent_name TEXT NOT NULL, -- layout_analysis, planning, content_generation, etc.
  status TEXT NOT NULL DEFAULT 'pending', -- pending, in_progress, completed, failed
  input_data JSONB,
  output_data JSONB,
  error_message TEXT,
  started_at TIMESTAMP WITH TIME ZONE,
  completed_at TIMESTAMP WITH TIME ZONE,
  execution_time_seconds INTEGER,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add check constraint for status
ALTER TABLE workflow_states 
ADD CONSTRAINT workflow_states_status_check 
CHECK (status IN ('pending', 'in_progress', 'completed', 'failed'));

-- =====================================================
-- SLIDES TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS slides (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE NOT NULL,
  slide_number INTEGER NOT NULL,
  title TEXT,
  content JSONB NOT NULL, -- structured slide content
  html_content TEXT, -- generated HTML visualizations
  refined_html TEXT, -- refined HTML after processing
  layout_type TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add unique constraint for slide number per project
ALTER TABLE slides 
ADD CONSTRAINT slides_project_slide_unique 
UNIQUE (project_id, slide_number);

-- =====================================================
-- CONVERSATIONS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE NOT NULL,
  slide_id UUID REFERENCES slides(id) ON DELETE CASCADE NOT NULL,
  messages JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- PROJECT_FILES TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS project_files (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE NOT NULL,
  file_type TEXT NOT NULL, -- pptx, html_debug, images
  file_path TEXT NOT NULL, -- Supabase Storage path
  file_name TEXT NOT NULL,
  file_size INTEGER,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================
CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_workflow_states_project_id ON workflow_states(project_id);
CREATE INDEX IF NOT EXISTS idx_workflow_states_agent_name ON workflow_states(agent_name);
CREATE INDEX IF NOT EXISTS idx_workflow_states_status ON workflow_states(status);

CREATE INDEX IF NOT EXISTS idx_slides_project_id ON slides(project_id);
CREATE INDEX IF NOT EXISTS idx_slides_slide_number ON slides(slide_number);

CREATE INDEX IF NOT EXISTS idx_conversations_project_id ON conversations(project_id);
CREATE INDEX IF NOT EXISTS idx_conversations_slide_id ON conversations(slide_id);

CREATE INDEX IF NOT EXISTS idx_project_files_project_id ON project_files(project_id);
CREATE INDEX IF NOT EXISTS idx_project_files_file_type ON project_files(file_type);

-- =====================================================
-- UPDATED_AT TRIGGERS
-- =====================================================
-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to tables with updated_at column
DROP TRIGGER IF EXISTS update_projects_updated_at ON projects;
CREATE TRIGGER update_projects_updated_at 
    BEFORE UPDATE ON projects 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_slides_updated_at ON slides;
CREATE TRIGGER update_slides_updated_at 
    BEFORE UPDATE ON slides 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_conversations_updated_at ON conversations;
CREATE TRIGGER update_conversations_updated_at 
    BEFORE UPDATE ON conversations 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- ROW LEVEL SECURITY POLICIES
-- =====================================================

-- Enable RLS on all tables
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE slides ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_files ENABLE ROW LEVEL SECURITY;

-- PROJECTS POLICIES
CREATE POLICY "Users can view their own projects" ON projects
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own projects" ON projects
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own projects" ON projects
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own projects" ON projects
    FOR DELETE USING (auth.uid() = user_id);

-- WORKFLOW_STATES POLICIES
CREATE POLICY "Users can view workflow states for their projects" ON workflow_states
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM projects 
            WHERE projects.id = workflow_states.project_id 
            AND projects.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert workflow states for their projects" ON workflow_states
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM projects 
            WHERE projects.id = workflow_states.project_id 
            AND projects.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update workflow states for their projects" ON workflow_states
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM projects 
            WHERE projects.id = workflow_states.project_id 
            AND projects.user_id = auth.uid()
        )
    );

-- SLIDES POLICIES
CREATE POLICY "Users can view slides for their projects" ON slides
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM projects 
            WHERE projects.id = slides.project_id 
            AND projects.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert slides for their projects" ON slides
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM projects 
            WHERE projects.id = slides.project_id 
            AND projects.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update slides for their projects" ON slides
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM projects 
            WHERE projects.id = slides.project_id 
            AND projects.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete slides for their projects" ON slides
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM projects 
            WHERE projects.id = slides.project_id 
            AND projects.user_id = auth.uid()
        )
    );

-- CONVERSATIONS POLICIES
CREATE POLICY "Users can view conversations for their projects" ON conversations
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM projects 
            WHERE projects.id = conversations.project_id 
            AND projects.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert conversations for their projects" ON conversations
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM projects 
            WHERE projects.id = conversations.project_id 
            AND projects.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update conversations for their projects" ON conversations
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM projects 
            WHERE projects.id = conversations.project_id 
            AND projects.user_id = auth.uid()
        )
    );

-- PROJECT_FILES POLICIES
CREATE POLICY "Users can view files for their projects" ON project_files
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM projects 
            WHERE projects.id = project_files.project_id 
            AND projects.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert files for their projects" ON project_files
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM projects 
            WHERE projects.id = project_files.project_id 
            AND projects.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update files for their projects" ON project_files
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM projects 
            WHERE projects.id = project_files.project_id 
            AND projects.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete files for their projects" ON project_files
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM projects 
            WHERE projects.id = project_files.project_id 
            AND projects.user_id = auth.uid()
        )
    );

-- =====================================================
-- STORAGE SETUP (Optional - for file uploads)
-- =====================================================

-- Create storage bucket for presentations (run this in Supabase dashboard if needed)
-- INSERT INTO storage.buckets (id, name, public) 
-- VALUES ('presentations', 'presentations', false);

-- Storage policies (uncomment if using storage)
-- CREATE POLICY "Users can upload their own presentation files" ON storage.objects
--     FOR INSERT WITH CHECK (
--         bucket_id = 'presentations' AND 
--         auth.uid()::text = (storage.foldername(name))[1]
--     );

-- CREATE POLICY "Users can view their own presentation files" ON storage.objects
--     FOR SELECT USING (
--         bucket_id = 'presentations' AND 
--         auth.uid()::text = (storage.foldername(name))[1]
--     );

-- =====================================================
-- VERIFICATION QUERIES
-- =====================================================

-- Run these queries to verify setup
-- SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
-- SELECT * FROM projects LIMIT 1;
-- SELECT * FROM workflow_states LIMIT 1;
-- SELECT * FROM slides LIMIT 1;
-- SELECT * FROM conversations LIMIT 1;
-- SELECT * FROM project_files LIMIT 1;