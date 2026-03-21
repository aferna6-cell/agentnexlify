/**
 * Content Studio API functions.
 */
import { request } from "./_client";

export function fetchContentItems(tenantId, token, { status } = {}) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  const qs = params.toString() ? `?${params}` : "";
  return request(`/api/v1/content/${tenantId}${qs}`, { token });
}

export function fetchContentItem(tenantId, token, contentId) {
  return request(`/api/v1/content/${tenantId}/${contentId}`, { token });
}

export function createContentItem(tenantId, token, data) {
  return request(`/api/v1/content/${tenantId}`, { method: "POST", token, body: data });
}

export function updateContentItem(tenantId, token, contentId, data) {
  return request(`/api/v1/content/${tenantId}/${contentId}`, { method: "PATCH", token, body: data });
}

export function deleteContentItem(tenantId, token, contentId) {
  return request(`/api/v1/content/${tenantId}/${contentId}`, { method: "DELETE", token });
}

export function repurposeContent(tenantId, token, contentId) {
  return request(`/api/v1/content/${tenantId}/${contentId}/repurpose`, { method: "POST", token });
}
