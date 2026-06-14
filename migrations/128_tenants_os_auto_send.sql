-- 128_tenants_os_auto_send.sql
-- Per-tenant auto-send toggle for Agent OS deliverables.
--
-- Default FALSE: every worker deliverable lands as `pending_approval`,
-- waiting for the owner to approve or reject. When TRUE: worker
-- deliverables are marked `approved` directly at the moment the worker
-- succeeds, skipping the owner review gate. Action-handler firing is
-- decided by the existing os_agent_runs.action_type wiring (migration
-- 126); this flag only controls the approval gate.
--
-- Risk: a stale prompt + a wired action handler + auto_send=TRUE means
-- a customer-facing action fires with zero human review. Default OFF;
-- owner-gated toggle in the dashboard Settings page.

ALTER TABLE tenants
    ADD COLUMN IF NOT EXISTS os_auto_send_enabled BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN tenants.os_auto_send_enabled IS
    'When TRUE, Agent OS worker deliverables are auto-approved (no owner review). Default FALSE (every deliverable waits for approval).';
