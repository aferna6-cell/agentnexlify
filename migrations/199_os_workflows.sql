-- 199_os_workflows.sql
-- M9.2 Persistent Planner: durable Workflow + WorkflowStep tables.
--
-- M9.1 shipped the typed contract only (backend/services/os_workflows/contract.py).
-- This migration persists those records. The planner still never executes tools;
-- steps hold tool_intent JSON and optional execution_id into os_tool_executions
-- after the existing Action Executor runs.
--
-- client_id (NOT tenant_id) — matches the os_* family (CLAUDE.md invariant #1).
-- RLS: deny-public; service role reaches rows via tenant_scope.py.

CREATE TABLE IF NOT EXISTS os_workflows (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id       UUID NOT NULL,
    owner_goal      TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'planned'
        CHECK (status IN (
            'planned', 'running', 'paused', 'succeeded', 'failed', 'cancelled'
        )),
    row_version     INTEGER NOT NULL DEFAULT 1 CHECK (row_version >= 1),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE os_workflows IS
    'M9 persistent planner: one durable multi-step owner goal. Planner writes state; Action Executor runs steps.';

CREATE INDEX IF NOT EXISTS os_workflows_client_id_idx
    ON os_workflows (client_id);
CREATE INDEX IF NOT EXISTS os_workflows_client_status_idx
    ON os_workflows (client_id, status);

CREATE TABLE IF NOT EXISTS os_workflow_steps (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id          UUID NOT NULL REFERENCES os_workflows (id) ON DELETE CASCADE,
    client_id            UUID NOT NULL,
    ordinal              INTEGER NOT NULL CHECK (ordinal >= 0),
    description          TEXT NOT NULL,
    dependencies         UUID[] NOT NULL DEFAULT '{}',
    department           TEXT,
    tool_intent          JSONB,
    state                TEXT NOT NULL DEFAULT 'planned'
        CHECK (state IN (
            'planned', 'ready', 'pending_approval', 'running', 'verifying',
            'succeeded', 'failed', 'unknown', 'blocked', 'cancelled'
        )),
    risk_level           SMALLINT NOT NULL DEFAULT 1
        CHECK (risk_level BETWEEN 0 AND 3),
    execution_id         UUID,
    verification_state   TEXT
        CHECK (
            verification_state IS NULL OR verification_state IN (
                'not_required', 'pending', 'passed', 'failed', 'unknown'
            )
        ),
    error                TEXT,
    retry_count          INTEGER NOT NULL DEFAULT 0 CHECK (retry_count >= 0),
    max_retries          INTEGER NOT NULL DEFAULT 2 CHECK (max_retries >= 0),
    row_version          INTEGER NOT NULL DEFAULT 1 CHECK (row_version >= 1),
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE os_workflow_steps IS
    'M9 persistent planner steps. tool_intent is declared intent only; execution_id links to os_tool_executions after Action Executor.';

-- Optional FK to action audit trail (nullable; SET NULL if execution row removed).
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'os_tool_executions'
    ) THEN
        ALTER TABLE os_workflow_steps
            DROP CONSTRAINT IF EXISTS os_workflow_steps_execution_id_fkey;
        ALTER TABLE os_workflow_steps
            ADD CONSTRAINT os_workflow_steps_execution_id_fkey
            FOREIGN KEY (execution_id)
            REFERENCES os_tool_executions (id)
            ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS os_workflow_steps_workflow_id_idx
    ON os_workflow_steps (workflow_id);
CREATE INDEX IF NOT EXISTS os_workflow_steps_client_state_idx
    ON os_workflow_steps (client_id, state);
CREATE INDEX IF NOT EXISTS os_workflow_steps_workflow_state_idx
    ON os_workflow_steps (workflow_id, state);

ALTER TABLE os_workflows ENABLE ROW LEVEL SECURITY;
ALTER TABLE os_workflow_steps ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "os_workflows_deny_public" ON os_workflows;
CREATE POLICY "os_workflows_deny_public"
    ON os_workflows
    FOR ALL
    TO public
    USING (false)
    WITH CHECK (false);

DROP POLICY IF EXISTS "os_workflow_steps_deny_public" ON os_workflow_steps;
CREATE POLICY "os_workflow_steps_deny_public"
    ON os_workflow_steps
    FOR ALL
    TO public
    USING (false)
    WITH CHECK (false);
