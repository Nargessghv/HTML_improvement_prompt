-- Migration: Add missing HTML-related columns to slides table
-- Date: 2025-01-19

-- Add requires_html column to track if HTML generation is needed
ALTER TABLE slides 
ADD COLUMN IF NOT EXISTS requires_html BOOLEAN DEFAULT false;

-- Add html_ready column to indicate when HTML content is ready
ALTER TABLE slides 
ADD COLUMN IF NOT EXISTS html_ready BOOLEAN DEFAULT false;

-- Add status column to track slide processing status
ALTER TABLE slides 
ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'pending';

-- Add layout_index column for proper slide generation
ALTER TABLE slides 
ADD COLUMN IF NOT EXISTS layout_index INTEGER DEFAULT 0;

-- Add comments to explain column purposes
COMMENT ON COLUMN slides.requires_html IS 'Indicates if this slide requires HTML visualization generation';
COMMENT ON COLUMN slides.html_ready IS 'Flag to indicate when HTML content generation is complete';
COMMENT ON COLUMN slides.status IS 'Processing status: pending, in_progress, completed, failed';
COMMENT ON COLUMN slides.layout_index IS 'Index of the layout to use in the PowerPoint template';