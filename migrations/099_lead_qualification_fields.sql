-- Migration 099: AI lead qualification fields
-- Date: 2026-04-09
-- Purpose: Store structured output from the Claude Managed Agents
--   `lead_qualifier` agent. Runs asynchronously on paid plans after a
--   new lead is captured. Complements (does NOT replace) the rule-based
--   `lead_scoring` service — the inline scorer runs on every lead, the
--   AI qualifier only on plans >= growth.
--
-- Output shape from the agent (see config/managed_agents.yaml):
--   {
--     "intent_score": 1-10,
--     "fit_score": 1-10,
--     "recommendation": "hot_call_now" | "warm_nurture_sequence"
--                       | "cold_drop" | "disqualify_spam",
--     "reasoning": "...",
--     "suggested_first_reply": "..."
--   }

-- Full structured response as JSON — source of truth for all derived fields.
ALTER TABLE leads ADD COLUMN IF NOT EXISTS qualification_json JSONB;

-- Extracted recommendation for indexed filters + fast dashboard reads.
ALTER TABLE leads ADD COLUMN IF NOT EXISTS qualification_recommendation TEXT
  CHECK (qualification_recommendation IN (
    'hot_call_now', 'warm_nurture_sequence', 'cold_drop', 'disqualify_spam'
  ));

-- When the last successful qualification run completed.
ALTER TABLE leads ADD COLUMN IF NOT EXISTS qualified_at TIMESTAMPTZ;

-- Indexes for dashboard filtering (e.g. "show me all hot leads").
CREATE INDEX IF NOT EXISTS idx_leads_qualification_recommendation
  ON leads(qualification_recommendation)
  WHERE qualification_recommendation IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_leads_qualified_at
  ON leads(qualified_at)
  WHERE qualified_at IS NOT NULL;
