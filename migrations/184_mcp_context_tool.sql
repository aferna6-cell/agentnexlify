-- Migration 184: owner-designated MCP context tool (interop phase 2).
--
-- Phase 1 (mig 179) made agents AWARE of connected MCP servers; calls stayed
-- owner-invoked. Phase 2 lets the owner designate ONE read-only tool per
-- server (plus fixed arguments) whose result is fetched live and injected
-- into every Agent OS run's context. Only that owner-chosen tool auto-runs;
-- arbitrary calls remain owner-invoked from Agent Controls, so side effects
-- stay behind the human gate.

ALTER TABLE tenant_mcp_servers
    ADD COLUMN IF NOT EXISTS context_tool text;

ALTER TABLE tenant_mcp_servers
    ADD COLUMN IF NOT EXISTS context_args jsonb NOT NULL DEFAULT '{}'::jsonb;
