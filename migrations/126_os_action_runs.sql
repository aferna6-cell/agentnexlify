-- 126_os_action_runs.sql
-- Agent OS Group B foundation: action-handler runs.
--
-- Workers produce approval-gated deliverables on os_agent_runs. When the
-- owner approves and the deliverable is wired to an action handler, the
-- handler executes via BackgroundTasks and writes its outcome here. One
-- os_action_runs row per attempt; retries re-use deliverable_id with a new
-- attempt.
--
-- Idempotency: a deliverable can spawn at most one *succeeded* action of a
-- given action_type. Replay protection is enforced by a partial unique
-- index on (deliverable_id, action_type) WHERE status = 'succeeded'.
--
-- RLS: deny-public (same pattern as 118+).

CREATE TABLE IF NOT EXISTS os_action_runs (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id         UUID NOT NULL,
    deliverable_id    UUID NOT NULL REFERENCES os_agent_runs (id) ON DELETE CASCADE,
    action_type       TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'queued',  -- queued|running|succeeded|failed
    request_payload   JSONB NOT NULL DEFAULT '{}'::jsonb,
    response_payload  JSONB,
    error_detail      JSONB,
    started_at        TIMESTAMPTZ,
    finished_at       TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE os_action_runs IS
    'Agent OS action-handler runs (Group B). One row per attempt; partial unique on (deliverable_id, action_type) WHERE succeeded.';

CREATE INDEX IF NOT EXISTS os_action_runs_client_status_idx
    ON os_action_runs (client_id, status);

CREATE INDEX IF NOT EXISTS os_action_runs_deliverable_idx
    ON os_action_runs (deliverable_id);

-- Replay protection: at most one succeeded run per (deliverable_id, action_type).
-- Failed/queued/running rows are exempt so retries can re-attempt.
CREATE UNIQUE INDEX IF NOT EXISTS os_action_runs_succeeded_unique_idx
    ON os_action_runs (deliverable_id, action_type)
    WHERE status = 'succeeded';

ALTER TABLE os_action_runs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "os_action_runs_deny_public"
    ON os_action_runs
    FOR ALL
    TO public
    USING (false)
    WITH CHECK (false);

-- Link the deliverable to the action_type it should fire on approve, and to
-- the latest run (for UI status). Both nullable: deliverables without an
-- action_type are display-only (e.g. customer_question summaries).
ALTER TABLE os_agent_runs
    ADD COLUMN IF NOT EXISTS action_type TEXT NULL;

ALTER TABLE os_agent_runs
    ADD COLUMN IF NOT EXISTS action_run_id UUID NULL
        REFERENCES os_action_runs (id) ON DELETE SET NULL;
