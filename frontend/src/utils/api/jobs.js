/**
 * Job board API functions.
 */
import { request } from "./_client";

export function fetchJobs(tenantId, token) {
  return request(`/api/v1/jobs/${tenantId}`, { token });
}

export function createJob(tenantId, token, jobData) {
  return request(`/api/v1/jobs/${tenantId}`, { method: "POST", token, body: jobData });
}

export function updateJob(tenantId, token, jobId, jobData) {
  return request(`/api/v1/jobs/${tenantId}/${jobId}`, { method: "PUT", token, body: jobData });
}

export function deleteJob(tenantId, token, jobId) {
  return request(`/api/v1/jobs/${tenantId}/${jobId}`, { method: "DELETE", token });
}

export function fetchJobApplications(tenantId, token, jobId) {
  return request(`/api/v1/jobs/${tenantId}/${jobId}/applications`, { token });
}

export function updateApplicationStatus(tenantId, token, appId, status, notes) {
  return request(`/api/v1/jobs/${tenantId}/applications/${appId}/status`, { method: "PUT", token, body: { status, notes } });
}

export function aiWriteJobDescription(tenantId, token, roleDescription) {
  return request(`/api/v1/jobs/${tenantId}/ai-write`, { method: "POST", token, body: { role_description: roleDescription } });
}
