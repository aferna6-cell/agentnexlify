/**
 * Tag definition management API functions.
 */
import { request } from "./_client";

export function fetchTagDefinitions(tenantId, token) {
  return request(`/api/v1/tags/${tenantId}`, { token });
}

export function createTagDefinition(tenantId, token, data) {
  return request(`/api/v1/tags/${tenantId}`, { method: "POST", token, body: data });
}

export function updateTagDefinition(tenantId, token, tagId, data) {
  return request(`/api/v1/tags/${tenantId}/${tagId}`, { method: "PUT", token, body: data });
}

export function deleteTagDefinition(tenantId, token, tagId) {
  return request(`/api/v1/tags/${tenantId}/${tagId}`, { method: "DELETE", token });
}
