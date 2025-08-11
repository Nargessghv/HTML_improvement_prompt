-- Migration: Add Row Level Security policies for interactive tables
-- Created: 2025-07-23

-- Enable RLS on all interactive tables
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE presentation_drafts ENABLE ROW LEVEL SECURITY;
ALTER TABLE slide_drafts ENABLE ROW LEVEL SECURITY;
ALTER TABLE slide_comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE slide_edit_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE slide_previews ENABLE ROW LEVEL SECURITY;

-- Chat Sessions Policies
CREATE POLICY "Users can view their own chat sessions" ON chat_sessions
    FOR SELECT USING (
        project_id IN (
            SELECT id FROM projects WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can create chat sessions for their projects" ON chat_sessions
    FOR INSERT WITH CHECK (
        project_id IN (
            SELECT id FROM projects WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update their own chat sessions" ON chat_sessions
    FOR UPDATE USING (
        project_id IN (
            SELECT id FROM projects WHERE user_id = auth.uid()
        )
    );

-- Presentation Drafts Policies
CREATE POLICY "Users can view their own presentation drafts" ON presentation_drafts
    FOR SELECT USING (
        project_id IN (
            SELECT id FROM projects WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can create presentation drafts for their projects" ON presentation_drafts
    FOR INSERT WITH CHECK (
        project_id IN (
            SELECT id FROM projects WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update their own presentation drafts" ON presentation_drafts
    FOR UPDATE USING (
        project_id IN (
            SELECT id FROM projects WHERE user_id = auth.uid()
        )
    );

-- Slide Drafts Policies
CREATE POLICY "Users can view their own slide drafts" ON slide_drafts
    FOR SELECT USING (
        project_id IN (
            SELECT id FROM projects WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can create slide drafts for their projects" ON slide_drafts
    FOR INSERT WITH CHECK (
        project_id IN (
            SELECT id FROM projects WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update their own slide drafts" ON slide_drafts
    FOR UPDATE USING (
        project_id IN (
            SELECT id FROM projects WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete their own slide drafts" ON slide_drafts
    FOR DELETE USING (
        project_id IN (
            SELECT id FROM projects WHERE user_id = auth.uid()
        )
    );

-- Slide Comments Policies
CREATE POLICY "Users can view comments on their slides" ON slide_comments
    FOR SELECT USING (
        slide_draft_id IN (
            SELECT id FROM slide_drafts WHERE project_id IN (
                SELECT id FROM projects WHERE user_id = auth.uid()
            )
        )
    );

CREATE POLICY "Users can create comments on their slides" ON slide_comments
    FOR INSERT WITH CHECK (
        auth.uid() = user_id AND
        slide_draft_id IN (
            SELECT id FROM slide_drafts WHERE project_id IN (
                SELECT id FROM projects WHERE user_id = auth.uid()
            )
        )
    );

CREATE POLICY "Users can update their own comments" ON slide_comments
    FOR UPDATE USING (
        user_id = auth.uid()
    );

CREATE POLICY "Users can delete their own comments" ON slide_comments
    FOR DELETE USING (
        user_id = auth.uid()
    );

-- Slide Edit Requests Policies
CREATE POLICY "Users can view edit requests for their slides" ON slide_edit_requests
    FOR SELECT USING (
        slide_draft_id IN (
            SELECT id FROM slide_drafts WHERE project_id IN (
                SELECT id FROM projects WHERE user_id = auth.uid()
            )
        )
    );

CREATE POLICY "Users can create edit requests for their slides" ON slide_edit_requests
    FOR INSERT WITH CHECK (
        auth.uid() = user_id AND
        slide_draft_id IN (
            SELECT id FROM slide_drafts WHERE project_id IN (
                SELECT id FROM projects WHERE user_id = auth.uid()
            )
        )
    );

CREATE POLICY "Users can update their own edit requests" ON slide_edit_requests
    FOR UPDATE USING (
        user_id = auth.uid() AND status = 'pending'
    );

-- Slide Previews Policies
CREATE POLICY "Users can view previews of their slides" ON slide_previews
    FOR SELECT USING (
        slide_draft_id IN (
            SELECT id FROM slide_drafts WHERE project_id IN (
                SELECT id FROM projects WHERE user_id = auth.uid()
            )
        )
    );

CREATE POLICY "Service role can manage slide previews" ON slide_previews
    FOR ALL USING (auth.role() = 'service_role');

-- Grant necessary permissions to authenticated users
GRANT SELECT, INSERT, UPDATE ON chat_sessions TO authenticated;
GRANT SELECT, INSERT, UPDATE ON presentation_drafts TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON slide_drafts TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON slide_comments TO authenticated;
GRANT SELECT, INSERT, UPDATE ON slide_edit_requests TO authenticated;
GRANT SELECT ON slide_previews TO authenticated;

-- Grant service role full access for backend operations
GRANT ALL ON chat_sessions TO service_role;
GRANT ALL ON presentation_drafts TO service_role;
GRANT ALL ON slide_drafts TO service_role;
GRANT ALL ON slide_comments TO service_role;
GRANT ALL ON slide_edit_requests TO service_role;
GRANT ALL ON slide_previews TO service_role;