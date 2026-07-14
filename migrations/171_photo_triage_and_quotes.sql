-- Migration 171: photo-triage + instant quoting (opportunities #R1 + #R2)
--
-- #R1 Photo-triage: a widget visitor uploads 1-3 photos (broken pipe, roof,
-- dented car). Claude vision (backend/services/photo_triage.py) assesses
-- urgency + scope and routes to booking / attaches to the lead.
-- `leads.photo_urls` holds the Supabase Storage public URLs for the
-- uploaded photos (same "widget upload -> Supabase Storage, no BLOB column"
-- pattern as ADR "Widget file upload: Supabase Storage, no new migration");
-- `leads.ai_triage` holds the structured assessment
-- ({urgency, category, scope_summary, recommended_action}). `leads` uses
-- `client_id`, NOT `tenant_id` — see .claude/rules/schema-discipline.md.
-- No new column added to `leads` follows the tenant/client_id pattern
-- because these two columns describe the lead itself, not tenant ownership.
--
-- #R2 Instant quoting: from a job description (+ optional triage), draft an
-- itemized Good/Better/Best quote (backend/services/quote_builder.py)
-- GROUNDED in the tenant's own `service_types` catalog (migration 063) —
-- the moat is real tenant prices, never generic/invented ones. `quotes` is
-- a per-tenant aggregate table, so it uses `tenant_id` (standard column,
-- not the leads-table `client_id` pattern). `lead_id` is an FK-less pointer
-- to `leads.id`, matching the no-FK-to-cross-schema convention used by
-- `review_responses.review_id` (migrations/168_review_responses.sql) —
-- keeps this table decoupled from `leads` schema churn.
--
-- No RLS on `quotes` — matches the two most recent per-tenant tables
-- (167_appointment_reminders.sql, 168_review_responses.sql, and
-- 170_bot_health_scores.sql). The app uses a Supabase service-role client
-- exclusively; RLS is not the guardrail here.

ALTER TABLE leads ADD COLUMN IF NOT EXISTS photo_urls jsonb;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS ai_triage jsonb;

CREATE TABLE IF NOT EXISTS quotes (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        uuid NOT NULL,
    lead_id          uuid,             -- FK-less pointer to leads.id, when known
    job_description  text NOT NULL,
    triage           jsonb,
    tiers            jsonb NOT NULL,   -- {"good": {...}, "better": {...}, "best": {...}}
    status           text NOT NULL DEFAULT 'draft'
                     CHECK (status IN ('draft', 'sent', 'accepted', 'rejected')),
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now()
);

-- Dashboard query: "give me tenant X's quotes, newest first".
CREATE INDEX IF NOT EXISTS idx_quotes_tenant_created
    ON quotes (tenant_id, created_at DESC);
