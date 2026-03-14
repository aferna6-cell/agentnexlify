-- Migration 035: Team member presence tracking
-- Tracks which conversation each team member is currently viewing.

ALTER TABLE team_members ADD COLUMN IF NOT EXISTS last_active_conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL;
ALTER TABLE team_members ADD COLUMN IF NOT EXISTS last_active_at TIMESTAMPTZ;
