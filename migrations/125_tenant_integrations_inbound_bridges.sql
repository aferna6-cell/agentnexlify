-- 125_tenant_integrations_inbound_bridges.sql
-- Agent OS Connector Group A: bridge toggle storage.
--
-- Per spec §Data Model, per-tenant bridge toggles live in
-- ``tenant_integrations`` keyed by ``provider='os_inbound_bridges'`` with
-- the per-source enabled flags in ``config_jsonb``. The existing CHECK
-- constraint on ``tenant_integrations.provider`` (migration 109) only
-- allows the four Drive providers. This migration extends it to add
-- ``os_inbound_bridges`` as a valid provider sentinel.
--
-- Source spec: specs/agent-os-connectors-inbound_spec.md
-- Build plan:  plans/agent-os-connectors-inbound_plan.md
--
-- Stored row shape:
--   provider     = 'os_inbound_bridges'
--   config_jsonb = {
--                    "widget_enabled":   true|false,
--                    "email_enabled":    true|false,
--                    "sms_enabled":      true|false,
--                    "facebook_enabled": true|false,
--                    "email_provider":   "postmark"|"mailgun"|null,
--                    "email_inbound_address": "agent@tenant.com"|null
--                  }
--   oauth_*      = unused for this provider (NULL)
--
-- The unique (client_id, provider) constraint from 109 enforces one
-- bridge-config row per tenant.

ALTER TABLE tenant_integrations
    DROP CONSTRAINT IF EXISTS tenant_integrations_provider_check;

ALTER TABLE tenant_integrations
    ADD CONSTRAINT tenant_integrations_provider_check
    CHECK (provider IN (
        'drive',
        'dropbox',
        'onedrive',
        'box',
        'os_inbound_bridges'
    ));

-- ---------------------------------------------------------------------------
-- Notes
-- ---------------------------------------------------------------------------
-- 1. No data migration. Existing rows already conform to the old subset.
-- 2. RLS unchanged. Service-role-only policy from 109 still applies.
-- 3. Rollback: re-add the old CHECK (drop 'os_inbound_bridges' first if any
--    rows were written under it).
