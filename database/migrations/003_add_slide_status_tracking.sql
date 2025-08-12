-- =====================================================
-- Add Slide Status Tracking for Parallel Processing
-- =====================================================
-- This migration adds status tracking fields to the slides table
-- to support real-time parallel slide generation progress

-- Add status field to slides table
ALTER TABLE slides ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'pending';

-- Add check constraint for slide status
ALTER TABLE slides 
ADD CONSTRAINT slides_status_check 
CHECK (status IN ('pending', 'planning', 'content_generation', 'html_generation', 
                  'html_refinement', 'image_prompt_generation', 'image_generation', 
                  'image_refinement', 'quality_review', 'completed', 'failed'));

-- Add processing timestamps
ALTER TABLE slides ADD COLUMN IF NOT EXISTS started_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE slides ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE slides ADD COLUMN IF NOT EXISTS processing_time_seconds INTEGER;

-- Add error tracking
ALTER TABLE slides ADD COLUMN IF NOT EXISTS error_message TEXT;

-- Add current agent processing info
ALTER TABLE slides ADD COLUMN IF NOT EXISTS current_agent TEXT;

-- Add metadata for tracking processing details
ALTER TABLE slides ADD COLUMN IF NOT EXISTS processing_metadata JSONB DEFAULT '{}'::jsonb;

-- Create index for status queries
CREATE INDEX IF NOT EXISTS idx_slides_status ON slides(status);
CREATE INDEX IF NOT EXISTS idx_slides_project_status ON slides(project_id, status);

-- Update existing slides to have 'pending' status
UPDATE slides SET status = 'pending' WHERE status IS NULL;

-- =====================================================
-- Add Slide Processing Events Table (Optional)
-- =====================================================
-- For detailed tracking of slide processing events

CREATE TABLE IF NOT EXISTS slide_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slide_id UUID REFERENCES slides(id) ON DELETE CASCADE NOT NULL,
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE NOT NULL,
  event_type TEXT NOT NULL, -- agent_started, agent_completed, agent_failed, status_changed
  agent_name TEXT,
  event_data JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes for slide events
CREATE INDEX IF NOT EXISTS idx_slide_events_slide_id ON slide_events(slide_id);
CREATE INDEX IF NOT EXISTS idx_slide_events_project_id ON slide_events(project_id);
CREATE INDEX IF NOT EXISTS idx_slide_events_event_type ON slide_events(event_type);
CREATE INDEX IF NOT EXISTS idx_slide_events_created_at ON slide_events(created_at DESC);

-- Enable RLS on slide_events
ALTER TABLE slide_events ENABLE ROW LEVEL SECURITY;

-- RLS Policies for slide_events
CREATE POLICY "Users can view slide events for their projects" ON slide_events
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM projects 
            WHERE projects.id = slide_events.project_id 
            AND projects.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert slide events for their projects" ON slide_events
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM projects 
            WHERE projects.id = slide_events.project_id 
            AND projects.user_id = auth.uid()
        )
    );

-- =====================================================
-- Functions for Slide Status Management
-- =====================================================

-- Function to update slide status with automatic timestamps
CREATE OR REPLACE FUNCTION update_slide_status(
    p_slide_id UUID,
    p_status TEXT,
    p_agent_name TEXT DEFAULT NULL,
    p_error_message TEXT DEFAULT NULL
)
RETURNS BOOLEAN AS $$
DECLARE
    current_time TIMESTAMP WITH TIME ZONE := NOW();
BEGIN
    UPDATE slides 
    SET 
        status = p_status,
        current_agent = p_agent_name,
        error_message = p_error_message,
        updated_at = current_time,
        started_at = CASE 
            WHEN p_status != 'pending' AND started_at IS NULL 
            THEN current_time 
            ELSE started_at 
        END,
        completed_at = CASE 
            WHEN p_status IN ('completed', 'failed') 
            THEN current_time 
            ELSE NULL 
        END,
        processing_time_seconds = CASE 
            WHEN p_status IN ('completed', 'failed') AND started_at IS NOT NULL
            THEN EXTRACT(EPOCH FROM (current_time - started_at))::INTEGER
            ELSE processing_time_seconds
        END
    WHERE id = p_slide_id;
    
    -- Log the status change event
    INSERT INTO slide_events (slide_id, project_id, event_type, agent_name, event_data)
    SELECT 
        p_slide_id,
        project_id,
        'status_changed',
        p_agent_name,
        jsonb_build_object(
            'new_status', p_status,
            'agent_name', p_agent_name,
            'error_message', p_error_message,
            'timestamp', current_time
        )
    FROM slides WHERE id = p_slide_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get project slide progress
CREATE OR REPLACE FUNCTION get_project_slide_progress(p_project_id UUID)
RETURNS TABLE (
    total_slides INTEGER,
    completed_slides INTEGER,
    failed_slides INTEGER,
    in_progress_slides INTEGER,
    pending_slides INTEGER,
    completion_percentage DECIMAL(5,2)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::INTEGER as total_slides,
        COUNT(CASE WHEN status = 'completed' THEN 1 END)::INTEGER as completed_slides,
        COUNT(CASE WHEN status = 'failed' THEN 1 END)::INTEGER as failed_slides,
        COUNT(CASE WHEN status NOT IN ('completed', 'failed', 'pending') THEN 1 END)::INTEGER as in_progress_slides,
        COUNT(CASE WHEN status = 'pending' THEN 1 END)::INTEGER as pending_slides,
        ROUND(
            (COUNT(CASE WHEN status = 'completed' THEN 1 END) * 100.0 / GREATEST(COUNT(*), 1)), 
            2
        ) as completion_percentage
    FROM slides 
    WHERE project_id = p_project_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- Verification Queries
-- =====================================================

-- Run these queries to verify the migration
-- SELECT column_name, data_type, is_nullable, column_default 
-- FROM information_schema.columns 
-- WHERE table_name = 'slides' 
-- ORDER BY ordinal_position;

-- SELECT * FROM get_project_slide_progress('your-project-id');