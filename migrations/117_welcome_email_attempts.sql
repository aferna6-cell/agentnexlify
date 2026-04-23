-- 117: welcome_email_attempts table — tracks drip onboarding email schedule
-- Applied: 2026-04-23

CREATE TABLE IF NOT EXISTS welcome_email_attempts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    attempt_number      INT NOT NULL CHECK (attempt_number BETWEEN 1 AND 4),
    scheduled_for       TIMESTAMPTZ NOT NULL,
    sent_at             TIMESTAMPTZ,
    status              TEXT NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending', 'sent', 'failed', 'skipped')),
    error_message       TEXT,
    resend_message_id   TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_welcome_email_tenant_attempt
    ON welcome_email_attempts (tenant_id, attempt_number);

CREATE INDEX idx_welcome_email_pending
    ON welcome_email_attempts (status, scheduled_for)
    WHERE status = 'pending';

ALTER TABLE welcome_email_attempts ENABLE ROW LEVEL SECURITY;

CREATE POLICY welcome_email_service ON welcome_email_attempts
    FOR ALL TO service_role USING (true) WITH CHECK (true);
