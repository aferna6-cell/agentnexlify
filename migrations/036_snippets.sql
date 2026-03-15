-- Migration 036: Snippets / Quick Replies
-- Pre-written response templates for team members to use in live conversations.

CREATE TABLE IF NOT EXISTS snippets (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    shortcut TEXT,
    category TEXT NOT NULL DEFAULT 'General',
    usage_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_snippets_tenant ON snippets(tenant_id);
CREATE INDEX IF NOT EXISTS idx_snippets_tenant_category ON snippets(tenant_id, category);
CREATE UNIQUE INDEX IF NOT EXISTS idx_snippets_shortcut ON snippets(tenant_id, shortcut) WHERE shortcut IS NOT NULL;

-- RLS
ALTER TABLE snippets ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Tenants manage own snippets" ON snippets
    FOR ALL USING (tenant_id::text = current_setting('request.jwt.claims', true)::json->>'tenant_id')
    WITH CHECK (tenant_id::text = current_setting('request.jwt.claims', true)::json->>'tenant_id');

CREATE POLICY "Service role full access on snippets" ON snippets
    FOR ALL USING (current_setting('role', true) = 'service_role');
