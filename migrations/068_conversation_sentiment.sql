-- Migration 068: Add sentiment column to conversations table
-- Stores AI-analyzed overall sentiment of each conversation
-- Values: positive, neutral, negative (same as calls.sentiment)

ALTER TABLE conversations
    ADD COLUMN IF NOT EXISTS sentiment TEXT CHECK (sentiment IN ('positive', 'neutral', 'negative'));

-- Index for dashboard analytics queries filtering by sentiment
CREATE INDEX IF NOT EXISTS idx_conversations_sentiment
    ON conversations(client_id, sentiment)
    WHERE sentiment IS NOT NULL;
