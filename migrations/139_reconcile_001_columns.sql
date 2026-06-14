-- Migration 139: reconcile migration-001 stale DDL with production reality.
--
-- Audit 2026-06-10 (addendum CRITICAL): migrations/001 declares
-- leads.tenant_id / leads.service_interest / leads.lead_stage and
-- conversations.tenant_id, but LIVE uses leads.client_id /
-- leads.areas_of_interest / leads.status and conversations.client_id.
-- No migration ever creates leads.status or leads.areas_of_interest —
-- they exist ad-hoc in prod only, so a fresh-DB replay of migrations/
-- does NOT reproduce production. Same failure class as the 2026-06-10
-- referral-columns incident.
--
-- This migration is a NO-OP on production (every statement is guarded);
-- its purpose is to make fresh replays converge on the live shape.
-- Never renumber or edit migration 001 — it has been applied.

-- leads: live tenant column is client_id
ALTER TABLE leads ADD COLUMN IF NOT EXISTS client_id UUID REFERENCES tenants(id);
-- leads: live status column (001 called it lead_stage, which never existed live)
ALTER TABLE leads ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'new';
-- leads: live interest column (001 called it service_interest, never existed live)
ALTER TABLE leads ADD COLUMN IF NOT EXISTS areas_of_interest TEXT;

-- conversations: live tenant column is client_id
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS client_id UUID REFERENCES tenants(id);

-- Drop the 001-era names IF they exist (fresh replays create them; prod never had them)
ALTER TABLE leads DROP COLUMN IF EXISTS tenant_id;
ALTER TABLE leads DROP COLUMN IF EXISTS service_interest;
ALTER TABLE leads DROP COLUMN IF EXISTS lead_stage;
ALTER TABLE conversations DROP COLUMN IF EXISTS tenant_id;
