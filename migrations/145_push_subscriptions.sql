-- Migration 145: push_subscriptions — Web Push subscriptions for pending-approval alerts
--
-- Free browser-push leg of os_approval_notify (email + SMS already exist).
-- One row per browser subscription. endpoint is globally unique per the
-- Push API spec; keys holds the p256dh/auth pair returned by
-- PushSubscription.toJSON().
--
-- Uses tenant_id (appointments-style) — this is a new OS-adjacent table,
-- NOT leads/conversations (those use client_id).

CREATE TABLE IF NOT EXISTS push_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    endpoint TEXT NOT NULL UNIQUE,
    keys JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_push_subscriptions_tenant_id
    ON push_subscriptions (tenant_id);

-- Service-role-only access (backend uses service key; no anon/authenticated
-- access path exists for this table).
ALTER TABLE push_subscriptions ENABLE ROW LEVEL SECURITY;
