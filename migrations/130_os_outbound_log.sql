-- 130_os_outbound_log.sql
-- Group C Phase 3: cross-process replay protection for SMS / email /
-- Facebook outbound mirror.
--
-- The mirror is best-effort and runs from multiple worker processes
-- (4 Uvicorn workers in prod). Today widget is idempotent via
-- chat_messages.os_message_id (migration 129); SMS / email / Facebook
-- have no such guard, so a runner re-fire on the same os_messages row
-- can re-send the same SMS / email / FB DM to the customer.
--
-- This table is the dedup anchor. The mirror checks
-- (client_id, os_message_id, channel) before sending and inserts after
-- a successful send. Channel-scoped uniqueness lets future fan-out work
-- (e.g. simultaneous SMS + email mirror of the same OS reply) without
-- collision.
--
-- Failure semantics: best-effort. DB failure on the pre-check falls
-- through to send (we'd rather risk a rare duplicate than block the
-- customer's reply). DB failure on the post-insert is logged and
-- swallowed — the OS reply was already delivered to the customer.

CREATE TABLE IF NOT EXISTS os_outbound_log (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id           UUID NOT NULL,
    os_message_id       UUID NOT NULL REFERENCES os_messages (id) ON DELETE CASCADE,
    channel             TEXT NOT NULL,
    provider            TEXT NOT NULL,
    provider_message_id TEXT NOT NULL DEFAULT '',
    status              TEXT NOT NULL DEFAULT 'sent',
    sent_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE os_outbound_log IS
    'Agent OS Group C Phase 3: per-channel outbound dedup log. The OS '
    'outbound mirror inserts one row per successful send (SMS, email, '
    'Facebook DM). Widget uses chat_messages.os_message_id instead.';

COMMENT ON COLUMN os_outbound_log.channel IS
    'Originating thread.source — sms | email | facebook. Widget mirrors '
    'use chat_messages.os_message_id and do NOT write here.';

COMMENT ON COLUMN os_outbound_log.provider IS
    'Transport that delivered the message: twilio_byo, twilio_platform, '
    'resend, messenger.';

COMMENT ON COLUMN os_outbound_log.provider_message_id IS
    'Provider correlation id (Twilio SID, Resend id, FB message_id). '
    'Empty string when the provider returned no id.';

-- Replay-protection lookup is always (client_id, os_message_id, channel).
-- Unique constraint serves both dedup and the pre-check select.
CREATE UNIQUE INDEX IF NOT EXISTS os_outbound_log_dedup_uniq
    ON os_outbound_log (client_id, os_message_id, channel);

-- Operational queries (recent sends per tenant, last 24h failure rate).
CREATE INDEX IF NOT EXISTS os_outbound_log_client_sent_idx
    ON os_outbound_log (client_id, sent_at DESC);

ALTER TABLE os_outbound_log ENABLE ROW LEVEL SECURITY;

-- Service-role only (matches sibling os_* tables — see 119_os_messages).
CREATE POLICY "os_outbound_log_deny_public"
    ON os_outbound_log
    FOR ALL
    TO public
    USING (false)
    WITH CHECK (false);
