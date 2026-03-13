-- Migration 029: Menu items for restaurant order taking
-- Stores menu items (food/drinks) for restaurant tenants

CREATE TABLE IF NOT EXISTS menu_items (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    price NUMERIC(10, 2) NOT NULL,
    category TEXT NOT NULL DEFAULT 'uncategorized',
    modifiers_json JSONB DEFAULT '[]'::jsonb,
    available BOOLEAN NOT NULL DEFAULT true,
    image_url TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Index for fast lookups by tenant + category
CREATE INDEX IF NOT EXISTS idx_menu_items_tenant_category ON menu_items(tenant_id, category);

-- RLS
ALTER TABLE menu_items ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Tenants manage their own menu items"
    ON menu_items FOR ALL
    USING (tenant_id::text = current_setting('request.jwt.claims', true)::json->>'tenant_id')
    WITH CHECK (tenant_id::text = current_setting('request.jwt.claims', true)::json->>'tenant_id');

-- Service role bypass
CREATE POLICY "Service role full access on menu_items"
    ON menu_items FOR ALL
    USING (current_setting('role', true) = 'service_role');
