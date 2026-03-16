-- Migration 047: CSAT/NPS satisfaction surveys
-- Auto-sent after conversations are resolved. Tracks customer satisfaction.

CREATE TABLE IF NOT EXISTS csat_responses (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    session_id TEXT,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    feedback TEXT,
    channel TEXT NOT NULL DEFAULT 'email',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_csat_tenant ON csat_responses(tenant_id, created_at DESC);

ALTER TABLE csat_responses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on csat_responses" ON csat_responses
    FOR ALL USING (current_setting('role', true) = 'service_role');
