-- 133_os_action_outcomes.sql
-- Agent OS learning loop (north-star gap #2): action -> outcome -> memory.
--
-- After a lead-targeting action succeeds (email.send / sms.send /
-- calendar.event.create), os_learning.record_action_outcome_pending resolves
-- the recipient to a lead and writes one *pending* row here. A scheduled tick
-- (resolve_all_due_outcomes, hourly) settles each row once settle_by elapses,
-- computing a deterministic outcome (booked > converted > no_response) and
-- writing it back to os_memory_entries (kind='outcome') so the orchestrator's
-- search_memory recalls it.
--
-- Capture is lead-targeting only: broadcast actions never produce a row
-- (no recipient -> lead join, no insert).
--
-- Idempotency: one outcome per action_run_id (UNIQUE). The memory write is
-- separately deduped by source_ref='outcome:<action_run_id>'.
--
-- RLS: deny-public (same pattern as 126+). Tenant scope column is client_id,
-- registered in backend/services/tenant_scope.py.

CREATE TABLE IF NOT EXISTS os_action_outcomes (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id            UUID NOT NULL,
    action_run_id        UUID NOT NULL REFERENCES os_action_runs (id) ON DELETE CASCADE,
    action_type          TEXT NOT NULL,
    lead_id              UUID REFERENCES leads (id) ON DELETE SET NULL,
    recipient            TEXT,
    lead_status_at_send  TEXT,
    sent_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    settle_by            TIMESTAMPTZ NOT NULL,
    status               TEXT NOT NULL DEFAULT 'pending',  -- pending|resolved
    outcome              TEXT,                             -- booked|converted|no_response
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at          TIMESTAMPTZ
);

COMMENT ON TABLE os_action_outcomes IS
    'Agent OS learning loop: one pending row per succeeded lead-targeting action, settled deterministically after settle_by into an outcome + memory entry.';

-- One outcome per action run — replay/duplicate capture protection.
CREATE UNIQUE INDEX IF NOT EXISTS os_action_outcomes_action_run_unique_idx
    ON os_action_outcomes (action_run_id);

-- Scheduler sweep: pending rows past their settle window.
CREATE INDEX IF NOT EXISTS os_action_outcomes_due_idx
    ON os_action_outcomes (status, settle_by);

CREATE INDEX IF NOT EXISTS os_action_outcomes_client_idx
    ON os_action_outcomes (client_id, status);

ALTER TABLE os_action_outcomes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "os_action_outcomes_deny_public"
    ON os_action_outcomes
    FOR ALL
    TO public
    USING (false)
    WITH CHECK (false);
