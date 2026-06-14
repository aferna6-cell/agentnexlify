-- 118_os_threads.sql
-- Agent OS P0: task-conversation threads. One row per task conversation.
-- The orchestrator opens a thread per task; messages + agent runs hang off it.
--
-- RLS: deny-public (matches migration 116). The backend uses a Supabase
-- service-role client which bypasses RLS; anon/authenticated public keys get
-- nothing. App-layer tenant scoping is enforced via client_id filters
-- (backend/services/tenant_scope.py). The deny-public policy is the backstop
-- that guarantees no cross-tenant leak through public keys.

CREATE TABLE IF NOT EXISTS os_threads (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id   UUID NOT NULL,
    title       TEXT NOT NULL DEFAULT 'New conversation',
    created_by  TEXT,
    status      TEXT NOT NULL DEFAULT 'active',   -- active | archived
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE os_threads IS
    'Agent OS task-conversation threads (P0). One row per task conversation.';

CREATE INDEX IF NOT EXISTS os_threads_client_status_idx
    ON os_threads (client_id, status);

ALTER TABLE os_threads ENABLE ROW LEVEL SECURITY;

CREATE POLICY "os_threads_deny_public"
    ON os_threads
    FOR ALL
    TO public
    USING (false)
    WITH CHECK (false);
