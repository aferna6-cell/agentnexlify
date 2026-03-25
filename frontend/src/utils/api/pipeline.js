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

// Pipeline automations
export function fetchPipelineAutomations(tenantId, token) {
  return request(`/api/v1/pipeline/${tenantId}/automations`, { token });
}

export function createPipelineAutomation(tenantId, token, data) {
  return request(`/api/v1/pipeline/${tenantId}/automations`, { method: "POST", token, body: data });
}

export function updatePipelineAutomation(tenantId, token, automationId, data) {
  return request(`/api/v1/pipeline/${tenantId}/automations/${automationId}`, { method: "PUT", token, body: data });
}

export function deletePipelineAutomation(tenantId, token, automationId) {
  return request(`/api/v1/pipeline/${tenantId}/automations/${automationId}`, { method: "DELETE", token });
}
