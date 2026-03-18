-- Migration 053: Smart Lists (Dynamic Lead Segments)
-- Tenant-configurable saved filters that dynamically resolve to lead sets.

CREATE TABLE IF NOT EXISTS smart_lists (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  filter_json JSONB NOT NULL DEFAULT '{}',
  cached_lead_count INTEGER DEFAULT 0,
  last_refreshed_at TIMESTAMPTZ,
  is_default BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_smart_lists_tenant ON smart_lists(tenant_id);
ALTER TABLE smart_lists ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access on smart_lists" ON smart_lists
    FOR ALL USING (current_setting('role', true) = 'service_role');
