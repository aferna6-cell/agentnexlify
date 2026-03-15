-- Migration 042: Contractor Bid Manager — bids + bid templates
-- AI generates professional estimates from job descriptions.

CREATE TABLE IF NOT EXISTS bid_templates (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    default_items JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS bids (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    description TEXT,
    items_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    subtotal NUMERIC(10, 2) NOT NULL DEFAULT 0,
    tax NUMERIC(10, 2) NOT NULL DEFAULT 0,
    total NUMERIC(10, 2) NOT NULL DEFAULT 0,
    terms TEXT,
    timeline TEXT,
    warranty TEXT,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'sent', 'viewed', 'accepted', 'rejected', 'expired')),
    pdf_url TEXT,
    sent_at TIMESTAMPTZ,
    viewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_bids_tenant ON bids(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_bids_tenant_created ON bids(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_bid_templates_tenant ON bid_templates(tenant_id);

ALTER TABLE bids ENABLE ROW LEVEL SECURITY;
ALTER TABLE bid_templates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on bids" ON bids
    FOR ALL USING (current_setting('role', true) = 'service_role');
CREATE POLICY "Service role full access on bid_templates" ON bid_templates
    FOR ALL USING (current_setting('role', true) = 'service_role');
