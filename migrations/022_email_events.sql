-- Migration 022: Email event tracking (opens, clicks)
-- Tracks email opens via tracking pixel and link clicks via redirect.
-- Works for both sequence emails and campaign blasts.

CREATE TABLE IF NOT EXISTS email_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,  -- 'open', 'click'
    execution_id UUID,  -- populated for sequence emails
    campaign_tag TEXT,  -- populated for campaign blasts
    details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_events_tenant ON email_events(tenant_id);
CREATE INDEX IF NOT EXISTS idx_email_events_exec ON email_events(execution_id) WHERE execution_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_email_events_type ON email_events(event_type, created_at);

ALTER TABLE email_events ENABLE ROW LEVEL SECURITY;
