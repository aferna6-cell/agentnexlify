-- Migration 041: MCP API keys for AI assistant integration
-- Separate from widget API keys. Used to authenticate MCP server connections.

ALTER TABLE tenants ADD COLUMN IF NOT EXISTS mcp_api_key TEXT;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS mcp_enabled BOOLEAN NOT NULL DEFAULT false;

CREATE UNIQUE INDEX IF NOT EXISTS idx_tenants_mcp_key ON tenants(mcp_api_key) WHERE mcp_api_key IS NOT NULL;
