-- Migration 057: Index + backfill channel column on conversations
-- Note: channel column already exists (DEFAULT 'widget'). conversations uses client_id.
CREATE INDEX IF NOT EXISTS idx_conversations_channel ON conversations(client_id, channel);
UPDATE conversations SET channel = 'sms' WHERE session_id LIKE 'sms_%' AND (channel IS NULL OR channel = 'widget');
