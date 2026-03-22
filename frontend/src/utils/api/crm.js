/**
 * CRM / client management API functions.
 */
import { request } from "./_client";

export function fetchClients(tenantId, token, { search, stage, sort, order } = {}) {
  const params = new URLSearchParams();
  if (search) params.set("search", search);
  if (stage) params.set("stage", stage);
  if (sort) params.set("sort", sort);
  if (order) params.set("order", order);
  const qs = params.toString();
  return request(`/api/v1/clients/${tenantId}${qs ? `?${qs}` : ""}`, { token });
}

export function fetchClientProfile(tenantId, leadId, token) {
  return request(`/api/v1/clients/${tenantId}/${leadId}`, { token });
}

export function fetchClientTimeline(tenantId, leadId, token, { offset = 0, limit = 20 } = {}) {
  return request(`/api/v1/clients/${tenantId}/${leadId}/timeline?offset=${offset}&limit=${limit}`, { token });
}

export function addClientNote(tenantId, leadId, token, content) {
  return request(`/api/v1/clients/${tenantId}/${leadId}/notes`, {
    method: "POST",
    token,
    body: { content },
  });
}

export function updateClient(tenantId, leadId, token, data) {
  return request(`/api/v1/clients/${tenantId}/${leadId}`, {
    method: "PUT",
    token,
    body: data,
  });
}

export function changeClientStage(tenantId, leadId, token, stage) {
  return request(`/api/v1/clients/${tenantId}/${leadId}/stage`, {
    method: "PUT",
    token,
    body: { stage },
  });
}

export function fetchCrmDashboardWidgets(tenantId, token) {
  return request(`/api/v1/clients/${tenantId}/dashboard-widgets`, { token });
}
