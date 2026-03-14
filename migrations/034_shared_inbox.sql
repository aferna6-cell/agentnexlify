-- Migration 034: Shared team inbox — conversation assignment + internal notes
-- Enables team members to claim conversations and leave internal notes
-- that are invisible to the customer via the widget.

-- Add conversation assignment
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS assigned_to UUID REFERENCES team_members(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_conversations_assigned ON conversations(tenant_id, assigned_to) WHERE assigned_to IS NOT NULL;

-- Internal notes on conversations (team-only, customer never sees)
CREATE TABLE IF NOT EXISTS conversation_notes (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    author_id UUID NOT NULL REFERENCES team_members(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_conversation_notes_conv ON conversation_notes(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversation_notes_tenant ON conversation_notes(tenant_id);

-- RLS
ALTER TABLE conversation_notes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Tenants manage own conversation notes" ON conversation_notes
    FOR ALL USING (tenant_id::text = current_setting('request.jwt.claims', true)::json->>'tenant_id')
    WITH CHECK (tenant_id::text = current_setting('request.jwt.claims', true)::json->>'tenant_id');

CREATE POLICY "Service role full access on conversation_notes" ON conversation_notes
    FOR ALL USING (current_setting('role', true) = 'service_role');
