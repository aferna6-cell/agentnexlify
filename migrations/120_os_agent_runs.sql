-- 120_os_agent_runs.sql
-- Agent OS P0: one row per delegated worker-agent invocation. Async — the
-- worker writes status + deliverable back here when it finishes.
-- thought_process drives the agent-run flowchart in the UI.
-- deliverable holds an approval-gated draft (addressed by run_id via the
-- /deliverables endpoints) — no separate deliverables table in P0.
--
-- RLS: deny-public (see 118 rationale).

CREATE TABLE IF NOT EXISTS os_agent_runs (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id            UUID NOT NULL,
    thread_id            UUID NOT NULL REFERENCES os_threads (id) ON DELETE CASCADE,
    agent_name           TEXT NOT NULL,
    status               TEXT NOT NULL DEFAULT 'queued',  -- queued|running|succeeded|failed
    thought_process      JSONB NOT NULL DEFAULT '[]'::jsonb,
    deliverable          JSONB,                            -- approval-gated draft, nullable
    deliverable_status   TEXT,                             -- pending_approval|approved|rejected
    error_detail         TEXT,
    bug_reported_at      TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at         TIMESTAMPTZ
);

COMMENT ON TABLE os_agent_runs IS
    'Agent OS worker-agent runs (P0). Async status + approval-gated deliverable.';

CREATE INDEX IF NOT EXISTS os_agent_runs_client_status_idx
    ON os_agent_runs (client_id, status);

ALTER TABLE os_agent_runs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "os_agent_runs_deny_public"
    ON os_agent_runs
    FOR ALL
    TO public
    USING (false)
    WITH CHECK (false);
