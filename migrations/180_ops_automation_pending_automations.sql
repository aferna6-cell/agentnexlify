-- 180: ops-automation — pending_automations queue (DRAFT — UNAPPLIED)
--
-- Status: DRAFT for peer review. NOT yet applied via Supabase (this session had
--   no Supabase MCP access). A peer/owner must review, then apply via
--   mcp__supabase__apply_migration and flip the schema-log entry to APPLIED.
-- Author: fable5 (Agent Nexlify team contract) — lane team/114/fable5/ops-automation-migration
-- Issue: #114 (ops-automation foundation). Supersedes that issue's stale
--   "migration 118" number — 118 was taken by 118_os_threads.sql; repo is at 179.
--
-- WHY ONLY pending_automations HERE (and not the full spec §6.2 schema):
--   The spec (specs/ops-automation-surfacing_spec.md §6.2) proposed missed_call_texts,
--   an appointments *booking* table, pending_automations, and an activity_feed_events
--   materialized view + refresh triggers. Auditing what actually shipped:
--
--     1. missed_call_texts LANDED in migration 111 — but with tenant_id (NOT the
--        spec's client_id) and a different column set (from_phone/to_phone/created_at,
--        status IN ('sent','failed','skipped')) than the spec (caller_phone/
--        call_received_at/sms_body/delivery_status).
--     2. The appointments *booking* table from the spec was NEVER created. The
--        existing appointments table (migration 005) is a reminders table with
--        tenant_id and none of the spec's booking columns (start_ts, service_type,
--        avg_ticket_amount, source, gcal_event_id, the extended status CHECK).
--     3. pending_automations was never created anywhere (confirmed absent).
--
--   Consequence: the spec's activity_feed_events materialized view reads
--   client_id, missed_call_texts.call_received_at/caller_phone/sms_body, and
--   appointments.start_ts/service_type/avg_ticket_amount — columns and a naming
--   convention that DO NOT EXIST in the applied tables. Writing that view here
--   would produce a migration that fails on apply. Per the no-half-migration
--   rule, it is DEFERRED until two decisions are made (see below).
--
-- OPEN DECISIONS for peers/owner (blocking the matview + booking table):
--   D1. Column convention: applied tables use tenant_id; the spec + issue #114
--       say client_id. This file follows the APPLIED reality (tenant_id) so the
--       queue is consistent with its siblings and the eventual view can join them.
--       If the team instead wants client_id everywhere, that is a rename migration
--       across missed_call_texts + automations + appointments FIRST, then this.
--   D2. Appointments: ALTER the migration-005 reminders table into the spec's
--       booking table, or create a new table? This gates activity_feed_events.
--
-- This table alone is safe, additive, and unblocks the retry worker (#118) and
-- the Twilio/GCal failure paths (spec §"pending_automations" enqueue points).

-- ============================================================
-- pending_automations — durable retry queue (no silent loss; spec G6)
-- Convention: tenant_id to match missed_call_texts (mig 111), automations
-- (mig 001), and appointments (mig 005). See D1 above.
-- ============================================================
CREATE TABLE IF NOT EXISTS pending_automations (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    automation_type text NOT NULL,          -- missed_call_text|appointment_sync|sms_confirm
    payload_json    jsonb NOT NULL,
    scheduled_for   timestamptz NOT NULL DEFAULT now(),
    status          text NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'processing', 'done', 'failed', 'cancelled')),
    retry_count     int NOT NULL DEFAULT 0,
    last_error      text,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

-- Drainer query shape: WHERE tenant_id=? AND status=? ORDER BY scheduled_for.
CREATE INDEX IF NOT EXISTS idx_pending_automations_tenant_status
    ON pending_automations (tenant_id, status, scheduled_for);

-- RLS: service_role bypasses automatically; auth users see only their tenant
-- rows. Mirrors migration 111 (missed_call_texts) exactly.
ALTER TABLE pending_automations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS pending_automations_tenant_isolation ON pending_automations;
CREATE POLICY pending_automations_tenant_isolation ON pending_automations
    FOR ALL USING (tenant_id = auth.uid());
