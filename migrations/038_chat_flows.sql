-- Migration 038: Chat flows for visual flow builder
-- Stores customizable chat conversation flows as JSONB.
-- Each flow has nodes (greeting, question, condition, action, handoff)
-- and edges connecting them.

CREATE TABLE IF NOT EXISTS chat_flows (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    flow_json JSONB NOT NULL DEFAULT '{"nodes":[],"edges":[]}'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT false,
    is_template BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chat_flows_tenant ON chat_flows(tenant_id);
CREATE INDEX IF NOT EXISTS idx_chat_flows_active ON chat_flows(tenant_id) WHERE is_active = true;

-- RLS
ALTER TABLE chat_flows ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Tenants manage own chat flows" ON chat_flows
    FOR ALL USING (tenant_id::text = current_setting('request.jwt.claims', true)::json->>'tenant_id')
    WITH CHECK (tenant_id::text = current_setting('request.jwt.claims', true)::json->>'tenant_id');

CREATE POLICY "Service role full access on chat_flows" ON chat_flows
    FOR ALL USING (current_setting('role', true) = 'service_role');
