-- Migration 103 — Structured lead parser flag
-- Date: 2026-04-15
-- Source spec: /specs/lead-parser-replacement_spec.md
-- Plan: /plans/lead-parser-replacement_plan.md (Phase 1)
--
-- Adds opt-in boolean controlling whether widget chat runs the
-- structured_extractor managed agent as a background enrichment pass
-- on each user message. Fills name/email/phone/interest/timeline/budget
-- fields the regex parser missed.
--
-- Default false — zero behavior change until tenant explicitly enabled.
-- Reversible via DROP COLUMN.

ALTER TABLE widget_configs
    ADD COLUMN IF NOT EXISTS enable_structured_lead_parser boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN widget_configs.enable_structured_lead_parser IS
'When true, widget chat runs the structured_extractor managed agent as a background enrichment pass on each user message to fill in name/email/phone/interest/timeline/budget fields the regex parser missed. Added 2026-04-15 (migration 103). Spec: /specs/lead-parser-replacement_spec.md';
