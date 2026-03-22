/**
 * Automation sequences API functions.
 */
import { request } from "./_client";

export function fetchSequences(tenantId, token) {
  return request(`/api/v1/sequences/${tenantId}`, { token });
}

export function createSequence(tenantId, token, data) {
  return request(`/api/v1/sequences/${tenantId}`, { method: "POST", token, body: data });
}

export function updateSequence(tenantId, token, seqId, data) {
  return request(`/api/v1/sequences/${tenantId}/${seqId}`, { method: "PUT", token, body: data });
}

export function deleteSequence(tenantId, token, seqId) {
  return request(`/api/v1/sequences/${tenantId}/${seqId}`, { method: "DELETE", token });
}

export function toggleSequence(tenantId, token, seqId) {
  return request(`/api/v1/sequences/${tenantId}/${seqId}/toggle`, { method: "POST", token });
}

export function fetchSequenceDetail(tenantId, token, seqId) {
  return request(`/api/v1/sequences/${tenantId}/${seqId}`, { token });
}

export function fetchSequenceStats(tenantId, token) {
  return request(`/api/v1/sequences/${tenantId}/stats`, { token });
}

export function createFromTemplate(tenantId, token, templateId) {
  return request(`/api/v1/sequences/${tenantId}/templates`, { method: "POST", token, body: { template_id: templateId } });
}
