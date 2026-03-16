-- Migration 048: Custom lead fields — per-tenant configurable attributes
-- Stores field definitions per tenant and custom values per lead.

CREATE TABLE IF NOT EXISTS custom_field_definitions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    field_name TEXT NOT NULL,
    field_type TEXT NOT NULL DEFAULT 'text' CHECK (field_type IN ('text', 'number', 'dropdown', 'date', 'checkbox')),
    options JSONB DEFAULT '[]'::jsonb,
    is_required BOOLEAN NOT NULL DEFAULT false,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(tenant_id, field_name)
);

ALTER TABLE leads ADD COLUMN IF NOT EXISTS custom_fields JSONB DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_custom_field_defs_tenant ON custom_field_definitions(tenant_id);

ALTER TABLE custom_field_definitions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on custom_field_definitions" ON custom_field_definitions
    FOR ALL USING (current_setting('role', true) = 'service_role');
