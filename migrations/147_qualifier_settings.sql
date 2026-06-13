-- Migration 147: per-tenant AI lead-qualifier settings
--
-- Ported from PR #212 (branch gap-3-research-worker-87IXF).
-- Original was migration 134 on that branch; renumbered 147 here because
-- 134–146 are already applied on this branch.
--
-- Adds an owner-facing kill switch and a cost threshold for the AI lead
-- qualifier (backend/services/lead_qualification.py). Both columns are
-- additive with safe defaults so existing tenants keep current behavior:
--   qualifier_enabled    = true  -> qualifier runs (matches pre-147 behavior)
--   qualifier_min_intent = 0     -> no rule-score gate (always qualify)
--
-- qualifier_min_intent is compared against leads.lead_score (1-10 rule-based
-- score from lead_scoring.py): the AI qualifier is skipped when a lead's cheap
-- rule score is below the threshold, so owners only spend Managed-Agent budget
-- on leads that already look promising.

ALTER TABLE tenants
    ADD COLUMN IF NOT EXISTS qualifier_enabled BOOLEAN NOT NULL DEFAULT true;

ALTER TABLE tenants
    ADD COLUMN IF NOT EXISTS qualifier_min_intent INTEGER NOT NULL DEFAULT 0;

-- Keep the threshold inside the lead_score scale (0 disables the gate, 1-10
-- mirrors the rule-based score range).
ALTER TABLE tenants
    DROP CONSTRAINT IF EXISTS tenants_qualifier_min_intent_range;
ALTER TABLE tenants
    ADD CONSTRAINT tenants_qualifier_min_intent_range
    CHECK (qualifier_min_intent >= 0 AND qualifier_min_intent <= 10);

COMMENT ON COLUMN tenants.qualifier_enabled IS
    'Owner toggle for AI lead qualification (lead_qualification.py). Default true.';
COMMENT ON COLUMN tenants.qualifier_min_intent IS
    'Minimum rule-based lead_score (0-10) required to run AI qualification. 0 = always.';
