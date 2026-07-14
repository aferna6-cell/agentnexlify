-- 165_appointment_reminders.sql
--
-- Phase 1 of "AI appointment reminders + smart rebooking": automated SMS
-- reminders before booked appointments, to cut no-shows. Reminders are
-- scheduled at booking time (24h + 2h before start_time) and sent by a
-- polling job (POST /api/v1/appointments/reminders/run). One row per
-- (appointment_id, reminder_type) — the unique constraint below makes
-- scheduling idempotent: re-calling schedule_reminders_for_appointment for
-- the same appointment (e.g. a retry) can't create duplicate reminder rows
-- for a window already scheduled.
--
-- appointments.tenant_id (NOT client_id — appointments differ from
-- leads/conversations, which use client_id). See schema-discipline.md.
--
-- status flow:
--   pending -> sending (claimed right before the SMS send) -> sent | failed
--   pending -> skipped (no phone on file / appointment cancelled / recipient
--              opted out via sms_compliance / tenant disabled reminders)
-- The pending -> sending -> terminal claim dance lets the 4 Uvicorn workers
-- that all poll this table via the same cron call avoid double-sending the
-- same reminder (same idiom as
-- backend/services/automation/scheduled/billing_jobs.py's
-- process_recurring_invoices claim-before-insert pattern).

CREATE TABLE IF NOT EXISTS appointment_reminders (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id      uuid NOT NULL,
  appointment_id uuid NOT NULL REFERENCES appointments(id) ON DELETE CASCADE,
  reminder_type  text NOT NULL CHECK (reminder_type IN ('24h', '2h')),
  scheduled_for  timestamptz NOT NULL,
  sent_at        timestamptz,
  status         text NOT NULL DEFAULT 'pending'
                   CHECK (status IN ('pending', 'sending', 'sent', 'failed', 'skipped')),
  created_at     timestamptz NOT NULL DEFAULT now(),
  UNIQUE (appointment_id, reminder_type)
);

CREATE INDEX IF NOT EXISTS idx_appointment_reminders_due
  ON appointment_reminders (scheduled_for, status);

-- Per-tenant opt-out toggle for this feature (dashboard settings, exposed via
-- GET/PUT /api/v1/appointments/reminders/settings/{tenant_id}). Bundled into
-- this migration rather than a separate file because it's the same feature
-- and the router needs it to exist before the toggle endpoints are useful.
-- Defaults to enabled — reminders cutting no-shows is the point of the
-- feature; tenants opt out, not in.
ALTER TABLE tenants
  ADD COLUMN IF NOT EXISTS appointment_reminders_enabled boolean NOT NULL DEFAULT true;
