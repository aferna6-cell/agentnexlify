/**
 * Lead management API functions.
 */
import { request, BASE, ApiError } from "./_client";

export function createLead(tenantId, token, data) {
  return request(`/api/v1/leads/${tenantId}`, { method: "POST", token, body: data });
}

export function fetchLeads(tenantId, token, { stage, search, sort, order, assigned_to, page, per_page } = {}) {
  const params = new URLSearchParams();
  if (stage) params.set("stage", stage);
  if (search) params.set("search", search);
  if (sort) params.set("sort", sort);
  if (order) params.set("order", order);
  if (assigned_to) params.set("assigned_to", assigned_to);
  if (page) params.set("page", String(page));
  if (per_page) params.set("per_page", String(per_page));
  const qs = params.toString();
  return request(`/api/v1/leads/${tenantId}${qs ? `?${qs}` : ""}`, { token });
}

export function updateLead(tenantId, token, leadId, data) {
  return request(`/api/v1/leads/${tenantId}/${leadId}`, { method: "PATCH", token, body: data });
}

export async function deleteLead(tenantId, token, leadId) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${BASE}/api/v1/leads/${tenantId}/${leadId}`, { method: "DELETE", headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new ApiError(res.status, err);
  }
}

export function fetchLeadScore(tenantId, leadId, token) {
  return request(`/api/v1/leads/${tenantId}/${leadId}/score`, { token });
}

export async function importLeadsCSV(tenantId, token, file) {
  const formData = new FormData();
  formData.append("file", file);
  const headers = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${BASE}/api/v1/leads/${tenantId}/import`, { method: "POST", headers, body: formData });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new ApiError(res.status, err);
  }
  return res.json();
}

export function sendLeadEmail(tenantId, token, leadId, data) {
  return request(`/api/v1/leads/${tenantId}/${leadId}/email`, { method: "POST", token, body: data });
}

export function sendLeadSms(tenantId, token, leadId, message) {
  return request(`/api/v1/leads/${tenantId}/${leadId}/sms`, { method: "POST", token, body: { message } });
}

export function requestReviewForLead(tenantId, token, leadId) {
  return request(`/api/v1/reviews/${tenantId}/request-review/${leadId}`, { method: "POST", token });
}

export function assignLead(tenantId, token, leadId, assignedTo) {
  return request(`/api/v1/leads/${tenantId}/${leadId}/assign`, { method: "PUT", token, body: { assigned_to: assignedTo } });
}

export function generateLeadSummary(tenantId, token, leadId) {
  return request(`/api/v1/leads/${tenantId}/${leadId}/generate-summary`, { method: "POST", token });
}

export function findDuplicateLeads(tenantId, token) {
  return request(`/api/v1/leads/${tenantId}/duplicates`, { token });
}

export function mergeLeads(tenantId, token, keepId, mergeId) {
  return request(`/api/v1/leads/${tenantId}/merge`, { method: "POST", token, body: { keep_id: keepId, merge_id: mergeId } });
}

export function fetchLeadSuggestions(tenantId, token) {
  return request(`/api/v1/leads/${tenantId}/suggestions`, { token });
}

export function handleLeadSuggestion(tenantId, token, suggestionId, action) {
  return request(`/api/v1/leads/${tenantId}/suggestions/${suggestionId}`, { method: "POST", token, body: { action } });
}

export function bulkUpdateLeads(tenantId, token, { lead_ids, status, assigned_to, tags_add }) {
  return request(`/api/v1/leads/${tenantId}/bulk-update`, {
    method: "POST", token,
    body: { lead_ids, status: status || undefined, assigned_to: assigned_to || undefined, tags_add: tags_add || undefined },
  });
}

export function fetchLeadActivity(tenantId, token, leadId) {
  return request(`/api/v1/leads/${tenantId}/${leadId}/activity`, { token });
}
