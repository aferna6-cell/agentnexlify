-- Migration 079: Wizard drop-off tracking
-- Lightweight event table for onboarding wizard funnel analytics.

CREATE TABLE IF NOT EXISTS wizard_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    step INTEGER NOT NULL CHECK (step >= 1 AND step <= 6),
    action TEXT NOT NULL CHECK (action IN ('enter', 'complete', 'skip', 'abandon')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_wizard_events_tenant ON wizard_events(tenant_id);
CREATE INDEX IF NOT EXISTS idx_wizard_events_step ON wizard_events(step);

-- RLS
ALTER TABLE wizard_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_full_access" ON wizard_events
    FOR ALL USING (true) WITH CHECK (true);
