-- Migration 180: recurring Agent OS tasks (suite item 1 — autonomous agents).
--
-- "Your AI workforce shows up on Monday": owner-defined recurring prompts
-- that run through the normal engine turn path (thread + approvals + outbound
-- guard) on a simple every-N-days cadence. client_id scope — os_* family.

CREATE TABLE IF NOT EXISTS os_scheduled_tasks (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id      uuid NOT NULL,
    department     text NOT NULL,
    prompt         text NOT NULL,
    interval_days  integer NOT NULL DEFAULT 7,
    enabled        boolean NOT NULL DEFAULT true,
    next_run_at    timestamptz NOT NULL DEFAULT now(),
    last_run_at    timestamptz,
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS os_scheduled_tasks_due_idx
    ON os_scheduled_tasks (enabled, next_run_at);
CREATE INDEX IF NOT EXISTS os_scheduled_tasks_client_idx
    ON os_scheduled_tasks (client_id);

ALTER TABLE os_scheduled_tasks ENABLE ROW LEVEL SECURITY;
