/**
 * Smart Lists (dynamic lead segments) API functions.
 */
import { request, BASE, ApiError } from "./_client";

export function fetchSmartLists(tenantId, token) {
  return request(`/api/v1/smart-lists/${tenantId}`, { token });
}

export function createSmartList(tenantId, token, data) {
  return request(`/api/v1/smart-lists/${tenantId}`, { method: "POST", token, body: data });
}

export function updateSmartList(tenantId, token, listId, data) {
  return request(`/api/v1/smart-lists/${tenantId}/${listId}`, { method: "PUT", token, body: data });
}

export function deleteSmartList(tenantId, token, listId) {
  return request(`/api/v1/smart-lists/${tenantId}/${listId}`, { method: "DELETE", token });
}

export function fetchSmartListLeads(tenantId, token, listId) {
  return request(`/api/v1/smart-lists/${tenantId}/${listId}/leads`, { token });
}

export function refreshSmartList(tenantId, token, listId) {
  return request(`/api/v1/smart-lists/${tenantId}/${listId}/refresh`, { method: "POST", token });
}

export async function exportSmartList(tenantId, token, listId) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${BASE}/api/v1/smart-lists/${tenantId}/${listId}/export`, { headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new ApiError(res.status, err);
  }
  return res.blob();
}
