-- 133: Phase 4 — pending_automations durable retry queue
-- Drained by backend/services/retry_worker.py on the 60s automation tick.
-- Exponential backoff 30s/2min/10min, max 3 attempts; stuck rows
-- (status='failed' or pending >1h) surface via GET /automations/{tenant_id}/pending.
--
-- Uses tenant_id (matching sibling missed_call_texts, migration 111) — NOT client_id.

CREATE TABLE IF NOT EXISTS pending_automations (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    automation_type text NOT NULL,
    payload_json    jsonb NOT NULL DEFAULT '{}'::jsonb,
    status          text NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending', 'processing', 'done', 'failed')),
    retry_count     integer NOT NULL DEFAULT 0,
    scheduled_for   timestamptz NOT NULL DEFAULT now(),
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

-- RLS: service_role bypasses automatically; auth users see only their tenant rows
ALTER TABLE pending_automations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS pending_automations_tenant_isolation ON pending_automations;
CREATE POLICY pending_automations_tenant_isolation ON pending_automations
    FOR ALL USING (tenant_id = auth.uid());

-- Drain query: WHERE status='pending' AND scheduled_for <= now() ORDER BY scheduled_for
CREATE INDEX IF NOT EXISTS idx_pending_automations_due
    ON pending_automations (status, scheduled_for);

-- /pending endpoint: stuck rows per tenant
CREATE INDEX IF NOT EXISTS idx_pending_automations_tenant_status
    ON pending_automations (tenant_id, status, created_at DESC);
