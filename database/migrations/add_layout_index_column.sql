-- Add layout_index column to slides table if it doesn't exist
ALTER TABLE slides 
ADD COLUMN IF NOT EXISTS layout_index INTEGER DEFAULT 0;

-- Optional: Add a comment to describe the column
COMMENT ON COLUMN slides.layout_index IS 'PowerPoint layout index for the slide (0-based)';

-- Optional: Update any existing rows that might have NULL values
UPDATE slides 
SET layout_index = 0 
WHERE layout_index IS NULL;