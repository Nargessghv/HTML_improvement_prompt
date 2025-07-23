# HTML Refinement Tracking Setup

This guide explains how to set up the new HTML refinement tracking feature that stores refinement iterations in Supabase Storage and provides a frontend visualization interface.

## Overview

The HTML refinement tracking system captures each iteration of HTML refinement during the slide generation process, storing both the HTML content and visual screenshots in Supabase Storage, with metadata tracked in the database. Users can then visualize the refinement progression through a dedicated frontend component.

## Backend Setup

### 1. Database Schema

First, run the refinement schema SQL script in your Supabase SQL editor:

```bash
# Run this file in Supabase SQL Editor
database-schema-refinements.sql
```

This creates:
- `html_refinements` table for storing refinement metadata
- Proper indexes and RLS policies
- Updated triggers for `updated_at` columns

### 2. Supabase Storage Bucket

Create the storage bucket in your Supabase dashboard:

1. Go to Storage → Buckets
2. Create a new bucket named `html-refinements`
3. Set it as **private** (public = false)
4. Set file size limit to 50MB
5. Allow MIME types: `text/html`, `image/png`, `image/jpeg`

Or run this SQL in your Supabase SQL editor:

```sql
-- Create storage bucket for HTML refinements
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types) 
VALUES ('html-refinements', 'html-refinements', false, 52428800, ARRAY['text/html', 'image/png', 'image/jpeg']::text[]);

-- Storage policies for html-refinements bucket
CREATE POLICY "Users can upload refinement files for their projects" ON storage.objects
    FOR INSERT WITH CHECK (
        bucket_id = 'html-refinements' AND 
        auth.uid()::text = (storage.foldername(name))[1]
    );

CREATE POLICY "Users can view refinement files for their projects" ON storage.objects
    FOR SELECT USING (
        bucket_id = 'html-refinements' AND 
        auth.uid()::text = (storage.foldername(name))[1]
    );

CREATE POLICY "Users can update refinement files for their projects" ON storage.objects
    FOR UPDATE USING (
        bucket_id = 'html-refinements' AND 
        auth.uid()::text = (storage.foldername(name))[1]
    );

CREATE POLICY "Users can delete refinement files for their projects" ON storage.objects
    FOR DELETE USING (
        bucket_id = 'html-refinements' AND 
        auth.uid()::text = (storage.foldername(name))[1]
    );
```

### 3. Environment Variables

Ensure your backend has the necessary environment variables:

```bash
# .env file (backend)
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key  # Required for storage operations
SUPABASE_ANON_KEY=your_anon_key
```

### 4. Backend Dependencies

The refinement tracking system uses these new backend modules:
- `src/supabase_storage.py` - Handles file uploads to Supabase Storage
- `src/database.py` - Extended with HTML refinement database operations
- `src/agents.py` - HTMLRefinementAgent updated with tracking integration

## Frontend Setup

### 1. Component Integration

The `RefinementViewer` component is automatically integrated into the project detail page for projects with status `processing` or `completed`.

### 2. Dependencies

The frontend component uses these UI components (already available):
- `@/components/ui/card`
- `@/components/ui/button`
- `@/components/ui/badge`
- `@/components/ui/tabs`
- `@/components/ui/scroll-area`
- `@/components/ui/dialog`

## Features

### Storage Organization

Files are organized in Supabase Storage with this structure:
```
html-refinements/
├── {project_id}/
│   ├── {slide_id}/
│   │   ├── iteration_01/
│   │   │   ├── refined_html_20241221_143025.html
│   │   │   └── screenshot_20241221_143025.png
│   │   ├── iteration_02/
│   │   │   ├── refined_html_20241221_143128.html
│   │   │   └── screenshot_20241221_143128.png
│   │   └── ...
```

### Database Tracking

Each refinement iteration stores:
- HTML content (full text)
- File URLs (Supabase Storage public URLs)
- LLM feedback and reasoning
- Refinement prompt used
- Iteration number and timestamps
- Final version flag

### Frontend Features

The RefinementViewer component provides:
- **Slide Selection**: Choose from slides with HTML refinements
- **Iteration Navigation**: Step through refinement iterations
- **Dual View Modes**: Visual preview or HTML code view
- **Timeline View**: Visual timeline of all refinements
- **Download**: Export HTML files locally
- **Full Screen**: Expand previews for detailed inspection
- **Real-time Updates**: Automatic refresh during processing

## Usage

### For Development

1. Ensure your backend environment has the required Supabase credentials
2. Run the database schema migration
3. Create the storage bucket with proper policies
4. Start your backend server
5. Frontend will automatically show refinements for processing/completed projects

### For Production

1. Apply the database schema to your production Supabase instance
2. Create the production storage bucket
3. Update your production environment variables
4. Deploy the updated backend code
5. Deploy the updated frontend code

## Monitoring

The system logs refinement tracking operations:
- ✅ Successful uploads and database records
- ⚠️ Non-critical failures (continues processing)
- ❌ Critical failures (stops refinement for that slide)

## File Size Considerations

- HTML files are typically small (< 100KB)
- PNG screenshots are compressed and optimized for LLM processing
- Target size: ~5MB per image after compression
- Storage bucket limit: 50MB per file
- Automatic cleanup of old local debug files

## Security

- All files are stored privately in Supabase Storage
- RLS policies ensure users only access their own project refinements
- File uploads are authenticated with service role key
- Frontend access uses user JWT tokens through RLS

## Troubleshooting

### Common Issues

**"Supabase clients not available"**
- Check environment variables are set correctly
- Ensure `SUPABASE_SERVICE_ROLE_KEY` is provided for backend

**"Failed to upload refinement files"**
- Verify storage bucket exists and is named `html-refinements`
- Check storage policies are correctly applied
- Confirm service role key has storage permissions

**"No HTML refinements found"**
- Ensure project has completed HTML generation phase
- Check that slides contain HTML content (not just text)
- Verify database schema was applied correctly

### Debugging

Enable detailed logging by setting:
```bash
# Add to backend environment
LOG_LEVEL=DEBUG
```

This will show detailed Supabase operation logs and help identify issues.

## Future Enhancements

Potential future improvements:
- **Diff Visualization**: Show changes between iterations
- **User Feedback**: Allow users to mark preferred iterations
- **Batch Download**: Download all refinements as ZIP
- **Sharing**: Share refinement progressions with others
- **Analytics**: Track refinement patterns and success rates