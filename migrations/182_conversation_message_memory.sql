-- 182: conversation message memory tier (issue #69) — APPLIED 2026-07-21
--
-- Status: APPLIED to prod Supabase 2026-07-21 by fable5 via apply_migration.
--   Verified: message_relevance_score + message_confidence columns present,
--   idx_chat_messages_session_confidence partial index created.
-- Author: fable5 (Agent Nexlify team contract) — lane team/69/fable5/conversation-memory-tier
-- Issue: #69. Migration number 182 chosen next-free after 180 (PR #517) and
--   181 (PR #518); the issue body's "migration 110/111" is long stale.
--
-- SCHEMA CORRECTION (contract §7 — applied schema wins over the issue text):
--   The issue proposed columns on `conversations.messages` keyed by
--   `conversation_id`, scoped by `client_id`. All three are wrong for this repo:
--     * `conversations.messages` (JSONB) was DROPPED in the reconciliation
--       migration — the canonical message store is `chat_messages`
--       (pre-commit guard enforces this).
--     * `chat_messages` is keyed by `session_id` (TEXT), not `conversation_id`.
--     * `chat_messages` is scoped by `tenant_id`, not `client_id`
--       (client_id is the leads/conversations convention only).
--   So the scoring columns + index land on `chat_messages` accordingly.

ALTER TABLE chat_messages
    ADD COLUMN IF NOT EXISTS message_relevance_score double precision NOT NULL DEFAULT 0.5;

ALTER TABLE chat_messages
    ADD COLUMN IF NOT EXISTS message_confidence double precision NOT NULL DEFAULT 0.8;

-- Retrieval only ever considers reasonably-confident messages; a partial index
-- keeps it small and fast for the per-session memory-tier lookup.
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_confidence
    ON chat_messages (session_id, message_confidence)
    WHERE message_confidence > 0.3;
