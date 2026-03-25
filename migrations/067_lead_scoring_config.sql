-- Migration 067: Lead Scoring Configuration
-- Per-tenant configurable scoring weights for lead scoring v2.

CREATE TABLE IF NOT EXISTS scoring_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    factor TEXT NOT NULL,
    weight INTEGER NOT NULL DEFAULT 10 CHECK (weight >= 0 AND weight <= 100),
    description TEXT,
    is_enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_scoring_config_tenant_factor ON scoring_configs(tenant_id, factor);
CREATE INDEX idx_scoring_config_tenant ON scoring_configs(tenant_id);

ALTER TABLE scoring_configs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access on scoring_configs"
    ON scoring_configs FOR ALL
    USING (true)
    WITH CHECK (true);
