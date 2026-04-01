-- Migration 073: Email Sequences
-- Dedicated email/SMS drip sequence tables separate from the older
-- automation_sequences system. Supports lead_captured, tag_added,
-- and manual trigger types with per-step delay (days + hours).

-- ============================================================
-- 1. email_sequences — sequence definitions
-- ============================================================
CREATE TABLE IF NOT EXISTS email_sequences (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id      UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name           TEXT NOT NULL,
    trigger_type   TEXT NOT NULL DEFAULT 'lead_captured',
    -- 'lead_captured', 'tag_added', 'manual'
    trigger_config JSONB DEFAULT '{}',
    is_active      BOOLEAN DEFAULT true,
    created_at     TIMESTAMPTZ DEFAULT now(),
    updated_at     TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 2. email_sequence_steps — individual steps in a sequence
-- ============================================================
CREATE TABLE IF NOT EXISTS email_sequence_steps (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sequence_id  UUID NOT NULL REFERENCES email_sequences(id) ON DELETE CASCADE,
    step_order   INT NOT NULL,
    delay_days   INT NOT NULL DEFAULT 0,
    delay_hours  INT NOT NULL DEFAULT 0,
    subject      TEXT NOT NULL,
    body         TEXT NOT NULL,
    email_type   TEXT NOT NULL DEFAULT 'email',
    -- 'email' or 'sms'
    is_active    BOOLEAN DEFAULT true,
    created_at   TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 3. email_sequence_enrollments — lead enrollment tracking
-- ============================================================
CREATE TABLE IF NOT EXISTS email_sequence_enrollments (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sequence_id  UUID NOT NULL REFERENCES email_sequences(id) ON DELETE CASCADE,
    lead_id      UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    tenant_id    UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    status       TEXT NOT NULL DEFAULT 'active',
    -- 'active', 'completed', 'cancelled', 'paused'
    current_step INT NOT NULL DEFAULT 0,
    enrolled_at  TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ NULL,
    created_at   TIMESTAMPTZ DEFAULT now(),
    UNIQUE (sequence_id, lead_id)
);

-- ============================================================
-- 4. email_sequence_sends — individual send records
-- ============================================================
CREATE TABLE IF NOT EXISTS email_sequence_sends (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enrollment_id  UUID NOT NULL REFERENCES email_sequence_enrollments(id) ON DELETE CASCADE,
    step_id        UUID NOT NULL REFERENCES email_sequence_steps(id) ON DELETE CASCADE,
    lead_id        UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    tenant_id      UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    status         TEXT NOT NULL DEFAULT 'pending',
    -- 'pending', 'sent', 'failed', 'skipped'
    scheduled_for  TIMESTAMPTZ NOT NULL,
    sent_at        TIMESTAMPTZ NULL,
    error          TEXT NULL,
    created_at     TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- Indexes
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_email_sequences_tenant
    ON email_sequences(tenant_id);

CREATE INDEX IF NOT EXISTS idx_email_sequence_steps_seq
    ON email_sequence_steps(sequence_id);

CREATE INDEX IF NOT EXISTS idx_email_seq_enrollments_tenant_status
    ON email_sequence_enrollments(tenant_id, status);

CREATE INDEX IF NOT EXISTS idx_email_seq_sends_tenant_status_sched
    ON email_sequence_sends(tenant_id, status, scheduled_for);

CREATE INDEX IF NOT EXISTS idx_email_seq_sends_enrollment
    ON email_sequence_sends(enrollment_id);

-- ============================================================
-- Row Level Security
-- ============================================================
ALTER TABLE email_sequences            ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_sequence_steps       ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_sequence_enrollments ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_sequence_sends       ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on email_sequences"
    ON email_sequences
    FOR ALL
    USING (current_setting('role', true) = 'service_role');

CREATE POLICY "Service role full access on email_sequence_steps"
    ON email_sequence_steps
    FOR ALL
    USING (current_setting('role', true) = 'service_role');

CREATE POLICY "Service role full access on email_sequence_enrollments"
    ON email_sequence_enrollments
    FOR ALL
    USING (current_setting('role', true) = 'service_role');

CREATE POLICY "Service role full access on email_sequence_sends"
    ON email_sequence_sends
    FOR ALL
    USING (current_setting('role', true) = 'service_role');
