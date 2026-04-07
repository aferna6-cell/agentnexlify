-- Migration 057: Index + backfill channel column on conversations
-- Note: channel column already exists (DEFAULT 'widget'). conversations uses client_id.
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS client_id UUID REFERENCES tenants(id) ON DELETE CASCADE;
UPDATE conversations SET client_id = tenant_id WHERE client_id IS NULL AND tenant_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_conversations_channel ON conversations(client_id, channel);
UPDATE conversations SET channel = 'sms' WHERE session_id LIKE 'sms_%' AND (channel IS NULL OR channel = 'widget');
