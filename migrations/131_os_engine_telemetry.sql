-- 131_os_engine_telemetry.sql
-- Agent OS engine telemetry: persist the parts of an orchestration run record
-- that the os_agent_runs row does NOT capture, so /admin/routing and
-- /admin/costs have a ledger.
--
-- The agent-service engine returns a RunRecordBundle per turn
-- (backend/services/agent_os_bridge.py). os_agent_runs already stores the run +
-- approval-gated deliverable. These two tables store the rest:
--   os_routing_decision  -> every routing decision (the fine-tuning + routing-
--                           accuracy dataset; one+ per turn).
--   os_model_call_log    -> every model call with token + cost (cost ledger;
--                           offline composer + failed calls included, cost 0).
--
-- Both are client_id-scoped (consistent with every other os_* table) and
-- best-effort writes: a failure here never breaks the owner's turn. run_id is a
-- plain nullable UUID (no FK) — it references the persisted os_agent_runs.id
-- when a run was created, else null for answer/decline turns.
--
-- RLS: deny-public (see migration 118 rationale). Service-role client only.

CREATE TABLE IF NOT EXISTS os_routing_decision (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id     UUID NOT NULL,
    run_id        UUID,                     -- os_agent_runs.id when a run fired
    ask           TEXT NOT NULL,
    classifier    TEXT NOT NULL,            -- haiku | heuristic
    decision      TEXT NOT NULL,            -- routed|ambiguous|wishlist_fallback|owner_override|direct_answer|declined
    chosen_agent  TEXT NOT NULL DEFAULT '',
    confidence    DOUBLE PRECISION NOT NULL DEFAULT 0,
    alternates    JSONB,                    -- ranked candidate list
    accepted      BOOLEAN,                  -- set false when the owner re-routed
    changed_to    TEXT,                     -- agent the owner re-routed to
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE os_routing_decision IS
    'Agent OS engine: one row per routing decision. Powers /admin/routing '
    '(routing accuracy) and the routing fine-tuning dataset.';

CREATE INDEX IF NOT EXISTS os_routing_decision_client_created_idx
    ON os_routing_decision (client_id, created_at DESC);

ALTER TABLE os_routing_decision ENABLE ROW LEVEL SECURITY;

CREATE POLICY "os_routing_decision_deny_public"
    ON os_routing_decision
    FOR ALL
    TO public
    USING (false)
    WITH CHECK (false);


CREATE TABLE IF NOT EXISTS os_model_call_log (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id      UUID NOT NULL,
    run_id         UUID,                    -- os_agent_runs.id when a run fired
    purpose        TEXT NOT NULL,           -- routing | draft | other
    model          TEXT NOT NULL,           -- claude-* or local-composer / down marker
    input_tokens   INTEGER NOT NULL DEFAULT 0,
    output_tokens  INTEGER NOT NULL DEFAULT 0,
    cost_usd       DOUBLE PRECISION NOT NULL DEFAULT 0,
    ok             BOOLEAN NOT NULL DEFAULT true,
    error          TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE os_model_call_log IS
    'Agent OS engine: one row per model call (real + offline composer). '
    'Powers /admin/costs. Offline / failed calls are logged with cost 0 so '
    'cost-per-run is always recorded.';

CREATE INDEX IF NOT EXISTS os_model_call_log_client_created_idx
    ON os_model_call_log (client_id, created_at DESC);

ALTER TABLE os_model_call_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "os_model_call_log_deny_public"
    ON os_model_call_log
    FOR ALL
    TO public
    USING (false)
    WITH CHECK (false);
