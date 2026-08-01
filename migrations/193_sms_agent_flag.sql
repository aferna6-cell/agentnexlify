-- 193_sms_agent_flag.sql
--
-- Phase 3 (plans/nexlify-capabilities-roadmap_plan.md) — multi-turn SMS
-- conversation agent. Per-tenant opt-in: default false preserves the
-- existing behavior of POST /api/v1/twilio/sms-reply (410 Gone, tenants
-- must migrate inbound SMS to /api/v1/os/inbound/sms). When a tenant flips
-- this on, backend/services/sms_agent.py answers inbound SMS replies with
-- a multi-turn AI conversation — reusing the widget chat pipeline's KB
-- grounding + system-prompt builder — instead of the 410.
--
-- No new conversations/leads columns needed for this lane:
--   - conversations.channel (migration 057) already discriminates 'sms'
--     vs 'widget'.
--   - backend/routers/sms.py already established the 'sms_<digits>'
--     session_id convention this feature reuses for session mapping.

ALTER TABLE tenants ADD COLUMN IF NOT EXISTS sms_agent_enabled BOOLEAN NOT NULL DEFAULT false;
