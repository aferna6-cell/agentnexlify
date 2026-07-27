-- Migration 188: durable storage for the agent graph runtime (backend/graph/).
--
-- The graph runtime (spec: specs/agent-graph-runtime_spec.md) executes cyclic
-- agent workflows as a Pregel-style superstep loop. It writes one checkpoint
-- per superstep boundary so a run can survive a process restart, and one step
-- record per node execution so every attempt is auditable and costable.
-- Without these tables the only checkpointer is in-process
-- (backend/graph/checkpoint.py::InMemoryCheckpointer), which means a Railway
-- redeploy silently drops every in-flight run — including runs parked at
-- `awaiting_input` waiting on a human.
--
-- Two tables, deliberately different shapes:
--   * graph_runs      — ONE row per run, updated in place each superstep. It is
--                       the resume point: current state, current frontier,
--                       current budget. Not a log.
--   * graph_run_steps — append-only ledger, one row per node execution
--                       (per attempt outcome). The audit trail and the cost
--                       review surface.
--
-- NAMING (deliberate): this table family uses `tenant_id`, matching the
-- `automation_*` family and `pending_automations` (migrations 186/187), which
-- is what the graph runtime scopes on. The `os_*` family (os_scheduled_tasks,
-- os_projects, os_custom_instructions) uses `client_id` instead, as do `leads`
-- and `conversations`. Both conventions are live in this schema; the graph
-- runtime follows the automation convention because it is the automation
-- layer's executor, and backend/graph/checkpoint.py carries `tenant_id` on
-- both Checkpoint and StepRecord. Do not "fix" this to client_id.
--
-- tenant_id is NULLABLE on purpose: a graph run can be platform-level
-- (nightly maintenance, internal evals, cross-tenant reporting) and not belong
-- to any one tenant. Tenant-scoped runs always carry the id.
--
-- Service-only surface: RLS enabled with an explicit always-true policy scoped
-- TO service_role, per the convention set by migration 173 (documentation plus
-- belt-and-braces against a future role misconfiguration; service_role also
-- has BYPASSRLS). Nothing reads these tables with the anon key.
--
-- Additive + idempotent. NOT YET APPLIED to any database — file only.

CREATE TABLE IF NOT EXISTS graph_runs (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id      uuid,
    graph_name     text NOT NULL,
    graph_version  text NOT NULL DEFAULT '1',
    status         text NOT NULL
        CHECK (status IN (
            'running',
            'awaiting_input',
            'completed',
            'failed',
            'budget_exhausted'
        )),
    superstep      integer NOT NULL DEFAULT 0,
    state          jsonb NOT NULL DEFAULT '{}'::jsonb,
    frontier       jsonb NOT NULL DEFAULT '[]'::jsonb,
    budget         jsonb NOT NULL DEFAULT '{}'::jsonb,
    -- Set only when status = 'awaiting_input': which node paused, why, and the
    -- results banked from its siblings so resume() re-runs only the pauser.
    interrupt      jsonb,
    error          text,
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS graph_run_steps (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id       uuid NOT NULL REFERENCES graph_runs(id) ON DELETE CASCADE,
    tenant_id    uuid,
    superstep    integer NOT NULL,
    node         text NOT NULL,
    kind         text NOT NULL DEFAULT 'task',
    status       text NOT NULL,
    attempts     integer NOT NULL DEFAULT 1,
    duration_ms  integer NOT NULL DEFAULT 0,
    tokens       integer NOT NULL DEFAULT 0,
    updates      jsonb NOT NULL DEFAULT '{}'::jsonb,
    meta         jsonb NOT NULL DEFAULT '{}'::jsonb,
    error        text,
    created_at   timestamptz NOT NULL DEFAULT now()
);

-- The resume sweeper's hot query: runs stuck in a non-terminal status, oldest
-- touch first ("what has been sitting in 'running' since before the deploy?").
CREATE INDEX IF NOT EXISTS graph_runs_status_updated_idx
    ON graph_runs (status, updated_at);

CREATE INDEX IF NOT EXISTS graph_runs_tenant_idx
    ON graph_runs (tenant_id);

-- "Show me every run of this graph at this version" — rollout + regression
-- comparison after a graph version bump.
CREATE INDEX IF NOT EXISTS graph_runs_graph_idx
    ON graph_runs (graph_name, graph_version);

-- Replaying one run in execution order; also covers the FK for cascade deletes.
CREATE INDEX IF NOT EXISTS graph_run_steps_run_superstep_idx
    ON graph_run_steps (run_id, superstep);

-- Cost review: token/duration rollups per tenant over a time window.
CREATE INDEX IF NOT EXISTS graph_run_steps_tenant_created_idx
    ON graph_run_steps (tenant_id, created_at);

ALTER TABLE graph_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph_run_steps ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS graph_runs_service_role ON public.graph_runs;

CREATE POLICY graph_runs_service_role
    ON public.graph_runs
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

DROP POLICY IF EXISTS graph_run_steps_service_role ON public.graph_run_steps;

CREATE POLICY graph_run_steps_service_role
    ON public.graph_run_steps
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Rollback (manual, commented):
-- drop policy if exists graph_run_steps_service_role on public.graph_run_steps;
-- drop policy if exists graph_runs_service_role on public.graph_runs;
-- drop table if exists graph_run_steps;
-- drop table if exists graph_runs;
