-- 067: Lead Scoring Configuration
-- Per-tenant configurable lead scoring weights so businesses can customize
-- which signals matter most for their industry.

CREATE TABLE IF NOT EXISTS scoring_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    factor TEXT NOT NULL,
    weight INTEGER NOT NULL DEFAULT 10 CHECK (weight >= 0 AND weight <= 100),
    description TEXT,
    is_enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_scoring_configs_tenant_factor ON scoring_configs(tenant_id, factor);
CREATE INDEX IF NOT EXISTS idx_scoring_configs_tenant ON scoring_configs(tenant_id);

ALTER TABLE scoring_configs ENABLE ROW LEVEL SECURITY;
