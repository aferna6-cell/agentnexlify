-- Migration 018: Add tags to conversations for organization
-- Allows business owners to label/categorize conversations (e.g., "sales", "support", "complaint")

ALTER TABLE conversations ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}';

CREATE INDEX IF NOT EXISTS idx_conversations_tags ON conversations USING GIN (tags);
