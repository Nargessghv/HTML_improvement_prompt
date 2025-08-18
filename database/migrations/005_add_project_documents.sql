-- Migration: Add project documents support
-- Purpose: Allow users to upload context documents (PDF, Word, PowerPoint, txt) for presentation generation

-- Create table for project context documents
CREATE TABLE IF NOT EXISTS project_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    
    -- Document metadata
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL, -- pdf, docx, pptx, txt
    file_size INTEGER NOT NULL, -- in bytes
    mime_type TEXT NOT NULL,
    
    -- Storage information
    storage_path TEXT NOT NULL, -- Supabase Storage path
    storage_url TEXT, -- Signed URL for downloading
    
    -- Document processing
    processing_status TEXT DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
    extracted_text TEXT, -- Extracted text content for context
    extracted_metadata JSONB DEFAULT '{}'::jsonb, -- Additional metadata (page count, author, etc.)
    error_message TEXT, -- Error message if processing failed
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    processed_at TIMESTAMPTZ,
    
    -- Ensure unique filename per project
    UNIQUE(project_id, filename)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_project_documents_project_id ON project_documents(project_id);
CREATE INDEX IF NOT EXISTS idx_project_documents_user_id ON project_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_project_documents_processing_status ON project_documents(processing_status);

-- Add document context reference to projects table
ALTER TABLE projects ADD COLUMN IF NOT EXISTS has_context_documents BOOLEAN DEFAULT false;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS context_document_ids UUID[] DEFAULT ARRAY[]::UUID[];

-- Add document context to workflow_states for tracking
ALTER TABLE workflow_states ADD COLUMN IF NOT EXISTS context_documents JSONB DEFAULT '[]'::jsonb;

-- Create storage bucket for documents (run in Supabase dashboard)
-- INSERT INTO storage.buckets (id, name, public) 
-- VALUES ('project-documents', 'project-documents', false)
-- ON CONFLICT (id) DO NOTHING;

-- Enable RLS for project_documents
ALTER TABLE project_documents ENABLE ROW LEVEL SECURITY;

-- RLS policies for project_documents
-- Users can view their own documents
CREATE POLICY "Users can view own project documents" ON project_documents
    FOR SELECT USING (auth.uid() = user_id);

-- Users can insert documents for their projects
CREATE POLICY "Users can insert own project documents" ON project_documents
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Users can update their own documents
CREATE POLICY "Users can update own project documents" ON project_documents
    FOR UPDATE USING (auth.uid() = user_id);

-- Users can delete their own documents
CREATE POLICY "Users can delete own project documents" ON project_documents
    FOR DELETE USING (auth.uid() = user_id);

-- Service role can do everything (for backend processing)
CREATE POLICY "Service role has full access to project documents" ON project_documents
    FOR ALL USING (auth.jwt()->>'role' = 'service_role');

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_project_documents_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update updated_at
CREATE TRIGGER update_project_documents_updated_at_trigger
    BEFORE UPDATE ON project_documents
    FOR EACH ROW
    EXECUTE FUNCTION update_project_documents_updated_at();

-- Function to update project has_context_documents flag
CREATE OR REPLACE FUNCTION update_project_context_flag()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE projects 
        SET has_context_documents = true,
            context_document_ids = array_append(context_document_ids, NEW.id)
        WHERE id = NEW.project_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE projects 
        SET context_document_ids = array_remove(context_document_ids, OLD.id),
            has_context_documents = (
                SELECT COUNT(*) > 0 
                FROM project_documents 
                WHERE project_id = OLD.project_id AND id != OLD.id
            )
        WHERE id = OLD.project_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update project context flags
CREATE TRIGGER update_project_context_on_document_change
    AFTER INSERT OR DELETE ON project_documents
    FOR EACH ROW
    EXECUTE FUNCTION update_project_context_flag();