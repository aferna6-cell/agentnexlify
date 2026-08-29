-- 197_os_tool_executions_l2_idempotency_required.sql
-- Slice B safety: L2 / approval-gated executions must carry a replay key.
--
-- Migration 195's unique index is partial
--   (client_id, tool_id, idempotency_key) WHERE idempotency_key IS NOT NULL
-- so two keyless L2 proposals can both sit at pending_approval and later
-- double-send. This follow-on does not rewrite 195/196 and does not drop
-- the table.
--
-- Historical terminal rows (succeeded/failed/denied/cancelled) may still
-- be keyless; only parked or running L2/approval-gated rows are constrained
-- so an already-applied 195/196 with leftover audit history can still land.

UPDATE os_tool_executions
SET status = 'cancelled',
    updated_at = now()
WHERE (risk_level >= 2 OR requires_approval = true)
  AND (idempotency_key IS NULL OR btrim(idempotency_key) = '')
  AND status IN ('pending_approval', 'running');

ALTER TABLE os_tool_executions
    DROP CONSTRAINT IF EXISTS os_tool_executions_l2_idempotency_required;

ALTER TABLE os_tool_executions
    ADD CONSTRAINT os_tool_executions_l2_idempotency_required
    CHECK (
        status NOT IN ('pending_approval', 'running')
        OR NOT (risk_level >= 2 OR requires_approval)
        OR (
            idempotency_key IS NOT NULL
            AND length(btrim(idempotency_key)) > 0
        )
    );
