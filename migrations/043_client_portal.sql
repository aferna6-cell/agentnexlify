-- Migration 043: Client Portal — service records + portal tokens
-- Customers get a link to view service history, photos, and rebook.

CREATE TABLE IF NOT EXISTS service_records (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    description TEXT,
    service_date DATE,
    photos_json JSONB DEFAULT '[]'::jsonb,
    documents_json JSONB DEFAULT '[]'::jsonb,
    notes TEXT,
    invoice_amount NUMERIC(10, 2),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS portal_tokens (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_service_records_tenant ON service_records(tenant_id);
CREATE INDEX IF NOT EXISTS idx_service_records_lead ON service_records(lead_id);
CREATE INDEX IF NOT EXISTS idx_portal_tokens_token ON portal_tokens(token);
CREATE INDEX IF NOT EXISTS idx_portal_tokens_lead ON portal_tokens(tenant_id, lead_id);

ALTER TABLE service_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE portal_tokens ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on service_records" ON service_records
    FOR ALL USING (current_setting('role', true) = 'service_role');
CREATE POLICY "Service role full access on portal_tokens" ON portal_tokens
    FOR ALL USING (current_setting('role', true) = 'service_role');
