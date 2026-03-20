-- Migration 059: Invoice item templates (line item library)
-- Reusable line items that can be quickly added to invoices

CREATE TABLE IF NOT EXISTS invoice_item_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL DEFAULT 0,
    category TEXT,
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_item_templates_tenant ON invoice_item_templates(tenant_id);

-- RLS
ALTER TABLE invoice_item_templates ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_all_item_templates" ON invoice_item_templates
    FOR ALL USING (true) WITH CHECK (true);
