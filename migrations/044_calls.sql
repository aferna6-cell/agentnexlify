-- Migration 044: AI Answering Service — call records
-- Stores call logs with AI transcripts, summaries, and action items.

CREATE TABLE IF NOT EXISTS calls (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    caller_phone TEXT NOT NULL,
    called_number TEXT,
    direction TEXT NOT NULL DEFAULT 'inbound' CHECK (direction IN ('inbound', 'outbound')),
    duration_seconds INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'completed' CHECK (status IN ('ringing', 'in-progress', 'completed', 'no-answer', 'busy', 'failed')),
    recording_url TEXT,
    transcript JSONB DEFAULT '[]'::jsonb,
    summary TEXT,
    sentiment TEXT CHECK (sentiment IN ('positive', 'neutral', 'negative')),
    action_taken TEXT,
    twilio_call_sid TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_calls_tenant ON calls(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_calls_tenant_status ON calls(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_calls_twilio_sid ON calls(twilio_call_sid) WHERE twilio_call_sid IS NOT NULL;

ALTER TABLE calls ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on calls" ON calls
    FOR ALL USING (current_setting('role', true) = 'service_role');
