-- Migration 104 — 2026-04-22 (planned, apply after 1 week clean rollout)
-- Changes enable_structured_lead_parser default from false to true for all
-- new widget_configs rows. Existing rows are unchanged.
--
-- Gate: apply ONLY after ≥95% lead-field completion rate holds for 7 days
-- across all 5 Phase 5 testers (MTOptions + 4 others).
-- See: audits/audit-lead-enrichment-2026-04-15.md Step 6.

ALTER TABLE widget_configs
    ALTER COLUMN enable_structured_lead_parser SET DEFAULT true;

COMMENT ON COLUMN widget_configs.enable_structured_lead_parser IS
'When true, widget chat runs the structured_extractor managed agent as a background
enrichment pass on each user message to fill in name/email/phone/interest/timeline/budget
fields the regex parser missed. Added 2026-04-15 (migration 103). Default changed to
true 2026-04-22 (migration 104) after 1-week clean rollout.';
