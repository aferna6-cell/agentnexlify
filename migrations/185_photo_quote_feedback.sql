-- 185_photo_quote_feedback.sql
-- Photo-quote pilot instrumentation (#44): tenant feedback + conversion signal.
--
-- Adds two columns to quote_requests so the pilot can measure the two GA-gate
-- metrics: tenant-reported error rate (<5% goal) and quote->appointment
-- conversion (30% goal). Additive + idempotent; the feedback/telemetry code
-- reads them fail-open, so shipping the code before this migration is applied
-- degrades to "no feedback recorded" rather than erroring.
--
-- client_id-scoped table (migration 108). NOT auto-applied — apply via Supabase.

alter table quote_requests
  add column if not exists tenant_feedback text
    check (
      tenant_feedback is null
      or tenant_feedback in ('correct', 'too_low', 'too_high', 'unclear')
    ),
  add column if not exists led_to_appointment boolean not null default false;

-- Feedback lookups for the error-rate metric (only rated rows).
create index if not exists idx_quote_requests_feedback
  on quote_requests (client_id, tenant_feedback)
  where tenant_feedback is not null;

-- Rollback (manual, commented):
-- drop index if exists idx_quote_requests_feedback;
-- alter table quote_requests drop column if exists tenant_feedback;
-- alter table quote_requests drop column if exists led_to_appointment;
