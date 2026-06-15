-- Migration 152: pay_gate_exempt column for grandfathering existing tenants.
--
-- New signups (pay_gate_exempt = false by default) must pay before accessing
-- the dashboard. All tenants that existed before this migration are grandfathered
-- (pay_gate_exempt = true) so they are never blocked.
--
-- Applied: parent session applies via Supabase MCP. DO NOT apply here.

ALTER TABLE tenants
  ADD COLUMN IF NOT EXISTS pay_gate_exempt boolean NOT NULL DEFAULT false;

-- Grandfather every existing row so no current customer is blocked.
UPDATE tenants SET pay_gate_exempt = true;
