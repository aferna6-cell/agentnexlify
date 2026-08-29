-- 195_os_tool_executions.sql
-- Agent OS action layer: the audit trail for agent tool use.
--
-- The engine (agent-service/src/agent-os/actions/) lets a department agent
-- invoke a typed tool through one central executor: resolve -> validate input
-- -> evaluate policy -> record -> gate on approval -> execute -> verify ->
-- persist. One row here per execution attempt, so the complete history of
-- everything an agent did (or was stopped from doing) is answerable from the
-- database.
--
-- Distinct from os_action_runs (migration 126): that table records the channel
-- handler fired when an owner approves a *deliverable* (send this drafted SMS).
-- This one records an agent's own *tool* choice mid-run, with a risk level, an
-- input schema, an approval gate and an independent verification result.
-- os_action_runs stays as-is; nothing is migrated off it.
--
-- client_id (NOT tenant_id) to match os_agent_runs and the rest of the os_*
-- surface (CLAUDE.md invariant #1).
--
-- RLS: deny-public (same pattern as 118+); the service role reaches it through
-- backend/services/tenant_scope.py, which forces the client_id filter.

CREATE TABLE IF NOT EXISTS os_tool_executions (
    id                  UUID PRIMARY KEY,
    client_id           UUID NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    -- The agent run that selected the tool. Nullable: an execution can also be
    -- driven straight from an approval, after its run row is long finished.
    agent_run_id        UUID NULL REFERENCES os_agent_runs (id) ON DELETE SET NULL,
    -- The engine's own run id for this turn, kept verbatim for cross-referencing
    -- the reasoning trace even when agent_run_id is null.
    engine_run_id       TEXT NULL,
    agent_id            TEXT NULL,
    tool_id             TEXT NOT NULL,
    -- 0 read-only | 1 internal mutation | 2 external communication
    -- | 3 financial, legal or destructive.
    risk_level          SMALLINT NOT NULL CHECK (risk_level BETWEEN 0 AND 3),
    mutating            BOOLEAN NOT NULL DEFAULT false,
    requires_approval   BOOLEAN NOT NULL DEFAULT false,
    approval_state      TEXT NOT NULL DEFAULT 'not_required'
        CHECK (approval_state IN ('not_required', 'pending', 'approved', 'rejected')),
    approved_by         TEXT NULL,
    approved_at         TIMESTAMPTZ NULL,
    rejected_by         TEXT NULL,
    rejected_at         TIMESTAMPTZ NULL,
    rejection_reason    TEXT NULL,
    -- Status CHECK as first applied. 'approved' on status collides with
    -- approval_state; migration 196 drops it. Do not rewrite this CHECK
    -- in place — 195 may already be applied on prod.
    status              TEXT NOT NULL DEFAULT 'pending_approval'
        CHECK (status IN (
            'pending_approval', 'approved', 'running', 'succeeded',
            'failed', 'verification_failed', 'denied', 'cancelled'
        )),
    -- Sanitized by the engine before it leaves the process: secret-looking keys
    -- are redacted and oversized payloads truncated. Never store raw credentials.
    input               JSONB NOT NULL DEFAULT '{}'::jsonb,
    result              JSONB NULL,
    error               JSONB NULL,
    -- Verification is a separate axis from status on purpose: "it ran" and "we
    -- confirmed it landed" must never be conflated.
    verification_state  TEXT NOT NULL DEFAULT 'not_applicable'
        CHECK (verification_state IN ('not_applicable', 'pending', 'passed', 'failed')),
    verification_detail TEXT NULL,
    verified_at         TIMESTAMPTZ NULL,
    -- Why policy allowed, gated or denied this execution.
    policy_reason       TEXT NOT NULL DEFAULT '',
    -- How many times the tool body actually ran (at-most-once keeps this <= 1).
    attempts            INTEGER NOT NULL DEFAULT 0,
    idempotency_key     TEXT NULL,
    -- Which port performed the side effect, and whether that port is durable.
    effect              JSONB NULL,
    started_at          TIMESTAMPTZ NULL,
    finished_at         TIMESTAMPTZ NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE os_tool_executions IS
    'Agent OS action layer: one row per agent tool execution attempt (risk level, policy decision, approval state, result, verification). Distinct from os_action_runs, which fires channel handlers on deliverable approval.';

-- The approvals queue: "what is waiting on me?" for one tenant.
CREATE INDEX IF NOT EXISTS os_tool_executions_client_status_idx
    ON os_tool_executions (client_id, status, created_at DESC);

-- Everything one turn did.
CREATE INDEX IF NOT EXISTS os_tool_executions_agent_run_idx
    ON os_tool_executions (agent_run_id);

-- Replay protection for callers that supply an idempotency key: one execution
-- per (client, tool, key). Rows without a key are unaffected.
CREATE UNIQUE INDEX IF NOT EXISTS os_tool_executions_idempotency_idx
    ON os_tool_executions (client_id, tool_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

ALTER TABLE os_tool_executions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "os_tool_executions_deny_public"
    ON os_tool_executions
    FOR ALL
    TO public
    USING (false)
    WITH CHECK (false);
