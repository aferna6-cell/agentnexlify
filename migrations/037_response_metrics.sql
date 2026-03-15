-- Migration 037: Response metrics for analytics dashboard upgrade
-- Tracks response times, conversation outcomes, and channel data.

CREATE TABLE IF NOT EXISTS response_metrics (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    session_id TEXT,
    first_message_at TIMESTAMPTZ,
    first_response_at TIMESTAMPTZ,
    response_time_seconds INTEGER,
    channel TEXT NOT NULL DEFAULT 'widget',
    resolved_at TIMESTAMPTZ,
    outcome TEXT CHECK (outcome IN ('lead_captured', 'appointment_booked', 'question_answered', 'order_placed', 'no_action')),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_response_metrics_tenant ON response_metrics(tenant_id);
CREATE INDEX IF NOT EXISTS idx_response_metrics_tenant_created ON response_metrics(tenant_id, created_at DESC);

-- RLS
ALTER TABLE response_metrics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Tenants view own response metrics" ON response_metrics
    FOR ALL USING (tenant_id::text = current_setting('request.jwt.claims', true)::json->>'tenant_id')
    WITH CHECK (tenant_id::text = current_setting('request.jwt.claims', true)::json->>'tenant_id');

CREATE POLICY "Service role full access on response_metrics" ON response_metrics
    FOR ALL USING (current_setting('role', true) = 'service_role');
