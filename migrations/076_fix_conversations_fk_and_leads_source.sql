-- Migration 076: Fix conversations FK + add leads.source column
--
-- Root cause of analytics showing 0 conversations:
--   conversations.client_id had a FK pointing to the legacy `clients` table
--   (from the original real-estate-agent platform). Widget chat inserts
--   `client_id = tenant_id` (a UUID from `tenants`), which violates the FK
--   and is silently rejected. The conversations table stays empty, so any
--   endpoint querying it returns 0.
--
-- Fix 1: Re-point the FK to tenants.id (correct multi-tenant table).
-- Fix 2: Add leads.source column for lead source analytics.

-- Fix 1: Re-point conversations.client_id FK to tenants
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS client_id UUID REFERENCES tenants(id) ON DELETE CASCADE;
UPDATE conversations SET client_id = tenant_id WHERE client_id IS NULL AND tenant_id IS NOT NULL;

ALTER TABLE conversations DROP CONSTRAINT IF EXISTS conversations_client_id_fkey;
ALTER TABLE conversations
  ADD CONSTRAINT conversations_client_id_fkey
  FOREIGN KEY (client_id) REFERENCES tenants(id) ON DELETE CASCADE;

-- Fix 2: Add source column to leads table
ALTER TABLE leads ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'widget';
-- Back-fill existing leads with 'widget' source (they came from the widget)
UPDATE leads SET source = 'widget' WHERE source IS NULL;
