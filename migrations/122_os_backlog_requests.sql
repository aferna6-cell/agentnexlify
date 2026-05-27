-- 122_os_backlog_requests.sql
-- Agent OS P0: no-fit backlog. When the orchestrator decides a request can't be
-- served by any current worker agent, it parks the request here for an owner
-- decision (build it / drop it / defer).
--
-- RLS: deny-public (see 118 rationale).

CREATE TABLE IF NOT EXISTS os_backlog_requests (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id     UUID NOT NULL,
    thread_id     UUID REFERENCES os_threads (id) ON DELETE SET NULL,
    summary       TEXT NOT NULL,
    detail        TEXT,
    reason        TEXT,                            -- why no current agent fits
    status        TEXT NOT NULL DEFAULT 'open',    -- open|accepted|declined|deferred
    decided_by    TEXT,
    decision_note TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_at    TIMESTAMPTZ
);

COMMENT ON TABLE os_backlog_requests IS
    'Agent OS no-fit backlog (P0). Requests no current worker agent can serve.';

CREATE INDEX IF NOT EXISTS os_backlog_requests_client_status_idx
    ON os_backlog_requests (client_id, status);

ALTER TABLE os_backlog_requests ENABLE ROW LEVEL SECURITY;

CREATE POLICY "os_backlog_requests_deny_public"
    ON os_backlog_requests
    FOR ALL
    TO public
    USING (false)
    WITH CHECK (false);
