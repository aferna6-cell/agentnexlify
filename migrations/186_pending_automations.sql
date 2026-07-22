-- 186_pending_automations.sql
-- Ops-automation retry queue (#118, with enqueuers #117 missed_call_gate /
-- #119 booking_gcal). The enqueue side shipped writing to this table fail-open,
-- but no migration ever created it (the sibling code comment citing "migration
-- 180" is wrong; 180 is os_scheduled_tasks). This closes that gap so the retry
-- drainer (backend/services/retry_worker.py) has a real table to drain.
--
-- Column names match the shipped enqueuers: tenant_id-scoped, retry counter is
-- `attempts`. Additive + idempotent. NOT auto-applied — apply via Supabase.

CREATE TABLE IF NOT EXISTS pending_automations (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        uuid NOT NULL,
    automation_type  text NOT NULL,
    payload          jsonb NOT NULL DEFAULT '{}'::jsonb,
    status           text NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'done', 'failed')),
    attempts         integer NOT NULL DEFAULT 0,
    scheduled_for    timestamptz NOT NULL DEFAULT now(),
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now()
);

-- The drainer's hot query: due pending rows, oldest first.
CREATE INDEX IF NOT EXISTS pending_automations_due_idx
    ON pending_automations (status, scheduled_for);

CREATE INDEX IF NOT EXISTS pending_automations_tenant_idx
    ON pending_automations (tenant_id);

ALTER TABLE pending_automations ENABLE ROW LEVEL SECURITY;

-- Rollback (manual, commented):
-- drop table if exists pending_automations;
