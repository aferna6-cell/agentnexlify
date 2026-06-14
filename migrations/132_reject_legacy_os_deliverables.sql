-- 132 — Auto-reject legacy v1-shape Agent OS deliverables.
--
-- The v2 engine (agent-service) writes deliverables with `channel` + `metadata`.
-- The legacy in-process workers wrote `{title, format: "markdown", body}` with no
-- `channel`. The redesigned dashboard only renders the v2 shape, so pre-cutover
-- v1 drafts sit in the pending list forever with no Review path. Reject them once
-- so owners see a clean v2-only approval queue.
--
-- Discriminator: pending row whose deliverable has `format` and lacks `channel`.
-- Idempotent (re-running rejects nothing new). Non-destructive: the deliverable
-- body stays on the row; only deliverable_status flips pending_approval→rejected.

UPDATE os_agent_runs
SET deliverable_status = 'rejected',
    updated_at = now()
WHERE deliverable_status = 'pending_approval'
  AND deliverable ? 'format'
  AND NOT (deliverable ? 'channel');
