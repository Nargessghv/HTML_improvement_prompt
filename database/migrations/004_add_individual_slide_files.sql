-- =====================================================
-- Add Individual Slide File Support
-- =====================================================
-- This migration adds support for storing individual slide PPTX files
-- and tracking their generation/storage status

-- Add file tracking columns to slides table
ALTER TABLE slides ADD COLUMN IF NOT EXISTS individual_pptx_path TEXT;
ALTER TABLE slides ADD COLUMN IF NOT EXISTS individual_pptx_url TEXT;
ALTER TABLE slides ADD COLUMN IF NOT EXISTS individual_pptx_size INTEGER;
ALTER TABLE slides ADD COLUMN IF NOT EXISTS individual_pptx_generated_at TIMESTAMP WITH TIME ZONE;

-- Create slide_files table for comprehensive file tracking
CREATE TABLE IF NOT EXISTS slide_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slide_id UUID REFERENCES slides(id) ON DELETE CASCADE NOT NULL,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE NOT NULL,
    file_type TEXT NOT NULL, -- 'individual_pptx', 'preview_image', 'pdf_export'
    file_path TEXT NOT NULL, -- Supabase Storage path
    file_url TEXT, -- Signed URL for access
    file_name TEXT NOT NULL,
    file_size INTEGER,
    mime_type TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE -- For signed URLs
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_slide_files_slide_id ON slide_files(slide_id);
CREATE INDEX IF NOT EXISTS idx_slide_files_project_id ON slide_files(project_id);
CREATE INDEX IF NOT EXISTS idx_slide_files_type ON slide_files(file_type);
CREATE INDEX IF NOT EXISTS idx_slides_individual_pptx ON slides(individual_pptx_path) WHERE individual_pptx_path IS NOT NULL;

-- Add check constraint for file types
ALTER TABLE slide_files 
ADD CONSTRAINT slide_files_type_check 
CHECK (file_type IN ('individual_pptx', 'preview_image', 'pdf_export', 'html_debug'));

-- Enable RLS on slide_files
ALTER TABLE slide_files ENABLE ROW LEVEL SECURITY;

-- RLS Policies for slide_files
CREATE POLICY "Users can view slide files for their projects" ON slide_files
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM projects 
            WHERE projects.id = slide_files.project_id 
            AND projects.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert slide files for their projects" ON slide_files
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM projects 
            WHERE projects.id = slide_files.project_id 
            AND projects.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update slide files for their projects" ON slide_files
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM projects 
            WHERE projects.id = slide_files.project_id 
            AND projects.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete slide files for their projects" ON slide_files
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM projects 
            WHERE projects.id = slide_files.project_id 
            AND projects.user_id = auth.uid()
        )
    );

-- Add updated_at trigger for slide_files
DROP TRIGGER IF EXISTS update_slide_files_updated_at ON slide_files;
CREATE TRIGGER update_slide_files_updated_at 
    BEFORE UPDATE ON slide_files 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to get slide with files
CREATE OR REPLACE FUNCTION get_slide_with_files(p_slide_id UUID)
RETURNS TABLE (
    slide_id UUID,
    slide_number INTEGER,
    title TEXT,
    status TEXT,
    individual_pptx_path TEXT,
    individual_pptx_url TEXT,
    files JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.id as slide_id,
        s.slide_number,
        s.title,
        s.status,
        s.individual_pptx_path,
        s.individual_pptx_url,
        COALESCE(
            jsonb_agg(
                jsonb_build_object(
                    'id', sf.id,
                    'file_type', sf.file_type,
                    'file_name', sf.file_name,
                    'file_url', sf.file_url,
                    'file_size', sf.file_size,
                    'created_at', sf.created_at
                )
            ) FILTER (WHERE sf.id IS NOT NULL),
            '[]'::jsonb
        ) as files
    FROM slides s
    LEFT JOIN slide_files sf ON s.id = sf.slide_id
    WHERE s.id = p_slide_id
    GROUP BY s.id, s.slide_number, s.title, s.status, s.individual_pptx_path, s.individual_pptx_url;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to clean up expired URLs
CREATE OR REPLACE FUNCTION cleanup_expired_slide_file_urls()
RETURNS INTEGER AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE slide_files 
    SET 
        file_url = NULL,
        expires_at = NULL,
        updated_at = NOW()
    WHERE expires_at IS NOT NULL 
    AND expires_at < NOW();
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create a scheduled cleanup function (to be called by cron/scheduler)
CREATE OR REPLACE FUNCTION schedule_slide_file_cleanup()
RETURNS VOID AS $$
BEGIN
    PERFORM cleanup_expired_slide_file_urls();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- Verification Queries
-- =====================================================

-- Run these queries to verify the migration
-- SELECT column_name, data_type, is_nullable 
-- FROM information_schema.columns 
-- WHERE table_name = 'slides' AND column_name LIKE '%pptx%'
-- ORDER BY ordinal_position;

-- SELECT * FROM slide_files LIMIT 1;
-- SELECT * FROM get_slide_with_files('sample-uuid');
-- SELECT cleanup_expired_slide_file_urls();