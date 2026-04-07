-- Migration 095: Add conversation memory column
-- Date: 2026-04-07
-- Purpose: Store structured conversation memory for context continuity across
--   AI interactions without needing the full message history in the prompt.

ALTER TABLE conversations ADD COLUMN IF NOT EXISTS memory JSONB;

-- Index for querying conversations with memory (useful for analytics)
CREATE INDEX IF NOT EXISTS idx_conversations_has_memory ON conversations USING GIN (memory) WHERE memory IS NOT NULL;
