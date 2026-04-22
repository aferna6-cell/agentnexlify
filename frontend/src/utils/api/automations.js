/**
 * Automation sequences API functions.
 */
import { request } from "./_client";

export function fetchSequences(tenantId, token) {
  return request(`/api/v1/sequences/${tenantId}`, { token });
}

export function createSequence(tenantId, token, data) {
  return request(`/api/v1/sequences/${tenantId}`, {
    method: "POST",
    token,
    body: data,
  });
}

export function updateSequence(tenantId, token, seqId, data) {
  return request(`/api/v1/sequences/${tenantId}/${seqId}`, {
    method: "PUT",
    token,
    body: data,
  });
}

export function deleteSequence(tenantId, token, seqId) {
  return request(`/api/v1/sequences/${tenantId}/${seqId}`, {
    method: "DELETE",
    token,
  });
}

export function toggleSequence(tenantId, token, seqId) {
  return request(`/api/v1/sequences/${tenantId}/${seqId}/toggle`, {
    method: "POST",
    token,
  });
}

export function fetchSequenceDetail(tenantId, token, seqId) {
  return request(`/api/v1/sequences/${tenantId}/${seqId}`, { token });
}

export function fetchSequenceStats(tenantId, token) {
  return request(`/api/v1/sequences/${tenantId}/stats`, { token });
}

export function createFromTemplate(tenantId, token, templateId) {
  return request(`/api/v1/sequences/${tenantId}/templates`, {
    method: "POST",
    token,
    body: { template_id: templateId },
  });
}

export function fetchAutomations(tenantId, token) {
  return request(`/api/v1/automations/${tenantId}`, { token });
}

/**
 * Fetch automation activity events for the dashboard card.
 *
 * @param {Object} params
 * @param {string} params.tenantId
 * @param {string} params.token - Bearer token
 * @param {number} [params.limit=5] - Max events to return
 * @param {string} [params.type] - Filter by activity_type
 * @param {string} [params.since] - ISO8601 datetime lower bound
 */
export function getActivity({ tenantId, token, limit = 5, type, since }) {
  const qs = new URLSearchParams({ limit: String(limit) });
  if (type) qs.set("type", type);
  if (since) qs.set("since", since);
  return request(`/api/v1/automations/${tenantId}/activity?${qs.toString()}`, {
    token,
  });
}

export function getActivityTotals({ tenantId, token }) {
  return request(`/api/v1/automations/${tenantId}/activity?limit=0`, { token });
}

export function sendCampaign(
  tenantId,
  token,
  { subject, body_html, channel, filters },
) {
  return request(`/api/v1/sequences/${tenantId}/campaigns/send`, {
    method: "POST",
    token,
    body: { subject, body_html, channel, filters },
  });
}

export function fetchEmailTemplates(tenantId, token) {
  return request(`/api/v1/email-templates/${tenantId}`, { token });
}

export function createEmailTemplate(tenantId, token, data) {
  return request(`/api/v1/email-templates/${tenantId}`, {
    method: "POST",
    token,
    body: data,
  });
}
