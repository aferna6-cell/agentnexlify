-- chat_messages: dedicated table for widget chat message history.
-- The conversations table schema is unreliable (missing columns on live DB),
-- so this table provides reliable message storage keyed by session_id.

CREATE TABLE IF NOT EXISTS chat_messages (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id  UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL,
    role       TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content    TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_lookup
    ON chat_messages(tenant_id, session_id, created_at);

ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
