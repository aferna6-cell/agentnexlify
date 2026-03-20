-- Migration 063: Service types for appointment booking
-- Allows different services to have different durations

CREATE TABLE IF NOT EXISTS service_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL DEFAULT 30,
    description TEXT,
    price NUMERIC(10, 2),
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_service_types_tenant ON service_types(tenant_id);

ALTER TABLE service_types ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_all_service_types" ON service_types FOR ALL USING (true) WITH CHECK (true);
