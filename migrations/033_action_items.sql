-- Migration 033: Action items extracted from conversations by AI
-- Turns passive conversation history into an active to-do list.
-- AI extracts actionable items like "send quote by Friday" or "schedule follow-up call".

CREATE TABLE IF NOT EXISTS action_items (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    description TEXT NOT NULL,
    due_date DATE,
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'done', 'dismissed')),
    assigned_to UUID REFERENCES team_members(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_action_items_tenant_status ON action_items(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_action_items_tenant_due ON action_items(tenant_id, due_date) WHERE due_date IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_action_items_conversation ON action_items(conversation_id) WHERE conversation_id IS NOT NULL;

-- RLS
ALTER TABLE action_items ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Tenants manage own action items" ON action_items
    FOR ALL USING (tenant_id::text = current_setting('request.jwt.claims', true)::json->>'tenant_id')
    WITH CHECK (tenant_id::text = current_setting('request.jwt.claims', true)::json->>'tenant_id');

CREATE POLICY "Service role full access on action_items" ON action_items
    FOR ALL USING (current_setting('role', true) = 'service_role');
