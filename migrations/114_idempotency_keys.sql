-- 114_idempotency_keys.sql
-- Prevent duplicate webhook processing for Stripe and Twilio redeliveries.
-- Key format: 'stripe:evt_abc123' or 'twilio:<MessageSid>'
-- TTL: 7 days recommended — no auto-delete here; schedule a cron later:
--   DELETE FROM idempotency_keys WHERE created_at < now() - INTERVAL '7 days';

CREATE TABLE IF NOT EXISTS idempotency_keys (
    key             TEXT PRIMARY KEY,          -- 'provider:event_id'
    provider        TEXT NOT NULL,             -- 'stripe' | 'twilio'
    created_at      TIMESTAMPTZ DEFAULT now(),
    response_status INT,                       -- HTTP status returned to caller
    response_body   JSONB                      -- response payload cached for replay
);

COMMENT ON TABLE idempotency_keys IS
    'Dedup store for webhook event redeliveries. TTL = 7 days (manual cron cleanup).';

-- Index for TTL cleanup queries
CREATE INDEX IF NOT EXISTS idempotency_keys_created_at_idx
    ON idempotency_keys (created_at);
