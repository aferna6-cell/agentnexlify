/**
 * Action item management API functions.
 */
import { request } from "./_client";

export function fetchActionItems(tenantId, token, params = {}) {
  const qs = new URLSearchParams();
  if (params.status) qs.set("status", params.status);
  if (params.priority) qs.set("priority", params.priority);
  if (params.limit) qs.set("limit", params.limit);
  const q = qs.toString();
  return request(`/api/v1/action-items/${tenantId}${q ? `?${q}` : ""}`, { token });
}

export function fetchActionItemsSummary(tenantId, token) {
  return request(`/api/v1/action-items/${tenantId}/summary`, { token });
}

export function createActionItem(tenantId, token, data) {
  return request(`/api/v1/action-items/${tenantId}`, { method: "POST", token, body: data });
}

export function updateActionItem(tenantId, token, itemId, data) {
  return request(`/api/v1/action-items/${tenantId}/${itemId}`, { method: "PUT", token, body: data });
}

export function deleteActionItem(tenantId, token, itemId) {
  return request(`/api/v1/action-items/${tenantId}/${itemId}`, { method: "DELETE", token });
}
