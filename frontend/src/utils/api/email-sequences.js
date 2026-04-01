/**
 * Email sequences API functions.
 * Endpoint base: /api/v1/email-sequences
 */
import { request } from "./_client";

export function fetchEmailSequences(tenantId, token) {
  return request(`/api/v1/email-sequences`, { token, body: undefined });
}

export function createEmailSequence(tenantId, token, data) {
  return request(`/api/v1/email-sequences`, { method: "POST", token, body: { ...data, tenant_id: tenantId } });
}

export function getEmailSequence(id, token) {
  return request(`/api/v1/email-sequences/${id}`, { token });
}

export function updateEmailSequence(id, token, data) {
  return request(`/api/v1/email-sequences/${id}`, { method: "PUT", token, body: data });
}

export function deleteEmailSequence(id, token) {
  return request(`/api/v1/email-sequences/${id}`, { method: "DELETE", token });
}

export function addEmailSequenceStep(sequenceId, token, data) {
  return request(`/api/v1/email-sequences/${sequenceId}/steps`, { method: "POST", token, body: data });
}

export function updateEmailSequenceStep(sequenceId, stepId, token, data) {
  return request(`/api/v1/email-sequences/${sequenceId}/steps/${stepId}`, { method: "PUT", token, body: data });
}

export function deleteEmailSequenceStep(sequenceId, stepId, token) {
  return request(`/api/v1/email-sequences/${sequenceId}/steps/${stepId}`, { method: "DELETE", token });
}

export function fetchEmailSequenceEnrollments(sequenceId, token) {
  return request(`/api/v1/email-sequences/${sequenceId}/enrollments`, { token });
}

export function enrollLeadInEmailSequence(sequenceId, token, leadId) {
  return request(`/api/v1/email-sequences/${sequenceId}/enroll`, { method: "POST", token, body: { lead_id: leadId } });
}
