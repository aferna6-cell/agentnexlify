-- Migration 026: Add assigned_to column to leads
-- Allows assigning leads to specific team members for follow-up.
-- FK references team_members(id), nullable (unassigned by default).

ALTER TABLE leads ADD COLUMN IF NOT EXISTS assigned_to UUID REFERENCES team_members(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_leads_assigned_to ON leads(client_id, assigned_to)
    WHERE assigned_to IS NOT NULL;
