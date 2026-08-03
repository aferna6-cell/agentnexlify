/**
 * Escalation queue API functions - conversations/issues the AI agent flagged
 * for human review. Tenant is derived from the JWT; no tenant id in the path.
 */
import { request } from "./_client";

export function fetchEscalations(token, status) {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  return request(`/api/v1/escalations${qs}`, { token });
}

export function resolveEscalation(token, escalationId) {
  return request(`/api/v1/escalations/${escalationId}/resolve`, {
    method: "POST",
    token,
  });
}

export function assignEscalation(token, escalationId, assignedTo) {
  return request(`/api/v1/escalations/${escalationId}/assign`, {
    method: "POST",
    token,
    body: { assigned_to: assignedTo || null },
  });
}
