-- Migration 016: Add tags column to leads table for auto-tagging from conversations
-- Tags are extracted by AI during lead capture (e.g., "interested in: kitchen remodel", "budget: high")

ALTER TABLE leads ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}';

-- Index for tag-based filtering
CREATE INDEX IF NOT EXISTS idx_leads_tags ON leads USING GIN (tags);
