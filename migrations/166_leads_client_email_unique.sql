-- Close the duplicate-lead check-then-insert race (launch audit H1, 2026-07-09).
--
-- Lead capture runs as a background task on EVERY chat message and dedups by
-- SELECT-then-INSERT on email. With no DB-level uniqueness, two messages
-- arriving close together in one session both pass the SELECT and both INSERT,
-- creating two lead rows for the same visitor — which then double-fires the
-- owner SMS/email alert, trigger_sequence("new_lead"), sequence enrollment,
-- lead scoring, and the lead.created webhook, and skews funnel metrics.
--
-- This constraint serializes concurrent inserts at the database. It is a plain
-- (non-partial) UNIQUE so PostgREST upsert can use it as an ON CONFLICT arbiter
-- (partial/expression indexes cannot be inferred by PostgREST). NULL emails
-- stay DISTINCT under Postgres defaults, so multiple phone-only leads
-- (email IS NULL) per client remain allowed.
--
-- Verified 0 existing (client_id, email) duplicate groups in production before
-- adding (2026-07-09). Phone-based uniqueness is intentionally NOT added here:
-- one real (client_id, phone) duplicate exists in prod and must be merged by
-- the owner first (customer records are propose-only, not auto-deleted).

ALTER TABLE leads
  ADD CONSTRAINT leads_client_email_uniq UNIQUE (client_id, email);
