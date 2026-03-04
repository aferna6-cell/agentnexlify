-- CRM tables: activity log + client notes
-- Run in Supabase SQL editor

-- activity_log: tracks all client interactions
CREATE TABLE activity_log (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    lead_id       UUID REFERENCES leads(id) ON DELETE SET NULL,
    activity_type TEXT NOT NULL,  -- lead_created, lead_updated, stage_change, message, note_added, automation_triggered, email_sent
    description   TEXT NOT NULL,
    metadata      JSONB DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- client_notes: manual CRM notes
CREATE TABLE client_notes (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id  UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    lead_id    UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    content    TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for fast timeline queries
CREATE INDEX idx_activity_log_tenant_lead_created ON activity_log(tenant_id, lead_id, created_at DESC);
CREATE INDEX idx_activity_log_tenant_created ON activity_log(tenant_id, created_at DESC);
CREATE INDEX idx_client_notes_tenant_lead ON client_notes(tenant_id, lead_id);

-- RLS
ALTER TABLE activity_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE client_notes ENABLE ROW LEVEL SECURITY;
