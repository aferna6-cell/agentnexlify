-- 123_os_tenant_usage.sql
-- Agent OS P0: per-tenant usage metering. One row per client per billing cycle.
-- The usage_meter service increments counters as agent runs complete; the
-- /usage endpoint reads the current cycle row.
--
-- RLS: deny-public (see 118 rationale).

CREATE TABLE IF NOT EXISTS os_tenant_usage (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id      UUID NOT NULL,
    cycle_start    DATE NOT NULL,
    agent_runs     INTEGER NOT NULL DEFAULT 0,
    messages       INTEGER NOT NULL DEFAULT 0,
    input_tokens   BIGINT NOT NULL DEFAULT 0,
    output_tokens  BIGINT NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (client_id, cycle_start)
);

COMMENT ON TABLE os_tenant_usage IS
    'Agent OS per-tenant usage metering (P0). One row per client per cycle.';

CREATE INDEX IF NOT EXISTS os_tenant_usage_client_idx
    ON os_tenant_usage (client_id, cycle_start DESC);

ALTER TABLE os_tenant_usage ENABLE ROW LEVEL SECURITY;

CREATE POLICY "os_tenant_usage_deny_public"
    ON os_tenant_usage
    FOR ALL
    TO public
    USING (false)
    WITH CHECK (false);
