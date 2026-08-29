-- 196_os_tool_executions_status_no_approved.sql
-- Architect / CoS collision repair for Slice A.
--
-- Migration 195 created os_tool_executions with status CHECK that included
-- 'approved'. That collides with approval_state, which already has
-- not_required | pending | approved | rejected. Status is parked / running /
-- terminal only. This follow-on tightens the CHECK without rewriting 195
-- (195 may already be applied on prod). Does NOT drop the table.
--
-- Dual tables stay: os_action_runs (mig 126, deliverable channel handlers)
-- vs os_tool_executions (mig 195, agent tool attempts). Not merged.

-- Remap any mid-flight rows that used the old status='approved'.
-- Parked-but-mislabelled stays pending_approval; anything else was the
-- old "policy allowed / owner just approved" intermediate and becomes running.
UPDATE os_tool_executions
SET status = CASE
        WHEN approval_state = 'pending' THEN 'pending_approval'
        ELSE 'running'
    END,
    updated_at = now()
WHERE status = 'approved';

ALTER TABLE os_tool_executions
    DROP CONSTRAINT IF EXISTS os_tool_executions_status_check;

ALTER TABLE os_tool_executions
    ADD CONSTRAINT os_tool_executions_status_check
    CHECK (status IN (
        'pending_approval', 'running', 'succeeded',
        'failed', 'verification_failed', 'denied', 'cancelled'
    ));
