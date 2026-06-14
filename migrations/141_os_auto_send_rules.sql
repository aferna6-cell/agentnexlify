-- Migration 141: per-agent auto-send rules (gap G6).
--
-- os_auto_send_enabled was all-or-nothing: a 2 AM widget FAQ answer waited
-- for morning approval unless the owner trusted EVERYTHING to auto-send.
-- os_auto_send_rules holds per-agent overrides: {"booking": true,
-- "generalist": false}. Gate logic lives in
-- agent_os_bridge.resolve_deliverable_status — a per-agent value beats the
-- global flag; agents in NEVER_AUTO_SEND_AGENTS always require approval.

ALTER TABLE tenants
  ADD COLUMN IF NOT EXISTS os_auto_send_rules JSONB NOT NULL DEFAULT '{}'::jsonb;
