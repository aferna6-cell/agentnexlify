-- Google Calendar integration: integrations table + appointments google_event_id

CREATE TABLE IF NOT EXISTS integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    access_token TEXT,
    refresh_token TEXT,
    token_expiry TIMESTAMPTZ,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, provider)
);

CREATE INDEX IF NOT EXISTS idx_integrations_tenant ON integrations(tenant_id);

-- RLS
ALTER TABLE integrations ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS integrations_service ON integrations;
CREATE POLICY integrations_service ON integrations FOR ALL USING (true) WITH CHECK (true);

-- Add google_event_id to appointments
ALTER TABLE appointments ADD COLUMN IF NOT EXISTS google_event_id TEXT;
