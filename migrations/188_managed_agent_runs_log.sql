-- Migration 188: managed_agent_runs run log (Phase 0, plans/managed-agents-rollout_plan.md)
--
-- Persists one row per Managed Agent run so Phase 0 can measure cost/run,
-- duration, and failure rate before any external tenant is enabled. Written
-- fail-open by backend/services/managed_agent_run_log.py::record_run — a
-- missing table degrades to "no run logged", never a 500 on the run path.
--
-- status values:
--   success     — run completed and a response was returned to the caller
--   error       — run started but failed terminally (reserved; wired later)
--   unavailable — agent not provisioned; structured 503 stub returned
--
-- tokens_in / tokens_out default 0 — the synchronous transcript path does
-- not surface usage yet; Phase 0 wiring records duration + outcome and the
-- token columns fill in when usage plumbing lands.
--
-- RLS: service-only table. Explicit always-true policy scoped TO service_role
-- per the convention set by migration 173 and restated by migration 187.
--
-- Idempotent: CREATE IF NOT EXISTS + DROP POLICY IF EXISTS.

CREATE TABLE IF NOT EXISTS public.managed_agent_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    agent_key text NOT NULL,
    status text NOT NULL CHECK (status IN ('success', 'error', 'unavailable')),
    tokens_in integer NOT NULL DEFAULT 0,
    tokens_out integer NOT NULL DEFAULT 0,
    duration_ms integer NOT NULL DEFAULT 0,
    request_summary text NOT NULL DEFAULT '',
    error text,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Hot queries: per-tenant run history + per-agent trend review (Phase 0 exit
-- criteria: cost/run measured and logged; weekly eval trend in Phase 2).
CREATE INDEX IF NOT EXISTS idx_managed_agent_runs_tenant_created
    ON public.managed_agent_runs (tenant_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_managed_agent_runs_agent_created
    ON public.managed_agent_runs (agent_key, created_at DESC);

ALTER TABLE public.managed_agent_runs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS managed_agent_runs_service_role ON public.managed_agent_runs;

CREATE POLICY managed_agent_runs_service_role
    ON public.managed_agent_runs
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Rollback (manual, commented):
-- DROP POLICY IF EXISTS managed_agent_runs_service_role ON public.managed_agent_runs;
-- DROP TABLE IF EXISTS public.managed_agent_runs;
