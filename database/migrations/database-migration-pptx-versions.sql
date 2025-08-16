-- Migration: Add PPTX version support to html_refinements table
-- This enables storing PPTX versions for each HTML refinement iteration

-- Add PPTX file URL column to track individual slide PPTX versions
ALTER TABLE html_refinements 
ADD COLUMN IF NOT EXISTS pptx_file_url TEXT;

-- Add comment to the new column
COMMENT ON COLUMN html_refinements.pptx_file_url IS 'Supabase Storage URL for PPTX version of this refinement iteration';

-- Update the README table documentation comment for clarity
COMMENT ON TABLE html_refinements IS 'Tracks HTML refinement iterations with HTML, image, and PPTX versions for each iteration';