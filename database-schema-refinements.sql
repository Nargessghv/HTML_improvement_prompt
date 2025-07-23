-- =====================================================
-- HTML REFINEMENT TRACKING SCHEMA
-- =====================================================
-- This script adds tables to track HTML refinement iterations
-- Run this in your Supabase SQL editor AFTER the main database-setup.sql

-- =====================================================
-- HTML_REFINEMENTS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS html_refinements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE NOT NULL,
  slide_id UUID REFERENCES slides(id) ON DELETE CASCADE NOT NULL,
  iteration_number INTEGER NOT NULL DEFAULT 1,
  html_content TEXT NOT NULL,
  html_file_url TEXT, -- Supabase Storage URL for HTML file
  image_file_url TEXT, -- Supabase Storage URL for PNG screenshot
  refinement_feedback TEXT, -- LLM feedback/analysis
  refinement_prompt TEXT, -- Prompt used for this iteration
  is_final BOOLEAN DEFAULT FALSE, -- Marks the final/accepted version
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add composite unique constraint for slide refinement iterations
ALTER TABLE html_refinements 
ADD CONSTRAINT html_refinements_slide_iteration_unique 
UNIQUE (slide_id, iteration_number);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================
CREATE INDEX IF NOT EXISTS idx_html_refinements_project_id ON html_refinements(project_id);
CREATE INDEX IF NOT EXISTS idx_html_refinements_slide_id ON html_refinements(slide_id);
CREATE INDEX IF NOT EXISTS idx_html_refinements_iteration ON html_refinements(iteration_number);
CREATE INDEX IF NOT EXISTS idx_html_refinements_is_final ON html_refinements(is_final);
CREATE INDEX IF NOT EXISTS idx_html_refinements_created_at ON html_refinements(created_at DESC);

-- =====================================================
-- UPDATED_AT TRIGGER
-- =====================================================
DROP TRIGGER IF EXISTS update_html_refinements_updated_at ON html_refinements;
CREATE TRIGGER update_html_refinements_updated_at 
    BEFORE UPDATE ON html_refinements 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- ROW LEVEL SECURITY POLICIES
-- =====================================================
ALTER TABLE html_refinements ENABLE ROW LEVEL SECURITY;

-- HTML_REFINEMENTS POLICIES
CREATE POLICY "Users can view refinements for their projects" ON html_refinements
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM projects 
            WHERE projects.id = html_refinements.project_id 
            AND projects.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert refinements for their projects" ON html_refinements
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM projects 
            WHERE projects.id = html_refinements.project_id 
            AND projects.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update refinements for their projects" ON html_refinements
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM projects 
            WHERE projects.id = html_refinements.project_id 
            AND projects.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete refinements for their projects" ON html_refinements
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM projects 
            WHERE projects.id = html_refinements.project_id 
            AND projects.user_id = auth.uid()
        )
    );

-- =====================================================
-- STORAGE BUCKET SETUP
-- =====================================================
-- Create storage bucket for HTML refinements (run this in Supabase dashboard)
-- INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types) 
-- VALUES ('html-refinements', 'html-refinements', false, 52428800, ARRAY['text/html', 'image/png', 'image/jpeg']::text[]);

-- Storage policies for html-refinements bucket
-- CREATE POLICY "Users can upload refinement files for their projects" ON storage.objects
--     FOR INSERT WITH CHECK (
--         bucket_id = 'html-refinements' AND 
--         auth.uid()::text = (storage.foldername(name))[1]
--     );

-- CREATE POLICY "Users can view refinement files for their projects" ON storage.objects
--     FOR SELECT USING (
--         bucket_id = 'html-refinements' AND 
--         auth.uid()::text = (storage.foldername(name))[1]
--     );

-- CREATE POLICY "Users can update refinement files for their projects" ON storage.objects
--     FOR UPDATE USING (
--         bucket_id = 'html-refinements' AND 
--         auth.uid()::text = (storage.foldername(name))[1]
--     );

-- CREATE POLICY "Users can delete refinement files for their projects" ON storage.objects
--     FOR DELETE USING (
--         bucket_id = 'html-refinements' AND 
--         auth.uid()::text = (storage.foldername(name))[1]
--     );

-- =====================================================
-- VERIFICATION QUERIES
-- =====================================================
-- SELECT * FROM html_refinements LIMIT 5;
-- SELECT table_name FROM information_schema.tables WHERE table_name = 'html_refinements';