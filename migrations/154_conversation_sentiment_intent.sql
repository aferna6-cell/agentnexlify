-- Migration 154: per-conversation sentiment + intent on conversations
-- Stores a classification (sentiment + intent) for each widget conversation so
-- the Conversation Insights agent can report a real sentiment breakdown instead
-- of inferring it from complaint keywords. Populated off the user hot path by
-- backend/services/conversation_enrichment.py (Haiku classification).
--
-- The conversations table is client_id-scoped (see schema-discipline.md), one
-- row per (client_id, session_id). Both columns are nullable: unclassified
-- conversations and graceful classification failures leave them NULL.
--
-- Sentiment vocabulary mirrors the calls table (migration 044) exactly:
--   sentiment IN ('positive', 'neutral', 'negative').

ALTER TABLE conversations
    ADD COLUMN IF NOT EXISTS sentiment TEXT
        CHECK (sentiment IN ('positive', 'neutral', 'negative'));

ALTER TABLE conversations
    ADD COLUMN IF NOT EXISTS intent TEXT;
