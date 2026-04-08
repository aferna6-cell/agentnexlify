/**
 * Snippet (quick reply) management API functions.
 */
import { request } from "./_client";

export function fetchSnippets(tenantId, token, params = {}) {
  const qs = new URLSearchParams();
  if (params.category) qs.set("category", params.category);
  if (params.search) qs.set("search", params.search);
  const q = qs.toString();
  return request(`/api/v1/snippets/${tenantId}${q ? `?${q}` : ""}`, { token });
}

export function createSnippet(tenantId, token, data) {
  return request(`/api/v1/snippets/${tenantId}`, { method: "POST", token, body: data });
}

export function updateSnippet(tenantId, token, snippetId, data) {
  return request(`/api/v1/snippets/${tenantId}/${snippetId}`, { method: "PUT", token, body: data });
}

export function deleteSnippet(tenantId, token, snippetId) {
  return request(`/api/v1/snippets/${tenantId}/${snippetId}`, { method: "DELETE", token });
}

