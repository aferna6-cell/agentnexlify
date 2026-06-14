-- 146_conversation_email_notify.sql
-- Per-tenant "email me the full transcript when a widget conversation wraps up".
-- Opt-in (default OFF). A scheduled idle-sweep (notify_idle_conversations) emails
-- the configured address once per conversation, stamping conversations.notified_at
-- so each conversation is sent exactly once.

ALTER TABLE tenants
    ADD COLUMN IF NOT EXISTS conversation_email_notify_enabled BOOLEAN NOT NULL DEFAULT FALSE;

-- Where transcript notifications are sent. Falls back to owner_email when null
-- (only relevant while enabled). Kept separate so a tenant can route alerts to a
-- shared front-desk inbox distinct from their account email.
ALTER TABLE tenants
    ADD COLUMN IF NOT EXISTS conversation_notify_email TEXT;

-- Stamped when the wrap-up email is sent; guarantees one email per conversation.
ALTER TABLE conversations
    ADD COLUMN IF NOT EXISTS notified_at TIMESTAMPTZ;

-- The sweep scans only un-notified conversations per tenant.
CREATE INDEX IF NOT EXISTS idx_conversations_unnotified
    ON conversations (client_id)
    WHERE notified_at IS NULL;
