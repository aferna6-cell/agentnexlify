-- Migration 039: Add compound index on leads for common query patterns
-- Speeds up: lead list page (sorted by created_at), analytics date-range queries,
-- and dashboard summary counts.

CREATE INDEX IF NOT EXISTS idx_leads_client_created ON leads(client_id, created_at DESC);
