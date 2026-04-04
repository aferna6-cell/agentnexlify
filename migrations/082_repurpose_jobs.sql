-- 082: Content Repurpose Jobs table
-- Stores AI-generated repurposed content from any source

CREATE TABLE IF NOT EXISTS repurpose_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    source_type TEXT NOT NULL,
    source_url TEXT,
    source_content TEXT NOT NULL,
    source_title TEXT,
    tone TEXT DEFAULT 'professional',
    outputs JSONB,
    status TEXT DEFAULT 'processing',
    connected_social_post_ids UUID[] DEFAULT '{}',
    connected_email_sequence_id UUID,
    created_via TEXT DEFAULT 'dashboard',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX repurpose_jobs_tenant_idx ON repurpose_jobs (tenant_id);
CREATE INDEX repurpose_jobs_status_idx ON repurpose_jobs (status);

ALTER TABLE repurpose_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Tenants can manage own repurpose jobs"
    ON repurpose_jobs FOR ALL
    USING (tenant_id = auth.uid())
    WITH CHECK (tenant_id = auth.uid());

CREATE POLICY "Service role full access on repurpose_jobs"
    ON repurpose_jobs FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
