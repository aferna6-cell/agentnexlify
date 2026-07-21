-- 180: ops-automation foundation — pending_automations queue + activity_feed_events view
--
-- Status: DRAFT for peer review. Validated locally by applying against a scratch
--   Postgres 16 with the real prerequisite tables (see PR #517 proof). NOT yet
--   applied to prod Supabase (this session had no Supabase MCP access). A peer/owner
--   reviews, applies via mcp__supabase__apply_migration, and flips the schema-log
--   entry to APPLIED.
-- Author: fable5 (Agent Nexlify team contract) — lane team/114/fable5/ops-automation-migration
-- Issue: #114 (ops-automation foundation). Supersedes that issue's stale "migration
--   118" number — repo is at 179.
--
-- DECISIONS (delegated to fable5; contract §7 authority order = applied schema/code
-- wins over the stale spec):
--   D1 — Convention is tenant_id, NOT the spec's client_id. Every applied sibling
--        (missed_call_texts mig 111, appointments mig 005, automations mig 001) uses
--        tenant_id; the schema-discipline rule scopes client_id to leads + conversations
--        only. Using client_id here would break joins against the applied tables.
--   D2 — The appointments table (mig 005 + 007 + 15 later migrations) is ALREADY a
--        full booking table: tenant_id, customer_name/email/phone, start_time/end_time,
--        status, google_event_id, notes, an anti-double-book EXCLUDE constraint. The
--        spec's proposed client_id/start_ts/contact_* columns are renames of things that
--        already exist. No speculative ALTER — the feed reads the real existing columns.
--   D3 — activity_feed_events is a PLAIN VIEW (security_invoker), not a materialized
--        view. No backend consumer exists yet (activity_feed_service.py is unwritten),
--        so the spec's per-insert REFRESH MATERIALIZED VIEW triggers would be pure
--        write-amplification. A live view is always-fresh, has zero refresh cost, and
--        respects base-table RLS via security_invoker=true (Supabase is PG15+). Dollar
--        attribution is computed at read time by attribution_service.get_avg_ticket
--        (tenant-resolved), so there is no stored dollar column and no appointments ALTER.
--        When #115 builds the reader, swapping this view to a materialized view is a
--        one-migration change if read latency ever demands it.

-- ============================================================
-- 1. pending_automations — durable retry queue (no silent loss; spec G6)
--    Consumer: retry worker (#118) + Twilio/GCal failure enqueue paths.
--    Convention: tenant_id, mirroring missed_call_texts (mig 111).
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

-- RLS: service_role bypasses automatically; auth users see only their tenant rows.
-- Mirrors migration 111 (missed_call_texts).
ALTER TABLE pending_automations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS pending_automations_tenant_isolation ON pending_automations;
CREATE POLICY pending_automations_tenant_isolation ON pending_automations
    FOR ALL USING (tenant_id = auth.uid());

-- ============================================================
-- 2. activity_feed_events — unified activity stream (view, not materialized; D3)
--    security_invoker=true → the querying user's RLS on the base tables applies,
--    so the view needs no policy of its own. Reader filters WHERE tenant_id = ?.
-- ============================================================
CREATE OR REPLACE VIEW activity_feed_events
WITH (security_invoker = true) AS
    SELECT
        'missed_call'::text                                              AS event_type,
        mct.tenant_id                                                    AS tenant_id,
        mct.created_at                                                   AS occurred_at,
        mct.from_phone                                                   AS contact_identifier,
        ('Missed call -> text ' || COALESCE(mct.status, 'pending'))::text AS summary,
        mct.id                                                           AS source_id,
        'missed_call_texts'::text                                        AS source_table
    FROM missed_call_texts mct
    UNION ALL
    SELECT
        'appointment_booked'::text,
        appt.tenant_id,
        appt.created_at,
        appt.customer_phone,
        ('Appointment ' || to_char(appt.start_time AT TIME ZONE 'UTC', 'Mon DD HH24:MI'))::text,
        appt.id,
        'appointments'::text
    FROM appointments appt
    WHERE appt.status <> 'cancelled';
