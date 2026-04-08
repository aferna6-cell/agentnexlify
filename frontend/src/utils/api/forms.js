/**
 * Forms & surveys API functions.
 */
import { request } from "./_client";

export function fetchForms(tenantId, token) {
  return request(`/api/v1/forms/${tenantId}`, { token });
}

export function createForm(tenantId, token, data) {
  return request(`/api/v1/forms/${tenantId}`, { method: "POST", token, body: data });
}

export function fetchForm(tenantId, token, formId) {
  return request(`/api/v1/forms/${tenantId}/${formId}`, { token });
}

export function updateForm(tenantId, token, formId, data) {
  return request(`/api/v1/forms/${tenantId}/${formId}`, { method: "PUT", token, body: data });
}

export function deleteForm(tenantId, token, formId) {
  return request(`/api/v1/forms/${tenantId}/${formId}`, { method: "DELETE", token });
}

export function fetchFormSubmissions(tenantId, token, formId) {
  return request(`/api/v1/forms/${tenantId}/${formId}/submissions`, { token });
}

export function fetchFormStats(tenantId, token) {
  return request(`/api/v1/forms/${tenantId}/stats`, { token });
}
