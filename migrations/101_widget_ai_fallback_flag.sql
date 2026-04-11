-- Migration 101: widget_ai_fallback_flag
-- Date: 2026-04-10
--
-- Adds an opt-in boolean to widget_configs controlling whether widget chat
-- escalates to the support_agent managed agent as a second-tier fallback
-- when the first-tier Claude reply emits the FALLBACK_TO_SUPPORT_AGENT
-- marker. Default false — rollout is tenant-by-tenant.
--
-- See backend/routers/widget_chat.py:Step 9a and
-- docs/managed-agents.md for the full flow description.

ALTER TABLE widget_configs
    ADD COLUMN IF NOT EXISTS enable_ai_fallback boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN widget_configs.enable_ai_fallback IS
'When true, widget chat escalates to the support_agent managed agent as a second-tier fallback before human handoff. Added 2026-04-10 (migration 101).';
