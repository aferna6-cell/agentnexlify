-- Migration 179: tenant-configured MCP servers (enterprise-audit item 5).
--
-- V1 of open interop: a tenant can register Streamable-HTTP MCP servers whose
-- tools the Agent OS can list and (owner-invoked) call. Gated platform-wide
-- by the os_mcp_enabled flag; calls are owner-initiated from the dashboard,
-- so the propose-only trust model is preserved.
--
-- auth_token is stored like integrations tokens today (plaintext pending the
-- INTEGRATIONS_ENC_KEY rollout, GH #266); it is write-only at the API layer
-- and never returned to clients.

CREATE TABLE IF NOT EXISTS tenant_mcp_servers (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    uuid NOT NULL,
    name         text NOT NULL,
    url          text NOT NULL,
    auth_header  text NOT NULL DEFAULT 'Authorization',
    auth_token   text,
    enabled      boolean NOT NULL DEFAULT true,
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS tenant_mcp_servers_tenant_idx
    ON tenant_mcp_servers (tenant_id, enabled);

ALTER TABLE tenant_mcp_servers ENABLE ROW LEVEL SECURITY;
