-- Migration 032: Tenant tag definitions for AI conversation auto-categorization
-- Tags are preset business categories (not freeform lead tags).
-- System tags are seeded and read-only; tenants can add custom tags.

CREATE TABLE IF NOT EXISTS tenant_tag_definitions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    tag_name TEXT NOT NULL,
    tag_color TEXT NOT NULL DEFAULT '#6b7280',
    is_system BOOLEAN NOT NULL DEFAULT false,
    is_enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Index for tenant lookups
CREATE INDEX IF NOT EXISTS idx_tag_definitions_tenant ON tenant_tag_definitions(tenant_id);

-- Unique constraint: no duplicate tag names per tenant
CREATE UNIQUE INDEX IF NOT EXISTS idx_tag_definitions_unique ON tenant_tag_definitions(tenant_id, tag_name);

-- RLS
ALTER TABLE tenant_tag_definitions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Tenants manage own tag definitions" ON tenant_tag_definitions
    FOR ALL USING (tenant_id = auth.uid()::uuid);

-- Seed 6 system tags for all existing tenants
-- (For new tenants, the backend will seed on first access)
INSERT INTO tenant_tag_definitions (tenant_id, tag_name, tag_color, is_system)
SELECT t.id, tag.name, tag.color, true
FROM tenants t
CROSS JOIN (VALUES
    ('New Lead', '#3b82f6'),
    ('Pricing Question', '#f59e0b'),
    ('Complaint', '#ef4444'),
    ('Appointment Request', '#22c55e'),
    ('Urgent', '#dc2626'),
    ('Follow-up Needed', '#8b5cf6')
) AS tag(name, color)
ON CONFLICT (tenant_id, tag_name) DO NOTHING;
