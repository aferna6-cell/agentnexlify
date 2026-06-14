-- 119_os_messages.sql
-- Agent OS P0: messages within a thread. Carries client_id for RLS + direct
-- scoping (every new OS table is client_id-scoped per spec).
-- agent_run_id links an assistant/agent message to the run that produced it.
--
-- RLS: deny-public (see 118 rationale).

CREATE TABLE IF NOT EXISTS os_messages (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id     UUID NOT NULL,
    thread_id     UUID NOT NULL REFERENCES os_threads (id) ON DELETE CASCADE,
    role          TEXT NOT NULL,                  -- user | assistant | agent | system
    content       TEXT NOT NULL,
    agent_run_id  UUID,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE os_messages IS
    'Agent OS thread messages (P0). agent_run_id links to os_agent_runs.';

CREATE INDEX IF NOT EXISTS os_messages_thread_idx
    ON os_messages (thread_id, created_at);

ALTER TABLE os_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "os_messages_deny_public"
    ON os_messages
    FOR ALL
    TO public
    USING (false)
    WITH CHECK (false);
