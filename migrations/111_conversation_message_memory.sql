-- Migration 111: conversation message memory tier
-- Adds relevance scoring, confidence, and embedding columns to chat_messages.
-- Enables MemGPT-style retrieval for sessions exceeding 20 messages:
-- older messages are scored by hybrid formula (cosine + recency + confidence)
-- and top-k are retrieved instead of relying solely on recency compaction.
--
-- See: backend/services/conversation_memory.py
-- Issue: #69

ALTER TABLE chat_messages
    ADD COLUMN IF NOT EXISTS message_relevance_score DOUBLE PRECISION DEFAULT 0.5,
    ADD COLUMN IF NOT EXISTS message_confidence DOUBLE PRECISION DEFAULT 0.8,
    ADD COLUMN IF NOT EXISTS embedding vector(512);

-- Partial index for confidence-filtered retrieval.
-- Only indexes messages above the confidence floor (0.3) per retrieval spec.
-- Scoped by tenant_id + session_id for RLS-consistent access patterns.
CREATE INDEX IF NOT EXISTS idx_chat_messages_memory
    ON chat_messages (tenant_id, session_id, message_confidence)
    WHERE message_confidence > 0.3;
