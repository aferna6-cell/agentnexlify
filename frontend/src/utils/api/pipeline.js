/**
 * Pipeline / Kanban board API functions.
 */
import { request } from "./_client";

export function fetchPipelineStages(tenantId, token) {
  return request(`/api/v1/pipeline/${tenantId}/stages`, { token });
}

export function fetchPipelineBoard(tenantId, token) {
  return request(`/api/v1/pipeline/${tenantId}/board`, { token });
}

export function fetchPipelineAnalytics(tenantId, token) {
  return request(`/api/v1/pipeline/${tenantId}/analytics`, { token });
}

export function movePipelineLead(tenantId, token, leadId, data) {
  return request(`/api/v1/pipeline/${tenantId}/move/${leadId}`, { method: "PUT", token, body: data });
}
