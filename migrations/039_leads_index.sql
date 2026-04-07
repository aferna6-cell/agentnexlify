-- Migration 039: Add compound index on leads for common query patterns
-- Speeds up: lead list page (sorted by created_at), analytics date-range queries,
-- and dashboard summary counts.

ALTER TABLE leads ADD COLUMN IF NOT EXISTS client_id UUID REFERENCES tenants(id) ON DELETE CASCADE;
UPDATE leads SET client_id = tenant_id WHERE client_id IS NULL AND tenant_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_leads_client_created ON leads(client_id, created_at DESC);
