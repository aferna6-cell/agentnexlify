-- Migration 027: AI feedback table for conversation tuning
-- Lets business owners rate AI responses and provide corrections.
-- Corrections are injected into the system prompt to improve future responses.

CREATE TABLE IF NOT EXISTS ai_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL,
    message_index INTEGER NOT NULL,
    rating TEXT NOT NULL CHECK (rating IN ('thumbs_up', 'thumbs_down')),
    correction TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ai_feedback_tenant ON ai_feedback(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_feedback_session ON ai_feedback(tenant_id, session_id);

ALTER TABLE ai_feedback ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Tenants manage own feedback" ON ai_feedback
    FOR ALL USING (tenant_id = auth.uid());
