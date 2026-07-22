/**
 * MCP key management - the dedicated mcp_ key owners use to connect
 * Claude Desktop (or any MCP client) to their business data. Distinct
 * from the widget key (anx_...), which the MCP server rejects.
 */

import { request } from "./_client";

/** GET /api/v1/auth/mcp-key/:tenantId -> { mcp_api_key, mcp_enabled } */
export function fetchMcpKey(tenantId, token) {
  return request(`/api/v1/auth/mcp-key/${tenantId}`, { token });
}

/**
 * POST /api/v1/auth/mcp-key/:tenantId -> { mcp_api_key }
 * Generates or rotates the key. 402 when the plan lacks the suite.
 */
export function generateMcpKey(tenantId, token) {
  return request(`/api/v1/auth/mcp-key/${tenantId}`, {
    method: "POST",
    token,
  });
}

/** DELETE /api/v1/auth/mcp-key/:tenantId -> { success } */
export function revokeMcpKey(tenantId, token) {
  return request(`/api/v1/auth/mcp-key/${tenantId}`, {
    method: "DELETE",
    token,
  });
}
