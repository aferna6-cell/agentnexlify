/**
 * Widget health check and allowed-domains configuration API functions.
 *
 * Endpoints:
 *   GET  /api/v1/widget-health/{tenant_id}
 *   PUT  /api/v1/widget/config/{tenant_id}/allowed-domains
 */
import { request } from "./_client";

/**
 * Fetch the full integration/setup health check payload for a tenant.
 * @param {string} tenantId
 * @param {string} token  - JWT bearer token
 * @returns {Promise<{overall: string, checks: Array, allowed_domains: string[], stats: object}>}
 */
export function getWidgetHealth(tenantId, token) {
  return request(`/api/v1/widget-health/${tenantId}`, { token });
}

/**
 * Replace the full allowed-domains list for a tenant's widget configuration.
 * Mirrors the base path of /api/v1/widget/config/{tenant_id}/online-status.
 * @param {string} tenantId
 * @param {string} token  - JWT bearer token
 * @param {string[]} domains - normalized domain list (replaces existing list entirely)
 * @returns {Promise<{allowed_domains: string[]}>}
 */
export function updateAllowedDomains(tenantId, token, domains) {
  return request(`/api/v1/widget/config/${tenantId}/allowed-domains`, {
    method: "PUT",
    token,
    body: { allowed_domains: domains },
  });
}
